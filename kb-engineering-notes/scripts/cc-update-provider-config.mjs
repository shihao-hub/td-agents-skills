#!/usr/bin/env node
// cc-update-provider-config.mjs — 改既有供应商条目的 settings_config（任意 app 段通用）
// 默认 dry-run 打印改前/改后全文；--apply 才写库（自动备份、事务、写后回读深比较）。
// 只动 settings_config 一列，name/icon/meta 等其余列不变（要改显示名/图标请手工或扩展本脚本）。
//
// 两种改法（至少给一种，可叠加：--config 作基底，--set 在其上打补丁）：
//   1) --config <cfg.json>        整体替换 settings_config
//   2) --set <dotted.path>=<value> 定点改一个字段（可重复），无需落临时 JSON 文件。
//      value 先按 JSON 解析（数字/布尔/对象/数组），解析失败则当字符串。
//      换密钥示例（claude 段）：
//        node scripts/cc-update-provider-config.mjs --app claude --id <id> \
//          --set env.ANTHROPIC_AUTH_TOKEN=xxxxxxxx --apply
import { DatabaseSync } from 'node:sqlite';
import { copyFileSync, readFileSync } from 'node:fs';
import os from 'os';
import path from 'path';

const USAGE = 'usage: node cc-update-provider-config.mjs --app <app_type> --id <id> [--config <cfg.json>] [--set <dotted.path>=<value>]... [--db <沙箱.db>] [--apply]';

const argv = process.argv.slice(2);
const flag = (n) => { const i = argv.indexOf(n); return i >= 0 ? argv.splice(i, 2)[1] : undefined; };
const APPLY = argv.includes('--apply');
const dbPath = flag('--db') || path.join(os.homedir(), '.cc-switch', 'cc-switch.db');
const appType = flag('--app');
const id = flag('--id');
const cfgPath = flag('--config');

// --set 可重复，需单独抽取（flag() 只取首次）
const sets = [];
for (let i = 0; i < argv.length;) {
  if (argv[i] === '--set') { sets.push(argv[i + 1]); argv.splice(i, 2); } else { i++; }
}

if (!appType || !id || (!cfgPath && sets.length === 0)) { console.error(USAGE); process.exit(1); }

// 深合并：a.b.c = value
function applySet(obj, expr) {
  const eq = expr.indexOf('=');
  if (eq <= 0) { console.error(`ABORT: --set 需形如 <dotted.path>=<value>，收到：${expr}`); process.exit(1); }
  const keys = expr.slice(0, eq).split('.');
  const raw = expr.slice(eq + 1);
  let val;
  try { val = JSON.parse(raw); } catch { val = raw; }
  let cur = obj;
  for (let i = 0; i < keys.length - 1; i++) {
    if (typeof cur[keys[i]] !== 'object' || cur[keys[i]] === null) cur[keys[i]] = {};
    cur = cur[keys[i]];
  }
  cur[keys[keys.length - 1]] = val;
  return expr;
}

// 探查只读（总原则 1）：dry-run 时以 readOnly 打开，避免误锁库
const db = new DatabaseSync(dbPath, { readOnly: !APPLY });
const old = db.prepare('SELECT settings_config FROM providers WHERE app_type=? AND id=?').get(appType, id);
if (!old) { console.error(`ABORT: providers (${appType}, ${id}) 不存在`); process.exit(1); }

// 基底：--config 显式给全量，否则取库里现值再打补丁
const cfg = cfgPath
  ? JSON.parse(readFileSync(cfgPath, 'utf-8').replace(/^﻿/, ''))
  : JSON.parse(old.settings_config);
for (const expr of sets) applySet(cfg, expr);

console.log('=== 改前 settings_config ===');
console.log(old.settings_config);
console.log('=== 改后 settings_config ===');
console.log(JSON.stringify(cfg, null, 2));
if (!APPLY) { console.log('\n(dry-run only，确认后加 --apply)'); process.exit(0); }

const bak = `${dbPath}.bak-${Date.now()}`;
copyFileSync(dbPath, bak);
console.log('已备份 ->', bak);

db.exec('BEGIN');
try {
  db.prepare('UPDATE providers SET settings_config=? WHERE app_type=? AND id=?').run(JSON.stringify(cfg, null, 2), appType, id);
  db.exec('COMMIT');
} catch (e) {
  db.exec('ROLLBACK');
  console.error('更新失败，已 ROLLBACK：', e.message);
  process.exit(1);
}

const back = JSON.parse(db.prepare('SELECT settings_config FROM providers WHERE app_type=? AND id=?').get(appType, id).settings_config);
const ok = JSON.stringify(back) === JSON.stringify(cfg);
console.log('round-trip 一致:', ok);
if (!ok) process.exit(1);
console.log('OK（提醒：重启 cc-switch 后生效；若该条是 current，还需同步其投影文件如 ~/.claude/settings.json）');
