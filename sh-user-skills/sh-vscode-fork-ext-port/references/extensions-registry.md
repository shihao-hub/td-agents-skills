# 扩展注册表：`extensions.json` 与 `.obsolete`

## 一、`extensions.json` 是什么

扩展目录根下的 `extensions.json` 是**已装扩展的注册表**（数组，一条一个扩展）。IDE 启动时按它 + 磁盘目录做双向对齐：

- 条目在、目录在 → 正常加载；
- **条目在、目录不在** → 加载失败（"扩展不见了"）；
- **目录在、条目不在** → 不加载（手工复制目录却没写注册表的典型症状）。

所以"手工搬扩展"必须两件套齐全。文件损坏（非法 JSON）时 IDE 会重建，但期间已装扩展可能全丢——写入前留 `.bak` 是划算的。

## 二、条目结构（按来源不同，字段多少不同）

```jsonc
{
  "identifier": { "id": "publisher.name", "uuid": "…（市场分配，可省）" },
  "version": "1.0.13",
  "location": { "$mid": 1, "path": "/c:/Users/29580/.cursor/extensions/publisher.name-1.0.13", "scheme": "file" },
  "relativeLocation": "publisher.name-1.0.13",
  "metadata": {
    "isApplicationScoped": false,
    "installedTimestamp": 1791242757881,
    "source": "vsix",
    "targetPlatform": "undefined",
    "updated": false,
    "private": false,
    "isPreReleaseVersion": false,
    "hasPreReleaseVersion": false
  }
}
```

三种来源的实际差异（本机实测）：

| 来源 | `source` | `targetPlatform` | 额外字段 | 目录名 |
|---|---|---|---|---|
| 市场安装 | `gallery` | `universal` / `win32-x64` / … | `uuid`、`publisherId`、`publisherDisplayName`、`pinned`、`updated` | `publisher.name-<ver>-<platform>` |
| VSIX 安装 | `vsix` | `undefined` | 无 | `publisher.name-<ver>` |
| 手工搬运 | 照抄源条目或写 `vsix` | 同上 | 无 | 跟随复制过来的目录名 |

硬要求（三条，缺哪条都会"装了不生效"）：

1. **`version` 必须与目录/`package.json` 一致**——不一致时扫描器视作另一个扩展（旧版本缺失、新版本未注册）；
2. **`relativeLocation` 必须等于磁盘上的目录名**，目录名要能解析成 `<publisher>.<name>-<version>[-<platform>]`；
3. **`location.path` 用 VS Code 的 URI 形式**：`/c:/Users/...`（盘符小写、正斜杠）。带全 `fsPath`/`external` 的完整形式也认，最小三键形式（`$mid`/`path`/`scheme`）同样认。

关于 `uuid`：它是市场分配的身份，手工搬运**可以不带**（Antigravity IDE 实测不带照样加载）；从别的分支连 `uuid` 一起照抄也照常工作（Qoder/Trae 实测如此）。不必为它纠结。

## 三、`.obsolete` 是什么

扩展目录根的 `.obsolete` 是 `{"<目录名>": true}` 的 JSON 对象，**"已卸载、待删除"名单**：

- 卸载扩展 = 从 `extensions.json` 摘条目 + 目录名写进 `.obsolete`；
- IDE 下次启动时把这些目录从磁盘删掉；
- 手工搬来的扩展**绝不能**出现在 `.obsolete` 里（否则重启就被删）；反过来，想彻底清掉一个扩展，光删目录不够，还要摘注册表条目。

## 四、症状对照表（排障用）

| 现象 | 查什么 |
|---|---|
| 装完看不到、命令面板没有 | 目录在不在？注册表有没有？`version`/`relativeLocation` 对不对？ |
| 提示"扩展不可用 / 需要重新安装" | 目录被删了或改名了（注册表还在） |
| 重载后扩展消失 | 被写进 `.obsolete` 了；或 IDE 在跑时改注册表被它内部状态覆盖 |
| 主题/语言包"看不到" | 主题是扩展提供的，扩展没加载 → 主题列表里就没有它 |
| 装了但只有某个 profile 看不见 | 该 profile 的注册表在 `<userData>\User\profiles\<名>\extensions.json` |
