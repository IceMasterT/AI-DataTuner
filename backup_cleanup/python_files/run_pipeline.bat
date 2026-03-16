@echo off
setlocal ENABLEDELAYEDEXPANSION

set SCRIPT_DIR=%~dp0
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%
set PY_BIN=%PYTHON_BIN%
if "%PY_BIN%"=="" set PY_BIN=%SCRIPT_DIR%\venv\Scripts\python.exe
if not exist "%PY_BIN%" set PY_BIN=python

set RUN_SETUP=0
set INSTALL_TYPE=minimal
set RUN_SMOKE=0
set HEALTH_ONLY=0
set RUN_GUI=1
set STRICT_HEALTH=0

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="--setup" (
  set RUN_SETUP=1
  if not "%~2"=="" (
    if /I not "%~2"=="--smoke" if /I not "%~2"=="--health-only" if /I not "%~2"=="--strict" if /I not "%~2"=="--no-gui" if /I not "%~2"=="--help" if /I not "%~2"=="-h" (
      set INSTALL_TYPE=%~2
      shift
    )
  )
) else if /I "%~1"=="--smoke" (
  set RUN_SMOKE=1
) else if /I "%~1"=="--health-only" (
  set HEALTH_ONLY=1
  set RUN_GUI=0
) else if /I "%~1"=="--strict" (
  set STRICT_HEALTH=1
) else if /I "%~1"=="--no-gui" (
  set RUN_GUI=0
) else if /I "%~1"=="--python" (
  if not "%~2"=="" (
    set PY_BIN=%~2
    shift
  )
) else if /I "%~1"=="--help" (
  goto usage
) else if /I "%~1"=="-h" (
  goto usage
) else (
  echo Unknown option: %~1
  goto usage
)
shift
goto parse_args

:args_done
echo [INFO] Using Python: %PY_BIN%

if %RUN_SETUP%==1 (
  echo [INFO] Running setup (--install-type %INSTALL_TYPE%)
  "%PY_BIN%" "%SCRIPT_DIR%\setup.py" --install-type %INSTALL_TYPE% --yes
  if errorlevel 1 exit /b 1
)

echo [INFO] Running operational health checks
set HEALTH_ARGS=--init-folders
if %RUN_SMOKE%==1 set HEALTH_ARGS=%HEALTH_ARGS% --smoke
if %STRICT_HEALTH%==1 set HEALTH_ARGS=%HEALTH_ARGS% --strict
"%PY_BIN%" "%SCRIPT_DIR%\operational_health_check.py" %HEALTH_ARGS%
if errorlevel 1 exit /b 1

if %HEALTH_ONLY%==1 goto done
if %RUN_GUI%==0 goto done

echo [INFO] Launching unified pipeline GUI
"%PY_BIN%" "%SCRIPT_DIR%\unified_pipeline_gui.py"
if errorlevel 1 exit /b 1

:done
echo [INFO] Done
exit /b 0

:usage
echo AI Data Pipeline Launcher (Windows)
echo Usage: run_pipeline.bat [options]
echo   --setup [minimal^|full]   Install dependencies before checks
echo   --smoke                    Run synthetic smoke checks
echo   --health-only              Run checks and exit
echo   --strict                   Fail on missing creds/deps
echo   --no-gui                   Skip GUI launch
echo   --python PATH              Python executable override
echo   -h, --help                 Show help
exit /b 2
