#!/usr/bin/env python3
"""Interactive app launcher installer for Linux, Windows and iOS."""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def ask_yes_no(question: str, default: bool = True) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        reply = input(f"{question} {suffix}: ").strip().lower()
        if not reply:
            return default
        if reply in {"y", "yes"}:
            return True
        if reply in {"n", "no"}:
            return False


def install_linux(script_dir: Path, add_desktop: bool, add_menu: bool) -> None:
    home = Path.home()
    local_bin = home / ".local" / "bin"
    applications_dir = home / ".local" / "share" / "applications"
    desktop_dir = home / "Desktop"
    icon_path = script_dir / "assets" / "robot-head.svg"
    icon_value = str(icon_path) if icon_path.exists() else "applications-science"

    local_bin.mkdir(parents=True, exist_ok=True)
    applications_dir.mkdir(parents=True, exist_ok=True)
    desktop_dir.mkdir(parents=True, exist_ok=True)

    wrapper_path = local_bin / "ai-data-pipeline-launcher"
    run_script = script_dir / "run_pipeline.sh"
    venv_python = script_dir / "venv" / "bin" / "python"

    wrapper_content = f"""#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=\"{script_dir}\"
if [[ -x \"{venv_python}\" ]]; then
  export PYTHON_BIN=\"{venv_python}\"
fi
exec \"{run_script}\"\n"""
    wrapper_path.write_text(wrapper_content, encoding="utf-8")
    os.chmod(wrapper_path, 0o755)

    desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=AI Data Pipeline
Comment=Launch AI Data Pipeline GUI
Exec={wrapper_path}
Icon={icon_value}
Terminal=false
Categories=Development;Utility;
StartupNotify=true
"""

    app_entry = applications_dir / "ai-data-pipeline.desktop"
    desktop_entry = desktop_dir / "AI Data Pipeline.desktop"

    if add_menu:
        app_entry.write_text(desktop_content, encoding="utf-8")
        os.chmod(app_entry, 0o755)
        print(f"✅ Linux app menu entry: {app_entry}")

    if add_desktop:
        desktop_entry.write_text(desktop_content, encoding="utf-8")
        os.chmod(desktop_entry, 0o755)
        print(f"✅ Linux desktop icon: {desktop_entry}")

    print(f"✅ Linux command launcher: {wrapper_path}")


WINDOWS_BAT = """@echo off
rem Launches AI Data Pipeline. Paths are relative to this file, so the folder can be moved.
setlocal
set "SCRIPT_DIR=%~dp0..\\.."
call "%SCRIPT_DIR%\\run_pipeline.bat" %*
endlocal
"""

WINDOWS_PS1 = """# Launches AI Data Pipeline. Paths are relative to this file, so the folder can be moved.
$ScriptDir = (Resolve-Path (Join-Path $PSScriptRoot '..\\..')).Path
& (Join-Path $ScriptDir 'run_pipeline.bat') @args
exit $LASTEXITCODE
"""


def write_windows_launchers(script_dir: Path) -> Path:
    launchers_dir = script_dir / "launchers" / "windows"
    launchers_dir.mkdir(parents=True, exist_ok=True)
    (launchers_dir / "AI-Data-Pipeline.bat").write_text(WINDOWS_BAT.replace("\n", "\r\n"), encoding="utf-8", newline="")
    (launchers_dir / "AI-Data-Pipeline.ps1").write_text(WINDOWS_PS1, encoding="utf-8")
    return launchers_dir


def install_windows(script_dir: Path, add_desktop: bool, add_menu: bool) -> None:
    """On Windows: full install (venv, dependencies, shortcuts). Elsewhere: only the launchers."""
    launchers_dir = write_windows_launchers(script_dir)
    ps1 = script_dir / "install_windows.ps1"

    if not sys.platform.startswith("win"):
        (launchers_dir / "INSTALL_WINDOWS_SHORTCUTS.md").write_text(
            "# Install on Windows\n\n"
            "Copy this folder to the Windows PC and double-click `Install-Windows.bat` in the\n"
            "repository root. It finds Python 3.10+, creates a virtual environment, installs the\n"
            "dependencies and adds Desktop and Start Menu shortcuts.\n\n"
            "Options (run from PowerShell in `backup_cleanup\\python_files`):\n\n"
            "```powershell\n"
            "powershell -ExecutionPolicy Bypass -File install_windows.ps1 -Minimal      # fewer dependencies\n"
            "powershell -ExecutionPolicy Bypass -File install_windows.ps1 -NoDesktop    # Start Menu only\n"
            "powershell -ExecutionPolicy Bypass -File install_windows.ps1 -Uninstall    # remove shortcuts\n"
            "```\n",
            encoding="utf-8",
        )
        print(f"✅ Windows launchers written: {launchers_dir}")
        print("ℹ️  Run Install-Windows.bat on the Windows PC to finish the install.")
        return

    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1)]
    if not add_desktop:
        cmd.append("-NoDesktop")
    if not add_menu:
        cmd.append("-NoStartMenu")
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        print("❌ Windows install did not finish; read the messages above.")
        raise SystemExit(result.returncode)


def install_ios_pack(script_dir: Path) -> None:
    """iOS cannot run the Tk app, so install the web remote: token, start scripts, guide."""
    ios_dir = script_dir / "launchers" / "ios"
    ios_dir.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(script_dir))
    import ios_remote_server

    ios_remote_server.load_or_create_token()      # creates ios_remote/.token (owner-only) once

    start_sh = ios_dir / "start_ios_remote.sh"
    start_sh.write_text(
        """#!/usr/bin/env bash
# Starts the iOS remote. Extra arguments go to ios_remote_server.py (e.g. --host 192.168.1.20).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY="$HERE/venv/bin/python"
[[ -x "$PY" ]] || PY=python3
exec "$PY" "$HERE/ios_remote_server.py" "$@"
""",
        encoding="utf-8",
    )
    os.chmod(start_sh, 0o755)

    (ios_dir / "start_ios_remote.bat").write_text(
        "@echo off\r\n"
        "rem Starts the iOS remote. Extra arguments go to ios_remote_server.py (e.g. --host 192.168.1.20).\r\n"
        "set \"HERE=%~dp0..\\..\"\r\n"
        "set \"PY=%HERE%\\venv\\Scripts\\python.exe\"\r\n"
        "if not exist \"%PY%\" set \"PY=python\"\r\n"
        "\"%PY%\" \"%HERE%\\ios_remote_server.py\" %*\r\n",
        encoding="utf-8", newline="",
    )

    (ios_dir / "ai-data-pipeline-remote.service").write_text(
        f"""# Optional: start the iOS remote at login (Linux).
#   mkdir -p ~/.config/systemd/user
#   cp ai-data-pipeline-remote.service ~/.config/systemd/user/
#   systemctl --user daemon-reload && systemctl --user enable --now ai-data-pipeline-remote
# Edit ExecStart to add --host <your Tailscale or LAN address> before enabling.
[Unit]
Description=AI Data Pipeline iOS remote

[Service]
WorkingDirectory={script_dir}
ExecStart={script_dir / "launchers" / "ios" / "start_ios_remote.sh"}
Restart=on-failure

[Install]
WantedBy=default.target
""",
        encoding="utf-8",
    )

    guide = ios_dir / "INSTALL_IOS_APP.md"
    guide.write_text(
        """# Install AI Data Pipeline on iPhone / iPad

iOS cannot run the desktop app, so this installs a **Home Screen app** that remotely controls the
computer running the pipeline: upload documents, start a run, watch the log, download the results.

## 1. Start the remote on the computer

```bash
# Linux / macOS
backup_cleanup/python_files/launchers/ios/start_ios_remote.sh --host <address>

# Windows
backup_cleanup\\python_files\\launchers\\ios\\start_ios_remote.bat --host <address>
```

Which `<address>`:

| Situation | Use |
|-----------|-----|
| Phone and computer both on **Tailscale** (recommended: encrypted, works anywhere) | leave `--host` off; the Tailscale address is picked automatically |
| Same home Wi-Fi, no Tailscale | the computer's LAN address, e.g. `--host 192.168.1.20` (plain HTTP: trusted network only) |
| Testing on the computer itself | nothing (binds to 127.0.0.1) |

It prints a link and a QR code.

## 2. Install on the iPhone

1. Scan the QR code with the Camera app (or open the link in **Safari**; it must be Safari).
2. Tap **Share** then **Add to Home Screen** then **Add**.

The icon on your Home Screen opens the app full-screen. The link carries your access token, so
the Home Screen icon stays signed in. Anyone with the link can use the remote: treat it like a password.

## What it does

- **Upload documents**: PDF, TXT, MD, CSV, JSON, JSONL (up to 100 MB each) into the pipeline's input folder.
- **Process input folder**: runs the same pipeline as `pipeline_cli.py process`.
- **Health check**: runs the operational health check.
- **Log** streams while a job runs; **Results** lists the output files with Download buttons.

## Security

- Every request needs the access token, and repeated wrong tokens lock the client out for a minute.
- The server can only run the two fixed commands above; uploads are restricted by file type and size
  and can never overwrite or escape the input folder; downloads only come from the output folder.
- Traffic is plain HTTP. Over Tailscale it is encrypted by the tunnel; on a LAN it is not.
  Never port-forward this to the internet.
- Reset the token (invalidates every installed icon):
  `python ios_remote_server.py --new-token --show-url`
- Show the link/QR again: `python ios_remote_server.py --show-url`

## Start at login (optional, Linux)

See the comments in `ai-data-pipeline-remote.service` next to this file.

## Alternative: SSH Shortcut

If you prefer no web app: in **Shortcuts**, add **Run Script Over SSH** with
`cd "/path/to/backup_cleanup/python_files" && ./run_pipeline.sh --health-only --smoke`.
""",
        encoding="utf-8",
    )
    print(f"✅ iOS remote installed: {ios_dir}")
    print("   Start it with launchers/ios/start_ios_remote.sh (or .bat), then scan the QR code on your iPhone.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Install app launchers")
    parser.add_argument(
        "--yes", action="store_true", help="Use defaults without prompts"
    )
    parser.add_argument(
        "--only",
        choices=["linux", "windows", "ios"],
        help="Install just one target instead of all",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent

    print("AI Data Pipeline App Installer")
    print("=" * 32)

    want = lambda target: args.only in (None, target)  # noqa: E731

    add_desktop = add_menu = add_ios = True
    if not args.yes:
        if want("linux") or want("windows"):
            add_desktop = ask_yes_no("Create desktop icon?", default=True)
            add_menu = ask_yes_no("Create app menu entry?", default=True)
        if want("ios"):
            add_ios = ask_yes_no("Install the iOS remote (Home Screen app)?", default=True)

    if want("linux"):
        if sys.platform.startswith("linux"):
            install_linux(script_dir, add_desktop=add_desktop, add_menu=add_menu)
        else:
            print("ℹ️ Linux launcher install skipped on non-Linux host")

    if want("windows"):
        install_windows(script_dir, add_desktop=add_desktop, add_menu=add_menu)

    if want("ios") and add_ios:
        install_ios_pack(script_dir)

    print("\n✅ App installer finished")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
