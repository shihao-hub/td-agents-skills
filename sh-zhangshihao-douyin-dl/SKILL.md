---
name: sh-zhangshihao-douyin-dl
description: 本机抖音/B 站视频下载 + 知乎文章提取：用本机打包好的 douyin_dl.exe（Nuitka 产物，路径仅在本机 ZHANGSHIHAO 有效）下载抖音无水印视频、B 站视频（含多 P），并把知乎回答/专栏文章提取为 Markdown + 本地原图。用户提到抖音分享文案、无水印下载、BV 号/b23.tv/bilibili 链接、知乎回答或专栏文章提取/存成 Markdown 时使用。点名使用
---

# sh-zhangshihao-douyin-dl — 本机抖音/B 站下载 + 知乎文章提取

把三件事各变成一条固定命令：

| 输入 | 产出 |
|---|---|
| 抖音分享文案 / 链接 | 无水印 mp4（音视频已合并，默认存 `~/Downloads`） |
| B 站链接 / 裸 BV 号 / b23.tv 短链 | mp4（DASH 流经 ffmpeg 无损合并，多 P 时每 P 一个文件） |
| 知乎回答 / 专栏文章链接 | `~/Downloads/zhihu/{标题}/article.md` + `images/`（原图） |

一条命令可以混着给，工具按域名自动分流、串行处理。本 skill 与**当前这台电脑绑定**：exe 是 Nuitka 编译产物，路径写死在本文，换机器必然失效。

## 绑定声明（先核对再执行）

- 仅在主机名 `ZHANGSHIHAO` 的电脑上有效（PowerShell `$env:COMPUTERNAME` 核对；不一致时停手，走文末「跨机器」）。
- exe 固定路径（全文以 `$EXE` 指代）：
  `D:\Users\language_projects\python_projects\douyin_downloader\dist\douyin_dl.exe`
- 版本对应关系：B 站支持自 v2.4.0 起、知乎提取自 v2.5.0 起；若手上 exe 更早（`--version` 一看便知），先按文末「exe 缺失或需更新」重建再谈对应链路。

## 用法（照抄，替换引号内文案）

```powershell
# 抖音分享文案
& "D:\Users\language_projects\python_projects\douyin_downloader\dist\douyin_dl.exe" "8.74 复制打开抖音 https://v.douyin.com/xxxxx/ 复制此链接，打开Dou音搜索，直接观看视频！"

# B 站：主站链接 / 短链 / 裸 BV 号等效
& "D:\Users\language_projects\python_projects\douyin_downloader\dist\douyin_dl.exe" "https://b23.tv/xxxxxxx"
& "D:\Users\language_projects\python_projects\douyin_downloader\dist\douyin_dl.exe" "BV1B6YR6gEyd"

# 知乎：回答（/question/<qid>/answer/<aid>）与专栏文章（/p/<pid>）
& "D:\Users\language_projects\python_projects\douyin_downloader\dist\douyin_dl.exe" "https://zhuanlan.zhihu.com/p/96956163"

# 混合：一条命令三类链接都处理
& "D:\Users\language_projects\python_projects\douyin_downloader\dist\douyin_dl.exe" "<抖音文案> https://b23.tv/xxxxxxx https://www.zhihu.com/question/xxx/answer/yyy"
```

- 文案中**所有**链接都会被检查：抖音与 B 站链接逐个下载、知乎链接逐篇提取（串行，复用同一个 Chrome）；不支持的链接跳过并在 `skipped` 里如实列出（不会静默丢弃）。
- 知乎只认回答与专栏文章两类链接；想法（`/pin/`）、收藏夹、问题页整页会按 `invalid_url` 失败。
- 管道与文件：

```powershell
Get-Content 文案.txt -Raw | & "D:\Users\language_projects\python_projects\douyin_downloader\dist\douyin_dl.exe" --json
```

- 常用参数：`--json`（stdout 仅一个 JSON 包络）、`--output-dir DIR`（改输出目录）、`--headed`（前台可见窗口，人工过验证 / 首次登录 B 站与知乎用）、`--headless=background`（真 Chrome + 窗口移到屏幕外）、`--close-browser`（关掉常驻实例）、`schema`（导出 CLI 契约 JSON）、`--help`、`--version`。

## 抖音：音视频合并（已修复：不再产出无声视频）

抖音是 DASH 音视频分离，工具会把 `media-video-*` 与 `media-audio-*` **两条流都抓下来再经 ffmpeg 合并**，产出带声音的完整 mp4。成功记录的 JSON 带 `audio` 字段：

| 值 | 含义 |
|---|---|
| `merged` | 视频+音频分别下载后合并（正常情况） |
| `included` | 抓到的流本身自带音轨，无需合并 |
| `missing` | **没抓到音频流，文件是无声的**——stderr 同时打警告，汇报时要讲清楚 |

> 历史 bug：早期版本抓流时主动过滤掉 `media-audio`，导致抖音视频永远无声。若用户手上只有旧版本产出的无声文件，属该 bug，已修复。

## B 站：API + 登录态

- 走 B 站公开 web API（view / playurl）拿 DASH 流地址，**登录态决定清晰度档位**（取服务端按账号权益下发的最高档）。
- 多 P：链接带 `?p=N` 只下指定 P；不带 `p` 且是多 P 时全部下载，每 P 一条记录（`video_id` 形如 `BVxxx_p2`，文件名带 `_P{n}`）。
- 未登录（profile 无 `SESSDATA`）时该批按 `bilibili_not_logged_in` 失败：提示用户 `--headed` 重跑，在弹出的窗口里登录 bilibili.com 后再重跑（Cookie 持久化，之后不用再登）。
- 需要本机已安装 **ffmpeg**。

## 知乎：浏览器提取为 Markdown + 原图

- 知乎正文是登录后才完整下发、且匿名直连 403，所以走真实浏览器：CDP 读登录态（关键 cookie `z_c0`，HttpOnly）→ 打开页面 → 等正文容器渲染 → 浏览器内滚动触发图片懒加载后取正文 HTML → BeautifulSoup 清洗 + html2text 转 Markdown → 原图逐张下载。
- 产出目录（每篇一个目录，可整目录拷走）：

```
{output_dir}/zhihu/{标题}/
├── article.md          # 标题 + 来源/作者/提取时间元信息 + 正文
└── images/image_001.jpg # 正文原图，按出现顺序编号（同 URL 只存一份）
```

- Markdown 用相对路径引用图片；段落/引用/代码块/列表/加粗斜体保真，目录重名自动加 `_1` 后缀（不覆盖既有产物）。
- **单张图片下载失败不影响任务成功**：该图在 Markdown 里保留原始 URL，失败张数记在 `images_failed`（汇报时提一句）。
- 未登录（profile 无 `z_c0`）时该批按 `zhihu_not_logged_in` 失败：提示用户 `--headed` 重跑并登录 zhihu.com，之后重跑命令即可。
- 提取失败（知乎改版/链接失效）按 `zhihu_extract_failed` 失败，`error.detail` 里带页面标题与正文候选区统计——汇报时把 detail 一并给出，便于判断是改版还是链接问题。
- 不提取：问题页整页多回答、评论与赞同数、公式 LaTeX 还原（公式以渲染图片保存）。

## 启动模式（不会打扰用户）

| 模式 | 触发 | 屏幕表现 |
|---|---|---|
| `headless-new`（**默认**） | 不带参数 | Chrome 新版无头，**无窗口、无任务栏图标** |
| `background`（自动回退） | 默认模式被抖音拦时自动切换，或 `--headless=background` | 真 Chrome，窗口移到屏幕外（`-32000,-32000`）+ 静音 |
| `headed` | `--headed` | 前台可见窗口，供人工过验证滑块 / 登录 B 站与知乎 |

- 默认模式屏幕上零痕迹，不影响用户正常用电脑；被抖音拦截时会**自动回退 `background` 重试一遍**。
- `--headless=old` 是旧无头，**已被抖音风控识别**（必然 `stream_not_found`），保留仅为对照，别用。
- 注意：`background` 模式**不要**改成「把窗口压到最底层 / `WS_EX_NOACTIVATE`」——实测那样窗口会被判定为不可见，抖音播放器直接不加载视频流；必须用移出屏幕的做法。
- 知乎与 B 站的登录态都是**持久化**的：登录一次后默认无头模式也能用，不需要每次 `--headed`。

## 行为与判定

- 过程日志（启动 Chrome、进度条）走 **stderr**；结果汇总走 stdout；`--json` 时 stdout 只有一个 JSON 对象。
- 退出码：`0` 全部成功；`1` 存在失败项；`2` 参数错误、输入为空、或没有可处理的抖音/B 站/知乎链接。
- JSON 包络：
  - `data.downloaded[]`：视频记录，含 `path`/`bytes`/`audio`（B 站多 P 时多条）；
  - `data.extracted[]`：知乎记录，含 `path`（article.md）/`images_total`/`images_failed`；
  - `data.skipped[]`：不支持的链接；`data.summary`：`total`/`succeeded`/`failed`/`skipped`/`extracted`；
  - 失败项带 `error{code,message,detail}`。汇报时引用 `path`（与 `bytes`/图片数），失败引用 `error.code`，必要时带 `detail`。
- 常见错误码：`stream_not_found`（抖音未捕获到流，多半要人工验证）、`bilibili_not_logged_in`、`bilibili_api_error`、`ffmpeg_merge_failed`、`zhihu_not_logged_in`、`zhihu_extract_failed`、`invalid_url`。

## 注意

- Chrome 实例运行结束后**常驻不退出**（复用登录态，二次运行秒连），这是设计行为，不是资源泄漏。收尾用 `--close-browser`（优雅关停并确认退出），不要去任务管理器乱杀。
- 触发滑块时该条失败（`stream_not_found`）：默认模式已自动回退 `background` 试过一遍；仍失败就提示用户 `--headed` 重跑，在弹出的窗口里人工完成后再重跑。
- **ffmpeg 只有视频链路需要**（抖音/B 站 DASH 合并用 `-c copy`，无重编码，秒级完成）；纯知乎提取不需要 ffmpeg。
- 单条失败不中断整批；exe 无签名可能被杀软误报，属已知现象。

## exe 缺失或需更新

1. 先核对主机名与路径确实没抄错；
2. 到 `D:\Users\language_projects\python_projects\douyin_downloader` 按 `NUITKA.md` 重建：`uv run scripts\build_exe.py`（需 MSVC，首次数分钟；v2.5.0 产物约 7.6 MB）；
3. 不要自行改写本 skill 里的路径——路径变更属用户决策，先问。

## 跨机器

本 skill 不适用。经用户同意后可用源脚本等价替代（需 uv，首次会自动准备依赖）：

```powershell
cd D:\Users\language_projects\python_projects\douyin_downloader
uv run douyin_dl.py "<文案或链接>"
```
