param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$TargetDir,
    [switch]$KeepDemo
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SkillDir = Split-Path -Parent $ScriptDir
$TemplateDir = Join-Path $SkillDir "template"

if (-not (Test-Path $TargetDir)) {
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
}

$StudioHtml = Join-Path $TargetDir "studio.html"
if (Test-Path $StudioHtml) {
    Write-Error "error: $TargetDir already has a studio.html; not overwriting"
    exit 1
}

Write-Host "== copying template to $TargetDir"
Copy-Item -Path "$TemplateDir\*" -Destination $TargetDir -Recurse -Force

$AssetsDir = Join-Path $TargetDir "assets"
$CheckDir = Join-Path $TargetDir "out\check"
if (-not (Test-Path $AssetsDir)) { New-Item -ItemType Directory -Path $AssetsDir -Force | Out-Null }
if (-not (Test-Path $CheckDir)) { New-Item -ItemType Directory -Path $CheckDir -Force | Out-Null }

if (-not $KeepDemo) {
    $content = [System.IO.File]::ReadAllText($StudioHtml, [System.Text.Encoding]::UTF8)
    $content = $content.Replace('<script src="src/scenes/demo.js"></script>', '<!-- <script src="src/scenes/demo.js"></script>  (example only) -->')
    [System.IO.File]::WriteAllText($StudioHtml, $content, [System.Text.UTF8Encoding]::new($false))
}

Push-Location $TargetDir
try {
    Write-Host "== installing p5, p5.brush, puppeteer-core"
    npm install --silent

    Write-Host "== toolchain verification"
    if (Get-Command node -ErrorAction SilentlyContinue) {
        Write-Host "node   $(node -v)"
    } else {
        Write-Warning "MISSING: node"
    }

    if (Get-Command ffmpeg -ErrorAction SilentlyContinue) {
        Write-Host "ffmpeg ok"
    } else {
        Write-Warning "MISSING: ffmpeg"
    }

    $chromes = @(
        $env:CHROME_PATH,
        'C:\Program Files\Google\Chrome\Application\chrome.exe',
        'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe'
    )
    $foundChrome = $chromes | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
    if ($foundChrome) {
        Write-Host "chrome $foundChrome"
    } else {
        Write-Warning "MISSING: Chrome (pass --chrome=<path> to render.mjs)"
    }

    Write-Host "== ready: $TargetDir"
} finally {
    Pop-Location
}
