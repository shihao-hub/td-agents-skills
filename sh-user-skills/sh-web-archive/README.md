---
name: sh-web-archive
description: 公开网页存档为离线三 tab 页面（原文转录+AI 总结+可编辑），媒体本地化；仅限无鉴权页面。点名使用
---

# 网页文章 → 三 tab 离线存档（原文 / AI 总结 / 可编辑页面）

给定一个无需鉴权的公开网页 URL，产出**目录形态**的静态存档：`index.html` +
`assets/`（本地化资源）+ `history/`（版本快照）+ `manifest.json`，`file://`
双击即开、完全离线可看。编辑保存走 Chrome/Edge 的 File System Access API
（file:// 下已实证可用），每次保存生成带时间戳的不可变版本。

## 职责分离

- **脚本管确定性管线**：`scripts/build_archive.py` 负责抓取、资源本地化、渲染
  页面骨架与版本历史。模型不要手写 HTML，不要手改 `article.json`/`index.html`/
  `history/`/`manifest.json`（它们归脚本与浏览器所有）。
- **模型管语义**：通读原文、写 `summary.json`（AI 总结栏内容）、把握安全门与交付。
- 生成总结前**必读** `references/design-rules.md`（去 AI 味排版 + 网页总结写作纪律）。

## 两处同名目录的职责区别（重要）

| 路径 | 职责 |
|---|---|
| `~\.agents\skills\sh-web-archive\`（skill 本体仓库，`~` 为用户主目录） | **skill 本体**：SKILL.md、scripts、references（代码） |
| `~\agents-skills\sh-web-archive\` | **存档产物根目录**：每个网页一个「日期 标题」子目录（数据） |

> 位置变更：最初用 `%APPDATA%\agents-skills\`，但 Chrome 的 showDirectoryPicker
> 拒绝选择带隐藏属性目录链（AppData 默认 Hidden，报"包含系统文件"）导致编辑
> 授权无法完成，已迁至用户主目录 `~\agents-skills\`。

两者互不相干，不要把存档数据写进 skill 本体目录，也不要把代码放进产物目录。

## 工作流（七步）

1. **接 URL**：向用户要（或从消息里提取）目标网页 URL。无需鉴权即可匿名访问的
   页面才继续；用户明确说需要登录的，直接说明本 skill 不做鉴权页。
2. **fetch 抓取**：
   ```powershell
   uv run ~\.agents\skills\sh-web-archive\scripts\build_archive.py `
     fetch --url "<URL>" [--dir "<子目录名>"] [--title "<标题>"]
   ```
   默认目录名 `YYYY-MM-DD 标题`（标题取页面 og:title，非法字符自动清洗）。
   退出码：0 成功；1 业务拒绝（`auth_required`/`login_wall`/`blocked_by_site`/
   `extract_failed`，stderr 有可读原因，**未创建任何目录**）；2 URL 不合法。
   拒绝时把 stderr 原因如实告诉用户，不要绕过、不要重试出半成品。
3. **写 summary.json**：先读 `references/design-rules.md`，再通读存档目录下
   `article.json` 的 `text` 字段（纯文本全文），按写作纪律撰写 `summary.json`
   （格式见下），放到存档目录里。数字必须与原文一致，不确定的删掉不编。
   注意：`text` 是单行长文本，直接读 `article.json` 会被读取工具按行截断，
   漏掉中后段小节。先导出全文到临时文件再通读（临时文件用完在收尾时删除）：
   ```powershell
   uv run python -c "import json,io,os; d=json.load(io.open(r'<存档目录>\article.json',encoding='utf-8')); io.open(os.path.join(os.environ['TEMP'],'opencode','article-text.txt'),'w',encoding='utf-8').write(d['text'])"
   ```
4. **render 渲染**：
   ```powershell
   uv run ~\.agents\skills\sh-web-archive\scripts\build_archive.py `
     render --dir "<存档目录>" --summary "<summary.json 路径>"
   ```
   首次渲染产出 `index.html` + `history/` 各 tab v1 快照 + `manifest.json`；
   重跑是幂等的——内容未变的 tab 不产生重复版本，改了总结只追加总结的新版本
   （秒级完成，资源不重复下载）。不带 `--summary` 时总结栏显示占位。
5. **交付**：用 chrome-devtools 以 `file://` 打开 `index.html` 自检：三主 tab
   切换、图片本地加载（Network 无红色失败）、总结小节齐全、关键数字抽查。
   然后把路径交给用户过目。
6. **反馈迭代**：用户对总结/排版提意见 → 只改 `summary.json` → 重跑 render
   （第 4 步）。原文内容有问题 → 重新 fetch 到新目录。不要手改 index.html。
7. **收尾**：chrome-devtools 打开的测试页关闭；测试用的临时文件删除；
   按 AGENTS.md 约定确认不残留浏览器进程组。

## 可编辑页面与历史版本（交付时向用户说明）

- 页面用 **Chrome/Edge** 打开才有编辑与完整历史（Firefox/Safari 只读，页面会提示）。
- 首次点左侧「启用编辑」，选择**存档目录本身**（名字与子目录一致）授权；
  handle 存进 IndexedDB，重开页面只需再点一次授权即可同步最新历史。
- 「可编辑页面」tab 是编辑入口：选编辑对象（自由页/原文转录/AI 总结）→ 改文字
  → 保存新版本。每次保存写 `history/{tab}-<时间戳>.html` 并更新 manifest，
  不可变、只增不改；各 tab 的子 tab 倒序展示版本（可编辑页面是动作时间线）。
- 编辑持久化闭环（授权 → 改字 → 保存 → 重开页面验证修改仍在）由用户完成验收。

## summary.json（模型写，脚本校验）

```json
{
  "one_liner": "一句话导语，≤ 60 字",
  "sections": [
    {"title": "观点式小节标题",
     "paragraphs": ["自然段 2-5 句……"],
     "quote": "可选：原文原句",
     "quote_ref": "可选：出处小节名"}
  ]
}
```

校验失败（缺字段/超长/类型错误）会报出具体 JSON 路径并退出码 1，按提示修。
写作纪律（主题分节、引原句、成段不成列、数字与原文一致、禁套话）见
`references/design-rules.md` 第三节。

## 安全门

- **鉴权拒绝如实上报**：`auth_required`/`login_wall`/`blocked_by_site` 是结论不是
  故障，转述给用户即可；不做 Cookie/UA 伪装绕过，不出半成品目录。
- **SPA 报错说明**：`extract_failed` 说明该页由 JS 渲染，本 skill 不做无头浏览器，
  建议用户换服务端渲染的原文源。
- **测试页用后即清**：chrome-devtools 打开的验证页在收尾时关闭；按 AGENTS.md
  终止专属 Chrome 进程组需用户数据目录过滤，确需保留时先征得用户同意。

## 相关技能分工

- 飞书聊天记录 → 单文件 HTML 存档：sh-lark-chat-archive（姊妹 skill，单文件形态）。
- 把存档发回飞书/消息分发：不在本 skill 范围。
