#!/usr/bin/env python3
"""
iOS remote for AI Data Pipeline.

iOS cannot run the Python/Tk desktop app, so this serves a small web app that
the iPhone/iPad installs on the Home Screen ("Add to Home Screen"). It talks
to the machine running the pipeline: upload documents, start a run, watch the
log, download results.

Security model
  * Every API call needs the access token (constant-time compare). The token
    is generated once and stored in ios_remote/.token (owner-only).
  * The server only ever runs two fixed commands (health check, process the
    input folder). Nothing from a request reaches a shell or a command line.
  * Uploads: extension allow-list, size cap, basename only, never overwrites.
    Downloads: only files inside the output folder.
  * By default it binds to your Tailscale address if there is one, otherwise
    to 127.0.0.1. Serving your home network needs an explicit --host, and
    that traffic is plain HTTP.
"""

import argparse
import hmac
import json
import mimetypes
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
WEB_DIR = HERE / "ios_remote"
TOKEN_FILE = WEB_DIR / ".token"
DEFAULT_PORT = 8765

ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".txt", ".md", ".csv", ".json", ".jsonl"}
MAX_UPLOAD_BYTES = 100 * 1024 * 1024
MAX_LOG_BYTES = 64 * 1024
AUTH_FAIL_LIMIT = 20          # failures per client per minute before lockout
AUTH_WINDOW_SECONDS = 60

STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/manifest.webmanifest": ("manifest.webmanifest", "application/manifest+json"),
    "/apple-touch-icon.png": ("apple-touch-icon.png", "image/png"),
    "/icon-512.png": ("icon-512.png", "image/png"),
}


# --- token -----------------------------------------------------------------

def load_or_create_token(path: Path = TOKEN_FILE) -> str:
    """Return the access token, creating an owner-only file on first use."""
    if path.exists():
        token = path.read_text(encoding="utf-8").strip()
        if token:
            return token
    token = secrets.token_urlsafe(24)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(token + "\n")
    return token


def regenerate_token(path: Path = TOKEN_FILE) -> str:
    if path.exists():
        path.unlink()
    return load_or_create_token(path)


# --- upload / download path safety ----------------------------------------

def safe_upload_name(raw: str) -> Optional[str]:
    """Sanitise a client-supplied file name; None if it is not acceptable."""
    name = os.path.basename((raw or "").replace("\\", "/")).strip()
    if not name or name.startswith("."):       # hidden files are not documents
        return None
    name = re.sub(r"[^A-Za-z0-9._ \-()]", "_", name).strip(" .")
    if not name:
        return None
    if Path(name).suffix.lower() not in ALLOWED_UPLOAD_EXTENSIONS:
        return None
    return name[:150]


def unique_path(directory: Path, name: str) -> Path:
    """A path in `directory` for `name` that does not overwrite anything."""
    target = directory / name
    stem, suffix, n = target.stem, target.suffix, 1
    while target.exists():
        target = directory / f"{stem} ({n}){suffix}"
        n += 1
    return target


def resolve_inside(root: Path, relative: str) -> Optional[Path]:
    """`relative` resolved under `root`, or None if it escapes or is not a file."""
    try:
        candidate = (root / relative).resolve()
        candidate.relative_to(root.resolve())
    except (ValueError, OSError):
        return None
    return candidate if candidate.is_file() else None


# --- job runner ------------------------------------------------------------

class JobRunner:
    """Runs one fixed command at a time and keeps its log."""

    def __init__(self, commands: Dict[str, Sequence[str]], cwd: Path, log_path: Path):
        self.commands = {k: list(v) for k, v in commands.items()}
        self.cwd = cwd
        self.log_path = log_path
        self._lock = threading.Lock()
        self._proc: Optional[subprocess.Popen] = None
        self.current: Optional[str] = None
        self.last: Optional[dict] = None
        self._started = 0.0

    def start(self, name: str) -> bool:
        """Start `name`; False if another job is running. Unknown names raise KeyError."""
        cmd = self.commands[name]
        with self._lock:
            if self._proc is not None and self._proc.poll() is None:
                return False
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            log = open(self.log_path, "wb")
            try:
                self._proc = subprocess.Popen(
                    cmd, cwd=str(self.cwd), stdout=log, stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                )
            finally:
                log.close()
            self.current = name
            self._started = time.time()
            threading.Thread(target=self._wait, args=(self._proc, name), daemon=True).start()
            return True

    def _wait(self, proc: subprocess.Popen, name: str) -> None:
        code = proc.wait()
        with self._lock:
            self.last = {
                "name": name, "exit_code": code,
                "seconds": round(time.time() - self._started, 1),
                "finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            if self._proc is proc:
                self.current = None

    def cancel(self) -> bool:
        with self._lock:
            if self._proc is not None and self._proc.poll() is None:
                self._proc.terminate()
                return True
            return False

    def running(self) -> Optional[str]:
        with self._lock:
            return self.current if self._proc is not None and self._proc.poll() is None else None

    def log_tail(self, max_bytes: int = MAX_LOG_BYTES) -> str:
        try:
            with open(self.log_path, "rb") as f:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                f.seek(max(0, size - max_bytes))
                return f.read().decode("utf-8", errors="replace")
        except FileNotFoundError:
            return ""


# --- HTTP ------------------------------------------------------------------

class RemoteApp:
    """State shared by all requests."""

    def __init__(self, token: str, input_dir: Path, output_dir: Path, runner: JobRunner,
                 web_dir: Path = WEB_DIR, clock: Callable[[], float] = time.time):
        self.token = token
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.runner = runner
        self.web_dir = web_dir
        self._clock = clock
        self._fail_lock = threading.Lock()
        self._failures: Dict[str, List[float]] = {}

    def locked_out(self, client: str) -> bool:
        now = self._clock()
        with self._fail_lock:
            recent = [t for t in self._failures.get(client, []) if now - t < AUTH_WINDOW_SECONDS]
            self._failures[client] = recent
            return len(recent) >= AUTH_FAIL_LIMIT

    def record_failure(self, client: str) -> None:
        with self._fail_lock:
            self._failures.setdefault(client, []).append(self._clock())

    def token_ok(self, supplied: str) -> bool:
        return hmac.compare_digest(supplied.encode("utf-8"), self.token.encode("utf-8"))

    @staticmethod
    def _listing(directory: Path, limit: int = 500) -> List[dict]:
        if not directory.exists():
            return []
        rows = []
        for p in directory.rglob("*"):
            if p.is_file() and not p.name.startswith("."):
                rows.append({"path": p.relative_to(directory).as_posix(), "bytes": p.stat().st_size,
                             "mtime": int(p.stat().st_mtime)})
        rows.sort(key=lambda r: r["mtime"], reverse=True)
        return rows[:limit]

    def status(self) -> dict:
        return {
            "running": self.runner.running(),
            "last_job": self.runner.last,
            "input": self._listing(self.input_dir),
            "output_count": len(self._listing(self.output_dir)),
        }


def make_handler(app: RemoteApp):
    class Handler(BaseHTTPRequestHandler):
        server_version = "AIDataPipelineRemote"
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):  # keep tokens/paths out of the console
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args if args else fmt))

        # -- helpers --
        def _send(self, status: int, body: bytes, ctype: str, extra: Optional[Dict[str, str]] = None):
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, payload) -> None:
            self._send(status, json.dumps(payload).encode("utf-8"), "application/json")

        def _authorised(self) -> bool:
            client = self.client_address[0]
            if app.locked_out(client):
                self._json(HTTPStatus.TOO_MANY_REQUESTS, {"error": "too many failed attempts; wait a minute"})
                return False
            header = self.headers.get("Authorization", "")
            supplied = header[7:].strip() if header.lower().startswith("bearer ") else ""
            if not supplied or not app.token_ok(supplied):
                app.record_failure(client)
                self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorised"})
                return False
            return True

        def _query(self) -> Dict[str, str]:
            return {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}

        # -- routes --
        def do_GET(self):
            path = urlparse(self.path).path
            if path in STATIC_FILES:
                fname, ctype = STATIC_FILES[path]
                f = app.web_dir / fname
                if not f.is_file():
                    return self._json(HTTPStatus.NOT_FOUND, {"error": "missing asset"})
                return self._send(HTTPStatus.OK, f.read_bytes(), ctype)
            if not path.startswith("/api/"):
                return self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            if not self._authorised():
                return
            if path == "/api/status":
                return self._json(HTTPStatus.OK, app.status())
            if path == "/api/log":
                return self._send(HTTPStatus.OK, app.runner.log_tail().encode("utf-8"), "text/plain; charset=utf-8")
            if path == "/api/outputs":
                return self._json(HTTPStatus.OK, {"files": app._listing(app.output_dir)})
            if path == "/api/download":
                f = resolve_inside(app.output_dir, self._query().get("path", ""))
                if f is None:
                    return self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
                ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
                return self._send(HTTPStatus.OK, f.read_bytes(), ctype,
                                  {"Content-Disposition": 'attachment; filename="%s"' % f.name.replace('"', "")})
            return self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def do_POST(self):
            path = urlparse(self.path).path
            if not path.startswith("/api/"):
                return self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            if not self._authorised():
                return
            if path in ("/api/health", "/api/process"):
                job = "health" if path == "/api/health" else "process"
                if not app.runner.start(job):
                    return self._json(HTTPStatus.CONFLICT, {"error": "a job is already running"})
                return self._json(HTTPStatus.ACCEPTED, {"started": job})
            if path == "/api/cancel":
                return self._json(HTTPStatus.OK, {"cancelled": app.runner.cancel()})
            if path == "/api/upload":
                return self._upload()
            return self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def _upload(self):
            name = safe_upload_name(self._query().get("name", ""))
            if name is None:
                return self._json(HTTPStatus.BAD_REQUEST, {
                    "error": "file name missing or type not allowed (%s)" % ", ".join(sorted(ALLOWED_UPLOAD_EXTENSIONS))})
            try:
                length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                return self._json(HTTPStatus.LENGTH_REQUIRED, {"error": "Content-Length required"})
            if length <= 0:
                return self._json(HTTPStatus.BAD_REQUEST, {"error": "empty upload"})
            if length > MAX_UPLOAD_BYTES:
                return self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                                  {"error": "file larger than %d MB" % (MAX_UPLOAD_BYTES // 1024 // 1024)})
            app.input_dir.mkdir(parents=True, exist_ok=True)
            target = unique_path(app.input_dir, name)
            tmp = target.with_name(target.name + ".part")
            remaining = length
            try:
                with open(tmp, "wb") as out:
                    while remaining > 0:
                        chunk = self.rfile.read(min(1 << 20, remaining))
                        if not chunk:
                            raise ConnectionError("client closed before the upload finished")
                        out.write(chunk)
                        remaining -= len(chunk)
                os.replace(tmp, target)
            except Exception:
                tmp.unlink(missing_ok=True)
                self.close_connection = True
                return self._json(HTTPStatus.BAD_REQUEST, {"error": "upload interrupted"})
            return self._json(HTTPStatus.CREATED, {"saved": target.name, "bytes": length})

    return Handler


def build_server(host: str, port: int, app: RemoteApp) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), make_handler(app))
    server.daemon_threads = True
    return server


# --- addresses / CLI ---------------------------------------------------------

def tailscale_ip() -> Optional[str]:
    exe = shutil.which("tailscale")
    if not exe:
        return None
    try:
        out = subprocess.run([exe, "ip", "-4"], capture_output=True, text=True, timeout=5)
        ip = out.stdout.strip().splitlines()[0] if out.returncode == 0 and out.stdout.strip() else ""
        return ip or None
    except (OSError, subprocess.SubprocessError):
        return None


def lan_ip() -> Optional[str]:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("192.0.2.1", 9))     # no packet is sent; selects the outbound interface
            return s.getsockname()[0]
    except OSError:
        return None


def access_url(host: str, port: int, token: str) -> str:
    display = host
    if host in ("0.0.0.0", ""):
        display = lan_ip() or "localhost"
    return f"http://{display}:{port}/?t={token}"


def print_qr(url: str) -> None:
    try:
        import segno
    except ImportError:
        print("(install 'segno' for a scannable QR code: pip install segno)")
        return
    segno.make(url, error="m").terminal(compact=True)


def default_runner(project_dir: Path) -> JobRunner:
    py = sys.executable
    return JobRunner(
        commands={
            "health": [py, str(project_dir / "operational_health_check.py"), "--init-folders", "--smoke"],
            "process": [py, str(project_dir / "pipeline_cli.py"), "process"],
        },
        cwd=project_dir,
        log_path=project_dir / "logs" / "ios_remote_job.log",
    )


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Serve the AI Data Pipeline iOS remote")
    ap.add_argument("--host", help="address to bind (default: Tailscale address if present, else 127.0.0.1; "
                                   "use your LAN IP or 0.0.0.0 to serve the home network over plain HTTP)")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--show-url", action="store_true", help="print the access URL (and QR) then exit")
    ap.add_argument("--new-token", action="store_true", help="invalidate the old token and create a new one")
    args = ap.parse_args(argv)

    os.chdir(HERE)                      # the pipeline's folders are relative to here
    sys.path.insert(0, str(HERE))
    from env_config import get_config

    token = regenerate_token() if args.new_token else load_or_create_token()
    host = args.host or tailscale_ip() or "127.0.0.1"
    url = access_url(host, args.port, token)

    if args.show_url:
        print(url)
        print_qr(url)
        return 0

    cfg = get_config()
    app = RemoteApp(token, Path(cfg.input_folder).resolve(), Path(cfg.output_folder).resolve(),
                    default_runner(HERE))
    server = build_server(host, args.port, app)

    print("AI Data Pipeline iOS remote")
    print(f"  Serving on {host}:{args.port}")
    if host not in ("127.0.0.1", "localhost") and not host.startswith("100."):
        print("  NOTE: plain HTTP on your network. Use Tailscale for anything beyond a trusted home network.")
    if host in ("127.0.0.1", "localhost"):
        print("  Reachable from this computer only. Start it with --host <your LAN or Tailscale IP> for your phone.")
    print(f"  Open on the iPhone (Safari), then Share > Add to Home Screen:\n  {url}")
    print_qr(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
