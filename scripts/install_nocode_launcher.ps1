<#
.SYNOPSIS
  Install nocode launcher to PATH. After installation, run `nocode` from any directory.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\install_nocode_launcher.ps1
  powershell -ExecutionPolicy Bypass -File scripts\install_nocode_launcher.ps1 -Force
#>

param(
    [switch] $Force
)

$ErrorActionPreference = 'Stop'

# Resolve repo root (this script lives in scripts/)
$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Definition)
$SourcePath = Join-Path $RepoRoot 'scripts\nocode.ps1'

if (-not (Test-Path $SourcePath)) {
    Write-Error "Launcher script not found: $SourcePath"
    exit 1
}

$TargetDir = if ($env:NOCODE_BIN_DIR) { $env:NOCODE_BIN_DIR } else { Join-Path $env:USERPROFILE '.local\bin' }
$TargetPath = Join-Path $TargetDir 'nocode.ps1'

if (-not (Test-Path $TargetDir)) {
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
}

# Add target dir to user PATH if not already present
$PathEnv = [Environment]::GetEnvironmentVariable('Path', 'User')
if ($PathEnv -notlike "*$TargetDir*") {
    [Environment]::SetEnvironmentVariable('Path', "$PathEnv;$TargetDir", 'User')
    Write-Host "Added $TargetDir to user PATH (takes effect in new terminal windows)."
}

# Set NOCODE_HOME environment variable so the launcher can find the project
$CurrentHome = [Environment]::GetEnvironmentVariable('NOCODE_HOME', 'User')
if ($CurrentHome -ne $RepoRoot) {
    [Environment]::SetEnvironmentVariable('NOCODE_HOME', $RepoRoot, 'User')
    Write-Host "Set NOCODE_HOME = $RepoRoot"
}

# Skip if already installed and identical
if ((Test-Path $TargetPath) -and -not $Force) {
    $SrcHash = (Get-FileHash $SourcePath -Algorithm SHA256).Hash
    $DstHash = (Get-FileHash $TargetPath -Algorithm SHA256).Hash
    if ($SrcHash -eq $DstHash) {
        Write-Host "Already installed and up-to-date: $TargetPath"
        exit 0
    }
    Write-Host "File exists but content differs: $TargetPath" -ForegroundColor Yellow
    Write-Host 'Re-run with -Force to overwrite.'
    exit 1
}

# Copy with UTF-8 BOM so Windows PowerShell reads it correctly
$Content = [System.IO.File]::ReadAllText($SourcePath, [System.Text.Encoding]::UTF8)
$Utf8Bom = New-Object System.Text.UTF8Encoding($true)
[System.IO.File]::WriteAllText($TargetPath, $Content, $Utf8Bom)

Write-Host "Installed: $TargetPath" -ForegroundColor Green
Write-Host ''
Write-Host 'You can now run nocode from any directory:' -ForegroundColor Cyan
Write-Host '  nocode' -ForegroundColor White
