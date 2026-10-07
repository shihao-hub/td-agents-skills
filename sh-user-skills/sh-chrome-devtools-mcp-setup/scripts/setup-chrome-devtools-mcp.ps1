# Setup chrome-devtools-mcp for opencode (idempotent)
# Checks node + Chrome, injects mcp entry into global opencode.json, backs up before write.
$ErrorActionPreference = "Stop"

$CfgDir  = Join-Path $env:USERPROFILE ".config\opencode"
$CfgPath = Join-Path $CfgDir "opencode.json"
$EntryName = "chrome-devtools"

# 1. Check prerequisites
$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) { Write-Host "[FAIL] node not found. Install Node.js LTS first: https://nodejs.org"; exit 1 }
Write-Host "[OK] node $(node -v)"

$chromePaths = @(
  "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
  "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)
$chrome = $chromePaths | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $chrome) {
  Write-Host "[WARN] Chrome not found in standard paths. Install Chrome (stable) before using browser tools."
} else {
  Write-Host "[OK] chrome $chrome"
}

# 2. Load or create config
if (Test-Path -LiteralPath $CfgPath) {
  try {
    $raw = Get-Content -LiteralPath $CfgPath -Raw -Encoding UTF8
    $cfg = $raw | ConvertFrom-Json
  } catch {
    Write-Host "[FAIL] $CfgPath is not valid JSON, fix it manually. Aborting (no changes made)."
    exit 1
  }
} else {
  New-Item -ItemType Directory -Force -Path $CfgDir | Out-Null
  $cfg = $null
}

# 3. Idempotency: skip if entry already present
$hasEntry = $false
if ($cfg -and $cfg.PSObject.Properties["mcp"] -and $cfg.mcp.PSObject.Properties[$EntryName]) { $hasEntry = $true }

if ($hasEntry) {
  Write-Host "[SKIP] mcp.$EntryName already configured in $CfgPath"
  Write-Host "[NEXT] Restart opencode to (re)load config."
  exit 0
}

# 4. Inject entry (build fresh config when file absent)
if (-not $cfg) {
  $doc = [ordered]@{
    '$schema' = "https://opencode.ai/config.json"
    "mcp"     = [ordered]@{ $EntryName = [ordered]@{ type = "local"; command = @("npx", "-y", "chrome-devtools-mcp@latest"); enabled = $true } }
  }
  $json = ConvertTo-Json -InputObject ([pscustomobject]$doc) -Depth 64
} else {
  $entry = [pscustomobject]@{ type = "local"; command = @("npx", "-y", "chrome-devtools-mcp@latest"); enabled = $true }
  if (-not $cfg.PSObject.Properties["mcp"]) {
    $cfg | Add-Member -NotePropertyName "mcp" -NotePropertyValue ([pscustomobject]@{})
  }
  $cfg.mcp | Add-Member -NotePropertyName $EntryName -NotePropertyValue $entry
  $json = ConvertTo-Json -InputObject $cfg -Depth 64
}

# 5. Backup + write (UTF8 no BOM)
if (Test-Path -LiteralPath $CfgPath) {
  Copy-Item -LiteralPath $CfgPath -Destination "$CfgPath.bak" -Force
  Write-Host "[OK] backup -> $CfgPath.bak"
}
[System.IO.File]::WriteAllText($CfgPath, $json, (New-Object System.Text.UTF8Encoding($false)))

# 6. Validate what we wrote
try {
  Get-Content -LiteralPath $CfgPath -Raw | ConvertFrom-Json | Out-Null
  Write-Host "[OK] written + JSON valid: $CfgPath"
  Write-Host "[NEXT] Restart opencode. First browser-tool use downloads the MCP package via npx."
} catch {
  Write-Host "[FAIL] post-write validation error: $_"
  if (Test-Path -LiteralPath "$CfgPath.bak") { Copy-Item -LiteralPath "$CfgPath.bak" -Destination $CfgPath -Force; Write-Host "[ROLLBACK] restored from backup" }
  exit 1
}
