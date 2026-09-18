# gh 授权排障、OAuth 设备流自驱动、GitHub Lists API

## 1. gh auth 授权"不生效"排障

用户说"我登录了/授权了"，但 `gh auth status` 依旧未登录或 scope 不变。排查顺序：

1. **凭据是全局的**：gh 登录凭据存于 `%AppData%\GitHub CLI\hosts.yml`（或 keyring），所有终端共享。任何终端看不到 = 流程没走完。检查：
   ```powershell
   Test-Path "$env:APPDATA\GitHub CLI\hosts.yml"
   ```
2. **常见断点**（按概率排序）：
   - 浏览器设备授权页输入 8 位码后**没点 Authorize 按钮**就关了页面
   - `gh auth login` / `gh auth refresh` 进程在令牌写回前被 Ctrl+C / 关终端打断（浏览器显示成功 ≠ 本地写入；**唯一成功标志是终端自己滚出 `✓ Authentication complete`**）
   - 用户只登录了 github.com 网页，根本没跑过 CLI 命令
   - 登录发生在别的 Windows 账户 / WSL（凭据不跨账户）
3. **scope 补授权**：`delete_repo`、`user` 等 scope 不在默认集。让用户跑 `gh auth refresh -h github.com -s <scope>`；反复失败就放弃交互流程，改用 §2 自驱动方案。

## 2. OAuth 设备流自驱动（绕过 gh 交互）

适用：只需要给某个 API 调用补一次性 token（如创建 List）。利用 gh CLI 的公开 client_id，自己发起设备流，**轮询进程由自己持有，不会像 gh 那样被中断**。

### 2.1 发起

```powershell
curl.exe -s -X POST https://github.com/login/device/code -H "Accept: application/json" `
  -d "client_id=178c6fc778ccc68e1d6a" -d "scope=user"
# 返回 device_code / user_code / verification_uri / expires_in(≈900s) / interval
```

把 `user_code` 给用户，让其打开 `https://github.com/login/device` 输入并点 Authorize。

### 2.2 轮询取令牌

```powershell
$r = curl.exe -s -X POST https://github.com/login/oauth/access_token -H "Accept: application/json" `
  -d "client_id=178c6fc778ccc68e1d6a" -d "device_code=<dc>" `
  -d "grant_type=urn:ietf:params:oauth:grant-type:device_code"
```

- 响应 `authorization_pending` → 继续等
- 响应 `slow_down` → **轮询过快被惩罚，interval 翻倍**（可被罚到 195s+）。经验：首次轮询前先 sleep，间隔取 `max(interval*2, 15~20s)`，宁慢勿快
- 响应含 `access_token` → 存临时文件，**用完即焚**（`Remove-Item`），不留明文凭据

注意：token 放在 PS 变量里拼 header 是安全的（token 是 40 位 hex，无空格）：`-H "Authorization: bearer $t"`。

## 3. GitHub Lists（GraphQL）

Lists 的 Web UI 尚在灰度（很多账号的 `github.com/stars` 侧栏没有 Lists 入口），但 **API 已全量可用**。API 创建后用户可通过公开直链访问：`https://github.com/stars/<user>/lists/<slug>`（中文 slug 需 URL 编码，浏览器地址栏直接粘中文也行）。

### 3.1 探测 schema（mutation/字段名曾变动，先 introspect 再用）

```json
{"query": "{ __schema { mutationType { fields { name } } } }"}
```

过滤 `(?i)list` 找到 `createUserList` / `updateUserList` / `updateUserListsForItem`。输入类型再 introspect 一次：`__type(name: "CreateUserListInput")` / `__type(name: "UpdateUserListsForItemInput")`。

**实战确认的字段名**（与直觉不同，别猜）：
- `createUserList` 的返回字段是 **`list`**（不是 `userList`）
- `updateUserListsForItem` 的 `itemId` = **仓库的 node_id**（`gh api repos/<o>/<r> --jq .node_id`，GraphQL 调用不需要 user scope，用 gh 现有 token 即可）
- 查询入口：`viewer { lists(first:10) { nodes { id name slug items { totalCount } } } }`（User 类型上是 `lists`）

### 3.2 创建 + 批量添加

创建：

```json
{"query": "mutation($input: CreateUserListInput!) { createUserList(input: $input) { list { id name slug isPrivate } } }",
 "variables": {"input": {"name": "<名称>", "description": "<描述>"}}}
```

批量添加：把 N 个 `updateUserListsForItem` 用别名拼进**单个 mutation** 一次发送（省请求）。但注意：

- **单请求别超 ~40 个 mutation**：实测 64 个一发的结果是一半成功一半撞限流（响应里 errors + 对应别名为 null）
- 剩余的**逐个单发 + 800ms 间隔**最稳
- 该操作幂等（listIds 是全量设置），失败重发无副作用
- 完成后用 §3.1 的查询核对 `totalCount`

### 3.3 调用方式（Windows 必读）

`gh api graphql -f query=...` 在 PS 5.1 传不进带空格的参数。两种方式：
1. `gh api graphql --input <json文件>`（gh 的 token 够权限时）
2. `curl.exe --data "@<json文件>"` + 自驱动 token（推荐，见 §2）

JSON 文件用无 BOM UTF-8 写入（见 powershell-quirks.md §5）。

## 4. 令牌与网络杂症

- **间歇性 `Bad credentials` 401**：同命令隔几秒重试就通，是网络/边缘节点抖动，不是凭据失效。判定顺序：先重试 → 再换端点验证（GET /user）→ 最后才怀疑 token 被吊销。
- **自驱动 token 可能被 gh 干掉**：它与 gh 同 client_id。若用户中途成功跑了 `gh auth refresh`，gh 换新令牌时可能撤销旧的。做 List 操作期间别让用户同时跑 refresh。
- **API 端点行为差异**：`repos/<o>/<r>` 偶发 404 时，用 `search/repositories?q=<name>` 交叉验证仓库是否存在。
