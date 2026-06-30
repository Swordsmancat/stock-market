from dataclasses import dataclass


@dataclass(frozen=True)
class ReportContext:
    symbol: str
    as_of: str
    price_summary: str
    indicator_summary: str
    news_summary: str
    citations: list[str]
    fundamental_summary: str = "No fundamental metrics are available yet."
    combined_summary: str = "No combined analysis is available yet."


def build_stock_report(context: ReportContext) -> str:
    citations = "\n".join(f"- {citation}" for citation in context.citations)
    return f"""# {context.symbol} AI 个股报告

数据截止时间：{context.as_of}

## 综合研判

{context.combined_summary}

## 行情摘要

{context.price_summary}

## 技术指标

{context.indicator_summary}

## 基本面指标

{context.fundamental_summary}

## 新闻舆情

{context.news_summary}

## 风险提示

本报告仅基于平台内可验证数据生成，用于研究辅助，不构成收益承诺或自动交易指令。

## 引用

{citations}
"""
