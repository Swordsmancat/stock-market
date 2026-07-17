# 宏观经济数据来源与换源指南

本文档是宏观经济看板的数据来源登记表。实现入口位于
`packages/providers/akshare_macro_provider.py`、
`packages/services/market_indicators.py` 和
`apps/api/routers/market_indicators.py`。

## 数据落库与读取边界

- 所有成功观测最终写入 `MarketIndicatorObservation`，指标定义存放在
  `MarketIndicator`。
- 页面 GET `GET /market-indicators/dashboard` 只读数据库，不请求外部来源。
- 中国宏观公开数据只在显式调用
  `POST /market-indicators/official-refresh/akshare-cn` 时刷新。
- 每条观测的 `components` 必须保存 `provider`、`provider_function`、
  `source_name`、`source_url`、`source_date_field`、`source_value_field`、
  `retrieved_at` 和 `methodology`。这些字段用于审计，也用于判断历史数据究竟来自哪个来源。
- 空值、非法日期、非有限数值和字段不匹配均跳过，不能写成 `0`，也不能用其他周期数据补齐。

## 当前 23 项指标来源

### 中国及中美公开宏观来源（AkShare 适配层）

AkShare 是调用库，不是原始发布机构。下表同时登记 AkShare 函数和实际网页上游，换源时必须保留这一区分。

| 指标代码 | 含义 | AkShare 函数 | 当前上游页面 | 日期字段 | 数值字段 |
|---|---|---|---|---|---|
| `cn_lpr_1y` | LPR 1年期 | `macro_china_lpr` | 东方财富 LPR | `TRADE_DATE` | `LPR1Y` |
| `cn_lpr_5y` | LPR 5年期 | `macro_china_lpr` | 东方财富 LPR | `TRADE_DATE` | `LPR5Y` |
| `cn_shibor_overnight` | SHIBOR 隔夜 | `macro_china_shibor_all` | 金十数据 SHIBOR | `日期` | `O/N-定价` |
| `cn_10y_yield` | 中国10年期国债收益率 | `bond_zh_us_rate` | 东方财富中美国债收益率 | `日期` | `中国国债收益率10年` |
| `us_10y_yield` | 美国10年期国债收益率 | `bond_zh_us_rate` | 东方财富中美国债收益率 | `日期` | `美国国债收益率10年` |
| `cn_cpi_yoy` | 中国 CPI 同比 | `macro_china_cpi` | 东方财富 CPI | `月份` | `全国-同比增长` |
| `cn_ppi_yoy` | 中国 PPI 同比 | `macro_china_ppi` | 东方财富 PPI | `月份` | `当月同比增长` |
| `cn_retail_sales_yoy` | 社会消费品零售总额同比 | `macro_china_consumer_goods_retail` | 东方财富消费数据 | `月份` | `同比增长` |
| `cn_manufacturing_pmi` | 制造业 PMI | `macro_china_pmi` | 东方财富 PMI | `月份` | `制造业-指数` |
| `cn_gdp_yoy` | 中国 GDP 累计同比 | `macro_china_gdp` | 东方财富 GDP | `季度` | `国内生产总值-同比增长` |
| `cn_exports_yoy` | 当月出口额同比 | `macro_china_hgjck` | 东方财富海关进出口 | `月份` | `当月出口额-同比增长` |
| `cn_imports_yoy` | 当月进口额同比 | `macro_china_hgjck` | 东方财富海关进出口 | `月份` | `当月进口额-同比增长` |
| `cn_m2_yoy` | 中国 M2 同比 | `macro_china_money_supply` | 东方财富货币供应量 | `月份` | `货币和准货币(M2)-同比增长` |
| `cn_m1_yoy` | 中国 M1 同比 | `macro_china_money_supply` | 东方财富货币供应量 | `月份` | `货币(M1)-同比增长` |
| `cn_m0_yoy` | 中国 M0 同比 | `macro_china_money_supply` | 东方财富货币供应量 | `月份` | `流通中的现金(M0)-同比增长` |
| `cn_tax_revenue_yoy` | 全国税收收入累计同比 | `macro_china_national_tax_receipts` | 东方财富全国税收收入 | `季度` | `较上年同期` |

当前上游页面：

| Family | URL |
|---|---|
| LPR | <https://data.eastmoney.com/cjsj/globalRateLPR.html> |
| SHIBOR | <https://datacenter.jin10.com/reportType/dc_shibor> |
| 中美国债收益率 | <https://data.eastmoney.com/cjsj/zmgzsyl.html> |
| CPI | <https://data.eastmoney.com/cjsj/cpi.html> |
| PPI | <https://data.eastmoney.com/cjsj/ppi.html> |
| 社会消费品零售 | <https://data.eastmoney.com/cjsj/xfp.html> |
| PMI | <https://data.eastmoney.com/cjsj/pmi.html> |
| GDP | <https://data.eastmoney.com/cjsj/gdp.html> |
| 货币供应 | <https://data.eastmoney.com/cjsj/hbgyl.html> |
| 海关进出口 | <https://data.eastmoney.com/cjsj/hgjck.html> |
| 全国税收收入 | <https://data.eastmoney.com/cjsj/qgsssr.html> |

上游 URL 的唯一代码登记位置是
`AKSHARE_MACRO_SOURCE_URLS`，函数、日期字段、数值字段和目标指标的唯一登记位置是
`AKSHARE_MACRO_FAMILIES`。不要在 API 或前端复制这些映射。

### FRED 美国宏观来源

| 指标代码 | FRED Series | 处理方式 |
|---|---|---|
| `us_10y_yield` | `DGS10` | 原值，百分比 |
| `us_2y_yield` | `DGS2` | 原值，百分比 |
| `us_10y_2y_spread` | `T10Y2Y` | 原值，百分点 |
| `us_cpi_yoy` | `CPIAUCSL` | 当前值与上年同期值计算同比 |
| `us_m2_yoy` | `M2SL` | 当前值与上年同期值计算同比 |

FRED 映射的唯一代码登记位置是 `FRED_MACRO_SERIES`。刷新需要
`FRED_API_KEY`，操作方式见 [官方宏观刷新](./official-macro-refresh.md)。
FRED API 默认基址为 <https://api.stlouisfed.org/fred>，系列说明页为
`https://fred.stlouisfed.org/series/<SERIES_ID>`。

`us_10y_yield` 同时存在 AkShare/东方财富和 FRED 两条可选来源。每一条已入库观测都保留自己的来源元数据；不要仅凭指标代码假设来源。若要求统一为 FRED，应停止 AkShare 对该代码的写入并显式执行 FRED 刷新。

### World Bank 市场估值来源

| 指标代码 | 国家/地区 | World Bank Indicator | 辅助上下文 |
|---|---|---|---|
| `buffett_indicator_cn` | `CHN` | `CM.MKT.LCAP.GD.ZS` | `NY.GDP.MKTP.CD` |
| `buffett_indicator_hk` | `HKG` | `CM.MKT.LCAP.GD.ZS` | `NY.GDP.MKTP.CD` |
| `buffett_indicator_us` | `USA` | `CM.MKT.LCAP.GD.ZS` | `NY.GDP.MKTP.CD` |

映射的唯一代码登记位置是 `WORLD_BANK_BUFFETT_TARGETS`。World Bank 数据为年度数据，允许自然滞后，不能描述为实时估值。
World Bank API 默认基址为 <https://api.worldbank.org/v2>，指标说明页为
<https://data.worldbank.org/indicator/CM.MKT.LCAP.GD.ZS>。

## 如何更换数据源

1. **先确认语义一致**：频率、单位、是否累计、是否季调、发布日期与观测期必须与现有指标定义一致。不一致时应新增指标代码，而不是悄悄替换。
2. **在 Provider 层接入**：新适配器输出规范化的 `code`、`as_of`、`value`、`source` 和完整 `components`。不要让 API 或页面解析供应商字段。
3. **保持指标代码稳定**：语义相同的换源继续写现有代码，因此数据库、看板和 AI citation 无需修改。
4. **显式切换刷新入口**：修改 service 的 refresh 组合或新增独立 POST/脚本；普通 GET 始终只读。
5. **保留历史来源**：不要批量改写旧 observation 的来源。新来源从切换日期开始写入，便于追溯。
6. **增加契约测试**：至少覆盖正常表格、升降序、空值、日期格式、字段变化、部分失败和错误脱敏。
7. **先 dry-run/测试，再写库**：确认同一日期重复刷新是幂等 upsert，且来源失败不会删除最后一次成功数据。

## 换源检查清单

- [ ] 原始发布机构、聚合网站和调用库分别记录。
- [ ] URL、函数/API、日期字段、数值字段已更新。
- [ ] 单位、频率、季调/累计口径与原指标一致。
- [ ] `components.methodology` 能说明计算和转换。
- [ ] 缺失值不会变成 0，也不会跨周期拼接。
- [ ] 历史旧来源记录未被覆盖或伪造。
- [ ] Provider、service、API 和页面测试通过。
- [ ] 本文档与代码中的唯一映射同步更新。

## 当前未覆盖项

DR007、国债期货、指数 PE/股息率、详细失业率、商品价格和财政支出尚未进入生产映射。接入前必须先验证来源语义和运行时字段，再按上述流程新增，不能仅根据页面截图填充。
