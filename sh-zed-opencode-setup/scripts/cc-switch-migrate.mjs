// cc-switch-migrate.mjs — 把 cc-switch 里 Claude Code 的中转供应商迁移到 opencode 段
//
// 用法:
//   node cc-switch-migrate.mjs            # dry-run：只打印计划，不写库（默认，安全）
//   node cc-switch-migrate.mjs --apply    # 真正写入（自动备份 db，事务，失败回滚）
//   node cc-switch-migrate.mjs --db <路径> # 指定 db（默认 ~/.cc-switch/cc-switch.db）
//
// 约定: 供应商名称 == 供应商标识（opencode.json 的 provider key / cc-switch 的 id）。
// 迁移后需重启 cc-switch。详见 skill 的 references/cc-switch-migration.md。

import { DatabaseSync } from "node:sqlite";
import { copyFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const args = process.argv.slice(2);
const APPLY = args.includes("--apply");
const dbIdx = args.indexOf("--db");
const DB = dbIdx >= 0 ? args[dbIdx + 1] : join(homedir(), ".cc-switch", "cc-switch.db");

// 与 opencode.json 中验证过的配置一致：effort max + 变体全禁用（无下拉框，默认即 max）
function claudeProviderBlob(id, token, baseUrl) {
  const disabled = Object.fromEntries(
    ["low", "medium", "high", "xhigh", "max"].map((k) => [k, { disabled: true }]),
  );
  const model = (name) => ({
    name,
    limit: { context: 1000000, output: 128000 },
    options: { effort: "max" },
    reasoning: false,
    variants: disabled,
  });
  return JSON.stringify({
    npm: "@ai-sdk/anthropic",
    name: id,
    options: { baseURL: baseUrl, authToken: token },
    models: { "claude-opus-5": model("claude-opus-5"), "claude-sonnet-5": model("claude-sonnet-5") },
  });
}

const db = new DatabaseSync(DB, { readOnly: !APPLY });
const claudeRows = db.prepare("SELECT id, name, category, settings_config FROM providers WHERE app_type='claude'").all();
const opencodeRows = db.prepare("SELECT id, name FROM providers WHERE app_type='opencode'").all();
const opencodeIds = new Set(opencodeRows.map((r) => r.id));

const toInsert = [], toUpdate = [];
for (const row of claudeRows) {
  const slug = row.name; // claude 段 name 是 slug（subclaude-xxx），id 是 UUID
  const cfg = JSON.parse(row.settings_config);
  const env = cfg.env ?? {};
  const token = env.ANTHROPIC_AUTH_TOKEN;
  let baseUrl = env.ANTHROPIC_BASE_URL;

  // 只迁移"中转型"：同时有 token 和 baseURL；跳过官方与智谱（opencode 已有 coding 端点版本）
  if (!token || !baseUrl) { console.log(`SKIP ${slug}: 非中转（缺 AUTH_TOKEN/BASE_URL）`); continue; }
  if (row.category === "official" || row.category === "cn_official" || /zhipu|glm/i.test(slug)) {
    console.log(`SKIP ${slug}: 官方/智谱条目不迁移`);
    continue;
  }
  // claude 段是 https://xxx/ ，opencode 的 anthropic SDK 需要 https://xxx/v1
  baseUrl = baseUrl.replace(/\/+$/, "");
  if (!baseUrl.endsWith("/v1")) baseUrl += "/v1";

  if (opencodeIds.has(slug)) toUpdate.push({ slug, token, baseUrl });
  else toInsert.push({ slug, token, baseUrl });
}

console.log(`\n=== 迁移计划（${APPLY ? "APPLY 写入" : "DRY-RUN 预览"}）===`);
for (const u of toUpdate) console.log(`UPDATE opencode/${u.slug}: name 改为标识、settings_config 换成新模板（含 variants 全禁用）`);
for (const i of toInsert) console.log(`INSERT  opencode/${i.slug}: 新建（模板同上，token/baseURL 来自 claude 段）`);
if (toInsert.length === 0 && toUpdate.length === 0) { console.log("（无可迁移条目）"); db.close(); process.exit(0); }

// 顺带修正已存在 opencode 条目的 name==id（仅安全场景：条目 id 本身就是标识）
const nameFixes = opencodeRows.filter((r) => r.name !== r.id && !r.id.includes("-"));
if (nameFixes.length) { console.log(`RENAME  ${nameFixes.map((r) => `${r.name} -> ${r.id}`).join(", ")}`); }

if (!APPLY) {
  console.log("\n这是预览。确认无误后加 --apply 执行（会自动备份 db）。");
  db.close();
  process.exit(0);
}

// ---- 写入 ----
const stamp = new Date().toISOString().replace(/[:.]/g, "-");
const backup = join(homedir(), ".cc-switch", "backups", `cc-switch-before-migrate-${stamp}.db`);
copyFileSync(DB, backup);
console.log(`\n备份: ${backup}`);

db.close();
const dbRW = new DatabaseSync(DB);
dbRW.exec("BEGIN");
try {
  const now = Date.now();
  for (const u of toUpdate) {
    dbRW.prepare("UPDATE providers SET name=?, settings_config=? WHERE id=? AND app_type='opencode'")
      .run(u.slug, claudeProviderBlob(u.slug, u.token, u.baseUrl), u.slug);
  }
  const insProv = dbRW.prepare(
    `INSERT INTO providers (id, app_type, name, settings_config, website_url, category, created_at, sort_index,
     notes, icon, icon_color, meta, is_current, in_failover_queue, cost_multiplier, limit_daily_usd, limit_monthly_usd, provider_type)
     VALUES (?, 'opencode', ?, ?, ?, NULL, ?, NULL, NULL, 'anthropic', '#D4915D',
     '{"endpointAutoSelect":true,"liveConfigManaged":true}', 0, 0, '1.0', NULL, NULL, NULL)`,
  );
  const insEp = dbRW.prepare(
    "INSERT INTO provider_endpoints (provider_id, app_type, url, added_at) VALUES (?, 'opencode', ?, ?)",
  );
  for (const i of toInsert) {
    const site = i.baseUrl.replace(/\/v1$/, "");
    insProv.run(i.slug, i.slug, claudeProviderBlob(i.slug, i.token, i.baseUrl), site, now);
    insEp.run(i.slug, site, now);
  }
  dbRW.exec("COMMIT");
  console.log("写入完成（事务提交）");
} catch (e) {
  dbRW.exec("ROLLBACK");
  console.error("ROLLBACK:", e.message);
  process.exit(1);
}

// 回读验证
const check = dbRW.prepare("SELECT id, name, settings_config FROM providers WHERE app_type='opencode' ORDER BY created_at").all();
let bad = 0;
for (const r of check) {
  const cfg = JSON.parse(r.settings_config);
  const okVariants = Object.values(cfg.models ?? {}).every((m) => !m.variants || Object.values(m.variants).every((v) => v.disabled));
  const okName = r.name === r.id && cfg.name === r.id;
  if (!okVariants || !okName) { console.log(`CHECK-FAIL ${r.id}: name=${r.name}/${cfg.name} variantsOk=${okVariants}`); bad++; }
  else console.log(`CHECK-OK ${r.id}`);
}
dbRW.close();
console.log(bad === 0 ? "\n全部验证通过。请重启 cc-switch 使其加载新数据。" : `\n${bad} 项异常，可回滚: 关闭 cc-switch 后把备份复制回 ${DB}`);
process.exit(bad === 0 ? 0 : 1);
