# 前端去 AI 味资源清单

配套 sh-frontend-deai，按需查阅，不必每次全读。链接均为外部资源，失效时按名称搜索最新地址。

## 网站模板（无参考时的起步骨架）

| 站点 | 地址 | 特点 |
|---|---|---|
| HTML5 UP | html5up.net | 免费响应式网站合集，极简风格 |
| WordPress 主题库 | cn.wordpress.org/themes/ | 1 万+ 免费主题 |
| Start Bootstrap | startbootstrap.com | Bootstrap 生态免费模板 |
| Colorlib | colorlib.com/wp/free-wordpress-themes/ | 设计精美的免费模板 |

## 设计优先工具（先 Demo 后开发）

大项目不要直接梭哈：先产出纯静态 Demo，设计确认后再按同一风格开发完整项目，避免方向错误后大规模返工。

- Google Stitch（stitch.withgoogle.com）：输入描述生成专业界面原型，草图拍照也能转代码
- Figma + Figma MCP（github.com/GLips/Figma-Context-MCP）：先设计稿后生成代码
- Onlook（onlook.ai）：可视化直接编辑网页代码
- Screenshot to Code（github.com/abi/screenshot-to-code）：截图转代码，转出结果作为风格参考喂给 AI

## 图片系统

| 用途 | 资源 | 说明 |
|---|---|---|
| 功能图标 | Iconify（iconify.design） | 20 万+ 免费矢量图标，统一图标语言 |
| 占位图 | Picsum Photos（picsum.photos） | URL 指定尺寸即得真实照片：`picsum.photos/800/400` |
| 真实照片 | Pexels（pexels.com） | 免费高质量图库，有 API |
| SVG 插画 | unDraw（undraw.co） | 免费插画，可自定义颜色，改成站点主色后融入整体 |

## 配色工具

- Coolors（coolors.co）：按空格随机生成配色，支持多格式导出；适合快速跳出默认色板
- Adobe Color（color.adobe.com）：Adobe 官方专业配色（互补/三角/类比规则）

生成后把具体色值写进设计约束，让 AI 严格执行。

## 反 AI 味组件库

需要组件库时优先这些有性格的选择。小众库 AI 容易记错用法：先查官方文档或用 Context7 插件，再写代码。

| 库 | 地址 | 风格 |
|---|---|---|
| Aceternity UI | ui.aceternity.com | 闪光粒子、极光背景、流星效果 |
| Magic UI | magicui.design | 150+ 动画组件、流光边框、文字渐变 |
| DaisyUI | daisyui.com | 30+ 主题（cyberpunk / retro / cupcake 等） |
| Brutalist UI | brutalistui.site | 粗野主义：粗边框、硬阴影、高对比 |
| Glass UI | ui.glass | 玻璃拟态 |
| ikun-ui | github.com/ikun-svelte/ikun-ui | Svelte + UnoCSS |
| Radix UI | radix-ui.com | 无样式原语，样式完全自定义 |
| Mantine | mantine.dev | 100+ 组件 |

## 现成 Agent Skills（可安装的配套技能）

- Anthropic 官方 frontend-design：github.com/anthropics/skills/tree/main/skills/frontend-design
  - Claude Code 安装：`/plugin marketplace add anthropics/skills` → `/plugin install example-skills@anthropic-agent-skills`
- UI UX Pro Max：github.com/nextlevelbuilder/ui-ux-pro-max-skill
  - 安装：`npm install -g uipro-cli` → 项目内 `uipro init --ai cursor`

## 组合实战案例（源自鱼皮，示范方法怎么组合）

1. 个人技术博客：AGENTS.md 设计规则 + UI UX Pro Max → 极客范
2. SaaS 落地页：AGENTS.md + UI UX Pro Max + 语境注入（《黑客帝国》红蓝药丸）+ Aceternity UI → 代码雨背景
3. 健身 App 落地页（移动端）：AGENTS.md + UI UX Pro Max + ikun-ui
