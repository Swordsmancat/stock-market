from dataclasses import dataclass


@dataclass(frozen=True)
class MarketIndexDefinition:
    code: str
    name: str
    name_zh: str
    region: str
    market: str
    currency: str
    provider_symbols: dict[str, str]
    display_order: int


DEFAULT_MARKET_INDICES: tuple[MarketIndexDefinition, ...] = (
    MarketIndexDefinition(
        code="cn_shanghai_composite",
        name="Shanghai Composite",
        name_zh="上证指数",
        region="CN",
        market="CN",
        currency="CNY",
        provider_symbols={"mock": "SH000001", "yfinance": "000001.SS", "akshare": "000001", "tushare": "000001"},
        display_order=10,
    ),
    MarketIndexDefinition(
        code="cn_shenzhen_component",
        name="Shenzhen Component",
        name_zh="深证成指",
        region="CN",
        market="CN",
        currency="CNY",
        provider_symbols={"mock": "SZ399001", "yfinance": "399001.SZ", "akshare": "399001", "tushare": "399001"},
        display_order=20,
    ),
    MarketIndexDefinition(
        code="cn_chinext",
        name="ChiNext",
        name_zh="创业板指",
        region="CN",
        market="CN",
        currency="CNY",
        provider_symbols={"mock": "SZ399006", "yfinance": "399006.SZ", "akshare": "399006", "tushare": "399006"},
        display_order=30,
    ),
    MarketIndexDefinition(
        code="cn_csi_300",
        name="CSI 300",
        name_zh="沪深300",
        region="CN",
        market="CN",
        currency="CNY",
        provider_symbols={"mock": "CSI300", "yfinance": "000300.SS", "akshare": "000300", "tushare": "000300"},
        display_order=40,
    ),
    MarketIndexDefinition(
        code="cn_csi_500",
        name="CSI 500",
        name_zh="中证500",
        region="CN",
        market="CN",
        currency="CNY",
        provider_symbols={"mock": "CSI500", "yfinance": "000905.SS", "akshare": "000905", "tushare": "000905"},
        display_order=50,
    ),
    MarketIndexDefinition(
        code="hk_hang_seng",
        name="Hang Seng Index",
        name_zh="恒生指数",
        region="HK",
        market="HK",
        currency="HKD",
        provider_symbols={"mock": "HSI", "yfinance": "^HSI", "akshare": "HSI", "tushare": "HSI"},
        display_order=60,
    ),
    MarketIndexDefinition(
        code="hk_hang_seng_tech",
        name="Hang Seng Tech Index",
        name_zh="恒生科技",
        region="HK",
        market="HK",
        currency="HKD",
        provider_symbols={"mock": "HSTECH", "yfinance": "^HSTECH", "akshare": "HSTECH", "tushare": "HSTECH"},
        display_order=70,
    ),
    MarketIndexDefinition(
        code="us_sp_500",
        name="S&P 500",
        name_zh="标普500",
        region="US",
        market="US",
        currency="USD",
        provider_symbols={"mock": "SPX", "yfinance": "^GSPC", "akshare": "SPX", "tushare": "SPX"},
        display_order=80,
    ),
    MarketIndexDefinition(
        code="us_nasdaq_composite",
        name="Nasdaq Composite",
        name_zh="纳斯达克",
        region="US",
        market="US",
        currency="USD",
        provider_symbols={"mock": "IXIC", "yfinance": "^IXIC", "akshare": "IXIC", "tushare": "IXIC"},
        display_order=90,
    ),
    MarketIndexDefinition(
        code="us_dow_jones",
        name="Dow Jones Industrial Average",
        name_zh="道琼斯",
        region="US",
        market="US",
        currency="USD",
        provider_symbols={"mock": "DJI", "yfinance": "^DJI", "akshare": "DJI", "tushare": "DJI"},
        display_order=100,
    ),
)


def resolve_provider_symbol(index: MarketIndexDefinition, provider_name: str) -> str:
    normalized_provider_name = provider_name.strip().lower()
    return index.provider_symbols.get(normalized_provider_name) or index.provider_symbols["mock"]
