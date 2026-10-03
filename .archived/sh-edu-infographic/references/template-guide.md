# 高考教辅/知识手账设计规范与完整 HTML 模板

本参考手册供 `sh-edu-infographic` 技能在生成教学图解、学科知识手账卡、公式图解或概念卡片时按需查阅。

## 1. 核心配色体系 (Design Tokens)

```css
:root {
  /* 背景与主卡 */
  --bg-page: #e2e8f0;            /* 页面背景（柔和灰蓝） */
  --bg-card: #ffffff;            /* 卡片主体 */
  --border-primary: #0284c7;     /* 主卡边框（高饱和天蓝，2.5px solid） */
  --border-section: #38bdf8;     /* 内部区块边框（1.5px solid） */
  
  /* 头部 Header */
  --header-bg: #f0f9ff;          /* 头部微底（极浅冰蓝） */
  --header-border: #0284c7;      /* 头部框线 */
  --header-title: #0f172a;       /* 标题深黑板岩 */
  --header-subtitle: #475569;    /* 副标题灰 */
  --header-accent: #0284c7;      /* 标语手写蓝 */

  /* 语义色族 1：激进/升/氧化/酸性/热（深红体系） */
  --red-main: #ef4444;           /* 实心胶囊底色 */
  --red-border: #f87171;         /* 区块边框 */
  --red-light-bg: #fff5f5;       /* 浅底色块 */
  --red-text: #991b1b;           /* 强调深色文字 */

  /* 语义色族 2：保守/降/还原/碱性/冷（翠绿体系） */
  --green-main: #10b981;         /* 实心胶囊底色 */
  --green-border: #34d399;       /* 区块边框 */
  --green-light-bg: #f0fdf4;     /* 浅底色块 */
  --green-text: #065f46;         /* 强调深色文字 */

  /* 语义色族 3：中间态/产物/转化/警告（暖琥珀体系） */
  --amber-main: #f59e0b;         /* 实心胶囊底色 */
  --amber-border: #fcd34d;       /* 区块边框 */
  --amber-light-bg: #fffbeb;     /* 浅底色块 */
  --amber-text: #92400e;         /* 强调深色文字 */

  /* 语义色族 4：转移/介质/能量/桥接（典雅紫体系） */
  --purple-main: #7e22ce;        /* 实心胶囊底色 */
  --purple-border: #c084fc;      /* 区块边框 */
  --purple-light-bg: #faf5ff;    /* 浅底色块 */
  --purple-text: #581c87;        /* 强调深色文字 */
}
```

## 2. 经典排版组件模版

### 2.1 头部 Header（含手绘 SVG 图标 + 倾斜手写感标语）
```html
<div class="header-box">
  <div class="header-left">
    <!-- 手绘风格仪器或学科标志性 SVG -->
    <svg class="flask-icon" viewBox="0 0 60 70" fill="none">
      <path d="M22 6 L38 6 M30 6 L30 22 L48 56 C50 60 46 64 40 64 L20 64 C14 64 10 60 12 56 L30 22" 
            stroke="#0284c7" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M16 52 C20 48 28 56 34 50 C38 46 42 50 44 48" 
            stroke="#38bdf8" stroke-width="2.5" stroke-linecap="round"/>
      <circle cx="24" cy="40" r="3" fill="#38bdf8"/>
      <circle cx="34" cy="34" r="2" fill="#0284c7"/>
    </svg>
    <div class="title-content">
      <h1>氧化还原反应 · 核心图解与记忆精要</h1>
      <p>高中化学必修一 · 模块核心突破卡</p>
    </div>
  </div>
  <div class="header-tag">化学让世界<br>更有规律！✨</div>
</div>
```

### 2.2 流程链条节点与连接符
```html
<div class="chain-flow">
  <div class="chain-node">
    <div class="node-main">
      <div class="node-badge">失</div>
      <div class="node-sub">失去电子 (偏离)</div>
    </div>
  </div>
  <div class="arrow-sym">➜</div>
  <div class="chain-node">
    <div class="node-main">
      <div class="node-badge">升</div>
      <div class="node-sub">化合价升高</div>
    </div>
  </div>
  <div class="arrow-sym">➜</div>
  <div class="chain-node">
    <div class="node-main">
      <div class="node-badge">氧化</div>
      <div class="node-sub">被氧化 / 氧化反应</div>
    </div>
  </div>
</div>
```

### 2.3 底部总结卡（三列对称暖框）
```html
<div class="summary-box">
  <div class="summary-head">
    <span class="gold-badge">★ 核心规律总结</span>
    <span class="summary-sub">牢记三大铁律，秒杀解题</span>
  </div>
  <div class="summary-grid">
    <div class="summary-col">
      <div class="col-num">01</div>
      <div class="col-title">左上右下</div>
      <div class="col-desc">强氧化剂与强还原剂优先反应，强制弱生成弱。</div>
    </div>
    <div class="summary-col">
      <div class="col-num">02</div>
      <div class="col-title">垂直对应</div>
      <div class="col-desc">上排反应物产物必在下排垂直正对应位置。</div>
    </div>
    <div class="summary-col">
      <div class="col-num">03</div>
      <div class="col-title">远者优先</div>
      <div class="col-desc">氧化性与还原性差值越大（距离越远），越先发生反应。</div>
    </div>
  </div>
</div>
```
