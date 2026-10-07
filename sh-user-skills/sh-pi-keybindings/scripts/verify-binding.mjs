#!/usr/bin/env node
/**
 * verify-binding.mjs — 离线验证 pi 快捷键配置与按键字节序列的匹配关系
 *
 * 用法:
 *   node verify-binding.mjs list [actionId]
 *   node verify-binding.mjs test <keyId> <dataSpec>
 *
 * dataSpec 支持:
 *   kitty:<codepoint>:<modifier>    Kitty CSI-u        例: kitty:118:4     => ESC[118;4u
 *   modother:<modifier>:<codepoint> xterm modifyOtherKeys 例: modother:4:118 => ESC[27;4;118~
 *   alt:<char>                      传统 alt 编码      例: alt:v           => ESC v
 *   ctrl:<char>                     传统 ctrl 编码     例: ctrl:v          => 0x16
 *   hex:<hex bytes>                 原始字节           例: hex:1b56        => ESC V
 *   json:"<escaped>"                JSON 转义字符串    例: json:"\u001b[118;4u"
 *
 * 环境变量 PI_ROOT: 指向 @earendil-works/pi-coding-agent 安装目录（默认用 npm root -g 探测）
 */
import { execSync } from "node:child_process";
import { existsSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const PKG = "@earendil-works/pi-coding-agent";

function findPiRoot() {
  const candidates = [];
  if (process.env.PI_ROOT) candidates.push(process.env.PI_ROOT);
  try {
    const npmRoot = execSync("npm root -g", { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
    if (npmRoot) candidates.push(join(npmRoot, PKG));
  } catch {
    // npm 不在 PATH 时忽略，继续尝试其它路径
  }
  const home = process.env.USERPROFILE || process.env.HOME || "";
  if (home) {
    candidates.push(join(home, "AppData", "Roaming", "npm", "node_modules", PKG));
    const nvmDir = join(home, "AppData", "Local", "nvm");
    if (existsSync(nvmDir)) {
      for (const entry of readdirSync(nvmDir)) {
        if (/^v\d/.test(entry)) candidates.push(join(nvmDir, entry, "node_modules", PKG));
      }
    }
  }
  for (const c of candidates) {
    if (c && existsSync(join(c, "dist", "core", "keybindings.js"))) return c;
  }
  return null;
}

function usage(exitCode = 1) {
  console.log(`用法:
  node verify-binding.mjs list [actionId]
  node verify-binding.mjs test <keyId> <dataSpec>

dataSpec:
  kitty:<codepoint>:<modifier>      Kitty CSI-u           例 kitty:118:4       => ESC[118;4u
  modother:<modifier>:<codepoint>   xterm modifyOtherKeys 例 modother:4:118     => ESC[27;4;118~
  alt:<char>                        传统 alt 编码         例 alt:v             => ESC v
  ctrl:<char>                       传统 ctrl 编码        例 ctrl:v            => 0x16
  hex:<bytes>                       原始字节              例 hex:1b56          => ESC V
  json:"<escaped>"                  JSON 转义字符串       例 json:"\\u001b[118;4u"

环境变量 PI_ROOT 可指定 pi 安装目录（默认用 npm root -g 探测）。`);
  process.exit(exitCode);
}

function parseData(spec) {
  if (spec.startsWith("kitty:")) {
    const [cp, mod] = spec.slice(6).split(":").map(Number);
    if (!Number.isInteger(cp) || !Number.isInteger(mod)) throw new Error("kitty: 需要 kitty:<codepoint>:<modifier>");
    return `\x1b[${cp};${mod}u`;
  }
  if (spec.startsWith("modother:")) {
    const [mod, cp] = spec.slice(9).split(":").map(Number);
    if (!Number.isInteger(cp) || !Number.isInteger(mod)) throw new Error("modother: 需要 modother:<modifier>:<codepoint>");
    return `\x1b[27;${mod};${cp}~`;
  }
  if (spec.startsWith("alt:")) {
    const ch = spec.slice(4);
    if (ch.length !== 1) throw new Error("alt: 需要单个字符，如 alt:v / alt:V");
    return `\x1b${ch}`;
  }
  if (spec.startsWith("ctrl:")) {
    const ch = spec.slice(5).toLowerCase();
    const code = ch.charCodeAt(0);
    const ok = (code >= 97 && code <= 122) || ["[", "\\", "]", "_"].includes(ch);
    if (!ok) throw new Error("ctrl: 只支持字母与 [ \\ ] _");
    return String.fromCharCode(code & 0x1f);
  }
  if (spec.startsWith("hex:")) {
    const hex = spec.slice(4);
    if (!/^[0-9a-fA-F]+$/.test(hex) || hex.length % 2 !== 0) throw new Error("hex: 需要偶数字节，如 hex:1b56");
    return Buffer.from(hex, "hex").toString("latin1");
  }
  if (spec.startsWith("json:")) {
    return JSON.parse(spec.slice(5));
  }
  throw new Error(`未知 dataSpec: ${spec}（见 usage）`);
}

const [cmd, ...rest] = process.argv.slice(2);

const root = findPiRoot();
if (!root) {
  console.error("找不到 pi 安装目录。请用 PI_ROOT 指定，例如：");
  console.error('  PI_ROOT="$(npm root -g)/@earendil-works/pi-coding-agent" node verify-binding.mjs list');
  process.exit(2);
}

const keybindingsUrl = pathToFileURL(join(root, "dist", "core", "keybindings.js")).href;
const configUrl = pathToFileURL(join(root, "dist", "config.js")).href;
const { KeybindingsManager, KEYBINDINGS } = await import(keybindingsUrl);
const { getAgentDir } = await import(configUrl);

let matchesKey = null;
for (const base of [join(root, "node_modules"), join(root, "..", "..")]) {
  const tuiKeys = join(base, "@earendil-works", "pi-tui", "dist", "keys.js");
  if (existsSync(tuiKeys)) {
    ({ matchesKey } = await import(pathToFileURL(tuiKeys).href));
    break;
  }
}

let kb;
try {
  kb = KeybindingsManager.create(getAgentDir());
} catch (error) {
  console.error(`读取 keybindings.json 失败：${error.message}`);
  process.exit(2);
}

const agentDir = getAgentDir();
console.log(`pi root : ${root}`);
console.log(`agent   : ${agentDir}`);

function label(keys) {
  if (keys === undefined) return "(未定义)";
  const list = Array.isArray(keys) ? keys : [keys];
  return list.length ? list.join(", ") : "(已禁用)";
}

if (cmd === "list") {
  const filter = rest[0];
  const all = kb.getResolvedBindings();
  const actions = filter ? [filter] : Object.keys(all);
  for (const action of actions) {
    const keys = all[action];
    if (keys === undefined) {
      console.log(`${action} = (未知动作 id，不在 pi 的 KEYBINDINGS 表中)`);
      continue;
    }
    const def = KEYBINDINGS[action]?.defaultKeys;
    const changed = JSON.stringify(keys) !== JSON.stringify(def);
    const defaultText = def === undefined || (Array.isArray(def) && def.length === 0) ? "" : `   [默认: ${label(def)}]`;
    console.log(`${action} = ${label(keys)}${changed ? defaultText : ""}`);
  }
} else if (cmd === "test") {
  const [keyId, spec] = rest;
  if (!keyId || !spec) usage();
  let data;
  try {
    data = parseData(spec);
  } catch (error) {
    console.error(error.message);
    process.exit(2);
  }
  const all = kb.getResolvedBindings();
  const direct = matchesKey
    ? matchesKey(data, keyId)
    : Object.hasOwn(all, keyId) && kb.matches(data, keyId);
  const reverse = [];
  for (const [action, keys] of Object.entries(all)) {
    if (keys !== undefined && kb.matches(data, action)) reverse.push(`${action} (${label(keys)})`);
  }
  const hex = Buffer.from(data, "latin1").toString("hex");
  console.log(`data    : ${JSON.stringify(data)}  [hex: ${hex}]`);
  console.log(`key     : ${keyId}`);
  console.log(`matches : ${direct}   (按 pi 按键语法判断该键 id 能否匹配此序列)`);
  console.log("reverse : 当前生效配置里会被此序列触发的动作");
  if (reverse.length === 0) console.log("  (无 —— 这个字节序列会被 pi 忽略，按下不会有任何动作)");
  else for (const r of reverse) console.log(`  - ${r}`);
} else {
  usage(cmd === undefined ? 0 : 1);
}
