def map_symbol_to_ticker(symbol: str) -> str:
    if symbol == "0700":
        return "0700.HK"
    if symbol == "600519":
        return "600519.SS"
    return symbol
