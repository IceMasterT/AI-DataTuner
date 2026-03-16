#!/usr/bin/env python3
"""
Setup script for AI Data Processing System
Installs all dependencies and sets up the environment.
"""

import subprocess
import sys
import os
import argparse
from pathlib import Path


def create_linux_launcher(script_dir: Path) -> bool:
    """Create Linux desktop launcher and command wrapper."""
    try:
        home = Path.home()
        local_bin = home / ".local" / "bin"
        applications_dir = home / ".local" / "share" / "applications"
        desktop_dir = home / "Desktop"

        local_bin.mkdir(parents=True, exist_ok=True)
        applications_dir.mkdir(parents=True, exist_ok=True)
        desktop_dir.mkdir(parents=True, exist_ok=True)

        launcher_name = "ai-data-pipeline-launcher"
        wrapper_path = local_bin / launcher_name
        run_script = script_dir / "run_pipeline.sh"
        venv_python = script_dir / "venv" / "bin" / "python"
        icon_path = script_dir / "assets" / "robot-head.svg"
        icon_value = str(icon_path) if icon_path.exists() else "applications-science"

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
Icon=applications-science
Terminal=false
Categories=Development;Utility;
StartupNotify=true
"""
        desktop_content = desktop_content.replace(
            "Icon=applications-science", f"Icon={icon_value}"
        )

        app_entry = applications_dir / "ai-data-pipeline.desktop"
        desktop_entry = desktop_dir / "AI Data Pipeline.desktop"
        app_entry.write_text(desktop_content, encoding="utf-8")
        desktop_entry.write_text(desktop_content, encoding="utf-8")
        os.chmod(app_entry, 0o755)
        os.chmod(desktop_entry, 0o755)

        print(f"✅ Linux desktop launcher created: {desktop_entry}")
        print(f"✅ Linux command launcher created: {wrapper_path}")
        return True
    except Exception as e:
        print(f"⚠️  Linux launcher setup skipped: {e}")
        return False


def create_windows_launchers(script_dir: Path) -> bool:
    """Create Windows launcher scripts/assets for easy startup."""
    try:
        launchers_dir = script_dir / "launchers" / "windows"
        launchers_dir.mkdir(parents=True, exist_ok=True)

        bat_path = launchers_dir / "AI-Data-Pipeline.bat"
        ps1_path = launchers_dir / "AI-Data-Pipeline.ps1"

        bat_content = f"""@echo off
setlocal
set SCRIPT_DIR={script_dir}
set PY_BIN=%SCRIPT_DIR%\\venv\\Scripts\\python.exe
if not exist "%PY_BIN%" set PY_BIN=python
set RUNNER=%SCRIPT_DIR%\\run_pipeline.bat
if exist "%RUNNER%" (
  call "%RUNNER%" %*
) else (
  "%PY_BIN%" "%SCRIPT_DIR%\\operational_health_check.py" --init-folders --smoke
  if errorlevel 1 exit /b 1
  "%PY_BIN%" "%SCRIPT_DIR%\\unified_pipeline_gui.py"
)
endlocal
"""
        bat_path.write_text(bat_content, encoding="utf-8")

        ps1_content = f"""$ScriptDir = "{script_dir}"
$PyBin = Join-Path $ScriptDir "venv\\Scripts\\python.exe"
if (-Not (Test-Path $PyBin)) {{ $PyBin = "python" }}
$Runner = Join-Path $ScriptDir "run_pipeline.bat"
if (Test-Path $Runner) {{
    & $Runner @args
}} else {{
    & $PyBin (Join-Path $ScriptDir "operational_health_check.py") --init-folders --smoke
    if ($LASTEXITCODE -ne 0) {{ exit $LASTEXITCODE }}
    & $PyBin (Join-Path $ScriptDir "unified_pipeline_gui.py")
}}
"""
        ps1_path.write_text(ps1_content, encoding="utf-8")

        print(f"✅ Windows launcher assets created: {launchers_dir}")
        return True
    except Exception as e:
        print(f"⚠️  Windows launcher generation skipped: {e}")
        return False


def create_ios_launcher_guide(script_dir: Path) -> bool:
    """Create iOS launcher guidance (remote trigger via Shortcuts)."""
    try:
        launchers_dir = script_dir / "launchers" / "ios"
        launchers_dir.mkdir(parents=True, exist_ok=True)

        guide_path = launchers_dir / "IOS_LAUNCHER_SETUP.md"
        guide_text = """# iOS Launcher Setup

iOS cannot run this Python desktop app natively. Use a one-tap Shortcut that remotely triggers your Linux/Windows host.

## Option A: SSH Shortcut (Recommended)

1. In iOS **Shortcuts**, create a new shortcut.
2. Add action: **Run Script Over SSH**.
3. Host: your machine running AI Data Pipeline.
4. Script:

```bash
cd "/path/to/backup_cleanup/python_files" && ./run_pipeline.sh --health-only --smoke
```

5. Add to Home Screen and name it `AI Data Pipeline`.

## Option B: Web Trigger

If you expose a secure internal endpoint that executes the launcher, create an iOS Home Screen web shortcut to that endpoint.

Security note: use VPN/Tailscale + key auth, never expose raw SSH publicly.
"""
        guide_path.write_text(guide_text, encoding="utf-8")
        print(f"✅ iOS launcher guide created: {guide_path}")
        return True
    except Exception as e:
        print(f"⚠️  iOS launcher guide generation skipped: {e}")
        return False


def create_platform_launchers(script_dir: Path, yes: bool = False):
    """Create launcher assets for Linux, Windows, and iOS."""
    installer = script_dir / "install_app.py"
    if installer.exists():
        cmd = [sys.executable, str(installer)]
        if yes:
            cmd.append("--yes")
        subprocess.run(cmd, check=False)
        return

    create_linux_launcher(script_dir)
    create_windows_launchers(script_dir)
    create_ios_launcher_guide(script_dir)


def run_command(command, description):
    """Run a command and handle errors."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(
            command, shell=True, check=True, capture_output=True, text=True
        )
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Error: {e.stderr}")
        return False


def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(
            f"❌ Python 3.8+ required. Current version: {version.major}.{version.minor}"
        )
        return False
    print(
        f"✅ Python version {version.major}.{version.minor}.{version.micro} is compatible"
    )
    return True


def setup_environment(
    install_type: str = "minimal", yes: bool = False, desktop_icon: bool = True
):
    """Set up the AI data processing environment."""
    script_dir = Path(__file__).resolve().parent

    print("🚀 AI DATA PROCESSING SYSTEM SETUP")
    print("=" * 50)

    # Check Python version
    if not check_python_version():
        return False

    # Check if virtual environment is active
    if not hasattr(sys, "real_prefix") and not (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    ):
        print(
            "⚠️  Virtual environment not detected. It's recommended to use a virtual environment."
        )
        if not yes:
            response = input("Continue anyway? (y/N): ")
            if response.lower() != "y":
                print(
                    "Setup cancelled. Please activate your virtual environment and try again."
                )
                return False
    else:
        print("✅ Virtual environment detected")

    # Upgrade pip
    if not run_command(
        f'"{sys.executable}" -m pip install --upgrade pip', "Upgrading pip"
    ):
        return False

    # Resolve requirements files
    minimal_req = script_dir / "requirements-minimal.txt"
    full_req = script_dir / "requirements.txt"

    requirements_file = minimal_req if install_type == "minimal" else full_req
    description = (
        "Installing minimal dependencies"
        if install_type == "minimal"
        else "Installing full dependencies"
    )

    if not requirements_file.exists():
        print(f"❌ {requirements_file.name} not found")
        return False

    if not run_command(
        f'"{sys.executable}" -m pip install -r "{requirements_file}"', description
    ):
        return False

    # Download NLTK data
    print("\n📚 Setting up NLTK data...")
    try:
        import nltk

        nltk.download("punkt", quiet=True)
        nltk.download("stopwords", quiet=True)
        nltk.download("wordnet", quiet=True)
        print("✅ NLTK data downloaded successfully")
    except Exception as e:
        print(f"⚠️  NLTK data download failed: {e}")

    # Create necessary directories
    print("\n📁 Creating directory structure...")
    directories = [
        "input",
        "filtered",
        "output",
        "errors",
        "archive",
        "logs",
        "cache",
        "quarantine",
        "audit_logs",
    ]

    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created directory: {directory}")

    # Check .env file
    local_env = script_dir / ".env"
    project_env = script_dir.parents[1] / ".env"
    if local_env.exists() or project_env.exists():
        found_env = local_env if local_env.exists() else project_env
        print(f"✅ .env file found: {found_env}")
    else:
        print("⚠️  .env file not found. Please create one with your provider settings.")

    # Test imports
    print("\n🧪 Testing critical imports...")
    critical_imports = [
        "openai",
        "yaml",
        "nltk",
        "PyPDF2",
        "pdfplumber",
        "pathlib",
        "json",
        "logging",
    ]

    failed_imports = []
    for module in critical_imports:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module}")
            failed_imports.append(module)

    if failed_imports:
        print(f"\n❌ Failed to import: {', '.join(failed_imports)}")
        print("Please check the installation and try again.")
        return False

    if desktop_icon:
        print("\n🖥️  Creating launcher assets (Linux/Windows/iOS)...")
        create_platform_launchers(script_dir, yes=yes)

    print("\n🎉 SETUP COMPLETED SUCCESSFULLY!")
    print("=" * 50)
    print("✅ All dependencies installed")
    print("✅ Directory structure created")
    print("✅ Critical imports verified")
    print("\n🚀 You can now run the AI data processing system!")
    print("\nNext steps:")
    print("1. Verify your .env file has the correct API keys")
    print("2. Run: python unified_pipeline_gui.py")
    print("3. Or run: python ten_pillars_integration.py")

    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Setup AI Data Processing environment")
    parser.add_argument(
        "--install-type",
        choices=["minimal", "full"],
        default="minimal",
        help="dependency profile to install",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="run non-interactively and continue without venv prompt",
    )
    parser.add_argument(
        "--no-desktop-icon",
        action="store_true",
        help="skip desktop/icon launcher creation",
    )
    args = parser.parse_args()

    success = setup_environment(
        install_type=args.install_type,
        yes=args.yes,
        desktop_icon=not args.no_desktop_icon,
    )
    sys.exit(0 if success else 1)
