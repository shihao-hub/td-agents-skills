---
name: sh-video-transcribe
description: 从视频或音频文件中提取字幕（语音转文字）并总结内容：ffprobe 探流 → ffmpeg 抽音轨 → faster-whisper 本地转写产出 SRT+TXT → AI 总结（自动修正 ASR 同音错字）。当用户给出 .mp4/.mov/.mkv/.webm/.mp3/.m4a/.wav/.flac 等媒体文件，要求"提取字幕""转成文字""语音转文字""这个视频/播客/录音讲了什么""帮我总结这个视频"，或任何把媒体里的语音变成文字再提炼内容的请求时，必须使用本 skill——即使用户没提"字幕"或"转写"二字，只丢来一个视频文件问内容也要触发。已有字幕/文本文件的纯总结不触发本 skill（直接读文件总结即可）。
---

# 视频字幕提取与总结

把媒体文件里的语音变成文字（SRT + TXT），并给出内容总结。核心流程四步：探流 → 问模型档位 → 转写 → 总结。

环境假设：Windows + PowerShell，`ffmpeg/ffprobe` 与 `uv` 已安装（转写脚本为 PEP 723 格式，`uv run` 会自动创建环境装依赖，无需预装 faster-whisper）。

## 第一步：探流（ffprobe）

先弄清输入是什么，再决定走哪条路：

```powershell
ffprobe -v error -show_entries stream=index,codec_type,codec_name -of csv=p=0 "<媒体文件>"
ffprobe -v error -show_entries format=duration -of csv=p=0 "<媒体文件>"
```

- **纯音频**（只有 audio 流）→ 直接进入转写，跳过抽音轨
- **视频且有内嵌字幕流**（出现 `subtitle` 类型流，极少见）→ 可直接 `ffmpeg -i in.mp4 -map 0:s:0 out.srt` 抽取，跳过 ASR
- **视频且无字幕流**（绝大多数情况：抖音/B站/录屏等）→ 网络视频的字幕即使画面上看得见也是烧录进像素的，无法提取，必须走语音转文字
- **时长**用于下一步推荐模型档位

## 第二步：问模型档位

转写前问一次用户，给出推荐默认。推荐依据（中文内容实测）：

| 档位 | 首次下载 | 适用 | CPU 转写速度（约） |
|---|---|---|---|
| tiny | ~75MB | 只想快速知道大概内容 | 实时 ×10 |
| base | ~145MB | 短音频、普通话清晰 | 实时 ×7 |
| **small（默认推荐）** | ~460MB | 中文短视频/会议录音，准确率与速度平衡 | 实时 ×4 |
| medium | ~1.5GB | 专业术语多、口音重 | 实时 ×2 |
| large-v3 | ~3GB | 追求最高准确率，建议有 GPU | 很慢 |

话术示例："用哪个模型档位？推荐 small（下载约 460MB，7 分钟视频 CPU 转写约 2 分钟）；想更快选 base，想更准选 medium。"首次下载走 hf-mirror 镜像，之后有缓存不再下载。

无人值守场景（subagent 执行测试、批量任务等无人可问时）：直接用推荐默认 small，并在结果中说明用了哪个档位、如何换档重跑。

## 第三步：转写（跑捆绑脚本）

不要手写转写代码，直接用本 skill 捆绑的脚本（已固化镜像、编码、GPU 检测、进度输出）：

```powershell
uv run "<skill目录>/scripts/transcribe.py" "<媒体文件>" --model small
```

参数：`--model` 档位（默认 small）；`--lang auto` 自动检测语言（默认，已知纯中文可传 `--lang zh` 减少误判）；`--outdir` 输出目录（默认与输入文件同目录）。

脚本行为要点（排查问题时知道去哪看）：

- 自动检测 NVIDIA GPU：有则 `cuda + float16`，无则 `cpu + int8`，无需干预
- 默认 `HF_ENDPOINT=https://hf-mirror.com` 下载模型；想回官方源先设 `$env:HF_ENDPOINT="https://huggingface.co"`
- 强制 UTF-8 stdout，规避 Windows GBK 控制台乱码
- 开启 `vad_filter=True` 跳过静音段，`beam_size=5`
- 产出 `<同名>.srt`（带时间戳）与 `<同名>.txt`（纯文本），落在输入文件同目录

注意事项：

- **长视频**（>30 分钟）：bash/终端调用要设置足够大的 timeout（约 = 时长 × 30 秒起步），并确认输出在持续打印（脚本逐段 flush，卡住可及早发现）
- **临时文件**（抽出的 wav 等）放系统临时目录，用完即清；字幕产物放媒体文件同目录，方便用户查找
- `uv` 不存在时：提示安装（`winget install astral-sh.uv`），不要改成 pip 全局装依赖

## 第四步：AI 总结

读 `.txt` 全文，直接在对话里总结。转写原文不要改写；总结遵循两条：

1. **按修正后的语义总结**：ASR 输出必有同音错字，中文高频错法有规律——"用例→用力"、"SQL→ccode/ccoli"、"Postgres→postgrade/postgrid"、"抛出→拨出"、"依赖倒置→依赖道质"、"解耦→解偶"、"LeetCode→litcode"、"乱麻→乱马"。总结时按上下文还原术语，不要把错字复述进总结
2. 总结结构按内容自定（论点/方案/步骤/结论），技术教程类给出核心论证与关键手法；不确定的词（如专有名词转错）标注说明

汇报时告知产物位置（SRT/TXT 路径）与模型档位，方便用户复现或换档位重跑。

## 常见坑

- **把画面上的字幕当可提取的字幕流**：ffprobe 没有 subtitle 流就必须 ASR，没有捷径
- **首次运行卡在下载**：是模型在下载（460MB 起），不是挂了；镜像走 hf-mirror，已设则勿覆盖
- **控制台中文乱码**：脚本内部已强制 UTF-8；若用其他方式打印中文乱码，是 GBK 控制台问题，文件本身正常
- **超时被杀**：长视频转写时间按 CPU 实时 ×4（small）预估，timeout 给足余量
- **Windows 路径含中文/空格**：PowerShell 下统一用双引号包裹完整路径
