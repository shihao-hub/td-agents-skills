---
name: kb-zed-acp-prompt-response-loss
description: |
  Zed 编辑器外接 ACP Agent（如 antigravity-acp）在经历 600+ 步长会话或 502 网络断线重试后，模型文本已全部输出但界面永久转圈、正文末尾挂三点脉冲、输入框死锁无法发送下一条、点击停止报错 Method not found 的全链路根因剖析与抢救 SOP。
version: 1.0.0
created: 2026-10-20
updated: 2026-10-20
id: "083"
domain: ide
scope: zed
type: fix
slug: "Zed外接ACP长会话生成完毕转圈卡死与PromptResponse丢失排障"
status: verified
last_verified: "2026-10-20"
compatibility:
  os: ["windows"]
invocation:
  auto_trigger: true
---

# ide_fix_083_Zed外接ACP长会话生成完毕转圈卡死与PromptResponse丢失排障

> **条目定位**：**Type A 疑难排障与 ACP 协议状态机深度复盘条目**  
> **危险评级**：★★★☆☆（AI 正常生成代码并落盘，但宿主前端交互链路假死，导致用户陷入发一条重启一次的恶性循环）  
> **验证环境**：Zed 1.24.4+stable (Windows x64)、`antigravity-acp v1.4.1` (Gemini 3.8 Flash)、Python 3.11、PowerShell 5.1。  
> **关联条目**：会话提取与 SQLite 抢救见 `025_ide_zed_fix_Zed会话丢失提取与SQLite解析抢救.md`；ACP 进程池累积与内存治理见 `023_ide_zed_fix_Zed与IDEA外接ACP代理失效与进程堆积.md`；外部 ACP 线程不自动命名见 `077_ide_zed_fix_Zed外部ACP线程不自动命名与首消息标题链路.md`。

---

## 一、现象直击与典型症状

在 Zed 中使用外接 ACP Agent（如 `antigravity-acp`）进行中大型项目开发时，遭遇以下典型症状：

1. **“假死式”完成**：
   用户在 Zed 的 Assistant / Composer 面板中发送一条指令，AI 在几秒到几分钟内输出了完整的思考、工具调用与 Markdown 最终回复（代码已成功写入并编译通过）；
2. **正文末尾脉冲与死锁转圈**：
   尽管文本已经 100% 渲染在屏幕上，但：
   - 回复内容最底部始终挂着三个小点 `⋮`（思考/生成脉冲动画）；
   - 左侧历史会话列表对应会话条目持续挂着旋转图标 `⟳`；
   - 底部输入框变灰并处于禁用锁定状态，无法聚焦也无法敲回车发送下一条消息；
3. **取消按钮拒绝服务**：
   用户点击右下角红色的“停止生成”按钮时，不仅无法中止转圈，后台还抛出未处理异常：
   ```text
   WARN [agent_servers::acp::transport] agent stderr: Unhandled error while handling notification method=$/cancel_request
   acp.exceptions.RequestError: Method not found
   ```
4. **被迫频繁重启**：
   除非彻底关闭退出 Zed 并重新打开，否则该会话永远停留在“转圈”状态；而重启后发送新消息，生成完毕后又立即再次卡死。

---

## 二、误区纠偏与侦破复盘

排查过程中极易产生三个假阳性误区：

| 假阳性误区 | 为什么是错的？（确凿反证） |
| :--- | :--- |
| **误区 1：以为是账号欠费或 Token 失效** | **反证**：调用 `.\agyquota.exe --raw` 查询，Google Cloud Code 接口稳定返回 `HTTP 200`，`remainingFraction: 1`（100% 满额），Token 自动续期正常。且屏幕上能清晰打印出 AI 生成的完整文字，证明大模型端早已正确生成完毕。 |
| **误区 2：以为是 Zed 1.24.4 自身全盘死机** | **反证**：此时新建一个纯文本会话（New Thread），连续提问 3 次均能毫秒级回复并正常解锁输入框；编辑器本体、LSP、终端面板均工作正常，仅特定历史会话必定触发死锁。 |
| **误区 3：以为是任务本身太复杂导致模型假死** | **反证**：即使在该长会话中发送极其简单的纯文本“你好”，模型也会在回复完一句话后卡死在末尾的 `⋮`。问题与当前单次 Prompt 的复杂度无关，而是与**该会话的历史状态积压**强相关。 |

---

## 三、全链路架构机理与代码行级根因剖析

问题的本质是：**ACP 协议的会话完成结账包（`PromptResponse`）在服务端被永久挂起，且伴随取消路由缺失。**

### 1. ACP 协议的生命周期契约
在开源标准 **Agent Client Protocol (ACP)** 中：
- 客户端（Zed）向服务端发起 `session/prompt` 请求；
- 服务端在执行期间，流式发送 `session/update`（如 `AgentMessageChunk` 文本增量、`ToolCallProgress` 工具进度）；
- **输入框解锁原则**：客户端必须等待服务端返回最终的 JSON-RPC 响应结构：
  ```python
  schema.PromptResponse(stop_reason="end_turn")
  ```
  只有收到该结账响应，Zed 前端才会终止脉冲动画并解开输入框供用户输入下一轮。

### 2. 服务端卡死在 `receive_steps()`（行号定位）
在 `antigravity-acp` 服务端核心文件 `server.py`：
```python
# C:\Users\<User>\AppData\Local\Temp\_MEI*\google3\cloud\developer_experience\antigravity_extensions\acp_server\server.py:5453
response = await agent.chat(chat_prompt)
async for step in agent.conversation.receive_steps():
    await self._stream_live_step(session_id, step, open_tool_calls, hidden_tool_calls)

# 必须等上述循环彻底退出，才能走到第 5652 行返回结账单：
return schema.PromptResponse(stop_reason=stop_reason)
```

进入 `receive_steps()` 实现（`local_connection.py`）：
```python
# local_connection.py:490-506
while True:
    if self.is_idle and self._processor.step_queue.empty():
        return  # 退出循环的唯一正常出口！
    step_obj = await self._processor.step_queue.get()  # <--- 永远阻塞于此！
    if step_obj is event_processor.IDLE_SENTINEL:
        continue
```

### 3. 底层 Go harness 状态机失步与漏推
- 循环退出的充要条件是：**`self.is_idle == True`** 且队列为空。
- 而 `self.is_idle.set()`（`event_processor.py:967`）**100% 依赖底层 Go 进程 `localharness_external.exe` 在本地 WebSocket 上推送一条 `TrajectoryStateUpdate(state=STATE_FULLY_IDLE)`**。
- **致命失步触发链**：
  1. 当前会话步数达到 **600+ 步**（上下文累积近 25 万 Token，数据库近 10MB）；
  2. 中途遭遇 Google 远端 **502 Bad Gateway / SSL UNEXPECTED_EOF** 网络断线重试（`planner_generator.go:348 retrying in 4s`）；
  3. Go 底层调度器在从异常重试中恢复并输出最终文本（如 Step 613）后，将数据落入 SQLite，但**内部状态机发生时序竞态，漏掉了向 WebSocket 推送 `STATE_FULLY_IDLE` 的事件帧**；
  4. Python 端未收到 `STATE_FULLY_IDLE`，`self.is_idle` 永远为 `False`，在读空 `step_queue` 后死死挂在 `step_queue.get()`；
  5. `server.py` 永远走不到第 5652 行向 Zed 返回 `PromptResponse`；
  6. Zed 认为后端仍在生成，前端死等，正文末尾挂 `⋮` 脉冲，输入框死锁。

### 4. 客户端取消链路失效
当用户在 Zed 界面点击红色“停止生成”按钮时：
- Zed 发送 JSON-RPC 通知 `$/cancel_request`；
- `antigravity-acp v1.4.1` 的服务端路由表根本没有注册该路由，直接抛出 `acp.exceptions.RequestError: Method not found`；
- Zed 取消失败，且缺乏客户端强制断连重置的兜底机制，导致界面永久死锁。

---

## 四、标准解决与抢救 SOP

### SOP 1：开辟轻量新 Thread 绕过失步上下文（立竿见影）
1. 在 Zed 右侧 Assistant 面板顶部，点击 **`+`（New Context / New Thread）**；
2. 保持在当前工作目录继续对话；
3. **原理解析**：新会话步数从 0 起步，没有 600+ 步的膨胀上下文与历史重试包袱，Go 端在生成完后能于 0 毫秒内推送 `STATE_FULLY_IDLE`，Zed 收到 `PromptResponse` 后秒解输入框。旧会长会话已成功落盘代码，直接作为历史归档即可。

### SOP 2：清理脱钩孤儿进程（防止端口与句柄占用）
Zed 重启后，底层由 `localharness` 派生的 MCP 进程（如 `aoci.exe`）容易沦为孤儿进程常驻后台。使用单文件脚本安全清洗：

```powershell
uv run --with psutil python -c "
import psutil

zed_pids = {p.pid for p in psutil.process_iter(['name', 'pid']) if 'zed' in p.info['name'].lower()}
targets = {'aoci.exe', 'agy_acp_server.exe', 'localharness_external.exe'}

for p in psutil.process_iter(['name', 'pid', 'ppid']):
    try:
        if p.info['name'].lower() in targets:
            parent_alive = psutil.pid_exists(p.info['ppid'])
            # 向上追溯是否有活着的 Zed 祖先
            curr = p
            has_zed = False
            while curr:
                try:
                    parent = curr.parent()
                    if parent and parent.pid in zed_pids:
                        has_zed = True; break
                    curr = parent
                except Exception: break
            if not has_zed:
                print(f'Killing orphan: {p.info[\"name\"]} (PID {p.info[\"pid\"]})')
                p.kill()
    except Exception: pass
"
```

### SOP 3：工程最佳实践——“一功能 / 一任务，一开 Thread”
1. **控制会话生命周期**：避免在 Zed Assistant 单个 Thread 中无休止滚雪球超过 100 步；
2. **阶段性拆分**：一个独立功能设计、一次 Bug 排障、或一次重构完成后，主动开新 Thread 接力；
3. **多重收益**：
   - 彻底避免 Go 状态机在大上下文下的时序失步 Bug；
   - 每次交互省去 20+ 万 Token 的冗余网络传输，大幅提速；
   - 极大降低 Google 远端接口遭遇 502/SSL EOF 网络抖动的几率。

---

## 五、验证与复查证据

- **实测验证**：在同一机器与同一 Zed 1.24.4 环境下，开辟新 Thread 后连续发送 3 次复杂编码请求，全部在生成完文本后 **0 毫秒完成结账并解开输入框**，再无转圈脉冲卡死现象；
- **进程树监控**：活动 `localharness_external.exe` 与 `agy_acp_server.exe` 响应平稳，CPU 在闲置时回落至 0%，无任何悬挂死锁。
