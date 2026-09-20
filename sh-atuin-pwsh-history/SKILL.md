---
name: sh-atuin-pwsh-history
description: 在 Windows 上配置/修复 atuin「当前目录最近命令」历史显示（PowerShell 5.1 + Tabby/任意终端）：winget 装 atuin、写带 UTF-8 BOM 的 $PROFILE（atuin init 必须在 search 之前）、提供 hh 命令按需刷新（默认 5 条，hh N 自定义条数）。只要用户提到 atuin、shell/命令历史、"当前目录上次执行的命令"、开终端想看历史、新电脑配 Tabby/PowerShell 环境、ATUIN_SESSION 报错、atuin search 不显示或报错、profile 中文乱码、Set-Alias h AllScope 冲突、profile 被覆盖想恢复，都必须使用本 skill——即使用户只说"帮我配一下命令历史"也要触发；诊断任何 profile "不生效/不显示"类问题时也必须使用。
---

# atuin + PowerShell「当前目录最近命令」配置（Windows / Tabby）

## 目标效果

PowerShell（Tabby 或任意终端宿主）里随时敲 `hh`，显示**当前目录**最近执行过的命令（默认 5 条，`hh 20` 显示 20 条）。数据源是 atuin 本地历史库，按"新→旧"排序、无时间限制。开窗默认不自动显示（用户偏好；想自动显示见"常用定制"）。

## 新机器安装（两步）

### 1. 安装 atuin

```powershell
winget install AtuinSh.Atuin
```

装完**必须重开终端**（winget 写的是用户级 PATH，旧进程看不到）。`atuin --version` 能出版本号才算就绪。

### 2. 写 $PROFILE（推荐用脚本，自动备份 + 带 BOM）

写之前**必须先看现有 profile**：`Test-Path $PROFILE` 为真就先读内容问用户要不要保留。真实事故：用户旧配置（oh-my-posh 等）被 `Set-Content` 直接覆盖，无任何自动备份可恢复。脚本会自动备份为 `.bak-时间戳`：

```powershell
powershell -ExecutionPolicy Bypass -File <本skill目录>/scripts/install-profile.ps1        # 默认：开窗不显示，敲 hh 才显示
powershell -ExecutionPolicy Bypass -File <本skill目录>/scripts/install-profile.ps1 -AutoShow  # 开窗自动显示一次
```

手动路径（无脚本时）：用**单引号 here-string** `@'...'@` 包住下方模板 + `Set-Content -Path $PROFILE -Encoding UTF8`（PS 5.1 的 UTF8 自带 BOM）。绝不能用双引号 here-string（`$` 和反引号会被当场展开）。

### 3. 重开终端窗口，敲 `hh` 验证

## profile 最终模板（已在本机验证）

这就是磁盘上的最终内容；脚本里内嵌的同一份，改一处要同步另一处。

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 先初始化 atuin（这一步才会设置 ATUIN_SESSION，必须在 search 之前）
Invoke-Expression (& { (atuin init powershell) -join "`n" })

# 显示当前目录最近执行过的命令；敲 hh 刷新（默认5条），hh 20 显示20条（h 是系统内置别名，别用）
function Show-CwdHistory {
    param([int]$Count = 5)
    $lines = atuin search --cwd . --limit $Count --format "{exit}`t{command}" 2>$null
    if ($lines) {
        Write-Host "`n[当前目录上次执行的命令]" -ForegroundColor Cyan
        $validCommands = @()
        foreach ($line in $lines) {
            $parts = $line -split "`t", 2
            if ($parts.Count -eq 2 -and $parts[0] -match '^\d+$') {
                $cmd = $parts[1].Trim()
                if ($cmd -and ($cmd -notmatch '^[@{]') -and ($cmd.Length -lt 120)) {
                    $validCommands += $cmd
                }
            }
        }
        $validCommands | Select-Object -Last $Count | ForEach-Object {
            Write-Host "  > $_" -ForegroundColor DarkGray
        }
        Write-Host ""
    }
}
Set-Alias hh Show-CwdHistory
```

## 五个必踩的坑（每个都真实踩过，原因比现象重要）

1. **init 必须在 search 之前**。`atuin search` 依赖 `$ATUIN_SESSION`，它由 `atuin init powershell` 输出的脚本设置。顺序错了 search 必报 `Failed to find $ATUIN_SESSION`；如果还挂着 `2>$null`，错误被吞，表现为"什么都不显示"。极具迷惑性：用户**手动**在终端跑 `atuin search` 又是好的——因为那时 profile 已加载完、session 已存在。所以"手动能跑、开窗不显示"基本就是顺序问题。
2. **PS 5.1 读中文需要 UTF-8 BOM**。记事本"UTF-8"存的是无 BOM → 5.1 按 GBK 读 → 中文乱码（不影响解析但难看）。检查：文件前 3 字节应为 `EF BB BF`。修法：`[System.IO.File]::WriteAllText($p, [System.IO.File]::ReadAllText($p, [System.Text.Encoding]::UTF8), (New-Object System.Text.UTF8Encoding($true)))`。
3. **别用 `h` 做别名**。`h` 是内置 AllScope 别名（→ `Get-History`），`Set-Alias h ...` 会报"无法从别名 h 中删除 AllScope 选项"。用 `hh`（已验证空闲）。
4. **别手拆 atuin 默认输出**。默认列是 duration/exit/time/command 的 tab 分隔，靠列号猜容易错；而且多行脏命令（比如历史里混进的 here-string）会内嵌换行，把输出打成残片。用 `--format "{exit}`t{command}"` + 数字前缀校验：真正的每条记录以退出码（纯数字）+tab 开头，多行命令的残片行没有数字前缀，自动被滤掉。
5. **子进程验证时 PSReadLine 假警报**。`powershell -NoProfile -Command` 非交互会话不自动加载 PSReadLine，atuin init 会 `Write-Error "Atuin requires the PSReadLine module to be installed."` 然后退出——这是复现环境的假信号，不是用户真实环境的问题。子进程里先 `Import-Module PSReadLine` 再测。

## 诊断流程（"不显示历史"）

只读检查，按序：

1. `Get-Content $PROFILE`——确认**磁盘上**的内容和用户以为的一致。最常见原因：在编辑器里改了没保存。
2. 文件前 3 字节是否 `EF BB BF`（坑 2）。
3. profile 里 `atuin init` 是否在 `atuin search` 之前（坑 1）。
4. 让用户（或子进程，注意坑 5）去掉 `2>$null` 手动跑 `atuin search --cwd . --limit 5` 看真实报错。
5. 确认目录里确实没历史也会不显示（正常现象）。看库里有啥：设好 session 后跑 `atuin search --limit 8 --format '{directory} | {command}'`。
6. `Get-ExecutionPolicy -List`——LocalMachine Unrestricted 一般无碍；Restricted 会导致 profile 整个不加载。
7. 用户实际用的宿主：Tabby/VS Code/Windows Terminal 默认 shell 必须是 `powershell.exe`（5.1），本配置的 `$PROFILE` 才会被加载；pwsh 7 的 profile 在 `Documents\PowerShell\`，是另一个文件。

## 验证方法（改完 profile 必做）

在子进程模拟"用户开新窗口"（PATH 修 atuin、导 PSReadLine、dot-source profile）：

```powershell
powershell -NoProfile -Command "`$env:Path = 'C:\Users\<user>\AppData\Local\Microsoft\WinGet\Packages\Atuinsh.Atuin_Microsoft.Winget.Source_8wekyb3d8bbwe;' + `$env:Path; Import-Module PSReadLine; . `$PROFILE; Write-Host '===hh==='; hh; Write-Host '===hh 15==='; hh 15"
```

（工作目录切到一个有历史记录的目录跑。）预期：`===hh===` 后出现青色标题 `[当前目录上次执行的命令]` 和最多 N 条灰色命令；开窗阶段不应有输出（默认不自动显示）。

## 常用定制

- **条数**：`hh N` 临时指定；默认改函数里 `param([int]$Count = 5)` 的 5。
- **开窗自动显示**：profile 末尾加一行 `Show-CwdHistory`。
- **跨机器同步历史**：`atuin register`（注册同步账号）+ `atuin sync`；或直接把旧机 `~\.local\share\atuin` 目录拷到新机同位置。不弄就是从零记，功能不受影响。
- **过滤行为**：残片/超长（≥120 字符）/以 `@`、`{` 开头的条目会被滤掉，实际展示可能少于请求数，属正常。
