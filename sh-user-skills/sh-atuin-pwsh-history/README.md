---
name: sh-atuin-pwsh-history
description: 装机/排障：Windows atuin 命令历史配置与 profile 修复（hh、Ctrl+r、上下键召回）。点名使用
---

# atuin + PowerShell「当前目录最近命令」配置（Windows / Tabby）

## 目标效果

PowerShell（Tabby 或任意终端宿主）里随时敲 `hh`，显示**当前目录**最近执行过的命令（默认 5 条，`hh 20` 显示 20 条）。数据源是 atuin 本地历史库、无时间限制；时间升序展示，最新一条在最下方、紧贴提示符。

**Ctrl+r 全屏搜索默认只搜当前目录**（底部显示 `[ DIRECTORY ]`）；在搜索界面里再按一次 Ctrl+r 即在 `目录 ↔ 全局` 之间一键切换（Ctrl+s 切换搜索模式）。开窗默认不自动显示 `hh`（用户偏好；想自动显示见"常用定制"）。

## 新机器安装（三步）

### 1. 安装 atuin

```powershell
winget install AtuinSh.Atuin
```

装完**必须重开终端**（winget 写的是用户级 PATH，旧进程看不到）。`atuin --version` 能出版本号才算就绪。

### 2. 写 $PROFILE + config.toml（推荐用脚本，自动备份 + 带 BOM）

写之前**必须先看现有 profile**：`Test-Path $PROFILE` 为真就先读内容问用户要不要保留。真实事故：用户旧配置（oh-my-posh 等）被 `Set-Content` 直接覆盖，无任何自动备份可恢复。脚本会自动备份为 `.bak-时间戳`：

```powershell
powershell -ExecutionPolicy Bypass -File <本skill目录>/scripts/install-profile.ps1        # 默认：开窗不显示，敲 hh 才显示
powershell -ExecutionPolicy Bypass -File <本skill目录>/scripts/install-profile.ps1 -AutoShow  # 开窗自动显示一次
```

脚本同时幂等处理 `~\.config\atuin\config.toml`（不存在则创建；注释掉的默认行则原地启用；已有行则改写）：

```toml
enter_accept = false
filter_mode = "directory"

[search]
filters = ["directory", "global", "host", "session", "workspace", "session-preload"]
```

- `enter_accept = false`：Ctrl+r 选中后放回输入行编辑，而不是立即执行。
- `filter_mode = "directory"`：Ctrl+r 默认只搜当前目录。
- `filters` 把 directory 排第一：TUI 里 Ctrl+r 循环时一步切到 global（默认顺序会先跑到 session-preload 再绕回 global）。
- `filter_mode` 是顶层键，必须出现在 `[search]` 段之前；`filters` 才是 `[search]` 的键。

手动路径（无脚本时）：用**单引号 here-string** `@'...'@` 包住下方模板 + `Set-Content -Path $PROFILE -Encoding UTF8`（PS 5.1 的 UTF8 自带 BOM）。绝不能用双引号 here-string（`$` 和反引号会被当场展开）。

### 3. 重开终端窗口，敲 `hh` 验证；Ctrl+r 打开搜索应显示 `[ DIRECTORY ]`

## profile 最终模板（已在本机验证）

这就是磁盘上的最终内容；脚本里内嵌的同一份，改一处要同步另一处。

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 先初始化 atuin（这一步才会设置 ATUIN_SESSION，必须在 search 之前）
Invoke-Expression (& { (atuin init powershell) -join "`n" })

# 上/下键恢复经典行为：召回上/下一条命令到输入行，可直接编辑（必须写在 init 之后才能覆盖 atuin 的绑定）
# atuin 全屏搜索保留在 Ctrl+r
Set-PSReadLineKeyHandler -Chord UpArrow -Function PreviousHistory
Set-PSReadLineKeyHandler -Chord DownArrow -Function NextHistory

# 显示当前目录最近执行过的命令；敲 hh 刷新（默认5条），hh 20 显示20条（h 是系统内置别名，别用）
# --filter-mode global 是保险：hh 自己用 --cwd 精确过滤，不受 config.toml 里 filter_mode 影响
function Show-CwdHistory {
    param([int]$Count = 5)
    $lines = atuin search --filter-mode global --cwd $PWD.Path --limit $Count --format "{exit}`t{command}" 2>$null
    if ($lines) {
        Write-Host "`n[当前目录上次执行的命令]" -ForegroundColor Cyan
        $validCommands = @()
        foreach ($line in $lines) {
            $parts = $line -split "`t", 2
            if ($parts.Count -eq 2 -and $parts[0] -match '^-?\d+$') {
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

## 必踩的坑（每个都真实踩过，原因比现象重要）

1. **init 必须在 search 之前**。`atuin search` 依赖 `$ATUIN_SESSION`，它由 `atuin init powershell` 输出的脚本设置。顺序错了 search 必报 `Failed to find $ATUIN_SESSION`；如果还挂着 `2>$null`，错误被吞，表现为"什么都不显示"。极具迷惑性：用户**手动**在终端跑 `atuin search` 又是好的——因为那时 profile 已加载完、session 已存在。所以"手动能跑、开窗不显示"基本就是顺序问题。
2. **PS 5.1 读中文需要 UTF-8 BOM**。记事本"UTF-8"存的是无 BOM → 5.1 按 GBK 读 → 中文乱码（不影响解析但难看）。检查：文件前 3 字节应为 `EF BB BF`。修法：`[System.IO.File]::WriteAllText($p, [System.IO.File]::ReadAllText($p, [System.Text.Encoding]::UTF8), (New-Object System.Text.UTF8Encoding($true)))`。
3. **别用 `h` 做别名**。`h` 是内置 AllScope 别名（→ `Get-History`），`Set-Alias h ...` 会报"无法从别名 h 中删除 AllScope 选项"。用 `hh`（已验证空闲）。
4. **别手拆 atuin 默认输出**。默认列是 duration/exit/time/command 的 tab 分隔，靠列号猜容易错；而且多行脏命令（比如历史里混进的 here-string）会内嵌换行，把输出打成残片。用 `--format "{exit}`t{command}"` + 数字前缀校验：真正的每条记录以退出码+tab 开头，多行命令的残片行没有数字前缀，自动被滤掉。**退出码可能是负数**（`-1`、Ctrl+C 等），校验正则必须用 `^-?\d+$`；用 `^\d+$` 会把失败命令静默吞掉。
5. **子进程验证时 PSReadLine 假警报**。`powershell -NoProfile -Command` 非交互会话不自动加载 PSReadLine，atuin init 会 `Write-Error "Atuin requires the PSReadLine module to be installed."` 然后退出——这是复现环境的假信号，不是用户真实环境的问题。子进程里先 `Import-Module PSReadLine` 再测。
6. **上键被 atuin 接管，丢失经典"召回可编辑"**。atuin 18 默认把 UpArrow 绑成全屏搜索，且新版安装默认 `enter_accept = true`——搜索界面选中回车**立即执行**，用户失去"按上键召回上一条、补个参数再跑"的习惯（强烈差评）。修复两处：① profile 里 init **之后**重绑 `Set-PSReadLineKeyHandler -Chord UpArrow -Function PreviousHistory`（DownArrow 同理 NextHistory）——必须写在 init 之后，否则会被 atuin 的绑定盖掉；② `~\.config\atuin\config.toml` 设 `enter_accept = false`，让 atuin 搜索（Ctrl+r）选中后放回输入行而不是直接执行。重绑后 Up/Down 走的是 PSReadLine 自己的历史文件（atuin 运行时它仍持续记录，行为与装 atuin 前完全一致）。
7. **`--cwd .` 在 atuin 18.22 不再解析成当前目录**（按目录字段字面匹配，`.` 返回 0 条），加上 `2>$null` 后静默失败，表现为 `hh` 什么都不显示。必须传真实路径：`--cwd $PWD.Path`。
8. **atuin 判定"当前目录"优先读 `PWD` 环境变量**（`get_current_dir()` 里 `env::var("PWD")` 优先于进程 cwd）。从 git-bash/msys 启动的 powershell 会带 POSIX 路径的 `PWD`，目录过滤会全空——真实终端（Tabby/开始菜单启动）无此变量，不受影响。用子进程验证目录过滤前先 `Remove-Item Env:PWD`，否则拿到的是假阴性。
9. **Ctrl+r 在 TUI 内不是"再开一次搜索"，而是循环切换过滤模式**（Ctrl+s 切换搜索模式）。配合 `filters` 把 directory 排第一，`目录 ↔ 全局` 就是一键切换。

## 诊断流程（"不显示历史"）

只读检查，按序：

1. `Get-Content $PROFILE`——确认**磁盘上**的内容和用户以为的一致。最常见原因：在编辑器里改了没保存。
2. 文件前 3 字节是否 `EF BB BF`（坑 2）。
3. profile 里 `atuin init` 是否在 `atuin search` 之前（坑 1）。
4. 让用户（或子进程，注意坑 5）去掉 `2>$null` 手动跑 `atuin search --cwd $PWD.Path --limit 5` 看真实报错。
5. 确认目录里确实没历史也会不显示（正常现象）。看库里有啥：设好 session 后跑 `atuin search --filter-mode global --limit 8 --format '{directory} | {command}'`。若全局有、当前目录没有：先确认该目录真的没记录，再按坑 7/8 检查（`--cwd` 是否真实路径、`PWD` 是否被 msys 污染）。
6. `Get-ExecutionPolicy -List`——LocalMachine Unrestricted 一般无碍；Restricted 会导致 profile 整个不加载。
7. 用户实际用的宿主：Tabby/VS Code/Windows Terminal 默认 shell 必须是 `powershell.exe`（5.1），本配置的 `$PROFILE` 才会被加载；pwsh 7 的 profile 在 `Documents\PowerShell\`，是另一个文件。

## 验证方法（改完 profile 必做）

在子进程模拟"用户开新窗口"（PATH 修 atuin、导 PSReadLine、dot-source profile）：

```powershell
powershell -NoProfile -Command "Remove-Item Env:PWD -ErrorAction SilentlyContinue; `$env:Path = 'C:\Users\<user>\AppData\Local\Microsoft\WinGet\Packages\Atuinsh.Atuin_Microsoft.Winget.Source_8wekyb3d8bbwe;' + `$env:Path; Import-Module PSReadLine; . `$PROFILE; Write-Host '===hh==='; hh; Write-Host '===hh 15==='; hh 15"
```

（工作目录切到一个有历史记录的目录跑；开头的 `Remove-Item Env:PWD` 消除 msys 假阴性，坑 8。）预期：`===hh===` 后出现青色标题 `[当前目录上次执行的命令]` 和最多 N 条灰色命令；开窗阶段不应有输出（默认不自动显示）。

再验证 config.toml 的默认过滤是否生效（同一子进程、同一目录）：

```powershell
(atuin search --limit 500 --format '{command}' | Measure-Object).Count   # 默认=directory，应等于当前目录条数
(atuin search --filter-mode global --limit 500 --format '{command}' | Measure-Object).Count   # global，应明显更大
```

## 常用定制

- **条数**：`hh N` 临时指定；默认改函数里 `param([int]$Count = 5)` 的 5。
- **改 Ctrl+r 默认过滤**：改 `~\.config\atuin\config.toml` 的 `filter_mode`（取值 global/host/session/directory/workspace/session-preload）；`[search].filters` 控制启用列表和 Ctrl+r 的循环顺序。
- **放大到整个 git 仓库**：`workspaces = true`，再在 TUI 里切到 workspace（或 `filter_mode = "workspace"`）。子模块/多包项目比 directory 更实用。
- **开窗自动显示**：profile 末尾加一行 `Show-CwdHistory`。
- **跨机器同步历史**：`atuin register`（注册同步账号）+ `atuin sync`；或直接把旧机 `~\.local\share\atuin` 目录拷到新机同位置。不弄就是从零记，功能不受影响。
- **过滤行为**：残片/超长（≥120 字符）/以 `@`、`{` 开头的条目会被滤掉，实际展示可能少于请求数，属正常。
