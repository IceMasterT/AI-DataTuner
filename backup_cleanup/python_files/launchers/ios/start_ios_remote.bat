@echo off
rem Starts the iOS remote. Extra arguments go to ios_remote_server.py (e.g. --host 192.168.1.20).
set "HERE=%~dp0..\.."
set "PY=%HERE%\venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" "%HERE%\ios_remote_server.py" %*
