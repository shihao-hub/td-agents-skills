---
name: sh-dst-mod-workshop
description: 饥荒联机版（DST）创意工坊模组下载、DaxSg/混淆壳解密与逆向实战SOP。点名使用
version: 1.0.0
created: 2026-10-13
updated: 2026-10-13
---

# sh-dst-mod-workshop：饥荒联机版（DST）创意工坊模组下载与 DaxSg 壳解密实战

> 本技能为《饥荒联机版》（Don't Starve Together, AppID: 322330）创意工坊模组全流程管理与逆向工程标准作业手册（SOP）。
> 覆盖：SteamCMD 官方工具链匿名下载工坊物品、模组加密指纹识别（DaxSg 壳）、无侵入式动态 Hook 脱壳、自校验与反调试陷阱绕过、以及解密产物完整性校验。

---

## 一、版本与来源对照

* **目标游戏**：Don't Starve Together（饥荒联机版，Steam AppID `322330`）
* **依赖工具**：
  * **Valve 官方 SteamCMD**（绿色控制台工具，支持匿名下载创意工坊公共物品）
  * **Lua 5.1 / DST 原生运行时**（Klei 游戏内置 Lua 引擎）
  * **Python 3.8+**（分析指纹与批量文件校验）
* **实战案例**：创意工坊 ID `3152990521`（开源模组《奎姆 Quem》，作者“残”，版本 7.8）

---

## 二、前置检查与环境准备

### 1. 检查或安装 SteamCMD

若系统未预装 SteamCMD，通过 PowerShell 一键拉取官方免安装绿色包：

```powershell
$steamcmdDir = "$env:TEMP\steamcmd"
if (-not (Test-Path "$steamcmdDir\steamcmd.exe")) {
    New-Item -ItemType Directory -Path $steamcmdDir -Force | Out-Null
    $zip = "$steamcmdDir\steamcmd.zip"
    Invoke-WebRequest -Uri "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip" -OutFile $zip
    Expand-Archive -Path $zip -DestinationPath $steamcmdDir -Force
    Remove-Item $zip -Force
}
& "$steamcmdDir\steamcmd.exe" +quit
```

### 2. 检查游戏本地模组环境

检查 Steam 游戏安装目录与模组目录：
```powershell
$dstMods = "D:\Program Files (x86)\Steam\steamapps\common\Don't Starve Together\mods"
Test-Path $dstMods
```

---

## 三、分步执行 SOP

### 步骤 1：下载创意工坊模组

调用配套脚本执行匿名拉取（以 Mod ID `3152990521` 为例）：

```powershell
$skillRoot = "D:\Users\language_projects\.agents\skills\sh-user-skills\sh-dst-mod-workshop"
& "$skillRoot\scripts\download_workshop_item.ps1" -WorkshopId "3152990521"
```

* **落位校验**：
  检查输出目录是否存在完整文件结构：
  ```powershell
  Get-ChildItem "$env:TEMP\steamcmd\steamapps\workshop\content\322330\3152990521" | Select-Object Name, Length
  ```

---

### 步骤 2：加密特征指纹识别

运行结构分析脚本检测加密类型：

```powershell
python "$skillRoot\scripts\verify_daxsg_structure.py" "$env:TEMP\steamcmd\steamapps\workshop\content\322330\3152990521"
```

* **特征匹配判定**：
  * 若包含 `daxsg_mod_path.txt` + `modmain0.lua` + 包含单行 VM 的 `modmain.lua`，即判定为 **DaxSg 混淆壳**。
  * `daxsg_mod_path.txt` 记录了所有待解密载荷的相对路径列表。

---

### 步骤 3：无侵入式 Hook 动态脱壳（绕过自校验）

> ⚠️ **核心原则**：绝对不要修改 `modmain.lua` 源码！DaxSg 壳会在入口处调用 `io.open` 读取自身并比对 Hash/长度，一旦篡改即触发反调试分支（生成 `\sblg..vbs` / 报 `Do not debug this file!` 崩溃）。

#### 实施步骤：
1. **复制模组至游戏本地 mods 目录**：
   ```powershell
   $dstModTarget = "D:\Program Files (x86)\Steam\steamapps\common\Don't Starve Together\mods\workshop-3152990521"
   Copy-Item -Path "$env:TEMP\steamcmd\steamapps\workshop\content\322330\3152990521" -Destination $dstModTarget -Recurse -Force
   ```

2. **在 `modsettings.lua` 中部署非侵入 Hook**：
   在 `Don't Starve Together/mods/modsettings.lua` 底部追加脱壳代码与强制加载指令：
   ```lua
   -- === DST Mod Decryptor Hook ===
   local DUMP_DIR = "D:/dst_mod_dump/"
   pcall(function() os.execute('mkdir "' .. DUMP_DIR:gsub("/", "\\") .. '" 2>nul') end)

   local orig_loadstring = _G.loadstring or loadstring
   local function hooked_loadstring(str, name)
       local safe = tostring(name or "chunk"):gsub("[^%w_%-%.]", "_")
       if str and #str > 0 then
           local f = io.open(DUMP_DIR .. safe .. ".lua", "wb")
           if f then f:write(str); f:close() end
       end
       return orig_loadstring(str, name)
   end
   _G.loadstring = hooked_loadstring
   if GLOBAL then GLOBAL.loadstring = hooked_loadstring end

   -- 强制激活该模组触发解密链
   ForceEnableMod("workshop-3152990521")
   ```

3. **启动游戏触发脱壳**：
   启动游戏进入主菜单（主菜单初始化时即会加载模组并完成所有解密调用）。
   完成后在 `D:\dst_mod_dump\` 中即可获取全部解密后的明文 `.lua` 源码！

---

### 步骤 4：解密源码校验与还原

对比 `daxsg_mod_path.txt` 中的文件清单，校验 dump 出的文件完整性：

```powershell
$targetList = Get-Content "$dstModTarget\daxsg_mod_path.txt"
$dumpFiles = Get-ChildItem "D:\dst_mod_dump" -Filter "*.lua"
Write-Host "期望解密清单数: $($targetList.Count)，实际 Dump 产物数: $($dumpFiles.Count)"
```

---

## 四、常见踩坑与回滚指示

1. **踩坑：触发 `Do not debug this file!` 或 `\sblg..vbs` 报错**：
   * **原因**：在脱机 Lua 环境运行，或直接编辑了 `modmain.lua` 触发了完整性哈希自校验。
   * **规避**：还原 `modmain.lua` 保持原始 Hash，改在 `modsettings.lua` 处全局 Hook。
2. **踩坑：PowerShell 中写出的 Lua 文件报 `unexpected symbol near '\239'`**：
   * **原因**：PowerShell 的 `Set-Content -Encoding UTF8` 默认携带 UTF-8 BOM 头，Lua 5.1 解析器无法识别。
   * **规避**：使用 Python 脚本或 `[System.IO.File]::WriteAllText($path, $text, [System.Text.UTF8Encoding]::new($false))` 强制写入无 BOM 文本。
3. **脱壳完成回滚指示**：
   脱壳完成后，将 `mods/modsettings.lua` 中追加的 Hook 代码和 `ForceEnableMod` 移除，避免影响正常游戏。
