# VS Code 系分支的目录坐标（推导规则 + 本机实测）

## 一、通用推导规则（任何分支都适用）

每个分支的安装目录里都有 `resources/app/product.json`，四个字段决定所有路径：

| 字段 | 决定什么 | 路径 |
|---|---|---|
| `dataFolderName`（如 `.cursor`） | 程序级数据：扩展目录、argv.json | `%USERPROFILE%\<dataFolderName>\extensions`、`...\<dataFolderName>\argv.json` |
| `nameShort`（如 `Cursor`） | 运行级数据：设置、状态、缓存 | `%APPDATA%\<nameShort>\User\settings.json`、`...\User\globalStorage\state.vscdb` |
| `applicationName`（如 `cursor`） | CLI 名 | `<安装目录>\bin\<applicationName>.cmd`（Windows）/ 同名无后缀（macOS/Linux） |
| `extensionsGallery.serviceUrl` | 该分支的扩展市场 | 决定"能不能直接装" |

要点：

- **两个目录不是一回事**：`~\.<dataFolderName>` 放扩展与 argv，`%APPDATA%\<nameShort>` 放用户设置与运行状态。只搬扩展不写设置时，改的是前者；要改主题/配置时，动的是后者。
- **扩展注册表按 profile 分**：默认 profile 用 `<扩展目录>\extensions.json`；具名 profile 用 `<userData>\User\profiles\<profile>\extensions.json`。目标分支若存在 `User\profiles\` 下的具名 profile，注册表要改对文件，否则"注册了但那个 profile 看不见"。
- **安装目录可能不在系统盘**：本机就有装到 `D:\` 的情况，别只扫 `C:\Program Files` 与 `%LOCALAPPDATA%\Programs`。
- **product.json 缺失时的兜底**：`~\.<x>\argv.json` 是"这是 VS Code 系分支数据目录"的特征文件，可以据此推出扩展目录；运行数据目录按名字在 `%APPDATA%` 里认领（`.trae-cn` → `Trae CN`）。

## 二、本机实测表（2026-10-06，随安装变化，用 `scan_ides.py` 重新生成）

| 分支 | dataFolderName | 扩展目录 | 市场 | 备注 |
|---|---|---|---|---|
| VS Code | `.vscode` | `C:\Users\29580\.vscode\extensions` | `marketplace.visualstudio.com` | 扩展最多；安装目录 `D:\...\Programs\Microsoft VS Code` |
| Cursor | `.cursor` | `C:\Users\29580\.cursor\extensions` | `marketplace.cursorapi.com` | 自带 `extensions.json.bak` 备份习惯 |
| Antigravity IDE | `.antigravity-ide` | `C:\Users\29580\.antigravity-ide\extensions` | `open-vsx.org` | 装在 `D:\...\Programs\Antigravity IDE`；CLI `antigravity-ide.cmd` |
| Kiro | `.kiro` | `C:\Users\29580\.kiro\extensions` | `open-vsx.org` | |
| Trae | `.trae` | `C:\Users\29580\.trae\extensions` | 自建 | 未找到安装目录，仅数据目录 |
| Trae CN | `.trae-cn` | `C:\Users\29580\.trae-cn\extensions` | 自建 | 运行数据是 `%APPDATA%\Trae CN` |
| Qoder | `.qoder` | `C:\Users\29580\.qoder\extensions` | 自建 | 未找到安装目录 |
| WorkBuddy | `.workbuddy` | `C:\Users\29580\.workbuddy\extensions` | 自建 | 未找到安装目录 |

同机实测的市场差异造成的现实后果（`edwinsulaiman.jetbrains-rider-dark-theme` 这个主题）：

- Open VSX 上**查不到**（`https://open-vsx.org/api/edwinsulaiman/jetbrains-rider-dark-theme` → 404，只有 `Anan.jetbrains-darcula-theme` 之类近似品）；
- 于是它在 VS Code 装完后，被手工搬到了 Cursor / Qoder / Trae，最后是 Antigravity IDE —— 一条典型的"VS Code → 各分支"搬运链。
