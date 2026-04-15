param([Parameter(ValueFromRemainingArguments)] $ExtraArgs)

$ErrorActionPreference = 'Stop'

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Error 'node not found, please install Node.js first.'
    exit 1
}

# NOCODE_HOME is set during installation.
$NocodeHome = if ($env:NOCODE_HOME) { $env:NOCODE_HOME } else { Split-Path -Parent $MyInvocation.MyCommand.Definition }
$FrontendDir = Join-Path $NocodeHome 'frontend'
$DistDir = Join-Path $FrontendDir 'dist'
$EntryPath = Join-Path $DistDir 'index.js'

if (-not (Test-Path $FrontendDir)) {
    Write-Error "Cannot find frontend in $NocodeHome. Please reinstall or set NOCODE_HOME."
    exit 1
}

$NeedsBuild = -not (Test-Path $EntryPath)
if (-not $NeedsBuild) {
    $EntryTime = (Get-Item $EntryPath).LastWriteTimeUtc
    $SourceFiles = Get-ChildItem $FrontendDir -Recurse -File | Where-Object {
        $_.FullName -notlike "$DistDir*" -and
        $_.FullName -notlike (Join-Path $FrontendDir 'node_modules*') -and
        ($_.Extension -in '.ts', '.tsx', '.json')
    }
    $NeedsBuild = $SourceFiles | Where-Object { $_.LastWriteTimeUtc -gt $EntryTime } | Select-Object -First 1
}

if ($NeedsBuild) {
    Push-Location $FrontendDir
    try {
        npm run build | Out-Host
    } finally {
        Pop-Location
    }
}

# Prepend venv Python to PATH so backend uses the right interpreter
$VenvPython = Join-Path $NocodeHome '.venv\Scripts'
if (Test-Path $VenvPython) {
    $env:PATH = "$VenvPython;$env:PATH"
}

Remove-Item Env:NOCODE_PROJECT_DIR -ErrorAction SilentlyContinue
node $EntryPath @ExtraArgs
