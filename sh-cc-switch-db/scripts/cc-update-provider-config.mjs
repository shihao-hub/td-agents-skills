#!/usr/bin/env node
// cc-update-provider-config.mjs — 改既有供应商条目的 settings_config（任意 app 段通用）
// 默认 dry-run 打印改前/改后全文；--apply 才写库（自动备份、事务、写后回读深比较）。
// 只动 settings_config 一列，name/icon/meta 等其余列不变（要改显示名/图标请手工或扩展本脚本）。
import { DatabaseSync } from 'node:sqlite';
import { copyFileSync, readFileSync } from 'node:fs';
import os from 'os';
import path from 'path';

const argv = process.argv.slice(2);
const flag = (n) => { const i = argv.indexOf(n); return i >= 0 ? argv.splice(i, 2)[1] : undefined; };
const APPLY = argv.includes('--apply');
const dbPath = flag('--db') || path.join(os.homedir(), '.cc-switch', 'cc-switch.db');
const appType = flag('--app');
const id = flag('--id');
const cfgPath = flag('--config');
if (!appType || !id || !cfgPath) {
  console.error('usage: node cc-update-provider-config.mjs --app <app_type> --id <id> --config <cfg.json> [--db <沙箱.db>] [--apply]');
  process.exit(1);
}

const cfg = JSON.parse(readFileSync(cfgPath, 'utf-8').replace(/^﻿/, ''));
const db = new DatabaseSync(dbPath);
const old = db.prepare('SELECT settings_config FROM providers WHERE app_type=? AND id=?').get(appType, id);
if (!old) { console.error(`ABORT: providers (${appType}, ${id}) 不存在`); process.exit(1); }

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
console.log('OK（提醒：重启 cc-switch 后生效）');
