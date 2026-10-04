---
name: sh-agy-schedule
description: antigravity 的 /schedule 定时调度：单次延时提醒与周期性任务。速查表：想隔一段时间执行或周期性监控。点名使用
version: 1.0.0
---

# sh-agy-schedule：定时与调度任务

> 版本 v1.0.0 ｜ 移植自 Google Antigravity 斜杠命令 /schedule，工具描述提取自 language_server.exe（2026-09-23 构建）

## 功能介绍

Antigravity 的 /schedule：官方释义 "Run an instruction on a recurring schedule or as a one-time timer."。原版有原生 schedule 工具：单次定时器（DurationSeconds）或周期 cron（标准 5 字段 CronExpression）；TimerCondition 早取消（匹配消息即唤醒并取消计时）；IsDaemon 标记独立常驻任务；调用后立即结束回合等通知，且明令禁止用 shell sleep 当定时器。

原版场景：10 分钟后查 CI 构建状态；每小时拉线上错误日志做摘要；每天早上生成今日日程待办。

## 执行协议（Windows 适配）

opencode 无原生定时唤醒工具，用 Windows schtasks 模拟。先和用户确认三件事：触发时间/周期、要执行的动作、一次性还是常驻。

### 1. 定时执行（脚本落盘后注册计划任务）

```bat
:: 单次延时（先算好绝对时间 HH:MM）
schtasks /create /tn "AGY-<任务名>" /tr "<命令或脚本路径>" /sc once /st HH:MM /f

:: 周期任务
schtasks /create /tn "AGY-<任务名>" /tr "<命令>" /sc minute /mo 10 /f   :: 每 10 分钟
schtasks /create /tn "AGY-<任务名>" /tr "<命令>" /sc hourly /f           :: 每小时
schtasks /create /tn "AGY-<任务名>" /tr "<命令>" /sc daily /st 09:00 /f  :: 每天 9 点
```

### 2. 管理

```bat
schtasks /query /tn "AGY-<任务名>" /v /fo list   :: 查状态
schtasks /run /tn "AGY-<任务名>"                 :: 立即触发
schtasks /end /tn "AGY-<任务名>"                 :: 停止运行中实例
schtasks /delete /tn "AGY-<任务名>" /f           :: 取消
```

### 3. 结果如何回到对话

计划任务执行的是脚本，**不会唤醒对话**。二选一：

- 脚本把结果写到约定文件（如 `<工作目录>\.agy-schedule\<任务名>.log`），用户下次提"看定时任务结果"时读取汇报。
- 环境有可用 agent CLI（agy / opencode 非交互模式）时，任务里直接调 CLI 执行并落盘报告。

### 红线

- 禁止用 shell sleep 当长定时器（原版明令，且占死会话）。
- 每个注册任务必须告知用户任务名与删除命令。
- 不把密钥/敏感信息写进任务脚本。

## 与原版的差异

- 原版到点会用 Prompt 唤醒 agent 继续对话；本版只能执行脚本+落盘结果，无法自动唤醒对话。
- TimerCondition 早取消、IsDaemon 常驻由 schtasks 的 /sc once|minute|hourly|daily 组合近似。
