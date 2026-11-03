$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Instale e inicie Docker Desktop com containers Linux antes de executar este script.' }
if (-not (Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
$configText = Get-Content -LiteralPath '.env' -Raw
foreach ($taskKey in @('DEMO_PASSWORD','POSTGRES_PASSWORD','N8N_ENCRYPTION_KEY','AUTOMATION_TOKEN')) {
    if ($configText -match "(?m)^$taskKey=\s*$") {
        $taskBytes = New-Object byte[] 32
        [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($taskBytes)
        $taskSecret = -join ($taskBytes | ForEach-Object { $_.ToString('x2') })
        $configText = $configText -replace "(?m)^$taskKey=\s*$", "$taskKey=$taskSecret"
    }
}
[System.IO.File]::WriteAllText((Join-Path $taskRoot '.env'), $configText)
& docker compose up --build -d
if ($LASTEXITCODE) { throw 'Docker Compose não iniciou. Consulte docker compose logs.' }
& docker compose exec backend python -m app.seed
if ($LASTEXITCODE) { throw 'Seed não aplicado. Aguarde a API saudável e repita docker compose exec backend python -m app.seed.' }
Write-Host 'Ambiente iniciado: interface http://localhost:8080, API http://localhost:8010/docs e n8n http://localhost:5678.'
