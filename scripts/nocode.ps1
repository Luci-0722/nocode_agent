param([Parameter(ValueFromRemainingArguments)] $ExtraArgs)

$ErrorActionPreference = 'Stop'

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Error 'node not found, please install Node.js first.'
    exit 1
}

# NOCODE_HOME is set during installation.
$NocodeHome = if ($env:NOCODE_HOME) { $env:NOCODE_HOME } else { Split-Path -Parent $MyInvocation.MyCommand.Definition }
$TuiPath = Join-Path $NocodeHome 'frontend\tui.ts'

if (-not (Test-Path $TuiPath)) {
    Write-Error "Cannot find frontend\tui.ts in $NocodeHome. Please reinstall or set NOCODE_HOME."
    exit 1
}

# Prepend venv Python to PATH so backend uses the right interpreter
$VenvPython = Join-Path $NocodeHome '.venv\Scripts'
if (Test-Path $VenvPython) {
    $env:PATH = "$VenvPython;$env:PATH"
}

# Set project dir so backend can find config.yaml
$env:NOCODE_PROJECT_DIR = $NocodeHome

npx tsx $TuiPath @ExtraArgs
