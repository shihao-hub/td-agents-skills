# 02-Windows下Git变基PermissionDenied文件锁排障与Abort安全恢复

## 一、真实报错现象

在 Windows 环境下使用 Git 执行变基（`git rebase -i`）或通过 GUI 工具（Sublime Merge / VS Code / Cursor）执行 Squash、变基重排时，常遇到如下黄色弹窗或终端红字：

```text
failed: Edit Commit History
error: cannot update the ref 'HEAD': unable to append to 'D:/Users/.../.git/.../logs/HEAD': Permission denied
hint: Could not execute the todo command
hint:    pick <commit-hash>
hint: It has been rescheduled; To edit the command before continuing, please edit the todo list first:
hint:    git rebase --edit-todo
hint:    git rebase --continue
```

同时，客户端会显示：
- 当前处于 **`Rebase`** 状态；
- HEAD 停留在某个历史基底上（例如 `onto <hash>`）；
- 暂存区里多出了一批 **`Staged Files`**（原本属于该提交的文件被解压在暂存区）。

---

## 二、底层根本原因剖析

### 1. Windows 的独占文件句柄锁（Mandatory File Locking）
与 Linux/macOS 的文件系统不同，Windows 对正在被进程打开的文件采用强制独占锁定策略：
- 当 Git 准备将新生成的 Commit 写入引用日志（`logs/HEAD`）的一瞬间；
- 如果刚好有其他后台进程（例如：本项目的常驻后台守护服务 `python`/`zedhub serve`、IDE 的文件索引器、或是 Windows Defender 杀毒引擎的后台实时扫描）以只读方式打开了该文件；
- Git 的底层写入操作就会立即被 Windows 内核拒绝，抛出 **`Permission denied`**。

### 2. Git 的安全保护机制：为什么会停在中间状态？
Git 在变基过程中遵循“**宁可挂起、绝不丢代码**”的铁律：
- 它已经成功解压并应用了代码改动（因此文件变成了 `Staged Files`）；
- 但在最后一步写入引用时失败；
- 此时 Git 绝不会把改动扔掉，而是直接挂起变基，等待人工介入。

---

## 三、安全抢救与恢复 SOP（两条路径）

### 路径 A：一键安全回滚（推荐，100% 恢复如初）

如果你想退出当前卡死的变基，回到最初安稳的状态，切忌盲目乱删文件，按以下原子化步骤操作：

#### 步骤 1：确保工作区安全（防止 reset 报错）
如果终端直接执行 `git rebase --abort` 提示：
`error: The following untracked working tree files would be overwritten by reset...`
这是因为工作区有新增的新文件未被追踪，Git 为了防止覆盖它们而拒绝中止。

**正确的解决命令**：
```powershell
# 1. 先把所有改动和新增文件收纳进暂存区，告诉 Git 这些我们都认账
git add .

# 2. 安全中止变基，Git 会毫发无损地回滚到变基前的状态
git rebase --abort
```

#### 步骤 2：验证分支恢复
```powershell
git status
git log -n 5 --oneline
```
此时仓库会完全恢复到变基前的最新 commit，所有历史完好无损。

---

### 路径 B：释放文件锁并继续变基（继续执行）

如果你坚持要把变基走完：

1. **查杀占用进程**：
   在 PowerShell 中检查是否有正在运行的常驻后台服务或相关 Python 实例：
   ```powershell
   Get-Process -Name "*zedhub*", "*python*" -ErrorAction SilentlyContinue | Select-Object Id, ProcessName
   ```
   终止无关的后台占用服务或临时关闭杀毒软件。
2. **继续变基流程**：
   ```powershell
   git rebase --continue
   ```
   若提示暂存区有残留，按照提示完成提交或清理 todo 列表后继续。
