[CmdletBinding()]
param(
    [string]$RuntimeRoot = 'D:\AIALRA-MINIMAX-H3',
    [switch]$IncludeRef2VA,
    [Parameter(Mandatory = $true)]
    [switch]$AcceptModelTerms
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$manifestPath = Join-Path $repoRoot 'config\model-manifest.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$modelRoot = Join-Path $RuntimeRoot 'models'
$hfHome = Join-Path $RuntimeRoot 'cache\huggingface'
$hf = Join-Path $RuntimeRoot 'venvs\comfyui\Scripts\hf.exe'

if (-not (Test-Path -LiteralPath $hf -PathType Leaf)) {
    throw "Hugging Face CLI is missing at $hf. Run scripts\Install-Local.ps1 first."
}

$groups = @(
    $manifest.h3_fl2va,
    $manifest.seedvr2,
    $manifest.flux2_klein_4b_model,
    $manifest.flux2_klein_4b_support
)
if ($IncludeRef2VA) {
    $groups += $manifest.h3_ref2va_optional
}
$requiredBytes = ($groups.files.bytes | Measure-Object -Sum).Sum
$drive = Get-PSDrive -Name ([IO.Path]::GetPathRoot($RuntimeRoot).TrimEnd(':\'))
if ($drive.Free -lt ($requiredBytes + 15GB)) {
    throw "Insufficient free space on $($drive.Name): drive. Need model bytes plus a 15 GiB safety margin."
}

New-Item -ItemType Directory -Force -Path $modelRoot, $hfHome | Out-Null
$env:HF_HOME = $hfHome
$env:HF_HUB_CACHE = Join-Path $hfHome 'hub'
$env:HF_XET_CACHE = Join-Path $hfHome 'xet'

foreach ($group in $groups) {
    $groupRoot = if ($group.local_dir) {
        Join-Path $modelRoot $group.local_dir
    } else {
        $modelRoot
    }
    $pending = @()
    foreach ($file in $group.files) {
        $destination = Join-Path $groupRoot $file.path
        if ((Test-Path -LiteralPath $destination -PathType Leaf) -and
            (Get-Item -LiteralPath $destination).Length -eq [int64]$file.bytes) {
            Write-Host "[ok] $($file.path)"
        } else {
            $pending += $file.path
        }
    }
    if ($pending.Count -gt 0) {
        New-Item -ItemType Directory -Force -Path $groupRoot | Out-Null
        & $hf download $group.repo @pending --local-dir $groupRoot
        if ($LASTEXITCODE -ne 0) {
            throw "Model download failed for $($group.repo)"
        }
    }
}

foreach ($group in $groups) {
    $groupRoot = if ($group.local_dir) {
        Join-Path $modelRoot $group.local_dir
    } else {
        $modelRoot
    }
    foreach ($file in $group.files) {
        $destination = Join-Path $groupRoot $file.path
        if (-not (Test-Path -LiteralPath $destination -PathType Leaf)) {
            throw "Downloaded model is missing: $destination"
        }
        $actual = (Get-Item -LiteralPath $destination).Length
        if ($actual -ne [int64]$file.bytes) {
            throw "Size mismatch for $destination. Expected $($file.bytes), found $actual"
        }
    }
}

Write-Host "Model manifest verified under $modelRoot"
