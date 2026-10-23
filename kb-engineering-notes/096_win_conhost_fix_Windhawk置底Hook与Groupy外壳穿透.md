---
id: "096"
domain: "win"
scope: "conhost"
type: "fix"
slug: "Windhawk置底Hook与Groupy外壳穿透"
status: "draft"
created: "2026-10-24"
last_verified: null
superseded_by: null
deprecation_reason: null
compatibility:
  os: ["windows"]
falsification_signals:
  - "若系统中未运行 Stardock Groupy 等外部窗口管理软件，则不是外部外壳穿透根因"
  - "若控制台窗口无多标签外壳（无 '+' 或 'v' 按钮），说明未被 Groupy 捕获"
invocation:
  auto_trigger: false
  trigger_keywords: ["conhost", "Windhawk", "Groupy", "置底", "HWND_BOTTOM", "黑框抢焦点", "外壳穿透"]
---

# 96-Windhawk控制台置底Hook与Stardock Groupy外部多标签外壳穿透排障

> [!CAUTION] 未经验证 / 方案草案落盘存档声明
> **明确状态**：本篇手记为排障探索过程中整理沉淀的架构机制推演与技术资产落盘，**未经过端到端最终闭环验证，并未在生产/日常环境中正式实践应用**。本方案探索后已全部撤回，未对系统核心配置做任何持久化改动，仅作为技术储备归档，留作未来遇到同类桌面窗口争用与多标签管理器冲突时作为思路储备与参考。

---

## 一、现象与探索背景

在 Windows 11 环境下使用独立定制版/便携版 Windows Terminal（截断原版商店终端后，系统默认控制台宿主退化为 `conhost.exe`）时，后台调度命令行工具或特定插件（如 CLI、MCP 插件）会频繁弹出纯黑的 `conhost.exe` 控制台窗口。

### 1. 核心诉求与预期边界
* **物理避让诉求**：用户并非单纯要求“禁止夺取键盘焦点”，而是要求后台弹出的黑框在 Z 轴深度上**绝不能遮挡前台软件**（必须直接创建在所有已有窗口的背后，即 `HWND_BOTTOM`），或者保持完全静默最小化；
* **为什么现有方案不满足**：原版 Windhawk 模组（如 *Prevent Focus Stealing*）仅拦截了激活消息（替换为 `SW_SHOWNOACTIVATE`），但在 Z 轴层级上黑框依然处于 Topmost/顶层遮挡视线。

### 2. 探索路径：编写 Windhawk 进程内 Hook 模组（Quiet Conhost）
针对 `conhost.exe` 注入 C++ 模组，直接挂钩 Win32 窗口创建与几何排版核心 API：
* 拦截 `CreateWindowExW`：剥离 `WS_VISIBLE`，追加 `WS_MINIMIZE`；
* 拦截 `SetWindowPos`：剥离 `SWP_SHOWWINDOW`，重写 `hWndInsertAfter` 为 `HWND_BOTTOM`，改写显示标志为 `SWP_NOACTIVATE | SWP_NOZORDER`；
* 拦截 `ShowWindow`、`SetForegroundWindow`、`SetFocus`：全链路阻断前台激活。

### 3. 初步成效与异常复现
* **普通命令验证**：执行常规无父终端的后台命令行（如 `cmd.exe /c ...`），黑框确实成功被压在所有现有软件的底层，不再遮挡前台；
* **异象复现**：当通过某些开发工具拉起带有特定标志的原生二进制服务时，黑框依然顽固地弹到了屏幕最前端，且伴随窗口标签条。

---

## 二、底层机制剖析与冲突溯源

经过对窗口特征与进程链路的交叉比对，揭示了“进程内 Hook”与“系统级外部窗口管理器”之间的致命交互冲突：

### 1. Stardock Groupy 外部多标签外壳全局穿透（核心元凶）

```text
【内部拦截链路】
conhost.exe 内部 CreateWindowExW / SetWindowPos
      │
      ▼ Windhawk Hook 生效：强制剥离激活，重定向至 HWND_BOTTOM（底层）
   [此时 conhost 窗口自身确实位于底层]

【外部管理器突入链路】
Stardock Groupy 外部服务（GroupySrv.exe / CBT 钩子）
      │
      ▼ 全局侦测到系统生成了新的顶层顶级窗口（New Top-level Window）
      │
      ▼ Groupy 触发「自动捕获并合并标签页」行为：
      │   1. 在操作系统顶层创建一个新的 Groupy 容器窗口（带 + 和 v 按钮）；
      │   2. 将底层 conhost.exe 通过 SetParent 强行嵌为 Groupy 外壳的子窗体；
      │   3. Groupy 进程以独立权限调用 SetForegroundWindow / BringWindowToTop 将容器拉至最前！
      │
      ▼ 最终视觉结果：黑框被 Groupy“打捞”并强行置顶激活！
```

* **本质机制**：Windhawk 的 Hook 是**进程内 Hook（In-Process Hook）**，只能管辖 `conhost.exe` 自身发出的 Win32 调用。但 Stardock Groupy 属于**外部宿主进程（Out-of-Process Window Manager）**。任何在进程内部做的降权、置底或去激活，在外部窗口管理器看来都只是“发现了一个新窗口”，外部管理器调用自身的 API 将其包装置顶，内部 Hook 完全被击穿。

### 2. 原生 PE Subsystem 的内核级必然性
* CLI 工具由 Go 或 C 编译时，PE 头部若声明为 `Subsystem: 3 (IMAGE_SUBSYSTEM_WINDOWS_CUI)`，Windows 内核在没有父控制台时具有强制创建控制台的硬逻辑；
* 即使在应用层做无窗口镜像（如将 PE 头改写为 `Subsystem: 2 GUI` 的 `*w.exe` 镜像），虽然能避开控制台创建并彻底断绝 Groupy 的捕获，但会引入“上游更新需重新打补丁与同步”的外部维护成本。

---

## 三、方案推演与架构储备（留作未来使用的推演路径）

本节记录探索过程中编写的完整技术资产与未实践的推演方案，供未来需要时直接提取。

### 路径 A：Windhawk 模组源码归档（`Quiet Conhost v1.0.1` 核心代码）

此模组用于在进程内部强行将目标窗口压入底层或最小化：

```cpp
#undef WCHAR
#include <windows.h>

// 拦截 CreateWindowExW：强行剥离可见性
using CreateWindowExW_t = HWND(WINAPI*)(DWORD, LPCWSTR, LPCWSTR, DWORD, int, int, int, int, HWND, HMENU, HINSTANCE, LPVOID);
CreateWindowExW_t pOriginalCreateWindowExW = nullptr;

HWND WINAPI Hook_CreateWindowExW(DWORD dwExStyle, LPCWSTR lpClassName, LPCWSTR lpWindowName,
                                DWORD dwStyle, int X, int Y, int nWidth, int nHeight,
                                HWND hWndParent, HMENU hMenu, HINSTANCE hInstance, LPVOID lpParam) {
    // 强制剥离 WS_VISIBLE，追加 WS_MINIMIZE，防止首次绘制即弹窗
    dwStyle &= ~WS_VISIBLE;
    dwStyle |= WS_MINIMIZE;
    return pOriginalCreateWindowExW(dwExStyle, lpClassName, lpWindowName, dwStyle,
                                   X, Y, nWidth, nHeight, hWndParent, hMenu, hInstance, lpParam);
}

// 拦截 SetWindowPos：将窗口重定向至底层 HWND_BOTTOM
using SetWindowPos_t = BOOL(WINAPI*)(HWND, HWND, int, int, int, int, UINT);
SetWindowPos_t pOriginalSetWindowPos = nullptr;

BOOL WINAPI Hook_SetWindowPos(HWND hWnd, HWND hWndInsertAfter, int X, int Y, int cx, int cy, UINT uFlags) {
    // 阻断任何显示与置顶行为
    uFlags &= ~SWP_SHOWWINDOW;
    uFlags |= (SWP_NOACTIVATE | SWP_NOZORDER);
    // 强行插入最底层
    return pOriginalSetWindowPos(hWnd, HWND_BOTTOM, X, Y, cx, cy, uFlags);
}

// 拦截 ShowWindow：改写为静默最小化
using ShowWindow_t = BOOL(WINAPI*)(HWND, int);
ShowWindow_t pOriginalShowWindow = nullptr;

BOOL WINAPI Hook_ShowWindow(HWND hWnd, int nCmdShow) {
    if (nCmdShow == SW_SHOW || nCmdShow == SW_SHOWNORMAL || nCmdShow == SW_SHOWDEFAULT) {
        nCmdShow = SW_SHOWMINNOACTIVE; // 静默最小化且不抢焦点
    }
    return pOriginalShowWindow(hWnd, nCmdShow);
}
```

### 路径 B：Groupy 排除名单阻断外部套壳（未来优先验证路径）
既然元凶是外部多标签管理器（Groupy）的全局钩子，最自然的无感解法不是对抗 API，而是**在配置层切断 Groupy 对控制台的自动捕获**：
1. 打开 **Stardock Groupy 设置**；
2. 导航至 **Advanced** 或 **Excluded Applications**；
3. 将 `conhost.exe` 添加为全局排除对象；
4. **推演效果**：Groupy 将彻底无视 `conhost.exe` 的创建，不再生成外壳，从而使得路径 A 的 Windhawk 置底 Hook 完全透传并生效。

---

## 四、结论与回退存档（防复发原则）

### 1. 为什么本轮探索选择全部撤回？
* **未达端到端闭环**：在未实际配置并验证 Groupy 排除规则前，单独依赖 Windhawk Hook 无法完全根治 Stardock 外部置顶问题；
* **杜绝配置越界**：坚决避免私自魔改二进制（如 `aociw.exe`）或强行覆盖用户的生产配置文件，保持本地环境原生干净。

### 2. 知识库防腐与唤醒判定
* 未来若重新接手“Windows 后台黑框弹窗置顶”任务，**第一排查项必须是检查是否存在外部窗口管理工具**（Stardock Groupy、DisplayFusion、AquaSnap、PowerToys FancyZones）；
* 若存在此类工具，必须优先处理外部管理器的排除规则，严禁盲目在目标进程内部做单纯的 API Hook 徒劳对抗。
