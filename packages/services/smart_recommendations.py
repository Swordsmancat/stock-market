"""
Smart recommendation engine for stock market analysis.

Implements various recommendation algorithms:
- Breakout detection (突破提醒)
- Volume anomaly detection (成交量异常)
- Oversold rebound detection (超跌反弹)
- Strong momentum detection (强势股)
"""

from datetime import datetime, timedelta
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
