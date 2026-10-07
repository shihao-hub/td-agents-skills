# 为什么 book-to-skill 不入库、且不能跑 npx skills add/update

## npx 会删目录（最致命）

`skills` CLI（1.7.0）安装/更新目标目录的方式是**先删后拷**：
源码路径 `installSkillForAgent` → `cleanAndCreateDirectory`（cli.mjs:2326）；
update 本质是重新 spawn `add`（cli.mjs:7461）。

只要 book-to-skill 还在 `~/.agents/.skill-lock.json` 里，
为**任何别的 skill** 跑一次无参数 `npx skills update` 都会命中它——
整个目录连内嵌 `.venv`（106MB）一起被抹掉。所以：

1. 永远不对它跑 `npx skills add` / `npx skills update`；
2. 它的条目已从 `~/.agents/.skill-lock.json` 摘除
   （备份：`~/.agents/.skill-lock.json.bak-before-booktoskill-removal`）；
3. 更新只走 `cd ~/.agents/skills/book-to-skill && git pull`（不动未跟踪的 .venv）。

## 为什么不入 git 仓库（`~/.agents/skills`）

三个独立理由，任一都足够：

1. **嵌套 git 仓库**：直接提交会变成只有 commit 指针的 embedded repository，
   内容拿不到，还污染 `git status` 与子模块语义。
   → 外层 `.git/info/exclude` 加 `/book-to-skill/`。
2. **106MB 的 .venv 是运行环境不是源码**。
   → 内层 `.git/info/exclude` 加 `/.venv/`（及本机笔记 `ENVIRONMENT-SETUP.local.md`）。
3. **即使不删目录，npx 安装路径也无法自包含**：venv 若放 skill 外面（`~/.venvs/`），
   换机要装两处；放里面则活不过 update。git clone + 内嵌 venv 是唯一自包含解，
   代价就是上面两条铁律。

## 历史取舍表

| 方案 | 结论 |
|---|---|
| `.venv` 放 skill 目录 + npx 安装 | 否决：update 先删目录，venv 活不过一次更新 |
| venv 放 `~/.venvs/` + npx 安装 | 曾用；update 安全但换机装两处，自包含差 |
| **git clone + 内嵌 .venv（现役）** | 自包含，git pull 安全；代价：永不 npx update |
| 提交为 submodule | 可选但没必要：上游本来公开，指针意义不大 |

## PYTHON_BIN 正斜杠的原因

Git Bash 的 MSYS 路径转换会改写含反斜杠的路径，导致 `command -v "$PYTHON_BIN"`
失败，skill 静默退回**没装任何包的 MSYS2 python**（PEP 668 环境，无 pip）——
不报错，只是抽取质量莫名变差。正斜杠 `C:/Users/.../python.exe` 两侧都解析正常。
