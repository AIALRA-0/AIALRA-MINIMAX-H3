[CmdletBinding()]
param(
    [string]$RuntimeRoot = 'D:\AIALRA-MINIMAX-H3',
    [Parameter(Mandatory = $true)]
    [string]$Query,
    [ValidateSet('', 'Checkpoint', 'LORA', 'Workflows', 'ComfyWorkflows', 'Other')]
    [string]$Type = '',
    [string]$BaseModel = '',
    [ValidateRange(1, 100)]
    [int]$Limit = 20
)

$ErrorActionPreference = 'Stop'
$cli = Join-Path $RuntimeRoot 'tools\civitai-mcp\mcp-cli.mjs'
if (-not (Test-Path -LiteralPath $cli -PathType Leaf)) {
    throw 'Civitai MCP CLI is not installed. Run scripts\Install-CivitaiMcp.ps1 first.'
}

$arguments = [ordered]@{
    query = $Query
    sort = 'Most Downloaded'
    period = 'AllTime'
    limit = $Limit
}
if ($Type) { $arguments.type = $Type }
if ($BaseModel) { $arguments.baseModel = $BaseModel }
$json = $arguments | ConvertTo-Json -Compress

& node $cli call search_models $json --json
if ($LASTEXITCODE -ne 0) {
    throw 'Civitai MCP search failed'
}
