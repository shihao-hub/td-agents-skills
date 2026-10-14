---
name: sh-dst-mod-workshop
description: 饥荒联机版（DST）创意工坊模组下载、DaxSg加壳逆向、全自动/控制台活体内存Hex提取、x64字节码还原、工作区规范与免删独立模组组装归档实战SOP。点名使用
version: 1.2.0
created: 2026-10-13
updated: 2026-10-14
---

# sh-dst-mod-workshop：饥荒联机版（DST）模组脱壳与独立运行实战

> 本指南为《饥荒联机版》（Don't Starve Together，Steam AppID `322330`）针对 **DaxSg 混淆保护壳**的逆向工程、全自动活体内存提取、规范化生命周期管理与独立免订阅模组组装的工业级 SOP。
> 经历了大量真实环境踩坑验证，彻底攻克“改代码触发反调试死锁”、“0x1A 文本截断”、“常规 loadstring hook 无效”、“SavePersistentString 空字节截断”、“中间文件散落污染”以及“Steam 创意工坊启动静默删除”等全链路痛点。

---

## 一、版本与来源对照

* **目标游戏**：Don't Starve Together（饥荒联机版，Steam AppID `322330`）。
* **执行环境**：
  * **Lua 5.1 x64**：Klei 官方专用 64 位 Lua 运行环境（`sizeof(size_t) = 8`）。
  * **Python 3.8+**：Hex 批量转码、字节码反混淆、符号提取与自动归档。
  * **SteamCMD**：免客户端离线拉取创意工坊原版文件（工具链已内建）。
* **实战验证样本**：创意工坊 ID `3152990521`（知名大型模组“奎姆 Quem”，作者小版本 7.8）。

---

## 二、架构总览与全生命周期工作流

针对 DaxSg 等拥有自校验和专有 VM 的加壳模组，**静态修改与单纯反编译均会触发反调试**。最科学的方案是：**让宿主正常加载，在运行时从内存中提取解密后的函数对象，并在规范化的独立工作区中完成解码与归档**。

```
 ┌────────────────────────────────────────────────────────┐
 │ 1. 模组获取双轨制                                       │
 │    • 途径 A (推荐)：Steam 客户端正常订阅模组             │
 │    • 途径 B (备用)：SteamCMD 匿名下载，放置于 mods/      │
 └───────────────────────────┬────────────────────────────┘
                             │
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │ 2. 识别 DaxSg 壳指纹与加密列表 (daxsg_mod_path.txt 等) │
 └───────────────────────────┬────────────────────────────┘
                             │
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │ 3. 活体内存提取双通道                                   │
 │    • 通道 A (推荐)：00_auto_dumper 免控制台全自动静默提取 │
 │    • 通道 B (兜底)：进入世界按 ~ 键执行 dofile 手动提取   │
 └───────────────────────────┬────────────────────────────┘
                             │ 落地至 client_save/mod_config_data/q_*.hex
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │ 4. 规范化 Staging 隔离转码                             │
 │    • 工作区锁定于 mods/_staging_<ModName>/             │
 │    • Python 批量还原 336 个标准 Lua 5.1 x64 .luac      │
 │    • 解析 64 位符号头，恢复原始源码拓扑与常量表         │
 └───────────────────────────┬────────────────────────────┘
                             │
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │ 5. 独立本地模组组装与全自动归档                         │
 │    • 终态落位：mods/<ModName>/ (去除 workshop- 彻底免删)│
 │    • 过程资产归档：mods/<ModName>/_archive_reverse_tools/ │
 │    • 自动生成说明文档与原理解析 README.md               │
 │    • 自动清空 staging 与 client_save 中的 hex 临时碎片 │
 └────────────────────────────────────────────────────────┘
```

---

## 三、模组获取双轨制与前置准备

> [!IMPORTANT]
> **关于模组加载的核心前提**：
> 活体内存提取技术必须依赖**饥荒游戏引擎成功加载并运行该模组**，此时外壳 VM 才会把所有解密函数挂载到内存中。因此，模组必须处于游戏可加载的状态。

### 途径 A（推荐）：Steam 客户端直接订阅
* 在 Steam 创意工坊点击“订阅”该模组；
* 打开游戏客户端，模组将自动下载到 Steam 创意工坊缓存目录（`steamapps/workshop/content/322330/<ID>`），并在游戏的“模组列表”中可见。

### 途径 B（备用）：SteamCMD 离线匿名下载
若不需要在个人 Steam 账号中订阅，可直接使用本技能自带的脚本静默下载：
```powershell
$skillRoot = "D:\Users\language_projects\.agents\skills\sh-user-skills\sh-dst-mod-workshop"
& "$skillRoot\scripts\download_workshop_item.ps1" -WorkshopId 3152990521
```
* 下载完成后，将产物目录复制到游戏的本地模组文件夹下：
  ```powershell
  $dstMods = "D:\Program Files (x86)\Steam\steamapps\common\Don't Starve Together\mods"
  Copy-Item -Path "$env:TEMP\steamcmd\steamapps\workshop\content\322330\3152990521" -Destination "$dstMods\workshop-3152990521" -Recurse -Force
  ```

---

## 四、分步执行 SOP

### 步骤 1：识别加壳指纹与加密列表

进入模组目录，核验 DaxSg 指纹：
* 根目录存在 `daxsg_mod_path.txt`（记录所有被加壳加密的 73 个脚本清单）；
* 存在约 40KB 的 `modmain.lua`、约 100KB 的 `modmain0.lua` 与约 140KB 的 `modmain1.lua`；
* `modmain0.lua` 偏移 165 字节处含有 `0x1A` 陷阱字节（触发 CRT EOF 截断）；
* **红线警示**：**绝对不要直接修改 `modmain.lua`**！其内部有自校验代码（偏移 29203 处的 `daxsg_mistake`），任何修改都会导致释放 `.vbs` 警告弹窗并陷入 100% CPU 死循环。

---

### 步骤 2：部署活体提取脚本（双通道可选）

#### 通道 A（推荐：免手动控制台输入，全自动静默提取）
将技能库中的 `auto_dumper` 辅助模组一键部署到游戏模组目录：
```powershell
$dstMods = "D:\Program Files (x86)\Steam\steamapps\common\Don't Starve Together\mods"
$skillScripts = "D:\Users\language_projects\.agents\skills\sh-user-skills\sh-dst-mod-workshop\scripts"

# 1. 创建 00_auto_dumper 模组
New-Item -ItemType Directory -Path "$dstMods\00_auto_dumper" -Force | Out-Null
Copy-Item -Path "$skillScripts\auto_dumper\*" -Destination "$dstMods\00_auto_dumper\" -Recurse -Force

# 2. 将 dump_memory.lua 放入该模组中供其内部调度
Copy-Item -Path "$skillScripts\dump_memory.lua" -Destination "$dstMods\00_auto_dumper\" -Force
```
* **工作原理**：`00_auto_dumper` 设置了最低优先级 `priority = -99999`，确保其在所有目标模组完全初始化后才加载。它通过 `AddSimPostInit` 挂载定时器，在进入世界 1.5 秒后**全自动静默执行 Hex 导出写盘**，屏幕输出完成日志，玩家**全程无需打开控制台，无需敲代码**！

#### 通道 B（备用：控制台手动 dofile 提取）
不想安装辅助模组时，可直接复制提取脚本并由控制台调用：
```powershell
Copy-Item -Path "$skillScripts\dump_memory.lua" -Destination "$dstMods\dump_memory.lua" -Force
```

---

### 步骤 3：启动游戏触发内存转储

1. 启动《饥荒联机版》客户端；
2. 在模组列表中，勾选启用待脱壳模组（如使用通道 A，同时勾选 `00_脱壳抓取器 (Auto Dumper)`）；
3. 点击“创建世界”或直接进入任意房间；
4. **触发导出**：
   * **若使用通道 A**：进入世界 2 秒后，自动完成导出，可直接按 ESC 退出游戏！
   * **若使用通道 B**：按键盘反引号 `~` 打开游戏控制台，输入并回车：
     ```lua
     dofile("../mods/dump_memory.lua")
     ```
5. 核心数据已落地至用户的持久化存档目录：
   `Documents\Klei\DoNotStarveTogether\<SteamID>\client_save\mod_config_data\q_*.hex`。

---

### 步骤 4：规范化工作区（Staging）转码与符号还原

> [!TIP]
> **工作区整洁准则**：
> 严禁将临时解码产物随地丢在用户的个人项目（如 `MoreItems`）或 `mods/` 根目录。统一在目标模组专属的 Staging 临时隔离区进行处理。

创建隔离工作区并运行 Python 批量转码：
```powershell
$stagingDir = "$dstMods\_staging_quem"
python "$skillScripts\convert_hex_to_luac.py"
# 产物自动归拢在 $stagingDir
```
* **解决 NUL 截断**：剥除 Klei 存档头（`KLEI     1 `），通过 `bytes.fromhex` 还原出真实的 **336 个标准 Lua 5.1 x64 `.luac` 预编译块**。
* **解析 64 位文件头**：
  ```powershell
  python "$skillScripts\inspect_and_disassemble.py" "$stagingDir"
  ```
  提取出预编译块中的 `source` 原始源码路径（如 `../mods/workshop-3152990521/scripts/prefabs/kuimu_staff.lua`），锁定全部 119 个 Prefab、Boss 机制与角色专属脑。

---

### 步骤 5：组装免删本地独立模组与全自动归档

运行全自动组装与归档脚本：
```powershell
python "$skillScripts\assemble_standalone_mod.py" `
    "D:\Program Files (x86)\Steam\steamapps\workshop\content\322330\3152990521" `
    "$dstMods" `
    "quem" `
    "$stagingDir"
```

该脚本将**一键原子化完成全套标准化交付**：
1. **生成纯本地独立模组**：落位到 `mods/quem`，**强制去除 `workshop-` 前缀**。DST 将其识别为不受创意工坊管辖的 Local Mod，彻底摆脱“退订被 Steam 强制删除”的致命缺陷；
2. **修正 `modinfo.lua`**：写入纯正 UTF-8（无 BOM），更名为 `奎姆 (独立免订阅版)`，版本号标记为 `7.8.0_Standalone`；
3. **全量过程资产归档**：将 `_staging_quem` 中的 336 个 `.luac`、提取脚本等全部移入：
   `mods/quem/_archive_reverse_tools/`；
4. **生成内嵌白皮书**：在归档目录下自动生成 `README.md`，记录各文件用途、中间环节流转与逆向原理解析；
5. **自动化清洁环境**：
   * 自动删除 `_staging_quem` 临时工作区；
   * 自动清空 `client_save/mod_config_data/` 下遗留的几百个临时 `q_*.hex` 碎片；
   * 自动移除 `00_auto_dumper` 挂件模组；
   * 确保游戏目录除了干净的 `mods/quem` 之外，**零残留、零污染**！

---

## 五、常见踩坑与实战避坑手册

| 踩坑现象 | 根本原因 | 实战正确应对 |
|---|---|---|
| **Python 打开文件大小只有 165 字节** | Windows CRT 在文本模式下遇到 `0x1A` 触发 EOF 截断 | 所有 IO 打开必须使用二进制模式（`'rb'`） |
| **修改 modmain.lua 游戏卡死/弹出 VBS** | DaxSg 内部对自身代码和调用栈做了哈希校验（陷阱点 `daxsg_mistake`） | 绝不要修改原模组的加壳主文件，改走外部内存注入 |
| **常规 hook loadstring 捕获不到代码** | DaxSg 自写字节码解释器，直接操作虚拟机内存，不走 loadstring 语法解析 | 放弃 loadstring hook，转为提取 `GLOBAL.Prefabs` 与已载入 package 内存闭包 |
| **导出的字节码文件严重残缺（只有几十字节）** | 二进制中含有 `\0`，Klei 的 `SavePersistentString` 底层将其截断 | 在 Lua 端用 `to_hex` 编码为十六进制文本，落地后再用 Python 还原为二进制 |
| **解开的模组重启游戏后被离奇删除** | 模组文件夹以 `workshop-*` 命名，被 Steam 同步器判定为未订阅文件直接抹除 | 模组文件夹改用纯英文字符（如 `quem`），使游戏将其识别为不受管辖的 Local Mod |
| **逆向中间文件到处散落、工程混乱** | 临时提取脚本与 hex/luac 没有统一工作区管理 | 严格执行 Staging 隔离规范，最终自动归档入 `mods/<name>/_archive_reverse_tools/` |
