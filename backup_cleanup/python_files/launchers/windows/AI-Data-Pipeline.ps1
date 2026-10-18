# Launches AI Data Pipeline. Paths are relative to this file, so the folder can be moved.
$ScriptDir = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
& (Join-Path $ScriptDir 'run_pipeline.bat') @args
exit $LASTEXITCODE
