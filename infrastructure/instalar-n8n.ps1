param()
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskRuntime = Join-Path $taskRoot '.runtime'
$taskNodeVersion = 'v24.22.0'
$taskN8nVersion = '2.43.7'
$taskNodeFolder = Join-Path $taskRuntime "node-$taskNodeVersion-win-x64"
$taskNode = Join-Path $taskNodeFolder 'node.exe'
$taskN8nFolder = Join-Path $taskRuntime 'n8n'
$taskCache = Join-Path $taskRoot '.tmp\npm-cache'
New-Item -ItemType Directory -Force -Path $taskRuntime,$taskCache | Out-Null
if (-not (Test-Path -LiteralPath $taskNode)) {
    $taskArchiveName = "node-$taskNodeVersion-win-x64.zip"
    $taskArchive = Join-Path $taskRuntime $taskArchiveName
    $taskDistribution = "https://nodejs.org/dist/$taskNodeVersion"
    Invoke-WebRequest -Uri "$taskDistribution/$taskArchiveName" -OutFile $taskArchive -UseBasicParsing
    $taskChecksums = (Invoke-WebRequest -Uri "$taskDistribution/SHASUMS256.txt" -UseBasicParsing).Content
    $taskExpectedLine = $taskChecksums -split "`n" | Where-Object { $_.Trim().EndsWith(" $taskArchiveName") }
    if (-not $taskExpectedLine) { throw 'Checksum oficial do Node não encontrado.' }
    $taskExpected = ($taskExpectedLine.Trim() -split '\s+')[0]
    if ((Get-FileHash -LiteralPath $taskArchive -Algorithm SHA256).Hash -ne $taskExpected) { throw 'Checksum do Node não confere.' }
    Expand-Archive -LiteralPath $taskArchive -DestinationPath $taskRuntime
    Write-Host 'Runtime Node local instalado e checksum validado.'
}
$taskNpm = Join-Path $taskNodeFolder 'node_modules\npm\bin\npm-cli.js'
$taskInstalledPackage = Join-Path $taskN8nFolder 'node_modules\n8n\package.json'
if ((Test-Path -LiteralPath (Join-Path $taskRuntime 'n8n-installed.json')) -and (Test-Path -LiteralPath $taskInstalledPackage) -and ((Get-Content -LiteralPath $taskInstalledPackage -Raw | ConvertFrom-Json).version -eq $taskN8nVersion)) {
    Write-Host 'Versão fixada do n8n já instalada.'
    exit 0
}
$env:PATH = $taskNodeFolder + ';' + $env:PATH
& $taskNode $taskNpm install --prefix $taskN8nFolder --cache $taskCache --save-exact --no-audit --no-fund "n8n@$taskN8nVersion"
if ($LASTEXITCODE) { throw 'Falha na instalação local do n8n.' }
@{node=$taskNodeVersion; n8n=$taskN8nVersion} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskRuntime 'n8n-installed.json') -Encoding UTF8
Write-Host "n8n $taskN8nVersion instalado dentro do projeto."
