$ScriptDir = "/media/artiq/DATA/AI Data Pipeline/backup_cleanup/python_files"
$PyBin = Join-Path $ScriptDir "venv\Scripts\python.exe"
if (-Not (Test-Path $PyBin)) { $PyBin = "python" }
$Runner = Join-Path $ScriptDir "run_pipeline.bat"
if (Test-Path $Runner) {
    & $Runner @args
} else {
    & $PyBin (Join-Path $ScriptDir "operational_health_check.py") --init-folders --smoke
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & $PyBin (Join-Path $ScriptDir "unified_pipeline_gui.py")
}
