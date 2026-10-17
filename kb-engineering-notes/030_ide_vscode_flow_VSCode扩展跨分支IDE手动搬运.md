---
name: kb-vscode-ext-port
description: VS Code 体系扩展跨分支 IDE（Cursor/Antigravity/Trae）手工搬运、解压修补与本地注册生效指南。
---

# VSCode扩展跨分支IDE手动搬运与注册生效指南

# VS Code 系 IDE 扩展跨分支搬运

VS Code 的每个分支（VS Code、Cursor、Antigravity IDE、Trae、Kiro、Qoder…）共用同一套扩展机制，但**各有各的扩展目录、各有各的市场**。目标市场里没有的扩展（VS Code Marketplace 独占的、自制的、下架的主题/语言包等）靠"装"是装不来的，只能手工搬。

手工搬的关键认知：**扩展目录 + 注册表条目，两件套齐了才生效**。只复制目录不写注册表 = 装了但看不见；只写注册表没目录 = 报"扩展不可用"。下面的流程按这个事实组织。

## 第 0 步：先把两端坐标查出来，不要猜路径

```bash
uv run scripts/scan_ides.py                          # 本机所有分支：扩展目录/运行数据/市场/CLI
uv run scripts/scan_ides.py --has publisher.name     # 哪个分支已经装了它
uv run scripts/scan_ides.py --json                   # 给后续脚本或自己读
```

坐标一律从该分支自己的 `resources/app/product.json` 推导（`dataFolderName` → 扩展目录，`nameShort` → 运行数据目录，`applicationName` → CLI，`extensionsGallery` → 市场）。推导规则与**本机实测身份表**见 `references/ide-directory-map.md`——两个目录不是一回事，别把 `~\.cursor` 和 `%APPDATA%\Cursor` 混用。

## 第 1 步：能直接装就别手工搬

先看目标分支的市场是什么：

- `open-vsx.org`（Antigravity IDE、Kiro 等）→ 先查有没有：
  ```bash
  curl -s https://open-vsx.org/api/<publisher>/<name>     # 404 = 没有，别白折腾
  ```
- `marketplace.visualstudio.com` / `marketplace.cursorapi.com` / 自建（Trae、Qoder）→ 同理，先在 IDE 的扩展面板里搜一次。

有就直接用 CLI 装，注册表由 IDE 自己写，比手工搬干净：

```bash
"<安装目录>\bin\<applicationName>.cmd" --install-extension <publisher>.<name>
```

没有才进第 2 步。这一步别省：手工搬的扩展不会自动更新，能装就别搬。

## 第 2 步：搬运

```bash
uv run scripts/port_extension.py --from cursor --to antigravity-ide --id edwinsulaiman.jetbrains-rider-dark-theme
uv run scripts/port_extension.py --from cursor --to antigravity-ide --id <id> --dry-run    # 先看它要做什么
uv run scripts/port_extension.py --to antigravity-ide --list                              # 目标已装扩展 vs 注册表对照
```

脚本做三件事：在源分支扩展目录里按 `publisher.name` 找 `<id>-<version>[-<platform>]` → `copytree` 到目标扩展目录 → 在目标注册表里替换/追加条目（首次改动留 `extensions.json.bak`）。分支名可以用 `dataFolderName`、`nameShort`、安装目录名或路径。

一次只搬一个扩展；多个扩展或多个目标就循环调用（幂等，重复跑只会刷新成当前源版本）。

脚本不可用时手工做，三步：

1. **复制目录**（保留目录名，别改名——目录名要能被解析成 `<publisher>.<name>-<version>[-<platform>]`）：
   ```bash
   cp -a "<源扩展目录>/<id>-<版本>" "<目标扩展目录>/"
   ```
2. **写注册表**：读 `<目标扩展目录>/extensions.json`（先备份），摘掉同 id 的旧条目，追加新条目。字段与三种来源的差异见 `references/extensions-registry.md`。
3. 校验 `version` 与目录/`package.json` 一致、`relativeLocation` 等于目录名——这两条错一条就等于没装。

## 第 3 步：让它生效

- **目标 IDE 没在运行**：直接启动即可，启动时扫扩展目录。
- **目标 IDE 在运行**：执行「Developer: Reload Window」（命令面板），或重启。运行中改注册表会被它内部重扫，但热加载不保证。
- **主题类扩展**还要在目标分支的用户设置里点名，否则装了也不会用：
  ```bash
  uv run scripts/port_extension.py --from <源> --to <目标> --id <id> --apply-theme
  ```
  等价于在 `%APPDATA%\<nameShort>\User\settings.json` 里写 `"workbench.colorTheme": "<主题 label>"`（label 取 `package.json` 的 `contributes.themes[0].label`）。

## 第 4 步：验证与回滚

三级证据，从弱到强：

1. **CLI 列表**：`<安装目录>\bin\<applicationName>.cmd --list-extensions --show-versions` 能列出该 id；
2. **注册表回读**：条目 id/version/`relativeLocation` 与磁盘目录一致（`--list` 会标出不一致）；
3. **窗口侧证据**（最强）：主题类看运行数据里的 `state.vscdb` → `ItemTable.colorThemeData.settingsId` 是否变成该主题 label；扩展类看命令面板里有没有它贡献的命令。

第 3 级才代表"真的生效"，前两级只能说明"文件摆对了"。改完让用户自己确认一眼，比只报 CLI 结果靠谱。

回滚：

```bash
uv run scripts/port_extension.py --to "<目标>" --id <id> --uninstall --yes
```

## 关键事实（都是这台机器上踩过的）

- **市场差异是根因**：Antigravity IDE / Kiro 用 Open VSX，VS Code 用官方市场，Cursor / Trae / Qoder 用自建。同一个扩展在这边有、那边没有是常态，不要假设"搜不到就是没装"。
- **运行中改注册表会在 Antigravity IDE 里报一次未捕获异常**：`sharedProcess.log` 出现 `onDidChangeExtensionsFromAnotherSource → Cannot read properties of undefined (reading 'fireEvent')`，伴随 `antigravityAnalytics ... NOT registered` 告警。这是它自身处理"外部来源新增扩展"链路的 bug，**不影响扩展生效**，重启即清，不用追。
- **`.obsolete` 是待删名单**：卸载的扩展进 `.obsolete`，IDE 下次启动删目录。手工搬的目录绝不能进这个名单；`--list` 会把它标出来。
- **平台后缀（`-win32-x64`/`-darwin-arm64`）含平台二进制**，只能搬给同 OS、同架构的分支；纯主题/语言包类没有后缀，随便搬。
- **分支版本号不等于上游 VS Code 版本**（Kiro 是 1.1.14、Cursor 是 3.x，Antigravity IDE 是 1.107.0）：拿 `engines.vscode` 与分支版本硬比会得出假的"不兼容"，只在分支版本明显沿用上游序列时才值得比。
- **具名 profile 有独立注册表**：在 `<userData>\User\profiles\<名>\extensions.json`。目标分支有 profile 时，改默认那份等于没改。
- **别在扩展目录里留备份目录**（`.bak`、`-old` 之类）：扫描器会把它们当扩展解析，轻则日志告警重则列表脏。备份放在扩展目录外。
- **扩展目录里有历史包袱是正常的**：`--list` 里"磁盘有、注册表没有"往往就是别人手工搬过或刚卸载过的痕迹，先判断是 `.obsolete` 待删还是真漏注册，再决定动不动手。
- 搬运是**复制而非链接**：源分支后续升级该扩展，目标分支不会跟着变，需要重跑一次搬运。

## 脚本与参考

| 路径 | 用途 |
|---|---|
| `scripts/scan_ides.py` | 扫描本机所有分支的身份与目录（只读）；`--has` 查某扩展装在哪些分支 |
| `scripts/port_extension.py` | 搬运/刷新/卸载一个扩展；`--dry-run` 预演、`--apply-theme` 顺带应用主题、`--list` 对照排障 |
| `references/ide-directory-map.md` | 坐标推导规则 + 本机实测身份表 |
| `references/extensions-registry.md` | 注册表条目字段、三种来源差异、`.obsolete` 语义、症状对照表 |
