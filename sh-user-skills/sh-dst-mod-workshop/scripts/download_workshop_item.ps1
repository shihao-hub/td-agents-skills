<#
.SYNOPSIS
  使用 SteamCMD 匿名下载饥荒联机版（DST AppID: 322330）创意工坊模组
.PARAMETER WorkshopId
  创意工坊物品 ID（例如 3152990521）
.PARAMETER TargetDir
  可选的目标存放路径，若未提供则下载到 Temp/steamcmd
#>
param(
    [Parameter(Mandatory=$true)]
    [string]$WorkshopId,
    [string]$TargetDir = ""
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$steamcmdDir = "$env:TEMP\steamcmd"
$steamcmdExe = "$steamcmdDir\steamcmd.exe"

# 1. 检查或安装 SteamCMD
if (-not (Test-Path $steamcmdExe)) {
    Write-Host "[*] 未检测到 SteamCMD，准备下载官方绿色包..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $steamcmdDir -Force | Out-Null
    $zipPath = "$steamcmdDir\steamcmd.zip"
    Invoke-WebRequest -Uri "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip" -OutFile $zipPath
    Expand-Archive -Path $zipPath -DestinationPath $steamcmdDir -Force
    Remove-Item $zipPath -Force
    Write-Host "[+] SteamCMD 安装完成: $steamcmdExe" -ForegroundColor Green
}

# 2. 执行匿名下载
Write-Host "[*] 正在连接 SteamCMD 匿名下载模组 $WorkshopId (DST AppID: 322330)..." -ForegroundColor Cyan
& $steamcmdExe +login anonymous +workshop_download_item 322330 $WorkshopId +quit

$downloadedPath = "$steamcmdDir\steamapps\workshop\content\322330\$WorkshopId"
if (Test-Path $downloadedPath) {
    Write-Host "[+] 模组下载成功: $downloadedPath" -ForegroundColor Green
    if ($TargetDir -ne "") {
        New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
        Copy-Item -Path "$downloadedPath\*" -Destination $TargetDir -Recurse -Force
        Write-Host "[+] 模组已复制至目标路径: $TargetDir" -ForegroundColor Green
    }
} else {
    Write-Error "[-] 模组下载失败或未在预期路径找到: $downloadedPath"
}
