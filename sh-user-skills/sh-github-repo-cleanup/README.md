---
name: sh-github-repo-cleanup
description: GitHub 仓库大扫除：审计→fork 转 Star→mirror 备份→批量删除/归档。点名使用
---

# GitHub 账号仓库大扫除

一套经过实战验证的完整流程：135 个仓库清理到 5 个（64 个 fork 转 Star 收藏后删除、70 个仓库 mirror 备份后删除），零误删。

## 核心原则：为什么每一步都要这么谨慎

- **删除不可逆**（fork 删除连坐、历史消失），而 Star/归档/备份全部可逆。所以顺序永远是：快照 → 收藏（并核验）→ 备份（并验证）→ 删除 → 归档 → 终检。
- **先分类后动手**：fork 里可能藏着用户自己的提交（ahead_by>0），删之前必须逐一判定"纯收藏型"。
- **白名单优先**：`<user>.github.io`（GitHub Pages 主页，删除会下线站点）、用户点名保留的仓库，在任何批量操作前排除。
- **破坏性操作前必须逐名单给用户确认**，且本地已有快照兜底。

## 阶段 0：前置检查

```
gh auth status
```

- 未登录 → 让用户在**本机任意终端**跑 `gh auth login --scopes delete_repo`（默认 scope 不含 delete_repo，后面删除仓库必须要）。
- 登录成功的唯一标志：`✓ Logged in as <用户名>`。用户说"我登录了"但 `gh auth status` 仍报未登录 → 授权流程没走完，最常见断点是浏览器设备授权页没点最后的 Authorize 按钮，或中途关了终端。排障详见 `references/lists-and-device-auth.md` 的"授权不生效排障"一节。

## 阶段 1：审计（全程只读）

所有命令在 PowerShell 5.1 下必须以这行开头（否则中文描述全是乱码）：

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

### 1.1 拉取全部仓库元数据

```powershell
gh repo list --limit 1000 --json nameWithOwner,isFork,isArchived,isPrivate,pushedAt,stargazerCount,forkCount,isEmpty,description
```

注意：输出大且含中文时**不要**在 PS 里 `ConvertFrom-Json`（大数组会崩，见 references），让它原样输出后人工/正则分析，或用 `cmd /c "gh repo list ... > snapshot.json"` 重定向到文件留快照。

### 1.2 判定纯收藏型 fork（两道检查）

对每个 fork：

**① compare API 查超前提交**（是否有用户自己的 commit）：

```powershell
# 先拿上游与默认分支（--jq 表达式绝不能含空格和双引号，PS 5.1 会拆碎参数）
$info = gh api "repos/<user>/<fork>" --jq '[.parent.full_name,.parent.default_branch,.default_branch]|@csv'
$p = $info.Replace('"','').Split(',')   # 不要用 Split('","')，那是 char[] 语义！
# 再比较
gh api "repos/$($p[0])/compare/$($p[1])...<user>:$($p[2])" --jq '[.ahead_by,.behind_by,.status]|@csv'
```

`ahead_by=0` → 无自己的提交。parent 为 null → 上游已删（ORPHAN），需单独问用户。

**② 分支数检查**（防往非默认分支推过提交）：

```powershell
gh api "repos/<user>/<fork>/branches" --jq 'length'
```

两道都过（ahead_by=0 且单分支）才是**纯收藏型 fork**。

### 1.3 分类矩阵

| 分类 | 判定 | 默认处置（向用户推荐） |
|---|---|---|
| A 纯收藏型 fork | ahead_by=0 且单分支 | Star 上游 → 删除 |
| B 有改动 fork | ahead_by>0 | 保留，列给用户复核 |
| C 活跃原创 | 近 6 个月有 push | 保留 |
| D 沉寂原创 | >12 个月无 push | 归档（或备份后删除） |
| E 空仓库 | isEmpty=true | 归档或删除（无历史可保） |
| 特殊 | `<user>.github.io` | 默认保留，删除会让 Pages 站点下线 |

## 阶段 2：向用户确认处置方案

用结构化提问（question 工具）逐项确认：fork 是否全删（含被别人 star 过的要单独提醒）、空仓库归档还是删、归档阈值、白名单、List 名称。**不要替用户做主**，但每项给推荐项。

## 阶段 3：本地快照（一切破坏性操作的前提）

目录：`%USERPROFILE%\github-cleanup-<YYMMDD>\`，至少三份文件：

1. `all_repos_snapshot.json` —— 操作前完整元数据：
   ```powershell
   cmd /c "gh repo list --limit 1000 --json ... > %USERPROFILE%\github-cleanup-<YYMMDD>\all_repos_snapshot.json"
   ```
   （用 cmd /c 重定向是为了绕开 PS 管道对 UTF-8 的解码破坏）
2. `fork_upstream_map.md` —— 每个 fork → 上游仓库 + compare 状态的映射表（收藏依据 + 恢复依据）
3. `action_plan.md` —— 决策记录 + 删除/归档名单 + 预期终态 + 执行后追加记录（每轮操作完回写）

## 阶段 4：收藏（Star + 核验）

```powershell
gh api -X PUT "user/starred/<owner>/<repo>"    # 204，无输出
```

批量后**必须核验**（star 失败就不许删对应 fork）：

```powershell
$starred = gh api user/starred --paginate --jq '.[].full_name'
$missing = @($parents | Where-Object { $starred -notcontains $_ })   # 期望 0
```

### 可选：创建 GitHub List 归档

需要 `user` scope，gh 现有 token 通常没有，且 `gh auth refresh` 交互流程极易断。**推荐直接自驱动 OAuth 设备流**（用 gh 的公开 client_id，无需 gh 参与），拿 token 后走 GraphQL `createUserList` + `updateUserListsForItem`。完整流程、限流规避、UI 灰度问题见 `references/lists-and-device-auth.md`。

## 阶段 5：备份（mirror）与删除/归档

### 5.1 mirror 备份（删除任何"有内容"的仓库前必做）

```powershell
git clone --mirror "https://github.com/<user>/<repo>.git" "<备份目录>\<repo>.git"
```

备份后**验证**：bare 且至少有一个 ref 才算有效：

```powershell
$bare = git -C "<dir>" rev-parse --is-bare-repository      # 期望 true
$refs = git -C "<dir>" for-each-ref --count=1 --format='%(refname)'  # 期望非空
```

空仓库（isEmpty=true）没有 ref 属正常，不算备份失败——直接靠名字核对即可。

### 5.2 删除与归档

```powershell
gh repo delete "<user>/<repo>" --yes     # 需 delete_repo scope
gh repo archive "<user>/<repo>" --yes    # 可逆，随时 Settings 里 Undo
```

循环执行时统计成功/失败数并输出失败名单，**任何失败都不静默跳过**。

### 5.3 恢复路径（写进 action_plan.md 告知用户）

mirrors 目录下任意仓库可完整还原：新建空仓库 → `git push --mirror <新仓库URL>`。

## 阶段 6：终检

```powershell
gh repo list --limit 1000 --json nameWithOwner,isFork,isArchived
```

核对：总数 = 预期、fork 数 = 预期（通常 0）、归档数 = 预期、活跃清单 = 白名单。多出来的仓库先查创建时间（可能是审计后用户新建的，不是误操作）。

## 常见坑速查

| 症状 | 原因与解法 |
|---|---|
| `gh: accepts 1 arg(s), received 2` | PS 5.1 把含空格/双引号的 `--jq` 参数拆碎了。改用无空格无引号表达式：`'[.a,.b]|@csv'` |
| `ConvertFrom-Json` 报 MissingMethodException | PS 5.1 解析大数组的 bug。改用正则提取，或根本不在 PS 里解析 |
| `Split('","')` 拆出错位 | 它是 char[] 分割语义。用 `.Replace('"','').Split(',')` |
| PS 写的 JSON 文件 GraphQL 报错 | Set-Content 的 UTF8 带 BOM。用 `[IO.File]::WriteAllText($p, $s, (New-Object Text.UTF8Encoding($false)))` |
| gh/curl 间歇性 401/404 | 网络层抖动，不是凭据失效。重试同一条命令即可，别急着换 token |
| `repos/{x}` 查不到但仓库明明存在 | 同上，或已改名。用 `search/repositories?q=<名>` 定位 |
| gh auth 授权反复"不生效" | 见 `references/lists-and-device-auth.md` §1 |
| 设备流轮询返回 slow_down | 轮询过快被惩罚，interval 翻倍。放缓节奏（宁 20s 勿 5s） |
| 批量 GraphQL mutation 一半失败 | 撞限流点数。每请求 ≤40 个 mutation，或逐个 + 800ms 间隔 |
| 用户问 Top repositories 里为什么有别人的仓库 | 那是他贡献过（issue/PR 也算）的仓库，不是他的资产，无法也无需清理。验证：`gh api "search/issues?q=author:<user>+repo:<o>/<r>" --jq .total_count` |
| 用户在 github.com/stars 找不到 List | Lists Web UI 还在灰度。公开直链：`github.com/stars/<user>/lists/<slug>`（中文 slug 需 URL 编码） |

详细展开：PowerShell 兼容写法见 `references/powershell-quirks.md`；设备授权、Lists GraphQL、限流细节见 `references/lists-and-device-auth.md`。

## 追加轮次

清理往往分多轮（用户清完 fork 又想清活跃仓库）。每轮都：沿用同一个快照目录、在 `action_plan.md` 追加执行记录、重走"确认→备份→删除→终检"，白名单持续累积（如用户点名的 `td-*`、`github.io`）。
