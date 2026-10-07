cmake_minimum_required(VERSION 3.21)
project({{PROJECT_NAME}} C CXX)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 源码为 UTF-8 无 BOM，MSVC 默认按本地编码（GBK）误读中文注释，必须显式声明
if(MSVC)
    add_compile_options(/utf-8)
endif()

# ---- Lua 5.1.5：FetchContent 拉官方源码包，随项目编译为静态库 ----
# 坑1：lua/lua 官方镜像缺 v5.1.5 tag（只到 v5.1.1），必须走 lua.org tarball
# 坑2：CMake 解压自动剥掉顶层目录，.c/.h 在源码包的 src/ 子目录
include(FetchContent)
FetchContent_Declare(
    lua
    URL https://www.lua.org/ftp/lua-5.1.5.tar.gz
    URL_HASH SHA256=2640fc56a795f29d28ef15e13c34a47e223960b0240e8cb0a82d9b0738695333
)
FetchContent_MakeAvailable(lua)
set(LUA_SRC_DIR ${lua_SOURCE_DIR}/src)

add_library(lua51 STATIC
    ${LUA_SRC_DIR}/lapi.c
    ${LUA_SRC_DIR}/lcode.c
    ${LUA_SRC_DIR}/ldebug.c
    ${LUA_SRC_DIR}/ldo.c
    ${LUA_SRC_DIR}/ldump.c
    ${LUA_SRC_DIR}/lfunc.c
    ${LUA_SRC_DIR}/lgc.c
    ${LUA_SRC_DIR}/llex.c
    ${LUA_SRC_DIR}/lmem.c
    ${LUA_SRC_DIR}/lobject.c
    ${LUA_SRC_DIR}/lopcodes.c
    ${LUA_SRC_DIR}/lparser.c
    ${LUA_SRC_DIR}/lstate.c
    ${LUA_SRC_DIR}/lstring.c
    ${LUA_SRC_DIR}/ltable.c
    ${LUA_SRC_DIR}/ltm.c
    ${LUA_SRC_DIR}/lundump.c
    ${LUA_SRC_DIR}/lvm.c
    ${LUA_SRC_DIR}/lzio.c
    ${LUA_SRC_DIR}/lauxlib.c
    ${LUA_SRC_DIR}/lbaselib.c
    ${LUA_SRC_DIR}/ldblib.c
    ${LUA_SRC_DIR}/liolib.c
    ${LUA_SRC_DIR}/lmathlib.c
    ${LUA_SRC_DIR}/loslib.c
    ${LUA_SRC_DIR}/ltablib.c
    ${LUA_SRC_DIR}/lstrlib.c
    ${LUA_SRC_DIR}/loadlib.c
    ${LUA_SRC_DIR}/linit.c
)
target_include_directories(lua51 PUBLIC ${LUA_SRC_DIR})
# Lua 5.1 源码用了 sprintf/fopen 等老 CRT 接口，屏蔽安全警告
if(MSVC OR CMAKE_C_COMPILER_ID MATCHES "Clang")
    target_compile_definitions(lua51 PRIVATE _CRT_SECURE_NO_WARNINGS)
endif()

# ---- C 库（算法/能力层，extern "C" 接口供 C++ 与 Lua 双方使用）----
add_library({{PROJECT_NAME}}core STATIC src/mathutil.c)
target_include_directories({{PROJECT_NAME}}core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/src)

# ---- C++ 宿主 ----
# 资源随构建同步到 exe 所在目录（VS 生成器 exe 在 Debug/ 子目录），
# 运行时按相对路径 scripts/xxx.lua 加载（相对进程 CWD）
add_custom_command(TARGET {{PROJECT_NAME}} POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_directory
        ${CMAKE_CURRENT_SOURCE_DIR}/scripts $<TARGET_FILE_DIR:{{PROJECT_NAME}}>/scripts
)

add_executable({{PROJECT_NAME}} src/main.cpp)
target_link_libraries({{PROJECT_NAME}} PRIVATE lua51 {{PROJECT_NAME}}core)

# 一键构建运行：cmake --build --preset <preset> --target run
# （自动先构建依赖，并以 exe 所在目录为工作目录，免手动 cd）
add_custom_target(run
    COMMAND $<TARGET_FILE:{{PROJECT_NAME}}>
    WORKING_DIRECTORY $<TARGET_FILE_DIR:{{PROJECT_NAME}}>
    DEPENDS {{PROJECT_NAME}}
    USES_TERMINAL
)

# ---- 测试：doctest + CTest ----
FetchContent_Declare(
    doctest
    GIT_REPOSITORY https://github.com/doctest/doctest.git
    GIT_TAG v2.4.12
    GIT_SHALLOW TRUE
)
FetchContent_MakeAvailable(doctest)
# 坑：doctest_discover_tests 命令由 doctest 自带 cmake 模块提供，需显式 include
include(${doctest_SOURCE_DIR}/scripts/cmake/doctest.cmake)

enable_testing()
add_executable(test_{{PROJECT_NAME}}core tests/test_mathutil.cpp)
target_link_libraries(test_{{PROJECT_NAME}}core PRIVATE {{PROJECT_NAME}}core doctest::doctest)
doctest_discover_tests(test_{{PROJECT_NAME}}core)
