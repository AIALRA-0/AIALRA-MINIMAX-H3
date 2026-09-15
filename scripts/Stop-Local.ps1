[CmdletBinding()]
param(
    [string]$RuntimeRoot = 'D:\AIALRA-MINIMAX-H3',
    [switch]$KeepComfyUI
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$targets = @(
    @{
        Name = 'Frontend'
        Port = 3000
        PidFile = 'frontend.pid'
        ListenerPattern = 'next.*start.*-p\s+3000'
        LauncherPattern = 'npm\.cmd.*run start.*-p\s+3000'
    },
    @{
        Name = 'Backend'
        Port = 8001
        PidFile = 'backend.pid'
        ListenerPattern = 'main\.py serve.*--port\s+8001'
        LauncherPattern = 'studio-backend.*main\.py serve.*--port\s+8001'
    },
    @{
        Name = 'ComfyUI'
        Port = 8188
        PidFile = 'comfyui.pid'
        ListenerPattern = 'ComfyUI[\\/]main\.py.*--port\s+8188'
        LauncherPattern = 'ComfyUI[\\/]main\.py.*--port\s+8188'
    }
)

foreach ($target in $targets) {
    if ($KeepComfyUI -and $target.Name -eq 'ComfyUI') { continue }

    $listener = Get-NetTCPConnection -State Listen -LocalPort $target.Port -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($listener) {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)" -ErrorAction SilentlyContinue
        if (-not $process -or $process.CommandLine -notmatch $target.ListenerPattern) {
            throw "Refusing to stop unknown process listening on port $($target.Port)"
        }
        Stop-Process -Id $listener.OwningProcess -ErrorAction Stop
        Write-Host "Stopped $($target.Name) listener PID $($listener.OwningProcess)"
    }

    $pidPath = Join-Path $RuntimeRoot ('pids\' + $target.PidFile)
    if (Test-Path -LiteralPath $pidPath) {
        $recordedPid = (Get-Content -LiteralPath $pidPath -Raw).Trim()
        if ($recordedPid -match '^\d+$') {
            $launcher = Get-CimInstance Win32_Process -Filter "ProcessId=$recordedPid" -ErrorAction SilentlyContinue
            if ($launcher) {
                $expectedLauncher = $launcher.CommandLine -match $target.LauncherPattern
                if ($target.Name -eq 'Frontend') {
                    $expectedLauncher = $expectedLauncher -and $launcher.CommandLine.Contains($repoRoot)
                }
                if (-not $expectedLauncher) {
                    throw "Refusing to stop unexpected recorded $($target.Name) launcher PID $recordedPid"
                }
                Stop-Process -Id $recordedPid -ErrorAction SilentlyContinue
            }
        }
        Remove-Item -LiteralPath $pidPath -Force
    }
}
