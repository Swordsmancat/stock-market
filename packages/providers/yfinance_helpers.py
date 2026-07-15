def map_symbol_to_ticker(symbol: str, market: str | None = None) -> str:
    normalized_symbol = symbol.strip().upper()
    normalized_market = market.strip().upper() if market and market.strip() else None
    if "." in normalized_symbol or normalized_symbol.startswith("^"):
        return normalized_symbol
    if normalized_market == "CN" and len(normalized_symbol) == 6 and normalized_symbol.isdigit():
        if normalized_symbol.startswith(("4", "8", "9")):
            return f"{normalized_symbol}.BJ"
        if normalized_symbol.startswith(("5", "6")):
            return f"{normalized_symbol}.SS"
        return f"{normalized_symbol}.SZ"
    if normalized_market == "HK" and normalized_symbol.isdigit():
        return f"{normalized_symbol.zfill(4)}.HK"
    if normalized_symbol == "0700":
        return "0700.HK"
    if normalized_symbol == "600519":
        return "600519.SS"
    return normalized_symbol
