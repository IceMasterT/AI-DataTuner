<#
.SYNOPSIS
    Installs AI Data Pipeline on Windows: Python check, virtual environment,
    dependencies, Desktop and Start Menu shortcuts.

.DESCRIPTION
    Run it by double-clicking Install-Windows.bat in the repository root, or:
        powershell -ExecutionPolicy Bypass -File install_windows.ps1

    Nothing is installed system-wide. Dependencies go into a venv next to this
    script; shortcuts go to the current user's Desktop and Start Menu.

.PARAMETER NoDesktop      Skip the Desktop shortcut.
.PARAMETER NoStartMenu    Skip the Start Menu shortcut.
.PARAMETER Full           Install requirements.txt (PDF structure extraction, etc.).
                          Default. Use -Minimal for requirements-minimal.txt only.
.PARAMETER Minimal        Install only requirements-minimal.txt.
.PARAMETER PythonPath     Use this Python instead of auto-detecting one.
.PARAMETER Uninstall      Remove the shortcuts (and with -RemoveVenv, the venv).
.PARAMETER RemoveVenv     With -Uninstall, also delete the virtual environment.
.PARAMETER DryRun         Print what would happen; change nothing.
#>
[CmdletBinding()]
param(
    [switch]$NoDesktop,
    [switch]$NoStartMenu,
    [switch]$Minimal,
    [string]$PythonPath,
    [switch]$Uninstall,
    [switch]$RemoveVenv,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

$AppName   = 'AI Data Pipeline'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir   = Join-Path $ScriptDir 'venv'
$VenvPy    = Join-Path $VenvDir 'Scripts\python.exe'
$Runner    = Join-Path $ScriptDir 'run_pipeline.bat'
$IconPath  = Join-Path $ScriptDir 'assets\app.ico'
$MinPython = [version]'3.10'

function Write-Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    OK  $msg" -ForegroundColor Green }
function Write-Warn2($msg){ Write-Host "    !!  $msg" -ForegroundColor Yellow }

function Get-ShortcutPaths {
    $desktop  = [Environment]::GetFolderPath('Desktop')
    $programs = [Environment]::GetFolderPath('Programs')
    if (-not $programs -and $env:APPDATA) {
        $programs = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
    }
    $paths = @{}
    if ($desktop)  { $paths.Desktop   = Join-Path $desktop  "$AppName.lnk" }
    if ($programs) { $paths.StartMenu = Join-Path $programs "$AppName.lnk" }
    return $paths
}

# --- Uninstall ---------------------------------------------------------------
if ($Uninstall) {
    Write-Step "Removing $AppName shortcuts"
    foreach ($p in (Get-ShortcutPaths).Values) {
        if (Test-Path $p) {
            if ($DryRun) { Write-Host "    would remove $p" } else { Remove-Item $p -Force; Write-Ok "removed $p" }
        }
    }
    if ($RemoveVenv -and (Test-Path $VenvDir)) {
        if ($DryRun) { Write-Host "    would remove $VenvDir" }
        else { Remove-Item $VenvDir -Recurse -Force; Write-Ok "removed $VenvDir" }
    }
    Write-Host "Your input/output folders and settings were not touched."
    exit 0
}

# --- Find Python -------------------------------------------------------------
function Test-PythonCandidate([string]$exe, [string[]]$prefixArgs) {
    # Returns the resolved python.exe path if it runs and is >= $MinPython, else $null.
    try {
        $out = & $exe @prefixArgs -c "import sys; print(sys.executable); print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $out -or @($out).Count -lt 2) { return $null }
        $lines = @($out)
        if ([version]$lines[1] -ge $MinPython) { return $lines[0] }
    } catch { }
    return $null
}

function Find-Python {
    if ($PythonPath) {
        $found = Test-PythonCandidate $PythonPath @()
        if ($found) { return $found }
        throw "The Python given with -PythonPath ($PythonPath) is missing or older than $MinPython."
    }
    # The 'py' launcher is the reliable way on Windows; plain 'python' may be the Store stub.
    foreach ($cand in @(@('py', @('-3')), @('python', @()), @('python3', @()))) {
        if (Get-Command $cand[0] -ErrorAction SilentlyContinue) {
            $found = Test-PythonCandidate $cand[0] $cand[1]
            if ($found) { return $found }
        }
    }
    return $null
}

Write-Step "Looking for Python $MinPython or newer"
$Python = Find-Python
if (-not $Python) {
    Write-Warn2 "Python $MinPython+ was not found."
    Write-Host  "    Install it from https://www.python.org/downloads/ (tick 'Add python.exe to PATH'),"
    Write-Host  "    or run:  winget install Python.Python.3.12"
    Write-Host  "    then run this installer again."
    exit 1
}
Write-Ok $Python

if (-not (Test-Path $Runner)) { throw "run_pipeline.bat not found next to this script ($ScriptDir)." }

# --- Virtual environment + dependencies -------------------------------------
$req = if ($Minimal) { 'requirements-minimal.txt' } else { 'requirements.txt' }
Write-Step "Setting up the virtual environment ($req)"
if ($DryRun) {
    Write-Host "    would run: $Python -m venv `"$VenvDir`""
    Write-Host "    would run: $VenvPy -m pip install -r $req"
} else {
    if (-not (Test-Path $VenvPy)) {
        & $Python -m venv $VenvDir
        if ($LASTEXITCODE -ne 0) { throw "Creating the virtual environment failed." }
    }
    & $VenvPy -m pip install --upgrade pip --quiet
    & $VenvPy -m pip install -r (Join-Path $ScriptDir $req)
    if ($LASTEXITCODE -ne 0) { throw "Installing dependencies from $req failed." }
    & $VenvPy -c "import tkinter" 2>$null
    if ($LASTEXITCODE -ne 0) {
        throw "This Python has no Tkinter (needed for the GUI). Re-run the python.org installer, choose Modify, and tick 'tcl/tk and IDLE'."
    }
    Write-Ok "dependencies installed"
}

# --- Shortcuts ---------------------------------------------------------------
function New-AppShortcut([string]$path) {
    $shell = New-Object -ComObject WScript.Shell
    $lnk = $shell.CreateShortcut($path)
    $lnk.TargetPath       = $Runner
    $lnk.WorkingDirectory = $ScriptDir
    $lnk.WindowStyle      = 7          # minimized: the GUI is the window, not the console
    $lnk.Description      = "$AppName"
    if (Test-Path $IconPath) { $lnk.IconLocation = "$IconPath,0" }
    $lnk.Save()
}

Write-Step "Creating shortcuts"
$paths = Get-ShortcutPaths
$wanted = @()
if (-not $NoDesktop)   { if ($paths.Desktop)   { $wanted += $paths.Desktop }   else { Write-Warn2 'No Desktop folder found; skipping the Desktop shortcut.' } }
if (-not $NoStartMenu) { if ($paths.StartMenu) { $wanted += $paths.StartMenu } else { Write-Warn2 'No Start Menu folder found; skipping the Start Menu shortcut.' } }
foreach ($p in $wanted) {
    if ($DryRun) { Write-Host "    would create $p -> $Runner" }
    else { New-AppShortcut $p; Write-Ok $p }
}

Write-Host ""
if ($DryRun) { Write-Host "Dry run finished; nothing was changed." -ForegroundColor Yellow; exit 0 }
Write-Host "$AppName is installed." -ForegroundColor Green
Write-Host "Start it from the Desktop icon / Start Menu, or run: run_pipeline.bat"
Write-Host "To remove the shortcuts: powershell -ExecutionPolicy Bypass -File install_windows.ps1 -Uninstall"
