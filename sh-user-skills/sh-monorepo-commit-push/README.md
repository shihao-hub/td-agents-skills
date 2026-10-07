---
name: sh-monorepo-commit-push
description: Monorepo 与 git submodule 项目逐项审查、提交并推送。点名使用
---

# Monorepo 项目逐项提交与推送

按项目边界完成审查、commit 和 push。这个 skill 适用于父仓库、语言子仓库、子项目并存的 monorepo，核心目标是让每个逻辑项目拥有独立、可追溯、已推送的 commit，避免一次 `git add .` 把不同项目混在一起。

## 适用边界

- 用户明确要求把多个项目分别提交、逐项 push、整理提交历史时使用。
- 普通单仓库 Git 操作、rebase、cherry-pick 等不使用本 skill，交给通用 Git 流程。
- 用户没有明确授权的文件、项目、仓库或远端操作不处理；范围不清时先列出发现的范围并询问。
- 不因为“看起来像生成物”就删除用户文件。删除或清理未跟踪文件前，先按文件类型和项目规则确认；有疑问就保留并报告。

## 总体顺序

1. 读取仓库约定文件（`AGENTS.md`、`README.md`、贡献指南）和项目的真实验证命令。
2. 识别当前工作目录属于父仓库、子仓库还是具体项目；分别记录状态。
3. 盘点用户授权范围内的修改和未跟踪文件，按逻辑项目分类。
4. 排除运行时产物后，逐个审查项目并验证。
5. 在子仓库中一次只暂存一个逻辑项目，commit 后立即 push。
6. 所有子项目 push 成功后，回到父仓库更新子模块指针并单独 push。
7. 父仓库自身的修改继续按逻辑主题拆分，每个主题单独 commit、立即 push。
8. 最终检查所有仓库 clean、没有 ahead/behind、子模块指针一致。

不要把子项目源码提交到父仓库；父仓库只能记录子模块指针。不要在子仓库 commit 未经授权的其他项目改动。

## 阶段 1：建立安全基线

分别执行只读检查：

```powershell
cd <父仓库>
git status --short --branch
git submodule status
git log -5 --oneline --decorate

cd <子仓库>
git status --short --branch
git branch -vv
git remote -v
```

记录：

- 当前分支和远端跟踪关系；
- 已有但未 push 的 commit；
- 子模块是否 dirty、ahead 或落后；
- 用户明确授权的项目范围；
- 仓库约定要求的 commit message、构建和测试命令。

已有本地 commit 可以单独 push，但不能与后续工作区改动 amend、squash 或混合提交，除非用户明确要求改写历史。

## 阶段 2：识别并处理运行时产物

通常不应提交：

- `.venv/`、`venv/`、`__pycache__/`、`.pytest_cache/`；
- `dist/`、`build/`、覆盖率和工具缓存；
- 程序运行产生的 SQLite、JSON 数据库、锁文件、日志、会话文件；
- 项目约定明确排除的临时文件。

先查看项目 `.gitignore`、父仓库约定和文件来源。只清理明确属于运行时生成、且用户授权范围内的文件。保留源码、锁文件、必要示例资源和有意归档的数据。清理后再次检查：

```powershell
git status --short -uall
git diff --check
```

如果运行时产物已经被 Git 跟踪，不要直接删除并提交；先报告影响，并让用户确认是否需要 `git rm --cached` 或保留兼容迁移。

## 阶段 3：逐项目审查与验证

对每个项目单独处理，不跨项目批量暂存。

审查至少包括：

- 入口、核心业务逻辑和异常处理；
- 数据路径是否符合项目约定；
- CLI、MCP、schema 或 API 契约（如果项目有）；
- 依赖声明和锁文件是否匹配；
- 项目文档是否描述真实行为；
- 是否存在明显的连接、资源、并发或错误报告问题。

只修复用户授权范围内、证据充分的问题；不要为了“顺手整理”修改其他项目。使用项目声明的真实命令验证，例如 `uv run pytest`、`go test ./...`、`cargo test` 或 `npm test`。如果没有测试，不要把“没有测试”说成“测试通过”，应记录为“未配置测试”并执行可用的编译、schema、help 或 smoke check。

每个项目完成后，先确认它独立可提交，再进入下一个项目。验证失败时停在当前项目，不继续批量提交。

## 阶段 4：子仓库单项目 commit + push

在子仓库内只暂存当前项目：

```powershell
cd <子仓库>
git add -- <项目相对路径>
git diff --cached --check
git diff --cached --name-status
git diff --cached --stat
```

人工确认暂存清单只包含当前项目后提交：

```powershell
git commit -m "<project>:<type>: <中文主题>"
git push origin <branch>
git status --short --branch
git log -1 --oneline --decorate
```

子仓 monorepo 的 commit message 遵循项目约定，通常为：

```text
<project>:<type>: <中文描述>
```

一个 commit 应表达一个逻辑项目或一个项目内不可分割的修复。不要使用 `git add .`、`git commit -am` 来代替范围确认。push 被拒绝、远端分支分叉或发现其他人新提交时，停止并报告，不自动 force push。

## 阶段 5：父仓库提交

确认所有相关子仓库的 commit 已经推送成功后，再更新父仓库指针：

```powershell
cd <父仓库>
git submodule update --remote <子模块路径>
git add --force <子模块路径>
git diff --cached --submodule=short
git commit -m "chore: 更新 <子模块> 子模块指针"
git push origin <branch>
```

`ignore = all` 的子模块必须使用 `git add --force`。父仓库只提交指针，不要递归暂存子仓库源码。若父仓库还有自身文件改动，按主题逐组暂存，例如脚本、配置、指南、研究文档分别处理；每组 commit 后立即 push。

如果子仓库 push 成功但父仓库指针更新失败，保留子仓库已推送状态，修复父仓库提交问题，不回滚已经成功的子仓库 commit。

## 阶段 6：最终检查与汇报

所有提交完成后分别执行：

```powershell
cd <父仓库>
git status --short --branch
git log origin/<branch>..HEAD --oneline
git submodule status

git diff --check

cd <子仓库>
git status --short --branch
git log origin/<branch>..HEAD --oneline
git diff --check
```

最终汇报必须列出：

- 每个项目的 commit 哈希、commit message 和 push 结果；
- 父仓库每个主题 commit 及子模块指针 commit；
- 执行过的验证命令和结果；
- 被排除或保留的运行时产物；
- 未完成项、远端异常、测试缺失或治理工具阻塞。

只有父仓库和相关子仓库均无未提交、未 push 的授权范围内改动时，才能称为“已完成”。如果存在 AOCI、权限、审批或其他治理工具阻塞，明确报告阻塞状态，不用普通 Git 命令绕过治理。

## Commit 命令示例

子仓库项目：

```powershell
cd D:\Users\language_projects\python_projects
git add -- douyinnotify
git diff --cached --check
git commit -m "douyinnotify:fix: 修正检查结果统计"
git push origin main
```

父仓库指针：

```powershell
cd D:\Users\language_projects
git add --force python_projects
git commit -m "chore: 更新 python_projects 子模块指针"
git push origin main
```

示例中的路径、项目名、分支和 message 仅作格式示范，实际执行前必须以当前仓库状态和约定为准。
