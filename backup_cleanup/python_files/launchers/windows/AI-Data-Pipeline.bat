@echo off
set SCRIPT_DIR=/media/artiq/DATA/AI Data Pipeline/backup_cleanup/python_files
set PY_BIN=%SCRIPT_DIR%\venv\Scripts\python.exe
if not exist "%PY_BIN%" set PY_BIN=python
"%PY_BIN%" "%SCRIPT_DIR%\run_pipeline.bat"
