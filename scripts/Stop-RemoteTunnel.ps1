[CmdletBinding()]
param(
    [string]$RuntimeRoot = 'D:\AIALRA-MINIMAX-H3'
)

$ErrorActionPreference = 'Stop'
$pidPath = Join-Path $RuntimeRoot 'pids\remote-tunnel.pid'

if (-not (Test-Path -LiteralPath $pidPath)) {
    Write-Host 'No recorded remote tunnel is running'
    exit 0
}

$recordedPid = (Get-Content -LiteralPath $pidPath -Raw).Trim()
if ($recordedPid -notmatch '^\d+$') {
    throw 'The remote tunnel PID file is invalid'
}

$process = Get-CimInstance Win32_Process -Filter "ProcessId=$recordedPid" -ErrorAction SilentlyContinue
if ($process) {
    if ($process.Name -notmatch '^ssh(?:\.exe)?$' -or $process.CommandLine -notmatch 'ExitOnForwardFailure=yes' -or $process.CommandLine -notmatch '-R') {
        throw "Refusing to stop unexpected recorded process PID $recordedPid"
    }
    Stop-Process -Id $recordedPid -ErrorAction Stop
    Write-Host "Stopped reverse tunnel PID $recordedPid"
}

Remove-Item -LiteralPath $pidPath -Force
