// verify-opencode-effort.mjs — 验证 opencode 的思考档位配置（任务 B 必做步骤）
//
// 用法: node verify-opencode-effort.mjs <opencode.exe路径> [端口，默认随机]
//
// 原理: 起一个临时 `opencode serve`，查 /config/providers（ACP/Zed 实际读取的端点，
// 不是 /api/model——两者数据不同），断言：
//   1. 每个模型的 variants 为空（否则 Zed 会出现 effort 下拉框且默认落在第一档）
//   2. 配置了 effort/reasoningEffort 的模型，值必须是 max
// 任何 FAIL 都退出码 1。opencode 升级后此脚本是判断配置是否仍生效的第一道关。

import { spawn, spawnSync } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";

const [exe, portArg] = process.argv.slice(2);
if (!exe) {
  console.error("用法: node verify-opencode-effort.mjs <opencode.exe路径> [端口] [--only 供应商ID子串]");
  process.exit(2);
}
const onlyIdx = process.argv.indexOf("--only");
const ONLY = onlyIdx >= 0 ? process.argv[onlyIdx + 1] : null;
const port = Number(portArg) || 40000 + Math.floor(Math.random() * 2000);
const base = `http://127.0.0.1:${port}`;

const child = spawn(exe, ["serve", "--port", String(port)], { stdio: "ignore" });
const kill = () => {
  if (process.platform === "win32") spawnSync("taskkill", ["/PID", String(child.pid), "/T", "/F"]);
  else child.kill("SIGKILL");
};
process.on("exit", kill);

// 轮询直到 server 就绪
let body = null;
for (let i = 0; i < 30; i++) {
  await sleep(1000);
  try {
    const res = await fetch(`${base}/config/providers`);
    if (res.ok) { body = await res.json(); break; }
  } catch { /* not up yet */ }
}
if (!body) {
  console.error(`FAIL: opencode serve 在 ${base} 上 30 秒内未就绪`);
  process.exit(1);
}

let fails = 0;
for (const prov of body.providers ?? []) {
  if (ONLY && !prov.id.includes(ONLY)) continue;
  for (const [mid, m] of Object.entries(prov.models ?? {})) {
    const label = `${prov.id}/${mid}`;
    const variants = m.variants && Object.keys(m.variants).length > 0 ? Object.keys(m.variants) : null;
    const effortKey = m.options && ("effort" in m.options || "reasoningEffort" in m.options)
      ? ("effort" in m.options ? "effort" : "reasoningEffort")
      : null;
    const effortVal = effortKey ? m.options[effortKey] : null;

    if (variants) { console.log(`FAIL ${label}: variants 非空 [${variants.join(",")}] → Zed 会出现下拉框`); fails++; }
    else if (!effortKey) { console.log(`WARN ${label}: 未配置 effort/reasoningEffort（若该模型需要 max 则缺失）`); }
    else if (effortVal !== "max") { console.log(`FAIL ${label}: ${effortKey}=${effortVal}，应为 max`); fails++; }
    else console.log(`PASS ${label}: 无变体，${effortKey}=max`);
  }
}
console.log(fails === 0 ? "\n结论: 全部通过" : `\n结论: ${fails} 项失败`);
process.exit(fails === 0 ? 0 : 1);
