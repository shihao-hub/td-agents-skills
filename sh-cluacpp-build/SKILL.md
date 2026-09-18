---
name: sh-cluacpp-build
description: native_projects（C/C++/Lua 混合语言子仓）的工具链与构建手册。Windows 下 LLVM/Ninja/MSVC 工具链检测与安装（含 GitHub 下载慢的 curl 断点续传方案、静默装完不写 PATH 的补法）、CMake+CMakePresets+Ninja 双编译器项目搭建、FetchContent 集成 Lua 5.1.5 与 doctest、MSVC 编码/Lua API/VS 生成器目录等 12 条踩坑速查、clangd(.clangd) 编译数据库配置、Zed 扩展与 LSP（neocmake 高亮、Lua 5.1 runtime、宿主全局 @meta 声明）。当用户要在 language_projects 总仓新建/编译/调试 C、C++、Lua 项目，安装 clang/LLVM/ninja，遇到 'lua.h' file not found、C2065 中文乱码、LUA_OK 未定义、链接 32 位 Lua 报错、FetchContent 拉 Lua 失败、CMakeLists.txt 无高亮、Lua LSP 跳转到 5.4 等场景时必须使用。
---

# sh-cluacpp-build —— native_projects 构建手册

本 skill 沉淀自 `td-native_projects/trilang` 三语言项目从零到双编译器构建成功的完整验证链路（Windows）。

## 本机环境事实（先读这里，避免重复探测）

| 工具 | 状态 | 备注 |
|---|---|---|
| CMake 4.2 | 已装 | `D:\Program Files\CMake\bin` |
| VS Build Tools 2022 (MSVC) | 已装 | 用 vswhere 探测，VS 生成器无需 vcvars |
| MSYS2 MinGW64 (gcc/g++) | 已装 | 在 PATH，备选编译器 |
| LLVM 22 (clang/clangd/clang-format/clang-tidy) | 已装 | `C:\Program Files\LLVM\bin`，已补用户 PATH |
| Ninja 1.13 | 已装 | winget 安装，用户 PATH |
| xmake | 已装 | 轻量项目备选构建 |
| Lua 5.1 / LuaJIT | **32 位，不可链接 x64** | 一律走 FetchContent 源码编译 |

## 工作流总览

```
① 环境检测（只需首次）→ ② 工具链安装（缺什么装什么）→ ③ 复制 assets 模板建项目
→ ④ 三条命令构建运行 → ⑤ 编辑器集成（clangd + Zed 扩展/LSP）
```

### ① 环境检测

首次在新机器上工作时，按 `references/toolchain.md` 的检测矩阵跑一遍，确认上表各工具在位。

### ② 工具链安装

- Ninja：`winget install Ninja-build.Ninja -e`（小包秒装）
- LLVM：**winget 会超时**，按 `references/toolchain.md` 的 curl 断点续传方案（约 450MB，NSIS `/S` 静默装，**装完不会写 PATH 需手动补**——细节全在 toolchain.md）
- 已全装则跳过本步

### ③ 建项目（模板优先）

从本 skill 的 `assets/` 复制两个模板到新项目目录（`native_projects/<项目名>/`）：

- `assets/CMakeLists.txt.tpl` → `CMakeLists.txt`（替换 `{{PROJECT_NAME}}`）
- `assets/CMakePresets.json.tpl` → `CMakePresets.json`（双 preset：clang+Ninja 快链路 / MSVC+VS 生成器）

模板已内置全部踩坑修复：`/utf-8`、Lua 5.1.5 tarball FetchContent（29 个源文件 + `_CRT_SECURE_NO_WARNINGS`）、doctest + CTest、资源 POST_BUILD 同步、run target。**不要凭记忆重写，模板是验证过的最短路径。**

项目骨架约定：

```
<项目名>/
├── CMakeLists.txt / CMakePresets.json / .clangd
├── src/        # C 库(.c/.h) + C++ 宿主(.cpp)
├── scripts/    # Lua 脚本（随构建同步到 exe 旁）
├── tests/      # doctest 测试
└── meta/       # 宿主全局的 Lua 类型声明（@meta 文件）
```

`.clangd`（每个项目根放一份，指向自己的构建目录）：

```yaml
CompileFlags:
  CompilationDatabase: out/build/clang-debug
```

### ④ 构建运行（三条命令 + 一键）

```powershell
cd native_projects\<项目名>
cmake --preset clang-debug          # ① 配置：生成 out/build/clang-debug（build.ninja、compile_commands.json、_deps）
cmake --build --preset clang-debug  # ② 构建：Ninja 并行编译
ctest --preset clang-debug          # ③ 测试
cmake --build --preset clang-debug --target run   # 一键：增量构建 + 以 exe 目录为 CWD 运行
```

`out/` 构建树由 preset 的 `binaryDir` 指定，源码树零污染，删掉即彻底清理（.gitignore 已忽略 `out/`、`build/`）。

### ⑤ 编辑器集成（Zed）

- **CMake 高亮**：Zed 内置语言仅 14 种（无 CMake/TOML/Lua/HTML/PowerShell），由父仓库 `.zed/extensions.toml` 声明 neocmake 等扩展自动安装；`extensions.toml` 的 `version` 是必填下限（非锁死），配合默认自动更新即"始终最新"
- **Lua LSP 对准 5.1**：父仓库 `.zed/settings.json` 已配 `Lua.runtime.version = "Lua 5.1"`（默认 5.4，跳转/补全会对不上号）
- **宿主注入全局**（如 C++ 注册的 `tri` 表）：Lua LSP 静态分析看不见 → 写 `meta/host_env.lua` 声明（首行 `---@meta` 免诊断 + EmmyLua 注解提供跳转与签名），见 `references/pitfalls.md` 第 10-11 条
- **clangd**：全局 `--background-index=false` 省内存；编译数据库靠各项目 `.clangd` 指定（不要在 Zed 全局配置里写 `--compile-commands-dir`，相对路径按 Zed 项目根解析会指错位置）

## 何时读哪个文件

| 场景 | 去处 |
|---|---|
| 装工具链 / PATH 问题 / 下载超时 | `references/toolchain.md` |
| 编译或 LSP 报错 | `references/pitfalls.md`（症状→原因→修复，先查表） |
| 新建项目 | `assets/` 两个模板直接复制改造 |

## 核心原则（why）

- **源码树与构建树分离**：CMake 的 out-of-tree 设计，产物全在 `out/`，随时删掉重建
- **Lua 一律源码编译**：本机 Lua 安装是 32 位老包，任何预编译 lib 都可能踩位数/编译器 ABI 坑；FetchContent 源码随项目编译是唯一稳路径
- **双 preset 双编译器**：clang+Ninja 是日常快链路；MSVC(VS 生成器) 验证企业主流编译器兼容性，两者产物目录隔离互不干扰
- **坑都踩过了**：pitfalls.md 里 12 条全部来自 trilang 真实构建日志，报错信息可全文搜索
