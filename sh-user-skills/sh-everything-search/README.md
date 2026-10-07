---
name: sh-everything-search
description: 全盘/跨盘文件秒搜（Everything es.exe 一次性查询，查完即退）：按文件名、扩展名、大小、修改时间、正则定位文件，支持计数与 JSON/CSV 导出。当任务要在整个磁盘或跨盘范围找文件时使用（全盘搜索、找大文件、找最近改动的文件、不记得放哪的文件、磁盘清理候选）；仓内找文件或搜文件内容用 rg/glob，不用本 skill。
---

# sh-everything-search — 全盘/跨盘秒搜（Everything es.exe）

本机装有 Everything（voidtools，1.4.1.1032）常驻维护 C:/D: 全盘索引（500 万+条目）；`es.exe` 是它的官方 CLI。
需要"全盘找文件"时直接在 shell 调 es：一两行命令、0.3~0.8 秒返回、查完即退——不需要任何常驻 MCP，也没有"每个 Agent 一份"的内存开销。

## 何时用 / 何时不用

- 用（本 skill 的价值场景）：跨盘/全盘按 文件名、扩展名、大小、修改时间、正则 找文件；找磁盘上的大文件/最近改动文件（清理、排障、找回）；全盘计数与总量统计；导出文件清单交给脚本聚合。
- 不用：仓内/单目录找文件（glob/rg 更快更准）；按内容搜文件（rg）；读取或展示文件内容。

## 生命周期与前置检查

1. 路径：`D:\Program Files\Everything\`（es.exe / Everything.exe）；找不到时依序尝试 `where.exe es` → `C:\Program Files\Everything\es.exe`。
2. 生命周期（按需启动 + 闲置自动退出）：本机已禁用 Everything 开机自启，默认不常驻，由本 skill 自动管理：
   - **统一用包装器** `scripts/es_query.ps1` 执行查询：索引进程不在时自动 `-startup` 拉起并等待就绪（实测 ~2.5s、无窗口），已在运行则直接查询；
   - 每次查询刷新活动时间 `%APPDATA%\language_projects\sh-everything-search\last_use.txt`；
   - 计划任务 `sh-everything-idle-exit`（隐藏、每 5 分钟）在"15 分钟无查询 + 无可见窗口 + 无查询进行中"时自动 `es -exit` 释放 ~430MB；用户手动打开的实例不会被退掉；
   - 查询任务结束**不需要**手动退出；要立即释放可 `& "D:\Program Files\Everything\es.exe" -exit`；调试可绕过包装器直调 es（不刷新活动时间）。

   ```powershell
   # 统一入口（参数与 es 原样透传；git-bash 同样以 powershell -File 调用）
   powershell -NoProfile -ExecutionPolicy Bypass -File "D:/Users/language_projects/.agents/skills/sh-everything-search/scripts/es_query.ps1" -n 30 "report*.xlsx"

   # 自动退任务查看 / 移除；闲置时长改 scripts/idle_exit.ps1 的 $idleMinutes（默认 15）
   Get-ScheduledTask -TaskName sh-everything-idle-exit | Select-Object State
   # Unregister-ScheduledTask -TaskName sh-everything-idle-exit -Confirm:$false
   ```

3. 编码：优先 `-export-json` 落盘再读（UTF-8）；PS 5.1 直接抓 stdout 中文可能乱码。

## 命令速查（本机实测）

下列速查用原始 es 写法（便于阅读语法）；**日常执行请走包装器**（见上节），参数完全相同——Everything 闲置退出后，直连 es 会报 `Error 8: IPC not found`。

```powershell
$ES = "D:\Program Files\Everything\es.exe"          # 仅调试直连用；git bash: "/d/Program Files/Everything/es.exe"

# 基础：-n 封顶结果数；-path 限定目录；盘根必须写 'D:\'（带引号）
& $ES -n 30 report*.xlsx
& $ES -n 20 -path "D:\Users\language_projects" ext:toml
& $ES -n 20 -path 'D:\' ext:go

# 多条件：每个条件一个独立参数（空格分隔=AND），先 count 再取数
& $ES -no-digit-grouping -get-result-count dm:today ext:log        # 793（正确写法）
& $ES -n 20 -sort size-descending size:>500mb ext:zip
& $ES -n 20 -sort date-modified-descending size:>100mb dm:today
& $ES -n 30 ext:psd 'dm:2026-10-01..2026-10-07'                    # 范围宏同样是独立参数
```

### 搜索语法（Everything 1.4）

| 目的 | 写法 |
|---|---|
| 通配 / 短语 | `report*.xlsx`；短语用引号：`"CLI 工具"` |
| 多扩展名 | `ext:go;md` |
| 大小 | `size:>1gb`、`size:1mb..100mb` |
| 修改时间 | `dm:today`、`dm:thisweek`、`dm:2026-10-01..2026-10-07` |
| 最近变更 | `rc:today` |
| 正则 | `-r "claude\.json$"`（默认忽略大小写；`-i` 区分大小写） |
| 组合 | 独立参数=AND、`\|`=OR（如 `ext:log\|ext:tmp`）、`!词`=NOT（如 `!node_modules`） |

### 统计与导出

```powershell
& $ES -no-digit-grouping -get-result-count size:>1gb                # 宽查询先数，避免灌上下文
& $ES -no-digit-grouping -get-total-size -path 'D:\Users\language_projects' ext:md
& $ES -export-json "$env:TEMP\es-export.json" -n 2000 -path 'D:\' ext:log
```

## 硬规则

1. **多条件写成独立参数，绝不把整串表达式包进一对引号**——引号会让 es 把它当字面短语检索，实测直接归零：`dm:today ext:log` = 793，而 `"dm:today ext:log"` = 0。引号只用于真正的短语（如 `"CLI 工具"`）；单个 token（`ext:go`、`report*.xlsx`）加不加引号都一样。
2. **目录范围一律用 `-path` 选项**：本机是 Everything 1.4 引擎，不支持 1.5 的 `path:` 语法（会静默返回 0）；盘根写作 `'D:\'`，裸 `D:` 会被解析为"该盘当前目录"。
3. **避开实测卡死/失效的语法**：`dc:`（创建时间）、`da:`（访问时间）宏会让 es 长时间无响应（>20s），时间筛选只用 `dm:`/`rc:`；属性开关 `/ad`、`/a-d` 返回 0（不可用）；`-get-folder-size` 报 IPC 错误（需 Everything 1.5）。
4. **宽查询先 count 再取数**：预计 >100 条时先 `-get-result-count`；展示用 `-n` 限样（默认 ≤30）或导出后脚本筛选；聚合/去重/统计写一次性脚本处理导出文件（不要把原始清单灌进上下文）。
5. 只读定位：本 skill 不执行删除/移动/改名，找到后交给常规流程并让用户确认。
6. 索引有秒级延迟：刚创建/改名的文件可能查不到，用 rg/glob 兜底。

## 常见配方

```powershell
# 全盘找大文件（清理候选）
& $ES -no-digit-grouping -n 50 -sort size-descending size:>1gb

# 最近一天改动过的大文件（独立参数）
& $ES -n 50 -sort date-modified-descending size:>100mb dm:today

# 忘记放哪的文件（跨盘全盘）
& $ES -n 30 report*.xlsx

# 某类文件全盘计数（先数，不拉清单）
& $ES -no-digit-grouping -get-result-count ext:psd

# 排除干扰目录
& $ES -no-digit-grouping -get-result-count -path 'D:\Users\language_projects' ext:md '!node_modules'

# 导出清单给脚本聚合（UTF-8 JSON，用完删临时文件）
& $ES -export-json "$env:TEMP\es-export.json" -path 'D:\' ext:log
```

## 环境事实（2026-10-07 实测）

- Everything 1.4.1.1032：索引进程内存 ~430~475MB，索引 5,141,865 条，覆盖 C:/D:；Everything Service ~3MB 常驻。
- 按需模式实测：`-startup` 冷启动→可查询 2.2s（无窗口）；`es -exit` 退出释放内存并自动存索引库，耗时 2.3s。
- es 1.1.0.37：典型查询 0.3~0.8s；`dm:thisweek` 全盘约 64 万条（宽查询务必先 count）；不加 `-n` 默认输出全部结果（无内置上限）。
- `-export-json` 输出为 JSON 数组（`filename` 字段），中文路径正常。
- 包装器 `scripts/es_query.ps1`：冷启动+查询整体 ~2.9s（含 Everything 就绪 ~2.2s）；已在运行时无额外开销。
- 自动退：计划任务 `sh-everything-idle-exit` 隐藏运行、每 5 分钟检查、闲置 15 分钟退出（实例启动时间晚于活动记录 → 视为用户手动启动，不退出）。
