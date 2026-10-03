# book-to-skill：安装方式与取舍记录

> 结论先行：**book-to-skill 故意不入本仓库**。它是独立 git clone，内嵌 `.venv`，
> 被本仓库通过 `.git/info/exclude` 整体排除。本文记录它是什么、怎么装的、为什么不提交，
> 以及换机后如何重建。

## 一、它是什么

[virgiliojr94/book-to-skill](https://github.com/virgiliojr94/book-to-skill)
（33k+ star，MIT）：把 PDF / EPUB / DOCX / MD / HTML / RTF 转成结构化 agent skill ——
产出 `SKILL.md`（心智模型+章节索引）+ 按需加载的分章文件 + 词汇表/模式/速查表，
官方实测比整本书灌上下文省 24–51 倍 token。不仅用于书，也可折叠 docs/、ADR、runbook。

## 二、本机安装现状（2026-10-03）

| 项 | 值 |
|---|---|
| 真身 | `~/.agents/skills/book-to-skill`（独立 git clone，`master` @ `c108d25`）|
| Python 环境 | 内嵌 `~/.agents/skills/book-to-skill/.venv`（106 MB，base=anaconda 3.12.7）|
| 解释器切换 | User 级环境变量 `PYTHON_BIN = C:/Users/29580/.agents/skills/book-to-skill/.venv/Scripts/python.exe` |
| 本仓库跟踪状态 | **未跟踪、全历史 0 提交**（`.git/info/exclude` 排除 `/book-to-skill/`）|
| 可见性 | 1 份真身 + 16 个链接（`.claude/skills` 等 3 个是 skills 层 junction，其余 13 个是 skill 层 junction）|

## 三、为什么不提交进本仓库

三个理由，任何一个都足够：

1. **它是嵌套 git 仓库**。直接提交会变成一个只有 commit 指针的 embedded repository，
   既拿不到内容，又污染 `git status` 与子模块语义。
2. **里面带着 106 MB 的 `.venv`**。这是运行环境不是源码，入库只会膨胀历史、
   制造几千个未跟踪文件的噪音。
3. **`npx skills add/update` 对目标目录做的是 `rm -rf` 再重拷**
   （`skills` CLI 1.7.0 源码 `installSkillForAgent` → `cleanAndCreateDirectory`）。
   只要它还在 `skill-lock.json` 里，为别的 skill 跑一次 `npx skills update`
   就会把目录连 venv 一起抹掉。

## 四、当时的取舍（替代方案为何被否）

| 方案 | 结论 |
|---|---|
| npx 安装 + venv 放 `~/.venvs/` | 曾用过；venv 与 skill 分离，update 安全，但换机要装两处，且自包含性差 |
| `.venv` 放 skill 目录 + npx 安装 | **否决**：`npx skills update` 会先删目录，venv 活不过一次更新 |
| **git clone + 内嵌 `.venv`（已采用）** | 自包含；`git pull` 不动未跟踪文件；代价是**永远不能对它跑 `npx skills add/update`** |
| 提交为本仓库的 submodule | 可选但没必要：上游仓库本来就是公开的，指针意义不大 |

配套做的四件事（缺一不可）：

1. 从 `~/.agents/.skill-lock.json` 移除 book-to-skill 条目
   （备份：`~/.agents/.skill-lock.json.bak-before-booktoskill-removal`），
   否则无参数的 `npx skills update` 仍会命中它。
2. 外层 `.git/info/exclude` 加 `/book-to-skill/`，避免嵌套仓库被当作 embedded repo。
3. 内层 `.git/info/exclude` 加 `/.venv/` 与 `/ENVIRONMENT-SETUP.local.md`
   （后者是本机环境笔记，不随上游走，重建后需参照本文重做）。
4. `PYTHON_BIN` 用**正斜杠**路径 —— 反斜杠会被 Git Bash 的 MSYS 路径转换改写，
   导致 skill 静默退回没装包的 MSYS2 python（PEP 668 环境，无 pip）。

## 五、换机重建步骤

```bash
# 1. 克隆上游
git clone https://github.com/virgiliojr94/book-to-skill.git ~/.agents/skills/book-to-skill

# 2. 建 venv（base 任选一个带 pip 的 Windows Python）
~/.venvs 的父目录不存在也没关系；anaconda python 亦可
"D:/Users/29580/anaconda3/python.exe" -m venv ~/.agents/skills/book-to-skill/.venv

# 3. 装抽取依赖
& "C:/Users/29580/.agents/skills/book-to-skill/.venv/Scripts/python.exe" -m pip install `
    pypdf "pdfminer.six" ebooklib beautifulsoup4 python-docx striprtf trafilatura `
    "pdf-inspector>=1.15,<2"

# 4. 环境变量（User 级，必须正斜杠）
[Environment]::SetEnvironmentVariable('PYTHON_BIN',
  'C:/Users/29580/.agents/skills/book-to-skill/.venv/Scripts/python.exe', 'User')

# 5. 排除规则（外层防 embedded repo，内层防 venv 入库）
Add-Content ~/.agents/skills/.git/info/exclude '/book-to-skill/'
Add-Content ~/.agents/skills/book-to-skill/.git/info/exclude "/.venv/"

# 6. 从 skill-lock.json 摘除 book-to-skill（若重新跑过 npx skills add）
```

日常更新：`cd ~/.agents/skills/book-to-skill && git pull`。
**切勿**对它执行 `npx skills add` / `npx skills update`。

可选增强：技术书（表格/公式/代码）再装 `docling`；MOBI/AZW 需 Calibre（`ebook-convert`）。
本机尚未装这两样，普通 PDF/EPUB/DOCX/MD/HTML/RTF 已全部就绪。

## 六、验证

```powershell
$py = "C:/Users/29580/.agents/skills/book-to-skill/.venv/Scripts/python.exe"
& $py "$env:USERPROFILE\.agents\skills\book-to-skill\scripts\extract.py" --check
```

Git Bash 下按 `SKILL.md` 的正常解析方式 `"$PYTHON_BIN" .../extract.py --check` 亦可。
已验证：6 类格式 ready、真 PDF 抽取中文完好、junction 链路 17 处全部可达。
