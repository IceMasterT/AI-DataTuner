@echo off
rem Launches AI Data Pipeline. Paths are relative to this file, so the folder can be moved.
setlocal
set "SCRIPT_DIR=%~dp0..\.."
call "%SCRIPT_DIR%\run_pipeline.bat" %*
endlocal
