@echo off
rem Double-click to install AI Data Pipeline on Windows.
rem Runs install_windows.ps1 with a one-time execution-policy bypass for that
rem process only; your system PowerShell policy is not changed.
setlocal
set "HERE=%~dp0"
set "PS1=%HERE%backup_cleanup\python_files\install_windows.ps1"
if not exist "%PS1%" (
  echo Could not find %PS1%
  echo Run this file from the root of the AI-DataTuner folder.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" %*
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" echo Installation did not finish (exit code %RC%). Read the messages above.
pause
exit /b %RC%
