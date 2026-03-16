#!/usr/bin/env python3
"""Interactive app launcher installer for Linux/Windows/iOS workflows."""

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


def install_windows(script_dir: Path, add_desktop: bool, add_menu: bool) -> None:
    launchers_dir = script_dir / "launchers" / "windows"
    launchers_dir.mkdir(parents=True, exist_ok=True)

    bat_path = launchers_dir / "AI-Data-Pipeline.bat"
    bat_path.write_text(
        f"""@echo off
set SCRIPT_DIR={script_dir}
set PY_BIN=%SCRIPT_DIR%\\venv\\Scripts\\python.exe
if not exist "%PY_BIN%" set PY_BIN=python
"%PY_BIN%" "%SCRIPT_DIR%\\run_pipeline.bat"
""",
        encoding="utf-8",
    )

    if not sys.platform.startswith("win"):
        guide = launchers_dir / "INSTALL_WINDOWS_SHORTCUTS.md"
        guide.write_text(
            "Run `install_app.py` on Windows to create Desktop/Start Menu shortcuts automatically.\n",
            encoding="utf-8",
        )
        print(f"✅ Windows launcher assets generated: {launchers_dir}")
        return

    desktop_flag = "$true" if add_desktop else "$false"
    menu_flag = "$true" if add_menu else "$false"
    powershell_script = f"""
$W = New-Object -ComObject WScript.Shell
$Target = "{script_dir / "run_pipeline.bat"}"
$Icon = "{script_dir / "assets" / "robot-head.svg"}"
$DesktopPath = [Environment]::GetFolderPath('Desktop')
$StartMenuPath = Join-Path $env:APPDATA 'Microsoft\\Windows\\Start Menu\\Programs'
if ({desktop_flag}) {{
  $S = $W.CreateShortcut((Join-Path $DesktopPath 'AI Data Pipeline.lnk'))
  $S.TargetPath = $Target
  $S.Save()
}}
if ({menu_flag}) {{
  $S = $W.CreateShortcut((Join-Path $StartMenuPath 'AI Data Pipeline.lnk'))
  $S.TargetPath = $Target
  $S.Save()
}}
"""
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", powershell_script], check=False
    )
    print("✅ Windows shortcuts installed")


def install_ios_pack(script_dir: Path) -> None:
    ios_dir = script_dir / "launchers" / "ios"
    ios_dir.mkdir(parents=True, exist_ok=True)
    guide = ios_dir / "INSTALL_IOS_APP.md"
    guide.write_text(
        """# Install AI Data Pipeline on iOS (Shortcut App)

iOS cannot run this Python desktop app natively. Use a one-tap iOS Shortcut to trigger your host machine.

1. Open iOS Shortcuts.
2. Add action: Run Script Over SSH.
3. Host: your Linux/Windows machine.
4. Script:

```bash
cd \"/path/to/backup_cleanup/python_files\" && ./go_live.sh --check-only
```

5. Add shortcut to Home Screen and choose icon/name.

You now have an app-like launcher on iOS.
""",
        encoding="utf-8",
    )
    print(f"✅ iOS install pack created: {guide}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Install app launchers")
    parser.add_argument(
        "--yes", action="store_true", help="Use defaults without prompts"
    )
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent

    print("AI Data Pipeline App Installer")
    print("=" * 32)

    if args.yes:
        add_desktop = True
        add_menu = True
        add_ios = True
    else:
        add_desktop = ask_yes_no("Create desktop icon?", default=True)
        add_menu = ask_yes_no("Create app menu entry?", default=True)
        add_ios = ask_yes_no("Create iOS Shortcut install pack?", default=True)

    if sys.platform.startswith("linux"):
        install_linux(script_dir, add_desktop=add_desktop, add_menu=add_menu)
    else:
        print("ℹ️ Linux launcher install skipped on non-Linux host")

    install_windows(script_dir, add_desktop=add_desktop, add_menu=add_menu)

    if add_ios:
        install_ios_pack(script_dir)

    print("\n✅ App installer finished")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
