# PowerShell 5.1 兼容写法（gh / git / curl）

Windows PowerShell 5.1 与现代工具链的摩擦集中在四类问题：编码、参数传递、JSON 解析、文件写入。每一条都在实战中踩过。

## 1. 编码：中文乱码

**症状**：gh 输出的中文描述显示为 `??` 或乱码；PS 管道读到的 UTF-8 字节被按 GBK 解码。

**修法**：任何要处理 gh/git 中文输出的命令，第一行必须是：

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

这只影响"PS 如何解码子进程输出"，不影响用户系统设置，无副作用。

## 2. 参数传递：PS 5.1 的 native 参数 bug

**症状**：`gh api xxx --jq '.foo | "bar"'` 报 `accepts 1 arg(s), received 2` 或字段取出来是空。

**根因**：PS 5.1 向原生 exe 传参时，不转义参数内嵌的双引号；含空格的参数被拆成多个。`--jq` 表达式天然带空格和字符串引号，必炸。

**修法**：`--jq` 表达式里**不出现空格、不出现双引号**。用数组 + `@csv`：

```powershell
# 坏：含空格和引号，会被拆碎
gh api repos/x --jq '{a: .parent.full_name, b: .default_branch}'

# 好：无空格无引号，@csv 输出 "v1","v2","v3"
gh api repos/x --jq '[.parent.full_name,.parent.default_branch,.default_branch]|@csv'
```

同理：`gh api graphql` 的 query 参数也传不进去，**改用 `--input <file>` 把 JSON 放文件里**（见 §5）。

## 3. 字符串分割：Split('","') 陷阱

**症状**：`"a","b","c"` 用 `.Split('","')` 拆完字段错位（P1/P2 变空）。

**根因**：`String.Split(string)` 被 PS 绑定到 `Split(char[])` 重载，字符串被当字符集合，按 `"` **和** `,` 任意一个拆分。

**修法**：

```powershell
$p = $info.Replace('"','').Split(',')
```

先去掉全部双引号，再按逗号拆，结果干净可靠。

## 4. JSON 解析：ConvertFrom-Json 两宗罪

1. **大数组崩溃**：字段数多的对象数组（如 `__type` introspection 结果）报 `MissingMethodException: 没有为类型 System.String 定义无参数的构造函数`。PS 5.1 的已知 bug。
   - 修法：不解析，直接对原始文本用正则：
     ```powershell
     [regex]::Matches($raw, '"name":"([A-Za-z]+)"') | ForEach-Object { $_.Groups[1].Value }
     ```
2. **编码敏感**：管道喂进来的乱码字节解析必失败。
   - 修法：先做 §1 的 UTF-8 设置；大输出用 §6 的 cmd /c 重定向落盘。

## 5. JSON 文件写入：BOM 问题

**症状**：PS 写的 JSON 文件发给 GraphQL / HTTP 端点报莫名其妙的解析错误。

**根因**：`Set-Content -Encoding UTF8` 在 PS 5.1 写**带 BOM** 的 UTF-8；curl `--data @file` 会把 BOM 字节一起发出去，服务端 JSON 解析失败。

**修法**：无 BOM 写入：

```powershell
$body = @{query=$q} | ConvertTo-Json -Compress
[IO.File]::WriteAllText("$path\q.json", $body, (New-Object Text.UTF8Encoding($false)))
```

构造 GraphQL 请求体的标准姿势（避免手拼转义出错）：

```powershell
$q = 'mutation{updateUserListsForItem(input:{itemId:"ID",listIds:["LIST"]}){clientMutationId}}'
$body = @{query=$q} | ConvertTo-Json -Compress
[IO.File]::WriteAllText($f, $body, (New-Object Text.UTF8Encoding($false)))
curl.exe -s -X POST https://api.github.com/graphql -H "Authorization: bearer $t" -H "Content-Type: application/json" --data "@$f"
```

注意：curl 的 header 里嵌变量（`bearer $t`）没问题，因为 token 不含空格。

## 6. 大输出落盘：cmd /c 重定向

要把 gh 的大 JSON 原样存文件（快照），不要走 PS 管道（会经历一次 GBK 解码再 UTF-8 编码，中文必坏）：

```powershell
cmd /c "gh repo list --limit 1000 --json ... > %USERPROFILE%\dir\snapshot.json"
```

cmd 的重定向是原始字节流，UTF-8 原样落盘。

## 7. 循环排障套路

循环里 `2>$null` 吞掉所有错误会让整批调用静默失败（表现为全部 NOINFO/ERR）。调试顺序：

1. 先把循环体里**一条**拿出来，不带 `2>$null` 单独跑，看真实报错
2. 修好后还原循环，保留 `$LASTEXITCODE` 检查 + 失败名单收集：

```powershell
$ok = 0; $fail = @()
foreach ($n in $list) {
    gh repo delete "<user>/$n" --yes 2>$null
    if ($LASTEXITCODE -eq 0) { $ok++ } else { $fail += $n }
}
Write-Output "OK: $ok / $($list.Count)"; if ($fail.Count) { $fail }
```

## 8. 其他

- **PS 没有 `&&`**：用 `cmd1; if ($?) { cmd2 }`。
- **timeout 意识**：批量 API 循环（60+ 次调用）给 bash 工具设 300000~600000ms 超时，否则跑到一半被杀（如果循环同时在做 token 轮询这类有状态的事，被杀会导致状态丢失）。
- **gh api 间歇性 401/404**：网络抖动，重试同一命令即可；不要据此判定凭据失效而重走授权流程。
- **PS 数组单元素陷阱**：`@($r | Where-Object ...)` 强转数组再取 `.Count`，否则单元素时 `.Count` 可能为空。
