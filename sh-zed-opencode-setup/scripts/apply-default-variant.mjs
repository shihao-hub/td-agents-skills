// apply-default-variant.mjs — 任务 B3：给目标 provider 的有变体模型批量加 "default" 变体（最高档载荷）
//
// 机制（opencode 1.18.32 源码实证，详见 references/opencode-internals.md §11）：
//   - acp/config-option.ts: DEFAULT_VARIANT_VALUE="default"；模型 variants 含 default 键时
//     selectVariant() 一律返回 "default"，effort 下拉选项永远含 Default，模型列表过滤 default。
//   - acp/service.ts: newSession/切模型都走 selectVariant → 跨模型切捔回 Default，同模型保持手选。
//   - session/llm/request.ts: variant 载荷在 mergeDeep 链最后（优先级最高）→ default 载荷生效；
//     options 双写同一份载荷兜底（variant key 查不到时不报错、落回 options）。
//
// 载荷必须从 /config/providers 实测复制（键名不统一：reasoningEffort / effort /
// reasoningSummary+include / thinking），本脚本自动复制，不手写。
//
// 用法:
//   node apply-default-variant.mjs <opencode.exe>            # dry-run，打印计划
//   node apply-default-variant.mjs <opencode.exe> --apply    # 写入 opencode.json（自动备份，幂等）
//   node apply-default-variant.mjs <opencode.exe> --verify   # 复查 /config/providers 里 default 已生效
//
// 注意:
//   - TARGETS 按需增删 provider id；新模型/新 provider 重跑 --apply 即可（幂等）。
//   - cc-switch 管理的 provider（liveConfigManaged: true）还要同步 settings_config，
//     否则切换时被写回旧值（见任务 C / sh-cc-switch-db）。
//   - Zed 侧 agent_servers.opencode.default_config_options.effort 写 "default"（哨兵值），
//     不要写具体档位（无该档的模型会被 opencode 拒 InvalidEffortError）。
//   - opencode 升级后重验点：config-option.ts 的 DEFAULT_VARIANT_VALUE/selectVariant、
//     service.ts 的 hasVariant/selectModelVariant、session/llm/request.ts 的 variant 合并链。
import { spawn, spawnSync } from "node:child_process";
import { setTimeout as sleep } from "node:timers/promises";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const exe = process.argv[2];
const APPLY = process.argv.includes("--apply");
const VERIFY = process.argv.includes("--verify");
const CONFIG = path.join(os.homedir(), ".config", "opencode", "opencode.json");
// 目标 provider：只处理 /config/providers 里实际有变体的模型（无变体模型不动）
const TARGETS = ["opencode-go", "zhipuai-coding-plan", "deepseek"];
// 档位从低到高；"none" 是关闭思考不算档位，永不选为 default
const EFFORT_ORDER = ["none", "minimal", "low", "medium", "high", "xhigh", "max"];

function pickTop(keys) {
  const effort = keys.filter((k) => EFFORT_ORDER.includes(k) && k !== "none");
  if (effort.length) {
    let best = effort[0];
    for (const k of effort) if (EFFORT_ORDER.indexOf(k) > EFFORT_ORDER.indexOf(best)) best = k;
    return best;
  }
  // 开关型（无档位概念）：minimax-m3 的 [none,thinking] 选 thinking
  if (keys.includes("thinking")) return "thinking";
  if (keys.includes("thinking_mode")) return "thinking_mode";
  return keys.filter((k) => k !== "none")[0] ?? keys[0];
}

const port = 40000 + Math.floor(Math.random() * 2000);
const child = spawn(exe, ["serve", "--port", String(port)], { stdio: "ignore" });
const kill = () => {
  if (process.platform === "win32") spawnSync("taskkill", ["/PID", String(child.pid), "/T", "/F"]);
  else child.kill("SIGKILL");
};
process.on("exit", kill);

let body = null;
for (let i = 0; i < 60; i++) {
  await sleep(1000);
  try {
    const res = await fetch(`http://127.0.0.1:${port}/config/providers`);
    if (res.ok) { body = await res.json(); break; }
  } catch { /* not up yet */ }
}
if (!body) { console.error("FAIL: opencode serve 60 秒内未就绪"); process.exit(1); }
kill();

const config = JSON.parse(fs.readFileSync(CONFIG, "utf8"));
config.provider ??= {};

const planned = [];
for (const prov of body.providers ?? []) {
  if (!TARGETS.includes(prov.id)) continue;
  for (const [mid, model] of Object.entries(prov.models ?? {})) {
    const keys = model.variants ? Object.keys(model.variants) : [];
    if (!keys.length) continue;
    const top = pickTop(keys);
    const payload = model.variants[top] ?? {};
    planned.push({ provider: prov.id, model: mid, top, keys, payload });
  }
}

console.log(`目标模型 ${planned.length} 个：`);
for (const p of planned) {
  console.log(`  ${p.provider}/${p.model}  [${p.keys.join(",")}]  ->  default=${p.top}  payload=${JSON.stringify(p.payload)}`);
}

if (VERIFY) {
  let bad = 0;
  for (const p of planned) {
    const m = config.provider?.[p.provider]?.models?.[p.model];
    const ok = m?.variants?.default && JSON.stringify(m.variants.default) === JSON.stringify(p.payload);
    if (!ok) { console.log(`  MISSING ${p.provider}/${p.model}: variants.default 未写入或载荷不符`); bad++; }
  }
  console.log(bad === 0 ? "\nverify: 全部已写入" : `\nverify: ${bad} 项缺失`);
  process.exit(bad === 0 ? 0 : 1);
}

if (!APPLY) {
  console.log("\n(dry-run，未写入；加 --apply 写入)");
  process.exit(0);
}

const ts = new Date().toISOString().replace(/[-:T]/g, "").slice(0, 14);
const bak = `${CONFIG}.bak-${ts}-default-variant`;
fs.copyFileSync(CONFIG, bak);

for (const p of planned) {
  const providerCfg = (config.provider[p.provider] ??= {});
  const models = (providerCfg.models ??= {});
  const modelCfg = (models[p.model] ??= {});
  modelCfg.options = { ...(modelCfg.options ?? {}), ...p.payload };
  modelCfg.variants = { ...(modelCfg.variants ?? {}), default: p.payload };
}

fs.writeFileSync(CONFIG, JSON.stringify(config, null, 2) + "\n");
console.log(`\n已写入 ${CONFIG}\n备份: ${bak}`);
