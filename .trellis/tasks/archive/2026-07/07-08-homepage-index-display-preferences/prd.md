# 首页核心指数自选展示参数

## Goal

让用户可以自选首页顶部和“核心市场指数”区域展示哪些美股/A 股核心指数，以及这些指数卡片展示哪些关键字段，从而保持首页精简，但让入口信息更贴合个人关注重点。

## User Value

- 首页继续只承担“市场总览”职责，不重新堆回 AI、报告、K 线、技术指标等深层模块。
- 用户可以把最关心的指数放在首页第一屏，例如只看 S&P 500、Nasdaq、上证、沪深 300，或调整默认排序。
- 用户可以控制指数卡片的信息密度，避免每个人都被迫接受同一套字段。

## Confirmed Facts

- 当前首页已经被纠偏为 curated market overview，优先级是核心指数、宏观观察、热点板块、新闻舆情和重要状态，见 `.trellis/tasks/07-08-frontend-site-redesign/design.md`。
- 首页当前从 `/dashboard/market-overview` 读取 `indices.items`，`tickerItems` 使用前 10 个指数，`coreMarketIndexItems` 先筛选 `region === "US" || region === "CN"` 再截取 8 个，见 `apps/web/app/[locale]/page.tsx`。
- 设置页已有“首页宏观收藏” textarea，保存到 `platform_settings.json` 的 `favorite_macro_indicator_codes`，首页按该顺序展示宏观指标，见 `apps/web/lib/platform-settings-store.ts` 和 `apps/web/app/[locale]/settings/page.tsx`。
- 因此核心指数自选应沿用现有平台设置模式，而不是引入新的全局 client store 或账号系统。

## Requirements

### R1. 首页核心指数选择与排序

- 新增平台设置字段，例如 `favorite_home_index_codes`，用于保存首页核心指数代码的顺序。
- 默认值应覆盖当前核心意图：美股核心指数和 A 股核心指数，不包含港股作为默认核心首页卡片，除非用户自行添加。
- 首页应按用户配置顺序展示匹配的 `marketOverviewPayload.indices.items`。
- 当配置为空时，回退到推荐默认值；当配置中某些代码当前 payload 缺失时，页面应保留其缺失状态或给出明确降级提示，不能静默伪造行情。
- 顶部 `MarketTicker` 和“核心市场指数”卡片应使用同一套自选排序，避免两个首页指数入口互相矛盾。

### R2. 展示参数选择

- 新增平台设置字段，例如 `home_index_display_fields`，用于控制指数卡片显示字段。
- 推荐 MVP 字段范围：
  - latest close
  - percent change
  - freshness badge
  - as-of date
  - region
  - provider/source
- 默认字段保持当前首页卡片密度：价格、涨跌幅、freshness、as-of date、region。
- UI 需要避免把参数配置变成复杂报表设计器；用复选框或紧凑选项即可。

### R3. 设置页入口

- 在 Settings 页面新增“首页核心指数”设置区，紧邻现有“首页宏观收藏”。
- 允许用户以每行一个 code 或逗号分隔的形式编辑指数代码，和宏观收藏的输入习惯保持一致。
- 提供默认值提示和字段说明，中英文文案同步更新。
- 保存时复用 `savePlatformSettingsAction`，并保留现有 provider、LLM key、Tushare token、color scheme、macro favorites 的行为。

### R4. 首页信息架构边界

- 首页仍只展示核心指数、宏观观察、热点板块、新闻舆情和重要状态。
- 本任务不得把 AI research brief、comparison tool、K-line、technical indicators、fundamentals、reports 等深模块重新放回首页。
- 深模块入口可以通过现有导航或少量链接抵达，但不能变成首页内容块。

### R5. Tests And Safety

- 更新 `apps/web/app/[locale]/page.test.tsx`，覆盖自选指数排序、缺失配置回退、以及首页不渲染深模块的 contract。
- 更新 settings 相关测试，覆盖新字段保存、去重、空值处理和默认回退。
- 更新 `apps/web/lib/platform-settings-store.ts` 的 normalization 测试或新增测试，确保字符串/数组输入都能稳定归一化。
- 不在测试或文档中打印、暴露、重写真实 API key/token；保存设置时必须保留现有敏感字段行为。

## Acceptance Criteria

- [ ] Settings 页面出现“首页核心指数”设置区，支持编辑指数 code 顺序和选择展示字段。
- [ ] 首页顶部 ticker 和核心指数卡片都按用户配置顺序展示。
- [ ] 配置为空时使用推荐默认核心指数；重复 code 和空行会被忽略。
- [ ] 配置 code 在 payload 中缺失时有明确降级状态，不伪造价格或涨跌幅。
- [ ] 用户可见新文案同步存在于 `apps/web/messages/en.json` 和 `apps/web/messages/zh.json`。
- [ ] 首页仍不展示 AI brief、comparison tool、K-line、reports、technical indicators、fundamentals 等深模块。
- [ ] `npm run test:web -- --reporter=dot` 通过。
- [ ] `npx tsc -p apps/web/tsconfig.json --noEmit --ignoreDeprecations 6.0` 通过。
- [ ] `git diff --check` 通过。

## Out Of Scope

- 不做拖拽排序；textarea/checkbox/紧凑选项足够作为 MVP。
- 不做账号级、浏览器级或多设备同步设置；沿用现有 server-side platform settings。
- 不新增行情 provider、后端指数接口或数据库 schema。
- 不实现自定义公式、估值因子或完整 dashboard builder。
- 不把更多功能模块放回首页。

## Recommended MVP

1. 在 `platform-settings-store` 增加默认核心指数 code 列表、字段列表、归一化函数和 public settings 字段。
2. 在 `savePlatformSettingsAction` 接收并保存新字段。
3. 在 Settings 页面添加“首页核心指数”配置区。
4. 在首页构建 `tickerItems` 和 `coreMarketIndexItems` 前先应用用户配置。
5. 更新中英文文案和 focused tests。

## Open Questions

无阻塞问题。推荐默认实现为：首版仅支持 code 顺序和字段复选，不支持拖拽排序或账号级配置。
