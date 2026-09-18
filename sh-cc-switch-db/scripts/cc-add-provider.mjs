#!/usr/bin/env node
// cc-add-provider.mjs — 向 cc-switch 任意 app 段新增供应商（通用）
// 默认 dry-run 只打印将要写入的行；--apply 才写库（自动备份、事务、写后回读验证）。
// 写真实库前检查 cc-switch 是否在运行（沙箱 --db 跳过检查）。
import { DatabaseSync } from 'node:sqlite';
import { copyFileSync, mkdirSync, readFileSync } from 'node:fs';
import { execSync } from 'node:child_process';
import os from 'os';
import path from 'path';

const HOME = os.homedir();
const DEFAULT_DB = path.join(HOME, '.cc-switch', 'cc-switch.db');

const argv = process.argv.slice(2);
const flag = (name) => {
  const i = argv.indexOf(name);
  return i >= 0 ? argv.splice(i, 2)[1] : undefined;
};
const has = (name) => argv.includes(name);

const APPLY = has('--apply');
const dbPath = flag('--db') || DEFAULT_DB;
const isRealDb = dbPath === DEFAULT_DB;

const appType = flag('--app');
const id = flag('--id');
const name = flag('--name') || id;
const configPath = flag('--config');
const endpointUrl = flag('--endpoint');
const icon = flag('--icon') ?? null;
const iconColor = flag('--icon-color') ?? null;
const category = flag('--category') || 'custom';
const website = flag('--website') ?? null;
const metaPath = flag('--meta');

if (!appType || !id || !configPath) {
  console.log(`usage: node cc-add-provider.mjs --app <app_type> --id <id> --config <settings_config.json>
                    [--name <显示名>] [--endpoint <url>] [--category custom]
                    [--icon <icon>] [--icon-color <#hex>] [--website <url>]
                    [--meta <meta.json>] [--db <沙箱.db>] [--apply]

说明：
  --config  指向该 app 段 settings_config 的 JSON 文件（各段形状不同，见 references/app-config-shapes.md）
  --apply   默认 dry-run；--apply 才写库（自动备份到 backups/，事务包裹，写后回读验证）
  --db      指向沙箱副本可安全测试；仅写真实库时检查 cc-switch 进程`);
  process.exit(appType ? 0 : 1);
}

// 剥 BOM：PowerShell 5.1 Set-Content -Encoding UTF8 写的 JSON 带 BOM，JSON.parse 会挂
const readJsonFile = (p) => readFileSync(p, 'utf-8').replace(/^\uFEFF/, '');

let settingsConfigRaw = readJsonFile(configPath);
JSON.parse(settingsConfigRaw); // 坏 JSON 在这里直接抛错
const settingsConfig = JSON.parse(settingsConfigRaw);

let meta = '{}';
if (metaPath) {
  meta = JSON.stringify(JSON.parse(readJsonFile(metaPath)));
}

const db = new DatabaseSync(dbPath);
const exists = db.prepare('SELECT 1 FROM providers WHERE app_type=? AND id=?').get(appType, id);
if (exists) {
  console.error(`ABORT: providers (${appType}, ${id}) 已存在，不重复写入`);
  process.exit(1);
}

const now = Date.now();
const sortIndex = db.prepare('SELECT COALESCE(MAX(sort_index),0)+1 AS n FROM providers WHERE app_type=?').get(appType).n;

const row = {
  id,
  app_type: appType,
  name,
  settings_config: settingsConfig,
  website_url: website,
  category,
  created_at: now,
  sort_index: sortIndex,
  notes: null,
  icon,
  icon_color: iconColor,
  meta: JSON.parse(meta),
  is_current: 0,
  in_failover_queue: 0,
  cost_multiplier: '1.0',
  limit_daily_usd: null,
  limit_monthly_usd: null,
  provider_type: null,
};

console.log('=== DRY-RUN：将写入以下行 ===');
console.log(`[providers] id=${id} app_type=${appType} name=${name} category=${category} icon=${icon} sort_index=${sortIndex}`);
console.log('[providers] settings_config =');
console.log(JSON.stringify(settingsConfig, null, 2));
console.log('[providers] meta =', meta);
if (endpointUrl) console.log(`[provider_endpoints] (${id}, ${appType}, ${endpointUrl})`);

if (!APPLY) {
  console.log('\n(dry-run only，确认无误后加 --apply)');
  process.exit(0);
}

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

const backupDest = isRealDb
  ? path.join(HOME, '.cc-switch', 'backups', `cc-switch-before-${id}-${now}.db`)
  : `${dbPath}.bak-${now}`;mkdirSync(path.dirname(backupDest), { recursive: true });
copyFileSync(dbPath, backupDest);
console.log('已备份 ->', backupDest);

db.exec('BEGIN');
try {
  db.prepare(
    'INSERT INTO providers (id, app_type, name, settings_config, website_url, category, created_at, sort_index, notes, icon, icon_color, meta, is_current, in_failover_queue, cost_multiplier, limit_daily_usd, limit_monthly_usd, provider_type) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)'
  ).run(
    row.id, row.app_type, row.name, JSON.stringify(settingsConfig, null, 2), row.website_url,
    row.category, row.created_at, row.sort_index, row.notes, row.icon, row.icon_color, meta,
    row.is_current, row.in_failover_queue, row.cost_multiplier, row.limit_daily_usd,
    row.limit_monthly_usd, row.provider_type
  );
  if (endpointUrl) {
    db.prepare('INSERT INTO provider_endpoints (provider_id, app_type, url, added_at) VALUES (?,?,?,?)').run(id, appType, endpointUrl, now);
  }
  db.exec('COMMIT');
} catch (e) {
  db.exec('ROLLBACK');
  console.error('写入失败，已 ROLLBACK：', e.message);
  process.exit(1);
}

const back = db.prepare('SELECT id, app_type, name, category, sort_index FROM providers WHERE app_type=? AND id=?').get(appType, id);
const cfgBack = JSON.parse(db.prepare('SELECT settings_config FROM providers WHERE app_type=? AND id=?').get(appType, id).settings_config);
const identical = JSON.stringify(cfgBack) === JSON.stringify(settingsConfig);
console.log('=== 写入完成，回读 ===');
console.log(JSON.stringify(back));
console.log('settings_config round-trip 一致:', identical);
if (endpointUrl) {
  const ep = db.prepare('SELECT provider_id, app_type, url FROM provider_endpoints WHERE provider_id=? AND app_type=?').get(id, appType);
  console.log('endpoint:', JSON.stringify(ep));
}
if (!identical) process.exit(1);
console.log('提醒：重启 cc-switch 后生效（运行中的实例不热加载）。');
