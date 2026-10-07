---
name: sh-disk-space-cleanup
description: 排障：C 盘空间不足排查与清理（空间去向扫描、Temp/缓存/WSL 等安全释放，以移代删与软链接/环境变量重定向）。点名使用
---

# sh-disk-space-cleanup — C 盘空间不足排查与清理

先只读扫描摸清"空间去哪了"，把大头列成清单让用户拍板，再按风险分级处置（A 级直接清、B 级逐项确认/以移代删、C 级改系统或应用设置），最后验证剩余空间。
铁律：**扫描只读、删除前先列清单、不可逆操作必须用户逐项确认**。
系统内存防线原则：**严禁随意压缩 pagefile.sys 虚拟内存！**（参见 sh-windows-memory-guard，32GB~48GB 虚拟内存是多开开发工具与大模型的防 OOM 核心护城河）。

## 工作流

1. 排查扫描（全部只读，优先 FSO/热点快扫避免超时）
2. 汇总大头 + 按下表分级给建议（删除 vs 环境变量重定向 vs 跨盘迁移 Junction）
3. 用户拍板
4. 分级执行（先干掉 A 级垃圾，再按用户意向搬迁/清理 B 级）
5. 验证汇报（前后剩余空间对比、验证重定向/联接可用性）

## Step 1 排查扫描

### 1.1 总量与系统文件（PS 5.1）

```powershell
Get-Volume -DriveLetter C | Format-List Size, SizeRemaining
Get-ChildItem C:\ -Force -File -ErrorAction SilentlyContinue | Select-Object Name, @{N='SizeGB';E={[math]::Round($_.Length/1GB,2)}}   # hiberfil/pagefile/swapfile
```

### 1.2 秒级热点快扫（避坑：全量 Get-ChildItem -Recurse 扫描 Users 会超时 >600s）

采用 COM `Scripting.FileSystemObject` 结合已知重度目录，秒级返回占用：

```powershell
$fso = New-Object -ComObject Scripting.FileSystemObject
$targets = @(
    "$env:LOCALAPPDATA\Temp",
    "$env:USERPROFILE\Downloads",
    "$env:USERPROFILE\Videos",
    "$env:USERPROFILE\.cache",
    "$env:USERPROFILE\.ollama",
    "$env:USERPROFILE\.local\share\opencode\snapshot",
    "$env:LOCALAPPDATA\pip\cache",
    "$env:LOCALAPPDATA\uv\cache",
    "$env:APPDATA\npm-cache",
    "$env:APPDATA\LarkShell",
    "$env:USERPROFILE\.vscode",
    "$env:USERPROFILE\.docker"
)
foreach ($t in $targets) {
    if (Test-Path -LiteralPath $t) {
        try {
            $folder = $fso.GetFolder($t)
            [PSCustomObject]@{ Path = $t; SizeGB = [math]::Round($folder.Size / 1GB, 2) }
        } catch {
            [PSCustomObject]@{ Path = $t; SizeGB = 'AccessDenied' }
        }
    }
}
```

### 1.3 vhdx 猎手（WSL/Docker 虚拟磁盘）

```powershell
Get-ChildItem "$env:LOCALAPPDATA","$env:APPDATA" -Recurse -Force -Filter *.vhdx -ErrorAction SilentlyContinue | Select-Object FullName, @{N='SizeGB';E={[math]::Round($_.Length/1GB,2)}}
```

### 1.4 回收站与 Temp 垃圾细查

```powershell
# 回收站
$s = (Get-ChildItem 'C:\$Recycle.Bin' -Recurse -Force -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum; "RecycleBin: $([math]::Round($s/1GB,2)) GB"

# Temp _MEI* 垃圾计数
$mei = Get-ChildItem "$env:LOCALAPPDATA\Temp" -Directory -Filter '_MEI*' -Force -ErrorAction SilentlyContinue
"_MEI* Count: $($mei.Count)"
```

## Step 2 热点速查与处置分级表

| 位置 | 量级 | 是什么 / 处置策略（分级） |
|---|---|---|
| `%LOCALAPPDATA%\Temp\_MEI*` | 每个 1~2GB，可累积 100+ 个 (30GB+) | PyInstaller 单文件 exe 运行时自解压残留，异常退出不自动删 → **纯垃圾直接清【A】** |
| `%LOCALAPPDATA%\Temp` 其他孤立文件 | 数 GB | 临时文件，跳过 in-use【A】 |
| 回收站 | 不定 | `Clear-RecycleBin -Force`【A】 |
| `.ollama\models\blobs\*partial*` | 每个几 GB | 模型下载中断残留，直接删【A】 |
| `Local\uv\cache` (Python 包缓存) | 20GB+ | 官方原生提供全局环境变量。**最佳实践：搬到 D 盘 + 配置永久环境变量 `UV_CACHE_DIR` 重定向【B-重定向】** |
| `.local\share\opencode\snapshot` | 10~20GB | OpenCode 编辑快照。直接删丢历史回滚；**最佳实践：以移代删，robocopy 搬迁至 D 盘 + `mklink /J` 建立目录联接【B-迁移】** |
| `.ollama\models` 本地模型库 | 20~50GB+ | 模型权重。**最佳实践：搬迁至 D 盘 + 配环境变量 `OLLAMA_MODELS` + 原位做 `mklink /J` 双保险【B-迁移】** |
| npm-cache / pip cache | 数 GB | 包管理器缓存，时间换空间【B-清理】 |
| `Local\wsl\{guid}\ext4.vhdx` | 10~60GB | WSL 发行版整个系统，`wsl --unregister` 不可逆【B】 |
| Downloads 顶层 `*.exe`/`*.msi` | 每个 ~1GB | 安装完即无用的安装包，只删顶层不递归【B】 |
| Videos 大录屏 | 单个 20GB+ | 删前让用户过目清单【B】 |
| `Roaming\LarkShell` 等 IM 缓存 | 5~10GB | **坚决不直接做 Junction**（热更新易损坏软链接/SQLite WAL 锁异常）。**最佳实践：客户端设置内【清理缓存】+ 官方重定向【更改文件存储位置到 D 盘】【C】** |
| `hiberfil.sys` | 内存的 40%~100% | 休眠文件，`powercfg /h off` 释放（确认用户不用休眠/快速启动）【C】 |
| `pagefile.sys` | 32GB+ | **⚠️ 严禁随意收回压缩！** 本机配合 `sh-windows-memory-guard` 作为 55GB+ Commit 气囊护城河，防 OOM 闪退与死机。除非用户磁盘极度告急且完全不跑高负载，否则保持【保留/受保护】状态 |

分级：
- **A** 无风险直接清
- **B-重定向** 官方原生支持环境变量重定向（如 `UV_CACHE_DIR`），最干净健壮
- **B-迁移（以移代删）** 官方无简单环境变量但应用支持文件系统重定向，通过 `robocopy /MOVE` 迁到非系统盘 + `mklink /J` 目录联接挂回原路径，C 盘清空且功能完全不受影响
- **B-清理** 有代价（时间/历史回滚），用户确认后清
- **C** 改系统设置或客户端内部配置

## Step 3 核心操作 SOP

### 3.1 A 级：清理 Temp `_MEI*` 垃圾
```powershell
$volBefore = (Get-Volume -DriveLetter C).SizeRemaining
$dirs = Get-ChildItem "$env:LOCALAPPDATA\Temp" -Directory -Filter '_MEI*' -Force -ErrorAction SilentlyContinue
$deleted = 0; $skipped = 0
if ($dirs) {
    foreach ($d in $dirs) {
        try { Remove-Item -LiteralPath $d.FullName -Recurse -Force -ErrorAction Stop; $deleted++ }
        catch { $skipped++ }
    }
}
$freedGB = [math]::Round(((Get-Volume -DriveLetter C).SizeRemaining - $volBefore) / 1GB, 2)
"Deleted: $deleted, Skipped: $skipped, Freed: $freedGB GB"
```

### 3.2 B 级：Python uv 缓存搬迁与官方环境变量重定向（推荐方案 A）
1. 确认无运行中 uv 进程：`Get-Process "*uv*" | Stop-Process -Force`
2. 跨盘迁移已有轮子：`robocopy "$env:LOCALAPPDATA\uv\cache" "D:\Users\<user>\.cache\uv" /MOVE /E /R:1 /W:1 /MT:8`
3. 移除残留空目录：`Remove-Item "$env:LOCALAPPDATA\uv\cache" -Recurse -Force -ErrorAction SilentlyContinue`
4. 设置永久环境变量：`[Environment]::SetEnvironmentVariable("UV_CACHE_DIR", "D:\Users\<user>\.cache\uv", "User")`
5. 验证生效：命令行执行 `uv cache dir`，确认返回已指向 D 盘路径。

### 3.3 B 级：以移代删与目录联接（Directory Junction）
以 `OpenCode snapshot` 为例：
1. 终止占用进程：`Get-Process "*opencode*" | Stop-Process -Force`
2. 跨盘迁移：`robocopy "C:\Users\<user>\.local\share\opencode\snapshot" "D:\...\snapshot" /MOVE /E /R:1 /W:1 /MT:8`
3. 移除残留空目录：`Remove-Item "C:\Users\<user>\.local\share\opencode\snapshot" -Recurse -Force`
4. 建立目录联接：`cmd /c mklink /J "C:\Users\<user>\.local\share\opencode\snapshot" "D:\...\snapshot"`
5. 验证联接：`Get-Item "C:\Users\<user>\.local\share\opencode\snapshot" | Select-Object LinkType, Target`

### 3.4 B 级：Ollama 模型库迁移全套规约
1. 彻底退出 Ollama 进程：`Get-Process "*ollama*" | Stop-Process -Force`
2. 跨盘迁移：`robocopy "C:\Users\<user>\.ollama\models" "D:\...\models" /MOVE /E /R:2 /W:1 /MT:8`
3. 原位建立 Junction 双保险：`cmd /c mklink /J "C:\Users\<user>\.ollama\models" "D:\...\models"`
4. 配置永久用户环境变量：`[Environment]::SetEnvironmentVariable("OLLAMA_MODELS", "D:\...\models", "User")`
5. **避坑（新版 Ollama 0.17+ GUI 客户端）**：
   桌面端在 `%LOCALAPPDATA%\Ollama\db.sqlite` 的 `settings` 表记录了 `models` 字段。若界面输入框仍显示 C 盘旧值，需在客户端退出状态下执行 SQLite 更新，或指导用户在 UI 的【Settings -> Model location】中直接点击 `Browse` 选中 D 盘路径，实现 UI 与底层的完全统一。

## 踩坑备忘

1. **扫描性能大坑**：`Get-ChildItem -Recurse` 遇上海量小文件的开发目录（如 node_modules、.cache、snapshot）会极慢导致 600s 超时。必须改用 COM `Scripting.FileSystemObject` 结合目标清单秒级测算。
2. **虚拟内存与内存保护联动**：切勿盲目把 `pagefile.sys` 列为清理对象！在重度开发与大模型并发环境下，它与 `sh-windows-memory-guard` 强关联，是抵御 OOM 的物理底线。
3. **环境变量 vs Junction 选择标准**：官方原生支持配置环境变量重定向的工具（如 `uv` 的 `UV_CACHE_DIR`），优先采用纯环境变量配置，干净稳定无文件系统依赖；官方无原生重定向或多工具混用硬编码路径的（如 `opencode snapshot`），采用 `mklink /J` 目录联接。
4. **Junction vs 符号链接**：跨盘重定向目录必须优先使用 `mklink /J`（Directory Junction），无需管理员权限且 NTFS 驱动层透明代理；切勿用 `mklink /D`，后者需要开发者模式或提权。
5. **IM 软件（飞书/微信等）绝对不要整目录建软链接**：频繁的静默热更新会覆盖 ReparsePoint 导致权限报错或软链接断开；且 SQLite WAL 跨盘锁可能不稳定。优先走软件内置的【文件存储位置更改】。
6. **乱码与判空**：终端 UTF-16 乱码不等于操作失败，以 `Test-Path` 与 `Get-Volume` 为准；枚举文件必须先判断 `$files.Count -gt 0`，避免 `-LiteralPath` 报 null 绑定。

## 实战战果记录

- **2026-09-23 初战**：511GB 盘从 9.9GB 释放至 147.7GB（净释放 **137.8GB**，WSL 清理、Temp 清理、Videos 归档）。
- **2026-10-04~05 二战**：476GB 盘从 99.7GB 优化至 **188.85GB**（净优化 **+89.1GB**！）：
  - Temp `_MEI*` 垃圾物理清除释放 34.1GB；
  - OpenCode snapshot 跨盘 Junction 转移释放 13.6GB；
  - Ollama 跨盘迁移与新版客户端 DB 协同释放 23.6GB；
  - Python `uv` 缓存跨盘搬迁与官方 `UV_CACHE_DIR` 环境变量重定向释放 23.1GB。
