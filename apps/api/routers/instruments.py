from fastapi import APIRouter

router = APIRouter(prefix="/instruments", tags=["instruments"])


@router.get("")
def list_instruments() -> dict[str, list[dict[str, str]]]:
    return {
        "items": [
            {"symbol": "600519", "name": "Kweichow Moutai", "market": "CN"},
            {"symbol": "0700", "name": "Tencent Holdings", "market": "HK"},
            {"symbol": "AAPL", "name": "Apple Inc.", "market": "US"},
        ]
    }
