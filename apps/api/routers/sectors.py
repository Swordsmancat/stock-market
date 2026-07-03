"""API router for sector/industry analysis."""

from fastapi import APIRouter, Query
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


# Simplified sector data (in production, this would come from a database or data provider)
SECTOR_SYMBOLS = {
    "新能源汽车": ["TSLA", "NIO", "XPEV", "LI"],
    "人工智能": ["NVDA", "AMD", "GOOGL", "MSFT"],
    "半导体": ["TSM", "ASML", "INTC", "QCOM"],
    "生物医药": ["PFE", "MRNA", "JNJ", "ABBV"],
    "消费电子": ["AAPL", "SONY", "SAMSUNG"],
}


@router.get("/sectors/hot")
async def get_hot_sectors(
    limit: int = Query(5, ge=1, le=10, description="Number of sectors to return")
):
    """
    Get hot sectors based on recent performance.
    
    Returns top performing sectors with their performance metrics.
    """
    try:
        # Mock data for hot sectors
        # In production, this would calculate real performance from market data
        hot_sectors = [
            {
                "name": "新能源汽车",
                "name_en": "EV & New Energy",
                "change_percent": 5.2,
                "fund_flow": "流入",
                "fund_flow_amount": 12.5,
                "leader_symbol": "TSLA",
                "leader_name": "特斯拉",
                "leader_change_percent": 6.8,
                "symbols_count": len(SECTOR_SYMBOLS.get("新能源汽车", [])),
            },
            {
                "name": "人工智能",
                "name_en": "Artificial Intelligence",
                "change_percent": 3.8,
                "fund_flow": "流入",
                "fund_flow_amount": 8.3,
                "leader_symbol": "NVDA",
                "leader_name": "英伟达",
                "leader_change_percent": 5.2,
                "symbols_count": len(SECTOR_SYMBOLS.get("人工智能", [])),
            },
            {
                "name": "半导体",
                "name_en": "Semiconductor",
                "change_percent": 2.1,
                "fund_flow": "流出",
                "fund_flow_amount": -3.2,
                "leader_symbol": "TSM",
                "leader_name": "台积电",
                "leader_change_percent": 3.1,
                "symbols_count": len(SECTOR_SYMBOLS.get("半导体", [])),
            },
            {
                "name": "生物医药",
                "name_en": "Biotech & Pharma",
                "change_percent": -1.5,
                "fund_flow": "流出",
                "fund_flow_amount": -5.1,
                "leader_symbol": "PFE",
                "leader_name": "辉瑞",
                "leader_change_percent": -0.8,
                "symbols_count": len(SECTOR_SYMBOLS.get("生物医药", [])),
            },
            {
                "name": "消费电子",
                "name_en": "Consumer Electronics",
                "change_percent": 0.8,
                "fund_flow": "流入",
                "fund_flow_amount": 2.1,
                "leader_symbol": "AAPL",
                "leader_name": "苹果",
                "leader_change_percent": 1.2,
                "symbols_count": len(SECTOR_SYMBOLS.get("消费电子", [])),
            },
        ]
        
        # Sort by performance and limit
        hot_sectors.sort(key=lambda x: x["change_percent"], reverse=True)
        limited_sectors = hot_sectors[:limit]
        
        return {
            "status": "degraded",
            "data_mode": "mock",
            "source": "static_sector_fixture",
            "message": "Static mock sector data; not live market data.",
            "count": len(limited_sectors),
            "items": limited_sectors
        }
        
    except Exception as e:
        logger.error(f"Error in get_hot_sectors: {e}")
        return {
            "status": "unavailable",
            "data_mode": "none",
            "message": str(e),
            "count": 0,
            "items": []
        }
