# 股票分析平台用户手册

本手册面向平台使用者，说明当前可用的信息汇总、宏观/估值指标、AI 摘要、Phase 2 / Phase 3 金融分析能力、入口、数据状态和风险边界。当前产品定位是个人投资研究 cockpit：把分散数据、难找来源和 AI 总结集中到一个工作台，而不是与专业交易终端竞争。

> 重要说明：本平台是研究辅助系统，不连接实盘交易，不自动下单，也不构成投资建议。所有 AI、推荐、指标和深度数据都应与用户自己的研究流程交叉验证。

## 功能状态总览

| 阶段 | 功能 | 当前状态 | 用户含义 |
|---|---|---:|---|
| Phase 2 | K 线图交互增强（缩放 + 均线） | 已完成 | 个股详情页支持交互式 K 线、时间范围切换和 MA 等指标显示。 |
| Phase 2 | 智能推荐（突破 / 超跌） | 已完成 | 首页/相关模块可展示基于行情和技术规则的研究线索。 |
| Phase 2 | 热点板块轮动（资金流向） | Provider-backed MVP | 首页热点板块已使用统一 provider contract，可展示 live/delayed/mock/unavailable 状态、资金流口径、数据源、时间、成分股、广度、贡献和分类版本；默认静态样例仍明确标记为 mock/degraded。 |
| Phase 2 | 对比分析（相关性） | 已完成 | 支持多标的对比与相关性分析。 |
| Phase 3 | 分时图 | Provider-backed MVP | 个股详情页分时图已支持 yfinance `1m` 真实分钟线（可用时），并保留 `ok` / `no_data` / `degraded` 状态；不支持分钟线的 provider 会明确降级。 |
| Phase 3 | 深度数据（五档 / 大单） | Provider-boundary MVP | 个股详情页深度卡片支持真实 provider-backed 行和局部可用状态；内置生产 provider 尚未验证 Level-2 时仍明确显示不可用。 |
| Phase 3 | 技术指标库（MACD / RSI / KDJ） | 已完成 | K 线图指标工作台支持 MA、BOLL、成交量、MACD、RSI、KDJ。 |
| Phase 3 | AI 助手 | Research-citation MVP | 个股详情页已提供聊天式 AI 市场助手，可基于可验证日线、指标、基本面、新闻和已生成报告上下文回答问题，并显示可追踪引用、诊断和免责声明。 |
| P0 | 证据中心 | 已完成 | `/evidence` 提供专门的宏观/估值证据、信息源就绪度、seed 模板和 AI 摘要工作台，不再只依赖首页综合看板查找这些信息。 |
| P0 | 宏观/估值指标与 AI 日摘要 | No-data-safe MVP | 首页已扩展巴菲特指标、美国长短债收益率/利差、CPI、M2 和中国 M2 等观察点，并展示确定性 AI-ready 日摘要、引用、诊断和数据缺口。 |
| P0 | FRED 官方宏观刷新 | Opt-in adapter MVP | 配置 `FRED_API_KEY` 后，可用本地脚本刷新 DGS10、DGS2、T10Y2Y、CPIAUCSL 派生 YoY 和 M2SL 派生 YoY；成功入库后才成为 AI 可引用证据。 |
| P1 | 可审计宏观 seed 导入 | Manual import MVP | 已支持从本地 JSON/CSV 文件导入人工复核后的宏观/估值观测值；每行必须包含 source、as-of、components 和 methodology/notes 等审计信息。 |

## 首页市场看板

首页用于快速观察市场状态、关注标的、热点板块、智能推荐和报告摘要。

常见模块包括：

- 核心指数和市场概览。
- 关注标的 K 线摘要。
- 热点板块或板块资金流提示。
- 智能推荐线索，例如突破、超跌反弹、成交异常和强势动量。
- AI 报告、每日任务和运行状态入口。
- 宏观/估值指标与 AI 研究摘要，用于快速发现需要继续查证的市场背景和数据缺口。

## 证据中心

证据中心位于 `/evidence`，是当前宏观/估值研究的第一入口。它复用 `GET /dashboard/market-overview` 的既有 payload，不新增交易终端能力，重点回答四个问题：

- 哪些宏观/估值指标已经有本地、带来源和日期的观测值，可以进入 AI 摘要引用范围。
- 哪些指标仍然是 `needs_adapter`、`needs_manual_seed`、`no_data` 或 `future`，下一步应补适配器、人工 seed 还是等待未来文档能力。
- 当前 AI 摘要使用了哪些本地 citation，哪些只是 source-readiness 缺口，模型是 LLM 生成还是 deterministic fallback。
- 官方/合法来源链接、seed 模板、导入命令、复核清单和引用边界分别是什么。

页面顶部先展示 AI 证据摘要、引用计数、诊断和安全边界，再展示宏观/估值指标表。指标表会列出 code、名称、地区、分类、value、as-of、source、AI 可引用状态、source/method metadata 是否存在，以及 no-data 原因。缺失值显示为“暂无”/`N/A`，不会渲染成 0。

来源就绪度区域会按类别展示 FRED、PBOC、中国 M2、巴菲特指标组件、已生成报告、已存新闻、未来文档和用户 seed 文件等来源。外部链接只用于人工核对；seed 模板只用于准备本地 JSON/CSV。只有导入并通过校验的本地 observation、已生成报告和已存新闻，才能被 AI 当作 citation。

证据中心的安全边界与首页一致：它用于信息汇总、缺口追踪和 AI 研究摘要，不输出买入、卖出、持有、目标价、仓位或执行建议。

### 数据可信度标签

首页、行情 ticker、市场概览、个股详情页、分时图、报告列表和报告详情现在会尽量展示数据可信度和来源信息。常见标签含义如下：

- `新鲜` / `可用`：后端 payload 明确返回可用状态或 fresh 状态。若没有 `is_realtime=true`，仍不能把它理解为实时行情。
- `延迟`：上游声明数据是 delayed，页面会在可用时显示延迟分钟数。
- `陈旧`：数据存在但 freshness 已过期，适合提示用户刷新或重新采集。
- `模拟`：来自 mock、demo 或 fixture；只能用于界面演示、测试或 contract 验证，不能当作真实市场信号。
- `降级`：provider 不支持、接口失败、权限不足或只有部分区块可用。降级状态不是市场结论。
- `无数据`：当前 provider、日期范围或本地数据库没有返回可验证数据。
- `不可用`：功能或 provider 当前不可用。
- `未知`：payload 没有足够 metadata；系统不会默认把未知状态标成实时或新鲜。

这些标签旁边可能出现 `provider`、`source`、`as_of`、`generated_at`、`delay`、`cache`、`session` 和原因说明。它们用于回答“这个数字从哪里来、是否延迟、是否命中缓存、为什么没有数据”。如果某个页面显示 mock、degraded、no_data、unavailable 或 unknown，应先把它理解为数据能力或来源限制，而不是市场本身发生了相同状态。

### 宏观/估值指标与 AI 日摘要

首页现在包含一个宏观与估值观察区。P0 指标库包括：

- 巴菲特指标：中国、香港、美国。
- 利率：美国 10 年期国债收益率、2 年期国债收益率、10Y-2Y 利差。
- 通胀：美国 CPI 同比。
- 流动性：美国 M2 同比、中国 M2 同比。

这些指标优先强调来源透明和缺口透明：

- 如果还没有录入可审计观测值，页面会显示 `no_data` 或“尚未录入可审计观测值”，不会把缺失数据当作 0。
- 如果存在观测值，页面会显示 value、as-of 日期、source、components/method metadata。
- 手工 seed 或 demo 数据必须在 source/components 里明确标注，不能伪装成实时宏观源。

AI 日摘要当前是 deterministic brief，而不是 LLM 交易建议。它会按 “What changed / Why it matters / What to watch next / Data gaps” 汇总：

- 已有宏观/估值信号。
- 尚未接入或未审计的数据缺口。
- 关注标的日线新鲜度。
- 已生成报告和 dashboard 诊断入口。

使用边界：

- 摘要用于生成研究问题和下一步查证清单，不给出买入/卖出/持有指令。
- 宏观指标目前是 definitions-first MVP；没有接入官方 source adapter 的项目应被视为待补数据，而不是市场结论。
- 当前 dashboard brief 已包含 citation-aware narrative：如果配置了 OpenAI-compatible LLM 和 API key，系统会把已有 brief sections、citations、diagnostics 与 information-source gaps 交给模型综合；如果没有配置、模型失败、返回空内容或引用了未知 citation ID，则自动降级为 deterministic fallback。
- narrative 只能使用 dashboard payload 中已有的 citation ID。`needs_adapter`、`needs_manual_seed`、`no_data`、`future` 等 source-readiness 项会被总结成数据缺口和下一步动作，不能被当作事实引用。

### 可审计宏观 seed 导入

对于 FRED、PBOC、巴菲特指标组件等需要人工复核或暂时没有 adapter 的数据，可以先用本地 seed 文件导入。命令示例：

```bash
python scripts/import_market_indicator_seeds.py path/to/macro-seeds.json
python scripts/import_market_indicator_seeds.py path/to/macro-seeds.csv
```

JSON 可以是顶层数组，也可以是 `{ "observations": [...] }`；CSV 使用 `code,as_of,value,source,components_json`。每条记录至少需要：

- `code`：例如 `buffett_indicator_us`、`us_10y_yield`、`cn_m2_yoy`。
- `as_of`：观测日期，格式为 `YYYY-MM-DD`。
- `value`：十进制数值。
- `source`：人工复核后的来源说明。
- `components` / `components_json`：必须包含 `source_url`、`source_series_id`、`source_document` 或 `source_name` 之一，也必须包含 `methodology`、`calculation`、`notes` 或 `review_note` 之一。

导入会先校验整个文件；只要有一行缺少审计字段、日期/数值格式错误或指标代码不存在，就不会写入任何观测值。成功导入后，这些观测值会进入首页宏观指标、信息源就绪度和 AI 摘要证据层。

使用边界：

- 这只是离线、人工审计导入，不会实时调用官方宏观 API。
- seed 文件里的值必须来自你已核对的合法来源，不能把估算、猜测或未授权抓取当作事实数据。
- 导入后的指标仍然是研究证据，不构成买卖建议。

### FRED 官方宏观刷新

如果已经配置 FRED API key，可以用官方 FRED API 刷新美国利率、利差、通胀和流动性观察值。命令示例：

```powershell
$env:FRED_API_KEY="..."
python scripts/refresh_fred_macro_indicators.py --series rates --latest-only --dry-run
python scripts/refresh_fred_macro_indicators.py --series all --start 2025-01-01 --end 2026-07-06
```

当前覆盖：

- `DGS10` -> `us_10y_yield`。
- `DGS2` -> `us_2y_yield`。
- `T10Y2Y` -> `us_10y_2y_spread`。
- `CPIAUCSL` -> `us_cpi_yoy`，用同月去年值派生 YoY。
- `M2SL` -> `us_m2_yoy`，用同月去年值派生 YoY。

刷新成功后，观测值会写入本地 `MarketIndicatorObservation`，并保留 FRED series ID、source URL、retrieved_at、methodology 或 calculation。FRED 返回的缺失值，例如 `"."`，会被跳过，不会写成 0。缺少 API key 时脚本返回 `WARN`，不会请求网络；provider 或校验失败时返回 `FAIL`。

使用边界：

- 这是显式 opt-in 的维护命令，不是自动定时任务。
- FRED 链接、source readiness 和 seed 模板仍然不是 AI citation。
- 只有成功写入本地、带 source/as-of/components 的观测值，才能被首页宏观指标和 AI 摘要引用。

首页的信息源就绪度卡片会为部分宏观/估值来源展示 seed 模板，例如 FRED 利率、FRED CPI/M2、PBOC 中国 M2、巴菲特指标组件和通用用户 seed 文件。模板会列出目标指标代码、必填字段、JSON/CSV 占位行、复核清单和导入命令。模板里的 `YYYY-MM-DD`、`<reviewed decimal>`、`<operator review note>` 等都是占位符，不是市场数据，也不会自动写入数据库。

使用这些模板时，应先从官方或合法来源核对数据，再替换占位符，保留 source URL/series ID/source name 以及 methodology/calculation/notes/review_note。只有当你运行导入命令并通过校验后，观测值才会进入本地 evidence 层；模板本身、外部链接和未导入的行都不能被 AI 当作 citation。

### 信息源就绪度

首页现在也会展示“信息源就绪度”。这个模块不是实时数据源，也不是数据授权系统；它是个人研究 cockpit 的缺口地图，用来说明哪些来源已经有本地证据、哪些还需要适配器、哪些需要人工 seed，哪些只是未来方向。

当前 source registry 覆盖：

- FRED 美国利率、通胀、流动性候选序列，例如 DGS10、DGS2、T10Y2Y、CPIAUCSL、M2SL。
- PBOC / 中国 M2 这类需要人工复核或官方来源策略的宏观数据。
- 巴菲特指标的人工估值组件，例如市值、GDP、公式和来源说明。
- 本地已生成报告和已存新闻文章。
- SEC filings、公告、transcripts 等后续文档来源。
- 用户人工整理的 seed files。

每个需要补数据的来源会尽量显示“收集指引”“引用边界”和“官方/合法来源链接”。例如 FRED 利率项会给出 DGS10/DGS2/T10Y2Y 链接，巴菲特指标组件会给出公开市值/GDP 与 GDP 组件来源，SEC 文档项会给出官方检索入口。点击这些链接只是帮助你去官方或合法页面核对资料，不代表系统已经接入自动抓取、自动入库或文档授权。

引用边界尤其重要：这些外部链接本身不是 AI citation。只有当你把复核后的 observation、报告、新闻或文档摘要以本地可审计形式保存下来，并带有 source、as-of、methodology/notes 等 metadata 后，AI 摘要才可以把它当作证据引用。

状态含义：

- `configured`：当前本地数据库已有可引用证据，例如已生成报告、已存新闻或已录入宏观观测值。
- `needs_adapter`：来源清楚，但还没有实现官方 adapter 或导入流程。
- `needs_manual_seed`：需要用户或维护者人工复核来源和方法后录入。
- `no_data`：本地表或 evidence store 还没有数据。
- `future`：未来可做，但当前不能被 AI 当作已接入来源引用。

使用边界：

- AI 只能安全总结 `configured` 且带 source/as-of/metadata 的证据。
- `needs_adapter`、`needs_manual_seed`、`future` 会被当作数据缺口和下一步行动，而不是事实依据。
- 对 filings/transcripts/研报等难收集资料，必须先明确合法来源、授权边界和引用策略；不要把未授权抓取当作产品能力。

### 热点板块状态解释

热点板块功能现在采用 provider-backed MVP contract：后端 `GET /sectors/hot` 会返回统一的板块分类、资金流口径、数据源、时间戳、实时/延迟状态和成分股信息；前端会把这些元数据直接展示给用户。

新增的专业化元数据包括：

- `breadth` / 广度：展示上涨、下跌、平盘成分股数量和 A/D 比例。若 provider 没有可验证成分股表现，页面会显示不可用，而不是把缺失数据当作 0。
- `constituent_contribution` / 成分股贡献：在 provider 或派生输入可用时展示正贡献和负贡献成分股。当前没有完整权重/资金流时，会以已验证成分股变化或 provider 明确字段为基础，不把 mock 数据伪装成真实贡献。
- `taxonomy` / 分类版本：展示当前规范化分类版本，便于理解不同 provider 的板块分类差异。
- `history` / 轮动历史：只有存在明确快照元数据时才展示；当前没有生产级持久化快照时会显示“暂无可验证快照”。

页面上的数据模式含义如下：

- `live` / 实时数据：provider 明确返回经过验证的实时板块表现或资金流。
- `delayed` / 延迟数据：provider 返回可用但延迟的板块表现或资金流，页面会显示延迟分钟数。
- `demo` / 演示数据：用于演示交互，不应作为真实市场数据。
- `mock` / 模拟数据：静态 fixture 或测试数据；当前默认 fallback 就属于 `degraded + mock`。
- `none` / 不可用：没有可展示的板块数据，通常是 provider 不支持、接口失败或字段无法验证。

资金流显示包含“流入 / 流出 / 持平 / 未知”和金额。金额口径由 payload 的 `flow_definition` 描述，例如统计窗口、币种、单位和 provider 方法论。不同 provider 的“主力资金”“净流入”“板块资金流”口径可能不同，因此不要跨 provider 直接比较金额，除非口径一致。

使用边界：

- 默认静态热点板块仅用于 UI 和 contract 展示，不代表真实市场排名。
- 如果页面显示 mock/demo/degraded/unavailable，应把它理解为数据能力限制，而不是市场信号。
- 广度、贡献和轮动历史是附加解释层；不可用代表 provider/存储能力不足，不代表真实市场为 0 或无变化。
- 当真实 provider（例如 AkShare/Tushare/Eastmoney 类接口）可用时，页面会显示 provider、as-of、延迟和 verified 相关信息，便于判断数据可靠性。

## 个股详情页

个股详情页是研究单个标的的主要入口，包含行情快照、K 线图、分时图、深度数据、指标、基本面、新闻和报告引用。

### K 线图与指标工作台

K 线图基于日线 OHLCV 数据展示。当前支持：

- 时间范围切换，例如近月、近年、YTD 或全部数据。
- 图表库原生滚动/缩放交互。
- 移动平均线 MA。
- BOLL 布林线。
- 成交量。
- MACD。
- RSI。
- KDJ。
- 本地图表工作区：可在当前浏览器保存/恢复/重置当前范围、指标开关和研究注释。
- 研究注释：可记录支撑/压力位、观察点或复盘备注；这些注释仅用于研究流程，不是交易指令。

使用建议：

- MA、BOLL 和 KDJ 需要一定历史数据；数据不足时指标可能为空或从后续数据点开始显示。
- RSI、MACD、KDJ 是技术分析辅助信号，不代表买卖建议。
- 图表工作区当前仅保存在本机浏览器 localStorage，不会同步到账号或其他设备；清理浏览器数据可能删除已保存布局。
- 当前注释是轻量研究笔记，不包含完整画线、拖拽编辑、告警联动或下单能力。
- 若 K 线区块显示“暂无数据”，通常表示当前 provider、日期范围或本地数据库没有可用日线。

### 分时图

分时图用于展示分钟价格、均价、昨收参考和成交量。

当前状态：

- UI 和 API contract 已存在。
- yfinance provider 现在可以在可用窗口内返回已验证 `1m` 分钟线。
- yfinance 分钟线通常有历史留存窗口限制；较早日期、周末、节假日或 provider 空响应会返回 `no_data`，而不是伪造数据。
- 历史闭市交易日的 yfinance `1m` 数据在首次 verified provider 成功返回后会写入持久分钟缓存；同一标的、provider、日期和周期的后续请求可从缓存返回 `source="cache"`，避免重复打 provider。
- 分时 payload 现在会附带 `freshness` 和 `session` 元数据，用于解释数据是否来自 provider fetch、是否命中缓存、是否因非交易日/未来日期/不支持 provider 被跳过，以及当前是否只是可靠性 metadata 而不是 production 级实时行情系统。
- mock、AkShare、Tushare 当前仍不作为已验证分钟线 provider；系统会返回 `degraded`，页面显示“当前数据源暂不支持分时数据”等明确提示。
- 系统不会用日线、静态 fixture 或估算值冒充分钟线。

用户应如何理解：

- 如果分时图显示真实曲线，表示后端返回了 `status="ok"` 的分钟点位。
- 如果分时图显示 `no_data` 或降级提示，不代表市场没有交易，只代表当前 provider、日期或权限没有返回可验证分钟数据。
- 分时图的昨收参考线可来自日线数据，但日线数据只用于参考线，不会被用来生成分钟点位。
- `freshness.cache_status` 可用于区分 `hit`（历史闭市缓存命中）、`miss`（缓存未命中并走 provider）、`skipped`（session/provider policy 明确跳过）和 `unavailable`（没有可用数据库 session 或缓存写入/读取不可用）。这不是完整 realtime market-data plant；当前盘、半日市、盘前盘后、实时推送、更长历史窗口和多 provider 验证仍是后续能力。
- 后续接入更多真实分钟级 provider 后，该区块可继续复用当前 contract。

### 深度数据（五档 / 逐笔 / 大单 / 资金流）

深度数据卡片包括四类信息：

- 五档买卖盘：买一到买五、卖一到卖五的价格、数量、金额和委托数。
- 逐笔成交：成交时间、方向、价格、数量和金额。
- 大单追踪：超过明确金额阈值的成交记录。
- 资金流摘要：净流入、主力净流入、散户净流入和口径说明。

当前状态：

- UI 和 API contract 已存在。
- 后端现在只通过显式 `fetch_market_depth` provider 方法读取深度数据，不会复用日线、分时线或 mock fixture。
- 如果某个 provider 返回已验证的五档盘口、逐笔成交或资金流，页面会渲染真实行，并显示 provider、as-of、延迟和分区状态。
- 深度数据支持局部可用：例如五档盘口可为 `ok`，逐笔成交、资金流仍可保持 `degraded` 并显示各自原因。
- AkShare 现在具备显式 `fetch_market_depth` 候选路径，可在环境、接口和 schema 可用时尝试解析盘口；但它仍不是广泛 production-verified Level-2 能力，缺少 opt-in live smoke、接口变更监控和权限验证时仍应视为候选/可降级。

用户应如何理解：

- “不可用”或“暂无已验证盘口数据”是数据源能力限制，不是个股没有盘口。
- 大单金额阈值默认是 `1,000,000`，仅在有已验证逐笔成交数据时才用于筛选大单。
- 如果只有部分分区可用，应只信任标记为 `ok` 的分区；其他 `degraded` 分区仍表示该 provider 没有可验证数据。

## 智能推荐

智能推荐模块提供研究线索，而不是自动交易建议。当前支持的线索类型包括：

- 突破。
- 超跌反弹。
- 成交异常。
- 强势动量。

推荐信号现在具备第一层 deterministic 历史评估能力，可在服务层基于历史日线计算：

- 样本数。
- 1 / 5 / 20 等前瞻窗口收益。
- 命中率。
- 平均 / 中位前瞻收益。
- 信号后最大回撤。
- 有 benchmark 时的相对收益。
- 无足够历史、无信号、无 benchmark 或窗口无后续数据时的诊断。

使用建议：

- 推荐结果应与 K 线、成交量、基本面、新闻和风险偏好一起分析。
- 推荐算法基于可用行情和指标数据；当 provider 或日期范围没有足够数据时，推荐可能为空。
- 首页推荐卡片不再默认宣称“实时推荐”。如果后端提供 `status`、`provider`、`source`、`generated_at` 或 diagnostics，页面会展示这些元数据；`provider_error`、`no_data` 等诊断表示推荐线索的数据基础存在缺口。
- 历史评估指标只说明过去样本表现，样本少、数据缺口、幸存者偏差和不同市场交易日历都会影响解释。
- 推荐结果不会自动下单，也不保证收益。

## 对比分析

对比分析工具支持多标的横向比较和相关性分析。

当前适用场景：

- 比较同一行业或同一主题下多个标的走势。
- 观察多个资产之间的相关性。
- 辅助发现组合中过度集中的风险。

使用限制：

- 相关性依赖历史价格序列，样本过少时结论不稳定。
- 跨市场、跨币种和不同交易日历可能影响对比结果。

## AI 报告、AI 摘要与 AI 助手

当前平台已经具备 AI 报告和 AI 摘要类能力，例如每日个股报告、报告引用和研究辅助摘要。个股详情页也已上线 **AI 市场助手 MVP**。

报告中心现在会显示 `source_summary` 中的 `source`、`price_source`、`provider` 和关联 `task_run_id`。如果生成报告时没有显式 provider，前端会提示将使用后端默认数据源；若默认数据源是 mock 或 fallback，应以报告源摘要和引用为准，不要把报告内容当作 provider-verified 结论。

AI 市场助手当前能力：

- 在个股详情页价格摘要下方提供聊天式入口。
- 支持围绕单个标的提问，例如近期走势、主要风险和数据缺口。
- 后端通过 `POST /assistant/market` 聚合日线、指标、基本面、新闻舆情和已生成报告上下文。
- 回答会返回引用数据、上下文摘要、诊断信息和免责声明。
- 引用现在支持可选 metadata，例如 `source_type`、`as_of`、`provider`、`retrieved_at`、`excerpt` 和新闻 URL；页面会把有 URL 的引用显示为可点击链接。
- 如果 LLM 回答引用了不存在的 citation ID，后端会降级到 deterministic fallback 或显示 `CITATION_UNKNOWN_ID` 诊断，而不是把幻觉引用当作有效来源。
- 当 LLM 未配置、数据缺失或辅助上下文不可用时，会返回 deterministic fallback、`no_data` 或 `degraded` 诊断，而不是编造市场数据。

使用边界：

- AI 助手不会下单，不提供个性化投资建议，也不会给出必须买入/卖出/持有的交易指令。
- 当前 MVP 主要基于日线和平台内已验证上下文；filings、transcripts、exchange announcements、向量检索、多轮研究笔记本和 watchlist 级监控仍是后续能力。
- 实时行情、分时、Level-2、逐笔和资金流仍取决于后续 provider 管线。
- 对“能不能买”“该不该卖”等问题，系统应转为风险与证据框架，而不是直接交易指令。

## 专业信息平台对标

当前平台更适合对标信息聚合与 AI 研究产品，而不是专业交易终端。Koyfin、MacroMicro、TradingView、AlphaSense、FRED、World Bank、SEC EDGAR 和 Trading Economics 这类平台/数据源的启发点是：把分散来源组织成可追踪 dashboard、宏观图表、日历、watchlist、研究语料和 AI 摘要；本平台的重点则是个人使用、来源透明、数据缺口透明和 AI 研究辅助。

| 对标对象 | 成熟平台能力 | 当前已满足 | 主要缺口 |
|---|---|---|---|
| Koyfin / MacroMicro | 宏观、估值、经济周期、市场图表和跨资产 dashboard | 已有专门证据中心、宏观/估值 definitions-first 指标、no-data-safe 展示、source readiness 和 seed 模板 | 还缺官方宏观 adapter、发布日历、跨指标图表和可复用宏观专题页。 |
| TradingView / Yahoo Finance 类工具 | watchlist、图表、新闻、日历、筛选器和个人跟踪工作流 | 已有首页汇总、watchlist、K 线/指标、推荐线索、报告和 provider/degraded 状态 | 还缺 watchlist 事件监控、日/周 digest、保存的研究问题和更系统的提醒。 |
| AlphaSense 类研究产品 | 对 filings、transcripts、新闻和研究资料做 AI 搜索、监控、摘要和引用 | 已有 citation-aware dashboard narrative、AI 报告和个股 AI assistant 的引用校验 | 还缺合法研究语料库、文档 ingest policy、保存的 AI follow-up 和主题追踪。 |
| FRED / World Bank / SEC EDGAR / Trading Economics | 官方或 API 化宏观、公司文档、经济日历和指标源 | 已有 FRED opt-in adapter、官方/合法来源链接、导入边界、manual seed import 和 source-to-seed 模板 | 还缺 source capability matrix、宏观发布日历、更多官方源和 license/freshness 运营记录。 |

因此，当前实现已经满足一个个人研究 cockpit 的 MVP：它能把市场、watchlist、报告、推荐、新闻、宏观指标、来源缺口和 AI 摘要放到同一工作台，并通过证据中心明确区分“可引用证据”和“还需要收集/复核的来源”。但它还不是完整的信息平台：数据源仍以人工 seed 和本地证据为主，官方宏观源、文档语料、日历、watchlist 级监控和历史化 AI digest 仍是后续重点。

不建议优先追逐的能力：

- 实盘下单、券商账户、订单路由和交易执行。
- 低延迟实时行情、Level-2 全量盘口、逐笔订单流和盘口热力图。
- 大规模专业终端布局系统、复杂脚本市场和机构级权限/合规工作流。
- 没有来源、没有日期、没有授权边界或无法审计的数据抓取。

## 优先优化路线

1. **P0 宏观发布日历与缺口追踪**：在 FRED opt-in adapter 的基础上，为 CPI、M2、利率、GDP/市值组件等核心指标建立 release calendar / freshness policy，让首页直接显示“下一次该更新什么、当前缺哪一项”。
2. **P1 source capability matrix**：记录每个宏观源的 adapter 状态、license/usage note、retrieved_at、失败诊断和人工复核要求。
3. **P1 日/周 AI digest 历史**：把 dashboard brief 保存为可回看的日/周研究记录，包含 what changed、why it matters、what to watch next、citations、diagnostics 和 source gaps。
4. **P1 watchlist 事件监控**：把 watchlist 价格异动、报告更新、新闻事件、宏观发布和 source readiness 变化汇总成个人研究 inbox。
5. **P1 hard-to-find source notebook**：支持保存用户复核过的链接、摘录、seed 文件、计算备注和 AI follow-up，形成可引用的本地研究资料库。
6. **P2 文档/公告语料 ingest**：在合法来源和引用策略明确后，再接入 SEC filings、交易所公告、电话会 transcript 或用户上传文档；默认只保存 metadata/摘要/引用，不假设可随意抓取全文。
7. **P2 研究级筛选与提醒**：围绕宏观阈值、watchlist 异动、报告更新和资料更新做提醒；推荐继续作为“研究线索生成器”，输出证据、历史样本和风险，而不是直接买卖建议。
8. **P2 图表与个人工作区增强**：增加跨指标图表、参数持久化、轻量注释和 saved view；仍保持研究辅助定位，不把 terminal parity 作为近期目标。
