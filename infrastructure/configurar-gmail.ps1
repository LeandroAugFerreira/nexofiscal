param([string]$Email = 'cliente.nfse.portifolio@gmail.com')
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskEnvPath = Join-Path $taskRoot '.env'
if (-not (Test-Path -LiteralPath $taskEnvPath)) { throw 'Crie o .env antes de configurar o Gmail.' }
Write-Host 'Use a senha de app gerada pelo Google para esta conta. Não use a senha normal do Gmail.'
$taskSecurePassword = Read-Host 'Senha de app (entrada oculta)' -AsSecureString
$taskPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($taskSecurePassword)
try {
    $taskAppPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($taskPointer).Replace(' ', '')
    if ($taskAppPassword -notmatch '^[a-zA-Z0-9]{16}$') { throw 'Informe a senha de app de 16 caracteres gerada pelo Google.' }
    $taskConfig = Get-Content -LiteralPath $taskEnvPath -Raw
    $taskFields = @{ SMTP_HOST='smtp.gmail.com'; SMTP_PORT='465'; SMTP_USERNAME=$Email; SMTP_PASSWORD=$taskAppPassword; SMTP_FROM_EMAIL=$Email; SMTP_FROM_NAME='NexoFiscal' }
    foreach ($taskField in $taskFields.Keys) {
        $taskLine = "$taskField=$($taskFields[$taskField])"
        if ($taskConfig -match "(?m)^$taskField=.*$") { $taskConfig = [regex]::Replace($taskConfig, "(?m)^$taskField=.*$", [System.Text.RegularExpressions.MatchEvaluator]{ param($taskMatch) $taskLine }) }
        else { $taskConfig += "`n$taskLine" }
    }
    [System.IO.File]::WriteAllText($taskEnvPath, $taskConfig)
    $taskPython = Join-Path $taskRoot 'backend\.venv\Scripts\python.exe'
    $taskApiProcesses = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Where-Object { $_.CommandLine -and $_.CommandLine.Contains($taskPython) -and $_.CommandLine -match 'uvicorn app.main:app' -and $_.CommandLine -match '8010' }
    if ($taskApiProcesses) {
        $taskApiProcesses | ForEach-Object { Stop-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }
        $taskLogDir = Join-Path $taskRoot '.tmp'
        New-Item -ItemType Directory -Force -Path $taskLogDir | Out-Null
        Start-Process -FilePath $taskPython -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8010') -WorkingDirectory (Join-Path $taskRoot 'backend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskLogDir 'gmail-api.stdout.log') -RedirectStandardError (Join-Path $taskLogDir 'gmail-api.stderr.log') | Out-Null
        Write-Host 'Configuração gravada localmente e API reiniciada. Teste pelo detalhe da nota com seu usuário Administrador ou Financeiro.'
    } else { Write-Host 'Configuração gravada localmente. Inicie a API e teste pelo detalhe da nota com seu usuário Administrador ou Financeiro.' }
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($taskPointer)
    $taskAppPassword = $null
    $taskSecurePassword.Dispose()
}
