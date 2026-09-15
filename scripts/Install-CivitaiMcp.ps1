[CmdletBinding()]
param(
    [string]$RuntimeRoot = 'D:\AIALRA-MINIMAX-H3',
    [string]$ExpectedSha256 = '0A8331FA931E81EC7F546EA3E58BFDDA857D239C4430A649109347C771A78E04'
)

$ErrorActionPreference = 'Stop'
$toolRoot = Join-Path $RuntimeRoot 'tools\civitai-mcp'
$toolRootResolved = [IO.Path]::GetFullPath($toolRoot)
$runtimeResolved = [IO.Path]::GetFullPath($RuntimeRoot)
if (-not $toolRootResolved.StartsWith($runtimeResolved, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Civitai MCP tool path must stay inside RuntimeRoot'
}

New-Item -ItemType Directory -Force -Path $toolRoot | Out-Null
$destination = Join-Path $toolRoot 'mcp-cli.mjs'
$staging = Join-Path $toolRoot 'mcp-cli.mjs.download'

try {
    Invoke-WebRequest -UseBasicParsing -Uri 'https://mcp.civitai.com/cli' -OutFile $staging -TimeoutSec 60
    $actual = (Get-FileHash -Algorithm SHA256 -LiteralPath $staging).Hash
    if ($actual -ne $ExpectedSha256) {
        throw "Civitai MCP CLI checksum mismatch. Expected $ExpectedSha256, found $actual"
    }
    Move-Item -LiteralPath $staging -Destination $destination -Force
} finally {
    if (Test-Path -LiteralPath $staging -PathType Leaf) {
        Remove-Item -LiteralPath $staging -Force
    }
}

& node $destination schema search_models | Out-Host
if ($LASTEXITCODE -ne 0) {
    throw 'Civitai MCP read-only smoke test failed'
}
Write-Host "Civitai MCP CLI installed and verified: $destination"
