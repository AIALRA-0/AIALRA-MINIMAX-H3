[CmdletBinding()]
param(
    [string]$RuntimeRoot = 'D:\AIALRA-MINIMAX-H3',
    [int]$Port = 8188,
    [int]$GpuIndex = 0,
    [switch]$CpuOnly,
    [switch]$UsePinnedMemory,
    [switch]$DisableFastDisk,
    [switch]$DisableSageAttention,
    [switch]$Foreground
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $RuntimeRoot 'venvs\comfyui\Scripts\python.exe'
$comfyRoot = Join-Path $RuntimeRoot 'ComfyUI'
$config = Join-Path $repoRoot 'config\extra_model_paths.yaml'
$output = Join-Path $RuntimeRoot 'outputs\comfyui'
$logs = Join-Path $RuntimeRoot 'logs'
$pids = Join-Path $RuntimeRoot 'pids'
$state = Join-Path $RuntimeRoot 'state\comfyui'
New-Item -ItemType Directory -Force -Path $output, $logs, $pids, $state | Out-Null

if (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue) {
    throw "Port $Port is already in use. Refusing to replace an existing service."
}

$arguments = @(
    (Join-Path $comfyRoot 'main.py'),
    '--listen', '127.0.0.1',
    '--port', $Port,
    '--extra-model-paths-config', $config,
    '--output-directory', $output,
    '--user-directory', $state,
    '--database-url', ('sqlite:///' + ((Join-Path $state 'comfyui.db') -replace '\\', '/')),
    '--preview-method', 'none'
)
if ($CpuOnly) {
    $arguments += '--cpu'
} else {
    $arguments += @('--cuda-device', $GpuIndex, '--lowvram')
    if (-not $UsePinnedMemory) {
        $arguments += '--disable-pinned-memory'
    }
    if (-not $DisableFastDisk) {
        $arguments += '--fast-disk'
    }
    if (-not $DisableSageAttention) {
        $sageAvailable = & $python -c "import importlib.util; print('1' if importlib.util.find_spec('sageattention') else '0')"
        if ($LASTEXITCODE -eq 0 -and $sageAvailable.Trim() -eq '1') {
            $arguments += '--use-sage-attention'
        }
    }
}

if ($Foreground) {
    & $python @arguments
    exit $LASTEXITCODE
}

$startArguments = $arguments | ForEach-Object {
    if ($_ -match '[\s"]') {
        '"' + ($_ -replace '"', '\"') + '"'
    } else {
        $_
    }
}
$process = Start-Process -FilePath $python -ArgumentList ($startArguments -join ' ') -WorkingDirectory $comfyRoot `
    -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logs 'comfyui.stdout.log') `
    -RedirectStandardError (Join-Path $logs 'comfyui.stderr.log') -PassThru
Set-Content -LiteralPath (Join-Path $pids 'comfyui.pid') -Value $process.Id
Write-Host "ComfyUI started as PID $($process.Id) on GPU $GpuIndex at http://127.0.0.1:$Port"
