# Professional Financial Dashboard - 深度改造

## Goal

将股票分析平台首页改造为**专业级金融数据看板**，达到 Yahoo Finance 和 TradingView 的视觉和功能水准。

## Background

### 当前状态
- 已完成基础 UI 优化（信息密度提升、颜色系统、响应式布局）
- 仍使用卡片式布局，装饰性元素较多
- 与专业金融看板相比，信息密度、视觉风格差距明显

### 用户反馈
> "现在和专业的金融数据看板风格还是差距比较大"

### 参考网站分析

**Yahoo Finance 顶部滚动条**
- 超紧凑横向滚动：一行显示 7-10 个指数
- 黑色背景：`background: #000` 或深色
- 极简设计：只有指数名、数字、涨跌颜色
- 实时滚动：自动横向滚动展示更多数据
- 无边框、无圆角、无阴影

**TradingView 整体风格**
- 深色主题为主：专业感和眼睛友好
- 图表优先：大面积图表，数据为辅
- 表格化数据：清晰的行列对齐
- 功能性极强：工具栏、快捷键、多面板布局
- 等宽字体：数字对齐清晰

## Requirements

### 高优先级（必须）

#### 1. Yahoo Finance 风格顶部滚动条

**设计要求**
- 黑色或深灰背景（`bg-black` 或 `bg-gray-950`）
- 横向自动滚动或溢出滚动
- 单行显示多个指数（7-10 个可见）
- 极简信息：名称 + 价格 + 涨跌 + 涨跌幅
- 无边框、无圆角、无卡片装饰

**技术实现**
- 使用 `overflow-x-auto` 或自动滚动动画
- Flex 横向布局
- 等宽字体（`font-mono`）
- 涨跌颜色动态应用

**数据来源**
- 复用现有核心指数数据
- 或从市场概览 API 获取

#### 2. 深色主题优化

**主题配置**
- 默认启用深色模式（或根据系统）
- 背景色：`bg-gray-950` 或 `bg-black`
- 卡片背景：`bg-gray-900` 或略浅
- 文字：`text-gray-100` 或 `text-white`
- 边框：`border-gray-800`（如果需要）

**颜色对比度**
- 确保 WCAG AA 标准
- 涨跌颜色在深色背景下清晰可见
- 图表颜色调整为深色主题适配

#### 3. 表格化数据展示

**核心指数区域**
- 从卡片网格改为表格或类表格布局
- 列：指数名称 | 最新价 | 涨跌 | 涨跌幅 | 迷你图表
- 等宽字体数字列
- 行高紧凑（`py-1` 或 `py-2`）
- 斑马纹或悬停高亮

**关注标的区域**
- 同样改为表格布局
- 更大的图表区域
- 可选：展开/收起详情

#### 4. 信息密度最大化

**布局优化**
- 去掉所有卡片圆角（`rounded-none`）
- 去掉阴影（`shadow-none`）
- 减少内边距（`p-1` 或 `p-2`）
- 减少外边距和间距（`gap-1`）
- 使用极窄行高（`leading-tight`）

**字体优化**
- 数字使用等宽字体（`font-mono`）
- 更小的字号（`text-xs` 或 `text-sm`）
- 标签和次要信息使用 `text-[10px]`

#### 5. 图表优先布局

**图表区域扩大**
- 主图表占据更大空间
- K 线图高度增加（h-64 或 h-80）
- 迷你图表保持紧凑（h-8 或 h-12）

**数据面板紧凑**
- 数据指标使用表格或紧凑列表
- 不占用过多垂直空间

### 中优先级（应该）

#### 6. 响应式优化

**桌面优先**
- 专业金融看板主要用于桌面
- 桌面体验优先，信息密度最大化

**移动端降级**
- 移动端可适当简化
- 顶部滚动条保留但可调整

#### 7. 性能优化

**滚动性能**
- 横向滚动流畅
- 使用 CSS transform 或高性能动画

**数据更新**
- 实时数据更新不影响性能
- 使用虚拟滚动（如果数据量大）

### 低优先级（可选）

#### 8. 高级功能

**实时数据**
- WebSocket 实时推送（如果后端支持）
- 自动刷新机制

**交互增强**
- 点击指数快速跳转详情
- 快捷键支持
- 多面板布局

## Acceptance Criteria

- [ ] 顶部有 Yahoo Finance 风格的黑底横向滚动条
- [ ] 滚动条显示 7-10 个核心指数，信息极简
- [ ] 深色主题作为默认或主要风格
- [ ] 核心指数区域改为表格布局，等宽字体
- [ ] 关注标的区域改为表格或大图表布局
- [ ] 所有圆角、阴影、装饰性元素已移除
- [ ] 信息密度显著提升，接近专业金融看板水准
- [ ] 深色主题下颜色对比度符合 WCAG AA 标准
- [ ] 桌面端布局紧凑、专业，移动端基本可用
- [ ] 页面加载和滚动性能良好

## 2026-07-05 Automated Evidence Update

Code and test evidence now supports part of the professional-dashboard direction, but this task should remain active until the visual acceptance criteria are reviewed in a browser.

Evidence already present:

- `apps/web/components/market-ticker.tsx` implements a black, horizontally scrollable, font-mono ticker with compact index data and market filtering.
- `apps/web/components/market-overview-client.tsx` renders the core index area as a table with latest price, absolute change, percent change, mini chart, and status columns.
- The ticker, market overview, and shared `PriceChangeBadge` now use the global market-color context for homepage and reused badge movement values.
- Focused tests passed for settings, homepage rendering, ticker behavior, and route proxy cache-safety; full web tests passed.

Remaining professional-dashboard checks:

- Confirm 7-10 ticker items are visible at common desktop widths using browser screenshot evidence.
- Decide whether the whole dashboard should default to dark theme or preserve user theme while optimizing dark-mode styling.
- Review the followed-instrument section for table/big-chart parity.
- Decide how far to go on removing cards, rounding, and decorative elements without hurting shadcn accessibility/consistency.
- Verify WCAG contrast, mobile fallback, and scroll performance manually or with a browser automation/a11y follow-up.

## 2026-07-05 Professional Gap Research Update

Research and current-state inventory were written to:

- `.trellis/tasks/07-03-frontend-ui-polish/research/financial-dashboard-current-state-and-professional-gap.md`

Current position:

- The app is now a solid internal research dashboard MVP with compact ticker, market-overview table, provider-aware degraded states, technical charting, comparison, watchlist, portfolio, reports, AI assistant, hot sectors, intraday, and depth cards.
- It is not yet at TradingView/Yahoo Finance/Bloomberg/MarketWatch/Eastmoney/ifind-style professional parity because real-time feeds, Level-2/order-flow/fund-flow validation, screeners, backtests, configurable workstations, and production research corpus remain incomplete.

Trellis execution plan:

- P0: provider trust and no-fabrication UX.
  - Keep live/delayed/mock/no-data states visible across dashboard, sectors, intraday, depth, reports, and assistant.
  - Validate production providers for intraday/depth/fund-flow before calling the UI real-time or Level-2 capable.
  - Add durable browser/screenshot evidence for UI polish and WCAG contrast.
- P1: professional research workflows.
  - Add screener/watchlist custom columns, saved filters, richer alert conditions, and signal browsing.
  - Add sector rotation history, breadth/contribution drill-down, and real fund-flow provider integration.
  - Persist chart/dashboard workspace settings beyond the current local chart note/toggle MVP.
  - Expand AI assistant sources to filings/transcripts/announcements only after citation contracts and ingestion exist.
- P2: terminal-grade analytics and operations.
  - Add strategy backtesting UI, signal-history persistence, slippage/cost assumptions, and walk-forward validation.
  - Add portfolio attribution, exposure, factor/risk, and scenario analysis.
  - Add data SLA dashboards, provider incident history, entitlement/audit model, and usage monitoring.

## 2026-07-05 Final Audit Update

Latest browser smoke evidence supports the current MVP dashboard state:

- `/zh` rendered `首页概览` at 1440x900 and 390x844 without document/body horizontal overflow.
- `/zh/settings` rendered `设置`, exposed China/international market-color choices, and exposed the Tushare HTTP URL field at both viewports.
- No browser console errors were captured during the final smoke pass.

This is enough to close the current implementation audit, but not enough to declare professional-terminal parity. Screenshot and WCAG evidence are now complete; this task remains active for richer workstation/chart workflows, production provider validation, screeners, backtesting, and research-corpus expansion.

## 2026-07-05 Evidence Closure Update

The durable screenshot and WCAG evidence portion was completed in `07-05-dashboard-visual-evidence-wcag`:

- Screenshots now cover `/zh`, `/zh/settings`, `/zh/instruments/AAPL`, and `/zh/watchlist` at desktop and mobile widths.
- Browser observations recorded no console errors, runtime-error text, or document/body horizontal overflow on sampled routes.
- Light/dark contrast sampling passed for representative ticker, table, settings, instrument, and watchlist states after a small black-ticker neutral-text fix.

This strengthens the MVP/professional-style UI evidence, but does not change the professional-terminal parity conclusion. The remaining work is still production data/provider depth, Level-2/order-flow/fund-flow validation, screeners, backtests, configurable workstations, portfolio/risk analytics, and richer research corpus.

## 2026-07-05 Provider Trust Update

Child task `07-06-provider-trust-data-sla-dashboard` closed the next P0 no-fabrication/frontend trust gap:

- Homepage ticker and market overview now expose provider/source/freshness/status metadata.
- Recommendation cards no longer claim realtime by default and can display provider/source/generated_at/diagnostics.
- Instrument latest, K-line, and intraday displays surface provider/source/freshness/cache/session/degraded reasons.
- Reports list/detail display `source_summary`, and report generation warns when no explicit provider is passed.

This makes the MVP safer and closer to professional transparency practices, but it still is not a production SLA console or professional terminal. Remaining professional work includes validated live feeds, provider incident/SLA history, Level-2/order-flow/fund-flow validation, screeners, backtests, portfolio risk analytics, configurable workstations, and richer research corpus.

## Out of Scope

- 实时 WebSocket 数据推送（除非后端已支持）
- 完整的 TradingView 式图表工具（使用现有图表库）
- 多面板拖拽布局（可后续迭代）
- 自定义看板配置（可后续迭代）

## Open Questions

1. **滚动条实现方式**：自动滚动动画 or 手动溢出滚动？
   - 推荐：溢出滚动（`overflow-x-auto`），更简单可控
   - 备选：CSS 动画自动滚动（更炫酷但复杂）

2. **深色主题切换**：强制深色 or 保留用户选择？
   - 推荐：默认深色，但保留主题切换按钮
   - 理由：专业用户偏好深色，但给予灵活性

3. **表格 vs 类表格**：使用 `<table>` 还是 Flex/Grid 模拟？
   - 推荐：使用 shadcn `Table` 组件
   - 理由：语义化、可访问性、样式统一

4. **数据刷新频率**：多久刷新一次数据？
   - 推荐：1-5 分钟自动刷新
   - 或用户手动刷新

## Technical Notes

### 顶部滚动条实现

```tsx
<div className="bg-black text-white overflow-x-auto whitespace-nowrap border-b border-gray-800">
  <div className="flex gap-6 px-4 py-2">
    {indices.map(index => (
      <div key={index.code} className="inline-flex items-center gap-2 font-mono text-sm">
        <span className="text-gray-400">{index.name}</span>
        <span className="font-bold">{index.close}</span>
        <span className={cn(index.change >= 0 ? "text-green-500" : "text-red-500")}>
          {formatChange(index.change)} ({formatPercent(index.changePercent)})
        </span>
      </div>
    ))}
  </div>
</div>
```

### 表格化核心指数

```tsx
<Table>
  <TableHeader>
    <TableRow className="border-gray-800">
      <TableHead className="text-gray-400">指数</TableHead>
      <TableHead className="text-right text-gray-400">最新价</TableHead>
      <TableHead className="text-right text-gray-400">涨跌</TableHead>
      <TableHead className="text-right text-gray-400">涨跌幅</TableHead>
      <TableHead className="text-gray-400">走势</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    {indices.map(index => (
      <TableRow key={index.code} className="border-gray-800 hover:bg-gray-900">
        <TableCell className="font-medium">{index.name}</TableCell>
        <TableCell className="text-right font-mono">{index.close}</TableCell>
        <TableCell className={cn("text-right font-mono", colors.getMovementColor(index.change))}>
          {formatChange(index.change)}
        </TableCell>
        <TableCell className={cn("text-right font-mono", colors.getMovementColor(index.change))}>
          {formatPercent(index.changePercent)}
        </TableCell>
        <TableCell><MiniChart data={index.bars} height={32} /></TableCell>
      </TableRow>
    ))}
  </TableBody>
</Table>
```

### 深色主题 Tailwind 配置

```js
// tailwind.config.js
module.exports = {
  darkMode: 'class', // or 'media'
  theme: {
    extend: {
      colors: {
        // 自定义深色主题色板
      }
    }
  }
}
```

## Implementation Phases

**Phase 1: 顶部滚动条**（1-2h）
- 创建黑底横向滚动组件
- 集成核心指数数据
- 响应式优化

**Phase 2: 深色主题**（1-2h）
- 配置深色主题
- 调整所有颜色变量
- 确保对比度符合标准

**Phase 3: 表格化布局**（2-3h）
- 核心指数改为表格
- 关注标的改为表格或大图表
- 去装饰、紧凑化

**Phase 4: 测试优化**（1h）
- 响应式测试
- 性能测试
- 视觉对比调整

## Success Metrics

- 用户反馈："现在看起来专业多了"
- 首屏信息密度再提升 30%+
- 视觉风格接近 Yahoo Finance / TradingView
- 保持良好的性能和可访问性

## Notes

- 本次改造是"深度"改造，会大幅改变视觉风格
- 建议保留上一版本代码，便于对比和回滚
- 专业金融看板可能不适合所有用户，考虑提供"简洁/专业"模式切换
