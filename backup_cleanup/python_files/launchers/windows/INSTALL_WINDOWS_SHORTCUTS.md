# Install on Windows

Copy this folder to the Windows PC and double-click `Install-Windows.bat` in the
repository root. It finds Python 3.10+, creates a virtual environment, installs the
dependencies and adds Desktop and Start Menu shortcuts.

Options (run from PowerShell in `backup_cleanup\python_files`):

```powershell
powershell -ExecutionPolicy Bypass -File install_windows.ps1 -Minimal      # fewer dependencies
powershell -ExecutionPolicy Bypass -File install_windows.ps1 -NoDesktop    # Start Menu only
powershell -ExecutionPolicy Bypass -File install_windows.ps1 -Uninstall    # remove shortcuts
```
