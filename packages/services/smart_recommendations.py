"""
Smart recommendation engine for stock market analysis.

Implements various recommendation algorithms:
- Breakout detection (突破提醒)
- Volume anomaly detection (成交量异常)
- Oversold rebound detection (超跌反弹)
- Strong momentum detection (强势股)
"""

from statistics import median
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """Stock recommendation engine based on technical analysis."""
    
    def __init__(self):
        self.min_data_points = 30
    
    def generate_recommendations(
        self,
        symbol: str,
        bars: List[Dict[str, Any]],
        indicators: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Generate all recommendations for a symbol."""
        recommendations = []
        
        if len(bars) < self.min_data_points:
            return recommendations
        
        # Breakout detection
        breakout = self._detect_breakout(symbol, bars, indicators)
        if breakout:
            recommendations.append(breakout)
        
        # Volume anomaly
        volume_anomaly = self._detect_volume_anomaly(symbol, bars)
        if volume_anomaly:
            recommendations.append(volume_anomaly)
        
        # Oversold rebound
        oversold = self._detect_oversold_rebound(symbol, bars, indicators)
        if oversold:
            recommendations.append(oversold)
        
        # Strong momentum
        momentum = self._detect_strong_momentum(symbol, bars)
        if momentum:
            recommendations.append(momentum)
        
        return recommendations
    
    def _detect_breakout(
        self,
        symbol: str,
        bars: List[Dict[str, Any]],
        indicators: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Detect MA20 breakout."""
        if not indicators or 'ma20' not in indicators:
            return None
        
        latest = bars[-1]
        ma20 = indicators.get('ma20')
        
        if not ma20:
            return None
        
        # Check if price just crossed above MA20
        if len(bars) >= 2:
            prev_bar = bars[-2]
            if prev_bar['close'] < ma20 and latest['close'] > ma20:
                return {
                    'symbol': symbol,
                    'type': 'breakout',
                    'title': f'{symbol} 突破20日均线',
                    'reason': f'股价突破20日均线 ({ma20:.2f}),当前价格 {latest["close"]:.2f}',
                    'confidence': 0.75,
                    'timestamp': latest['timestamp'],
                    'data': {
                        'ma20': ma20,
                        'price': latest['close'],
                        'change_percent': ((latest['close'] - ma20) / ma20) * 100
                    }
                }
        
        return None
    
    def _detect_volume_anomaly(
        self,
        symbol: str,
        bars: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Detect abnormal trading volume."""
        if len(bars) < 6:
            return None
        
        latest = bars[-1]
        if 'volume' not in latest or not latest['volume']:
            return None
        
        # Calculate 5-day average volume
        recent_volumes = [b.get('volume', 0) for b in bars[-6:-1] if b.get('volume')]
        if not recent_volumes:
            return None
        
        avg_volume = sum(recent_volumes) / len(recent_volumes)
        current_volume = latest['volume']
        
        # Check if volume > 200% of average
        if current_volume > avg_volume * 2:
            volume_ratio = current_volume / avg_volume
            return {
                'symbol': symbol,
                'type': 'volume_anomaly',
                'title': f'{symbol} 成交量异常放大',
                'reason': f'成交量达到5日均量的 {volume_ratio:.1f} 倍,可能有重大消息',
                'confidence': 0.65,
                'timestamp': latest['timestamp'],
                'data': {
                    'volume': current_volume,
                    'avg_volume': avg_volume,
                    'ratio': volume_ratio
                }
            }
        
        return None
    
    def _detect_oversold_rebound(
        self,
        symbol: str,
        bars: List[Dict[str, Any]],
        indicators: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Detect oversold rebound opportunity."""
        if len(bars) < 6:
            return None
        
        # Check for 5 consecutive down days
        recent_bars = bars[-6:]
        down_days = 0
        for i in range(1, len(recent_bars)):
            if recent_bars[i]['close'] < recent_bars[i-1]['close']:
                down_days += 1
        
        if down_days < 5:
            return None
        
        # Check RSI if available
        rsi = indicators.get('rsi') if indicators else None
        if rsi and rsi < 30:
            latest = recent_bars[-1]
            total_decline = ((latest['close'] - recent_bars[0]['close']) / recent_bars[0]['close']) * 100
            
            return {
                'symbol': symbol,
                'type': 'oversold_rebound',
                'title': f'{symbol} 超跌反弹机会',
                'reason': f'连续下跌5天,累计跌幅 {abs(total_decline):.1f}%,RSI={rsi:.1f},超跌反弹概率高',
                'confidence': 0.70,
                'timestamp': latest['timestamp'],
                'data': {
                    'consecutive_down_days': down_days,
                    'total_decline_percent': total_decline,
                    'rsi': rsi
                }
            }
        
        return None
    
    def _detect_strong_momentum(
        self,
        symbol: str,
        bars: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Detect strong upward momentum."""
        if len(bars) < 4:
            return None
        
        # Check for 3 consecutive up days
        recent_bars = bars[-4:]
        up_days = 0
        for i in range(1, len(recent_bars)):
            if recent_bars[i]['close'] > recent_bars[i-1]['close']:
                up_days += 1
        
        if up_days < 3:
            return None
        
        # Calculate total gain
        total_gain = ((recent_bars[-1]['close'] - recent_bars[0]['close']) / recent_bars[0]['close']) * 100
        
        # Check if gain > 10%
        if total_gain > 10:
            latest = recent_bars[-1]
            return {
                'symbol': symbol,
                'type': 'strong_momentum',
                'title': f'{symbol} 强势上涨',
                'reason': f'连续上涨3天,累计涨幅 {total_gain:.1f}%,动能强劲',
                'confidence': 0.80,
                'timestamp': latest['timestamp'],
                'data': {
                    'consecutive_up_days': up_days,
                    'total_gain_percent': total_gain,
                    'current_price': latest['close']
                }
            }
        
        return None


def calculate_indicators(bars: List[Dict[str, Any]]) -> Dict[str, float]:
    """Calculate technical indicators for recommendation engine."""
    if not bars:
        return {}
    
    indicators = {}
    
    # MA20
    if len(bars) >= 20:
        ma20_sum = sum(b['close'] for b in bars[-20:])
        indicators['ma20'] = ma20_sum / 20
    
    # Simple RSI calculation
    if len(bars) >= 14:
        gains = []
        losses = []
        for i in range(len(bars) - 13, len(bars)):
            change = bars[i]['close'] - bars[i-1]['close']
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains) / 14
        avg_loss = sum(losses) / 14
        
        if avg_loss != 0:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            indicators['rsi'] = rsi
        else:
            indicators['rsi'] = 100
    
    return indicators


DEFAULT_EVALUATION_WINDOWS = (1, 5, 20)
RECOMMENDATION_SIGNAL_TYPES = (
    "breakout",
    "volume_anomaly",
    "oversold_rebound",
    "strong_momentum",
)


def evaluate_recommendation_signals(
    symbol: str,
    bars: List[Dict[str, Any]],
    signal_types: Optional[List[str]] = None,
    forward_windows: Optional[List[int]] = None,
    benchmark_bars: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Evaluate deterministic recommendation signals against historical bars.

    The output is a research-quality diagnostic payload. It is not a trading
    strategy result, does not include transaction costs, and does not persist
    signal history.
    """
    requested_signal_types = _normalize_signal_types(signal_types)
    requested_forward_windows, window_diagnostics = _normalize_forward_windows(forward_windows)
    diagnostics: List[Dict[str, Any]] = list(window_diagnostics)

    if len(bars) < RecommendationEngine().min_data_points:
        return {
            "symbol": symbol,
            "status": "no_data",
            "sample_size": 0,
            "signal_types": requested_signal_types,
            "forward_windows": requested_forward_windows,
            "metrics": {},
            "snapshots": [],
            "diagnostics": [
                *diagnostics,
                {
                    "code": "NOT_ENOUGH_HISTORICAL_BARS",
                    "message": "At least 30 historical bars are required to scan recommendation signals.",
                    "available_bars": len(bars),
                },
            ],
        }

    engine = RecommendationEngine()
    snapshots = _scan_signal_snapshots(symbol, bars, requested_signal_types, engine)

    if not snapshots:
        return {
            "symbol": symbol,
            "status": "no_signals",
            "sample_size": 0,
            "signal_types": requested_signal_types,
            "forward_windows": requested_forward_windows,
            "metrics": {},
            "snapshots": [],
            "diagnostics": [
                *diagnostics,
                {
                    "code": "NO_SIGNAL_SNAPSHOTS",
                    "message": "No historical recommendation signals matched the requested signal types.",
                },
            ],
        }

    metrics_by_signal_type = {
        signal_type: _evaluate_signal_type_snapshots(
            bars=bars,
            snapshots=[snapshot for snapshot in snapshots if snapshot["signal_type"] == signal_type],
            forward_windows=requested_forward_windows,
            benchmark_bars=benchmark_bars,
        )
        for signal_type in requested_signal_types
    }
    diagnostics.extend(_collect_metric_diagnostics(metrics_by_signal_type))

    if benchmark_bars is None:
        diagnostics.append(
            {
                "code": "BENCHMARK_UNAVAILABLE",
                "message": "No benchmark bars were supplied; benchmark-relative returns are omitted.",
            }
        )

    return {
        "symbol": symbol,
        "status": "ok",
        "sample_size": len(snapshots),
        "signal_types": requested_signal_types,
        "forward_windows": requested_forward_windows,
        "metrics": metrics_by_signal_type,
        "snapshots": snapshots,
        "diagnostics": diagnostics,
        "disclaimer": "Historical signal evaluation is a research aid only and is not investment advice.",
    }


def _normalize_signal_types(signal_types: Optional[List[str]]) -> List[str]:
    if not signal_types:
        return list(RECOMMENDATION_SIGNAL_TYPES)

    normalized_signal_types = []
    for signal_type in signal_types:
        if signal_type in RECOMMENDATION_SIGNAL_TYPES and signal_type not in normalized_signal_types:
            normalized_signal_types.append(signal_type)
    return normalized_signal_types or list(RECOMMENDATION_SIGNAL_TYPES)


def _normalize_forward_windows(forward_windows: Optional[List[int]]) -> tuple[List[int], List[Dict[str, Any]]]:
    diagnostics: List[Dict[str, Any]] = []
    raw_windows = forward_windows or list(DEFAULT_EVALUATION_WINDOWS)
    normalized_windows = []
    for window in raw_windows:
        if not isinstance(window, int) or window <= 0:
            diagnostics.append(
                {
                    "code": "INVALID_FORWARD_WINDOW",
                    "message": "Forward return windows must be positive integers.",
                    "window": window,
                }
            )
            continue
        if window not in normalized_windows:
            normalized_windows.append(window)
    return normalized_windows or list(DEFAULT_EVALUATION_WINDOWS), diagnostics


def _scan_signal_snapshots(
    symbol: str,
    bars: List[Dict[str, Any]],
    signal_types: List[str],
    engine: RecommendationEngine,
) -> List[Dict[str, Any]]:
    snapshots: List[Dict[str, Any]] = []
    for bar_index in range(engine.min_data_points - 1, len(bars)):
        historical_slice = bars[: bar_index + 1]
        indicators = calculate_indicators(historical_slice)
        recommendations = engine.generate_recommendations(symbol, historical_slice, indicators)
        for recommendation in recommendations:
            signal_type = recommendation.get("type")
            if signal_type not in signal_types:
                continue
            latest_bar = historical_slice[-1]
            snapshots.append(
                {
                    "symbol": symbol,
                    "signal_type": signal_type,
                    "signal_date": latest_bar.get("timestamp"),
                    "bar_index": bar_index,
                    "entry_price": latest_bar.get("close"),
                    "confidence": recommendation.get("confidence"),
                    "reason": recommendation.get("reason"),
                    "source_window": len(historical_slice),
                    "data_points_used": len(historical_slice),
                }
            )
    return snapshots


def _evaluate_signal_type_snapshots(
    *,
    bars: List[Dict[str, Any]],
    snapshots: List[Dict[str, Any]],
    forward_windows: List[int],
    benchmark_bars: Optional[List[Dict[str, Any]]],
) -> Dict[str, Any]:
    window_metrics = {}
    for window in forward_windows:
        evaluated_returns = []
        evaluated_drawdowns = []
        benchmark_relative_returns = []
        skipped_count = 0

        for snapshot in snapshots:
            bar_index = int(snapshot["bar_index"])
            entry_price = _safe_float(snapshot.get("entry_price"))
            future_index = bar_index + window
            if entry_price is None or entry_price == 0 or future_index >= len(bars):
                skipped_count += 1
                continue

            exit_price = _safe_float(bars[future_index].get("close"))
            if exit_price is None:
                skipped_count += 1
                continue

            forward_return = ((exit_price - entry_price) / entry_price) * 100
            evaluated_returns.append(forward_return)
            evaluated_drawdowns.append(_calculate_max_drawdown_after_signal(bars, bar_index, window, entry_price))

            benchmark_return = _calculate_benchmark_return(benchmark_bars, bar_index, window)
            if benchmark_return is not None:
                benchmark_relative_returns.append(forward_return - benchmark_return)

        sample_size = len(evaluated_returns)
        window_metrics[str(window)] = {
            "sample_size": sample_size,
            "skipped_count": skipped_count,
            "hit_rate": _calculate_hit_rate(evaluated_returns),
            "average_forward_return": _average(evaluated_returns),
            "median_forward_return": median(evaluated_returns) if evaluated_returns else None,
            "max_drawdown_after_signal": min(evaluated_drawdowns) if evaluated_drawdowns else None,
            "benchmark_relative_return": _average(benchmark_relative_returns),
        }

    return {
        "sample_size": len(snapshots),
        "windows": window_metrics,
    }


def _calculate_max_drawdown_after_signal(
    bars: List[Dict[str, Any]],
    bar_index: int,
    window: int,
    entry_price: float,
) -> float:
    future_bars = bars[bar_index + 1 : bar_index + window + 1]
    if not future_bars:
        return 0.0
    lowest_price = min(_safe_float(bar.get("low")) or _safe_float(bar.get("close")) or entry_price for bar in future_bars)
    return ((lowest_price - entry_price) / entry_price) * 100


def _calculate_benchmark_return(
    benchmark_bars: Optional[List[Dict[str, Any]]],
    bar_index: int,
    window: int,
) -> float | None:
    if benchmark_bars is None or bar_index + window >= len(benchmark_bars):
        return None
    benchmark_entry = _safe_float(benchmark_bars[bar_index].get("close"))
    benchmark_exit = _safe_float(benchmark_bars[bar_index + window].get("close"))
    if benchmark_entry is None or benchmark_entry == 0 or benchmark_exit is None:
        return None
    return ((benchmark_exit - benchmark_entry) / benchmark_entry) * 100


def _calculate_hit_rate(values: List[float]) -> float | None:
    if not values:
        return None
    positive_count = sum(1 for value in values if value > 0)
    return positive_count / len(values)


def _average(values: List[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def _collect_metric_diagnostics(metrics_by_signal_type: Dict[str, Any]) -> List[Dict[str, Any]]:
    diagnostics = []
    for signal_type, signal_metrics in metrics_by_signal_type.items():
        if signal_metrics["sample_size"] == 0:
            diagnostics.append(
                {
                    "code": "NO_SIGNAL_SNAPSHOTS_FOR_TYPE",
                    "signal_type": signal_type,
                    "message": "No snapshots were available for this signal type.",
                }
            )
        for window, window_metrics in signal_metrics["windows"].items():
            if window_metrics["sample_size"] == 0 and signal_metrics["sample_size"] > 0:
                diagnostics.append(
                    {
                        "code": "INSUFFICIENT_POST_SIGNAL_BARS",
                        "signal_type": signal_type,
                        "window": int(window),
                        "message": "Signals exist, but there are not enough post-signal bars for this forward window.",
                    }
                )
    return diagnostics


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
