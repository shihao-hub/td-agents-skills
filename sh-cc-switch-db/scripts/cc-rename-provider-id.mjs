#!/usr/bin/env node
// cc-rename-provider-id.mjs — 改供应商 id（providers 主键），并迁移外键子表 provider_endpoints / provider_health
// 默认 dry-run；--apply 生效（自动备份、事务、写后回读断言 + foreign_key_check 全库核验）。
// 外键坑（2026-09-14 实测）：两张子表引用 providers(id, app_type)，事务内先后改必违规，
// 必须先 PRAGMA defer_foreign_keys = ON 把 FK 校验推迟到 COMMIT。
import { DatabaseSync } from 'node:sqlite';
import { copyFileSync } from 'node:fs';
import os from 'os';
import path from 'path';

const argv = process.argv.slice(2);
const flag = (n) => { const i = argv.indexOf(n); return i >= 0 ? argv.splice(i, 2)[1] : undefined; };
const APPLY = argv.includes('--apply');
const dbPath = flag('--db') || path.join(os.homedir(), '.cc-switch', 'cc-switch.db');
const appType = flag('--app');
const fromId = flag('--from');
const toId = flag('--to');
if (!appType || !fromId || !toId) {
  console.error('usage: node cc-rename-provider-id.mjs --app <app_type> --from <旧id> --to <新id> [--db <沙箱.db>] [--apply]');
  process.exit(1);
}

const db = new DatabaseSync(dbPath);
const row = db.prepare('SELECT id, name FROM providers WHERE app_type=? AND id=?').get(appType, fromId);
if (!row) { console.error(`ABORT: (${appType}, ${fromId}) 不存在`); process.exit(1); }
if (db.prepare('SELECT 1 FROM providers WHERE app_type=? AND id=?').get(appType, toId)) {
  console.error(`ABORT: 目标 (${appType}, ${toId}) 已存在`); process.exit(1);
}
const eps = db.prepare('SELECT id, url FROM provider_endpoints WHERE app_type=? AND provider_id=?').all(appType, fromId);
console.log(`providers: (${appType}, ${fromId}) -> (${appType}, ${toId})  name="${row.name}"`);
console.log(`provider_endpoints: ${eps.length} 条 -> ${JSON.stringify(eps.map((e) => e.url))}`);
if (!APPLY) { console.log('\n(dry-run only，确认后加 --apply)'); process.exit(0); }

const bak = `${dbPath}.bak-${Date.now()}`;
copyFileSync(dbPath, bak);
console.log('已备份 ->', bak);

db.exec('PRAGMA defer_foreign_keys = ON'); // 提交时才校验外键，允许事务内主/子表先后换 id
db.exec('BEGIN');
try {
  db.prepare('UPDATE providers SET id=? WHERE app_type=? AND id=?').run(toId, appType, fromId);
  db.prepare('UPDATE provider_endpoints SET provider_id=? WHERE app_type=? AND provider_id=?').run(toId, appType, fromId);
  try {
    db.prepare('UPDATE provider_health SET provider_id=? WHERE app_type=? AND provider_id=?').run(toId, appType, fromId);
  } catch (e) { if (!/no such table/i.test(e.message)) throw e; } // 表不存在则跳过
  db.exec('COMMIT');
} catch (e) {
  db.exec('ROLLBACK');
  console.error('更新失败，已 ROLLBACK：', e.message);
  process.exit(1);
}

const okNew = !!db.prepare('SELECT 1 FROM providers WHERE app_type=? AND id=?').get(appType, toId);
const okGone = !db.prepare('SELECT 1 FROM providers WHERE app_type=? AND id=?').get(appType, fromId);
const okEp = db.prepare('SELECT COUNT(*) n FROM provider_endpoints WHERE app_type=? AND provider_id=?').get(appType, fromId).n === 0
  && db.prepare('SELECT COUNT(*) n FROM provider_endpoints WHERE app_type=? AND provider_id=?').get(appType, toId).n === eps.length;
console.log(`回读：新 id 存在=${okNew}，旧 id 已清=${okGone}，endpoints 已迁移=${okEp}`);
const fkBad = db.prepare('PRAGMA foreign_key_check').all();
console.log('全库外键完整性：', fkBad.length === 0 ? 'OK（无违规）' : JSON.stringify(fkBad));
if (!(okNew && okGone && okEp) || fkBad.length > 0) process.exit(1);
console.log('OK（提醒：重启 cc-switch 后生效；opencode/pi 段还要同步改原生配置文件里的 provider key）');
