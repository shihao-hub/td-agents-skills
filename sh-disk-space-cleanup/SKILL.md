---
name: sh-disk-space-cleanup
description: 排障：C 盘空间不足排查与清理（空间去向扫描、Temp/缓存/WSL 等安全释放）。点名使用
---

# sh-disk-space-cleanup — C 盘空间不足排查与清理

先只读扫描摸清"空间去哪了"，把大头列成清单让用户拍板，再按风险分级删除，最后验证剩余空间。铁律：**扫描只读、删除前先列清单、不可逆操作必须用户逐项确认**。

## 工作流

1. 排查扫描（全部只读）→ 2. 汇总大头 + 按下表分级给建议 → 3. 用户拍板 → 4. 分级执行 → 5. 验证汇报（前后剩余空间对比）

## Step 1 排查扫描（PS 5.1 命令模板，可直接用）

### 1.1 总量与系统文件

```powershell
Get-Volume -DriveLetter C | Format-List Size, SizeRemaining
Get-ChildItem C:\ -Force -File -ErrorAction SilentlyContinue | Select-Object Name, @{N='SizeGB';E={[math]::Round($_.Length/1GB,2)}}   # hiberfil/pagefile/swapfile
```

### 1.2 目录大小排行（万能模板，换路径复用）

```powershell
Get-ChildItem '<根目录>' -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object { $s = (Get-ChildItem $_.FullName -Recurse -Force -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum; [PSCustomObject]@{ Dir = $_.Name; SizeGB = [math]::Round($s/1GB,2) } } | Where-Object { $_.SizeGB -ge 0.5 } | Sort-Object SizeGB -Descending
```

依次扫：`C:\Users\<user>` → `AppData\Local` → `AppData\Roaming`。大目录扫描要数分钟，bash timeout 给 600s 以上。

### 1.3 vhdx 猎手（WSL/Docker 虚拟磁盘）

```powershell
Get-ChildItem "$env:LOCALAPPDATA","$env:APPDATA" -Recurse -Force -Filter *.vhdx -ErrorAction SilentlyContinue | Select-Object FullName, @{N='SizeGB';E={[math]::Round($_.Length/1GB,2)}}
```

### 1.4 杂项（回收站 + 常见缓存 + 大文件）

```powershell
# 回收站
$s = (Get-ChildItem 'C:\$Recycle.Bin' -Recurse -Force -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum; "RecycleBin: $([math]::Round($s/1GB,2)) GB"
# 大文件（安装包/视频等）
Get-ChildItem "$env:USERPROFILE\Downloads","$env:USERPROFILE\Videos" -Recurse -Force -File -ErrorAction SilentlyContinue | Where-Object { $_.Length -gt 100MB } | Sort-Object Length -Descending | Select-Object Length, FullName
```

## Step 2 热点速查表（本机实测量级，处置分级见括号）

| 位置 | 量级 | 是什么 / 删了会怎样 |
|---|---|---|
| `%LOCALAPPDATA%\Temp\_MEI*` | 每个 1~2GB，可累积 20+ 个 | PyInstaller one-file exe 运行时自解压目录，异常退出不自动删 → 纯垃圾【A】 |
| `%LOCALAPPDATA%\Temp` 其他 | 数 GB | 各工具临时文件（opencode 4GB 级也见过）【A】 |
| 回收站 | 不定 | `Clear-RecycleBin -Force`【A】 |
| `.ollama\models\blobs\*partial*` | 每个几 GB | 模型下载中断残留；非 partial 的 blob 是模型本体，删前须确认【A/部分 B】 |
| npm-cache / `Local\uv` / pip cache | 合计 20GB+ | 包管理器缓存，删了下次装包重新下载，"拿时间换空间"→ 空间够就别删【B】 |
| `Local\wsl\{guid}\ext4.vhdx` | 10~60GB | WSL 发行版整个系统，`wsl --unregister` 不可逆【B】 |
| `Local\Docker\wsl\**\*.vhdx` | 1~数 GB | docker-desktop 专用，属 Docker Desktop 不算用户发行版，默认不动【B】 |
| `.local\share\opencode\snapshot` | 10GB+ | 编辑前文件快照，删则旧会话不可回滚；同目录 `opencode.db` 是聊天记录**别删**【B】 |
| Downloads 顶层 `*.exe`/`*.msi` | 每个 ~1GB | 装完即无用的安装包，只删顶层不递归【B】 |
| Videos 等大视频 | 单个 20GB+ | 录屏/影片，删前让用户过目清单【B】 |
| `Roaming\LarkShell` 等 IM 缓存 | 5~10GB | 聊天文件缓存，应用内清理更稳【C】 |
| `hiberfil.sys` | 内存的 40%~100% | 休眠文件，`powercfg /h off` 释放（确认用户不用休眠/快速启动）【C】 |
| `pagefile.sys` | 10~30GB | 虚拟内存，设上限回收（改系统设置）【C】 |
| Windows 组件存储 | — | `DISM /Online /Cleanup-Image /StartComponentCleanup`，回收 2~5GB【C】 |

分级：**A** 无风险直接删 / **B** 不可逆或有代价，逐项等用户确认 / **C** 改系统设置，单独确认。

## Step 3 执行

### 3.1 删除操作硬规矩

1. **列清单再删**：删除命令内先逐行输出 `DELETE: <名> <大小>GB` 再删，透明可审计
2. **判空**：`$files` 为空时 `-LiteralPath $files.FullName` 报 null 绑定错误，先 `if ($files.Count -eq 0) { ... }`——扫描和执行之间现状可能已变（用户可能自己删了），以当场枚举为准，枚举到 0 个不是故障
3. **用 `-LiteralPath`** 不用 `-Path`：中文乱码名、`[]`、通配符都安全
4. **`-ErrorAction Continue` 逐个删**：被占用文件自动跳过，结尾报告 deleted/skipped 数
5. **系统级操作逐项确认**，一次一个，不打包执行

### 3.2 常用命令

```powershell
# Temp 的 _MEI* 残留（本机实测 21 个 / 24.4GB，其中 1 个 in-use 跳过属正常）
$dirs = Get-ChildItem "$env:LOCALAPPDATA\Temp" -Directory -Filter '_MEI*' -Force -ErrorAction SilentlyContinue
foreach ($d in $dirs) { try { Remove-Item -LiteralPath $d.FullName -Recurse -Force -ErrorAction Stop } catch {} }

# ollama 下载残留
Get-ChildItem "$env:USERPROFILE\.ollama\models\blobs" -Filter *partial* -File | Remove-Item -Force

# WSL 发行版：先映射名字再删
Get-ChildItem 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss' | ForEach-Object { $p = Get-ItemProperty $_.PSPath; [PSCustomObject]@{ Distro = $p.DistributionName; BasePath = $p.BasePath } }
wsl -l -v
wsl --unregister <发行版名>

# 顶层安装包/视频：枚举→列清单→删
$files = Get-ChildItem "$env:USERPROFILE\Downloads" -File | Where-Object { $_.Extension -in '.exe','.msi' }
if ($files.Count -gt 0) { $files | ForEach-Object { Write-Output ("DELETE: {0}  {1} GB" -f $_.Name, [math]::Round($_.Length/1GB,2)) }; Remove-Item -LiteralPath $files.FullName -Force -ErrorAction Continue }
```

## 踩坑备忘

- `wsl --unregister` / `wsl -l -v` 的中文输出是 UTF-16，终端显示为乱码间隔字符——乱码≠失败，用 `Test-Path <vhdx路径>` + `Get-Volume` 验证真实结果
- 目录大小扫描值 ≠ 删除时现状：本次实测 Videos 63GB 在用户批准与执行间隙已被用户手动清空，脚本枚举到 0 个文件，照常报告即可
- `Get-ChildItem` 列出的中文文件名乱码是控制台代码页问题，不影响 `-LiteralPath` 实际删除
- 增量确认清单：一轮没批准的项（缓存、IM 缓存、snapshot 等）记录下来，作为下次空间告急时的候选，不重复扫描全部

## 汇报模板

```text
C 盘剩余：X GB → Y GB（释放 Z GB）
| 项目 | 结果（哪些是我删的、哪些发现时已不在）|
遗留小尾巴：<不范围内的小文件，一句话>
后续候选：<本轮未批准项及大小>
```

发现"扫描时有大文件、执行时已不在"要如实说明不是我删的，避免用户误判。

---
**来源：** 2026-09-23 C 盘清理实战（511GB 盘 9.9GB→147.7GB，释放 137.8GB）
