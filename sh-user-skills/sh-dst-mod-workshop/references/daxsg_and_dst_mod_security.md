# DaxSg 壳机制逆向与饥荒引擎安全攻防实战

本文档作为 `sh-dst-mod-workshop` 技能的核心技术底座，深度复盘在《饥荒联机版》（Don't Starve Together，以下简称 DST）中针对 **DaxSg 混淆保护壳** 进行脱壳、内存提取与免删独立模组组装的全套实战经验。

---

## 一、DaxSg 壳体系架构剖析

以 Steam 创意工坊模组 `Quem 奎姆`（Workshop ID: `3152990521`）为样本，DaxSg 保护壳展现了以下经典拓扑与防御特征：

```
workshop-3152990521/
├── anim/                   (原始明文动画资源，未加密)
├── bigportraits/           (原始明文立绘，未加密)
├── images/                 (原始明文贴图，未加密)
├── modinfo.lua             (明文配置参数，未加密)
├── daxsg_mod_path.txt      (列出所有受 DaxSg 托管的脚本相对路径)
├── mod.manifest            (资源清单)
├── modmain.lua             (DaxSg 引导加载器：~40KB 混淆代码)
├── modmain0.lua            (DaxSg 核心解密机与文件自校验块：~100KB)
├── modmain1.lua            (DaxSg 预混淆中间数据与字节流：~140KB)
└── scripts/
    ├── speech_*.lua        (部分明文语音)
    ├── kuimu_foods.lua     (部分明文逻辑)
    └── prefabs/            (全部经过 DaxSg 二进制混淆/置换)
```

### 1. 引导流程与加壳执行链
1. 游戏引擎执行 `modmain.lua`；
2. `modmain.lua` 内部构建了一套基于寄存器的私有轻量级 VM；
3. 读取同目录下的 `modmain0.lua` 与 `modmain1.lua`，并执行**严格的文件大小与哈希自校验**；
4. 自定义加载器接管 `io.open` 或私有解码函数，逐一加载 `daxsg_mod_path.txt` 中指定的 73 个加密脚本；
5. 在内存中将解密后的实体与逻辑挂载到 `GLOBAL.Prefabs`、`package.loaded` 与 Mod 沙盒环境中。

---

## 二、三大经典踩坑与反调试陷阱（实战复盘）

在实战攻防中，盲目采用常规逆向思路会遭遇多处“致命陷阱”：

### 陷阱 1：Windows 平台文本模式 `0x1A`（EOF/SUB）截断导致自校验失败
* **现象**：通过 Python 或 C 读取 `modmain0.lua`，经常得到只有 165 字节的数据，而磁盘实际大小为 100,724 字节。
* **根因**：在 Windows 平台下，ASCII `0x1A`（`Ctrl+Z` / `SUB`）被操作系统 C 运行时（CRT）视为文件结束符（EOF）。若以文本模式（`"r"`）打开，读取流遇到第 165 字节的 `0x1A` 就会立即终止。
* **防御后果**：DaxSg 故意在文件前段埋入 `0x1A` 字节。当逆向脚本或外部工具在文本模式下处理该文件时，读取出的大小（165）与 DaxSg 硬编码期望的大小（100724）不符，校验报错并触发反调试逻辑。
* **解决对策**：在所有文件 IO 操作中必须强制采用二进制模式（Python 使用 `open(..., 'rb')`，Lua 使用 `io.open(..., "rb")`）。

### 陷阱 2：改动 `modmain.lua` 触发反调试逻辑炸弹与 VBS 弹窗
* **现象**：尝试在 `modmain.lua` 头部或尾部添加调试打印或 hook 语句，游戏立即死锁（100% CPU 卡死）或弹出 `Do not debug this file!` 弹窗后直接崩溃闪退。
* **根因**：DaxSg 内部对自身的指令字节码、行号、以及调用栈深度进行了探测（在 `modmain.lua` 偏移约 29203 字节处设有 `daxsg_mistake` 陷阱）。检测到代码被修改或单步跟踪后，会调用系统命令生成隐藏的 `.vbs` 脚本弹出警告并陷入死循环。
* **核心教训**：**绝不要直接静态修改原版 `modmain.lua` 或壳的核心数据文件**。

### 陷阱 3：试图用 `hook_loadstring` 脱壳完全失效
* **现象**：在 `modsettings.lua` 中将 `GLOBAL.loadstring` 劫持并记录参数，启动游戏后捕获到的全是空或者无关的系统代码。
* **根因**：DaxSg 并不使用 Lua 运行时的 `loadstring(source_str)` 来加载解密出的脚本！它的私有 VM 直接在内存中解析其专有的字节码结构并构造闭包，根本不走官方的语法分析器。

---

## 三、终极破解之道：运行时内存“摘果实”活体提取法

既然静态分析受阻且外壳不走 `loadstring`，最优雅且 100% 通杀的思路是：**让壳自己把代码解开并挂载到游戏引擎，我们直接在内存中摘取成熟的果实**。

### 1. 核心理论支撑
DST 引擎要生成世界和实体，必须依赖全局数据结构：
* `GLOBAL.Prefabs[name].fn`：每个预制体的实体生成构造函数；
* `package.loaded[module]`：所有已导入的 AI 决策树（`brains/`）、状态机（`stategraphs/`）、自定义组件（`components/`）；
* `GLOBAL.ModManager.loaded_mods[modname].env`：模组专属环境。

这些函数在内存中全部是合法的标准 Lua 5.1 x64 函数对象。只要通过 Lua 原生的 `string.dump(fn)`，即可将内存中的活跃函数对象重新序列化为标准的 Lua 5.1 x64 预编译字节码（bytecode chunk）！

### 2. 突破 Klei 引擎的三道保存枷锁
在将内存字节码落地写盘时，Klei 引擎设置了三重限制：
1. **写盘权限限制**：Klei C++ 核心拦截了 Lua 脚本对游戏目录的写入操作（`io.open` 写文件会抛出 `invalid filepath`）。**解决方案**：改用官方暴露的合规存档写盘接口 `SavePersistentString(path, data)`，落盘至用户文档存档目录 `Documents/Klei/DoNotStarveTogether/<SteamID>/client_save/`。
2. **多级目录限制**：`SavePersistentString` 无法创建深层嵌套目录（如 `mod_config_data/quem/prefabs/` 会默默失败）。**解决方案**：采用扁平化前缀命名法，统一输出到 `mod_config_data/q_<category>_<name>.hex`。
3. **NUL 字节截断限制**：`string.dump` 产生的二进制流中包含大量 `\0` 字节。Klei 引擎的 C++ 导出函数将字符串参数当做 `const char*` 读取，遇到首个 `\0` 即被截断，导致写盘文件严重残缺。**解决方案**：在 Lua 层使用 `to_hex` 算法将二进制字节码转为十六进制文本字符串，彻底杜绝截断。

---

## 四、本地独立模组（Local Mod）免删防丢机制

当提取完成并准备组装独立的免壳模组时，必须注意 DST 的创意工坊同步机制：

### 1. `workshop-` 前缀的危险性
* DST 每次启动时，其内置的 Steam Workshop 同步器（`ItemQuery`）会遍历 `mods/` 下所有以 `workshop-` 开头的文件夹。
* 如果该文件夹对应的 Workshop ID 不在当前 Steam 账号的订阅列表中，或者该 ID 带有自定义后缀（如 `workshop-3152990521_clean`），Steam 同步器会将其判定为“未订阅过时垃圾文件”，直接执行物理删除：
  ```
  [Workshop] ItemQuery pending to delete mod from /mods/ folder due to it being no longer subscribed with ID: 3152990521
  [Workshop] Deleting directory: ../mods/workshop-3152990521
  ```

### 2. 纯本地模组命名规则
* 将独立模组直接命名为常规英文字符串（如 `mods/quem`）。
* 游戏引擎识别到不带 `workshop-` 前缀的目录时，会将其归入**本地模组（Local Mod）**管理体系。
* 本地模组完全不受 Steam 创意工坊退订或同步的干扰，永久驻留，离线与开服均可稳定加载。
