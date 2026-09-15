[CmdletBinding()]
param(
    [string]$RuntimeRoot = 'D:\AIALRA-MINIMAX-H3',
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[A-Za-z0-9._-]+$')]
    [string]$SshAlias,
    [ValidateRange(1024, 65535)]
    [int]$RemotePort = 14280,
    [ValidateRange(1, 65535)]
    [int]$LocalPort = 3000,
    [switch]$Foreground
)

$ErrorActionPreference = 'Stop'

if (-not (Get-NetTCPConnection -State Listen -LocalPort $LocalPort -ErrorAction SilentlyContinue)) {
    throw "No local studio listener was found on port $LocalPort"
}

$ssh = (Get-Command ssh.exe -ErrorAction Stop).Source
$logs = Join-Path $RuntimeRoot 'logs'
$pids = Join-Path $RuntimeRoot 'pids'
New-Item -ItemType Directory -Force -Path $logs, $pids | Out-Null

$forward = "127.0.0.1:${RemotePort}:127.0.0.1:${LocalPort}"
$arguments = @(
    '-N',
    '-T',
    '-o', 'BatchMode=yes',
    '-o', 'ExitOnForwardFailure=yes',
    '-o', 'ServerAliveInterval=30',
    '-o', 'ServerAliveCountMax=3',
    '-R', $forward,
    $SshAlias
)

if ($Foreground) {
    & $ssh @arguments
    exit $LASTEXITCODE
}

$pidPath = Join-Path $pids 'remote-tunnel.pid'
if (Test-Path -LiteralPath $pidPath) {
    $recordedPid = (Get-Content -LiteralPath $pidPath -Raw).Trim()
    if ($recordedPid -match '^\d+$' -and (Get-Process -Id $recordedPid -ErrorAction SilentlyContinue)) {
        throw "A recorded remote tunnel is already running with PID $recordedPid"
    }
    Remove-Item -LiteralPath $pidPath -Force
}

$process = Start-Process -FilePath $ssh `
    -ArgumentList $arguments -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logs 'remote-tunnel.stdout.log') `
    -RedirectStandardError (Join-Path $logs 'remote-tunnel.stderr.log') -PassThru
Set-Content -LiteralPath $pidPath -Value $process.Id

Start-Sleep -Seconds 2
if ($process.HasExited) {
    Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue
    throw "The reverse tunnel exited before it became ready. Inspect $logs"
}

$probe = & $ssh -o BatchMode=yes $SshAlias "curl -fsS --max-time 8 http://127.0.0.1:$RemotePort/ >/dev/null"
if ($LASTEXITCODE -ne 0) {
    Stop-Process -Id $process.Id -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue
    throw "The VPS could not reach the studio through the reverse tunnel"
}

Write-Host "Reverse tunnel PID $($process.Id) is ready on VPS loopback port $RemotePort"
