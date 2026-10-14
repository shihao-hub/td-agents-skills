# 案例深度研析：奎姆模组（Quem，3152990521）实战脱壳全解析

> 本案例作为 `sh-dst-mod-workshop` 通用逆向技能的**深度实战参考对照**（Case Study）。
> 记录了针对 DaxSg 保护壳在真实商业级模组中的攻防全过程，用于供开发者和 AI 进行技术机理比对，**不作为通用 SOP 的硬编码依赖**。

---

## 一、样本档案
* **模组名称**：奎姆（Quem）
* **创意工坊 ID**：`3152990521`
* **版本号**：7.8
* **壳类型**：DaxSg 轻量级虚拟机外壳（混淆 + 寄存器 VM + 自校验）

---

## 二、DaxSg 外壳在奎姆中的具体实现

### 1. 结构与文件清单
```
workshop-3152990521/
├── anim/                   (原始明文动画资源，未加密)
├── bigportraits/           (原始明文立绘，未加密)
├── images/                 (原始明文贴图，未加密)
├── modinfo.lua             (明文配置参数，未加密)
├── daxsg_mod_path.txt      (列出所有受 DaxSg 托管的 73 个脚本相对路径)
├── modmain.lua             (DaxSg 引导加载器：~40KB 混淆代码)
├── modmain0.lua            (DaxSg 核心解密机与自校验块：~100KB)
├── modmain1.lua            (DaxSg 预混淆中间数据与字节流：~140KB)
└── scripts/                (包含 73 个受加密脚本与部分明文语音脚本)
```

### 2. 攻防细节实录
1. **0x1A 截断实录**：`modmain0.lua` 在偏移 165 处含有 Windows CRT EOF 字节。当 Python 以 `'r'` 模式打开时，文件在 165 字节处截断，导致 DaxSg 内部期望的 `100724` 大小不一致，直接触发安全防御。
2. **反调试死锁与 VBS 弹窗**：在 `modmain.lua` 偏移 29203 字节处设有 `daxsg_mistake` 陷阱。任何对 `modmain.lua` 的改动都会导致死锁与 VBS 弹窗。
3. **活体内存提取实战**：通过 `dump_memory.lua` 提取到 336 个 Hex 文件，转码出 336 个 64 位 `.luac` 预编译块，成功解析出：
   * 119 个 Prefab（包含 `kuimu_staff`, `kuimu_whiteboss`, `alicia` 等）；
   * 5 个专属 AI 决策脑（包含 `alicia_fldlsbrain.lua` 等）；
   * 13 个专属组件逻辑与全部 StateGraphs。
