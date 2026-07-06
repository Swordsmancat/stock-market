# 信息平台与 AI 研究能力对标

日期：2026-07-06

## 对标范围

本次对标只比较“个人投资信息汇总 + 宏观/估值数据 + hard-to-find source + AI 摘要推荐”能力，不按专业交易终端、券商下单平台或低延迟行情系统衡量。

参考对象：

- Koyfin: https://www.koyfin.com/
- MacroMicro: https://en.macromicro.me/
- TradingView economic calendar / public investor workflow: https://www.tradingview.com/economic-calendar/
- AlphaSense AI research platform: https://www.alpha-sense.com/platform/
- FRED API: https://fred.stlouisfed.org/docs/api/fred/
- World Bank API: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392
- SEC EDGAR APIs: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- Trading Economics API: https://tradingeconomics.com/api/

## 当前已满足

| 能力 | 当前实现 | 满足度 |
|---|---|---|
| 个人 dashboard 汇总 | 首页聚合市场概览、watchlist、报告、推荐、新闻、任务状态、宏观指标、source readiness 和 dashboard brief | MVP 满足 |
| 宏观/估值指标骨架 | `MarketIndicator` / `MarketIndicatorObservation` 支持 source-aware observation；已有 Buffett、利率、通胀、M2 等 definitions-first 指标 | MVP 满足 |
| No-data-safe 行为 | 无可审计观测值时明确返回 `no_data`，不伪造宏观数值 | 满足核心边界 |
| Hard-to-find source readiness | FRED/PBOC/Buffett/SEC/user seed files 等来源有 readiness、collection links、citation boundary | MVP 满足 |
| Manual seed/import pipeline | JSON/CSV seed import 需要 source、as_of、components、methodology/review metadata，并 validate-all-before-write | MVP 满足 |
| Source-to-seed templates | 首页可展示 target codes、required fields、JSON/CSV 占位模板、review checklist、import command | MVP 满足 |
| AI 摘要与引用 | dashboard narrative 和 instrument assistant 都有 citation validation / deterministic fallback 边界 | MVP 满足 |
| 推荐定位 | 推荐作为研究线索和历史样本评估，不是买卖指令 | 满足产品边界 |

结论：当前功能已经能支撑“个人投资信息 cockpit”的第一版。它能把已有本地证据和缺口一起展示，并把 AI 摘要限制在可引用证据和明确 data gaps 之内。

## 与成熟信息/研究平台的差距

### 1. 宏观源和发布日历

Koyfin、MacroMicro、FRED、Trading Economics 这类平台强在宏观序列覆盖、日历、图表和指标对照。当前平台已经有宏观指标模型和 seed/import 入口，但缺少：

- FRED 等官方 API adapter。
- CPI、M2、利率、GDP、市值组件的 release calendar / expected update date。
- 指标 freshness policy 和 source capability matrix。
- 跨指标 chart / macro dashboard 专题页。

### 2. AI 研究语料和主题追踪

AlphaSense 类产品强在 filings、transcripts、新闻、研究资料的 AI search / monitor / summarize。当前平台有 citation-aware assistant 和 dashboard brief，但缺少：

- 合法文档语料 ingest policy。
- SEC filings / exchange announcements / transcripts 的 production source pipeline。
- 主题、公司、watchlist 级别的 monitor。
- 保存的 AI follow-up、notebook、brief history。

### 3. Personal workflow

TradingView/Yahoo Finance 类工具强在 watchlist、日历、新闻流、图表和个人跟踪。当前平台已有 watchlist 和研究线索，但缺少：

- watchlist event inbox。
- daily/weekly digest history。
- 用户笔记与来源链接绑定。
- saved question / saved view / follow-up workflow。

### 4. 数据授权和可追溯运维

成熟平台通常会明确数据授权、延迟、来源和服务稳定性。当前平台已有 provider/source/degraded/no_data 语义，但后续应继续补：

- `retrieved_at`、license/usage note、source terms note。
- adapter 级失败诊断和重试策略。
- source capability matrix。
- 数据 freshness SLA 或个人维护 checklist。

## 不建议现在追逐的方向

- 实盘交易、券商账户、订单路由、自动下单。
- 低延迟实时行情、完整 Level-2、逐笔订单流、盘口热力图。
- 专业终端式多屏工作站、机构级权限/合规系统。
- 未授权全文抓取、无来源/无日期/无 methodology 的数据入库。
- AI 直接给买入/卖出/持有/仓位/目标价指令。

## Trellis 后续任务建议

### P0: Official Macro Adapter MVP

目标：把当前 manual seed-first 宏观能力推进到少数官方源 adapter。

验收要点：

- FRED rates/inflation/liquidity adapter 至少覆盖 `DGS10`、`DGS2`、`T10Y2Y`、`CPIAUCSL`、`M2SL` 中的一组。
- 每条 observation 保存 source URL / series ID、as_of、retrieved_at、methodology。
- API 失败、空响应、未知序列必须 degraded/no_data，不伪造值。
- dashboard citations 只引用成功入库的 observations。

### P0: Macro Release Calendar And Gap Tracker

目标：让用户知道“哪个宏观指标下一次该更新，当前缺什么”。

验收要点：

- 为核心宏观/估值指标定义 freshness policy、expected cadence、next expected update。
- 首页 source readiness / macro panel 展示 overdue、due soon、no data、manual review needed。
- 不从日历推断市场结论，只生成数据维护提示。

### P1: Daily / Weekly AI Digest History

目标：把 dashboard brief 从一次性摘要变成个人研究历史。

验收要点：

- 保存每日/每周 brief、citations、diagnostics、source gaps、model metadata。
- 支持列表和详情页查看历史。
- 未配置 LLM 时保存 deterministic fallback。
- 仍禁止投资建议、买卖指令和未知 citation。

### P1: Watchlist Event Inbox

目标：将个人关注标的的变化集中到一个 inbox。

验收要点：

- 汇总 watchlist 价格异动、报告更新、新闻事件、宏观数据更新、source readiness 变化。
- 每个事件保留 source、as_of/generated_at、status、citation 或 data gap。
- AI 只能总结事件，不把缺失来源当事实引用。

### P1: Hard-to-Find Source Notebook

目标：让用户保存人工复核的来源链接、摘录、seed 文件、计算备注和 AI follow-up。

验收要点：

- 用户可以把 link/note/file metadata 关联到 symbol、indicator、report 或 watchlist。
- notebook 条目默认不是 citation；只有审核字段齐全并入库后才能进入 evidence。
- 支持 source terms / usage note / review note。

### P2: Legal Document Ingestion

目标：在来源合法和引用边界明确后接入 SEC filings、交易所公告、transcripts 或用户上传文档。

验收要点：

- 先支持 metadata + excerpt/summary + citation，不默认存储未授权全文。
- 对每个 provider 标明 license/source boundary。
- AI 引用必须指向本地审核后的文档 metadata 或摘要。

### P2: Research Alerts And Cross-Indicator Views

目标：增强个人研究效率，而不是交易扫描。

验收要点：

- 支持宏观阈值、watchlist event、source update、report update 提醒。
- 支持跨指标图表、saved views、轻量注释。
- 推荐继续作为 research lead，展示 evidence、history sample 和 risk notes。

## 总体判断

当前实现满足用户提出的核心方向：个人信息汇总、宏观指标收集、AI 总结推荐，以及对难找数据的来源准备。下一阶段不应转向终端竞争，而应把“source -> audited evidence -> AI citation -> daily/weekly workflow”这条链路做深。
