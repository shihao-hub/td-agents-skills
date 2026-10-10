# Plan: 国内平台 API Key / 敏感凭据识别与本地 Git 拦截规则配置

📋 Plan for: "在当前仓库配置针对国内主流大模型与云平台的敏感凭据识别规则库（.gitleaks.toml 与 Git Hook），并提供基于 Python 的规范化测试套件（.tests/）"

## 问题陈述
GitHub 个人全局推送保护（Push protection for yourself）存在两个关键限制：
1. 仓库范围：仅对公开仓库（Public）生效，私有仓库/本地提交不会自动激活；
2. 规则范围：仅覆盖与 GitHub 官方合作的海外主流服务商（如 OpenAI、AWS 等），国内主流大模型平台（如 DeepSeek、月之暗面 Kimi、通义千问 DashScope、智谱 GLM、MiniMax、百度千帆、百川等）由于未加入合作计划，其 API Key 提交到仓库时会被完全放行。

需要一套针对国内主流模型与敏感凭据的规则集，在代码提交（commit）或推送（push）前实现本地化零成本拦截，并配套 Python 单元测试确保规则有效且不误报。

## 需求（含用户决策）
1. 应用范围：先部署在当前仓库（D:/Users/language_projects/.agents/skills）；
2. 工具形态：采用 Gitleaks 规范配置文件（.gitleaks.toml）为主规则库，同时配备无需外部重型依赖的轻量 Git Hook 联动；
3. 平台覆盖：国内主流大模型全集（DeepSeek、月之暗面 Kimi、阿里通义千问 DashScope、智谱 GLM、MiniMax、百度千帆、百川智能）及通用高危敏感串（带密码数据库连接串、标准私钥）；
4. 测试规范：所有测试一律采用 Python 脚本，放置在 .tests/ 目录下，禁止使用裸 powershell/bash 脚本进行断言。

## 背景与调研
- 仓库环境：当前仓库为 Git 子模块（.git 为指针文件指向 ../../.git/modules/.agents/skills），若使用传统 .git/hooks 会受子模块路径影响，因此最佳实践是配置 git config core.hooksPath .githooks，将 Hook 文件直接保存在版本库内的 .githooks/ 目录中统一版本化管理；
- 运行环境：已探测到本机原生配备 Python 3.12.5 与 uv，具备无需额外安装其他运行时的 Python 自动化执行能力；
- 国内 Key 特征调研：
  - DeepSeek：sk-[a-f0-9]{32}（32 位纯小写十六进制字符串，如 sk-4a8b...）；
  - 月之暗面 (Moonshot / Kimi)：sk-[a-zA-Z0-9]{48}（48 位 Base62 字符串）；
  - 通义千问 (DashScope)：sk-[a-f0-9]{32}（32 位十六进制字符串）；
  - 智谱 AI (GLM)：<32位uuid/key>.<16-32位secret> 组合凭证；
  - MiniMax：Group ID + API Key / JWT 鉴权格式；
  - 百度千帆 (Baidu Qianfan)：ALTAK-... 专有前缀鉴权 Token；
  - 百川智能 (Baichuan)：sk-[a-zA-Z0-9]{32}；
  - 排除规则（防止误报）：需排除 sk-your-key-here、sk-xxxx 等占位符，以及环境变量读取语法（如 os.getenv("...")）。

## 方案设计
1. 规则定义：创建 .gitleaks.toml，以 TOML 格式定义国内厂商专用 [[rules]]，包含精确 regex、关键词 keywords 以及白名单 allowlist（排除常见测试占位符）；
2. 钩子调度：创建 .githooks/pre-commit 拦截器脚本（Python 驱动），在执行 git commit 时自动提取暂存区代码（git diff --cached），基于规则执行正则匹配，发现泄露立即以 exit code 1 阻断提交，并打印友好中文告警；
3. 测试套件：创建 .tests/test_secret_rules.py，使用 Python 原生 unittest 框架：
   - 正向测试：针对各大国内厂商真实特征测试样例，断言全部命中；
   - 负向测试：针对正常占位符、注释、环境变量读取代码，断言全部豁免放行；
   - 钩子仿真测试：验证扫描函数的检测准确率与返回码。

## 任务分解

- [x] Task 1: 编写国内平台凭据识别规则文件 .gitleaks.toml
  - 文件：D:/Users/language_projects/.agents/skills/.gitleaks.toml
  - 实现：定义 DeepSeek、Kimi、通义千问、智谱 GLM、MiniMax、百度千帆、百川智能等专属规则段，配置 regex、keywords 和 allowlist
  - 验证：运行 Python 解析该 TOML 文件，确认语法合法无错误
  - Demo：能够完整打印出所有加载的规则 ID 和关键词列表

- [x] Task 2: 编写基于 Python 的凭据扫描器与 Git Hook 拦截脚本
  - 文件：D:/Users/language_projects/.agents/skills/.githooks/pre-commit, D:/Users/language_projects/.agents/skills/scripts/secret_scanner.py
  - 实现：实现读取 .gitleaks.toml 正则的扫描核心函数，并在 pre-commit 钩子中接入，检查 git diff --cached 变动文本
  - 验证：运行 git config core.hooksPath .githooks 激活钩子，并通过扫描模块测试函数检测静态文本
  - Demo：模拟暂存区含敏感 Key 时抛出拦截提示并拒绝提交

- [x] Task 3: 编写 Python 自动化测试套件 .tests/test_secret_rules.py
  - 文件：D:/Users/language_projects/.agents/skills/.tests/test_secret_rules.py
  - 实现：使用 Python unittest 编写正向测试用例（覆盖上述 7+ 家国内模型平台及数据库 URI）与负向用例（代码中的环境变量、示例占位符）
  - 验证：执行 python -m unittest .tests/test_secret_rules.py，全部测试用例 PASS (Ran N tests, OK)
  - Demo：控制台输出完整的用例通过清单与覆盖的国内平台列表

- [x] Task 4: 联调验证与仓库配置固化
  - 文件：D:/Users/language_projects/.agents/skills/README-SECURITY.md
  - 实现：编写简明配置与使用指南（如何添加新规则、如何单测、如何临时跳过），并在仓库中完成配置
  - 验证：运行 python -m unittest discover .tests 确认整体测试绿灯
  - Demo：完整的规则、钩子、测试与使用说明闭环就绪

---
**最后更新：** 2026-10-09
**作者：** AI & User
**版本：** v1.0.0
