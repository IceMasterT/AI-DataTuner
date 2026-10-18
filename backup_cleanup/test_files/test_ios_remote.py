#!/usr/bin/env python3
"""Tests for the iOS remote server (auth, upload/download safety, job runner)."""

import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "python_files"))

import ios_remote_server as srv

TOKEN = "test-token-0123456789"


class ServerCase(unittest.TestCase):
    """Starts the real HTTP server on an ephemeral port with temp folders."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.input_dir, self.output_dir = root / "input", root / "output"
        self.output_dir.mkdir()
        py = sys.executable
        self.runner = srv.JobRunner(
            commands={
                "health": [py, "-c", "print('health ok')"],
                "process": [py, "-c", "import time; print('working', flush=True); time.sleep(30)"],
            },
            cwd=root, log_path=root / "logs" / "job.log")
        self.app = srv.RemoteApp(TOKEN, self.input_dir, self.output_dir, self.runner)
        self.httpd = srv.build_server("127.0.0.1", 0, self.app)
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def tearDown(self):
        self.runner.cancel()
        self.httpd.shutdown()
        self.httpd.server_close()
        self.tmp.cleanup()

    def call(self, method, path, body=None, token=TOKEN, headers=None):
        req = urllib.request.Request(self.base + path, data=body, method=method)
        if token:
            req.add_header("Authorization", "Bearer " + token)
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read(), dict(e.headers)

    def wait_idle(self, timeout=10):
        end = time.time() + timeout
        while self.runner.running() and time.time() < end:
            time.sleep(0.05)
        time.sleep(0.1)


class TestAuth(ServerCase):

    def test_static_shell_is_public_but_api_is_not(self):
        self.assertEqual(self.call("GET", "/", token=None)[0], 200)
        self.assertEqual(self.call("GET", "/manifest.webmanifest", token=None)[0], 200)
        self.assertEqual(self.call("GET", "/apple-touch-icon.png", token=None)[0], 200)
        self.assertEqual(self.call("GET", "/api/status", token=None)[0], 401)
        self.assertEqual(self.call("POST", "/api/process", token=None)[0], 401)

    def test_wrong_token_rejected_and_right_token_accepted(self):
        self.assertEqual(self.call("GET", "/api/status", token="nope")[0], 401)
        self.assertEqual(self.call("GET", "/api/status")[0], 200)

    def test_token_in_query_string_is_not_accepted_by_the_api(self):
        self.assertEqual(self.call("GET", f"/api/status?t={TOKEN}", token=None)[0], 401)

    def test_repeated_failures_lock_the_client_out(self):
        for _ in range(srv.AUTH_FAIL_LIMIT):
            self.call("GET", "/api/status", token="bad")
        status, _, _ = self.call("GET", "/api/status")        # even the right token is refused now
        self.assertEqual(status, 429)

    def test_security_headers(self):
        _, _, headers = self.call("GET", "/", token=None)
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["Referrer-Policy"], "no-referrer")
        self.assertEqual(headers["Cache-Control"], "no-store")


class TestUpload(ServerCase):

    def upload(self, name, data=b"hello"):
        return self.call("POST", "/api/upload?name=" + urllib.request.quote(name), data,
                         headers={"Content-Type": "application/octet-stream"})

    def test_upload_saves_into_input_folder(self):
        status, body, _ = self.upload("notes.txt", b"some text")
        self.assertEqual(status, 201)
        self.assertEqual((self.input_dir / "notes.txt").read_bytes(), b"some text")
        self.assertEqual(json.loads(body)["saved"], "notes.txt")

    def test_existing_files_are_never_overwritten(self):
        self.upload("a.pdf", b"first")
        status, body, _ = self.upload("a.pdf", b"second")
        self.assertEqual(status, 201)
        self.assertEqual((self.input_dir / "a.pdf").read_bytes(), b"first")
        self.assertEqual((self.input_dir / "a (1).pdf").read_bytes(), b"second")

    def test_path_traversal_names_are_flattened(self):
        status, body, _ = self.upload("../../etc/evil.txt")
        self.assertEqual(status, 201)
        self.assertEqual(json.loads(body)["saved"], "evil.txt")
        self.assertTrue((self.input_dir / "evil.txt").exists())
        self.assertFalse((Path(self.tmp.name).parent / "evil.txt").exists())

    def test_disallowed_extension_and_hidden_names_rejected(self):
        for bad in ("run.sh", "x.exe", "noext", ".hidden.txt", ""):
            self.assertEqual(self.upload(bad)[0], 400, bad)
        self.assertEqual(list(self.input_dir.glob("*")) if self.input_dir.exists() else [], [])

    def test_empty_and_oversized_uploads_rejected(self):
        self.assertEqual(self.upload("empty.txt", b"")[0], 400)
        original = srv.MAX_UPLOAD_BYTES
        srv.MAX_UPLOAD_BYTES = 10
        try:
            self.assertEqual(self.upload("big.txt", b"x" * 11)[0], 413)
        finally:
            srv.MAX_UPLOAD_BYTES = original
        self.assertFalse((self.input_dir / "big.txt").exists())

    def test_name_sanitiser(self):
        self.assertEqual(srv.safe_upload_name("My Report (v2).PDF"), "My Report (v2).PDF")
        self.assertEqual(srv.safe_upload_name("a/b\\c.txt"), "c.txt")
        self.assertEqual(srv.safe_upload_name("we<ir>d?.md"), "we_ir_d_.md")
        self.assertIsNone(srv.safe_upload_name("script.py"))


class TestDownloads(ServerCase):

    def test_download_returns_output_files_only(self):
        (self.output_dir / "doc").mkdir()
        (self.output_dir / "doc" / "doc_chunks.jsonl").write_text('{"a":1}\n')
        (self.input_dir.parent / "secret.txt").write_text("secret")
        status, body, headers = self.call("GET", "/api/download?path=doc/doc_chunks.jsonl")
        self.assertEqual(status, 200)
        self.assertEqual(body, b'{"a":1}\n')
        self.assertIn("attachment", headers["Content-Disposition"])
        for attack in ("../secret.txt", "..%2Fsecret.txt", "/etc/passwd", "doc", "missing.txt"):
            self.assertEqual(self.call("GET", "/api/download?path=" + attack)[0], 404, attack)

    def test_outputs_listing(self):
        (self.output_dir / "x.txt").write_text("hi")
        status, body, _ = self.call("GET", "/api/outputs")
        self.assertEqual(status, 200)
        self.assertEqual([f["path"] for f in json.loads(body)["files"]], ["x.txt"])


class TestJobs(ServerCase):

    def test_health_job_runs_and_logs(self):
        self.assertEqual(self.call("POST", "/api/health")[0], 202)
        self.wait_idle()
        status, body, _ = self.call("GET", "/api/status")
        info = json.loads(body)
        self.assertIsNone(info["running"])
        self.assertEqual(info["last_job"]["name"], "health")
        self.assertEqual(info["last_job"]["exit_code"], 0)
        self.assertIn("health ok", self.call("GET", "/api/log")[1].decode())

    def test_only_one_job_at_a_time_and_cancel(self):
        self.assertEqual(self.call("POST", "/api/process")[0], 202)
        time.sleep(0.3)
        self.assertEqual(self.call("POST", "/api/health")[0], 409)
        self.assertEqual(json.loads(self.call("GET", "/api/status")[1])["running"], "process")
        self.assertTrue(json.loads(self.call("POST", "/api/cancel")[1])["cancelled"])
        self.wait_idle()
        self.assertIsNone(json.loads(self.call("GET", "/api/status")[1])["running"])
        self.assertNotEqual(json.loads(self.call("GET", "/api/status")[1])["last_job"]["exit_code"], 0)

    def test_unknown_routes_404_and_requests_cannot_choose_commands(self):
        self.assertEqual(self.call("POST", "/api/run?cmd=ls")[0], 404)
        self.assertEqual(self.call("POST", "/api/process?cmd=ls")[0], 202)   # query is ignored
        self.assertEqual(self.runner.commands["process"][1], "-c")


class TestToken(unittest.TestCase):

    def test_token_file_is_created_private_and_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sub" / ".token"
            t1 = srv.load_or_create_token(path)
            self.assertGreaterEqual(len(t1), 24)
            self.assertEqual(srv.load_or_create_token(path), t1)
            if os.name == "posix":
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            t2 = srv.regenerate_token(path)
            self.assertNotEqual(t1, t2)


if __name__ == "__main__":
    unittest.main()
