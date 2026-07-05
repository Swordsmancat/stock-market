"""Redis cache utilities for market data."""
import json
from datetime import date
from functools import wraps
from typing import Any, Callable

import redis

from packages.shared.config import settings

redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)


def cache_market_overview(ttl: int = 300):
    """Cache decorator for market overview data.
    
    Args:
        ttl: Time to live in seconds (default 5 minutes)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Build cache key from function arguments
            provider_name = kwargs.get("provider_name") or "default"
            today = kwargs.get("today")
            if today is None:
                today = date.today()
            elif not isinstance(today, date):
                today = date.today()
            
            cache_key = f"dashboard:market-overview:{provider_name}:{today.isoformat()}"
            
            # Try to get from cache
            try:
                cached = redis_client.get(cache_key)
                if cached:
                    # Successfully retrieved from cache
                    return json.loads(cached)
            except Exception:
                # Cache read failed, continue to function
                pass
            
            # Call the actual function
            result = func(*args, **kwargs)
            
            # Store in cache (async, don't block on failure)
            try:
                redis_client.set(
                    cache_key,
                    json.dumps(result, ensure_ascii=False, default=str),
                    ex=ttl,
                )
            except Exception:
                # Cache write failed, just log and continue
                pass
            
            return result
        return wrapper
    return decorator


def clear_market_overview_cache(provider_name: str | None = None) -> int:
    """Clear market overview cache.
    
    Args:
        provider_name: Optional provider to clear specific cache, or None for all
        
    Returns:
        Number of keys deleted
    """
    pattern = f"dashboard:market-overview:{provider_name or '*'}:*"
    try:
        keys = list(redis_client.scan_iter(match=pattern))
        if keys:
            return redis_client.delete(*keys)
        return 0
    except redis.RedisError:
        return 0
