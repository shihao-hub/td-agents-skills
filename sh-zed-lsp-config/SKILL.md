---
name: sh-zed-lsp-config
description: '为指定项目目录配置 Zed 编辑器的 .zed/settings.json LSP 白名单，配合全局 enable_language_server: false 实现"默认零 LSP、按项目白名单开启、尽量省内存"。当用户要求给某个目录/仓库"配置 zed / 来一个 .zed / 开跳转 / 阅读源码省内存"，或提到 vtsls、basedpyright、language_servers、enable_language_server、zed 内存占用等场景时使用。'
---

# Zed LSP 项目白名单配置

## 用户既定策略（前提，不要偏离）

用户的全局配置 `C:\Users\shawn.zhang\AppData\Roaming\Zed\settings.json` 已有顶层 `"enable_language_server": false`（全关）。本 skill 的工作是在**指定项目根目录**创建/更新 `.zed/settings.json`，用语言级 `enable_language_server: true` 单独放开需要的语言——白名单模式，目标是在"能跳转阅读代码"的前提下尽量省内存。**不要改全局文件**，除非用户明确要求。

## 工作流

### 第 1 步：扫描项目语言构成

不要只看根目录，常见的坑是 node_modules / package.json 藏在深层子目录（如 `code-practice/react/tic-tac-toe/node_modules`），带 maxdepth 的扫描会漏。推荐命令：

```bash
cd <目标目录>
ls -a                                   # 看根目录 markers（package.json/tsconfig.json/pyproject.toml/go.mod/Cargo.toml）和是否有 .git
find . -type d -name node_modules -not -path '*/node_modules/*'   # 全深度找嵌套 node_modules
find . \( -name package.json -o -name 'tsconfig*.json' \) -not -path '*/node_modules/*'
find . -type f -not -path '*/node_modules/*' -not -path '*/.git/*' -not -path '*/.venv/*' -not -path '*/__pycache__/*' -not -path '*/dist/*' | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -12
```

### 第 2 步：按映射选择语言服务器（宁少勿多）

| 项目构成 | 开启 | server | 附加加固 |
|---|---|---|---|
| Python 为主（阅读/大仓库） | Python | basedpyright | `diagnosticMode: "openFilesOnly"` + `autoSearchPaths: false` |
| TS/TSX 为主（monorepo） | TypeScript + TSX + JavaScript | vtsls | `maxTsServerMemory: 2048`；依赖不全再加 `disableAutomaticTypeAcquisition: true` |
| 少量 JS 练习文件 | JavaScript（+预置 TS/TSX） | vtsls | 无 node_modules 时加 `disableAutomaticTypeAcquisition: true` |

原则：

- **单 server 优先**：Python 只跑 basedpyright（排除 ruff/pyright 并发）；TS/JS 只跑 vtsls（排除 typescript-language-server/eslint）。
- **TSX 必须单独声明**：Zed 中 `.ts`→TypeScript、`.tsx`→TSX、`.js/.jsx/.mjs`→JavaScript 是三个独立语言条目，漏了 TSX 则 .tsx 文件没有跳转。
- **预置零成本**：LSP 只在打开对应语言文件时才拉起，所以多写语言条目不花钱——但非主力语言默认不写，告知用户可后补。
- 映射表之外的语言（Vue.js→volar、Go→gopls、Rust→rust-analyzer）：小众语言默认不开，说明一句"需要时加 XX 条目"。
- 用户说"阅读/学习/越轻越好"→ 只开主力语言；日常开发项目 → 可适当开全。没说明就按阅读处理并告知。

### 第 3 步：写入 `.zed/settings.json`

JSONC 格式（允许 `//` 中文注释）。若文件已存在，**先读原文件再合并**，不得覆盖用户已有配置。三个实战模板：

**Python 项目（阅读学习，如 QwenPaw）：**

```jsonc
{
  // 阅读学习用：只开 basedpyright 做 Python 跳转（配合全局 enable_language_server: false）
  "languages": {
    "Python": {
      "enable_language_server": true,
      "language_servers": ["basedpyright"]
    }
  },
  // 只分析打开的文件：跳转/补全保留，避免全量索引吃内存
  "lsp": {
    "basedpyright": {
      "settings": {
        "basedpyright.analysis.diagnosticMode": "openFilesOnly",
        "basedpyright.analysis.autoSearchPaths": false
      }
    }
  }
}
```

**TS monorepo（如 deepseek-harness）：**

```jsonc
{
  // 阅读源码用：只开 vtsls 提供 TS/TSX/JS 跳转（配合全局 enable_language_server: false）
  "languages": {
    "TypeScript": { "enable_language_server": true, "language_servers": ["vtsls"] },
    "TSX": { "enable_language_server": true, "language_servers": ["vtsls"] },
    "JavaScript": { "enable_language_server": true, "language_servers": ["vtsls"] }
  },
  // 限制 tsserver 堆上限，防止大 monorepo 下内存无限膨胀
  "lsp": {
    "vtsls": {
      "settings": {
        "typescript": {
          "tsserver": { "maxTsServerMemory": 2048 },
          "disableAutomaticTypeAcquisition": true
        },
        "javascript": {
          "tsserver": { "maxTsServerMemory": 2048 },
          "disableAutomaticTypeAcquisition": true
        }
      }
    }
  }
}
```

**轻量学习仓库（如 frontend-learning-guide）：**

```jsonc
{
  // 学习仓库：JS/JSX 立即可用；TypeScript/TSX 预置零成本，打开对应文件才拉起 vtsls
  "languages": {
    "JavaScript": { "enable_language_server": true, "language_servers": ["vtsls"] },
    "TypeScript": { "enable_language_server": true, "language_servers": ["vtsls"] },
    "TSX": { "enable_language_server": true, "language_servers": ["vtsls"] }
  }
}
```

### 第 4 步：汇报与提醒

完成后向用户说明：

1. 开了什么、没开什么、理由（一句话级别）。
2. 验证方式：打开对应语言文件用 `gd` 跳转；任务管理器看 node / basedpyright 进程数量与内存。
3. 按需提醒：
   - **git 仓库**：`.zed/settings.json` 会随提交影响所有用 Zed 的同事，是否提交由用户决定。
   - **worktree 范围**：该文件只对"所在目录作为项目根打开"的窗口生效；单独打开子目录需复制一份。
   - **多窗口**：每个 Zed 窗口独立一套 LSP 实例，同仓库多窗口 = 内存翻倍。
   - 配置保存即时生效，无需重启 Zed。

## 关键事实（避免凭模糊记忆写错）

- `language_servers` 数组**整体替换**默认列表：只列谁就只跑谁，不需要 `"..."`；`"!name"` 是排除语法。
- 语言级 `enable_language_server` 覆盖顶层同名设置；顶层（项目文件里也可写）一键全关是 `{"enable_language_server": false}`。
- `diagnosticMode: "openFilesOnly"` 只砍诊断（未打开文件的红色报错），跳转/引用/悬停全保留——对"只读阅读"是纯赚。
- `maxTsServerMemory` 是封顶不是降低日常占用；低于 2048 会导致大项目反复重启重建、跳转变卡，不要设更低。
- tsserver 的内存大头是全项目类型图，精确跳转的前提，配置省不掉；嫌内存大时正确做法是**缩小打开范围**（只打开子项目目录并复制一份配置），而不是压上限。
- Windows 本机全局配置在 `AppData\Roaming\Zed\settings.json`（不是 LocalAppData；LocalAppData 下是 db/extensions 等数据）。
