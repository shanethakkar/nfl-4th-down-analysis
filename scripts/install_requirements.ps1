# Run from Explorer: right-click -> Run with PowerShell
# Or from a terminal: .\install_requirements.ps1
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$req = Join-Path $PSScriptRoot 'requirements.txt'
if (-not (Test-Path $req)) {
    Write-Error "requirements.txt not found at $req"
    exit 1
}
& python -m pip install -r $req
