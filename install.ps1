<#
.SYNOPSIS
    Installs and registers the LM Studio Worker MCP server for Antigravity CLI (agy).
.DESCRIPTION
    1. Installs Python dependencies (mcp, openai, httpx).
    2. Registers the 'lmstudio-worker' MCP server in Antigravity's mcp_config.json.
    3. Deploys the skill definition to the global agy skills directory.
    4. Tests connection to the local LM Studio instance on port 1234.
#>

[CmdletBinding()]
param(
    [string]$LmStudioUrl = "http://localhost:1234/v1"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  LM Studio Worker for Antigravity CLI   " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Install Python dependencies
Write-Host "`n[1/4] Installing Python dependencies..." -ForegroundColor Yellow
$reqFile = Join-Path $ScriptDir "requirements.txt"
if (Test-Path $reqFile) {
    & python -m pip install -q -r $reqFile
    Write-Host "  Dependencies installed successfully." -ForegroundColor Green
} else {
    Write-Warning "requirements.txt not found in $ScriptDir."
}

# 2. Configure MCP Server in Antigravity configs
Write-Host "`n[2/4] Registering MCP server in Antigravity..." -ForegroundColor Yellow
$serverPy = Join-Path $ScriptDir "server.py"
$targetConfigs = @(
    "$HOME\.gemini\antigravity-cli\mcp_config.json",
    "$HOME\.gemini\config\mcp_config.json"
)

foreach ($cfgPath in $targetConfigs) {
    if (Test-Path $cfgPath) {
        try {
            $json = Get-Content $cfgPath -Raw | ConvertFrom-Json
            if (-not $json.mcpServers) {
                $json | Add-Member -MemberType NoteProperty -Name "mcpServers" -Value ([PSCustomObject]@{})
            }
            $serverObj = [PSCustomObject]@{
                command  = "python"
                args     = @($serverPy)
                disabled = $false
            }
            $json.mcpServers | Add-Member -MemberType NoteProperty -Name "lmstudio-worker" -Value $serverObj -Force
            $json | ConvertTo-Json -Depth 10 | Set-Content $cfgPath -Encoding UTF8
            Write-Host "  Registered in $cfgPath" -ForegroundColor Green
        } catch {
            Write-Warning "  Failed to update $cfgPath : $_"
        }
    }
}

# 3. Deploy Skill definition
Write-Host "`n[3/4] Registering Antigravity Skill..." -ForegroundColor Yellow
$skillSource = Join-Path $ScriptDir "SKILL.md"
$globalSkillDir = "$HOME\.gemini\config\skills\lmstudio-worker"

if (Test-Path $skillSource) {
    New-Item -ItemType Directory -Path $globalSkillDir -Force | Out-Null
    Copy-Item -Path $skillSource -Destination (Join-Path $globalSkillDir "SKILL.md") -Force
    Write-Host "  Skill installed to $globalSkillDir\SKILL.md" -ForegroundColor Green
}

# 4. Check LM Studio Connection
Write-Host "`n[4/4] Testing connection to LM Studio ($LmStudioUrl)..." -ForegroundColor Yellow
try {
    $modelsUrl = "$($LmStudioUrl.TrimEnd('/'))/models"
    $resp = Invoke-RestMethod -Uri $modelsUrl -Method Get -TimeoutSec 3
    $modelCount = if ($resp.data) { $resp.data.Count } else { 0 }
    Write-Host "  LM Studio is ONLINE ($modelCount models detected)." -ForegroundColor Green
} catch {
    Write-Host "  LM Studio not responding on $LmStudioUrl." -ForegroundColor DarkYellow
    Write-Host "  (Ensure LM Studio is open and the local server is started on port 1234)" -ForegroundColor DarkGray
}

Write-Host "`nInstallation complete! Restart agy or reload MCP servers to start delegating tasks." -ForegroundColor Cyan
