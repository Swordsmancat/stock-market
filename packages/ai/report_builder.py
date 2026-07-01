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


def _llm_analysis_prompt(context: ReportContext) -> str:
    return (
        f"你是股票研究助手。基于以下结构化数据，撰写一段 300 字以内的中文综合研判。"
        f"不要编造数据外的事实，不要给出买卖建议。\n\n"
        f"标的：{context.symbol}\n"
        f"截止：{context.as_of}\n"
        f"行情：{context.price_summary}\n"
        f"技术面：{context.indicator_summary}\n"
        f"基本面：{context.fundamental_summary}\n"
        f"消息面：{context.news_summary}\n"
    )


def resolve_combined_summary(context: ReportContext) -> str:
    from packages.ai.llm_factory import get_llm_provider
    from packages.services.platform_settings import get_platform_settings

    settings = get_platform_settings()
    if settings["llm_provider"] != "openai" or not str(settings["llm_api_key"]).strip():
        return context.combined_summary

    try:
        llm = get_llm_provider()
        generated = llm.generate(_llm_analysis_prompt(context)).strip()
        return generated or context.combined_summary
    except Exception:
        return context.combined_summary


def build_stock_report(context: ReportContext) -> str:
    combined_summary = resolve_combined_summary(context)
    citations = "\n".join(f"- {citation}" for citation in context.citations)
    return f"""# {context.symbol} AI 个股报告

数据截止时间：{context.as_of}

## 综合研判

{combined_summary}

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
