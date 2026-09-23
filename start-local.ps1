param([switch]$NoBrowser)

$ErrorActionPreference = 'Stop'
$repoRoot = $PSScriptRoot
$apiDir = Join-Path $repoRoot 'apps/api'
$webDir = Join-Path $repoRoot 'apps/web'
$python = Join-Path $apiDir '.venv/Scripts/python.exe'
$node = 'C:\Program Files\nodejs\node.exe'
$logDir = Join-Path $env:TEMP 'qaldy-career-quest-local'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

if (-not (Test-Path $python)) { throw "Python environment not found: $python" }
if (-not (Test-Path $node)) { throw "Node.js not found: $node" }

function Test-LocalEndpoint([string]$Url) {
    try { $null = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2; return $true }
    catch { return $false }
}

if (Test-LocalEndpoint 'http://127.0.0.1:8000/health') {
    try {
        $runningSchema = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/openapi.json' -TimeoutSec 5
        $hasCurrentAuth = $null -ne $runningSchema.paths.'/api/v1/auth/me'
    } catch {
        $hasCurrentAuth = $false
    }
    if (-not $hasCurrentAuth) {
        throw 'Port 8000 is occupied by an incompatible API. Stop or move that service, then run start-local.ps1 again. No existing process was stopped.'
    }
}

if (-not (Test-LocalEndpoint 'http://127.0.0.1:8000/health')) {
    & (Join-Path $repoRoot 'scripts/setup-demo-auth.ps1')
    $envContent = Get-Content -LiteralPath (Join-Path $repoRoot '.env')
    foreach ($line in $envContent) {
        if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
            [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], 'Process')
        }
    }
    $env:APP_ENV = 'development'
    $env:AUTH_MODE = 'demo'
    $env:ALLOW_INSECURE_DEMO_AUTH = 'false'
    $env:DATASET_DIR = Join-Path $repoRoot 'data/seed/career_quest_dataset'
    $runtimeDir = Join-Path $repoRoot 'data/runtime'
    New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
    $dbPath = (Join-Path $runtimeDir 'career_quest.db').Replace('\', '/')
    $env:DATABASE_URL = "sqlite:///$dbPath"
    $env:CORS_ORIGINS = 'http://localhost:3000,http://127.0.0.1:3000'
    $env:API_PORT = '8000'
    $null = Start-Process -FilePath $python `
        -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000') `
        -WorkingDirectory $apiDir -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $logDir 'api.out.log') `
        -RedirectStandardError (Join-Path $logDir 'api.err.log')

    $deadline = (Get-Date).AddSeconds(30)
    while ((Get-Date) -lt $deadline -and -not (Test-LocalEndpoint 'http://127.0.0.1:8000/health')) {
        Start-Sleep -Milliseconds 500
    }
    if (-not (Test-LocalEndpoint 'http://127.0.0.1:8000/health')) {
        $details = Get-Content (Join-Path $logDir 'api.err.log') -Tail 30 -ErrorAction SilentlyContinue
        throw "API did not start. Logs: $logDir`n$($details -join "`n")"
    }
    Write-Host "HR demo-токен: $env:DEMO_HR_TOKEN"
} else {
    Write-Host 'API уже запущен на http://localhost:8000'
}

if (-not (Test-LocalEndpoint 'http://127.0.0.1:3000')) {
    $env:NEXT_PUBLIC_API_URL = 'http://localhost:8000'
    $null = Start-Process -FilePath $node `
        -ArgumentList @('node_modules/next/dist/bin/next', 'dev', '--hostname', '127.0.0.1', '--port', '3000') `
        -WorkingDirectory $webDir -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $logDir 'web.out.log') `
        -RedirectStandardError (Join-Path $logDir 'web.err.log')

    $deadline = (Get-Date).AddSeconds(60)
    while ((Get-Date) -lt $deadline -and -not (Test-LocalEndpoint 'http://127.0.0.1:3000')) {
        Start-Sleep -Milliseconds 500
    }
    if (-not (Test-LocalEndpoint 'http://127.0.0.1:3000')) {
        $details = Get-Content (Join-Path $logDir 'web.err.log') -Tail 30 -ErrorAction SilentlyContinue
        throw "Web app did not start. Logs: $logDir`n$($details -join "`n")"
    }
}

Write-Host 'Приложение доступно: http://localhost:3000'
Write-Host "Логи: $logDir"
if (-not $NoBrowser) { Start-Process 'http://localhost:3000' }
