---
name: sh-docsearch
description: 本地文档与技能库轻量级语义检索（docsearch CLI 一次性查询，即查即退，0 内存驻留）：支持自然语言模糊检索本地 Markdown 文档与知识库，按相似度返回切块与行号。当需要跨项目/跨知识库按语义搜索文档内容、找历史方案与规范时使用。点名使用
version: 1.0.0
created: 2026-10-18
updated: 2026-10-18
disable-model-invocation: true
---

# sh-docsearch — 本地文档与知识库语义检索

> **外部依赖声明**：  
> 本技能由本地工程 **`docsearch`** 驱动。  
> - **代码与规范真身**：`D:\Users\language_projects\python_projects\docsearch\`  
> - **详细调用契约**：参见本体根目录下的 [SKILL_SPEC.md](file:///D:/Users/language_projects/python_projects/docsearch/SKILL_SPEC.md)

---

## 一、何时使用 / 何时不用

- **何时使用**：
  - 用户用自然语言/模糊描述查找本地技术方案、设计文档、架构规范、实战手记或技能库；
  - 关键词不确定、仅知道大致概念（如“搜一下豆包设计规范”、“找跨模块提交的经验”、“怎么做会话治理”）；
  - 需要快速定位某段知识所在的源文件路径与具体行号范围。
- **何时不用**：
  - 按文件名/扩展名全盘查找：使用 `sh-everything-search`；
  - 精确代码符号匹配、已知关键词 grep：直接在终端使用 `rg`；
  - 读取已知路径的具体文件：直接使用 `view_file`。

---

## 二、架构特性（零内存常驻）

- **即查即退**：不需要后台常驻运行任何服务（不占 1GB+ 内存）；
- **极速响应**：单次 CLI 冷启动查询约 **300ms**，查完进程立即退出，内存完全归还系统；
- **智能直通**：若后台碰巧打开了 WebUI 服务（8765 端口），CLI 自动秒级直通（~10ms），绝不重复加载模型。

---

## 三、标准执行 SOP

无论当前处于哪个工作目录，均使用原子命令直接调用：

```powershell
# 1. 基础自然语言检索（JSON 输出，便于 Agent 提取）
uv run --directory "D:\Users\language_projects\python_projects\docsearch" docsearch search "<检索关键词或描述句子>" --json

# 2. 控制返回数量（例如只取 top 5）
uv run --directory "D:\Users\language_projects\python_projects\docsearch" docsearch search "<检索词>" --top-k 5 --json

# 3. 若需要增量更新索引（添加了新文档后执行一次即可）
uv run --directory "D:\Users\language_projects\python_projects\docsearch" docsearch index
```

---

## 四、Agent 结果消费建议

1. **提取匹配结果**：从 JSON 输出的 `results` 数组中获取：
   - `filepath`：文档绝对路径
   - `heading`：所属标题
   - `start_line` ~ `end_line`：切块对应行号
   - `content`：切块核心内容
2. **落地反馈**：
   - 若切块已包含所需信息，可直接在回答中组织提炼给用户；
   - 若切块仅包含部分上下文，可调用 `view_file` 针对 `filepath` 与对应 `StartLine`/`EndLine` 展开阅读。
