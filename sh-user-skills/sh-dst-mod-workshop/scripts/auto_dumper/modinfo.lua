name = "00_脱壳抓取器 (Auto Dumper)"
description = "活体内存自动化提取工具，在所有模组加载完成后自动执行 Hex 转储，免控制台手动输入。"
author = "Reverse Tool"
version = "1.0.0"
api_version = 10
dst_compatible = true
all_clients_require_mod = false
client_only_mod = true

-- 设置超低优先级，确保在所有待脱壳的业务模组加载完毕后再执行
priority = -99999
