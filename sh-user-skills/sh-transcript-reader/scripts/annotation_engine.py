"""
精读本划词标注引擎（零外部依赖，file:// 离线直开可用）

对外只暴露两个东西：
  1. ANNOTATION_CSS / ANNOTATION_UI_HTML / ANNOTATION_JS 三段可注入资产；
  2. inject_annotation_engine(html) —— 幂等注入函数。

能力：
  - 选中正文任意句子，浮动工具条加粗 / 四色纸面荧光 / 移除；
  - 右侧标注抽屉：筛选、复制 Markdown 摘录、点击平滑跳回原文并脉冲提示；
  - 自定义浏览器标签页标题（仅改 <title>，不改正文主标题，刷新仍保留，不影响标注存储锚点）；
  - localStorage 按原始标题热持久化，刷新自动还原；
  - 「保存含标记 HTML」导出含全部标记与自定义标签名的独立文件（可继续增删）。
"""

import re

ANNOTATION_CSS = r"""
    /* === HL-ANNOTATION-CSS === */
    .hl-mark {
      border-radius: 2px; padding: 0 1px; cursor: pointer;
      transition: background-color 0.15s ease, box-shadow 0.15s ease;
    }
    .hl-mark[data-hl-color="amber"] { background: #FBF0C4; }
    .hl-mark[data-hl-color="jade"]  { background: #DCF0E4; }
    .hl-mark[data-hl-color="clay"]  { background: #F9E3D8; }
    .hl-mark[data-hl-color="mist"]  { background: #DDEBF4; }
    .hl-mark[data-hl-bold="true"] { font-weight: 700; color: #14251C; }
    .hl-mark[data-hl-bold="true"][data-hl-color="amber"] { color: #4A3608; }
    .hl-mark[data-hl-bold="true"][data-hl-color="jade"]  { color: #123A26; }
    .hl-mark[data-hl-bold="true"][data-hl-color="clay"]  { color: #4C2415; }
    .hl-mark[data-hl-bold="true"][data-hl-color="mist"]  { color: #16344A; }
    .hl-pulse { animation: hl-pulse 1.8s ease-out; }
    @keyframes hl-pulse {
      0%   { box-shadow: 0 0 0 0 rgba(230, 138, 54, 0.55); }
      60%  { box-shadow: 0 0 0 7px rgba(230, 138, 54, 0); }
      100% { box-shadow: 0 0 0 0 rgba(230, 138, 54, 0); }
    }

    #hl-popover {
      position: fixed; left: 0; top: 0; z-index: 1100; display: none;
      align-items: center; gap: 4px; padding: 6px;
      background: #FFFDF9; border: 1px solid var(--border-accent, #CBD5CA);
      border-radius: 8px; box-shadow: 0 10px 26px rgba(28, 34, 30, 0.16);
      transform: translate(-50%, -100%);
    }
    #hl-popover.show { display: flex; }
    #hl-popover.below { transform: translate(-50%, 0); }
    .hl-sw {
      display: inline-flex; align-items: center; justify-content: center;
      width: 28px; height: 28px; padding: 0; border-radius: 6px;
      border: 1px solid transparent; background: transparent;
      color: var(--text-main, #1C221E); cursor: pointer;
      font-family: var(--font-sans, sans-serif); font-size: 13px;
      transition: background 0.12s ease, border-color 0.12s ease;
    }
    .hl-sw:hover { background: var(--bg-subtle, #F4F6F3); border-color: var(--border-light, #E5E9E3); }
    .hl-sw.bold { font-family: var(--font-serif, Georgia, serif); font-weight: 700; font-size: 15px; }
    .hl-sw.active { background: var(--pine-light, #EBF3EE); border-color: var(--pine-mid, #2A5E47); color: var(--pine-deep, #1A4432); }
    .hl-swatch { width: 20px; height: 20px; border-radius: 50%; border: 1px solid rgba(28, 34, 30, 0.18); }
    .hl-swatch[data-color="amber"] { background: #FBF0C4; }
    .hl-swatch[data-color="jade"]  { background: #DCF0E4; }
    .hl-swatch[data-color="clay"]  { background: #F9E3D8; }
    .hl-swatch[data-color="mist"]  { background: #DDEBF4; }
    .hl-swatch.active { box-shadow: 0 0 0 2px #FFFDF9, 0 0 0 3.5px var(--pine-mid, #2A5E47); }
    .hl-sep { width: 1px; height: 16px; background: var(--border-light, #E5E9E3); margin: 0 2px; }
    .hl-clear {
      width: auto; padding: 0 8px; font-size: 12px;
      color: var(--clay-deep, #8E4A28);
    }
    .hl-clear:hover { background: var(--clay-light, #FBF2EC); border-color: #EFE0D5; }
    .hl-clear:disabled { opacity: 0.38; cursor: default; background: transparent; border-color: transparent; }
    .hl-clear[hidden] { display: none; }

    #hl-drawer {
      position: fixed; top: 0; right: 0; z-index: 950; width: 340px; height: 100vh;
      display: flex; flex-direction: column;
      background: #FFFFFF; border-left: 1px solid var(--border-light, #E5E9E3);
      box-shadow: -10px 0 30px rgba(28, 34, 30, 0.08);
      transform: translateX(102%); transition: transform 0.28s ease;
    }
    body.hl-drawer-open #hl-drawer { transform: translateX(0); }
    @media (min-width: 1280px) {
      .masthead-inner, .reader-toolbar-inner, .main-container { transition: transform 0.28s ease; }
      body.hl-drawer-open .masthead-inner,
      body.hl-drawer-open .reader-toolbar-inner,
      body.hl-drawer-open .main-container { transform: translateX(-170px); }
    }
    .hl-drawer-head {
      display: flex; align-items: center; justify-content: space-between;
      padding: 16px 18px 10px; border-bottom: 1px solid var(--border-light, #E5E9E3);
    }
    .hl-drawer-title {
      font-family: var(--font-serif, Georgia, serif); font-size: 16px; font-weight: 700;
      color: var(--text-main, #1C221E);
    }
    .hl-drawer-title span {
      font-family: var(--font-mono, monospace); font-size: 12px;
      color: var(--pine-mid, #2A5E47); margin-left: 4px;
    }
    #hl-drawer-close {
      border: none; background: transparent; font-size: 18px; line-height: 1;
      color: var(--text-soft, #85938B); cursor: pointer; padding: 4px;
    }
    #hl-drawer-close:hover { color: var(--text-main, #1C221E); }
    .hl-drawer-filters {
      display: flex; flex-wrap: wrap; gap: 6px; padding: 10px 18px;
      border-bottom: 1px dashed var(--border-light, #E5E9E3);
    }
    .hl-fchip {
      border: 1px solid var(--border-light, #E5E9E3); background: transparent;
      border-radius: 999px; padding: 3px 10px; font-size: 12px;
      color: var(--text-muted, #56645D); cursor: pointer; font-family: var(--font-sans, sans-serif);
    }
    .hl-fchip:hover { border-color: var(--border-accent, #CBD5CA); color: var(--text-main, #1C221E); }
    .hl-fchip.active {
      background: var(--pine-deep, #1A4432); border-color: var(--pine-deep, #1A4432);
      color: #FFFFFF; font-weight: 500;
    }
    .hl-drawer-actions { padding: 10px 18px 4px; display: flex; gap: 8px; }
    #hl-copy-md {
      flex: 1; border: 1px solid var(--border-light, #E5E9E3);
      background: var(--bg-subtle, #F4F6F3); border-radius: 5px; padding: 7px 10px;
      font-size: 12.5px; color: var(--text-muted, #56645D); cursor: pointer;
      font-family: var(--font-sans, sans-serif); transition: all 0.15s ease;
    }
    #hl-copy-md:hover { border-color: var(--border-accent, #CBD5CA); color: var(--text-main, #1C221E); background: #FFFFFF; }
    #hl-clear-all {
      flex: 0 0 auto; border: 1px solid var(--border-light, #E5E9E3);
      background: transparent; border-radius: 5px; padding: 7px 10px;
      font-size: 12.5px; color: var(--clay-deep, #8E4A28); cursor: pointer;
      font-family: var(--font-sans, sans-serif); transition: all 0.15s ease;
    }
    #hl-clear-all:hover { border-color: var(--clay-mid, #B0623B); background: var(--clay-light, #FBF2EC); }
    #hl-clear-all:disabled { opacity: 0.42; cursor: default; border-color: var(--border-light, #E5E9E3); background: transparent; }
    .hl-list {
      flex: 1; overflow-y: auto; padding: 8px 14px 18px;
      display: grid; gap: 8px; align-content: start; scrollbar-width: thin;
    }
    .hl-list::-webkit-scrollbar { width: 6px; }
    .hl-list::-webkit-scrollbar-thumb { background: var(--border-accent, #CBD5CA); border-radius: 3px; }
    .hl-item {
      border: 1px solid var(--border-light, #E5E9E3);
      border-left: 3px solid var(--border-accent, #CBD5CA);
      border-radius: 6px; padding: 9px 10px; cursor: pointer; background: #FFFFFF;
      transition: background 0.15s ease, box-shadow 0.15s ease;
    }
    .hl-item:hover { background: var(--bg-subtle, #F4F6F3); }
    .hl-item.is-active { box-shadow: 0 0 0 1px var(--pine-mid, #2A5E47) inset; }
    .hl-item.c-amber { border-left-color: #D9A93A; }
    .hl-item.c-jade  { border-left-color: #4E8A6A; }
    .hl-item.c-clay  { border-left-color: #C07A55; }
    .hl-item.c-mist  { border-left-color: #6E93AF; }
    .hl-item.c-bold  { border-left-color: #1A4432; }
    .hl-item-head { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
    .hl-badge {
      font-size: 11px; font-family: var(--font-serif, Georgia, serif); font-weight: 600;
      padding: 1px 7px; border-radius: 3px;
      background: var(--pine-light, #EBF3EE); color: var(--pine-deep, #1A4432);
    }
    .hl-badge.host { background: var(--clay-light, #FBF2EC); color: var(--clay-deep, #8E4A28); }
    .hl-time { font-family: var(--font-mono, monospace); font-size: 10.5px; color: var(--text-soft, #85938B); }
    .hl-item-remove {
      margin-left: auto; border: none; background: transparent;
      color: var(--text-soft, #85938B); cursor: pointer; font-size: 14px;
      opacity: 0; transition: opacity 0.12s ease, color 0.12s ease; padding: 0 2px;
    }
    .hl-item:hover .hl-item-remove { opacity: 1; }
    .hl-item-remove:hover { color: var(--clay-deep, #8E4A28); }
    .hl-item-text {
      font-size: 13px; line-height: 1.6; color: var(--text-main, #1C221E);
      display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
    }
    .hl-item-act {
      margin-top: 4px; font-size: 10.5px; color: var(--text-soft, #85938B);
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .hl-empty { padding: 28px 10px; text-align: center; font-size: 13px; line-height: 1.8; color: var(--text-soft, #85938B); white-space: pre-line; }
    .hl-toolbar-group { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
    .hl-tool-btn {
      background: transparent; border: 1px solid var(--border-light, #E5E9E3);
      padding: 5px 12px; border-radius: 4px; color: var(--text-muted, #56645D);
      cursor: pointer; font-size: 13px; font-family: var(--font-sans, sans-serif);
      transition: all 0.15s ease;
    }
    .hl-tool-btn:hover { border-color: var(--border-accent, #CBD5CA); color: var(--text-main, #1C221E); background: #FFFFFF; }
    .hl-tool-btn.active { background: var(--pine-light, #EBF3EE); border-color: var(--pine-mid, #2A5E47); color: var(--pine-deep, #1A4432); font-weight: 600; }
    #hl-title-modal {
      position: fixed; inset: 0; z-index: 1250; display: none;
      align-items: center; justify-content: center; padding: 16px;
      background: rgba(28, 34, 30, 0.36); backdrop-filter: blur(2px);
    }
    #hl-title-modal.show { display: flex; }
    .hl-title-dialog {
      width: min(460px, 100%); background: #FFFDF9;
      border: 1px solid var(--border-accent, #CBD5CA);
      border-top: 3px solid var(--pine-mid, #2A5E47);
      border-radius: 8px; padding: 20px 22px;
      box-shadow: 0 18px 42px rgba(28, 34, 30, 0.2);
      font-family: var(--font-sans, sans-serif);
    }
    .hl-title-dialog h3 {
      font-family: var(--font-serif, Georgia, serif);
      font-size: 17px; font-weight: 700; color: var(--text-main, #1C221E);
      margin-bottom: 6px;
    }
    .hl-title-hint {
      font-size: 12.5px; line-height: 1.6; color: var(--text-muted, #56645D);
      margin-bottom: 12px;
    }
    #hl-title-input {
      width: 100%; padding: 9px 11px; font-size: 14px;
      font-family: var(--font-sans, sans-serif); color: var(--text-main, #1C221E);
      background: #FFFFFF; border: 1px solid var(--border-accent, #CBD5CA);
      border-radius: 5px; outline: none; transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    #hl-title-input:focus {
      border-color: var(--pine-mid, #2A5E47);
      box-shadow: 0 0 0 3px rgba(42, 94, 71, 0.12);
    }
    .hl-title-orig {
      margin-top: 8px; font-size: 12px; line-height: 1.5;
      color: var(--text-soft, #85938B); word-break: break-all;
    }
    .hl-title-actions {
      display: flex; align-items: center; justify-content: space-between; gap: 8px;
      margin-top: 16px;
    }
    .hl-title-actions-right { display: flex; align-items: center; gap: 8px; }
    .hl-btn-primary {
      background: var(--pine-deep, #1A4432); border: 1px solid var(--pine-deep, #1A4432);
      color: #FFFFFF; padding: 6px 14px; border-radius: 4px;
      font-size: 13px; font-family: var(--font-sans, sans-serif); cursor: pointer;
    }
    .hl-btn-primary:hover { background: var(--pine-mid, #2A5E47); border-color: var(--pine-mid, #2A5E47); }
    .hl-btn-ghost {
      background: transparent; border: 1px solid var(--border-light, #E5E9E3);
      color: var(--text-muted, #56645D); padding: 6px 12px; border-radius: 4px;
      font-size: 13px; font-family: var(--font-sans, sans-serif); cursor: pointer;
    }
    .hl-btn-ghost:hover { border-color: var(--border-accent, #CBD5CA); color: var(--text-main, #1C221E); background: #FFFFFF; }
    .hl-btn-reset {
      background: transparent; border: 1px solid transparent;
      color: var(--clay-deep, #8E4A28); padding: 6px 8px; border-radius: 4px;
      font-size: 12.5px; font-family: var(--font-sans, sans-serif); cursor: pointer;
    }
    .hl-btn-reset:hover { background: var(--clay-light, #FBF2EC); border-color: #EFE0D5; }
    .hl-btn-reset:disabled { opacity: 0.4; cursor: default; background: transparent; border-color: transparent; }
    #hl-toast {
      position: fixed; left: 50%; bottom: 28px; z-index: 1200;
      display: flex; align-items: center; gap: 14px;
      padding: 10px 16px; background: #1C221E; color: #F7F5EF; border-radius: 8px;
      font-size: 13px; box-shadow: 0 12px 30px rgba(28, 34, 30, 0.24);
      opacity: 0; pointer-events: none; transform: translate(-50%, 12px);
      transition: opacity 0.2s ease, transform 0.2s ease;
    }
    #hl-toast.show { opacity: 1; transform: translate(-50%, 0); pointer-events: auto; }
    #hl-undo {
      border: none; background: transparent; color: #F2C078; font-weight: 600;
      font-size: 13px; cursor: pointer; text-decoration: underline; padding: 0;
      font-family: var(--font-sans, sans-serif);
    }
    #hl-undo[hidden] { display: none; }
    @media (max-width: 420px) { #hl-drawer { width: 100%; } }
    @media print {
      #hl-drawer, #hl-popover, #hl-toast, #hl-title-modal, .hl-toolbar-group { display: none !important; }
      .hl-mark { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    }
"""

ANNOTATION_UI_HTML = r"""
<!-- === HL-ANNOTATION-UI === -->
<div id="hl-popover" role="toolbar" aria-label="划词标注工具条">
  <button type="button" class="hl-sw bold" data-action="bold" title="加粗（B）">B</button>
  <span class="hl-sep"></span>
  <button type="button" class="hl-sw hl-swatch" data-color="amber" title="琥珀黄"></button>
  <button type="button" class="hl-sw hl-swatch" data-color="jade" title="松针绿"></button>
  <button type="button" class="hl-sw hl-swatch" data-color="clay" title="陶土粉"></button>
  <button type="button" class="hl-sw hl-swatch" data-color="mist" title="青黛蓝"></button>
  <span class="hl-sep"></span>
  <button type="button" class="hl-sw hl-clear" data-action="clear" title="清空当前标记的加粗与背景色" disabled>清空</button>
</div>

<aside id="hl-drawer" aria-label="标注清单" aria-hidden="true">
  <div class="hl-drawer-head">
    <div class="hl-drawer-title">📝 标注清单 <span id="hl-count">0</span></div>
    <button type="button" id="hl-drawer-close" title="收起标注清单">✕</button>
  </div>
  <div class="hl-drawer-filters" role="group" aria-label="标注筛选">
    <button type="button" class="hl-fchip active" data-hl-filter="all">全部</button>
    <button type="button" class="hl-fchip" data-hl-filter="bold">加粗</button>
    <button type="button" class="hl-fchip" data-hl-filter="amber">琥珀黄</button>
    <button type="button" class="hl-fchip" data-hl-filter="jade">松针绿</button>
    <button type="button" class="hl-fchip" data-hl-filter="clay">陶土粉</button>
    <button type="button" class="hl-fchip" data-hl-filter="mist">青黛蓝</button>
  </div>
  <div class="hl-drawer-actions">
    <button type="button" id="hl-copy-md">复制 Markdown 摘录</button>
    <button type="button" id="hl-clear-all" title="清空全部标注（5 秒内可撤销）" disabled>清空全部</button>
  </div>
  <div id="hl-list" class="hl-list"></div>
</aside>

<div id="hl-title-modal" role="dialog" aria-modal="true" aria-labelledby="hl-title-modal-heading" aria-hidden="true">
  <div class="hl-title-dialog">
    <h3 id="hl-title-modal-heading">自定义浏览器标签页名称</h3>
    <p class="hl-title-hint">仅修改 Chrome 标签栏显示的标题（&lt;title&gt;），页面正文主标题保持不变；刷新仍有效，点「保存含标记 HTML」可写入文件。</p>
    <input type="text" id="hl-title-input" placeholder="输入简短易区分的标签名…" maxlength="120" autocomplete="off">
    <div class="hl-title-orig">默认标题：<span id="hl-title-orig-text"></span></div>
    <div class="hl-title-actions">
      <button type="button" id="hl-title-reset" class="hl-btn-reset">恢复默认</button>
      <div class="hl-title-actions-right">
        <button type="button" id="hl-title-cancel" class="hl-btn-ghost">取消</button>
        <button type="button" id="hl-title-confirm" class="hl-btn-primary">保存标签名</button>
      </div>
    </div>
  </div>
</div>

<div id="hl-toast" role="status" aria-live="polite">
  <span id="hl-toast-msg"></span>
  <button type="button" id="hl-undo" hidden>撤销</button>
</div>
<!-- === /HL-ANNOTATION-UI === -->
"""

ANNOTATION_TOOLBAR_BUTTONS = r"""
<button type="button" id="hl-drawer-toggle" class="hl-tool-btn">📝 标注清单 (0)</button>
<button type="button" id="hl-rename-title" class="hl-tool-btn" title="自定义 Chrome 标签页标题（只改标签名，不改正文主标题）">🏷️ 改标签名</button>
<button type="button" id="hl-save-html" class="hl-tool-btn">💾 保存含标记 HTML</button>
"""

ANNOTATION_OVERLAY_HTML = ANNOTATION_UI_HTML


ANNOTATION_JS = r"""
/* === HL-ANNOTATION-JS === */
(function () {
  'use strict';

  var READ_ROOT = '.dialogue-flow, .essay-flow, .executive-card';
  var HOST_SEL = '.turn-content p, .essay-paragraph, .section-summary, .pull-quote, .executive-card p, .act-desc';
  var STORE_PREFIX = 'hl-annotations:';
  var TITLE_PREFIX = 'hl-tab-title:';

  var state = { pending: null, filter: 'all', undo: null, undoBatch: null, saveTimer: 0, toastTimer: 0, activeId: '' };
  var els = {};
  var hostCache = null;

  function qs(sel, root) { return (root || document).querySelector(sel); }
  function qsa(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  function isRoot(el) { return !!(el && el.closest && el.closest(READ_ROOT)); }

  function getTitleEl() { return document.querySelector('title'); }
  var titleElInit = getTitleEl();
  var INITIAL_DOM_TITLE = (titleElInit ? titleElInit.textContent : document.title) || '';
  var ORIG_TITLE = (titleElInit && titleElInit.getAttribute('data-orig-title')) || INITIAL_DOM_TITLE;
  if (titleElInit && !titleElInit.getAttribute('data-orig-title') && ORIG_TITLE) {
    titleElInit.setAttribute('data-orig-title', ORIG_TITLE);
  }

  function storeKey() { return STORE_PREFIX + (ORIG_TITLE || document.title); }
  function titleStoreKey() { return TITLE_PREFIX + (ORIG_TITLE || INITIAL_DOM_TITLE); }

  function updateRenameBtnState() {
    var btn = qs('#hl-rename-title');
    if (!btn) return;
    var customized = !!(ORIG_TITLE && document.title !== ORIG_TITLE);
    btn.classList.toggle('active', customized);
    btn.title = customized
      ? '当前标签名：' + document.title + '（默认：' + ORIG_TITLE + '）'
      : '自定义 Chrome 标签页标题（只改标签名，不改正文主标题）';
  }

  function applyDocumentTitle(nextTitle) {
    var t = (nextTitle || '').trim() || ORIG_TITLE;
    document.title = t;
    var tel = getTitleEl();
    if (tel) {
      tel.textContent = t;
      if (ORIG_TITLE) tel.setAttribute('data-orig-title', ORIG_TITLE);
    }
    updateRenameBtnState();
  }

  (function hydrateSavedTitle() {
    try {
      var saved = localStorage.getItem(titleStoreKey());
      if (saved && saved.trim()) applyDocumentTitle(saved.trim());
    } catch (e) {}
  })();

  function getHosts() {
    if (!hostCache) {
      hostCache = qsa(HOST_SEL).filter(function (el) { return isRoot(el); });
    }
    return hostCache;
  }

  function hostIndexOf(host) { return getHosts().indexOf(host); }

  function offsetInHost(host, node, offset) {
    var r = document.createRange();
    r.selectNodeContents(host);
    try { r.setEnd(node, offset); } catch (e) { return -1; }
    return r.toString().length;
  }

  function rangeToHosts(range) {
    var out = [];
    getHosts().forEach(function (host) {
      if (!range.intersectsNode(host)) return;
      var hr = document.createRange();
      hr.selectNodeContents(host);
      try {
        if (range.compareBoundaryPoints(Range.START_TO_START, hr) > 0) {
          hr.setStart(range.startContainer, range.startOffset);
        }
        if (range.compareBoundaryPoints(Range.END_TO_END, hr) < 0) {
          hr.setEnd(range.endContainer, range.endOffset);
        }
      } catch (e) { return; }
      if (hr.collapsed) return;
      var start = offsetInHost(host, hr.startContainer, hr.startOffset);
      var end = offsetInHost(host, hr.endContainer, hr.endOffset);
      if (start < 0 || end <= start) return;
      var text = host.textContent.slice(start, end);
      if (!text.replace(/\s+/g, '')) return;
      out.push({ host: host, start: start, end: end, text: text });
    });
    return out;
  }

  function currentSelection() {
    var sel = window.getSelection();
    if (!sel || sel.rangeCount === 0 || sel.isCollapsed) return null;
    var range = sel.getRangeAt(0);
    var node = range.commonAncestorContainer;
    var el = node.nodeType === 1 ? node : node.parentElement;
    if (!isRoot(el)) return null;
    var text = range.toString().replace(/\s+/g, ' ').trim();
    if (!text) return null;
    var segments = rangeToHosts(range);
    if (!segments.length) return null;
    return { range: range, segments: segments };
  }

  function boundaryAt(host, pos, isEnd) {
    var walker = document.createTreeWalker(host, NodeFilter.SHOW_TEXT, null);
    var acc = 0, node;
    while ((node = walker.nextNode())) {
      var len = node.nodeValue.length;
      if (pos < acc + len) return { node: node, offset: pos - acc };
      if (pos === acc + len) {
        if (isEnd) return { node: node, offset: len };
        var next = walker.nextNode();
        if (next) return { node: next, offset: 0 };
        return { node: node, offset: len };
      }
      acc += len;
    }
    return null;
  }

  function wrapHostRange(host, start, end, color, bold) {
    if (!host || start < 0 || end <= start) return null;
    var sb = boundaryAt(host, start, false);
    var eb = boundaryAt(host, end, true);
    if (!sb || !eb) return null;
    var sn = sb.node, so = sb.offset, en = eb.node, eo = eb.offset;
    if (sn === en) {
      if (so > 0) { en = sn.splitText(so); eo -= so; sn = en; so = 0; }
      if (eo < en.nodeValue.length) en.splitText(eo);
    } else {
      if (so > 0) { sn = sn.splitText(so); so = 0; }
      if (eo < en.nodeValue.length) en.splitText(eo);
    }
    var range = document.createRange();
    range.setStart(sn, so);
    range.setEnd(en, eo);
    var span = document.createElement('span');
    span.className = 'hl-mark';
    span.id = 'hl-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 7);
    if (color) span.setAttribute('data-hl-color', color);
    if (bold) span.setAttribute('data-hl-bold', 'true');
    try {
      range.surroundContents(span);
    } catch (e) {
      try {
        var frag = range.extractContents();
        span.appendChild(frag);
        range.insertNode(span);
      } catch (e2) { return null; }
    }
    return span;
  }

  function unwrapMark(mark) {
    var parent = mark.parentNode;
    if (!parent) return;
    while (mark.firstChild) parent.insertBefore(mark.firstChild, mark);
    parent.removeChild(mark);
    parent.normalize();
  }

  function allMarks() {
    return qsa('.hl-mark').filter(function (m) { return isRoot(m); });
  }

  function previousDivider(el) {
    var n = el.previousElementSibling;
    while (n) {
      if (n.classList && n.classList.contains('act-divider')) return n;
      n = n.previousElementSibling;
    }
    return null;
  }

  function contextFor(mark) {
    var ctx = { speaker: '', time: '', act: '', role: '' };
    var turn = mark.closest('.turn-block');
    if (turn) {
      var badge = qs('.speaker-badge', turn);
      var time = qs('.turn-time', turn);
      ctx.speaker = badge ? badge.textContent.trim() : '';
      ctx.time = time ? time.textContent.trim() : '';
      ctx.role = turn.getAttribute('data-speaker') || '';
      var divider = previousDivider(turn);
      if (divider) {
        var t = qs('.act-title', divider);
        if (t) ctx.act = t.textContent.trim();
      }
      return ctx;
    }
    var sec = mark.closest('.essay-section');
    if (sec) {
      var tag = qs('.section-tag', sec);
      var st = qs('.section-time', sec);
      var stitle = qs('.section-title', sec);
      ctx.speaker = tag ? tag.textContent.trim() : '';
      ctx.time = st ? st.textContent.trim() : '';
      ctx.act = stitle ? stitle.textContent.trim() : '';
      return ctx;
    }
    if (mark.closest('.executive-card')) {
      ctx.speaker = '导读';
      ctx.act = '核心认知模型';
    }
    return ctx;
  }

  function markInfo(mark) {
    var host = mark.closest(HOST_SEL);
    if (!host || !isRoot(host)) host = mark.closest('.turn-content') || mark.parentElement;
    if (!host) return null;
    var start = offsetInHost(host, mark, 0);
    var end = offsetInHost(host, mark, mark.childNodes.length);
    if (start < 0 || end < start) return null;
    var ctx = contextFor(mark);
    return {
      id: mark.id || '',
      text: mark.textContent,
      color: mark.getAttribute('data-hl-color') || '',
      bold: mark.getAttribute('data-hl-bold') === 'true',
      hostIndex: hostIndexOf(host),
      start: start,
      end: end,
      speaker: ctx.speaker,
      time: ctx.time,
      act: ctx.act,
      role: ctx.role
    };
  }

  function overlapsAnyMark(segments) {
    return segments.some(function (seg) {
      return qsa('.hl-mark', seg.host).some(function (m) {
        var info = markInfo(m);
        return info && info.start < seg.end && info.end > seg.start;
      });
    });
  }

  function markForSegments(segments) {
    if (segments.length !== 1) return null;
    var seg = segments[0];
    var marks = qsa('.hl-mark', seg.host);
    for (var i = 0; i < marks.length; i++) {
      var info = markInfo(marks[i]);
      if (info && info.start <= seg.start && info.end >= seg.end) return marks[i];
    }
    return null;
  }

  function overlapsExisting(host, start, end) {
    return qsa('.hl-mark', host).some(function (m) {
      var info = markInfo(m);
      return info && info.start < end && info.end > start;
    });
  }

  function serialize() {
    return allMarks().map(markInfo).filter(Boolean);
  }

  function saveNow() {
    try { localStorage.setItem(storeKey(), JSON.stringify(serialize())); } catch (e) {}
  }

  function saveSoon() {
    window.clearTimeout(state.saveTimer);
    state.saveTimer = window.setTimeout(saveNow, 160);
  }

  function restore() {
    var raw = null;
    try { raw = localStorage.getItem(storeKey()); } catch (e) { return; }
    if (!raw) return;
    var items;
    try { items = JSON.parse(raw); } catch (e) { return; }
    if (!Array.isArray(items) || !items.length) return;
    var hosts = getHosts();
    var restored = 0;
    items.forEach(function (it) {
      if (!it || typeof it.start !== 'number' || typeof it.end !== 'number' || !it.text) return;
      var host = hosts[it.hostIndex];
      if (!host) return;
      if (overlapsExisting(host, it.start, it.end)) return;
      var actual = host.textContent.slice(it.start, it.end);
      if (actual !== it.text) {
        var idx = host.textContent.indexOf(it.text);
        if (idx < 0) return;
        it.start = idx;
        it.end = idx + it.text.length;
      }
      var span = wrapHostRange(host, it.start, it.end, it.color, it.bold);
      if (span) {
        if (it.id) span.id = it.id;
        restored += 1;
      }
    });
    if (restored) {
      renderDrawer();
      saveNow();
    }
  }

  function markActiveItem() {
    if (!els.list) return;
    qsa('.hl-item', els.list).forEach(function (card) {
      card.classList.toggle('is-active', card.getAttribute('data-hl-id') === state.activeId);
    });
  }

  function renderDrawer() {
    var infos = allMarks().map(markInfo).filter(Boolean);
    if (els.count) els.count.textContent = String(infos.length);
    if (els.clearAll) els.clearAll.disabled = infos.length === 0;
    var toggle = qs('#hl-drawer-toggle');
    if (toggle) toggle.textContent = '📝 标注清单 (' + infos.length + ')';
    if (!els.list) return;
    var f = state.filter;
    var shown = infos.filter(function (it) {
      if (f === 'all') return true;
      if (f === 'bold') return it.bold;
      return it.color === f;
    });
    els.list.innerHTML = '';
    if (!shown.length) {
      var empty = document.createElement('div');
      empty.className = 'hl-empty';
      empty.textContent = infos.length
        ? '当前筛选下没有标注。'
        : '还没有标注。\n选中正文任意句子，即可加粗或标记背景色。';
      els.list.appendChild(empty);
      return;
    }
    shown.forEach(function (it) {
      var card = document.createElement('div');
      card.className = 'hl-item ' + (it.color ? 'c-' + it.color : 'c-bold');
      card.setAttribute('data-hl-id', it.id);
      card.setAttribute('role', 'button');
      card.setAttribute('tabindex', '0');

      var head = document.createElement('div');
      head.className = 'hl-item-head';
      var badge = document.createElement('span');
      badge.className = 'hl-badge' + (it.role === 'host' ? ' host' : '');
      badge.textContent = it.speaker || '标注';
      head.appendChild(badge);
      if (it.time) {
        var time = document.createElement('span');
        time.className = 'hl-time';
        time.textContent = it.time;
        head.appendChild(time);
      }
      var rm = document.createElement('button');
      rm.type = 'button';
      rm.className = 'hl-item-remove';
      rm.title = '移除这条标注';
      rm.textContent = '✕';
      rm.addEventListener('click', function (e) {
        e.stopPropagation();
        removeMarkById(it.id);
      });
      head.appendChild(rm);

      var text = document.createElement('div');
      text.className = 'hl-item-text';
      text.textContent = it.text;

      card.appendChild(head);
      card.appendChild(text);
      if (it.act) {
        var act = document.createElement('div');
        act.className = 'hl-item-act';
        act.textContent = it.act;
        card.appendChild(act);
      }
      card.addEventListener('click', function () { jumpTo(it.id); });
      card.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          jumpTo(it.id);
        }
      });
      els.list.appendChild(card);
    });
    markActiveItem();
  }

  function jumpTo(id) {
    var mark = document.getElementById(id);
    if (!mark) return;
    var block = mark.closest('.turn-block');
    if (block && block.classList.contains('hidden')) {
      var allBtn = qs('.filter-btn[data-filter="all"]');
      if (allBtn) allBtn.click();
      else qsa('.turn-block').forEach(function (b) { b.classList.remove('hidden'); });
    }
    state.activeId = id;
    mark.scrollIntoView({ behavior: 'smooth', block: 'center' });
    mark.classList.remove('hl-pulse');
    void mark.offsetWidth;
    mark.classList.add('hl-pulse');
    window.setTimeout(function () { mark.classList.remove('hl-pulse'); }, 1900);
    markActiveItem();
    if (window.innerWidth < 1280) setDrawer(false);
  }

  function removeMarkById(id) {
    var mark = document.getElementById(id);
    if (!mark) return;
    var info = markInfo(mark);
    unwrapMark(mark);
    hidePopover();
    if (info) {
      state.undoBatch = null;
      state.undo = info;
      showToast('已移除 1 条标注', true);
    }
    renderDrawer();
    saveSoon();
  }

  function clearAllMarks() {
    var marks = allMarks();
    if (!marks.length) {
      showToast('还没有标注', false);
      return;
    }
    var infos = marks.map(markInfo).filter(Boolean);
    marks.forEach(unwrapMark);
    hidePopover();
    state.undo = null;
    state.undoBatch = infos;
    showToast('已清空 ' + infos.length + ' 条标注', true);
    renderDrawer();
    saveSoon();
  }

  function restoreInfo(item, hosts) {
    var host = hosts[item.hostIndex];
    if (!host) return false;
    if (host.textContent.slice(item.start, item.end) !== item.text) {
      var idx = host.textContent.indexOf(item.text);
      if (idx < 0) return false;
      item.start = idx;
      item.end = idx + item.text.length;
    }
    return !!wrapHostRange(host, item.start, item.end, item.color, item.bold);
  }

  function undoRemove() {
    var batch = state.undoBatch;
    var item = state.undo;
    state.undo = null;
    state.undoBatch = null;
    hideToast();
    if (batch && batch.length) {
      var hosts = getHosts();
      var restored = 0;
      batch.forEach(function (it) {
        if (restoreInfo(it, hosts)) restored += 1;
      });
      if (restored) {
        renderDrawer();
        saveSoon();
      }
      return;
    }
    if (item && restoreInfo(item, getHosts())) {
      renderDrawer();
      saveSoon();
    }
  }

  function showToast(msg, withUndo) {
    if (!els.toast) return;
    if (!withUndo) {
      state.undo = null;
      state.undoBatch = null;
    }
    if (els.toastMsg) els.toastMsg.textContent = msg;
    if (els.undo) els.undo.hidden = !withUndo;
    els.toast.classList.add('show');
    window.clearTimeout(state.toastTimer);
    state.toastTimer = window.setTimeout(hideToast, 5000);
  }

  function hideToast() {
    if (els.toast) els.toast.classList.remove('show');
  }

  function markdownExcerpt() {
    var infos = allMarks().map(markInfo).filter(Boolean);
    return infos.map(function (it, i) {
      var meta = [it.speaker, it.time].filter(Boolean).join(' · ');
      var body = it.bold ? '**' + it.text + '**' : it.text;
      return (i + 1) + '. ' + body + (meta ? '（' + meta + '）' : '');
    }).join('\n');
  }

  function fallbackCopy(text, done) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); done(); } catch (e) {}
    ta.remove();
  }

  function copyMarkdown() {
    var text = markdownExcerpt();
    if (!text) { showToast('还没有可复制的标注', false); return; }
    function done() { showToast('已复制 ' + text.split('\n').length + ' 条摘录', false); }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { fallbackCopy(text, done); });
    } else {
      fallbackCopy(text, done);
    }
  }

  function showPopover(pending) {
    var pop = els.popover;
    if (!pop) return;
    var existing = pending.existing;
    var rect = pending.rect;
    qsa('.hl-sw', pop).forEach(function (b) { b.classList.remove('active'); });
    var boldBtn = qs('[data-action="bold"]', pop);
    var clearBtn = qs('[data-action="clear"]', pop);
    if (existing) {
      if (existing.getAttribute('data-hl-bold') === 'true') boldBtn.classList.add('active');
      var c = existing.getAttribute('data-hl-color');
      if (c) {
        var sw = qs('[data-color="' + c + '"]', pop);
        if (sw) sw.classList.add('active');
      }
      clearBtn.disabled = false;
      clearBtn.title = '清空当前标记的加粗与背景色';
    } else {
      clearBtn.disabled = true;
      clearBtn.title = '选中已有标注后可清空';
    }
    pop.classList.add('show');
    var pw = pop.offsetWidth;
    var ph = pop.offsetHeight;
    var left = rect.left + rect.width / 2;
    left = Math.max(8 + pw / 2, Math.min(left, window.innerWidth - 8 - pw / 2));
    var below = false;
    var top = rect.top - 10;
    if (top - ph < 8) {
      top = rect.bottom + 10;
      below = true;
    }
    pop.style.left = left + 'px';
    pop.style.top = top + 'px';
    pop.classList.toggle('below', below);
  }

  function hidePopover() {
    if (els.popover) {
      els.popover.classList.remove('show');
      els.popover.classList.remove('below');
    }
    state.pending = null;
  }

  function finishEdit() {
    var sel = window.getSelection();
    if (sel) sel.removeAllRanges();
    hidePopover();
    renderDrawer();
    saveSoon();
  }

  function applyBold() {
    var p = state.pending;
    if (!p) return;
    if (p.existing) {
      var mark = p.existing;
      if (mark.getAttribute('data-hl-bold') === 'true') {
        mark.removeAttribute('data-hl-bold');
        if (!mark.getAttribute('data-hl-color')) unwrapMark(mark);
      } else {
        mark.setAttribute('data-hl-bold', 'true');
      }
    } else {
      p.segments.forEach(function (seg) {
        wrapHostRange(seg.host, seg.start, seg.end, null, true);
      });
    }
    finishEdit();
  }

  function applyColor(color) {
    var p = state.pending;
    if (!p) return;
    if (p.existing) {
      var mark = p.existing;
      if ((mark.getAttribute('data-hl-color') || '') === color) mark.removeAttribute('data-hl-color');
      else mark.setAttribute('data-hl-color', color);
      if (!mark.getAttribute('data-hl-color') && mark.getAttribute('data-hl-bold') !== 'true') {
        unwrapMark(mark);
      }
    } else {
      p.segments.forEach(function (seg) {
        wrapHostRange(seg.host, seg.start, seg.end, color, false);
      });
    }
    finishEdit();
  }

  function removePending() {
    var p = state.pending;
    if (!p || !p.existing) {
      showToast('当前选区没有可清空的标注', false);
      return;
    }
    var id = p.existing.id;
    hidePopover();
    removeMarkById(id);
  }

  function onSelectionEnd(e) {
    if (e && e.target && e.target.closest) {
      if (
        e.target.closest('#hl-popover') ||
        e.target.closest('#hl-drawer') ||
        e.target.closest('#hl-title-modal') ||
        e.target.closest('.reader-toolbar')
      ) return;
    }
    var sel = currentSelection();
    if (!sel) {
      if (e && e.target && e.target.closest && e.target.closest('.hl-mark')) return;
      hidePopover();
      return;
    }
    var existing = markForSegments(sel.segments);
    if (!existing && overlapsAnyMark(sel.segments)) {
      hidePopover();
      showToast('选区与已有标注重叠，请缩小选择范围', false);
      return;
    }
    state.pending = {
      segments: sel.segments,
      existing: existing,
      rect: sel.range.getBoundingClientRect()
    };
    showPopover(state.pending);
  }

  function setDrawer(open) {
    document.body.classList.toggle('hl-drawer-open', !!open);
    if (els.drawer) els.drawer.setAttribute('aria-hidden', open ? 'false' : 'true');
    var btn = qs('#hl-drawer-toggle');
    if (btn) btn.classList.toggle('active', !!open);
    if (open) renderDrawer();
  }

  function openTitleModal() {
    if (!els.titleModal || !els.titleInput) return;
    hidePopover();
    els.titleInput.value = document.title || ORIG_TITLE;
    if (els.titleOrig) els.titleOrig.textContent = ORIG_TITLE || document.title;
    if (els.titleReset) els.titleReset.disabled = !ORIG_TITLE || document.title === ORIG_TITLE;
    els.titleModal.classList.add('show');
    els.titleModal.setAttribute('aria-hidden', 'false');
    window.setTimeout(function () {
      els.titleInput.focus();
      els.titleInput.select();
    }, 0);
  }

  function closeTitleModal() {
    if (!els.titleModal) return;
    els.titleModal.classList.remove('show');
    els.titleModal.setAttribute('aria-hidden', 'true');
  }

  function saveCustomTitle() {
    if (!els.titleInput) return;
    var val = (els.titleInput.value || '').replace(/[\r\n]+/g, ' ').trim();
    if (!val) {
      showToast('标签名不能为空；如需还原请点击「恢复默认」', false);
      els.titleInput.focus();
      return;
    }
    if (ORIG_TITLE && val === ORIG_TITLE) {
      resetCustomTitle();
      return;
    }
    try { localStorage.setItem(titleStoreKey(), val); } catch (e) {}
    applyDocumentTitle(val);
    closeTitleModal();
    showToast('标签名已更新，刷新仍保留（「保存含标记 HTML」可写入文件）', false);
  }

  function resetCustomTitle() {
    if (!ORIG_TITLE) {
      closeTitleModal();
      return;
    }
    try {
      if (INITIAL_DOM_TITLE === ORIG_TITLE) localStorage.removeItem(titleStoreKey());
      else localStorage.setItem(titleStoreKey(), ORIG_TITLE);
    } catch (e) {}
    applyDocumentTitle(ORIG_TITLE);
    closeTitleModal();
    showToast('已恢复默认标签名', false);
  }

  function bindTitleModal() {
    if (!els.titleModal || els.titleModal.__hlBound) return;
    els.titleModal.__hlBound = true;
    els.titleModal.addEventListener('click', function (e) {
      if (e.target === els.titleModal) closeTitleModal();
    });
    if (els.titleCancel) els.titleCancel.addEventListener('click', closeTitleModal);
    if (els.titleConfirm) els.titleConfirm.addEventListener('click', saveCustomTitle);
    if (els.titleReset) els.titleReset.addEventListener('click', resetCustomTitle);
    if (els.titleInput) {
      els.titleInput.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
          e.preventDefault();
          saveCustomTitle();
        }
      });
    }
  }

  function bindPopover() {
    if (!els.popover) return;
    els.popover.addEventListener('mousedown', function (e) { e.preventDefault(); });
    els.popover.addEventListener('click', function (e) {
      var btn = e.target.closest('button');
      if (!btn) return;
      e.preventDefault();
      e.stopPropagation();
      var action = btn.getAttribute('data-action');
      if (action === 'bold') applyBold();
      else if (action === 'clear') removePending();
      else {
        var c = btn.getAttribute('data-color');
        if (c) applyColor(c);
      }
    });
  }

  function bindDrawer() {
    var toggle = qs('#hl-drawer-toggle');
    if (toggle && !toggle.__hlBound) {
      toggle.__hlBound = true;
      toggle.addEventListener('click', function () {
        setDrawer(!document.body.classList.contains('hl-drawer-open'));
      });
    }
    if (els.close && !els.close.__hlBound) {
      els.close.__hlBound = true;
      els.close.addEventListener('click', function () { setDrawer(false); });
    }
    qsa('.hl-fchip').forEach(function (chip) {
      if (chip.__hlBound) return;
      chip.__hlBound = true;
      chip.addEventListener('click', function () {
        state.filter = chip.getAttribute('data-hl-filter') || 'all';
        qsa('.hl-fchip').forEach(function (c) { c.classList.toggle('active', c === chip); });
        renderDrawer();
      });
    });
    if (els.copy && !els.copy.__hlBound) {
      els.copy.__hlBound = true;
      els.copy.addEventListener('click', copyMarkdown);
    }
    if (els.undo && !els.undo.__hlBound) {
      els.undo.__hlBound = true;
      els.undo.addEventListener('click', undoRemove);
    }
    if (els.clearAll && !els.clearAll.__hlBound) {
      els.clearAll.__hlBound = true;
      els.clearAll.addEventListener('click', clearAllMarks);
    }
  }

  function ensureToolbarButtons() {
    var bar = qs('.reader-toolbar-inner');
    if (!bar) return;
    var existingToggle = qs('#hl-drawer-toggle');
    var existingRename = qs('#hl-rename-title');
    var existingSave = qs('#hl-save-html');
    if (existingToggle) {
      var hostGroup = existingToggle.parentElement || bar;
      if (!existingRename) {
        var rBtn = document.createElement('button');
        rBtn.type = 'button';
        rBtn.id = 'hl-rename-title';
        rBtn.className = 'hl-tool-btn';
        rBtn.textContent = '🏷️ 改标签名';
        rBtn.title = '自定义 Chrome 标签页标题（只改标签名，不改正文主标题）';
        if (existingSave && existingSave.parentElement === hostGroup) {
          hostGroup.insertBefore(rBtn, existingSave);
        } else {
          hostGroup.appendChild(rBtn);
        }
        existingRename = rBtn;
      }
      if (!existingRename.__hlBound) {
        existingRename.__hlBound = true;
        existingRename.addEventListener('click', openTitleModal);
      }
      if (existingSave && !existingSave.__hlBound) {
        existingSave.__hlBound = true;
        existingSave.addEventListener('click', saveHtml);
      }
      updateRenameBtnState();
      return;
    }
    var group = document.createElement('div');
    group.className = 'toolbar-group hl-toolbar-group';
    var b1 = document.createElement('button');
    b1.type = 'button';
    b1.id = 'hl-drawer-toggle';
    b1.className = 'hl-tool-btn';
    b1.textContent = '📝 标注清单 (0)';
    var b2 = document.createElement('button');
    b2.type = 'button';
    b2.id = 'hl-rename-title';
    b2.className = 'hl-tool-btn';
    b2.textContent = '🏷️ 改标签名';
    b2.title = '自定义 Chrome 标签页标题（只改标签名，不改正文主标题）';
    var b3 = document.createElement('button');
    b3.type = 'button';
    b3.id = 'hl-save-html';
    b3.className = 'hl-tool-btn';
    b3.textContent = '💾 保存含标记 HTML';
    group.appendChild(b1);
    group.appendChild(b2);
    group.appendChild(b3);
    bar.appendChild(group);
    b2.__hlBound = true;
    b2.addEventListener('click', openTitleModal);
    b3.__hlBound = true;
    b3.addEventListener('click', saveHtml);
    updateRenameBtnState();
  }

  function resetUiForExport(clone) {
    var pop = clone.querySelector('#hl-popover');
    if (pop) {
      pop.classList.remove('show');
      pop.classList.remove('below');
      pop.removeAttribute('style');
    }
    var modal = clone.querySelector('#hl-title-modal');
    if (modal) {
      modal.classList.remove('show');
      modal.setAttribute('aria-hidden', 'true');
    }
    var tInput = clone.querySelector('#hl-title-input');
    if (tInput) tInput.removeAttribute('value');
    var titleClone = clone.querySelector('title');
    if (titleClone) {
      titleClone.textContent = document.title || ORIG_TITLE;
      if (ORIG_TITLE) titleClone.setAttribute('data-orig-title', ORIG_TITLE);
    }
    var toast = clone.querySelector('#hl-toast');
    if (toast) toast.classList.remove('show');
    var undo = clone.querySelector('#hl-undo');
    if (undo) undo.hidden = true;
    var list = clone.querySelector('#hl-list');
    if (list) list.innerHTML = '';
    var drawer = clone.querySelector('#hl-drawer');
    if (drawer) drawer.setAttribute('aria-hidden', 'true');
    var body = clone.querySelector('body');
    if (body) body.classList.remove('hl-drawer-open');
    Array.prototype.forEach.call(clone.querySelectorAll('.hl-pulse'), function (el) {
      el.classList.remove('hl-pulse');
    });
    Array.prototype.forEach.call(clone.querySelectorAll('.is-active'), function (el) {
      el.classList.remove('is-active');
    });
    Array.prototype.forEach.call(clone.querySelectorAll('.hl-fchip'), function (c) {
      c.classList.toggle('active', c.getAttribute('data-hl-filter') === 'all');
    });
    var toggle = clone.querySelector('#hl-drawer-toggle');
    if (toggle) toggle.classList.remove('active');
  }

  async function saveHtml() {
    hidePopover();
    closeTitleModal();
    var clone = document.documentElement.cloneNode(true);
    resetUiForExport(clone);
    var html = '<!DOCTYPE html>\n' + clone.outerHTML;
    var rawBase = (document.title || '精读本').split('｜')[0].trim() || '精读本';
    var base = rawBase.replace(/[\\/:*?"<>|]/g, '_').replace(/\s+/g, ' ').trim() || '精读本';
    var name = base + '_已标注.html';
    if (window.showSaveFilePicker) {
      try {
        var handle = await window.showSaveFilePicker({
          suggestedName: name,
          types: [{ description: 'HTML 文件', accept: { 'text/html': ['.html'] } }]
        });
        var writable = await handle.createWritable();
        await writable.write(new Blob([html], { type: 'text/html;charset=utf-8' }));
        await writable.close();
        showToast('已保存含标记与当前标签名的 HTML', false);
        return;
      } catch (err) {
        if (err && (err.name === 'AbortError' || err.name === 'NotAllowedError')) return;
      }
    }
    var blob = new Blob([html], { type: 'text/html;charset=utf-8' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.setTimeout(function () { URL.revokeObjectURL(url); }, 5000);
    showToast('已导出 ' + name, false);
  }

  function init() {
    if (!document.querySelector(READ_ROOT)) return;
    els.popover = qs('#hl-popover');
    els.drawer = qs('#hl-drawer');
    els.close = qs('#hl-drawer-close');
    els.list = qs('#hl-list');
    els.count = qs('#hl-count');
    els.copy = qs('#hl-copy-md');
    els.clearAll = qs('#hl-clear-all');
    els.toast = qs('#hl-toast');
    els.toastMsg = qs('#hl-toast-msg');
    els.undo = qs('#hl-undo');
    els.titleModal = qs('#hl-title-modal');
    els.titleInput = qs('#hl-title-input');
    els.titleOrig = qs('#hl-title-orig-text');
    els.titleReset = qs('#hl-title-reset');
    els.titleCancel = qs('#hl-title-cancel');
    els.titleConfirm = qs('#hl-title-confirm');
    if (!els.popover || !els.drawer) return;
    ensureToolbarButtons();
    bindPopover();
    bindDrawer();
    bindTitleModal();
    restore();
    renderDrawer();
    document.addEventListener('mouseup', function (e) {
      window.setTimeout(function () { onSelectionEnd(e); }, 0);
    });
    document.addEventListener('keyup', function (e) {
      if (e.shiftKey || e.key === 'Shift') {
        window.setTimeout(function () { onSelectionEnd(e); }, 0);
      }
    });
    document.addEventListener('mousedown', function (e) {
      if (!e.target.closest || !e.target.closest('#hl-popover')) {
        if (!e.target.closest('.hl-mark')) hidePopover();
      }
    });
    document.addEventListener('click', function (e) {
      var mark = e.target.closest ? e.target.closest('.hl-mark') : null;
      if (!mark) return;
      state.pending = { segments: null, existing: mark, rect: mark.getBoundingClientRect() };
      showPopover(state.pending);
    });
    window.addEventListener('scroll', function () {
      if (els.popover && els.popover.classList.contains('show')) hidePopover();
    }, { passive: true });
    window.addEventListener('resize', hidePopover);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        if (els.titleModal && els.titleModal.classList.contains('show')) closeTitleModal();
        else if (els.popover && els.popover.classList.contains('show')) hidePopover();
        else setDrawer(false);
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
/* === /HL-ANNOTATION-JS === */
"""


def inject_annotation_engine(html: str) -> str:
    """把标注引擎幂等注入到精读本 HTML（无 </style>/</head>/</body> 时安全兜底）。"""
    if "HL-ANNOTATION-JS" in html:
        return html
    if "</style>" in html:
        html = html.replace("</style>", ANNOTATION_CSS + "\n  </style>", 1)
    elif "</head>" in html:
        html = html.replace("</head>", "<style>" + ANNOTATION_CSS + "</style>\n</head>", 1)
    payload = ANNOTATION_UI_HTML + "\n<script>\n" + ANNOTATION_JS + "\n</script>\n"
    if "</body>" in html:
        html = html.replace("</body>", payload + "</body>", 1)
    else:
        html += payload
    return html


def strip_annotation_engine(html: str) -> str:
    """移除已注入的 CSS + UI + JS 载荷，供 --force-inject 升级旧版引擎（兼容模板内嵌与外挂注入双形态）。"""
    html = re.sub(
        r"\n?[ \t]*/\* === HL-ANNOTATION-CSS === \*/.*?</style>",
        "</style>",
        html,
        flags=re.S,
    )
    html = re.sub(
        r"\n?<!-- === HL-ANNOTATION-UI === -->.*?<script>\s*/\* === HL-ANNOTATION-JS === \*/.*?</script>[ \t]*\n?",
        "",
        html,
        flags=re.S,
    )
    html = re.sub(
        r"\n?[ \t]*/\* === HL-ANNOTATION-JS === \*/.*?/\* === /HL-ANNOTATION-JS === \*/[ \t]*\n?",
        "\n",
        html,
        flags=re.S,
    )
    html = re.sub(
        r"\n?[ \t]*/\* === HL-ANNOTATION-JS === \*/.*?\}\)\(\);[ \t]*\n?",
        "\n",
        html,
        flags=re.S,
    )
    html = re.sub(
        r"\n?<!-- === HL-ANNOTATION-UI === -->.*?<!-- === /HL-ANNOTATION-UI === -->[ \t]*\n?",
        "\n",
        html,
        flags=re.S,
    )
    html = re.sub(
        r'\n?<!-- === HL-ANNOTATION-UI === -->.*?<div id="hl-toast"[^>]*>.*?</div>[ \t]*\n?',
        "\n",
        html,
        flags=re.S,
    )
    return html
