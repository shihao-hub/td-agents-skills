---
name: kb-github-repo-cleanup-audit
description: GitHub 账号海量仓库大扫除审计与安全清理流水线：包含 gh CLI 授权、fork 判定与超前提交比对、mirror 本地备份、白名单保护与批量归档删除 SOP。清理与归档个人/组织仓库时查阅。
id: "087"
domain: git
scope: gh
type: flow
slug: repo_cleanup_audit
status: verified
created: "2026-09-22"
last_verified: "2026-10-22"
compatibility:
  os: ["windows"]
invocation:
  auto_trigger: true
---

# GitHub 仓库大扫除与审计清理流水线

> 本条目沉淀自单账号 130+ 仓库大扫除至核心资产的实战经验（60+ fork 转 Star 收藏后删除、70+ 仓库本地 mirror 备份后删除，0 误删）。

---

## 一、业务场景与安全基线原则

个人或团队在长期开发中常积累大量临时 fork、废弃实验项目或测试仓库。
- **不可逆操作红线**：删除仓库为不可逆操作（可能导致 Issue、PR 引用失效，fork 关系链断裂），而 Star、本地归档备份为安全可逆操作。
- **固定执行顺序铁律**：`全局元数据快照 → 判定纯收藏 fork → 转 Star 收藏 → 核心资产 mirror 本地备份 → 验证备份 → 破坏性删除确认 → 批量删除/归档 → 终检`。
- **绝对白名单保护**：`<username>.github.io`（GitHub Pages 主页）、包含活跃 Issue/PR 的项目、用户明确指定的活跃工作区，在任何脚本过滤前必须硬编码排除。

---

## 二、架构难点与终端踩坑防线

1. **GitHub CLI (gh) 权限作用域陷阱**：
   - 默认通过 `gh auth login` 获得的 OAuth Token **不具备**删除仓库权限；
   - 必须显式请求 `delete_repo` 作用域：`gh auth login --scopes delete_repo`。
2. **PowerShell 5.1 编码与 JSON 数组陷阱**：
   - 默认控制台编码会导致中文 repo 描述乱码，需显式声明：`[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`；
   - 仓库元数据列表超千条时，直接在终端管道调用 `ConvertFrom-Json` 极易由于内存缓冲区截断引发语法崩溃，必须走文件落盘快照或 Python 辅助解析；
   - `gh api --jq` 表达式严禁包含空格与未转义双引号，PowerShell 5.1 参数解析器会拆碎参数导致 400 报错。
3. **识别“纯收藏型 Fork”（防丢失自己的 Commit）**：
   - fork 仓库可能包含自己的独有提交（`ahead_by > 0`），绝对不能粗暴按 fork 标志直接删；
   - 必须调用 Compare API 校验 `ahead_by == 0`，且上游默认分支与当前分支 commit 完全一致。

---

## 三、标准大扫除执行流水线 SOP

### 阶段 0：权限确认
```powershell
# 检查是否具备 delete_repo 权限
gh auth status
# 若缺失删除权限，执行交互式提权授权：
gh auth refresh -h github.com -s delete_repo
```

### 阶段 1：全量元数据快照（全程只读）
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 导出全量仓库快照至本地 JSON
gh repo list --limit 2000 --json nameWithOwner,isFork,isArchived,isPrivate,pushedAt,stargazerCount,forkCount,isEmpty,description > repo_snapshot.json
```

### 阶段 2：判定并清理纯收藏型 Fork
通过 Python 脚本精确比对每一个 fork 仓库是否有个人超前提交：
```python
# 核心检测逻辑（伪代码/单文件脚本）：
# 对每个 isFork == True 的仓库：
# 1. gh api repos/<user>/<fork> 获取 parent.full_name 与 parent.default_branch
# 2. gh api repos/<parent>/compare/<parent_branch>...<user>:<fork_branch>
# 3. 只有当 ahead_by == 0 时，判定为纯收藏型
# 4. 执行 gh api -X PUT user/starred/<parent> 补加 Star
# 5. 用户复核清单后执行 gh repo delete <user>/<fork> --yes
```

### 阶段 3：废弃非 Fork 仓库的本地 Mirror 备份
在批量删除个人独立仓库前，必须对仓库进行裸克隆镜像（包含全部分支、tag与完整提交历史）：
```powershell
$backupRoot = "D:\GitBackups\$(Get-Date -Format 'yyyyMMdd')"
New-Item -ItemType Directory -Force -Path $backupRoot

# 对待删除仓库逐项 mirror 克隆
git clone --mirror "https://github.com/<user>/<repo>.git" "$backupRoot\<repo>.git"

# 校验备份完整性（检查 HEAD 与 refs）
Test-Path "$backupRoot\<repo>.git\HEAD"
```

### 阶段 4：批量删除与终检确认
```powershell
# 绝不在终端无脑遍历删除！每次删除前输出清单，等待人工确认
Get-Content -Path "pending_delete_repos.txt" | ForEach-Object {
    $repo = $_.Trim()
    if ($repo -and $repo -notlike "*github.io*") {
        Write-Host "正在删除: $repo" -ForegroundColor Red
        gh repo delete $repo --yes
    }
}
```

---

## 四、交付断言与结果验证

1. **终端复核**：`gh repo list <user> --limit 100`，确认仓库列表已降噪至预期核心资产；
2. **备份核查**：检查备份目录下的 `.git` 镜像是否可正常执行 `git log -1`，确保历史资产 100% 可重现。
