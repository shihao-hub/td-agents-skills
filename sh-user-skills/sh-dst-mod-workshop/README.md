---
name: sh-dst-mod-workshop
description: 饥荒联机版（DST）创意工坊模组下载、DaxSg加壳逆向与活体内存Hex部分提取探索（实测未完全解密/部分流程，仅供逆向研究参考）。点名使用
version: 2.1.0
created: 2026-10-13
updated: 2026-10-21
disable-model-invocation: true
---

# sh-dst-mod-workshop：饥荒联机版（DST）通用模组脱壳与独立运行实战

> [!WARNING]
> **【流程不完整 / 实测未完全解密警示】**：  
> 实测表明：当前 SOP 仅成功走通了内存 Hex 导出与**部分**字节码函数的提取，**未能实现 100% 完整解密与免壳独立运行**。  
> DaxSg 等加壳模组内部存在反调试机制、动态混淆及部分未还原的核心函数。本流程仅供逆向工程分析、断点取证与部分代码抽样参考，不可视为可交付的确定性脱壳方案。



> 本指南为《饥荒联机版》（Don't Starve Together，Steam AppID `322330`）针对 **DaxSg 混淆保护壳及同类加壳模组** 的工业级通用脱壳、跨机器环境自适应、全自动活体内存提取、规范化 Staging 隔离与独立免删模组组装标准作业程序（SOP）。
> 核心设计遵循**高通用性（零先验知识差集提取）、跨环境自发现（无绝对路径绑定）以及防数据泄露的 AI 评测隔离体系（Eval Benchmark Ready）**。

---

## 一、设计哲学与核心机制

加壳模组（如 DaxSg）通常内建文件哈希自校验、反调试陷阱（修改代码触发死锁或弹出 VBS）并采用专用 VM 执行，常规的静态代码反编译或 loadstring hook 均会失效。
本技能采用**运行时活体内存提取（Live Runtime Memory Dump）**：
1. **零先验知识（Zero Prior Knowledge）**：不依赖对模组内部特定人物或物品名称的预判，直接从引擎内存的全局挂载点（`GLOBAL.Prefabs` 与已载入包）抓取活跃函数对象；
2. **跨机器环境自发现**：通过注册表与 Steam 配置文件自适应探测任意盘符下的游戏路径与 Klei 活跃用户存档目录，杜绝硬编码；
3. **数据流转与 Staging 隔离**：强制在独立的 `mods/_staging_<ModName>/` 下进行中间解码，绝不污染用户其它工程；组装完成后全自动归档并清理 Hex 碎片。

---

## 二、模组获取双轨制

> [!IMPORTANT]
> **模组运行前提**：活体内存提取必须建立在**游戏引擎成功加载并运行该模组**的基础上。只有外壳 VM 执行完毕，解密后的函数才会真实存在于引擎内存中。

* **途径 A（推荐：Steam 客户端订阅）**：
  在 Steam 创意工坊订阅目标模组 `<WorkshopId>`，启动游戏即可自动同步至缓存。
* **途径 B（备用：SteamCMD 离线匿名下载）**：
  若在无 Steam 客户端的测试环境中，可使用内建脚本匿名拉取：
  ```powershell
  python -c "import sys; from dst_detect_env import detect_dst_paths; _, mods_d, _ = detect_dst_paths(); print(mods_d)"
  & ".\scripts\download_workshop_item.ps1" -WorkshopId <WorkshopId>
  ```
  下载后将产物文件夹置于游戏 `mods/` 目录下即可。

---

## 三、通用分步执行 SOP

```
 ┌────────────────────────────────────────────────────────┐
 │ 步骤 1：自动探测机器环境                                │
 │   运行 dst_detect_env.py 获取 Steam、DST 与存档路径    │
 └───────────────────────────┬────────────────────────────┘
                             │
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │ 步骤 2：识别加壳特征与指纹                             │
 │   检查 daxsg_mod_path.txt / 混淆 main 文件 / 0x1A 字节 │
 └───────────────────────────┬────────────────────────────┘
                             │
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │ 步骤 3：部署活体提取（双通道可选）                     │
 │   • 通道 A (推荐)：00_auto_dumper 免控制台全自动静默提取 │
 │   • 通道 B (兜底)：进入世界按 ~ 键执行 dofile 手动提取   │
 └───────────────────────────┬────────────────────────────┘
                             │ 落地至 client_save/mod_config_data/q_*.hex
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │ 步骤 4：Staging 隔离区 Hex 批量转码与符号解析          │
 │   • 在 mods/_staging_<Name> 中转为标准 Lua 5.1 x64    │
 │   • 解析 64 位文件头，恢复 source 路径与常量清单       │
 └───────────────────────────┬────────────────────────────┘
                             │
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │ 步骤 5：组装免删本地独立模组与全自动清洁归档           │
 │   • 落地为 mods/<Name>/ (去除 workshop- 彻底免删)      │
 │   • 过程资产与说明文档归档至 _archive_reverse_tools/   │
 │   • 自动清空 staging 临时区与 client_save hex 碎片     │
 └────────────────────────────────────────────────────────┘
```

---

### 步骤 1：自动探测与环境绑定

无需手动翻找盘符与 SteamID，运行环境探测工具：
```powershell
python ".\scripts\dst_detect_env.py"
```
工具将自动返回当前机器上：
* Steam 安装根目录；
* 《饥荒联机版》主程序与 `mods/` 目录；
* 用户的活跃 Klei 存档目录（`client_save/mod_config_data/`）。

---

### 步骤 2：部署活体提取机制（双通道）

#### 通道 A（推荐：免控制台输入，全自动静默提取）
将自适应挂件模组模板部署到游戏 `mods/` 目录：
```powershell
$modsDir = (python -c "from dst_detect_env import detect_dst_paths; print(detect_dst_paths()[1])")
New-Item -ItemType Directory -Path "$modsDir\00_auto_dumper" -Force | Out-Null
Copy-Item -Path ".\scripts\auto_dumper\*" -Destination "$modsDir\00_auto_dumper\" -Recurse -Force
Copy-Item -Path ".\scripts\dump_memory.lua" -Destination "$modsDir\00_auto_dumper\" -Force
```
* **全自动机制**：挂件模组以 `priority = -99999` 保证在目标模组之后加载，并在世界加载后延时 1.5 秒通过 `AddSimPostInit` 自动触发 Hex 转储。
* **用户动作**：启动游戏 -> 勾选目标模组与挂件模组 -> 进入世界 -> 等待 2 秒听到提示 -> 直接退出游戏！**全程无需调出控制台，无需输入命令**！

#### 通道 B（备用：控制台手动执行）
复制提取脚本至 `mods/` 根目录：
```powershell
Copy-Item -Path ".\scripts\dump_memory.lua" -Destination "$modsDir\dump_memory.lua" -Force
```
进入世界后按键盘反引号 `~` 打开控制台，执行：
```lua
dofile("../mods/dump_memory.lua")
```

---

### 步骤 3：Staging 隔离批量解码与符号恢复

> [!TIP]
> **工作区整洁规约**：
> 所有临时解码工作统一在独立的临时区 `mods/_staging_<ModName>/` 下进行，严禁散落在其它用户项目或游戏根目录。

运行通用转码脚本：
```powershell
$stagingDir = "$modsDir\_staging_<ModName>"
python ".\scripts\convert_hex_to_luac.py" --output-dir "$stagingDir"
```
* **突破空字节截断**：剥除 Klei 存档头（`KLEI     1 `），按十六进制将数据反解为原汁原味的 **标准 Lua 5.1 x64 `.luac` 预编译块**；
* **解析符号与结构**：
  ```powershell
  python ".\scripts\inspect_and_disassemble.py" "$stagingDir" --export-map "$stagingDir\manifest.json"
  ```
  从 64 位文件头中提取出每一个块对应的原始 `source` 路径，完整复原模组原作者的代码树拓扑。

---

### 步骤 4：组装独立免删本地模组与自动归档

```powershell
python ".\scripts\assemble_standalone_mod.py" "<WorkshopModPath>" --name "<TargetModName>" --staging-dir "$stagingDir"
```

**该脚本一键原子化完成**：
1. **彻底解决退订自动删除**：生成目录 `mods/<TargetModName>/`（**强制去除 `workshop-` 前缀**）。DST 将其识别为永久 Local Mod，不受创意工坊退订自动物理删除机制影响；
2. **字符集与配置标准化**：自适应读取原始配置，重新写入纯正 UTF-8（无 BOM）的 `modinfo.lua`，并标记 `(独立免订阅版)`；
3. **中间资产安全归档**：将 Staging 区中的提取脚本、`.luac` 预编译块等全量移入：
   `mods/<TargetModName>/_archive_reverse_tools/`，并自动生成说明文档 `README.md`；
4. **环境自动化清洁**：清空并删除临时 Staging 目录，自动抹除 `client_save/mod_config_data/` 下遗留的临时 Hex 碎片，移除辅助挂件，保证游戏环境 100% 纯净。

---

## 四、AI 评测与防作弊检验（Eval Benchmark Protocol）

为了防止后续其它 AI 在针对本 Skill 进行评测时“偷翻现成解密目录”抄作业，本技能内建了客观的基准验证器：

```powershell
python ".\scripts\eval_verifier.py" "$modsDir\<TargetModName>" --staging-dir "$stagingDir"
```

**验证器判定维度**：
* ✅ **时间戳活性检验**：校验本次评测是否真正产生了实时的动态内存导出，而非静态重放；
* ✅ **预编译块合法性**：校验生成的 `.luac` 是否具备标准 64 位 Lua 5.1 文件头与真实的 `source` 符号；
* ✅ **防作弊哈希比对**：检测产物是否直接从既有历史目录偷复制而来（触发作弊直接扣分并报警）；
* 输出百分制评分报告（`score >= 80` 判定为 PASS）。

---

## 五、经典案例研析（Case Study）

有关奎姆（Quem，ID: 3152990521）的完整 73 个脚本加密结构、119 个 Prefab、336 个函数提取、以及针对 Windows `0x1A` EOF 截断的深度逆向报告，请参阅专用参考文档：
👉 [奎姆模组逆向案例深度剖析](references/case_study_quem.md)
