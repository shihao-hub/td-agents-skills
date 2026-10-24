---
name: kb-win-low-integrity-gui-init-failed
description: Windows 目录带 Mandatory Label\Low Mandatory Level 沙箱标签致新建 worktree/子目录与编译二进制继承 Low 完整性级别，双击报安全警告且点击运行无反应或闪退 ERROR_DLL_INIT_FAILED (0xC0000142) 排障与 icacls /setintegritylevel Medium 抢救及构建脚本防腐 SOP。
id: "098"
domain: win
scope: fs
type: fix
slug: "父目录Low完整性继承致GUI闪退与安全警告排障"
status: verified
created: "2026-10-24"
last_verified: "2026-10-24"
compatibility:
  os: ["windows"]
invocation:
  auto_trigger: true
---

# 098-Windows父目录Low完整性继承致GUI闪退与安全警告排障指南

> **一句话**：**「父目录带 Low 完整性标签」会导致所有新建目录（如 Git Worktree）默认继承低完整性级别（Low Integrity Level）**。Windows 内核严格限制低完整性进程访问桌面交互窗口站（`WinSta0`），导致程序刚启动就在 `user32.dll` / GUI 运行时初始化阶段崩溃（`ERROR_DLL_INIT_FAILED` / `0xC0000142`），表现为**双击弹安全警告、点击运行后毫无动静瞬间闪退**。

---

## 一、现象与报错直击

### 1.1 弹窗：打开文件 - 安全警告
双击新编译的 GUI 或 CLI 二进制文件时，Windows 附件管理器（Attachment Manager）强制弹出拦截窗口：
```text
打开文件 - 安全警告
无法验证发布者。你确定要运行此软件吗？
  名称: ...\typeai\bin\typeai-gui-dev.exe
  发行商: 未知发布者
  类型: 应用程序
  [运行(R)]  [取消]
```

### 1.2 点击“运行”毫无反应（静默闪退）
点击「运行」按钮后：
- 屏幕没有任何窗口弹出；
- 没有任何错误提示对话框；
- 任务管理器中进程出现不到 100 毫秒便消失；
- 哪怕直接在终端运行，也直接返回退出码且无任何标准输出，甚至连 `main()` 函数的第一行打印都没机会执行。

### 1.3 极具迷惑性的“跨目录对照”
在排查过程中，极易误判为“代码 Bug”或“Go/Wails 运行时损坏”：
| 测试场景 | 现象 | 结论陷阱 |
|:---|:---|:---|
| 在原主仓 `go_projects\typeai\bin` 下运行同名 exe | **秒开秒启，完全正常** | 误以为是新建的 worktree 代码改坏了 |
| 把新编译出来的 exe 拷贝到 `D:\Users` 运行 | **秒开秒启，完全正常** | 误以为是路径中带横杠 `-` 或文件名太长 |
| 只要在 `D:\Users\language_projects` 下新建任何子目录 | **100% 闪退崩溃** | 真实线索：根源在目录安全描述符（ACL） |

---

## 二、底层根因剖析

### 2.1 Windows 强制完整性控制（Mandatory Integrity Control, MIC）
Windows Vista 起引入了强制完整性控制机制，进程与对象按完整性级别分层隔离：
- **Untrusted (0x0000)**：匿名访问
- **Low (0x1000)**：沙箱隔离环境（如 AppContainer、沙箱浏览器）
- **Medium (0x2000)**：标准普通用户桌面交互进程（默认）
- **High (0x3000)**：管理员权限提升进程（UAC）
- **System (0x4000)**：系统核心服务

### 2.2 目录继承属性 `(OI)(CI)` 下毒机制
通过 `icacls` 查看根目录权限时，暴露了关键元凶：
```powershell
icacls "D:\Users\language_projects"
# 输出:
# Mandatory Label\Low Mandatory Level:(OI)(CI)(NW)
```
- `(OI)`: Object Inherit（在该目录下新建的文件，自动继承此标签）
- `(CI)`: Container Inherit（在该目录下新建的文件夹，自动继承此标签）
- `(NW)`: No Write Up（禁止低权限进程向高权限对象写入）

这通常发生在配置过 AI 沙箱（如 Codex Sandbox、Docker 隔离等）的工作区根目录。

### 2.3 为什么老目录正常，新 Worktree 目录中招？
- **老目录 `go_projects`**：在根目录被附加 `Low Mandatory Level` 之前就已经建立，且安全工具未执行递归下发（`/t`），因此保留了 Windows 默认的 `Medium` 级别；
- **新 Worktree `go_projects-wt-sidebar-deai`**：执行 `git worktree add ../go_projects-wt-sidebar-deai` 时，NTFS 在父目录下创建全新文件夹，立即被刻上了继承标记：
  ```text
  Mandatory Label\Low Mandatory Level:(I)(OI)(CI)(NW)
  ```
  末尾的 **`(I)`** 即代表 **Inherited（从父级继承）**。在该目录下编译出的所有 `bin\*.exe` 全部默认带上 `Low Mandatory Level`。

### 2.4 为什么 Low 级别会导致进程死在启动前？
Windows 安全架构强制规定：**Low 完整性级别的进程，严禁连接或获取交互式桌面窗口站 `WinSta0` 与默认桌面 `Default` 的句柄，亦严禁打开剪贴板**。
当二进制运行时：
1. Windows 创建进程，赋予其 Low Token；
2. 加载静态或动态链接的系统库 `user32.dll` / `shell32.dll`；
3. `user32.dll` 在 `DllMain` 阶段尝试调用内核服务接入交互窗口站（用于后续创建窗口、响应消息循环）；
4. 内核拒绝访问，`DllMain` 返回 `FALSE`；
5. Windows 进程加载器终止进程，抛出 **`ERROR_DLL_INIT_FAILED`（0xC0000142: A dynamic link library (DLL) initialization routine failed）**；
6. 进程直接自毁，连应用程序的 `main()` 入口都未触达。

---

## 三、标准排查与抢救 SOP

### 3.1 快速排查诊断命令
在终端运行 `icacls` 检查目标 exe 或其上级目录：
```powershell
# 1. 检查目标可执行文件
icacls ".\bin\typeai-gui-dev.exe"
# 若输出中包含 "Mandatory Label\Low Mandatory Level"，即命中本故障！

# 2. 检查父目录
icacls ".."
```

### 3.2 立即抢救（提升完整性级别与解锁）
通过 Windows 原生 `icacls` 工具将目标二进制的完整性标签显式提升回 `Medium`，并使用 PowerShell 解除附件标记：
```powershell
# 提升为标准 Medium 级别（允许访问交互式窗口站）
icacls "path\to\your-gui.exe" /setintegritylevel Medium

# 移除 Zone.Identifier 流（消除“无法验证发布者”弹窗）
Unblock-File "path\to\your-gui.exe"
```
执行后再次运行，GUI 窗口即可瞬间正常弹出。

### 3.3 目录级根治（可选）
如果希望整个 worktree 目录及其后续生成的产物不再继承 Low 级别：
```powershell
# 提升整个 bin 目录及子项
icacls "path\to\worktree\bin" /setintegritylevel Medium
```

---

## 四、工程防腐：构建脚本自动化免疫

为了防止未来在任何受沙箱策略影响的机器或目录下重新编译再次踩坑，应当在构建流水线（如 Python / Shell / Makefile）中加入**产物安全后处理守卫**。

以 [`scripts/build.py`](file:///D:/Users/language_projects/go_projects-wt-sidebar-deai/typeai/scripts/build.py) 为例，在生成 exe 之后追加：

```python
# scripts/build.py (构建完成后)
if sys.platform == "win32":
    # 保证产物具备标准 Medium 完整性级别（防止继承外部沙箱/容器目录的 Low 标签导致 DLL 初始化崩溃）
    subprocess.run(["icacls", str(out_exe), "/setintegritylevel", "Medium"], capture_output=True)
    # 解除 Windows 附件管理器 Zone.Identifier 锁定（防止未知发布者警告弹窗）
    try:
        Path(f"{out_exe}:Zone.Identifier").unlink(missing_ok=True)
    except OSError:
        pass
```

### 验证方法
构建完成后，在终端运行：
```powershell
icacls ".\bin\typeai-gui-dev.exe"
```
确认输出为：
```text
Mandatory Label\Medium Mandatory Level:(NW)
```
并且双击可直接秒开桌面 GUI 窗口，零弹窗、零闪退。
