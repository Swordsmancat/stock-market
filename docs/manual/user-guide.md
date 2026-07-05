# 股票分析平台用户手册

本手册面向平台使用者，说明当前可用的 Phase 2 / Phase 3 金融分析能力、入口、数据状态和风险边界。

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

## 首页市场看板

首页用于快速观察市场状态、关注标的、热点板块、智能推荐和报告摘要。

常见模块包括：

- 核心指数和市场概览。
- 关注标的 K 线摘要。
- 热点板块或板块资金流提示。
- 智能推荐线索，例如突破、超跌反弹、成交异常和强势动量。
- AI 报告、每日任务和运行状态入口。

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

使用建议：

- MA、BOLL 和 KDJ 需要一定历史数据；数据不足时指标可能为空或从后续数据点开始显示。
- RSI、MACD、KDJ 是技术分析辅助信号，不代表买卖建议。
- 若 K 线区块显示“暂无数据”，通常表示当前 provider、日期范围或本地数据库没有可用日线。

### 分时图

分时图用于展示分钟价格、均价、昨收参考和成交量。

当前状态：

- UI 和 API contract 已存在。
- yfinance provider 现在可以在可用窗口内返回已验证 `1m` 分钟线。
- yfinance 分钟线通常有历史留存窗口限制；较早日期、周末、节假日或 provider 空响应会返回 `no_data`，而不是伪造数据。
- 分时 payload 现在会附带 `freshness` 和 `session` 元数据，用于解释数据是否来自 provider fetch、是否因非交易日/未来日期/不支持 provider 被跳过，以及当前是否只是可靠性 metadata 而不是 production 级实时缓存。
- mock、AkShare、Tushare 当前仍不作为已验证分钟线 provider；系统会返回 `degraded`，页面显示“当前数据源暂不支持分时数据”等明确提示。
- 系统不会用日线、静态 fixture 或估算值冒充分钟线。

用户应如何理解：

- 如果分时图显示真实曲线，表示后端返回了 `status="ok"` 的分钟点位。
- 如果分时图显示 `no_data` 或降级提示，不代表市场没有交易，只代表当前 provider、日期或权限没有返回可验证分钟数据。
- 分时图的昨收参考线可来自日线数据，但日线数据只用于参考线，不会被用来生成分钟点位。
- `freshness.cache_status` 当前主要解释服务层是否跳过 provider 调用或走 provider fetch path；它不是完整的持久化分钟缓存功能。完整缓存、半日市、盘前盘后、实时推送和多 provider 验证仍是后续能力。
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

使用建议：

- 推荐结果应与 K 线、成交量、基本面、新闻和风险偏好一起分析。
- 推荐算法基于可用行情和指标数据；当 provider 或日期范围没有足够数据时，推荐可能为空。
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

## 专业金融网站/终端对比

与 TradingView、Bloomberg Terminal、Koyfin、AlphaSense、券商交易终端和 CN 零售终端相比，当前平台的定位更接近“内部研究平台 MVP + 自动化分析工作台”。

| 对比维度 | 当前平台状态 | 专业平台常见能力 | 差距 |
|---|---|---|---|
| 图表交互 | 已有交互式 K 线、区间切换、常用指标 | 多图层、多周期、多窗口、自定义脚本、告警 | 缺少脚本化指标、版面保存、多周期联动。 |
| 实时行情 | 日线和 yfinance `1m` 分钟线 MVP 可用；不支持 provider 会 no_data/degraded | 低延迟实时行情、盘前盘后、逐笔成交 | 分时已有 provider-backed MVP，但仍缺多 provider、长历史分钟线、实时推送和盘口/逐笔。 |
| 深度行情 | 有 provider-boundary MVP：显式 `fetch_market_depth` contract、分区状态和真实行渲染能力；AkShare 已有 fixture-tested 盘口候选路径 | Level-2、逐笔、订单流、盘口热力图 | 仍缺少已验证生产 Level-2 provider、逐笔/资金流生产验证、订单流分析和盘口热力图。 |
| 热点板块 | 已有 provider-backed contract、数据模式、资金流口径、成分股展示和降级提示；默认仍是 mock fallback | 板块资金流、涨跌家数、成分股贡献、实时/延迟口径、板块 taxonomy | 真实生产 provider、跨市场 taxonomy 治理、涨跌家数/贡献拆解和历史轮动分析仍待增强。 |
| 选股/推荐 | 有突破、超跌等研究线索 | 强筛选器、实时扫描、回测、告警 | 缺少条件选股器、回测和策略评价。 |
| AI 研究 | 有报告/摘要和 AI 市场助手 research-citation MVP；可展示 bars、指标、基本面、新闻、已生成报告引用和诊断 | 跨文档检索、公告/filing/transcript/电话会检索、持久研究会话、notebook workflow、实体/主题追踪 | 已增强引用和诊断，但仍缺生产级 filings/transcripts、向量检索、多轮研究空间和 watchlist 级叙事监控。 |
| 运维可用性 | 有任务监控、provider readiness、degraded 状态 | 数据 SLA、权限管理、审计日志、告警 | 缺少生产级数据 SLA 和权限模型。 |

## 优先优化路线

1. **AI 市场助手增强**：在现有 research-citation MVP 上继续扩展 filings/transcripts/announcements、向量检索、多轮上下文、研究 notebook、watchlist 级监控和实时行情联动。
2. **真实分时数据增强**：在 yfinance `1m` MVP 基础上补充更多 provider、分钟线缓存/存储、交易时段治理、盘前盘后和更长历史窗口。
3. **真实深度和大单数据管线**：在现有显式 `fetch_market_depth` boundary 上接入并验证 Level-2 / 逐笔 / 资金流 provider，保留 provider capability matrix 和局部可用状态。
4. **热点板块资金流增强**：在现有 provider-backed contract 上接入并验证真实生产 provider，补充涨跌家数、成分股贡献、历史轮动和跨市场 taxonomy 治理。
5. **专业图表增强**：增加多周期联动、指标参数持久化、告警和对比视图保存。
6. **策略验证与回测**：为智能推荐增加历史回测、命中率、回撤和风险统计。
