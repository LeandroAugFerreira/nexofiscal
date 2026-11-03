param([switch]$SkipInstall, [switch]$Portfolio)
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
New-Item -ItemType Directory -Force -Path (Join-Path $taskRoot '.tmp') | Out-Null
$env:TEMP = Join-Path $taskRoot '.tmp'
$env:TMP = $env:TEMP
if (-not (Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
$configText = Get-Content -LiteralPath '.env' -Raw
if ($Portfolio) {
    $configText = $configText -replace '(?m)^PORTFOLIO_ENABLED=false\s*$', 'PORTFOLIO_ENABLED=true'
    [System.IO.File]::WriteAllText((Join-Path $taskRoot '.env'), $configText)
}
if ($configText -match '(?m)^DEMO_PASSWORD=\s*$') {
    $taskBytes = New-Object byte[] 24
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($taskBytes)
    $taskPassword = [Convert]::ToBase64String($taskBytes)
    $configText = $configText -replace '(?m)^DEMO_PASSWORD=\s*$', "DEMO_PASSWORD=$taskPassword"
    [System.IO.File]::WriteAllText((Join-Path $taskRoot '.env'), $configText)
}
Set-Location -LiteralPath (Join-Path $taskRoot 'backend')
if (-not $SkipInstall) {
    if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) { python -m venv .venv; if ($LASTEXITCODE) { throw 'Falha na criação do ambiente Python.' } }
    & .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    if ($LASTEXITCODE) { throw 'Falha na instalação Python.' }
}
& .\.venv\Scripts\python.exe -m alembic upgrade head
if ($LASTEXITCODE) { throw 'Falha na migração.' }
& .\.venv\Scripts\python.exe -m app.seed
if ($LASTEXITCODE) { throw 'Falha no seed.' }
if (-not $SkipInstall) {
    Set-Location -LiteralPath (Join-Path $taskRoot 'frontend')
    & npm.cmd ci
    if ($LASTEXITCODE) { throw 'Falha na instalação React.' }
}
Set-Location -LiteralPath $taskRoot
Write-Host 'NexoFiscal configurado. Consulte README.md para iniciar os serviços. As senhas locais não são exibidas por este assistente.'
