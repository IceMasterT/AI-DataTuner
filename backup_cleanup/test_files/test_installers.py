#!/usr/bin/env python3
"""Tests for the Windows and iOS installers (what can be verified on any host)."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PY_DIR = Path(__file__).parent.parent / "python_files"
sys.path.insert(0, str(PY_DIR))

import install_app
import setup as project_setup


class TestWindowsLaunchers(unittest.TestCase):

    def test_launchers_are_relative_and_crlf(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = install_app.write_windows_launchers(Path(tmp))
            bat = (d / "AI-Data-Pipeline.bat").read_bytes()
            ps1 = (d / "AI-Data-Pipeline.ps1").read_text()
            self.assertIn(b"%~dp0", bat)
            self.assertIn(b"\r\n", bat)
            self.assertNotIn(b"\n", bat.replace(b"\r\n", b""))     # no bare LFs: cmd.exe needs CRLF
            self.assertIn("$PSScriptRoot", ps1)
            for text in (bat.decode(), ps1):
                self.assertNotIn(tmp, text)                         # no baked-in machine path
                self.assertNotIn("/home/", text)
                self.assertNotIn("/media/", text)

    def test_setup_py_fallback_generator_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(project_setup.create_windows_launchers(Path(tmp)))
            bat = (Path(tmp) / "launchers" / "windows" / "AI-Data-Pipeline.bat").read_bytes()
            self.assertIn(b"%~dp0", bat)
            self.assertNotIn(tmp.encode(), bat)

    def test_committed_launchers_have_no_machine_paths(self):
        for name in ("AI-Data-Pipeline.bat", "AI-Data-Pipeline.ps1"):
            text = (PY_DIR / "launchers" / "windows" / name).read_text()
            self.assertNotIn("/home/", text, name)
            self.assertNotIn("/media/", text, name)

    def test_icon_is_a_real_multi_size_ico(self):
        from PIL import Image
        ico = Image.open(PY_DIR / "assets" / "app.ico")
        self.assertEqual(ico.format, "ICO")
        self.assertIn((256, 256), ico.info["sizes"])
        self.assertIn((16, 16), ico.info["sizes"])


@unittest.skipUnless(shutil.which("pwsh"), "PowerShell (pwsh) not installed")
class TestWindowsInstallerScript(unittest.TestCase):

    ps1 = PY_DIR / "install_windows.ps1"

    def run_ps(self, *args):
        return subprocess.run(["pwsh", "-NoProfile", "-File", str(self.ps1), *args],
                              capture_output=True, text=True, timeout=120)

    def test_script_parses(self):
        cmd = ("$e=$null;$t=$null;[void][System.Management.Automation.Language.Parser]::ParseFile("
               f"'{self.ps1}',[ref]$t,[ref]$e); if($e){{$e|%{{$_.Message}};exit 1}}")
        r = subprocess.run(["pwsh", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_dry_run_changes_nothing_and_reports_the_plan(self):
        venv = PY_DIR / "venv"
        existed = venv.exists()
        r = self.run_ps("-DryRun", "-PythonPath", sys.executable)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("would run", r.stdout)
        self.assertIn("Dry run finished", r.stdout)
        self.assertEqual(venv.exists(), existed)

    def test_rejects_a_python_that_does_not_run(self):
        r = self.run_ps("-DryRun", "-PythonPath", "/nonexistent/python")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("/nonexistent/python", r.stdout + r.stderr)

    def test_uninstall_dry_run(self):
        r = self.run_ps("-Uninstall", "-DryRun")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("not touched", r.stdout)

    def test_root_batch_wrapper_points_at_the_script(self):
        bat = (PY_DIR.parent.parent / "Install-Windows.bat").read_text()
        self.assertIn(r"backup_cleanup\python_files\install_windows.ps1", bat)
        self.assertIn("-ExecutionPolicy Bypass", bat)


class TestIosPack(unittest.TestCase):

    def test_pack_is_generated_without_leaking_the_token(self):
        import ios_remote_server
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "ios_remote").mkdir()
            install_app.install_ios_pack(tmp_path)
            ios = tmp_path / "launchers" / "ios"
            for name in ("INSTALL_IOS_APP.md", "start_ios_remote.sh", "start_ios_remote.bat",
                         "ai-data-pipeline-remote.service"):
                self.assertTrue((ios / name).exists(), name)
            self.assertTrue(os.access(ios / "start_ios_remote.sh", os.X_OK))
            token = ios_remote_server.load_or_create_token()
            for f in ios.iterdir():
                self.assertNotIn(token, f.read_text(), f.name)
            self.assertIn(b"\r\n", (ios / "start_ios_remote.bat").read_bytes())

    def test_web_app_assets_exist_and_are_wired(self):
        web = PY_DIR / "ios_remote"
        html = (web / "index.html").read_text()
        for needle in ("apple-mobile-web-app-capable", 'rel="apple-touch-icon"', 'rel="manifest"', "viewport-fit=cover"):
            self.assertIn(needle, html)
        self.assertNotIn("innerHTML", html)           # file names are user-controlled; text nodes only
        self.assertNotIn("<script src=", html)        # no third-party scripts
        from PIL import Image
        self.assertEqual(Image.open(web / "apple-touch-icon.png").size, (180, 180))
        self.assertEqual(Image.open(web / "icon-512.png").size, (512, 512))


if __name__ == "__main__":
    unittest.main()
