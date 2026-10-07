---
name: sh-windows-audio-diagnose
description: 排障：Windows 喇叭无声/嗡嗡爆音/默认输出被虚拟声卡抢占的排查与修复。点名使用
---

# sh-windows-audio-diagnose — Windows 音频异常排查

针对"笔记本/台式机声音不对"：明明在播放却听不到、音量 100% 没声、持续嗡嗡或爆音、重启后自愈。核心思路是**先把路由、驱动、硬件三层分开再动手**，避免把软件问题误判成喇叭坏了。

## 三条核心判断（先读这个）

1. **"没声音"最常见的根因不是硬件，而是默认输出端点被虚拟声卡抢占**。网易UU远程、NVIDIA Broadcast、VB-Cable、Steam Streaming Speakers、VoiceMeeter 等安装的虚拟音频设备会接管默认输出（eConsole / eMultimedia / eCommunications）。声音全被送进虚拟设备，物理喇叭自然无声，而设备管理器里一切正常——极易误判为硬件故障。
2. **"持续嗡嗡 / 爆音，重启就好"≠ 喇叭硬件损坏**。坏了的喇叭或功放不会靠重启恢复。重启能好说明是软件层卡死：音效 APO（Nahimic / Senary / Dolby / Waves）或虚拟声卡驱动陷入死循环。
3. **先用测试音拿可闻证据，再下硬件结论**。日志干净不等于物理喇叭正常；切换端点后放一段已知信号，用"是否可闻、是否干净"作为判据。

## 工作流

1. 只读体检（`audio-triage.ps1`）
2. 判型（路由 / 音量与独占 / APO / 外设 / 硬件）
3. 修复（切默认端点 / 关音频增强 / 卸虚拟声卡）
4. 测试音验证（`play-test-tone.ps1`）
5. 汇报（模板见文末）

## Step 1 只读体检

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File <skill目录>\scripts\audio-triage.ps1
```

脚本只读，输出七部分：默认端点（三个角色）、输出端点清单、输入端点、PnP 设备状态、音频服务、近 3 天错误日志、判型提示。看输出时抓住三点：

- **默认输出是不是虚拟设备**（脚本会打 `<<< 虚拟设备` 标记）→ 路由被抢占，先修这个。
- 端点状态 `ACTIVE / DISABLED / NOTPRESENT / UNPLUGGED` 是否与预期相符（例如插着耳机却是 UNPLUGGED，是插孔检测问题）。
- PnP 里的 `CMPROB_PHANTOM` / `Unknown` 是历史残留，不是故障；`Audio/Operational` 与 `PlaybackManager` 无警告/错误也不代表物理喇叭健康。

## Step 2 判型表

| 现象 | 关键证据 | 判型 | 处置方向 |
|---|---|---|---|
| 完全无声，默认输出是"XX虚拟音频设备" | triage 第 1 节标记虚拟 | 路由被抢占 | `set-default-device.ps1` 切回物理设备 |
| 默认已正确却无声 | 端点 ACTIVE、无错误日志 | 音量/静音/独占/应用路由 | 查设备音量与静音、应用音量合成器、应用是否路由到别的设备；换播放器复测 |
| 嗡嗡/爆音，重启自愈 | FxProperties 有 Nahimic 等 APO | APO 卡死 | 关音频增强；复现则卸载/升级音效组件 |
| 嗡嗡与负载/温度相关，伴风扇声 | 出风口发热 | 风扇/电感啸叫 | 非音频问题：清灰、降负载 |
| 耳机响、喇叭不响 | 扬声器端点非 ACTIVE 或 Jack 状态异常 | 插孔/硬件检测 | 检查耳机孔微动与接口检测设置 |
| 声音在蓝牙/HDMI 设备 | 端点枚举器 BTHENUM / HDAUDIO | 外设路由 | 切回板载扬声器或重连外设 |

## Step 3 修复

### 3.1 切回真实输出（最高频修复）

```powershell
# 先看所有输出端点（状态/虚拟物理/Id）
powershell -File scripts\set-default-device.ps1 -List

# 按名称关键词自动挑 ACTIVE+物理设备，三个角色一起切
powershell -File scripts\set-default-device.ps1 -Match 'Senary'

# 明确要切到虚拟设备（如远程调试需要）时
powershell -File scripts\set-default-device.ps1 -Match 'UU远程' -IncludeVirtual

# 验证
powershell -File scripts\play-test-tone.ps1 -Volume 40
```

不指定 `-Match` / `-Id` 时脚本自动挑第一个 ACTIVE 物理设备；候选不唯一则只列出让你决定，不会乱切。切换后脚本会重新读取默认设备与音量确认生效。

### 3.2 验证听感

| 听感 | 结论 | 下一步 |
|---|---|---|
| 五段声音干净 | 硬件与数字链路正常 | 收尾；若是虚拟设备抢占，问题已解决 |
| 有声但破音/沙沙 | APO 或驱动问题 | 进入 3.3 |
| 完全无声 | 默认端点又被抢占、静音、或更下游 | 重跑 `audio-triage.ps1` 对比 |

### 3.3 音频增强 / APO 卡死

设置 → 系统 → 声音 → 点对应输出设备 → "音频增强"选"关"，复测。关闭后异常消失即可锁定 APO，再决定继续关闭、升级还是卸载对应音效组件（Nahimic / Senary / Dolby / Waves）。这类组件的进程卡死常表现为持续嗡嗡或爆音，重启或切设备才恢复。

### 3.4 虚拟声卡反复抢占

远程/串流/加速类软件（UU远程、远程桌面、OBS、NVIDIA Broadcast）会在会话期间接管默认音频，正常退出时应归还。若退出后仍被占用，手动切回即可；确定不再使用的虚拟设备可在设备管理器 → 音频输入和输出 中卸载，避免复发。

## 实战案例（2026-09-26 本机）

- **症状**：用户报"喇叭好像坏了、没声音"；前一天还出现过持续嗡嗡、重启后自愈。
- **体检**：PnP 全部 OK、音频服务正常、近 3 天音频日志零错误——但默认输出被 **UU远程虚拟音频设备**（枚举器 `ROOT`）抢占，真实扬声器（`HDAUDIO` 枚举的 Senary Audio）根本收不到音频。
- **处置**：用 IPolicyConfig 把 Console/Multimedia/Communications 三个角色切回 Senary 扬声器，音量 40%，播放 5 段测试音，用户确认恢复正常。
- **关联判断**：前一天的嗡嗡声很可能同源——虚拟声卡或 Nahimic（Avolute NH4）APO 卡死，而非喇叭硬件损坏；重启能让软件层复位，硬件坏了不会自愈。

## 踩坑备忘

- **PS 5.1 脚本必须带 UTF-8 BOM**，否则中文被按 ANSI 读成乱码。手工改脚本后注意别把 BOM 弄丢。
- 注册表 `HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render\<裸GUID>` 存端点；**IPolicyConfig 需要 `{0.0.0.00000000}.` + 裸 GUID 拼接**（录音端点前缀是 `{0.0.1...}`）。从 `IMMDevice.GetId()` 拿到的就是拼好的完整格式，优先用它。
- `DeviceState` 是**位掩码**，只用低 4 位（1/2/4/8 = ACTIVE/DISABLED/NOTPRESENT/UNPLUGGED）；高位是内部标志，别当成状态读。
- 虚拟端点识别特征：枚举器 `ROOT` / `SWD`；名称含"虚拟/Virtual/UU远程/Remote/Nahimic/Mirroring/Streaming"。
- CoreAudio 全量枚举（`0xF`）在有 NOTPRESENT 端点驱动卡死时可能整体失败（本机实测 `0xE000020B`，仅 render 流受影响，capture 正常）；脚本会自动降级为 ACTIVE+DISABLED 并告警。需要含"未插入"的全量清单时直接查注册表 `HKLM:\...\MMDevices\Audio\Render`。
- `set-default-device.ps1 -WhatIf` 可先预演切换动作，不实际生效。
- 虚拟设备与物理设备**音量各自独立**，切回后要重新确认音量与静音（`play-test-tone.ps1 -Volume` 已处理）。
- `SoundPlayer` 走系统默认 eConsole 设备，所以**先看默认端点再播**，否则测试音也进虚拟设备。
- Nahimic 会额外挂一个 SWD 镜像端点；其 APO 在端点 `FxProperties` 里可见 `#AVOLUTE_NH4APO`，是常见噪音源。
- `Get-PnpDevice` 里大量 `Unknown` + `CM_PROB_PHANTOM` 属正常残留，别当故障报。

## 汇报模板

```text
诊断：<默认端点/硬件/日志三句话>
判型：<路由被抢占 / APO / 音量独占 / 硬件>
处置：<切了哪些角色到哪个设备、音量、是否关增强>
验证：<测试音听感 + 用户确认>
提醒：<复发场景与下次自查路径>
```

---
**来源：** 2026-09-26 本机"喇叭无声"实战（UU远程虚拟音频设备抢占默认输出，Senary 扬声器硬件正常）
