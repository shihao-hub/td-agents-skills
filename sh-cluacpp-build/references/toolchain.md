# 工具链检测与安装（Windows）

## 检测矩阵（新机器首跑）

```powershell
$tools = 'cmake','ninja','cl','gcc','g++','clang','clangd','xmake','vcpkg','conan','lua','luajit'
foreach ($t in $tools) {
    $cmd = Get-Command $t -ErrorAction SilentlyContinue
    if ($cmd) { "$t => $($cmd.Source)" } else { "$t => (not found)" }
}
```

- `cl` 不在 PATH 是正常的（MSVC 需 vcvars 环境），单独用 vswhere 探测：

```powershell
& "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe" `
    -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 `
    -property installationPath
# 返回路径（如 ...\2022\BuildTools）即 MSVC x64 工具集在位
```

- clang/clangd 验证：`clang --version`（新装后当前会话看不到，先按下面方法刷新 PATH）

## Ninja 安装（小包，winget 直装）

```powershell
winget install Ninja-build.Ninja -e --silent --accept-package-agreements --accept-source-agreements
```

装到用户 PATH（`%LOCALAPPDATA%\Microsoft\WinGet\Packages\...`）。

## LLVM 安装（约 450MB，winget 会超时，用 curl 断点续传）

实测 winget 从 GitHub 下载 LLVM 安装包 10 分钟超时；直连速度约 1.5MB/s 且波动，**curl `-C -` 可断点续传，winget 不行**：

```powershell
# 1. 断点续传下载（可反复执行，接着上次的进度）
$f = "$env:TEMP\LLVM-22.1.8-win64.exe"
curl.exe -sL --retry 3 -C - -o $f `
  "https://github.com/llvm/llvm-project/releases/download/llvmorg-22.1.8/LLVM-22.1.8-win64.exe"

# 2. NSIS 静默安装（默认装 C:\Program Files\LLVM）
Start-Process -FilePath $f -ArgumentList '/S' -Wait

# 3. 补 PATH（坑：/S 静默安装不会写 PATH！）
$userPath = [System.Environment]::GetEnvironmentVariable('Path','User')
if ($userPath -notlike '*LLVM*') {
    [System.Environment]::SetEnvironmentVariable('Path',
        $userPath.TrimEnd(';') + ';C:\Program Files\LLVM\bin', 'User')
}

# 4. 当前会话立即生效（新开终端无需此步）
$env:Path = [System.Environment]::GetEnvironmentVariable('Path','Machine') + ';' +
            [System.Environment]::GetEnvironmentVariable('Path','User')
clang --version; clangd --version; clang-format --version
```

## 会话内刷新 PATH（通用技巧）

winget/curl 装完的新工具，已开的 shell 会话里 `Get-Command` 找不到，用：

```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable('Path','Machine') + ';' +
            [System.Environment]::GetEnvironmentVariable('Path','User')
```

## Lua 环境判定（重要）

本机 `D:\Program Files (x86)\Lua\5.1`（LuaForWindows）与 `D:\Programmer\luajit2`：

- **均为 32 位**（x86 安装、带 VC80 CRT），`lua5.1.lib` 无法给 x64 MSVC/MinGW 链接
- LuaJIT 目录只有 exe/dll，无头文件与导入库
- **结论：嵌入宿主一律 FetchContent 拉 lua.org 官方 tarball 源码编译**（见 assets/CMakeLists.txt.tpl），不要试图链接本机安装

LuaJIT 5.1 语义与 Lua 5.1 一致；LuaRocks（Lua 模块包管理）需要时再装。

## 版本参考（2026-09 验证）

CMake 4.2 / Ninja 1.13.2 / LLVM 22.1.8（clang、clangd、clang-format、clang-tidy 同包）/ VS Build Tools 2022 / MSYS2 MinGW64 / xmake
