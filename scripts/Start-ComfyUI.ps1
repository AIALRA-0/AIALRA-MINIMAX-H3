[CmdletBinding()]
param(
    [string]$RuntimeRoot = 'D:\AIALRA-MINIMAX-H3',
    [int]$Port = 8188,
    [switch]$CpuOnly,
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
New-Item -ItemType Directory -Force -Path $output, $logs, $pids | Out-Null

$arguments = @(
    (Join-Path $comfyRoot 'main.py'),
    '--listen', '127.0.0.1',
    '--port', $Port,
    '--extra-model-paths-config', $config,
    '--output-directory', $output,
    '--preview-method', 'none'
)
if ($CpuOnly) {
    $arguments += '--cpu'
} else {
    $arguments += '--lowvram'
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
Write-Host "ComfyUI started as PID $($process.Id) on http://127.0.0.1:$Port"
