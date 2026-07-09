# 前端整站重新美化

## Goal

将 `apps/web` 前端整站重构为统一、专业、数据密集的金融研究工作台，提升视觉一致性、信息扫读效率、响应式质量和可访问性。

本任务聚焦前端界面和交互体验：全局壳层、主题 token、页面标题/KPI 区、表格/卡片/状态样式、图表容器、导航、移动端适配和中英文文案一致性。除非为展示已有数据所必需，不扩展后端 API 或产品功能。

## Product Decision

用户已选择“专业金融终端密度优先”作为整站重美化方向。

- Dark mode 是重点打磨对象，但必须保留 light mode 可用性和 WCAG AA 对比度。
- 桌面端优先体现紧凑表格、低装饰、强数据层级、清晰状态色和高扫读效率。
- 移动端保留核心可用性与导航可达性，可以适当降低次要指标密度。
- 不采用营销式 landing page 或大面积留白的现代 SaaS 风格作为主方向。

## Background

- 用户明确希望“彻底重新重构或者重新编写，优化前端网站界面”，并已同意进入 Trellis 任务规划。
- 用户已确认采用推荐的专业金融终端密度优先方向。
- 前端是 Next.js App Router 应用，位于 `apps/web`，使用 Server Components、Server Actions、route handlers、`next-intl`、shadcn-style primitives、Tailwind CSS、Vitest + Testing Library；规范见 `.trellis/spec/frontend/index.md:9-20`。
- 全局布局已经包含 `TopNavBar`、`SidebarNavigation`、`MobileNavigation`、`Breadcrumbs` 和 `BackendStatusBanner`，主内容区在 `apps/web/app/[locale]/layout.tsx:54-64`。
- 主导航覆盖 Dashboard、Instruments、AI Research、Macro Research、Watchlist、Portfolios、Reports、Alerts、Task Runs、Settings，导航项和中英文文案分别见 `apps/web/components/navigation-items.ts:5-51`、`apps/web/messages/en.json:3-12`、`apps/web/messages/zh.json:3-12`。
- 当前全局主题仍接近默认 shadcn slate token：`globals.css` 定义基础 HSL token 和 `--radius: 0.5rem`，Tailwind 通过 CSS variables 暴露颜色和 radius，见 `apps/web/app/globals.css:7-49`、`apps/web/tailwind.config.ts:4-56`。
- 现有 `FinancialPageHeader` 提供紧凑金融页头和指标条，见 `apps/web/components/financial-page-header.tsx:37-49`。它目前只在 Watchlist、Settings、Instrument Detail 等局部使用，见 `apps/web/app/[locale]/watchlist/page.tsx:121`、`apps/web/app/[locale]/settings/page.tsx:33`、`apps/web/components/instrument-detail-client.tsx:154`。
- 多个核心页面仍使用普通 `<h1>` + Card/Table 组合，包括 Instruments、Reports、Alerts、Portfolios、Task Runs、Evidence 等；证据见 `research/frontend-redesign-current-state.md`。
- UI/UX Pro Max 已生成金融仪表盘设计系统研究，定位为 `Financial Dashboard`，推荐 `Data-Dense Dashboard`、密度 `8/10`、平衡现代风格、标准动效；见 `research/ui-ux-pro-max/design-system/stock-analysis-platform/MASTER.md:11-12`、`:164`、`:214-227`。
- 已归档的 `07-03-frontend-ui-polish` 完成了局部金融化与证据闭环；仍进行中的 `07-03-professional-financial-dashboard` 跟踪更深的专业终端/数据能力差距。当前任务不替代专业终端路线，而是做整站视觉系统统一。

## Requirements

### R1. 全局金融设计系统

- 将当前默认 slate/shadcn token 整理为更适合金融研究工作台的 semantic token：背景、surface、panel、border、muted、accent、positive、negative、warning、info、chart 系列、focus ring。
- 保留 light/dark mode，并分别验证对比度；不允许只在一个主题下看起来可用。
- 建立紧凑 spacing、radius、border、shadow/elevation、数字字体、表格行高和图表容器规则。
- 新增样式应优先通过 token、共享组件和 Tailwind utility 组合表达，避免每个页面重复 raw hex 或一次性视觉规则。

### R2. 全局壳层和导航重构

- 优化顶部导航、侧边导航和移动端导航，使其更像金融工作台：紧凑、可扫读、状态清晰，搜索和常用动作优先。
- 桌面侧边栏应支持多项导航的清晰 active state；移动端不能产生横向页面溢出或遮挡主内容。
- 固定导航、主内容滚动区、底部移动导航之间要有稳定的 spacing 和 safe-area 预留。

### R3. 整站页面标题和指标区统一

- 将所有核心页面统一到 `FinancialPageHeader` 或其升级版：Dashboard、Instruments、AI Research、Evidence、Watchlist、Portfolios、Reports、Report Detail、Alerts、Task Runs、Task Run Detail、Settings、Instrument Detail。
- 每个页面应有可扫读的 title、description、status badges、关键 metrics、主要 actions；不能混用大号普通 H1、装饰性 hero 和不一致卡片标题。
- 页面标题/指标区必须保持响应式可用，长中英文文本不能挤出容器。

### R4. 数据表格、卡片和状态模式统一

- 表格数据继续使用 shadcn `Table` 语义结构；复杂数据表要统一 header 行高、数字列对齐、hover、empty/error row、actions 尺寸和横向滚动策略。
- 金融数据面板应偏向低阴影、清晰边框、紧凑 padding、稳定高度；禁止卡片嵌套卡片式堆叠。
- `EmptyState` 和 `ErrorState` 必须继续用于空/失败分支，不把失败静默渲染为空状态。

### R5. 图表和市场数据可视化一致性

- 现有 `lightweight-charts`、Recharts、mini chart、candlestick、intraday、market overview 等图表容器要有统一 panel 样式、加载/空/失败状态、图例/tooltip 对齐和可访问 fallback。
- 涨跌颜色继续尊重已有 market color setting；颜色不能成为唯一信息表达，关键状态要有文本或 icon 辅助。
- 不新增大型图表库，除非现有库无法满足具体页面。

### R6. 表单、设置和动作反馈统一

- Settings、Watchlist forms、Portfolio forms、Research notebook、Evidence import 等表单区域使用一致 label、helper、error、disabled、success feedback 样式。
- Icon-only 动作必须有 `sr-only` 或 aria label；所有可点击元素应有明确 hover/focus/disabled 状态。
- 用户可见文案必须同步更新 `apps/web/messages/en.json` 和 `apps/web/messages/zh.json`。

### R7. 响应式、可访问性和性能

- 重点验证 375/390px mobile、768px tablet、1024px laptop、1440px desktop。
- 页面不得出现 document/body 横向溢出；固定导航不得遮挡内容。
- light/dark contrast 达到 WCAG AA；focus ring 可见；支持 `prefers-reduced-motion`。
- 动效控制在 150-300ms 微交互范围内，避免装饰性连续动画和布局位移动画。
- 保持 Server Components 优先和现有数据获取模式，不为了视觉重构引入不必要 client state。

## Acceptance Criteria

- [ ] `apps/web/app/globals.css`、`apps/web/tailwind.config.ts` 和共享 UI 组件形成可复用的金融工作台视觉系统，新增样式不依赖页面级 raw hex 重复。
- [ ] 全部主导航页面和核心 detail 页面使用统一页头/指标区模式，且页面内 card/table/action 样式一致。
- [ ] Dashboard、Instruments、Instrument Detail、AI Research、Evidence、Watchlist、Portfolios、Reports、Alerts、Task Runs、Settings 至少完成一次桌面和移动端浏览器 smoke。
- [ ] 375/390px、768px、1024px、1440px 视口下无 document/body 横向溢出，无导航遮挡主内容，无明显文本重叠。
- [ ] Light 和 dark mode 的代表性文本、状态 badge、ticker/table/chart panel 通过 WCAG AA 对比度抽样。
- [ ] 新增或变更的用户可见文案在 `en.json` 和 `zh.json` 中同步。
- [ ] 行为改变的页面或组件更新对应 Vitest/Testing Library 测试。
- [ ] `git diff --check` 通过。
- [ ] `npx tsc -p apps/web/tsconfig.json --noEmit --ignoreDeprecations 6.0` 通过。
- [ ] `npm run test:web -- --reporter=dot` 通过。

## Out Of Scope

- 不实现实时 WebSocket、Level-2/order-flow/fund-flow、专业 screener、backtesting、portfolio risk、可拖拽多面板工作站等终端级能力；这些仍属于 `07-03-professional-financial-dashboard` 或未来子任务。
- 不重构后端服务、数据库 schema、API contract，除非前端已有 UI 状态无法正确展示现有字段。
- 不做营销 landing page、品牌官网、Logo/CIP 设计。
- 不引入大型动画库或整套新 UI 框架。
- 不把 mock/degraded/no-data 包装成真实行情能力。
