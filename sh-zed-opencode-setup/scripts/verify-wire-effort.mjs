#!/usr/bin/env node
// verify-wire-effort.mjs — 发线层验证：隔离环境跑一次真实 opencode 请求，抓请求体断言 reasoning_effort
//
// 用法: node verify-wire-effort.mjs <opencode.exe> <providerId/modelId> [--expect max]
//         [--config <opencode.json>]（默认 ~/.config/opencode/opencode.json）
//
// 原理: 把真实配置里目标 provider 的条目复制到 XDG 隔离的临时 home（baseURL → 本地回显服务器、
//       apiKey → 假值），`opencode run -m <provider/model>` 发一次真请求；回显服务器记录请求体，
//       断言每笔 POST */chat/completions 的 reasoning_effort === expect。
//       不动真实配置、不调真实 API、不花钱。对应四层验证法的第 2 层（SKILL.md 任务 B）。
// 退出码: 0 = 全部请求带期望档位；1 = 有请求缺失/档位不符；2 = 参数错误。

import http from 'node:http';
import { spawn } from 'node:child_process';
import { mkdtempSync, rmSync, writeFileSync, readFileSync } from 'node:fs';
import os from 'os';
import path from 'path';

const argv = process.argv.slice(2);
const flag = (n) => { const i = argv.indexOf(n); return i >= 0 ? argv.splice(i, 2)[1] : undefined; };
const [exe, modelRef] = argv;
const expect = flag('--expect') || 'max';
const configPath = flag('--config') || path.join(os.homedir(), '.config', 'opencode', 'opencode.json');
if (!exe || !modelRef || !modelRef.includes('/')) {
  console.error('用法: node verify-wire-effort.mjs <opencode.exe> <providerId/modelId> [--expect max] [--config <opencode.json>]');
  process.exit(2);
}
const [providerId, modelId] = modelRef.split('/');

const readJson = (p) => JSON.parse(readFileSync(p, 'utf-8').replace(/^﻿/, ''));
const real = readJson(configPath);
const provCfg = real.provider?.[providerId];
if (!provCfg) {
  console.error(`FAIL: ${configPath} 里没有 provider.${providerId}（现有: ${Object.keys(real.provider || {}).join(', ')}）`);
  process.exit(1);
}

// 1) 本地回显服务器：记录请求体，返回最小 openai 兼容 SSE
const port = 43111 + Math.floor(Math.random() * 2000);
const captured = [];
const server = http.createServer((req, res) => {
  let body = '';
  req.on('data', (c) => (body += c));
  req.on('end', () => {
    let parsed = null;
    try { parsed = JSON.parse(body); } catch { /* 保底记录原文 */ }
    captured.push({ url: req.url, body: parsed ?? body });
    console.log(`[echo] ${req.method} ${req.url}`);
    const chunk = (o) => res.write(`data: ${JSON.stringify(o)}\n\n`);
    if (parsed && parsed.stream === false) {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        id: 'echo', object: 'chat.completion', created: 1, model: parsed.model ?? 'x',
        choices: [{ index: 0, message: { role: 'assistant', content: 'echo-ok' }, finish_reason: 'stop' }],
        usage: { prompt_tokens: 1, completion_tokens: 1, total_tokens: 2 },
      }));
      return;
    }
    res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache' });
    const mk = (delta, finish = null) => ({
      id: 'echo', object: 'chat.completion.chunk', created: 1, model: parsed?.model ?? 'x',
      choices: [{ index: 0, delta, finish_reason: finish }],
    });
    chunk(mk({ role: 'assistant', content: 'echo-ok' }));
    chunk(mk({}, 'stop'));
    res.write('data: [DONE]\n\n');
    res.end();
  });
});
await new Promise((r) => server.listen(port, '127.0.0.1', r));

// 2) XDG 隔离的临时 home + 测试配置（目标 provider 原样复制，仅换 baseURL/apiKey）
const tmp = mkdtempSync(path.join(os.tmpdir(), 'oc-wire-'));
const testCfg = { provider: { [providerId]: JSON.parse(JSON.stringify(provCfg)) } };
testCfg.provider[providerId].options = { ...provCfg.options, baseURL: `http://127.0.0.1:${port}/v1`, apiKey: 'sk-dummy-echo' };
const fs = await import('node:fs');
fs.mkdirSync(path.join(tmp, 'config', 'opencode'), { recursive: true });
fs.mkdirSync(path.join(tmp, 'data'), { recursive: true });
writeFileSync(path.join(tmp, 'config', 'opencode', 'opencode.json'), JSON.stringify(testCfg, null, 2));

// 3) 隔离环境跑 opencode run（2 分钟上限）
//    必须用异步 spawn：spawnSync 会阻塞事件循环，内置回显服务器将无法响应 → 死锁超时
const env = {
  ...process.env,
  XDG_CONFIG_HOME: path.join(tmp, 'config'),
  XDG_DATA_HOME: path.join(tmp, 'data'),
  XDG_STATE_HOME: path.join(tmp, 'data'),
  XDG_CACHE_HOME: path.join(tmp, 'data'),
};
const child = spawn(exe, ['run', '-m', modelRef, 'reply with ok'], {
  env, stdio: ['ignore', 'pipe', 'pipe'],
});
let stdout = '', stderr = '';
child.stdout.on('data', (d) => (stdout += d));
child.stderr.on('data', (d) => (stderr += d));
const exit = await new Promise((resolve) => {
  const t = setTimeout(() => { try { child.kill(); } catch {} resolve('timeout'); }, 120000);
  child.on('exit', (c) => { clearTimeout(t); resolve(c); });
  child.on('error', (e) => { clearTimeout(t); resolve('error:' + e.message); });
});
console.log(stdout.trim().split('\n').slice(-3).join('\n'));
if (typeof exit === 'string') console.error('(opencode run 异常: ' + exit + (stderr ? ' stderr: ' + stderr.trim().slice(0, 300) : '') + '，请求可能已发出，继续断言抓包结果)');
else if (exit !== 0) console.error('(opencode run 退出码 ' + exit + (stderr ? ' stderr: ' + stderr.trim().slice(0, 300) : '') + '，请求可能已发出，继续断言抓包结果)');

server.close();
try { rmSync(tmp, { recursive: true, force: true }); } catch { /* Windows 占用则留着，tmp 自清 */ }

// 4) 断言：每笔 chat/completions 请求都带期望档位
const hits = captured.filter((r) => /chat\/completions$/.test(r.url));
if (hits.length === 0) { console.error(`FAIL: 没有抓到任何 chat/completions 请求（抓到 ${captured.length} 笔其他请求）`); process.exit(1); }
let fails = 0;
for (const h of hits) {
  const v = h.body?.reasoning_effort;
  if (v === expect) console.log(`PASS ${providerId}/${h.body?.model ?? modelId}: 请求体 reasoning_effort=${v}`);
  else { console.log(`FAIL ${providerId}/${h.body?.model ?? modelId}: reasoning_effort=${JSON.stringify(v)}，应为 ${expect}`); fails++; }
}
console.log(fails === 0 ? `\n结论: ${hits.length} 笔请求全部带 ${expect}` : `\n结论: ${fails} 笔不符`);
process.exit(fails === 0 ? 0 : 1);
