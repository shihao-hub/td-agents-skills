# 安全扫描说明（README-SECURITY）

覆盖：DeepSeek / Kimi / DashScope / 智谱GLM / MiniMax / 百度千帆 ALTAK / 百川 / 数据库URI / 私钥。

## 文件

- `.gitleaks.toml`：Gitleaks 主规则库（`useDefault=true` + 国内规则）。
- `secret_scanner.py`：轻量 Python 扫描器（无第三方依赖，放 skills 根目录）。
- `.githooks/pre-commit`：commit 前拦截钩子，扫描 `git diff --cached`。
- `.tests/test_secret_rules.py`：`unittest` 正向/负向/钩子仿真测试。

## 使用

```bash
git config core.hooksPath .githooks   # 在仓库根执行；子模块请在子模块目录执行
python -m unittest discover -s .tests -v
python secret_scanner.py --list-rules
echo "sk-xxxx" | python secret_scanner.py
```

## 加新规则

1. 在 `.gitleaks.toml` 追加 `[[rules]]`（regex + keywords + allowlist）。
2. 在 `secret_scanner.py` 的 `RULES` 同步追加正则。
3. 在 `.tests/test_secret_rules.py` 加正/负向用例后跑全量测试。

## 跳过钩子（紧急）

```bash
git commit --no-verify -m "msg"
```
