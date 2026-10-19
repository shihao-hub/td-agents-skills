---
name: kb-windows-atomic-replace-held-file
description: Windows 上「临时文件 + 原子 rename」被外部程序持有的文件拒绝（EPERM / Win32 5），表现为上层设置静默丢失：点了没反应、自动回滚、刷新不生效、HTTP 200 但 revision 不变。含 Restart Manager 反查持有者、同目录对照实验、编辑器缓冲区与 ACP agent 会话及 SQLite 孤儿行定位、客户端本地断言兜底。
---

# 65-Windows文件被外部程序持有导致原子替换失败与上层写入静默丢失排障指南

> **一句话**：**「文件能写」≠「文件能被替换」**。Windows 上原子替换要求目标文件可删除；只要有任何进程持有句柄（尤其是内存映射），`MoveFileEx(REPLACE_EXISTING)` 直接 `ACCESS_DENIED`，而多数应用把它当成"写失败"只记在自己的日志里 —— 用户侧看到的就是「设置点了没反应」。
>
> 本条目源自一次真实排障：DSH（DeepSeek Harness）`dsh web` 的外观/设置写入全部静默丢失，最终定位到 **Zed 的 ACP agent 会话（opencode）把 `~/.dsh/profiles/<profile>/cordis.patch.yml` 当成了上下文文件**，Zed 主进程因此长期持有该文件句柄。  
> **上游 Issue 追踪**：该缺陷已正式向 Zed 官方上游建档追踪：[zed-industries/zed#65845](https://github.com/zed-industries/zed/issues/65845)。

---

## 一、现象与报错直击

### 1.1 用户侧症状（最容易被误判成"应用 bug"）

| 现象 | 说明 |
|---|---|
| 点「深色/浅色」或插件开关，**界面闪一下又跳回原值** | 上层先做本地乐观更新，宿主把旧值推回来后又被覆盖 |
| 刷新页面后设置**全部回到旧值** | 从头就没落盘 |
| 只有**部分效果**生效（如调色板生效、深浅基座不生效） | 客户端侧覆盖层与持久化偏好是两条路径，前者不写文件 |
| 界面**没有任何报错** | 失败发生在服务端 RPC 层，客户端没把它冒泡到 UI |
| 编辑器标签页里**看不到**、任务管理器里也**看不出**谁占着 | 句柄不是 UI 概念 |

### 1.2 服务端/RPC 层原文（真正的证据）

```text
settings/rejected: EPERM: operation not permitted, rename
'C:\Users\<user>\.dsh\profiles\web\cordis.patch.yml.8c69325781ba.tmp' ->
'C:\Users\<user>\.dsh\profiles\web\cordis.patch.yml'
```

```text
# 原生探测同一操作（temp → 覆盖目标）
rename FAILED (win32 5 Access is denied)
# 对照组：同目录下没人占用的文件，一样的 temp → rename
rename OK
```

### 1.3 文档其实"根本没动过"

对设置文档做一次读取再写入，`revision` 与 `user` 字段纹丝不动：

```text
before      value{preference:"system"}  user{}                  revision 0
set         ok:true                                             （HTTP 200，RPC 层失败）
after set   value{preference:"system"}  user{}                  revision 0    ← 完全没落盘
```

> **判据**：HTTP 200 ≠ 写入成功。远程 RPC 常把"业务失败"也包成 200，真实结果看响应信封里的 `ok/error` 与 `revision` 是否递增。

---

## 二、底层根因剖析

### 2.1 Windows 的"原子替换"到底要求什么

| 操作 | 需要什么 | 被句柄持有时的结果 |
|---|---|---|
| 直接覆写（`CreateFile` + `WriteFile`，`FileShare` 全开） | 目标可写 | **通常成功** —— 这就是"文件明明能写"的错觉来源 |
| 原子替换（临时文件 + `MoveFileEx(…, MOVEFILE_REPLACE_EXISTING)`） | 目标需可 **DELETE**（并在多数实现里要求无映射/无独占句柄） | `ERROR_ACCESS_DENIED`（win32 **5**） |
| 删除目标（`DeleteFile`） | 同上 | 同上 |

- Node.js 的 `fs.renameSync/fs.promises.rename` 走 libuv 的 `uv_fs_rename` → `MoveFileExW`，**win32 5 被映射成 `EPERM`** —— 于是错误信息长成 `EPERM: operation not permitted, rename ...`，看起来像权限问题，其实是**持有问题**。
- 关键鉴别点：用 `CreateFileW(DELETE, FILE_SHARE_READ|WRITE)` 探测**单独**拿到 DELETE 权限可能成功，但真正的替换仍可能失败（典型是文件被**内存映射**时）。**别用"能不能打开"当判据，要用"能不能替换"。**

### 2.2 为什么所有界面都看不到占用者

句柄是内核对象，不体现在：任务管理器的"资源占用"、编辑器的标签栏、应用自己的日志。**唯一可靠的路径是"按文件反查进程"**（见 3.2 的 Restart Manager 脚本），或者做"同目录对照实验"把"目录/ACL 问题"排除掉。

### 2.3 本例的完整因果链（可直接照抄的推理顺序）

```text
用户在 Zed 的 agent 面板里让 opencode 排查「DSH 设置文件被占」
   └─ 会话把 ~/.dsh/profiles/<profile>/cordis.patch.yml 收进上下文
        └─ Zed 主进程反复执行 acp_thread → opening file（Zed.log 原文）
             └─ Zed 长期持有该文件句柄
                  └─ DSH 的「临时文件 + 原子 rename」写设置 → win32 5 → EPERM
                       └─ 设置静默丢失（客户端乐观更新 → 被旧值覆盖）
```

证据三件套（都实测过）：

1. **持有者反查**：Restart Manager 报 `holder pid=<Zed主进程PID> app="Zed"` → 注意**持有者是主程序**，不是它拉起的 agent 子进程（`opencode.exe` 只是触发原因）；
2. **触发者日志**：`Zed.log` 里反复出现
   ```text
   ERROR [crates/acp_thread/src/acp_thread.rs:1716] opening file "C:\Users\<user>\.dsh\profiles\desktop"
   ```
   即 **agent（ACP）线程**在开这些路径 —— 这也是它"隐藏在界面上看不到"的原因；
3. **持久化残留**：Zed 的 `db.sqlite` 里 `editors` 表还留着这些文件的记录（`contents=NULL`，没有未保存内容），`items` 表里却**没有任何条目** → 于是"有句柄、没标签页"。

### 2.4 为什么"关标签页""重启程序"都没用

| 动作 | 为什么无效 |
|---|---|
| 在编辑器里 `Ctrl+W` 关标签页 | 没有标签页可关：句柄来自 **agent 会话上下文**（或孤儿 editor 行），不是打开的 tab |
| 重启编辑器（`restore_on_startup: last_session` 默认） | 会话状态会被**恢复**：窗口、缓冲区、以及按项目持久化的 **agent 线程**都会回来 → 句柄随即重新建立 |
| 只结束 agent 子进程（如 `opencode.exe`） | 句柄挂在**主程序**上，杀子进程不释放 |
| 关掉"最近文件"里的条目 | 最近文件列表不持有句柄，删它没有意义 |

---

## 三、标准抢救与修复 SOP

### Step 0 · 先判定"是不是被持有"（30 秒）

```powershell
# 同目录对照实验：目标 vs 同目录一个无人占用的文件，做同一种 temp → rename
# 目标失败 + 对照成功 ⇒ 目录/ACL 没问题，是"文件被持有"
$target = "$env:USERPROFILE\.dsh\profiles\web\cordis.patch.yml"
$dir = Split-Path $target
$tmp = Join-Path $dir ("probe-" + [guid]::NewGuid().ToString('N').Substring(0,8) + ".tmp")
Copy-Item $target $tmp -Force
cmd /c move /Y "$tmp" "$target"     # 失败时看错误码；这一步等价于 DSH 的原子替换
Remove-Item $tmp -Force -ErrorAction SilentlyContinue
```

### Step 1 · 按文件反查持有者（免安装，Restart Manager）

```powershell
# 保存为 find-holder.ps1，用法：.\find-holder.ps1 -Path <文件>
param([Parameter(Mandatory=$true)][string]$Path)
$code = @'
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public static class HolderProbe {
  [StructLayout(LayoutKind.Sequential)] public struct RM_UNIQUE_PROCESS { public int dwProcessId; public System.Runtime.InteropServices.ComTypes.FILETIME ProcessStartTime; }
  [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)] public struct RM_PROCESS_INFO {
    public RM_UNIQUE_PROCESS Process;
    [MarshalAs(UnmanagedType.ByValTStr, SizeConst=256)] public string strAppName;
    [MarshalAs(UnmanagedType.ByValTStr, SizeConst=64)] public string strServiceShortName;
    public int ApplicationType; public uint AppStatus; public uint TSSessionId; [MarshalAs(UnmanagedType.Bool)] public bool bRestartable; }
  [DllImport("rstrtmgr.dll", CharSet=CharSet.Unicode)] static extern int RmStartSession(out uint h, int f, string k);
  [DllImport("rstrtmgr.dll")] static extern int RmEndSession(uint h);
  [DllImport("rstrtmgr.dll", CharSet=CharSet.Unicode)] static extern int RmRegisterResources(uint h, uint n, string[] files, uint na, RM_UNIQUE_PROCESS[] a, uint ns, string[] s);
  [DllImport("rstrtmgr.dll")] static extern int RmGetList(uint h, out uint needed, ref uint count, [In,Out] RM_PROCESS_INFO[] infos, ref uint reasons);
  public static string[] Find(string path) {
    uint h; if (RmStartSession(out h, 0, Guid.NewGuid().ToString()) != 0) return new[]{"rm-session-failed"};
    try {
      if (RmRegisterResources(h, 1, new[]{path}, 0, null, 0, null) != 0) return new[]{"rm-register-failed"};
      uint needed = 0, count = 0, reasons = 0;
      int res = RmGetList(h, out needed, ref count, null, ref reasons);
      if (res != 234 && res != 0) return new[]{"rm-list-failed"};
      if (needed == 0) return new[]{"(no holder reported)"};
      var infos = new RM_PROCESS_INFO[needed]; count = needed;
      if (RmGetList(h, out needed, ref count, infos, ref reasons) != 0) return new[]{"rm-list2-failed"};
      var rows = new List<string>();
      for (int i = 0; i < count; i++) rows.Add("pid=" + infos[i].Process.dwProcessId + " app=\"" + infos[i].strAppName + "\"");
      return rows.ToArray();
    } finally { RmEndSession(h); }
  }
}
'@
Add-Type -TypeDefinition $code -Language CSharp | Out-Null
"exclusive-open: " + (try { $fs=[System.IO.File]::Open($Path,'Open','ReadWrite','None'); $fs.Close(); 'free' } catch { 'held' })
[HolderProbe]::Find($Path) | ForEach-Object { "  $_" }
```

### Step 2 · 按持有者类型处置

| 持有者类型 | 识别特征 | 处置 |
|---|---|---|
| **编辑器/Agent 会话上下文**（本例） | 持有者是主程序；`Zed.log`/等价日志里出现 `acp_thread … opening file "<配置路径>"`；DB 里有对应会话记录 | **在 Agent 面板删掉那个会话**（尤其引用了配置目录的），再用 Step 3 验证；不要只关标签页 |
| **编辑器缓冲区**（真的开着） | API 里能列出该文件的 editor/tab 条目 | 打开成可见标签 → `Ctrl+W` 关闭；随后确认"下次启动不再恢复" |
| **孤儿持久化实体** | DB 里有该文件的 editor/缓冲区记录，但对应的 items/panes 为空 → "有句柄、无标签" | 备份 DB（`.db` + `-wal` + `-shm`）后**删除该记录**；随后重启验证 |
| **自身/宿主进程**（自杀式占用） | 反查出来是自己的服务进程 | 检查应用是否正确关闭文件句柄 |
| **安全软件扫描/索引器** | 占用**时有时无**，采样可见 | 加白名单；或应用侧做有限重试 |

### Step 2b · 先量清楚"被挡的到底是写还是替换"（决定能不能不关对方就修好）

被持有 ≠ 内容写不进去。同一刻对目标分别测四件事：

```powershell
$p = "$env:USERPROFILE\.dsh\profiles\web\cordis.patch.yml"; $d = Split-Path $p
# ① 独占打开（能开 = 完全没人持有）
try { [IO.File]::Open($p,'Open','ReadWrite','None').Close(); 'share-none : free' } catch { 'share-none : HELD' }
# ② 只请求写权限（能开 = 内容本身写得进去）
try { [IO.File]::Open($p,'Open','Write','ReadWrite').Close(); 'open-write : OK' } catch { 'open-write : DENIED' }
# ③ 上层真实动作：temp -> rename 覆盖目标
$t = Join-Path $d ('p-'+[guid]::NewGuid().ToString('N').Substring(0,8)+'.tmp'); Copy-Item $p $t
cmd /c move /Y "$t" "$p"; "replace    : exit=$LASTEXITCODE"
# ④ 同一动作换成新名字（对照：证明目录/ACL 没问题，问题只在那一个目标）
Copy-Item $p $t; cmd /c move /Y "$t" "$d\fresh-$(Get-Random).tmp"; "fresh-name : exit=$LASTEXITCODE"
Remove-Item $t -Force -ErrorAction SilentlyContinue
```

（还要 `DELETE` 那一格时用 `CreateFileW(path, DELETE=0x00010000, FILE_SHARE_READ|WRITE|DELETE, …)` 探测；
完整探针与实测矩阵见 `dsh-local-plugins/docs/dsh-settings-document-lock.md` 第八节。）

| ② 写权限 | ③ 替换 | 结论 | 处置 |
|---|---|---|---|
| OK | 失败 | 对方只是**打开/映射**着，并没有禁止写入（本类问题最常见的形态） | **不必关对方**：让写入路径退化为"原地覆写 + 写前备份"，见 Step 4 第 2 条 |
| DENIED | 失败 | 连内容都进不去 | 只能先解除占用（Step 2），或把存储挪到别的路径 |
| OK | OK | 不是持有问题 | 查 ACL / 只读属性 / 磁盘错误 / 上层逻辑 |

> 这一格实测的价值：它把"必须让用户关掉编辑器"从**前提**降级成**可选项**。
> 上层若坚持"原子替换不可退化"，那就等于要求用户为一次设置修改关掉整个 IDE —— 这本身是 bug。

### Step 2c · 想连占用一起摘掉：换文件对象，而不是动对方句柄

若"写入退化"还不够（例如你希望这个路径彻底不再被占），可以在**不关对方程序、不改它任何配置**的前提下
解开占用 —— 前提是对方的句柄**共享了删除权限**（Step 2b 里 `delete-access open: GRANTED` 就是判据）：

| 原语 | 说明 |
|---|---|
| `ReplaceFileW(target, staged, NULL, REPLACEFILE_IGNORE_MERGE_ERRORS, 0, 0)` | Windows 专为"替换被别人打开着的文件"提供的 API；实测在被持有的文件上 OK |
| `DeleteFile(target)` → `MoveFile(staged, target)` | 先摘名、再落名；Node 里就是 `fs.rmSync` + `fs.renameSync` |

两者的本质都是**换掉路径指向的文件对象**：对方那个句柄退化为"指向一个已无名的旧文件"，不再占住这个路径，
而写进去的内容逐字节不变。实测解锁后路径 `free`、普通 rename 恢复、20 秒采样仍为 free。

注意事项（都要写进工具里）：

- **内容必须逐字节保真**；"摘名"与"落名"之间若失败，必须立刻用内存里的原字节把名字补回来，否则文件会消失；
- 对方的句柄**没有**共享删除权限时 `DeleteFile` 会失败 —— 此时不要硬来，退回 Step 4 的写入退化；
- 这是"路径级解锁"，不是"让对方松手"：对方下次重新打开该路径，占用就回来，再跑一次即可；
- 参考实现与端到端测试：`dsh-local-plugins/patches/unlock-settings-document.mjs`。

> 顺带修正一个常见猜测：这类占用**不是**内存映射的特权。受控四臂实验里，"普通句柄 + share=读|写|删"
> 与线上签名完全一致；而"只有映射、文件句柄已关"时替换反而是成功的。真正顽固的是
> `MoveFileEx(REPLACE_EXISTING)` 要求"目标没人开着"—— 它与共享模式无关，Node 的 `fs.rename` 走的正是这条路。

### Step 3 · 端到端验证（别只看"文件能打开"）

```powershell
# 45 秒采样：每 3 秒做一次与上层完全相同的替换操作，统计成功率并打印持有者
# 期望：修复后 15/15 OK；未修复：0/15 FAIL 且 holder 稳定指向同一进程
```

若上层是 RPC 服务，再补一次"读—写—读"探针：

```text
settings/describe → 记下 revision
settings/mutate   → 看响应信封 ok/error（HTTP 200 不代表成功）
settings/describe → revision 必须 +1，user 里必须出现刚写的字段
```

### Step 4 · 拿不到对方配合时的上层兜底（工程建议）

1. **失败必须可见**：把 `settings/rejected` / `EPERM` 冒泡到 UI（toast 或行内提示），禁止静默回滚；
2. **写入退化**：rename 遇 `EPERM/EACCES` 时退化为"直接覆写 + 写前备份"，或做有限重试后给出明确错误；
   - **"有限重试"救不了持续占用**：重试预算是给瞬时干扰（索引器、杀软）的，8 次 / ~1.3s 对一个
     **整场会话都不松手**的句柄毫无意义 —— 必须有"重试耗尽之后"的那条路，否则每次写入都从头重试再失败；
   - **参考实现**（本机已验证 17/17）：仅在"Windows 替换类拒绝（`EACCES/EBUSY/EPERM`）+ 重试耗尽"时，
     写 `<file>.bak`（存原字节）→ `r+` 打开目标、偏移 0 写入 → `truncate` 到新长度 → `fsync`
     → 按调用方 `mode` 做 `chmod` → 成功即返回；任一步失败则抛出**原错误**
     （不把"确实写不进去"伪装成成功，保持原行为）；
   - **退化必须可见**：`process.emitWarning(…, { code: 'DSH_ATOMIC_WRITE_INPLACE_FALLBACK' })` 报出文件名，
     并留一个环境变量开关关掉它 —— 因为这一步**放弃了原子性**（读方可能看到半份文件）；
   - **别把退化写进主路径**：无人占用时必须仍走 rename（否则平白降低原子性），4.1 有专门断言盯这个。
3. **别让客户端"假装成功"**：本地乐观更新后必须有一次"文档回读确认"，否则用户永远分不清"生效了没有"；
4. **客户端自保**（当配置本身写不进去时）：把关键渲染改成"本地断言"，例如主题把深色基座在客户端自行维持，只把"设置没保存"如实告知用户；
5. **存储分离**：用户设置（随时被程序改写）不要和"交给外部编辑器打开的配置文件"是同一份 —— 这是本例的**根因**而非诱因。
6. **判定要读"用户看到的产物"，但别让它替你做"意图"的决定**：上层自维护的状态视图在写入失败时可能
   **乐观前进且永不回退**，于是出现文档、视图、渲染三分叉（本例实测：文档 `preference: dark`、页面渲染深色、
   运行时视图 `system`+浅色），按视图算出的提示就会在深色页面上声称"基座是浅色"。但反过来，**产物本身也可能
   滞后一拍**（本例 presenter 的 `body[data-ds-dark-theme]` 晚于事件一个渲染帧）—— 若把"我自己该做什么"
   （例如"要不要自维持深色"）也交给产物判定，就会把"我刚下发的状态还没落笔"误读成"写入被拒"（实测踩过：
   行内弹出"写入失败"而文档其实写得好好的）。两条原则：
   **① 用户可见的结论用保守组合**（深色 = 视图为深色 **或** 产物为深色；"基座是浅色"只在两者都同意时说）；
   **② "我要做什么"只依据我自己的状态**；并在事件之后**延迟一拍复判**，把结论纠回真实产物。

> 改第三方安装目录（`node_modules`/asar）属于临时热补，升级即失效，优先级排在 1–5 之后。

---

## 四、验证与防复发闭环

### 4.1 验证断言（缺一不可）

- [ ] 同一替换操作连续采样 **15/15 成功**（不是"某一次成功"）；
- [ ] Restart Manager 报 **`(no holder reported)`**；
- [ ] 上层 RPC：`revision` 递增、`user` 出现新字段；
- [ ] **重启对方程序后仍然 free**（这一步才能证明"不是靠关掉程序临时绕开"）；
- [ ] 界面侧：改动**刷新后仍保持**。
- [ ] 若走了"写入退化"兜底：**无人占用时必须仍走 rename，且不产生 `.bak`**；被占用时内容逐字节不变、
      `.bak` 与写入前原文一致、退化有告警（`DSH_ATOMIC_WRITE_INPLACE_FALLBACK`）。

### 4.2 防复发清单

1. **别把配置目录交给 Agent 当上下文**：让 agent 读 `~/.dsh/…`、`~/.config/…` 这类"活配置"极易造成长期占用；要读就交给一个**只读、用完即关**的通道（或复制到临时目录再给它看）。
2. **会话用完就删**：Agent 线程/会话是按项目持久化的，删掉即可断根；"关窗口"不等于删会话。
3. **配置与手改文件分离**：程序的可写设置别放在用户会用编辑器长期打开的文件里。
4. **写入失败必须可见**（详见 Step 4.1/4.2），否则下次还会被误判成"应用 bug"。
5. **别急着改配置**：本例里"改 `restore_on_startup`"只是权宜，真正原因是 agent 上下文；先按 Step 1 反查，再决定动不动配置。
