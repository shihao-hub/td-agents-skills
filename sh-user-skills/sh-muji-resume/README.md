---
name: sh-muji-resume
description: 木及简历(mujicv.com)全流程制作 SOP：飞书内容转写、md 导入、极简色主题+思源黑体+墨线 CSS 配置、平台裁字 bug 修复与 PDF 导出验收。制作/更新简历、简历导出 PDF 异常时使用。点名使用。
version: 1.1.0
disable-model-invocation: true
created: 2026-10-27
updated: 2026-10-27
status: verified
last_verified: 2026-10-27
---

# sh-muji-resume：木及简历全流程制作 SOP

## 版本与来源

- v1.0.0：源自 2026-10-27 qiu-resume-workspace 实战会话（飞书 wiki → 木及 → PDF 全链路 + 平台两处 bug 逆向修复），全部步骤经 MCP Chrome 实机验证。
- 平台 bug 根因与自动化踩坑细节见知识库条目：`kb-engineering-notes/103_browser_mujicv_fix_*.md` 与 `104_agent_dsh_fix_MCP浏览器自动化antd表单与文件上传踩坑.md`。

## 前置检查与环境准备

1. **样式（规范来源在本技能内，项目无关）**：`<本技能>/assets/ink-rule.css`——墨线 12 段，**第 11、12 段是木及平台 bug 修复，严禁删改**。项目仓库里的 `08-ink-rule.css` 只是实例副本；两者不一致时以技能 assets 为准并把改动同步回去。
2. **内容（永远现取，不依赖任何项目）**：两个来源——
   - 飞书 wiki 拉取：`lark-cli docs +fetch --doc "<wiki URL>" --as user --doc-format markdown`，把返回 `content` 转写为木及 md（转写规则见第四节）；
   - 或用户提供现成 md（须符合木及 `::: left/right` 约定）。
3. **兜底预览（按需现生成）**：`uv run python <本技能>/scripts/md_to_preview.py --md <内容.md> --out <预览.html>`——参数化脚本，任何项目目录均可重新生成，无需预存 HTML。
4. mujicv.com 登录态（随浏览器 profile；换浏览器重新登录）；浏览器缩放 100%（`Ctrl+0`）。
5. 项目实例参考（qiu-resume-workspace，2026-10-27）：内容 `deliverables/10-import-zhangshihao-full.md`、实例样式 `deliverables/08-ink-rule.css`；**项目被删除不影响本技能可用性**——样式在 assets、脚本在 scripts、内容从飞书现拉，三者均可自愈重建。

## 分步执行 SOP

1. 编辑器 → **文件 → 导入md** → 选内容 md（破坏性替换，导入前确认本地已有备份）。
2. **选择主题** → 极简色 → 确定（弹窗第二步按页数选单/多页）。
3. 字体下拉 → **思源黑体2.0_Normal**；顶栏第一个色块图标 → 主题色 `#9A3B2E`。
4. 顶栏 `</>` 图标 → 「设置 CSS」弹窗 → `Ctrl+A` 全选删除 → 粘贴本技能 `assets/ink-rule.css` **全文**（AI 直接读该文件内容作为 cssText）→ **必须点「保 存」**（红线：不保存 = 样式不进账号，导出 PDF 带默认模板且裁字修复失效）。
5. 导出 → 导出 pdf，下载后逐项验收：
   - 每行行首/行尾字符完整（无缺半字）；
   - h1 宋体大字、h2 黑字+赭红竖线+暖灰横线、日期灰色右对齐；
   - 页数符合预期（全文版约 5 页）。

## 常见踩坑与回滚

| 症状 | 根因 | 处置 |
| :-- | :-- | :-- |
| 预览/PDF 行首裁半字 | 木及 JS 动态写 `.rs-view-inner{margin-left:84.8px}` 内联样式，刷新/切主题必重写 | CSS 第 12 段 `!important` 压制（已内置）；确认面板 CSS 已保存 |
| 竖线出血致两侧各裁 8px | 旧版 `h2::before left:-16px` 撑破内容盒 | CSS 第 11 段改盒内画线（已内置） |
| 导出 PDF 是默认蓝主题 | CSS 没经「设置 CSS」面板保存进账号 | 重走第 4 步，点「保 存」 |
| 「智能一页」报简历过长 | 内容 >1.5 页上限 | 忽略该功能，正常分页导出 |
| 换浏览器后样式/内容丢失排查顺序 | 内容与 CSS 是账号级（登录即有）；先查登录态，再查「设置 CSS」面板回显 | 面板为空 = 当年就没保存成功，重贴 |
| 预览里 h2 是红色 | 账号 CSS 还是排障时保存的「验证集」（故意用红色做导出链路检验） | 用 `assets/ink-rule.css` 全文覆盖面板并保存，h2 回归黑字 |

## 飞书内容 → 木及 md 转写规则

1. `lark-cli docs +fetch --doc "<wiki URL>" --as user --doc-format markdown` 的输出是**整个 JSON**——简历 md 在 `data.document.content` 字段里且 `\n` 转义，须先解析 JSON 提取（python `json.load` 或 jq `-r`），不要把 JSON 原文当 md 用。
2. 语义零改动原则：原文照搬，仅排版层转换——
   - 飞书编号前缀 `1、` → Markdown 有序列表 `1. `；
   - `### 项目背景：` 类小标题 → 加粗段首 `**项目背景**：`；
   - 技术架构多行分层 → 无序列表逐层保留；
   - 每个条目的日期与左侧标题用 `::: left / ::: right` 组包装（组内空行分段，组尾 `:::` 必须闭合）；
   - 头部可从工作经历提取一行岗位副标题（`**Agent 工程师 / Java 工程师**`），属排版增强可删。
3. 日期数据疑似笔误（如工作经历写 2025年07月 但毕业 2023年06月）时**必须交用户拍板**，不得擅自改。

## 回滚

- 木及编辑器「历史记录」可回滚文档版本；项目侧 md/css 入 git 的用 `git checkout` 回退。
- 兜底路径：`scripts/md_to_preview.py --md <内容.md> --out <预览.html>` 现生成预览页 → Chrome 打开 → `Ctrl+P` → 另存为 PDF（A4、勾选**背景图形**），完全绕开木及导出管线。

## AI 操作要点（chrome-devtools MCP 同款）

- 导入 md：`文件`菜单 → `导入md` uid → `upload_file`（文件先复制到 `%TEMP%`，MCP 沙箱不认工作区路径）。
- CSS 写入：`custom-style-modal` 的 textarea 是 React 受控 → 原生 value setter + `input` 事件，写入后回读长度校验。
- 导出：按钮不吃 `el.click()`，用 CDP click（快照 uid）；下拉菜单几秒自动收起，打开后**同一脚本内轮询**菜单项并立即以完整 Pointer+Mouse 序列点击。
- 验收探针：`getComputedStyle(document.querySelector('.rs-view-inner')).marginLeft === '0px'`；PDF 用 `uv run --with pymupdf` 渲染 PNG 目检。
- 页面偶发主线程卡死（截图/脚本超时）：等 10 秒重试，仍卡则 reload（注入的实验样式会清掉，属预期）。

## 内容更新流

改简历内容 = 改内容 md（或从飞书 wiki 重新拉取转写）→ 木及重新导入或源码模式全量替换 → 保存，样式无需重贴。
样式若要演进：**先改本技能 `assets/ink-rule.css`（canonical 来源），再同步到木及「设置 CSS」面板**，顺序不要反——避免项目副本与技能资产漂移。

## 内容写作方法论（AI 代写必读）

从高质量样本反推的通用骨架、句式模板、内容配比、反模式清单与 LLM/Agent 简历专用叙事，见 `references/content-playbook.md`——写内容前先读它；量化数据缺失必须占位待确认，严禁编造数字。
