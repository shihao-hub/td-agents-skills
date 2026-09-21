---
name: sh-lark-chat-archive
description: 飞书聊天记录归档为单文件 HTML（私聊/群聊/话题，纸面排版+图注+lightbox）。点名使用
---

# 飞书聊天区间 / 话题归档（HTML → 可选归档 → 可选撤回）

把一段飞书聊天（私聊区间、群区间、或会话内话题）提取成单文件 HTML 存档并总结；
区间模式可选后续：把归档结果发回原会话 → 撤回原消息。全程有审批门，高危写操作必须用户确认。

## 职责分离

- **脚本管确定性渲染**：`scripts/build_archive.py` 负责拉消息、下图、压缩、base64 内嵌、
  生成 HTML（含 lightbox 与页内编辑器）。模型不要手写 HTML。
- **模型管语义**：读消息、逐张看图、写 `afterword.json`（编后记）与 `captions.json`（图注）、
  把握审批门与高危决策。
- 生成前必读 `references/design-rules.md`（去 AI 味排版 + 编后记/图注写作纪律）。

## 第一步：识别读取源（用户指定，拿不准就问）

| 模式 | 输入 | 范围 |
|---|---|---|
| 私聊/群 **区间** | 会话 + 区间起点（某条消息 / 某个时间，如"昨天到今天"） | 起点 → 最后一条，需与用户确认边界 |
| **话题**（thread） | 话题根消息的链接 / 消息，或从消息列表的 thread 标记中确认 | 话题即范围，无需定区间 |

会话定位：`lark-cli im +chat-list --as user --types p2p,group --json`（p2p 仅 user 身份可见）。
按名称匹配有歧义时列候选问用户，不要猜。

### 话题定位（三层递进，锁定前向用户复述候选）

- **A1 网页版消息链接**（飞书网页版 messenger 的 URL，含 `oc_`/`om_` 等 ID）
  → 正则提取 ID 直接 mget，全自动。
- **A2 客户端复制的 applink**（`applink.feishu.cn/client/message/link/open?token=…`）
  → **实测不可解析**：落地页只跳客户端/要求登录，token 服务端加密。直接降级 B，
  并向用户要"话题里的一个关键词"。
- **B 关键词搜索**：`lark-cli im +messages-search --as user --query "<关键词>" --json`
  （会话已知可加 `--chat-id oc_xxx`）→ 从命中识别话题根（mget 验证能展开）→
  复述候选（会话名 + 内容摘要 + 楼数）让用户确认。关键词选独特词：数字、专有名词、原句片段。
- **C 末选**：时间窗内 `+chat-messages-list` 拉消息找 thread 标记列候选。

## 工作流（七步）

1. **识别读取源**（见上）。拿到 chat_id 或话题根消息 id。
2. **拉取与边界确认**：
   - 区间模式：向用户复述"从 X 到 Y 共 N 条、图 M 张"；
   - 话题模式：复述"该话题共 N 楼、图 M 张"。
   数字来自实际拉取结果（或 `build_archive.py` 的运行输出），不要估算。
3. **语义工作**：通读消息、逐张看图（用下图产物或图片消息的 content 描述），
   写出 `afterword.json` 与 `captions.json`（格式见下），遵守 design-rules.md。
4. **生成 HTML**：运行 `build_archive.py`（用法见下），把输出路径交给用户过目
   （chrome-devtools 打开或给出绝对路径）。用户要求改 → 改 JSON/参数重跑（图片缓存按 position 复用，重跑便宜）。
5. **交付**：HTML 完全完成并交用户过目。两种模式都继续第 6 步（回传产物）。
6. **可选回传（话题/区间通用，必须用户确认后才执行）**：HTML 过目后主动问一次"要把存档发回原会话吗？"
   - 默认（私聊/群通用，全自动）：**HTML 文件以用户身份发回原会话**
     ```powershell
     # --file 只接受 cwd 相对路径：先 cd 到 HTML 所在目录
     lark-cli im +messages-send --as user --chat-id <oc_xxx> --file "<文件名.html>"
     ```
   - 群 + bot 在群（可选原生合并消息形态，区间场景需要时）：
     `lark-cli im messages merge_forward --receive-id-type chat_id --as bot --data '<JSON>'`
     （该 API 平台级 bot-only，user token 会被拒；data 里 receive_id + message_ids 列表）
   - 无 bot 且用户坚持原生合并形态（末选）：提示用户在客户端手动合并转发，等确认。
   - 用户说不需要 → 流程结束。
7. **可选撤回（仅区间模式，仅在已回传且用户再次确认后）**：
   - 先列删除清单（从 `messages.json` 快照取 message_id 与内容摘要，N 条）；
   - 用户明确确认后逐条执行：
     ```powershell
     lark-cli im messages delete --message-id <om_xxx> --as user --yes
     ```
   - `delete` 是 high-risk-write：**`--yes` 只能在用户批准后出现，绝不自加**。
   - 失败要记录并如实汇报（非本人消息 / 超出 24h 窗口均会失败）。

## build_archive.py 用法

```powershell
# 区间模式（position 起点）
uv run build_archive.py --chat-id oc_xxx --start-position 30 --title "自言自语"
# 区间模式（时间起点，取首个 >= 该时间的消息）
uv run build_archive.py --chat-id oc_xxx --start-time "2026-09-20 09:13" --title "自言自语"
# 话题模式（根消息 + mget 展开全部回复；与 --start-* 互斥）
uv run build_archive.py --thread-root om_xxx --title "话题存档"

# 可选：--out-dir <目录>（默认 %TEMP%\opencode\lark_archive\<chat尾8位>\）
#        --dek "<一句话导语>"  --chat-name "<会话名>"
#        --afterword afterword.json  --captions captions.json
```

产出（都在工作目录）：
- `<YYYY-MM-DD> <title>.html`：单文件存档（图全部 base64 内嵌，可离线分发）；
- `messages.json`：消息快照（message_id、position、摘要），撤回阶段取 id 用它；
- `img/`：图片缓存（按 position 命名，重跑不重复下载）。

质量下限（脚本已内建，验收时抽查）：消息正序、回复锚点还原、图 base64 内嵌
（>1600px 自动压缩）、lightbox（锁滚动 + Ctrl 滚轮缩放 + 拖拽 + 双击复位）、
页内编辑器（删条/删节/改字/保存覆盖原文件）。

### afterword.json（编后记，模型写）

```json
[
  {"title": "小节标题",
   "before": ["引出段落，可多段……"],
   "quote": "可选：引用的原话",
   "after": ["引文后续段落……"]}
]
```

### captions.json（图注，模型逐张看图后写）

```json
{"31": "一句话说明这张图是什么、与哪条原文相关", "32": "……"}
```

键是消息 position（话题模式见 messages.json 的 pos_key）。编号（图1、图2…）由脚本按转录顺序自动生成。

## 安全门

- **归档与撤回都是写操作**：分别需要用户确认；撤回还需要第二次确认（删除清单过目）。
- **`delete --yes` 是高危**：只在用户明确批准后出现；一次只删清单内消息。
- 发消息、转发、撤回完成后如实报告结果（成功/失败与原因）。
- 浏览器测试页、临时服务等用后即清（AGENTS.md 约定）；`%TEMP%` 下的工作目录与图片缓存可保留复用。
- 话题模式不做第 7 步（撤回）：话题本身就是沉淀，原消息永不撤回；产物回传（第 6 步）照常。

## 相关技能分工

- 收发消息、群管理、表情回复：lark-im（本 skill 第 6 步的 `+messages-send` 语法已内建，直接用）
- 会话/联系人定位：本 skill 用 `+chat-list`；找群、找人走 lark-im / lark-contact
- 云文档导出 HTML 到飞书文档：lark-doc（本 skill 的 HTML 是本地文件，不是飞书文档）
