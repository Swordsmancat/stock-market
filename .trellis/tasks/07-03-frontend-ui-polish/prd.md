# 前端页面优化与美化

## Goal

优化股票分析平台的前端页面，采用**信息密度优先的金融风格**，提升专业性、可用性和数据阅读效率。

## Background

### 当前状态
- 首页包含市场看板：10个核心指数、关注标的 K 线、巴菲特指标、数据健康诊断
- 技术栈：Next.js 16 + React Server Components + Tailwind CSS + shadcn/ui
- 33+ 组件文件，支持亮暗模式切换

### 用户反馈
- 当前风格装饰性较强，不够实用
- 信息密度偏低，数据展示效率不足
- 需要更专业的金融数据展示风格

## Requirements

### 1. 金融风格视觉改造（高优先级）

**1.1 信息密度优化**
- 紧凑布局：减少卡片内边距（当前 p-4 → p-2 或 p-3）
- 数据层级：核心数值大（28-32px），次要信息小（12-14px）
- 首屏信息量：从 10 个指数提升到 15-20 个指数 + 关注标的

**1.2 涨跌颜色系统**
- 默认：涨绿跌红（中国习惯）
- 新增设置项：支持切换为国际习惯（涨红跌绿）
- 全局生效：所有页面和组件统一使用用户选择的颜色习惯
- 实现方式：通过 Context 或 platform_settings 存储

**1.3 视觉简化**
- 减少装饰：去掉非必要的阴影、圆角、背景色
- 强调数据：用字体大小和粗细区分层级，而非颜色装饰
- K 线图高度降低：从当前高度降至 60-80px，作为趋势参考

### 2. 布局和响应式改进（高优先级）

**2.1 桌面布局优化**
- 指数区域：从 5 列网格调整为更紧凑的 6-8 列
- 卡片间距统一：gap-3 或 gap-4
- 视觉分组：CN/HK/US 区域用分隔线或背景色区分

**2.2 响应式适配**
- 桌面（>1280px）：6-8 列指数卡片
- 平板（768-1279px）：4-5 列指数卡片
- 移动（<768px）：2 列指数卡片，保持信息密度

### 3. 全站页面统一优化（高优先级）

**3.1 优化范围**
- 首页（市场看板）
- 标的详情页（`/instruments/[symbol]`）
- 关注列表页（`/watchlist`）
- 设置页（`/settings`）
- 其他核心页面（任务监控、报告中心等）

**3.2 统一设计规范**
- 卡片样式：统一内边距、圆角、边框
- 数据展示：统一字体大小、颜色、间距
- 交互反馈：统一悬停、点击、加载状态

### 4. 交互和动画（中优先级）

**4.1 轻量级过渡动画**
- 页面/组件淡入淡出（transition-opacity duration-200）
- 数据更新平滑过渡（transition-all duration-300）
- 按钮悬停轻微变化（scale-105 或背景色变化）
- 使用 CSS transitions，无需额外库

**4.2 加载和错误状态**
- 骨架屏：数据加载时显示占位符
- 错误提示：友好的错误信息和重试按钮
- 空状态：清晰的提示和操作引导

### 5. 数据可视化细节（中优先级）

**5.1 K 线图优化**
- 线条粗细：更细的 K 线，减少视觉干扰
- 网格线：更淡的网格，不抢主体
- Tooltip：鼠标悬停时显示详细 OHLCV 数据

**5.2 成交量柱状图**
- 颜色与涨跌一致
- 高度适中，不干扰 K 线阅读

## Acceptance Criteria

- [ ] 首页首屏显示 15+ 个指数和关注标的，信息密度提升 50%+
- [ ] 涨跌颜色系统可在设置页面切换，切换后全局生效
- [ ] 所有主要页面（首页、详情页、关注列表、设置页）应用统一的金融风格
- [ ] 桌面、平板、移动端响应式布局正常，信息层级清晰
- [ ] 亮暗模式颜色对比度符合 WCAG AA 标准
- [ ] 加载状态有骨架屏，错误状态有友好提示
- [ ] 页面过渡动画流畅，无卡顿感
- [ ] K 线图清晰易读，不干扰数据阅读

## Out of Scope

- 后端 API 修改
- 数据结构调整
- 新功能开发（仅优化现有功能的视觉和交互）
- 完整重构（增量改进为主）
- 复杂动画库（如 framer-motion）

## Technical Notes

### 涨跌颜色实现方案
```typescript
// 1. 在 platform_settings 添加字段
{
  color_scheme: "china" | "international" // 默认 "china"
}

// 2. 创建颜色 hook
function useMarketColors() {
  const settings = usePlatformSettings();
  return settings.color_scheme === "china" 
    ? { up: "text-green-600", down: "text-red-600" }
    : { up: "text-red-600", down: "text-green-600" };
}

// 3. 全局应用
const colors = useMarketColors();
<span className={movement > 0 ? colors.up : colors.down}>
```

### 信息密度优化示例
```tsx
// 当前
<div className="p-4 space-y-3">
  <div className="text-2xl">3000.00</div>
  <div className="text-sm">上证指数</div>
</div>

// 优化后
<div className="p-2 space-y-1">
  <div className="text-3xl font-bold">3000.00</div>
  <div className="text-xs text-muted">上证指数</div>
</div>
```

## Implementation Notes

建议分阶段实施：
1. **Phase 1**: 首页金融风格改造 + 涨跌颜色系统
2. **Phase 2**: 其他页面应用统一风格
3. **Phase 3**: 交互细节和动画优化
