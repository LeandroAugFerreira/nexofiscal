param()
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskBackend = Join-Path $taskRoot 'backend'
$taskFrontend = Join-Path $taskRoot 'frontend'
$taskPython = Join-Path $taskBackend '.venv\Scripts\python.exe'
$taskVite = Join-Path $taskFrontend 'node_modules\vite\bin\vite.js'
$taskLogs = Join-Path $taskRoot '.tmp'
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Execute infrastructure\setup-local.ps1 para preparar o Python.' }
if (-not (Test-Path -LiteralPath $taskVite)) { throw 'Execute infrastructure\setup-local.ps1 para preparar a interface.' }
if (-not (Test-Path -LiteralPath (Join-Path $taskRoot '.env'))) { throw 'Configuração local ausente. Execute infrastructure\setup-local.ps1.' }
$taskNode = (Get-Command node.exe -ErrorAction Stop).Source
New-Item -ItemType Directory -Force -Path $taskLogs | Out-Null

function Test-TaskEndpoint([string]$Url, [switch]$Health) {
    try {
        $taskResponse = Invoke-WebRequest -Uri $Url -TimeoutSec 2 -UseBasicParsing
        if ($Health) {
            $taskHealth = $taskResponse.Content | ConvertFrom-Json
            return ($taskHealth.status -eq 'ok' -and $taskHealth.fiscal -eq 'simulador')
        }
        return ($taskResponse.StatusCode -eq 200 -and $taskResponse.Content -match 'NexoFiscal')
    } catch { return $false }
}
function Wait-TaskEndpoint([string]$Url, [switch]$Health) {
    for ($taskAttempt = 0; $taskAttempt -lt 40; $taskAttempt++) {
        if (Test-TaskEndpoint -Url $Url -Health:$Health) { return }
        Start-Sleep -Milliseconds 500
    }
    throw "O serviço não respondeu. Consulte os logs em $taskLogs."
}
function Assert-TaskPortFree([int]$Port) {
    if (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue) {
        throw "A porta $Port está ocupada por outro serviço. Nenhum processo foi encerrado."
    }
}

if (-not (Test-TaskEndpoint -Url 'http://127.0.0.1:8010/api/health' -Health)) {
    Assert-TaskPortFree -Port 8010
    $env:TEMP = $taskLogs
    $env:TMP = $taskLogs
    Start-Process -FilePath $taskPython -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8010','--no-access-log') -WorkingDirectory $taskBackend -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskLogs 'api.stdout.log') -RedirectStandardError (Join-Path $taskLogs 'api.stderr.log') | Out-Null
    Wait-TaskEndpoint -Url 'http://127.0.0.1:8010/api/health' -Health
    Write-Host 'API iniciada.'
} else { Write-Host 'API já está disponível.' }

if (-not (Test-TaskEndpoint -Url 'http://127.0.0.1:5180')) {
    Assert-TaskPortFree -Port 5180
    Start-Process -FilePath $taskNode -ArgumentList @(('"' + $taskVite + '"'),'--host','127.0.0.1') -WorkingDirectory $taskFrontend -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskLogs 'frontend.stdout.log') -RedirectStandardError (Join-Path $taskLogs 'frontend.stderr.log') | Out-Null
    Wait-TaskEndpoint -Url 'http://127.0.0.1:5180'
    Write-Host 'Interface iniciada.'
} else { Write-Host 'Interface já está disponível.' }

Wait-TaskEndpoint -Url 'http://127.0.0.1:5180/api/health' -Health
if ((Test-Path -LiteralPath (Join-Path $taskRoot '.runtime\n8n-installed.json')) -and ((Get-Content -LiteralPath (Join-Path $taskRoot '.env') -Raw) -match '(?m)^N8N_HEALTH_URL=http://127\.0\.0\.1:5678/healthz\s*$')) {
    & $taskPython (Join-Path $PSScriptRoot 'n8n-local.py') start
    if ($LASTEXITCODE) { throw 'O NexoFiscal iniciou, mas o n8n precisa de verificação nos logs locais.' }
}
Write-Host 'NexoFiscal disponível em http://127.0.0.1:5180'
Write-Host 'Os serviços continuam em segundo plano. Este script pode ser executado novamente sem duplicar processos.'
