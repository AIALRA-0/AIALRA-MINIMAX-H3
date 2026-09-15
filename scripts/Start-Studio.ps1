[CmdletBinding()]
param(
    [string]$RuntimeRoot = 'D:\AIALRA-MINIMAX-H3',
    [int]$BackendPort = 8001,
    [int]$FrontendPort = 3000,
    [switch]$LockedMode
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$logs = Join-Path $RuntimeRoot 'logs'
$pids = Join-Path $RuntimeRoot 'pids'
New-Item -ItemType Directory -Force -Path $logs, $pids | Out-Null

foreach ($port in @($BackendPort, $FrontendPort)) {
    if (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue) {
        throw "Port $port is already in use. Run scripts\Stop-Local.ps1 before restarting the studio."
    }
}

$env:AIALRA_LOCAL_ONLY = '1'
$env:AIALRA_H3_APPLIANCE = '1'
$env:AIALRA_LOCKED_MODE = if ($LockedMode) { '1' } else { '0' }
$env:AIALRA_DATA_ROOT = Join-Path $RuntimeRoot 'outputs\studio'
$env:AIALRA_JOB_DB = Join-Path $RuntimeRoot 'outputs\studio\jobs.sqlite3'
$env:COMFY_URL = 'http://127.0.0.1:8188'
$env:COMFY_DIR = Join-Path $RuntimeRoot 'ComfyUI'
$env:COMFY_MODELS_DIR = Join-Path $RuntimeRoot 'models'
$env:COMFY_OUTPUT_DIR = Join-Path $RuntimeRoot 'outputs\comfyui'
$env:COMFY_LORAS_DIR = Join-Path $RuntimeRoot 'models\loras'
$env:BACKEND_URL = "http://127.0.0.1:$BackendPort"

$backendPython = Join-Path $RuntimeRoot 'venvs\studio-backend\Scripts\python.exe'
$backend = Start-Process -FilePath $backendPython `
    -ArgumentList @('main.py', 'serve', '--host', '127.0.0.1', '--port', $BackendPort) `
    -WorkingDirectory (Join-Path $repoRoot 'backend') -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logs 'backend.stdout.log') `
    -RedirectStandardError (Join-Path $logs 'backend.stderr.log') -PassThru
Set-Content -LiteralPath (Join-Path $pids 'backend.pid') -Value $backend.Id

$npm = (Get-Command npm.cmd -ErrorAction Stop).Source
$frontend = Start-Process -FilePath $npm `
    -ArgumentList @('run', 'start', '--', '-p', $FrontendPort, '-H', '127.0.0.1') `
    -WorkingDirectory (Join-Path $repoRoot 'frontend') -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logs 'frontend.stdout.log') `
    -RedirectStandardError (Join-Path $logs 'frontend.stderr.log') -PassThru
Set-Content -LiteralPath (Join-Path $pids 'frontend.pid') -Value $frontend.Id

Write-Host "Studio backend PID $($backend.Id), frontend PID $($frontend.Id)"

$deadline = (Get-Date).AddSeconds(45)
do {
    $backendReady = try {
        (Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 -Uri "http://127.0.0.1:$BackendPort/health").StatusCode -eq 200
    } catch { $false }
    $frontendReady = try {
        (Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 -Uri "http://127.0.0.1:$FrontendPort/").StatusCode -eq 200
    } catch { $false }
    if ($backendReady -and $frontendReady) { break }
    Start-Sleep -Milliseconds 500
} while ((Get-Date) -lt $deadline)

if (-not ($backendReady -and $frontendReady)) {
    throw "Studio startup timed out. Inspect $logs for details."
}

Write-Host "Studio is ready at http://127.0.0.1:$FrontendPort"
