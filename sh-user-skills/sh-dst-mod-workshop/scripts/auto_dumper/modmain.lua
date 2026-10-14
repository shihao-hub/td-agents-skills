local _G = GLOBAL
local TheSim = _G.TheSim

print("[AUTO DUMPER] Auto Dumper Mod loaded, waiting for world & entity initialization...")

-- 当模拟器与玩家就绪后，延时 1 秒自动执行 dump 逻辑
AddSimPostInit(function()
    TheSim:ExecuteInTime(1.5, function()
        print("[AUTO DUMPER] Triggering automated memory extraction...")
        local dump_file = MODDIR .. "dump_memory.lua"
        local fn, err = loadfile(dump_file)
        if fn then
            local ok, run_err = pcall(fn)
            if ok then
                print("[AUTO DUMPER] Memory dump finished automatically! You can safely exit DST now.")
            else
                print("[AUTO DUMPER] Error executing dump script: " .. tostring(run_err))
            end
        else
            print("[AUTO DUMPER] Could not load dump_memory.lua: " .. tostring(err))
        end
    end)
end)
