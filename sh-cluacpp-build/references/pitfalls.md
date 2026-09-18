# 踩坑速查（症状 → 原因 → 修复）

全部来自 trilang 三语言项目（C 算法库 + C++ 宿主嵌入 Lua 5.1.5）真实构建日志，报错信息可全文搜索。

## 构建期

### 1. `fatal: invalid reference: v5.1.5`（FetchContent 拉 Lua）

- **原因**：`lua/lua` 官方 GitHub 镜像的 5.1 系列 tag 只到 v5.1.1，v5.1.5 不存在
- **修复**：改用 lua.org 官方 tarball：

```cmake
FetchContent_Declare(
    lua
    URL https://www.lua.org/ftp/lua-5.1.5.tar.gz
    URL_HASH SHA256=2640fc56a795f29d28ef15e13c34a47e223960b0240e8cb0a82d9b0738695333
)
```

### 2. `Cannot find source file: .../_deps/lua-src/lapi.c`

- **原因**：CMake URL 模式解压会**自动剥掉 tarball 顶层目录**（`lua-5.1.5/`），且 Lua 源码包把 .c/.h 全放在 `src/` 子目录；`SOURCE_SUBDIR` 不改变 `<name>_SOURCE_DIR` 变量
- **修复**：`set(LUA_SRC_DIR ${lua_SOURCE_DIR}/src)`，源文件写 `${LUA_SRC_DIR}/lapi.c`，头文件搜索 `${LUA_SRC_DIR}`

### 3. MSVC `error C2065: "xxx": 未声明的标识符`（报错附近中文乱码）

- **原因**：cl.exe 默认按本地编码（GBK）读**无 BOM UTF-8** 源文件，中文注释字节被误读，可吞掉行尾的 `if(` 等代码导致后续报错；clang 默认 UTF-8 所以同代码 clang 能过
- **修复**：`CMakeLists.txt` 里 `if(MSVC) add_compile_options(/utf-8) endif()`

### 4. `error: use of undeclared identifier 'LUA_OK'`

- **原因**：`LUA_OK` 是 Lua 5.2+ 的宏，5.1 没有
- **修复**：Lua 5.1 惯例与非 0 比较：`if (luaL_dofile(L, path) != 0)`、`if (lua_pcall(...) != 0)`

### 5. 运行时报 `cannot open scripts/xxx.lua: No such file or directory`

- **原因**：VS 生成器把 exe 放 `out/build/<preset>/Debug/` 子目录，而资源按 `${CMAKE_BINARY_DIR}` 拷贝就错位；且 exe 内相对路径按**进程 CWD** 解析，不是 exe 所在目录
- **修复**：POST_BUILD 拷到 exe 旁 + run target 固定工作目录（模板已内置）：

```cmake
add_custom_command(TARGET <target> POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_directory
        ${CMAKE_CURRENT_SOURCE_DIR}/scripts $<TARGET_FILE_DIR:<target>>/scripts)

add_custom_target(run
    COMMAND $<TARGET_FILE:<target>>
    WORKING_DIRECTORY $<TARGET_FILE_DIR:<target>>
    DEPENDS <target>
    USES_TERMINAL)
```

### 6. `Unknown CMake command "doctest_discover_tests"`

- **原因**：doctest v2.4.12 的 `scripts/cmake/` 里**没有** `doctestDiscover.cmake`（旧名），命令在 `doctest.cmake` 模块中，且不会随 `FetchContent_MakeAvailable` 自动可用
- **修复**：`include(${doctest_SOURCE_DIR}/scripts/cmake/doctest.cmake)`

### 7. `clangd: 'lua.h' file not found`（Zed/编辑器里）

- **原因**：clangd 靠 `compile_commands.json` 拿编译参数（include 路径），默认只探测文件向上各级目录的 `compile_commands.json` 与 `build/`；preset 产物在 `out/build/` 探测不到
- **修复**：项目根放 `.clangd`：`CompileFlags: CompilationDatabase: out/build/clang-debug`（相对 .clangd 所在目录解析）。**不要**在 Zed 全局 settings 里配 `--compile-commands-dir`——它相对 Zed 项目根（仓库根）解析，跨目录必错

## 编辑器 / LSP（Zed）

### 8. CMakeLists.txt / .toml / .lua 无高亮

- **原因**：Zed 深度内置语言仅 14 种（Bash/C/C++/CSS/Diff/Go/JS/JSON/Markdown/Python/Rust/Tailwind/TS/YAML），其余全靠扩展；Lua 在自动安装白名单所以"感觉内置"，CMake 不在（官方扩展库无 `cmake`，实际提供者是 **NeoCMake**）
- **修复**：父仓库 `.zed/extensions.toml` 声明 + `auto_install_extensions`（**对象格式**，扩展名→bool）：

```toml
[neocmake]
version = "1.0.0"
```

`version` 是必填的**最低版本要求**（无 latest 写法），配合默认全开的自动更新即"始终最新"。装扩展后其自带 `path_suffixes` 自动识别 `CMakeLists.txt`，无需 file_types 映射。

### 9. Lua 跳转进 5.4 的标准库定义

- **原因**：lua-language-server 内置标准库签名默认按 Lua 5.4 提供，与项目链接的 5.1.5 不符
- **修复**：`.zed/settings.json`：

```jsonc
"lua-language-server": {
  "settings": { "Lua": { "runtime": { "version": "Lua 5.1" } } }
}
```

### 10. Lua 报 `Undefined global 'tri'`（宿主注入的全局）

- **原因**：C++ 宿主运行时注册的全局，LSP 静态分析看不见；LSP 按语言隔离，**没有跨 C++/Lua 的混合 LSP**
- **修复**：项目 `meta/host_env.lua` 写类型声明（业界通行做法，游戏引擎同款）：

```lua
tri = {}
---@param n integer 序号（0 起）
---@return integer fib(n)
function tri.fib(n) end
```

### 11. 声明文件报 `Annotations specify that a return value is required here`

- **原因**：`---@return` 注解撞上空函数体，触发 missing-return 诊断
- **修复**：声明文件**首行加 `---@meta`**——官方声明文件机制，跳过全部诊断（内置标准库声明全是这种空函数体写法）

## 工具与流程

### 12. PowerShell 5.1 改文件后中文全变乱码

- **原因**：`Get-Content`/`Set-Content` 默认 ANSI(GBK) 编码读写 UTF-8 文件，中文字节被毁且不可逆（曾把注释与 `if(` 挤成一行导致 CMake flow control 报错）
- **修复**：**禁止用 PowerShell 文本 cmdlet 改带中文的 UTF-8 文件**，一律用专用文件编辑工具；JSONC 校验可用 `python -c` 去 `//` 注释后 `json.loads`
