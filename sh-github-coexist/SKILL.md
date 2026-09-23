---
name: sh-github-coexist
description: 装机：个人 GitHub 与公司 GitLab 共存，SSH key+includeIf 身份自动切换+批量推仓库。点名使用
---

# GitHub 与公司 GitLab 共存（Windows 实战版）

## 设计原理（先读懂再动手）

- **凭据层互不干扰**：公司 GitLab 走 HTTPS + Git Credential Manager（凭据按域名存储），个人 GitHub 走专用 SSH key。两条通道完全独立，加 GitHub 不需要动 GitLab 任何配置。
- **身份层按 remote URL 切换，不按目录**：commit 身份用 git 的 `includeIf hasconfig:remote.*.url`（需 git >= 2.36）——任意目录下，只要仓库 remote 指向 github.com，就自动加载个人身份；其他仓库保持全局默认（公司身份）。用户明确不喜欢固定目录方案，"哪个目录要提交就用哪个"。
- **边界情况**：本地 `git init` 且还没配 remote 的仓库会落到全局默认身份；`git remote add origin` 后自动切换，无需手动干预。

## 身份参数（全部是占位符，使用前逐项向用户确认，禁止假设或沿用旧机器值）

| 项 | 占位符 | 获取方式 |
|---|---|---|
| GitHub 用户名 | `<github-user>` | 问用户，或 `gh auth status` |
| 个人邮箱 | `<personal-email>` | 问用户（GitHub 绑定邮箱） |
| 公司身份 | `<work-user>` / `<work-email>` | `git config --global user.name/email` |
| 公司 GitLab | `<gitlab-host>`（HTTPS + GCM） | `git remote -v` 看现有仓库 |
| 远程仓库名前缀 | `<repo-prefix>` | 问用户 |
| SSH key | ~/.ssh/id_ed25519_github | GitHub 专用，与公司通道隔离 |

## 阶段 0：勘查现状（动任何东西之前）

```powershell
Get-ChildItem -Force ~/.ssh                    # 是否已有 key 可复用
git config --global --list                     # 现有身份与凭据方式
git config --global credential.helper          # manager = GCM，HTTPS 凭据按域名隔离
git --version                                  # 必须 >= 2.36（includeIf hasconfig）
```

判断：GitLab 走 HTTPS + GCM 则零冲突；git 版本过低则先升级（winget install Git.Git）。

## 阶段 1：GitHub 专用 SSH key

```powershell
# PowerShell 5.1 下空口令必须写 -N '""'（单引号包双引号）；
# 直接写 -N "" 空串参数会被 PowerShell 吞掉，退化为交互式卡死
ssh-keygen -t ed25519 -C "<personal-email>" -f "$HOME\.ssh\id_ed25519_github" -N '""'
```

新建（或追加到）`~/.ssh/config`——只影响 github.com，不碰其他 Host：

```
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_github
    IdentitiesOnly yes
```

`IdentitiesOnly yes` 的原因：防止 ssh 依次尝试所有默认 key，触发 GitHub "too many authentication failures"。

**必须由用户手动完成的一步**：打印公钥让用户复制，去 https://github.com/settings/keys → New SSH key 粘贴保存（agent 无法代替，需要登录用户的 GitHub 账号）：

```powershell
Get-Content "$HOME\.ssh\id_ed25519_github.pub"
```

连通性验证（结果判读）：

```powershell
ssh -T git@github.com
# Hi <github-user>! You've successfully authenticated  → 成功
# Permission denied (publickey)                    → 网络通，公钥还没加/加错
# 超时                                             → 直连失败，兜底：config 里改
#   HostName ssh.github.com / Port 443，再不行问代理
```

## 阶段 2：身份按 remote URL 自动切换

新建 `~/.gitconfig-github`：

```
[user]
	name = <github-user>
	email = <personal-email>
```

全局 `~/.gitconfig` 追加（三条 pattern 覆盖 ssh scp 风格 + https 风格；`**` 可跨斜杠）：

```
[includeIf "hasconfig:remote.*.url:git@github.com:**"]
	path = ~/.gitconfig-github
[includeIf "hasconfig:remote.*.url:git@github.com:*/**"]
	path = ~/.gitconfig-github
[includeIf "hasconfig:remote.*.url:https://github.com/**"]
	path = ~/.gitconfig-github
```

验证：随便 clone 一个 GitHub 公开仓库到临时目录，`git config user.name/email` 应为个人身份；`git config --global user.email` 仍是公司身份。验证完删掉临时仓库。

## 阶段 3：gh CLI（装 + 登录）

```powershell
winget install --id GitHub.cli --accept-source-agreements --accept-package-agreements --silent
# 已开着的会话看不到新 PATH，每次新 shell 先刷新：
$env:Path = [System.Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path','User')
```

**登录是本流程最大的坑，规则只有一条：让用户自己开一个新 PowerShell 窗口跑**

```powershell
gh auth login -h github.com -p ssh --skip-ssh-key -w
```

为什么不给 agent 代跑：设备码流程需要进程持续轮询等用户授权。agent 用 `Start-Job`/`Start-Process` 挂后台登录进程，会随 bash 会话结束或超时被连带杀掉——用户在浏览器输完码、本地进程却已死，token 永远落不了地（本机实测连续失败 3 次，用户被迫"登录好多次"）。用户在自己终端跑则一次成功。

用户跑完后 agent 验证：

```powershell
gh auth status   # 应显示 Logged in as <github-user>，scopes 含 repo
```

## 阶段 4：本地仓库批量上 GitHub

**先盘点**每个仓库的分支、脏文件数、历史身份（决定要不要改写）：

```powershell
foreach ($d in '<repo-1>','<repo-2>') {
  $p = "<项目父目录>\$d"
  git -C $p branch --show-current
  (git -C $p status --porcelain | Measure-Object).Count
  git -C $p log --format='%an %ae' | Sort-Object -Unique
}
```

**历史身份改写**（历史是公司邮箱且仓库要公开时必须做，否则泄露公司域名；改写会变更所有 commit hash，纯本地仓库无副作用）：

```powershell
uv tool install git-filter-repo    # 本机用 uv；也可 pip install git-filter-repo
```

mailmap 文件（例如 `%TEMP%\rewrite.mailmap`，格式：`新名 <新邮箱> <旧邮箱>`）：

```
<github-user> <<personal-email>> <<work-email>>
```

为什么用 mailmap 而不是 --name-callback：PowerShell 会剥掉传给原生命令的双引号，`'return b"x"'` 回调到达 filter-repo 时已残缺并静默失败（本机实测：报错被输出过滤吞掉，改写根本没发生还显示正常）。mailmap 文件完全绕开引号问题，且同时改 author + committer。

```powershell
# 脏仓库三步走（stash -u 连未跟踪文件一起保护，改完恢复原状）：
git -C $p stash push -u -m "pre-rewrite"
git -C $p filter-repo --force --mailmap <mailmap路径>
git -C $p stash pop
# 干净仓库跳过 stash 直接 filter-repo
# 验证：git log --format='%an <%ae> | %cn <%ce>' 应全为个人身份
```

**批量创建远程仓库 + 推送**（可见性先问用户，默认 Public 但历史必须先改写）：

```powershell
gh repo create "<github-user>/<repo-prefix>$d" --public --source "<项目父目录>\$d" --remote origin --push
# --source 自动添加 origin(ssh) 并推送当前分支、建好跟踪关系
# 之后用户日常裸 git push 即可；新分支首次要 git push -u origin <分支>
```

**最终验证**（每个仓库）：

```powershell
git -C $p remote get-url origin        # git@github.com:<github-user>/<repo-prefix>-xxx.git
git -C $p config user.email            # 个人邮箱（includeIf 已生效）
git -C $p status -sb                   # ## main...origin/main 无 ahead/behind
```

未提交文件按用户要求保留本地不 commit——push 只推已提交内容，提前跟用户说清楚。

## 踩坑速查（Windows/PowerShell，都是本机真金白银换来的）

| 坑 | 规避 |
|---|---|
| PowerShell 5.1 吞空字符串参数 | `-N ""`→`-N '""'`、`-P ""`→`-P '""'` |
| filter-repo 回调里的双引号被剥 | 用 mailmap 文件，别用回调 |
| agent 后台跑 gh 设备码登录被会话回收杀掉 | 坚决让用户自己开新终端跑 |
| 新装的 gh/git-filter-repo 在当前 shell 找不到 | 每个新 bash 调用先刷新 PATH（见阶段 3） |
| bash 调用超时会连带杀 Start-Process 的子进程 | 后台长任务不要和可能超时的调用混在一起；能拆小命令就拆 |
| filter-branch 拒绝脏工作树 | 改用 filter-repo --force + stash 往返 |
| 一个 bash 调用里输出过滤（Select-String）可能吞掉报错 | 排障时先看完整输出再过滤 |
