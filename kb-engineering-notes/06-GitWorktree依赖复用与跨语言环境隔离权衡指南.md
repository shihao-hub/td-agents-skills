---
name: kb-git-worktree-deps
description: Git Worktree 隔离开发时的依赖复用权衡：第三方依赖可共享，而项目自身状态（editable `.pth` 映射、`.bin` 脚本、增量编译锁）严禁共享；含 WinError 32 排他锁、环境漂移与 Python/TS/Go/Rust 跨生态规避策略。当纠结 Worktree 要不要软链接 `.venv`/`node_modules`/`target`、或遇到两端环境互相踩踏时查阅本条目。
---

# 06-GitWorktree依赖复用与跨语言(Python/TS/Go/Rust)环境隔离权衡指南

> **归档位置**：`kb-engineering-notes/06-GitWorktree依赖复用与跨语言(Python/TS/Go/Rust)环境隔离权衡指南.md`  
> **实战源起**：zedhub（多 Agent 会话正文气泡提取与 Worktree 独立验证）  
> **核心议题**：Git Worktree 下的依赖共享/软链接可行性、两端冲突规避与跨生态工程实践

---

## 一、现象与核心痛点直击

Git Worktree 允许在同一个 Git 仓库下同时检出多个分支到不同的物理工作目录。常用于：
- 主项目正在执行长任务/后台服务时，隔离出一个干净分支修 Bug 或开发新特性；
- 避免未提交改动在 `git stash` 过程中的脏状态混淆。

### 核心痛点
代码目录虽然通过 Worktree 隔离了，但**依赖环境（`.venv`、`node_modules`、`target/` 等）是空的**。
若每次开 Worktree 都要完整重新拉取、构建依赖，开发心智和时间成本高昂；如果直接粗暴建立软链接（NTFS Junction / Symlink）互指，又会引发严重的两边并发冲突、进程锁死与代码执行倒挂。

---

## 二、底层根因剖析：为什么直接软链接依赖目录是毒药？

在考虑软链接之前，必须将工程产物严格解构为两类资产：

```text
.venv / node_modules / target
├── 纯第三方依赖库 (无状态/只读资产)   ──> 适合共享：pydantic, lodash, crates
└── 项目自身状态与入口 (有状态/绑定源码) ──> 严禁共享：.pth 映射, .bin 脚本, 增量编译锁
```

### 1. 致命伤：Editable Install（可编辑安装）的“指鹿为马”
在 Python（`pip install -e .`）、Node（`pnpm link`）等工程中，本地正在开发的项目几乎都是以“可编辑模式”挂载进依赖环境的。
- **根因**：以 Python 为例，主工程 `.venv\Lib\site-packages\` 下生成了 `__editable__.zedhub.pth`，**文件内部硬编码写死了主项目的绝对物理路径**（如 `D:\Users\language_projects\python_projects\zedhub\src`）。
- **灾难后果**：若把主工程的 `.venv` 软链接给 Worktree，你在 Worktree 里改了半天代码，运行和测试时，**解释器顺着 `.pth` 读到的依然是主项目的源码，根本不加载 Worktree 的修改**！
- 若在 Worktree 里重新执行 `pip install -e .`，主工程的 `.pth` 就会被反向覆盖成 Worktree 的路径，两边环境互相踩踏。

### 2. Windows 排他锁与并发写冲突（WinError 32）
- Windows 系统对正在运行的 `.exe`、`.dll`、`.pyd` 实施内核级强制排他锁。
- 若主项目的服务（如 `zedhub.exe`）正在运行，你在 Worktree 里执行任何涉及 `.venv` 写入或更新的命令，都会抛出：
  ```text
  PermissionError: [WinError 32] 另一个程序正在使用此文件，进程无法访问。
  ```
- 此外，并发生成 `__pycache__` 或编译缓存会导致字节码损坏与死锁。

### 3. 依赖分叉与环境漂移（Dependency Drift）
若在 Worktree 分支临时测试性地安装了一个新库，由于软链接共享，主工程的环境被静默篡改；当 Worktree 分支被丢弃或回退时，主工程残留一堆幽灵依赖。

---

## 三、跨语言全景工程实战与避坑 SOP

| 语言生态 | 直接软链接（Junction）可行性 | 核心风险与冲突点 | 最佳实践建议 |
| :--- | :--- | :--- | :--- |
| **Python** | ❌ **极度危险** | `__editable__.pth` 绑定主目录物理绝对路径，导致 Worktree **代码执行倒挂**；Windows 下并发跑服务会产生 `.exe/.pyd` 锁死冲突。 | **首选**：`uv` 现代 Hardlink 缓存（3-5s 完成全新独立隔离环境）；<br>**次选**：`--system-site-packages` 寄生继承模式；<br>**单测**：直接用内存变量 `$env:PYTHONPATH` 置顶 Worktree 源码。 |
| **TypeScript / Node** | ⚠️ **有条件可用** | `node_modules` 文件极其庞大；若两分支 `package.json` 不一致或有人在 Worktree 内 `install`，会直接反向破坏主工程。 | **首选**：使用 `pnpm`（基于全局 Store 内容寻址，本地链接秒级完成）；<br>**若是 npm**：仅在依赖版本完全冻结时才允许软链 `node_modules`。 |
| **Go** |  **天然无需软链** | 若开启 `vendor/` 模式互相软链，在分支重构时会引发校验和（checksum）不匹配。 | **开箱即用**：Go 依赖全部保存在全局只读的 `$GOPATH/pkg/mod`（`GOMODCACHE`），Worktree 编译天然命中全局缓存，零额外耗时。 |
| **Rust** | ❌ **绝不可软链** | **严禁软链 `target/` 目录**！Cargo 在增量构建时持有独占编译锁（`.cargo-lock`），跨分支共享必报死锁或诡异的链接期符号冲突。 | **正统解法**：保持各自独立的 `target/` 目录，通过全局 `sccache` 作为 `rustc-wrapper` 共享编译 Object 缓存。 |

---

## 四、Python 生态三种免重复构建的高级操作

### 路径 A：系统库继承模式（`--system-site-packages`，巨型依赖推荐）
在 Worktree 中建一个轻量虚拟环境，所有第三方包走只读借用，自身源码独立挂载：
```powershell
# 1. 坐在 worktree 目录里，借用主项目 python 快速生成继承型虚拟环境
& "主项目路径/.venv/Scripts/python.exe" -m venv --system-site-packages .venv

# 2. 仅安装当前项目的源码映射（耗时 0.2 秒，只写入独立 .pth，不重复拉取依赖）
.\.venv\Scripts\pip.exe install -e . --no-deps
```
- **优势**：0.5 秒完成，数 GB 依赖 0 磁盘增量，且入口与源码完全独立，不穿透主分支。

### 路径 B：`uv` 现代化硬链缓存（标准开发首选）
在工具链支持 `uv` 的场景下：
```powershell
uv venv
uv pip install -e .
```
- **原理**：`uv` 在全局维护内容寻址缓存（Hardlink），无需联网，5 秒内构建完全独立的隔离环境，从物理上杜绝冲突。

### 路径 C：运行时内存环境变量（`PYTHONPATH`，单测/探针专用）
若仅为了在 Worktree 中跑测试或临时验证几行改动，**甚至无需创建 `.venv`**：
```powershell
# 1. 临时指定 PYTHONPATH 强行置顶 Worktree 源码
$env:PYTHONPATH = "D:\Users\language_projects\python_projects-wt\zedhub\src"

# 2. 直接借用主项目的 pytest 运行
& "D:\Users\language_projects\python_projects\zedhub\.venv\Scripts\python.exe" -m pytest tests/

# 3. 验证完毕清空环境变量
$env:PYTHONPATH = $null
```
- **优势**：0 环境落盘，0 秒启动，验证完毕直接清理 Worktree，不留任何临时垃圾。

---

## 五、完整 Worktree 实战工作流与提交闭环 SOP

以本次 zedhub 接入 Antigravity 正文气泡为例，标准且受控的 Worktree 操作闭环如下：

```powershell
# 1. 创建干净的隔离 Worktree
cd d:\Users\language_projects\python_projects
git worktree add -b feat/agy-content-bubbles ../python_projects-wt-agy HEAD

# 2. 端口/进程占用排查（避免与主工程服务端口冲突）
Get-NetTCPConnection -LocalPort 8766 -ErrorAction SilentlyContinue | Select-Object LocalAddress, LocalPort, OwningProcess, State
# 如有占用，受控终止
Stop-Process -Id <PID> -Force

# 3. 在 Worktree 中开发并测试验证
cd d:\Users\language_projects\python_projects-wt-agy\zedhub
uv venv; uv pip install -e .
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\zedhub.exe serve

# 4. 在 Worktree 中原子提交代码
git add -A; git commit -m "zedhub:feat: 支持 Antigravity 会话正文气泡提取与加载"

# 5. 回到主项目合并，并通过 --amend 规范化顶层合并节点
cd d:\Users\language_projects\python_projects
git merge feat/agy-content-bubbles
git commit --amend -m "zedhub:feat: 合并 Antigravity 会话正文气泡提取与加载" -m "- 详细说明..."

# 6. 安全清理 Worktree 与临时特性分支
git worktree remove ../python_projects-wt-agy
git branch -d feat/agy-content-bubbles
```
