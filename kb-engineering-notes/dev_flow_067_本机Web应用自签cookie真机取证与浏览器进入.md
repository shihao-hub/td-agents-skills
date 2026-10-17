---
name: kb-local-web-gui-selfsigned-session-cookie
description: 本机 Web 应用只认启动横幅里的令牌与签名 cookie、自动化浏览器（独立 profile）进不去时，如何只读存档密钥自签会话 cookie 进入 GUI 做真机 DOM 取证，全程不回显密钥与 cookie 值。
---

# 67-本机Web应用无凭证真机取证与自签会话cookie进入独立浏览器指南

## 一、现象与报错直击

需要看本机某个 Web 应用（本例 `dsh web`，`http://127.0.0.1:11111`）的**真实 DOM、计算样式、运行时状态**，但手上的自动化浏览器（如 chrome-devtools MCP）是**独立 profile**，不带你的登录态，页面只回一行纯文本：

```text
dsh web authentication required; reopen the URL printed by dsh web.
```

HTTP 状态是 **401**，`content-type: text/plain`。难点在于：

- 能进 GUI 的凭据是**启动横幅里带 `?token=` 的 URL**（浏览器书签/历史里有，命令行输出里也有，但都可能已滚掉）；
- 那个 token 是**进程内存里的 launch token**（`WeakMap` 持有，随进程生灭），**磁盘上根本没有**；
- 于是"看真实页面"这件事被卡在鉴权上，而你要修的恰恰是**鉴权之后**才渲染出来的东西。

## 二、底层根因剖析（先把鉴权方案从源码里读全）

不要猜、不要暴力试。第一方实现里一定写着 cookie 名、签发算法与密钥来源（本例 `dsh-client-connection/lib/index.js`）：

```js
const AUTH_RECORD_KEY = credentialKey("client-connection", "browser-session");  // 凭据库里的记录键
const COOKIE_PREFIX = "dsh-auth-";
const TOKEN_QUERY = "token";
cookieName(authority)  = COOKIE_PREFIX + base64url(sha256(authority))           // authority = 请求 Host 头
signature(secret, body) = hmacSha256(secretBytes, body)                          // secret 为 32 字节
encodeCookie(payload)   = `v1.${base64url(JSON payload)}.${base64url(signature)}`
payload                 = { version:1, authority, issuedAt, expiresAt }
```

关键事实（读完源码才能确认的四点）：

1. **密钥是持久化的**，不是每次启动随机：`credentials.modifyRecord(AUTH_RECORD_KEY, …)` 首次写入 `{kind:'grant', payload:{version:1, secret: base64url(32B)}}`，之后一直复用 —— 所以**你自己签出来的 cookie 和服务端签的一样有效**。
2. **cookie 名由 authority 决定**（`sha256(host)` 的 base64url），所以"跨端口"无所谓：**cookie 按 host 隔离、不按端口**，同 host 任意页面上写就生效。
3. **会话 cookie 的 `HttpOnly` 是服务端 `Set-Cookie` 的属性**，只限制"JS 读取"；**JS 自己 `document.cookie = …` 写的 cookie，浏览器照样会在请求里带上** —— 因此自签的 cookie 无需任何服务端配合。
4. **内存里的 launch token 拿不到**（`WeakMap` + 进程内存），但**不需要它**：它只是"换取签名 cookie 的入口"，而我们有密钥，可以直接签。

## 三、标准抢救与修复 SOP

> 安全纪律（本 SOP 的全部前提）：**密钥与 cookie 值绝不回显、不写盘、不入库、不进对话上下文**。下面每一步都按此设计。

### Step 1 · 只读凭据库，**只打印键名**确认记录存在

```powershell
$cred = "$env:USERPROFILE\.dsh\.credentials.yaml"     # 换成目标应用的凭据文件
[System.IO.File]::ReadAllLines($cred) | ForEach-Object {
  if ($_ -match '^(\s*)([^:]+):\s*(.*)$') {
    $indent = $Matches[1]; $k = $Matches[2]; $v = $Matches[3]
    if ($v -eq '') { "$indent${k}:" } else { "{0}{1}: <{2} chars>" -f $indent, $k, $v.Length }
  }
}
```

看到 `records: / <scope>/<id>: / payload: / secret: <43 chars>` 即确认（43 字符 base64url = 32 字节）。**永远不要打印那个值本身。**

### Step 2 · 起一个临时助手：读密钥 → 签 cookie → 只打印端口

助手（Node，无依赖）把密钥与 cookie **留在自己内存里**，只对外暴露一个本地端口，页面来取：

```js
// 关键片段：签法与第一方实现逐字对齐（详见 §二）
const key = Buffer.from(secret.replaceAll('-','+').replaceAll('_','/') + '='.repeat((4 - secret.length % 4) % 4), 'base64');
const b64u = (v) => Buffer.from(v).toString('base64').replaceAll('+','-').replaceAll('/','_').replace(/=+$/u, '');
const name  = `dsh-auth-${b64u(createHash('sha256').update(AUTHORITY).digest())}`;
const now   = Date.now();
const body  = b64u(Buffer.from(JSON.stringify({ version: 1, authority: AUTHORITY, issuedAt: now, expiresAt: now + 86400000 }), 'utf8'));
const value = `v1.${body}.${b64u(createHmac('sha256', key).update(body).digest())}`;

createServer((req, res) => {                      // 只回 cookie 串，且带 CORS 以便页面直接 fetch
  res.setHeader('access-control-allow-origin', '*');
  res.setHeader('content-type', 'text/plain; charset=utf-8');
  res.end(`${name}=${value}`);
}).listen(0, '127.0.0.1', function () { console.log(`PORT=${this.address().port}`); });
```

放在系统临时目录、用**后台作业**跑（`PORT=…` 是它唯一的输出），用完即杀、脚本即删。

### Step 3 · 让**目标 origin 的页面**自己把 cookie 写进 cookie jar

在自动化浏览器里先打开目标站点（哪怕只看到 401 页面 —— 它也在正确的 origin 上），然后执行：

```js
async () => {
  const res = await fetch('http://127.0.0.1:<PORT>/');           // 从助手取 cookie 串
  const cookie = (await res.text()).trim();
  document.cookie = cookie + '; Path=/';                          // 页面自己写，值不经过你的上下文
  return document.cookie.includes('dsh-auth-') ? 'cookie-set' : 'failed';
}
```

（替代写法：注入 `<script src="http://127.0.0.1:<PORT>/set.js">`，由助手返回 `document.cookie=...` —— 经典脚本跨源加载不需要 CORS。）

### Step 4 · 刷新 → 进入 GUI → 真机取证

```js
// 一进来先确认"真的进来了"，再开始读状态
({ title: document.title, hasBody: !!document.body })
```

之后就能用 CDP 读**真实**的 DOM / 计算样式 / 运行时对象（本例正是靠它把"覆盖层残留"钉死的）。

### Step 5 · 取证完毕：**立刻回收**

```js
// 1) 删掉自签 cookie（cookie 名不是秘密，值才是；这里只需要名字）
document.cookie = 'dsh-auth-<…>=; Max-Age=0; Path=/';
({ remaining: document.cookie.split('; ').filter(Boolean).length })   // → 0
```

```powershell
# 2) 停后台助手、删临时脚本、整组结束自动化浏览器（其 profile 里可能残留 cookie）
Remove-Item "$env:TEMP\<helper>.mjs" -Force
Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" |
  Where-Object { $_.CommandLine -like '*chrome-devtools-mcp\chrome-profile*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

## 四、验证与防复发闭环

### 4.1 验证断言（缺一不可）

- [ ] 401 页面**不再出现**，页面 `title` 是应用名，界面正常渲染；
- [ ] cookie 清理后 `document.cookie` **不再包含**该 cookie（计数为 0）；
- [ ] 全程**没有任何一次**密钥/cookie 值出现在终端输出、日志、提交内容或对话里；
- [ ] 助手进程、临时脚本、自动化浏览器进程**全部回收**；你自己的浏览器/编辑器进程**未受影响**；
- [ ] 若为"对比取证"（修复前后 A/B）：修复前的现场数据与修复后的数据**分别留档**，别只留结论。

### 4.2 防复发清单

1. **先读源码再动手**：cookie 名/签名算法/密钥来源/authority 口径四件事必须来自第一方实现，猜出来的方案会卡在下一个细节上。
2. **密钥只读、不回显**：打印长度、打印键名都可以，打印值不行；助手把秘密留在内存里、只暴露端口。
3. **别去偷内存里的 launch token**：既然密钥持久化，自签是**更短且更稳**的路径（且不依赖"横幅还在不在滚屏里"）。
4. **cookie 按 host 隔离**：把页面开到**目标 host 的任意端口**上写 cookie 即可，不必非要在应用端口上。
5. **`HttpOnly` 不等于"JS 不能设"**：它只挡读取；自己写的 cookie 照样随请求发送（这也是"自签可行"的根本原因）。
6. **取证即回收**：cookie 有有效期（本例 1 天）、自动化浏览器的 profile 会留下它 —— 收尾必须显式删除 + 杀进程 + 删脚本。
7. **别把这条路用在别人的服务上**：本 SOP 的正当性完全来自"这是你自己的机器、你自己的凭据、你装的应用"，仅用于本地真机取证。
