--[[
    dump_memory.lua
    饥荒联机版（DST）模组内存活体提取工具
    适用于 DaxSg / 自定义 VM 壳保护的模组逆向
    
    原理：
    模组通过外壳加载后，所有 Prefabs、Brains、Components 函数都以标准 Lua 5.1 x64 函数对象
    存在于引擎内存中。通过 string.dump 提取字节码，利用 to_hex 规避 Klei C++ 引擎在遇到 \0 时
    的截断 bug，并借助 SavePersistentString 落地到 client_save/mod_config_data/ 目录。
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

print("[DST DUMPER] Starting live memory bytecode extraction...")

-- 将二进制数据转为十六进制文本，避免 Klei SavePersistentString 遭遇 \0 截断
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
        print(string.format("[EXTRACTED #%d] %s (%d bytes)", count, safe_name, #bc))
    end
end

-- 目标模组特征关键词（按实际模组修改，如 quem, alicia, kuimu 等）
local mod_keywords = { "alicia", "kuimu", "fldls", "3152990521", "quem" }
local function is_target_mod(str)
    if not str then return false end
    str = str:lower()
    for _, kw in pairs(mod_keywords) do
        if str:find(kw) then return true end
    end
    return false
end

-- 1. 提取所有预制体（Prefabs）构造函数
for name, pref in pairs(Prefabs) do
    if is_target_mod(name) then
        if pref.fn then
            SaveBytecode("prefab", name, pref.fn)
        end
    end
end

-- 2. 提取已载入的包、模块、组件、AI 大脑、状态图
for modname, modtable in pairs(package.loaded or {}) do
    if is_target_mod(modname) then
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

-- 3. 提取 ModManager 中的模组闭包与独立环境
local mm = rawget(GLOBAL, "ModManager") or rawget(_G, "ModManager")
if mm and mm.loaded_mods then
    for mod_id, mod_instance in pairs(mm.loaded_mods) do
        if is_target_mod(mod_id) and mod_instance.env then
            for k, v in pairs(mod_instance.env) do
                if type(v) == "function" then
                    SaveBytecode("modenv", k, v)
                elseif type(v) == "table" and is_target_mod(k) then
                    for sub_k, sub_v in pairs(v) do
                        if type(sub_v) == "function" then
                            SaveBytecode("modenv_" .. k, sub_k, sub_v)
                        end
                    end
                end
            end
        end
    end
end

print(string.format("[DST DUMPER] Done! Successfully dumped %d bytecode functions to client_save/mod_config_data!", count))
