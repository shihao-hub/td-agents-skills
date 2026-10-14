--[[
    dump_memory.lua
    饥荒联机版（DST）通用模组内存活体提取工具
    适用于 DaxSg / 自定义 VM 壳 / 混淆加壳模组的通用提取

    工作原理：
    1. 零先验知识（Zero Prior Knowledge）：通过比对全局模组管理器（ModManager）已载入的
       第三方模组对象，或通过 TARGET_KEYWORD 动态过滤，自动捕获所有非原版实体函数。
    2. 解决 Klei 引擎 \0 截断：通过 to_hex 编码将二进制字节码转为十六进制纯文本。
    3. 解决写盘目录权限：调用合规引擎接口 SavePersistentString 落地到 client_save/mod_config_data/。
--]]

local _G = _G or getfenv()
local GLOBAL = rawget(_G, "GLOBAL") or _G

local Prefabs = rawget(GLOBAL, "Prefabs") or rawget(_G, "Prefabs") or {}
local package = rawget(GLOBAL, "package") or rawget(_G, "package") or package
local string = rawget(GLOBAL, "string") or string
local tostring = rawget(GLOBAL, "tostring") or tostring
local pairs = rawget(GLOBAL, "pairs") or pairs
local type = rawget(GLOBAL, "type") or type
local print = rawget(GLOBAL, "print") or print
local pcall = rawget(GLOBAL, "pcall") or pcall
local SavePersistentString = rawget(GLOBAL, "SavePersistentString") or rawget(_G, "SavePersistentString")
local ModManager = rawget(GLOBAL, "ModManager") or rawget(_G, "ModManager")

print("[UNIVERSAL DUMPER] Starting live memory bytecode extraction...")

-- 二进制转 Hex，彻底杜绝 SavePersistentString 遭遇 \0 截断
local function to_hex(str)
    return (str:gsub(".", function(c)
        return string.format("%02x", string.byte(c))
    end))
end

local count = 0
local function SaveBytecode(category, name, fn)
    if type(fn) ~= "function" then return end
    local ok, bc = pcall(string.dump, fn)
    if ok and bc and #bc > 0 then
        count = count + 1
        local safe_name = "q_" .. category .. "_" .. tostring(name):gsub("[^%w_]", "_") .. ".hex"
        local hex_data = to_hex(bc)
        if SavePersistentString then
            pcall(SavePersistentString, "mod_config_data/" .. safe_name, hex_data)
        end
        if count % 20 == 0 or count <= 5 then
            print(string.format("[EXTRACTED #%d] %s (%d bytes)", count, safe_name, #bc))
        end
    end
end

-- 动态目标过滤器：如果指定了全局目标关键词则按关键词过滤，否则提取所有非原生模组
local target_kw = rawget(GLOBAL, "TARGET_MOD_KEYWORD") or rawget(_G, "TARGET_MOD_KEYWORD")
local function is_target(str)
    if not str then return false end
    str = tostring(str):lower()
    if target_kw and target_kw ~= "" then
        return str:find(target_kw:lower(), 1, true) ~= nil
    end
    -- 默认通用过滤：排除系统标准库
    local sys_libs = { "string", "table", "math", "io", "os", "debug", "coroutine", "package", "_g", "strict" }
    for _, lib in pairs(sys_libs) do
        if str == lib then return false end
    end
    return true
end

-- 1. 提取所有已注册 Prefabs 中的模组实体构造函数
if ModManager and ModManager.mods then
    for mod_name, mod_data in pairs(ModManager.mods) do
        if is_target(mod_name) and mod_data.Prefabs then
            for _, p in pairs(mod_data.Prefabs) do
                if p.name and p.fn then
                    SaveBytecode("prefab", p.name, p.fn)
                end
            end
        end
    end
end

-- 补充：全局 Prefabs 扫描
for name, pref in pairs(Prefabs) do
    if is_target(name) and pref.fn then
        SaveBytecode("prefab", name, pref.fn)
    end
end

-- 2. 提取已载入模块（Brains, Components, StateGraphs, Widgets）
for modname, modtable in pairs(package.loaded or {}) do
    if is_target(modname) then
        if type(modtable) == "table" then
            for fn_name, fn in pairs(modtable) do
                if type(fn) == "function" then
                    SaveBytecode("pkg_" .. tostring(modname):gsub("[\\/]", "_"), fn_name, fn)
                end
            end
        elseif type(modtable) == "function" then
            SaveBytecode("pkg", tostring(modname):gsub("[\\/]", "_"), modtable)
        end
    end
end

-- 3. 提取 ModManager 中各模组闭包环境
if ModManager and ModManager.loaded_mods then
    for mod_id, mod_instance in pairs(ModManager.loaded_mods) do
        if is_target(mod_id) and mod_instance.env then
            for k, v in pairs(mod_instance.env) do
                if type(v) == "function" then
                    SaveBytecode("modenv_" .. tostring(mod_id):gsub("[^%w_]", "_"), k, v)
                end
            end
        end
    end
end

print(string.format("[UNIVERSAL DUMPER] Extraction Complete! Total functions dumped: %d", count))
