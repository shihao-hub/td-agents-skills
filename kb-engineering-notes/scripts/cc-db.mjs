#!/usr/bin/env node
// cc-db.mjs — cc-switch 数据库只读探查 + 备份工具
// 用法：node cc-db.mjs <command> [args] [--db <path>]
// 默认连 ~/.cc-switch/cc-switch.db；--db 可指向沙箱副本（测写操作用）。
import { DatabaseSync } from 'node:sqlite';
import { copyFileSync, mkdirSync } from 'node:fs';
import os from 'os';
import path from 'path';

const HOME = os.homedir();
const DEFAULT_DB = path.join(HOME, '.cc-switch', 'cc-switch.db');

const argv = process.argv.slice(2);
const flag = (name) => {
  const i = argv.indexOf(name);
  return i >= 0 ? argv.splice(i, 2)[1] : undefined;
};
const dbPath = flag('--db') || DEFAULT_DB;
const cmd = argv.shift() || 'help';
const ts = () => new Date().toISOString().replace(/[:T]/g, '-').slice(0, 19);

const usage = `cc-db.mjs — cc-switch DB read-only explorer + backup (db: ${dbPath})

commands:
  backup                 备份（真实库 -> ~/.cc-switch/backups/；沙箱 -> 同目录 .bak-<ts>）
  tables                 所有表 + 行数 + 列名
  list [app_type]        供应商列表（可按段过滤，如 pi / opencode / claude）
  show <app_type> <id>   单个供应商完整行（settings_config/meta 自动解析打印）
  settings               settings 表全量（key + value）
  endpoints [app_type]   provider_endpoints 表

options:
  --db <path>            指定数据库文件（默认 ~/.cc-switch/cc-switch.db）`;

switch (cmd) {
  case 'backup': {
    const dest = dbPath === DEFAULT_DB
      ? path.join(HOME, '.cc-switch', 'backups', `cc-switch-${ts()}.db`)
      : `${dbPath}.bak-${ts()}`;
    mkdirSync(path.dirname(dest), { recursive: true });
    copyFileSync(dbPath, dest);
    console.log('backup ->', dest);
    break;
  }
  case 'tables': {
    const d = new DatabaseSync(dbPath, { readOnly: true });
    const tables = d.prepare("SELECT name FROM sqlite_master WHERE type='table'").all();
    for (const t of tables) {
      const cols = d.prepare(`PRAGMA table_info(${t.name})`).all().map((c) => c.name);
      const cnt = d.prepare(`SELECT COUNT(*) c FROM ${t.name}`).get().c;
      console.log(`${t.name} (${cnt} rows): ${cols.join(', ')}`);
    }
    break;
  }
  case 'list': {
    const app = argv[0];
    const d = new DatabaseSync(dbPath, { readOnly: true });
    const sql = 'SELECT id, app_type, name, category, icon, icon_color, is_current, in_failover_queue, sort_index FROM providers';
    const rows = app
      ? d.prepare(sql + ' WHERE app_type=? ORDER BY sort_index').all(app)
      : d.prepare(sql + ' ORDER BY app_type, sort_index').all();
    console.log(JSON.stringify(rows, null, 2));
    break;
  }
  case 'show': {
    const [app, id] = argv;
    if (!app || !id) {
      console.error('usage: cc-db.mjs show <app_type> <id>');
      process.exit(1);
    }
    const d = new DatabaseSync(dbPath, { readOnly: true });
    const row = d.prepare('SELECT * FROM providers WHERE app_type=? AND id=?').get(app, id);
    if (!row) {
      console.error(`not found: (${app}, ${id})`);
      process.exit(1);
    }
    for (const k of ['settings_config', 'meta']) {
      if (row[k]) {
        try { row[k] = JSON.parse(row[k]); } catch { /* 保留原文 */ }
      }
    }
    console.log(JSON.stringify(row, null, 2));
    break;
  }
  case 'settings': {
    const d = new DatabaseSync(dbPath, { readOnly: true });
    for (const r of d.prepare('SELECT key, value FROM settings ORDER BY key').all()) {
      console.log(`\n### ${r.key}`);
      let v = r.value;
      try { v = JSON.stringify(JSON.parse(v), null, 2); } catch { /* 保留原文 */ }
      console.log(v);
    }
    break;
  }
  case 'endpoints': {
    const app = argv[0];
    const d = new DatabaseSync(dbPath, { readOnly: true });
    const rows = app
      ? d.prepare('SELECT id, provider_id, app_type, url, added_at FROM provider_endpoints WHERE app_type=?').all(app)
      : d.prepare('SELECT id, provider_id, app_type, url, added_at FROM provider_endpoints').all();
    console.log(JSON.stringify(rows, null, 2));
    break;
  }
  default:
    console.log(usage);
}
