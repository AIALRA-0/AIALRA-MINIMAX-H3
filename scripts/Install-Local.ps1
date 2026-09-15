[CmdletBinding()]
param(
    [string]$RuntimeRoot = 'D:\AIALRA-MINIMAX-H3',
    [switch]$SkipFrontend
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$comfyRoot = Join-Path $RuntimeRoot 'ComfyUI'
$comfyVenv = Join-Path $RuntimeRoot 'venvs\comfyui'
$backendVenv = Join-Path $RuntimeRoot 'venvs\studio-backend'

$pins = @{
    ComfyUI = '36da3ff763687eab86a35e1019995dd1fb369b0d'
    KJNodes = 'd3cfe21625e5170126ce06fbfcfe1d88108688c3'
    VideoHelperSuite = '4d907bee61e92c2e65af3bd6383a4e4d356126d1'
    PromptWriter = '33db7980ad98129bbff03d639b420da95f3bc684'
    Continuum = 'c38c616d54feb0310a3ca7540f2f4addc499fd1f'
}

function Install-PinnedRepository {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Commit
    )

    if (-not (Test-Path -LiteralPath (Join-Path $Path '.git'))) {
        git clone --filter=blob:none $Url $Path
        if ($LASTEXITCODE -ne 0) { throw "Unable to clone $Url" }
    }

    $dirty = git -C $Path status --porcelain
    if ($dirty) {
        throw "Refusing to change a modified dependency checkout: $Path"
    }

    git -C $Path fetch origin $Commit --depth 1
    if ($LASTEXITCODE -ne 0) { throw "Unable to fetch pinned commit $Commit from $Url" }
    git -C $Path checkout --detach $Commit
    if ($LASTEXITCODE -ne 0) { throw "Unable to check out pinned commit $Commit in $Path" }
}

$directories = @(
    (Join-Path $RuntimeRoot 'models'),
    (Join-Path $RuntimeRoot 'cache'),
    (Join-Path $RuntimeRoot 'outputs\comfyui'),
    (Join-Path $RuntimeRoot 'outputs\studio'),
    (Join-Path $RuntimeRoot 'logs'),
    (Join-Path $RuntimeRoot 'pids'),
    (Join-Path $RuntimeRoot 'tmp'),
    (Join-Path $RuntimeRoot 'venvs')
)
New-Item -ItemType Directory -Force -Path $directories | Out-Null

Install-PinnedRepository -Url 'https://github.com/Comfy-Org/ComfyUI.git' -Path $comfyRoot -Commit $pins.ComfyUI
if (-not (Test-Path -LiteralPath $comfyVenv)) {
    python -m venv $comfyVenv
}
$comfyPython = Join-Path $comfyVenv 'Scripts\python.exe'
& $comfyPython -m pip install --upgrade pip
& $comfyPython -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu130
& $comfyPython -m pip install -r (Join-Path $comfyRoot 'requirements.txt')

$customNodes = Join-Path $comfyRoot 'custom_nodes'
$kjNodes = Join-Path $customNodes 'ComfyUI-KJNodes'
$videoHelpers = Join-Path $customNodes 'ComfyUI-VideoHelperSuite'
$promptWriter = Join-Path $customNodes 'ComfyUI-MiniMaxH3-Prompt-Writer'
$continuum = Join-Path $customNodes 'ComfyUI-H3-Continuum'
Install-PinnedRepository -Url 'https://github.com/kijai/ComfyUI-KJNodes.git' -Path $kjNodes -Commit $pins.KJNodes
Install-PinnedRepository -Url 'https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git' -Path $videoHelpers -Commit $pins.VideoHelperSuite
Install-PinnedRepository -Url 'https://github.com/duckyshell/ComfyUI-MiniMaxH3-Prompt-Writer.git' -Path $promptWriter -Commit $pins.PromptWriter
Install-PinnedRepository -Url 'https://github.com/ukr8b3g-cmyk/ComfyUI-H3-Continuum.git' -Path $continuum -Commit $pins.Continuum
& $comfyPython -m pip install -r (Join-Path $kjNodes 'requirements.txt')
& $comfyPython -m pip install -r (Join-Path $videoHelpers 'requirements.txt')
if (Test-Path -LiteralPath (Join-Path $promptWriter 'requirements.txt')) {
    & $comfyPython -m pip install -r (Join-Path $promptWriter 'requirements.txt')
}
if (Test-Path -LiteralPath (Join-Path $continuum 'requirements.txt')) {
    & $comfyPython -m pip install -r (Join-Path $continuum 'requirements.txt')
}

if (-not (Test-Path -LiteralPath $backendVenv)) {
    python -m venv $backendVenv
}
$backendPython = Join-Path $backendVenv 'Scripts\python.exe'
& $backendPython -m pip install --upgrade pip
& $backendPython -m pip install -r (Join-Path $repoRoot 'backend\requirements-local.txt')

if (-not $SkipFrontend) {
    $env:npm_config_cache = Join-Path $RuntimeRoot 'cache\npm'
    npm --prefix (Join-Path $repoRoot 'frontend') ci
    npm --prefix (Join-Path $repoRoot 'frontend') run build
}

& $comfyPython -c "import torch; assert torch.cuda.is_available(); print(torch.__version__, torch.cuda.get_device_name(0))"
Write-Host "Local runtime installed at $RuntimeRoot"
