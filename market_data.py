# -*- coding: utf-8 -*-
"""
modules/market_data.py - 시장 데이터 및 지표 계산
"""

import pandas as pd
import numpy as np
import ta
import time
from datetime import datetime


class MarketDataProvider:
    """시장 데이터 제공 및 지표 계산"""
    
    def __init__(self, exchange=None, symbol="ETH/USDT"):
        self.exchange = exchange
        self.symbol = symbol
        self.demo_mode = False
    
    def set_demo_mode(self, enabled=True):
        """데모 모드 설정"""
        self.demo_mode = enabled
    
    def generate_demo_data(self, timeframe, limit=100):
        """데모 데이터 생성 (시뮬레이션)"""
        np.random.seed(int(time.time()))
        
        base_price = 1900.0
        prices = []
        rsi_values = []
        bb_pcts = []
        
        price = base_price
        for i in range(limit):
            change = np.random.normal(0.001, 0.008)
            price *= (1 + change)
            prices.append(price)
            
            if i < 20:
                rsi = 40 + i * 2 + np.random.normal(0, 3)
            else:
                rsi = 50 + np.sin(i/10) * 20 + np.random.normal(0, 5)
            rsi = max(20, min(80, rsi))
            rsi_values.append(rsi)
            
            bb_pct = 0.3 + (rsi - 30) / 100 * 0.5 + np.random.normal(0, 0.05)
            bb_pct = max(0.1, min(0.95, bb_pct))
            bb_pcts.append(bb_pct)
        
        df = pd.DataFrame({
            'timestamp': [int(time.time()) - (limit-i)*300 for i in range(limit)],
            'open': [p * (1 - abs(np.random.normal(0, 0.002))) for p in prices],
            'high': [p * (1 + abs(np.random.normal(0, 0.003))) for p in prices],
            'low': [p * (1 - abs(np.random.normal(0, 0.003))) for p in prices],
            'close': prices,
            'volume': [np.random.uniform(1000, 5000) for _ in range(limit)],
            'rsi': rsi_values,
            'bb_pct_b': bb_pcts,
            'bb_width': [np.random.uniform(0.03, 0.06) for _ in range(limit)],
            'trend': ['UP' if rsi > 50 else 'DOWN' for rsi in rsi_values]
        })
        
        return df
    
    def fetch_data(self, timeframe='5m', limit=100):
        """OHLCV 데이터 조회 및 지표 계산"""
        if self.demo_mode:
            return self.generate_demo_data(timeframe, limit)
        
        if not self.exchange:
            return None
        
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # RSI
            df['rsi'] = ta.momentum.rsi(df['close'], 14)
            
            # 볼린저 밴드
            bb = ta.volatility.BollingerBands(df['close'], 20, 2)
            df['bb_upper'] = bb.bollinger_hband()
            df['bb_lower'] = bb.bollinger_lband()
            df['bb_mid'] = bb.bollinger_mavg()
            df['bb_pct_b'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
            df['bb_bandwidth'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid']
            
            # EMA 추세
            df['ema8'] = ta.trend.ema_indicator(df['close'], 8)
            df['ema21'] = ta.trend.ema_indicator(df['close'], 21)
            df['trend'] = np.where(df['ema8'] > df['ema21'], 'UP', 'DOWN')
            
            # MACD
            macd = ta.trend.MACD(df['close'], 12, 26, 9)
            df['macd'] = macd.macd()
            df['macd_signal'] = macd.macd_signal()
            df['macd_hist'] = macd.macd_diff()
            
            # 거래량 비율
            df['volume_sma'] = df['volume'].rolling(20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            return df
            
        except Exception as e:
            print(f"❌ 데이터 조회 실패: {e}")
            return None
    
    def get_current_market_state(self, df):
        """현재 시장 상태 분석"""
        if df is None or len(df) < 20:
            return None
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        return {
            'price': latest['close'],
            'rsi': latest['rsi'],
            'bb_pct': latest['bb_pct_b'],
            'bb_width': latest.get('bb_bandwidth', 0.04),
            'trend': latest['trend'],
            'volume_ratio': latest.get('volume_ratio', 1.0),
            'macd': latest.get('macd', 0),
            'macd_signal': latest.get('macd_signal', 0),
            'ema8': latest['ema8'],
            'ema21': latest['ema21'],
            'is_sideways': latest.get('bb_bandwidth', 0.04) < 0.03,
            'market_mode': 'unknown'
        }
    
    def fetch_multi_timeframe_data(self, timeframes=['3m', '5m', '15m'], limit=50):
        """
        🆕 다중 시간대 데이터 조회
        3분, 5분, 15분봉 데이터를 동시에 가져와서 추세 확인
        """
        multi_data = {}
        
        for tf in timeframes:
            df = self.fetch_data(tf, limit)
            if df is not None:
                state = self.get_current_market_state(df)
                if state:
                    multi_data[tf] = {
                        'df': df,
                        'state': state
                    }
        
        return multi_data
    
    def check_multi_timeframe_alignment(self, multi_data, position='LONG'):
        """
        🆕 다중 시간대 추세 정렬 확인
        3m → 5m → 15m 순서로 추세가 일치하는지 확인
        """
        if len(multi_data) < 2:
            return False, "데이터 부족"
        
        trends = {}
        for tf in ['3m', '5m', '15m']:
            if tf in multi_data:
                trends[tf] = multi_data[tf]['state']['trend']
        
        if len(trends) < 2:
            return False, "시간대 데이터 부족"
        
        # 롱 진입 조건: 3m, 5m, 15m 모두 UP 또는 3m→5m→15m 순차적 UP
        if position == 'LONG':
            # 최소 2개 시간대 이상 UP 필요
            up_count = sum(1 for t in trends.values() if t == 'UP')
            if up_count >= 2:
                return True, f"추세 정렬 (UP: {up_count}/3)"
            else:
                return False, f"추세 불일치 (UP: {up_count}/3)"
        
        # 숏 진입 조건: 3m, 5m, 15m 모두 DOWN 또는 3m→5m→15m 순차적 DOWN  
        else:
            down_count = sum(1 for t in trends.values() if t == 'DOWN')
            if down_count >= 2:
                return True, f"추세 정렬 (DOWN: {down_count}/3)"
            else:
                return False, f"추세 불일치 (DOWN: {down_count}/3)"
    
    def check_sequential_reversal(self, multi_data, position='LONG'):
        """
        🆕 순차적 추세 반전 감지 (청산용)
        롱 포지션에서 3m DOWN → 5m DOWN → 15m 확인 중 DOWN
        """
        if len(multi_data) < 2:
            return False, None
        
        # 3m 추세 확인
        tf_3m = multi_data.get('3m', {}).get('state', {})
        tf_5m = multi_data.get('5m', {}).get('state', {})
        tf_15m = multi_data.get('15m', {}).get('state', {})
        
        if position == 'LONG':
            # 롱 청산 조건: 3m 하락 AND (5m 하락 OR 15m 하락)
            if tf_3m.get('trend') == 'DOWN':
                if tf_5m.get('trend') == 'DOWN' or tf_15m.get('trend') == 'DOWN':
                    return True, "3m→5m/15m 순차 하락"
            return False, None
        else:
            # 숏 청산 조건: 3m 상승 AND (5m 상승 OR 15m 상승)
            if tf_3m.get('trend') == 'UP':
                if tf_5m.get('trend') == 'UP' or tf_15m.get('trend') == 'UP':
                    return True, "3m→5m/15m 순차 상승"
            return False, None
