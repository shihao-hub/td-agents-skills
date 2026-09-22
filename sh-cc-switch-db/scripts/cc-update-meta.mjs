#!/usr/bin/env node
// cc-update-meta.mjs — 更新 providers.meta（任意 app 段），默认 dry-run，--apply 写库（备份+事务+回读）
import { DatabaseSync } from 'node:sqlite';
import { copyFileSync, mkdirSync, readFileSync } from 'node:fs';
import { execSync } from 'node:child_process';
import os from 'os';
import path from 'path';

const argv = process.argv.slice(2);
const flag = (n) => { const i = argv.indexOf(n); return i >= 0 ? argv.splice(i, 2)[1] : undefined; };
const APPLY = argv.includes('--apply');
const DEFAULT_DB = path.join(os.homedir(), '.cc-switch', 'cc-switch.db');
const dbPath = flag('--db') || DEFAULT_DB;
const isRealDb = path.resolve(dbPath) === path.resolve(DEFAULT_DB);
const appType = flag('--app');
const id = flag('--id');
const metaPath = flag('--meta');
if (!appType || !id || !metaPath) {
  console.error('usage: node cc-update-meta.mjs --app <app_type> --id <id> --meta <meta.json> [--db x.db] [--apply]');
  process.exit(1);
}

// 剥 BOM：PowerShell 5.1 Set-Content -Encoding UTF8 写的 JSON 带 BOM，JSON.parse 会挂
const meta = JSON.parse(readFileSync(metaPath, 'utf-8').replace(/^\uFEFF/, ''));
const db = new DatabaseSync(dbPath);
const old = db.prepare('SELECT meta FROM providers WHERE app_type=? AND id=?').get(appType, id);
if (!old) { console.error(`ABORT: providers (${appType}, ${id}) 不存在`); process.exit(1); }

console.log('=== 改前 meta ===');
console.log(old.meta);
console.log('=== 改后 meta ===');
console.log(JSON.stringify(meta, null, 2));
if (!APPLY) { console.log('\n(dry-run only，确认后加 --apply)'); process.exit(0); }

// 写真实库前：cc-switch 必须退出（运行实例持内存态且不热加载）
if (isRealDb) {
  try {
    const out = execSync('tasklist /FI "IMAGENAME eq cc-switch.exe" /NH', { encoding: 'utf-8' });
    if (/cc-switch\.exe/i.test(out)) {
      console.error('ABORT: cc-switch 正在运行。先 Stop-Process -Name cc-switch -Force，再 --apply。');
      process.exit(1);
    }
  } catch { /* tasklist 不可用时跳过检查 */ }
}

const now = Date.now();
const backupDest = isRealDb
  ? path.join(os.homedir(), '.cc-switch', 'backups', `cc-switch-before-meta-${id}-${now}.db`)
  : `${dbPath}.bak-${now}`;
mkdirSync(path.dirname(backupDest), { recursive: true });
copyFileSync(dbPath, backupDest);
console.log('已备份 ->', backupDest);

db.exec('BEGIN');
try {
  db.prepare('UPDATE providers SET meta=? WHERE app_type=? AND id=?').run(JSON.stringify(meta), appType, id);
  db.exec('COMMIT');
} catch (e) {
  db.exec('ROLLBACK');
  console.error('写入失败，已 ROLLBACK：', e.message);
  process.exit(1);
}

const back = db.prepare('SELECT meta FROM providers WHERE app_type=? AND id=?').get(appType, id).meta;
const ok = JSON.stringify(JSON.parse(back)) === JSON.stringify(meta);
console.log('=== 回读 ===');
console.log(back);
console.log('round-trip 一致:', ok);
if (!ok) process.exit(1);
console.log('OK（提醒：重启 cc-switch 后生效）');
