# 东方财富行业涨幅历史数据源

## 用途与入库范围

该链路为“宏观经济 / 证据中心”的行业涨幅历史榜提供数据。系统存储
东方财富一级行业板块代码、名称、交易日期、日涨跌幅、当日排名、来源、
抓取时间和非敏感审计元数据。默认读取最近 12 个已存储交易日、每日前
20 名；实际入库保留当日全部有效行业，便于之后调整展示数量。

## 当前来源

| 数据 | Provider | 上游接口 | 关键字段 |
|---|---|---|---|
| 一级行业板块清单 | Eastmoney push2 | `/api/qt/clist/get`, `fs=m:90 s:4` | `f12` 板块代码、`f14` 名称、`f3` 最新涨跌幅 |
| 行业日线历史 | Eastmoney push2his | `/api/qt/stock/kline/get`, `secid=90.BK...`, `klt=101` | `f51` 日期、`f59` 涨跌幅 |

实现入口为 `packages/providers/eastmoney_industry_rankings.py`。规范来源页固定为
`https://quote.eastmoney.com/center/gridlist.html#industry_board_1`，代表东方财富
行情中心一级行业口径。`industry_board_2` 和 `industry_board_3` 属于不同层级，
不得混入一级行业历史。系统也不会把带 Cookie、代理凭据或临时参数的请求
地址写入数据库。

## 访问降级顺序

1. 每个上游请求先尝试直连。
2. 直连连接、超时或状态失败时，若设置了 HTTP(S) 代理，则仅通过该代理
   再尝试一次。
3. 用户可手工填写 Cookie；系统不会读取浏览器 Cookie、自动登录、处理
   验证码或绕过网站访问控制。
4. 代理地址和 Cookie 均按密钥处理：公开设置只返回是否已配置，日志、
   API 错误、任务产物和排名表都不得包含其值。

## 刷新与读取边界

- `POST /sectors/industry-rankings/refresh?days=12` 才会访问上游并入库。
- `GET /sectors/industry-rankings?days=12&limit=20` 只读 PostgreSQL，页面加载
  不触发爬取。
- 批次在完成响应校验和排名计算后才提交；上游失败不会清空既有数据。
- 唯一键为 provider、taxonomy、industry code、trade date；重复刷新会修订
  同一观测，不会制造重复行。

## 后续更换来源

替换上游时保留 provider 适配器输出契约：板块代码、名称、交易日、有限
日涨跌幅、抓取时间。只有能够保留东方财富一级行业精确代码和名称口径的
来源，才可作为该数据集的降级来源；其他行业分类必须使用独立 provider /
taxonomy 和界面选项，不得混排。新来源不得直接写表或让 GET 触网；应由
service 统一计算排名、写审计字段和执行事务。
