# MVP 验收手册

## 验收项

1. `/health` 返回 `{ "status": "ok" }`。
2. `/instruments` 返回 A股、港股、美股样例标的。
3. 技术指标测试覆盖 MA、RSI。
4. 新闻舆情测试覆盖去重和情绪分类。
5. AI 报告测试确认报告包含数据截止时间和引用。
6. Web 首页展示“股票分析平台”和三类市场样例标的。
7. 后台任务可以调度 mock 行情采集、指标计算和报告生成。
8. AI 组合建议和报告内容保持研究辅助边界，不连接实盘交易，也不自动下单。

## 验收命令

```bash
python -m pytest -v
npm run test:web
```

## 通过标准

- 后端 pytest 全部通过。
- 前端 Vitest 全部通过。
- API、任务、指标、舆情、AI 报告和 Web Dashboard MVP 骨架均可被测试覆盖。
