[CmdletBinding()]
param([string]$RuntimeRoot = 'D:\AIALRA-MINIMAX-H3')

$services = @(
    @{ Name = 'ComfyUI'; Port = 8188; Path = '/system_stats'; PidFile = 'comfyui.pid' },
    @{ Name = 'Backend'; Port = 8001; Path = '/health'; PidFile = 'backend.pid' },
    @{ Name = 'Frontend'; Port = 3000; Path = '/'; PidFile = 'frontend.pid' }
)

foreach ($service in $services) {
    $pidPath = Join-Path $RuntimeRoot ('pids\' + $service.PidFile)
    $recordedPid = if (Test-Path -LiteralPath $pidPath) { Get-Content -LiteralPath $pidPath } else { $null }
    $running = $false
    if ($recordedPid) {
        $running = $null -ne (Get-Process -Id $recordedPid -ErrorAction SilentlyContinue)
    }
    $http = try {
        (Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 -Uri ("http://127.0.0.1:{0}{1}" -f $service.Port, $service.Path)).StatusCode
    } catch { $null }
    $listenerPid = Get-NetTCPConnection -State Listen -LocalPort $service.Port -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty OwningProcess
    [pscustomobject]@{
        Service = $service.Name
        LauncherPID = $recordedPid
        ListenerPID = $listenerPid
        LauncherRunning = $running
        HTTP = $http
    }
}

nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu --format=csv,noheader
