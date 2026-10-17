---
name: kb-csc-native-helper-replace-powershell
description: 把常驻轮询型 PowerShell 看护脚本（窗口记忆、看门狗）改造为 .NET 自带 csc 现场编译的原生 Win32 小程序：PowerShell 76.6MB 地板价与每 tick 约 10ms 开销、C# 5 语法约束、/target:winexe 消除 conhost、P/Invoke 与 DPI 虚拟化坑。当常驻 PowerShell 吃 100MB+ 内存时查阅。
version: 1.0.0
created: 2026-10-13
updated: 2026-10-13
---

# 常驻 PowerShell 轮询助手替换为 csc 现场编译原生 Win32 小程序与零 conhost 集成指南

> **适用场景**：某个功能必须有一个"活到目标关闭"的看护进程（记忆窗口几何、监视剪贴板/窗口/文件、当看门狗），实现方式是常驻 `powershell.exe` + `Add-Type` 调 Win32；它稳定吃 100 MB 级内存和几个点 CPU，机器内存本就紧张。要求**行为逐条保持一致**、不引入安装器或重型工具链。

---

## 一、业务场景与生成需求

**场景**：桌面应用自身不持久化窗口状态，需要在进程树外观测并记忆主窗口的大小/位置：启动时套用上次几何，之后持续跟踪用户拖拽并去抖落盘（最大化只记标志、隐藏/停靠位不落盘）。

**为何不能省掉常驻**：观测的终点是"窗口关闭前最后的几何"，除了持续观测没有别的采集时机；所以优化目标不是"取消常驻"，而是**换掉承载常驻的运行时**。

**旧实现成本（同机实测）**：

| 项 | 实测值 |
| :-- | :-- |
| 工作集 / 私有 | 106.0 MB / 81.4 MB |
| conhost 子进程 | +8.3 MB |
| CPU | **4.05% 单核**（28 分钟累计 91.8s，与窗口是否变化无关） |

**交付目标**：同等行为下把常驻成本降一个数量级，且**零系统依赖新增**（只用 Windows 自带编译器）。

---

## 二、技术难点与底层剖析

### 1. PowerShell 的地板价：76.6 MB，脚本怎么写都省不掉

实测裸进程：

```powershell
Start-Process powershell.exe -ArgumentList '-NoProfile','-NonInteractive','-Command','Start-Sleep -Seconds 4' -PassThru
# 稳定后 WorkingSet64 ≈ 76.6 MB
```

再看 `Get-CimInstance`（加载 CIM 栈）与 `Add-Type`（运行时把 C# 编译成内存程序集，加载 CodeDom/编译器程序集）之后就是 106 MB。**在 PowerShell 里做微观优化，最多省 CPU；内存地板价动不了**——这是"该换运行时"的判定依据。

### 2. 每 tick 真的贵：250ms 轮询 ≈ 每次 10ms

4 次/秒 × 每次约 10ms ≈ 4% 单核。单次开销来自 cmdlet 与反射：

```powershell
$r = New-Object DshWindowMemory+RECT     # 反射式创建对象，每次 1~3ms
$p = Get-Process -Id $MainPid            # cmdlet + 打开进程句柄
$t = Get-Date
```

同样逻辑在原生代码里是几次 P/Invoke，**微秒级**。反推公式：`单核占用% ≈ (每 tick 毫秒数 × 1000 / 轮询间隔毫秒) / 10`，用它可以先估算值不值得改。

### 3. csc 现成可用，但只认 C# 5

```text
C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe   ← Win10/11 自带，无需任何 SDK
C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe     ← 32 位回退
```

该版本编译器**只支持 C# 5**，必须回避：

- 字符串插值 `$"..."`（C# 6）
- 表达式体成员 `public int X => ...;`（C# 6）
- 空条件运算符 `?.` / `?[]`（C# 6）
- `nameof`（C# 6）
- 自动属性初始化器 `public int X { get; set; } = 1;`（C# 6）

安全写法：`string.Format(CultureInfo.InvariantCulture, ...)`、普通字段初始化器 `public int WaitSec = 180;`、匿名委托 `delegate(...) { }`、`var`。

### 4. conhost 的真凶：Node 的 `windowsHide` 只是"隐藏"，不是"不分配"

这是最容易误判的一点。Node 的 `windowsHide: true` 走的是 libuv `UV_PROCESS_WINDOWS_HIDE` → `STARTF_USESHOWWINDOW` + `SW_HIDE`：**控制台照样被分配，`conhost.exe` 照样出现**（约 8 MB），只是看不见。

真正不分配控制台要靠 PE 子系统：

```powershell
csc /nologo /target:winexe /platform:x64 /optimize+ /out:helper.exe helper.cs
#                        ^^^^^^^^^^^^^^^ GUI 子系统：完全不分配控制台 → 零 conhost
```

结论：**常驻小工具一律编 `/target:winexe`**。副作用检查：GUI 子系统进程在 Node 用管道 spawn 时，`Console.WriteLine` 仍能写出（stdout 句柄是继承的重定向管道），所以 `-SelfTest` 这类自检输出不会丢。

### 5. 每 tick 的隐藏大头：每轮新建 `Process` 对象

`Process.GetProcessById(pid)` 每次要打开句柄、分配对象、查询、关闭，约 0.2~0.5ms。250ms 一轮就是 0.1~0.2% 单核——**改完运行时它仍可能是最大的单项**。

替代方案（实测 0.195% → 0.000%）：

```csharp
[DllImport("kernel32.dll", SetLastError = true)] private static extern IntPtr OpenProcess(uint access, bool inherit, int pid);
[DllImport("kernel32.dll")] private static extern uint WaitForSingleObject(IntPtr h, uint ms);

IntPtr parent = OpenProcess(0x00100000 /* SYNCHRONIZE */, false, mainPid);   // 只开一次
// 循环里：h==Zero 时回退 Process 查询；否则
bool alive = WaitForSingleObject(parent, 0) != 0 /* WAIT_OBJECT_0 */;
```

并把"父进程存活"这类低频判据**降频**（每 ~2s 查一次），高频只保留窗口是否还存在（`IsWindow`，纯 P/Invoke）。

### 6. Win32 P/Invoke 坑清单

- `EnumWindows` 的回调委托必须 `GC.KeepAlive(cb)`，否则委托被回收后枚举行为不可预期；
- 结构体用 `[StructLayout(LayoutKind.Sequential)] struct RECT { int Left, Top, Right, Bottom; }` + `out RECT`；
- 只改几何不动 Z 序、不抢焦点：`SetWindowPos(h, IntPtr.Zero, x, y, w, h, SWP_NOZORDER|SWP_NOACTIVATE)`（`0x4|0x10`）；
- 判别"隐藏窗口停靠位"要用虚拟屏包围盒做交集，而不是硬编码坐标（Chromium 用过 `-25600,-25600` 也用过 `-32000,-32000`）：

```csharp
int vx = GetSystemMetrics(76), vy = GetSystemMetrics(77);   // SM_*VIRTUALSCREEN
int vw = GetSystemMetrics(78), vh = GetSystemMetrics(79);
int ix = Math.Min(x + w, vx + vw) - Math.Max(x, vx);
int iy = Math.Min(y + h, vy + vh) - Math.Max(y, vy);
return w >= 120 && h >= 80 && ix >= 120 && iy >= 40;
```

- 窗口可缩放时有**最小跟踪尺寸**（实测 `159x27` 会被系统撑成 `159x39`），写测试用例时别假设任意小尺寸能成立。

### 7. DPI 虚拟化：**不要**加 DPI manifest

非 DPI-aware 的进程拿到的是被 Windows 虚拟化后的坐标（本机 2560×1600 @125% → 进程视角 2048×1280）。旧 PowerShell 宿主同样不是 DPI-aware，所以它读写的 x/y 是一致的一套坐标。**改造时若顺手加了 `dpiAware` 或调用 `SetProcessDpiAwareness`，同一个 x/y 会被解释到另一个坐标空间，缩放屏上位置就会明显错位**——"改完更准"的直觉在这里是陷阱。保持无 manifest 才是行为一致。

### 8. 内存地板：CLR 约 20 MB

实测该原生 helper 常驻 **19.7 MB WS / 12.5 MB 私有**（.NET Framework CLR + P/Invoke），相比旧版 106 MB 是 5.4 倍改善，但**达不到"个位数 MB"**。要 ≤8 MB 只能换 Go/Rust（本机 `go`/`rustc` 均可用），代价是给插件引入新工具链依赖——按"是否值得为最后 15 MB 加一个构建依赖"来权衡。

---

## 三、标准自动化流水线与代码实现

### 1. 宿主侧：编译缓存 + 绝不阻塞启动（ESM）

```js
const STATE_DIR  = path.join(process.env.LOCALAPPDATA || os.tmpdir(), '<app>-helper');
const HELPER_EXE  = path.join(STATE_DIR, 'helper.exe');
const HELPER_HASH = path.join(STATE_DIR, 'helper.sha256');
const CSC_CANDIDATES = [
  path.join(process.env.WINDIR || 'C:\\Windows', 'Microsoft.NET', 'Framework64', 'v4.0.30319', 'csc.exe'),
  path.join(process.env.WINDIR || 'C:\\Windows', 'Microsoft.NET', 'Framework',   'v4.0.30319', 'csc.exe')
];

function sourceDigest() {                       // 用源码 SHA-256 判断是否需要重编
  return crypto.createHash('sha256').update(fs.readFileSync(helperSourcePath())).digest('hex');
}

function compileHelper(digest) {
  return new Promise((resolve) => {
    const csc = CSC_CANDIDATES.find((c) => fs.existsSync(c));
    if (!csc) { logLine('helper compile skipped: no csc.exe'); resolve(null); return; }
    const staged = HELPER_EXE + '.new';         // 先编到 .new，成功再 rename（原子）
    const child = spawn(csc, ['/nologo', '/target:winexe', '/platform:x64', '/optimize+',
                              `/out:${staged}`, helperSourcePath()],
                        { stdio: ['ignore', 'ignore', 'pipe'], windowsHide: true });
    // exit 0 且产物存在 → rename + 写 sha256 侧车；否则删 .new、记日志、返回 null
  });
}

let helperPromise;
export function ensureHelper() {                // 单飞：一个进程只编译一次
  if (helperPromise) return helperPromise;
  helperPromise = (async () => { /* 指纹命中直接返回；否则编译 */ })();
  return helperPromise;
}
```

三条硬规则：**异步编译**（`apply()` 立刻返回，绝不阻塞宿主启动）、**失败降级只记日志**（功能是化妆品，不能拖垮宿主）、**产物只落 `%LOCALAPPDATA%`**（不污染插件/仓库工作区，避免 `git status` 噪声）。强制重建用环境变量（如 `DSH_<APP>_REBUILD=1`）。

### 2. 原生侧：`helper.cs` 骨架要点

```csharp
// 1) 参数解析：int.Parse(v, CultureInfo.InvariantCulture)，未知参数忽略
// 2) 父进程白名单：Process.GetProcessById(pid).MainModule.FileName + 正则（比 CIM/WMI 便宜且够用）
//    - 提供 -AllowExeName 作为测试专用替换项，生产路径留空
// 3) 相位一（一次性）：轮询等待目标窗口出现 → 套用保存几何（回读并记 log）
// 4) 相位二（常驻）：每 tick 只做 IsWindow/IsIconic/IsWindowVisible/IsZoomed/GetWindowRect
//    父进程存活降频到每 ~2s，用缓存的 OpenProcess 句柄
// 5) 状态文件：临时文件 + File.Replace（不存在则 File.Move）原子替换
//    编码与行尾必须与旧实现字节一致（旧 PS 的 Set-Content -Encoding UTF8 产出 UTF-8 BOM + CRLF）
// 6) 日志：追加前判 >65536 就清空；时间戳 DateTimeOffset.Now.ToString("o") 对齐 PS 的 Get-Date -Format o
```

**行为契约清单**（改造前先把旧实现的分支逐条列出来，改完逐条对）：屏幕外/退化几何不落盘、历史坏值删除而非套用、最大化只记标志、最小化/隐藏跳过、去抖间隔、日志文案逐字保留（README 的排障表才不会失效）。

### 3. 宿主的 spawn（保持"不 detached"）

```js
const child = spawn(helperExe, ['-MainPid', String(mainPid), '-StateFile', stateFile],
                    { stdio: 'ignore', windowsHide: true });
child.on('error', (e) => logLine('helper spawn failed: ' + e.message));
child.unref();
```

`detached: true`（`DETACHED_PROCESS`）会让控制台程序在控制台初始化阶段直接静默退出（旧实现已踩过），**不要用**。用 `windowsHide` 即可：不可见、随父进程结束而结束。

---

## 四、交付验证与工程扩展建议

### 1. 两层回归测试（零依赖、`node` 直跑）

**第一层：`helper.exe -SelfTest` 纯逻辑自检**（不建窗口、不碰真实状态文件）：

- 守卫判据矩阵：`(-25600,-25600,159,27)`、`(-32000,-32000,199,34)`、退化尺寸、远屏外 → 必须 false；典型几何、最小允许、负原点多屏 → 必须 true；
- 状态文件字节格式：断言含 `EF BB BF`（BOM）且以 `0D 0A` 结尾；
- 往返与覆盖：写入→读回字段一致、覆盖已有文件走替换路径、`.tmp` 不残留；
- 容错：无 BOM / 无末尾换行 / 坏 JSON → 只记日志返回 null，绝不抛异常。

**第二层：真窗口回归测试**（用夹具窗口，自建、必然由自己持有）：

- 场景：恢复+去抖写回、首次运行、坏值拒绝并删除、屏幕外守卫不落盘、最大化只记标志、窗口销毁后自行退出；
- **断言要看"窗口真的在哪"**：夹具把自身真实几何打到 stdout，用第三方证据而不是 helper 自己的日志；
- 测试专用开关：`-AllowExeName ^test-window\.exe$`、`-LogFile <临时路径>`（否则会与生产日志串写导致断言抖动）；
- 收尾必须 `taskkill /PID <pid> /T /F` 连子孙一起收，并断言无残留。

**为什么不用记事本当靶子**：Windows 11 上 `notepad.exe` 只是壳，真正持有窗口的是 WindowsApps 里的商店包进程，按 pid 找不到窗口——测试会变成对系统版本的隐式依赖。夹具窗口才是确定性的。

### 2. 验收数字（同机实测）

| 指标 | 旧（常驻 PowerShell） | 新（csc 原生小程序） |
| :-- | :-- | :-- |
| 工作集 | 106.0 MB | **19.7 MB** |
| 私有内存 | 81.4 MB | 12.5 MB |
| conhost | +8.3 MB | **无** |
| CPU（8 秒采样） | 4.05% | **0.000%** |

### 3. 可复用范围

任何"常驻轮询/看护"型 PowerShell 都可套这条路：窗口状态记忆、剪贴板监听、进程看门狗、目录监视、定时探活。判定顺序建议：

1. 先测 PowerShell 地板价（裸进程 WS）与每 tick 耗时 → 估算收益；
2. 若常驻且每 tick ≥1ms，就换原生；
3. 用 `-SelfTest` + 夹具窗口把行为钉死，再谈性能数字。

### 4. 相关条目

- `011_win_conhost_fix_计划任务控制台委托闪窗与conhost注册.md`：conhost 与控制台委托的另一条战线（计划任务闪窗）；
- `052_win_conhost_fix_PE控制台委托DefTerm断层与MCP无窗口镜像.md`：PE Subsystem 2（GUI 子系统）实现无窗口运行的同源机制；
- `019_win_mem_fix_Win内存防死机与Pagefile提交归因优化.md`：内存归因与提交内存分析方法；
- `056_agent_dsh_fix_DSH挂载MCP包装层内存膨胀治理与直连改造.md`：同一轮内存治理里的 MCP 进程数侧。
