---
name: sh-sublime-menu
description: 装机：Sublime 右键菜单添加/删除/检查，Win11 菜单样式切换。点名使用
---

# sh-sublime-menu — Sublime Text 右键菜单管理

一次执行完成"用 Sublime Text 打开"右键项的增删查，外加 Win11 菜单样式切换。全部只写 HKCU 注册表，**不需要管理员权限**，Win10/Win11 通用。

## 铁律

1. **默认绝不改 Win11 右键菜单样式**。`add`/`remove`/`status` 不碰任何 CLSID 键，Win11 新版菜单原样保留。只有用户明确要求"恢复经典菜单/右键直接显示/不要显示更多选项"时才执行 `classic-on`，用户反悔或要求还原时用 `classic-off` 撤回——两个动作必须成对可用。
2. **只写 `HKCU\Software\Classes`**，不写 HKLM——无需管理员、只影响当前用户，也不与系统级策略打架。
3. 菜单项增删**即时生效**，无需重启资源管理器；只有 `classic-on`/`classic-off` 需要重启（任务栏闪一下、已打开的文件资源管理器窗口会关闭，执行前提醒用户一句）。
4. **每次执行完必须跑 `status` 验证**，把最终状态汇报给用户，不要只报"操作成功"。

## 用法

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "<skill目录>/scripts/sublime-menu.ps1" <Action> [-ExePath <sublime_text.exe完整路径>] [-Label <显示文案>]
```

| Action | 作用 | 备注 |
|---|---|---|
| `status` | exe 探测结果、四类菜单项有无、当前菜单样式 | 默认 action，只读，先跑它再做别的 |
| `add` | 添加四类右键项（带图标、置顶） | 自动探测 exe；非标准安装用 `-ExePath`，自定义文案用 `-Label` |
| `remove` | 删除全部四类右键项 | 不存在时静默通过，可重复执行 |
| `classic-on` | Win11 右键切换为经典完整菜单（免"显示更多选项"） | 仅用户明确要求时执行；重启资源管理器 |
| `classic-off` | 恢复 Win11 新版菜单 | 撤回 `classic-on`；重启资源管理器 |

典型组合：只加右键 = `add`；用户要彻底还原 = `remove`（若曾执行过 `classic-on` 再补 `classic-off`）。

## 注册表细节（理解后再改）

- 四类目标，均在 `HKCU\Software\Classes\` 下，verb 名固定 `SublimeText`：
  - `*\shell\SublimeText` — 任意类型文件（不限扩展名）
  - `Directory\shell\SublimeText` — 文件夹本身
  - `Directory\Background\shell\SublimeText` — 文件夹空白处/桌面
  - `Drive\shell\SublimeText` — 磁盘分区
- 命令行参数：空白处用 `%V`（当前目录），其余用 `%1`——`%1` 在库、zip 内部等特殊位置的空白处取不到值。
- `Icon` = `<exe路径>,0`（取 exe 内嵌图标）；`Position` = `Top`（菜单置顶）。
- 经典菜单切换 = `HKCU\Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\InprocServer32` 默认值设为空串；删掉整个 CLSID 键即恢复新版菜单。这就是全部开关，没有其他副作用。
- Win11 下静态 verb 菜单项只能出现在"显示更多选项"里（新版菜单只接受打包 COM 组件，纯注册表进不去）；**Shift+右键**可直接弹经典菜单跳过这一步，主动告诉用户。

## 提醒用户的点

- 添加后：文件在已有 Sublime 窗口开为新标签页；文件夹/磁盘会作为项目开新窗口（Sublime 自身行为，不是菜单项的问题）。
- 换电脑/重装 Sublime 后重跑 `add` 即可；exe 挪了位置用 `-ExePath` 或先 `remove` 再 `add`。
