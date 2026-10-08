---
name: kb-git-rebase-rescheduled
description: 解析 Git 变基 `It has been rescheduled` 的重调度机制：todo 队列为何被塞回、重复 pick 与空提交怎么产生、`git-rebase-todo`/`done`/`onto` 状态文件语义，以及正确的恢复次序。当变基提示 rescheduled、todo 列表混乱、或 `--continue` 报暂存区冲突/空提交时查阅本条目。
---

# 03-Git变基Rescheduled队列挂起与暂存区冲突深度解析

## 一、什么是 Rescheduled（重调度）？

在执行 Git 交互式变基时，你可能会在错误提示的尾部看到这一行小字：

```text
hint: It has been rescheduled; To edit the command before continuing, please
hint: edit the todo list first:
hint:    git rebase --edit-todo
hint:    git rebase --continue
```

很多开发者对这一行提示不以为意，但它往往是导致后续变基“越理越乱、冲突不断”的罪魁祸首。

---

## 二、底层执行机制揭秘（`.git/rebase-merge/` 目录内部）

在变基进行时，Git 会在 `.git/rebase-merge/`（对于子模块则是 `.git/modules/<name>/rebase-merge/`）目录下维护数个状态文件：

1. **`git-rebase-todo`**：接下来要顺序执行的命令清单（如 `pick <hash>`, `squash <hash>`）；
2. **`done`**：记录当前已经成功完成的命令历史；
3. **`onto`**：变基所基于的父提交节点。

### 为什么会出现“重复 Pick”或“空提交”？

- 当 Git 顺序执行到 `pick A` 时，它会做两件事：
  1. 将 Commit A 的代码差异应用到工作区和暂存区；
  2. 提交并更新 `HEAD` 引用。
- 如果第 1 步成功了，但第 2 步因为 **Windows 文件锁（Permission denied）** 或系统故障失败了；
- Git 的容错策略是：**把 `pick A` 重新塞回 `git-rebase-todo` 待办队列的第一行（即 Rescheduled）**；
- **致命后果**：
  - 此时代码改动**已经在暂存区里了**；
  - 但 todo 列表里又保留了 `pick A`；
  - 如果你此时盲目执行 `git rebase --continue`，Git 会再次尝试去应用 Commit A，结果发现改动全在暂存区里了，从而报错：
    `error: you have staged changes in your working tree` 或 `The previous cherry-pick is now empty`！

---

## 三、排障与避坑标准原则

### 原则 1：一旦出现 Rescheduled，优先考虑安全 Abort

当你看到 `It has been rescheduled` 时，说明 Git 内部的状态机已经与实际工作区/暂存区脱节了：
- **强烈推荐**：不要试图手动修改 `git-rebase-todo` 修复；
- **正确做法**：直接先执行 `git add .` 将所有变动暂存，然后执行 `git rebase --abort`。
- 回到最初干净的提交树后，排查并解除文件锁占用，重新执行一次合并。因为在干净起点下，Git 不会产生任何状态残留。

### 原则 2：非要 Continue 时，先检查 Todo 与 Done

如果一定要原地继续：
1. 检查已完成与待办清单：
   ```powershell
   Get-Content .git/rebase-merge/done
   Get-Content .git/rebase-merge/git-rebase-todo
   ```
2. 如果发现同一个 commit 既在 `done` 记录里、又在 `todo` 第一行里，必须执行 `git rebase --edit-todo` 将那一行多余的重复 `pick` 删掉，然后再执行 `git rebase --continue`。
