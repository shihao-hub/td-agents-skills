--[[
    DST Mod 通杀型动态解密脱壳 Hook 脚本
    原理：
    饥荒游戏加载模组时，被混淆/加密的代码（如 DaxSg）最终必须通过 GLOBAL.loadstring 动态编译。
    若直接修改模组的 modmain.lua，会触发自校验 Hash 校验与反调试陷阱（如写入 \sblg..vbs 嘲讽脚本）。
    因此最优方案是在 modsettings.lua 或外部预加载阶段进行非侵入式 Hook：
    保持模组文件 100% 原始不变，仅在引擎层拦截动态代码执行并 Dump 明文源码。
--]]

local DUMP_DIR = "D:/dst_mod_dump/"

-- 确保输出目录存在（可通过 os.execute 创建）
pcall(function()
    os.execute('mkdir "' .. DUMP_DIR:gsub("/", "\\") .. '" 2>nul')
end)

local counter = 0
local dumped_chunks = {}

-- 1. Hook GLOBAL.loadstring
local original_loadstring = _G.loadstring or loadstring
local function hooked_loadstring(str, chunkname)
    counter = counter + 1
    local name = tostring(chunkname or ("chunk_" .. counter))
    local safe_name = name:gsub("[^%w_%-%.]", "_")

    if str and type(str) == "string" and #str > 0 then
        -- 避免重复写入相同内容
        if not dumped_chunks[safe_name] then
            dumped_chunks[safe_name] = true
            local dump_path = DUMP_DIR .. safe_name .. ".lua"
            local f = io.open(dump_path, "wb")
            if f then
                f:write(str)
                f:close()
                print(string.format("[DUMP SUCCESS] 已抓取解密代码: %s (%d bytes)", dump_path, #str))
            else
                print("[DUMP ERROR] 无法写入文件: " .. dump_path)
            end
        end
    end

    return original_loadstring(str, chunkname)
end

_G.loadstring = hooked_loadstring
if GLOBAL and GLOBAL ~= _G then
    GLOBAL.loadstring = hooked_loadstring
end

-- 2. Hook RunInSandbox（部分高版本 DST 模组加载器）
if _G.RunInSandbox then
    local orig_sandbox = _G.RunInSandbox
    _G.RunInSandbox = function(fn, env)
        return orig_sandbox(fn, env)
    end
end

print("[HOOK INSTALLED] DST Mod 动态代码拦截器已就绪，等待模组加载...")
