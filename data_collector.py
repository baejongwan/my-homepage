# -*- coding: utf-8 -*-
"""
LUMI 데이터 수집기
실시간 차트 데이터 + 거래 시점 분석 데이터 저장
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import os
import json
import csv
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import threading
import time
from config import *

class DataCollector:
    """종합 데이터 수집기"""
    
    def __init__(self, symbol=SYMBOL):
        self.symbol = symbol
        self.data_dir = Path("logs") / "collected_data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 파일 경로
        self.price_data_file = self.data_dir / f"price_data_{datetime.now().strftime('%Y%m')}.csv"
        self.trade_data_file = self.data_dir / f"trade_analysis_{datetime.now().strftime('%Y%m')}.csv"
        self.market_regime_file = self.data_dir / f"market_regime_{datetime.now().strftime('%Y%m')}.json"
        self.performance_file = self.data_dir / f"performance_{datetime.now().strftime('%Y%m')}.csv"
        
        # 실시간 데이터 버퍼
        self.price_buffer = []
        self.buffer_lock = threading.Lock()
        self.buffer_size = 100
        
        # 컬럼 정의
        self.price_columns = [
            'timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume',
            'rsi', 'rsi_14', 'rsi_6', 'rsi_21',
            'bb_mid', 'bb_upper', 'bb_lower', 'bb_pct', 'bb_width',
            'ema_9', 'ema_21', 'ema_50', 'ema_200',
            'macd', 'macdsignal', 'macdhist',
            'vwap', 'atr', 'adx', 
            'trend_5m', 'trend_15m', 'trend_1h',
            'fvg_bull', 'fvg_bear', 'fvg_size',
            'volume_ratio', 'volume_sma20',
            'cvd', 'cvd_slope',
            'market_mode', 'session'
        ]
        
        self.trade_columns = [
            'trade_id', 'timestamp', 'type', 'mode', 'action',
            'entry_price', 'exit_price', 'stop_loss', 'take_profit',
            'position_size', 'leverage', 'pnl', 'pnl_pct',
            'entry_rsi', 'entry_bb_pct', 'entry_trend',
            'entry_volume_ratio', 'entry_fvg',
            'exit_reason', 'exit_rsi', 'exit_bb_pct',
            'duration_seconds', 'max_profit', 'max_loss',
            'market_regime', 'volatility_state',
            'notes', 'strategy_version'
        ]
        
        self._init_files()
    
    def _init_files(self):
        """파일 초기화 (헤더 작성)"""
        # 가격 데이터 파일
        if not self.price_data_file.exists():
            with open(self.price_data_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(self.price_columns)
            print(f"✅ 가격 데이터 파일 생성: {self.price_data_file}")
        
        # 거래 분석 파일
        if not self.trade_data_file.exists():
            with open(self.trade_data_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(self.trade_columns)
            print(f"✅ 거래 분석 파일 생성: {self.trade_data_file}")
        
        # 성과 파일
        if not self.performance_file.exists():
            perf_columns = ['date', 'total_return', 'win_rate', 'profit_factor', 
                          'avg_trade', 'max_drawdown', 'trades_count', 'notes']
            with open(self.performance_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(perf_columns)
    
    def record_price_data(self, **kwargs):
        """실시간 가격 데이터 기록"""
        try:
            row = {col: kwargs.get(col, None) for col in self.price_columns}
            row['timestamp'] = datetime.now().isoformat()
            
            with self.buffer_lock:
                self.price_buffer.append(row)
                
                if len(self.price_buffer) >= self.buffer_size:
                    self._flush_buffer()
        except Exception as e:
            print(f"데이터 기록 오류: {e}")
    
    def _flush_buffer(self):
        """버퍼 플러시 (파일에 저장)"""
        if not self.price_buffer:
            return
        
        try:
            df = pd.DataFrame(self.price_buffer)
            
            # 파일이 존재하면 append, 없으면 새로 생성
            if self.price_data_file.exists():
                df.to_csv(self.price_data_file, mode='a', header=False, index=False)
            else:
                df.to_csv(self.price_data_file, mode='w', header=True, index=False)
            
            self.price_buffer = []
            print(f"💾 {len(df)}개 캔들 데이터 저장 완료")
        except Exception as e:
            print(f"버퍼 플러시 오류: {e}")
    
    def record_trade(self, trade_info):
        """거래 완료 시 상세 분석 데이터 기록"""
        try:
            row = {col: trade_info.get(col, None) for col in self.trade_columns}
            row['timestamp'] = datetime.now().isoformat()
            
            with open(self.trade_data_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.trade_columns)
                writer.writerow(row)
            
            print(f"✅ 거래 #{row.get('trade_id')} 분석 데이터 저장")
        except Exception as e:
            print(f"거래 기록 오류: {e}")
    
    def get_current_market_snapshot(self):
        """현재 시장 스냅샷 가져오기"""
        try:
            df = pd.read_csv(self.price_data_file)
            if len(df) > 0:
                return df.iloc[-1].to_dict()
            return None
        except:
            return None
    
    def analyze_daily_performance(self, date=None):
        """일일 성과 분석"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            df = pd.read_csv(self.trade_data_file)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['date'] = df['timestamp'].dt.date
            
            daily = df[df['date'] == date]
            
            if len(daily) == 0:
                return None
            
            return {
                'date': date,
                'total_trades': len(daily),
                'winning_trades': len(daily[daily['pnl'] > 0]),
                'losing_trades': len(daily[daily['pnl'] <= 0]),
                'total_pnl': daily['pnl'].sum(),
                'avg_pnl': daily['pnl'].mean(),
                'best_trade': daily['pnl'].max(),
                'worst_trade': daily['pnl'].min(),
                'trend_trades': len(daily[daily['mode'] == 'trend']),
                'reversal_trades': len(daily[daily['mode'] == 'reversal'])
            }
        except Exception as e:
            print(f"성과 분석 오류: {e}")
            return None


class TradeAnalyzer:
    """거래 분석기 - 승률/패턴 분석"""
    
    def __init__(self):
        self.data_dir = Path("logs") / "collected_data"
        self.analysis_file = self.data_dir / "trade_patterns.json"
    
    def analyze_patterns(self, days=30):
        """거래 패턴 분석"""
        try:
            df = pd.read_csv(self.data_dir / f"trade_analysis_{datetime.now().strftime('%Y%m')}.csv")
            
            if len(df) < 5:
                print("분석할 거래 데이터가 부족합니다 (최소 5회)")
                return None
            
            # 승리/패배 조건 분석
            winners = df[df['pnl'] > 0]
            losers = df[df['pnl'] <= 0]
            
            analysis = {
                'generated_at': datetime.now().isoformat(),
                'total_trades': len(df),
                'win_rate': len(winners) / len(df) * 100,
                'profit_factor': abs(winners['pnl'].sum() / losers['pnl'].sum()) if len(losers) > 0 and losers['pnl'].sum() != 0 else float('inf'),
                'avg_win': winners['pnl'].mean() if len(winners) > 0 else 0,
                'avg_loss': losers['pnl'].mean() if len(losers) > 0 else 0,
                
                'best_entry_conditions': self._analyze_entry_conditions(winners),
                'worst_entry_conditions': self._analyze_entry_conditions(losers),
                
                'exit_analysis': {
                    'sl_hits': len(df[df['exit_reason'] == 'SL']),
                    'tp_hits': len(df[df['exit_reason'] == 'TP']),
                    'sl_pct': len(df[df['exit_reason'] == 'SL']) / len(df) * 100,
                    'tp_pct': len(df[df['exit_reason'] == 'TP']) / len(df) * 100
                },
                
                'mode_analysis': {
                    'trend_win_rate': len(winners[winners['mode'] == 'trend']) / len(df[df['mode'] == 'trend']) * 100 if len(df[df['mode'] == 'trend']) > 0 else 0,
                    'reversal_win_rate': len(winners[winners['mode'] == 'reversal']) / len(df[df['mode'] == 'reversal']) * 100 if len(df[df['mode'] == 'reversal']) > 0 else 0
                },
                
                'recommended_adjustments': self._generate_recommendations(df, winners, losers)
            }
            
            # JSON으로 저장
            with open(self.analysis_file, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False, default=str)
            
            return analysis
            
        except Exception as e:
            print(f"패턴 분석 오류: {e}")
            return None
    
    def _analyze_entry_conditions(self, trades):
        """진입 조건 분석"""
        if len(trades) == 0:
            return {}
        
        return {
            'avg_entry_rsi': trades['entry_rsi'].mean(),
            'avg_entry_bb_pct': trades['entry_bb_pct'].mean(),
            'avg_volume_ratio': trades['entry_volume_ratio'].mean(),
            'most_common_trend': trades['entry_trend'].mode()[0] if len(trades['entry_trend'].mode()) > 0 else None,
            'most_common_fvg': trades['entry_fvg'].mode()[0] if len(trades['entry_fvg'].mode()) > 0 else None,
            'rsi_range': f"{trades['entry_rsi'].min():.1f} ~ {trades['entry_rsi'].max():.1f}",
            'bb_pct_range': f"{trades['entry_bb_pct'].min():.2f} ~ {trades['entry_bb_pct'].max():.2f}"
        }
    
    def _generate_recommendations(self, all_trades, winners, losers):
        """개선 권장사항 생성"""
        recommendations = []
        
        # SL/TP 비율 분석
        sl_rate = len(all_trades[all_trades['exit_reason'] == 'SL']) / len(all_trades)
        if sl_rate > 0.6:
            recommendations.append("⚠️ SL 비율이 높습니다. SL 간격을 넓히거나 진입 조건을 강화하세요.")
        
        # 모드별 승률
        trend_trades = all_trades[all_trades['mode'] == 'trend']
        if len(trend_trades) > 0:
            trend_win = len(winners[winners['mode'] == 'trend']) / len(trend_trades)
            if trend_win > 0.6:
                recommendations.append(f"✅ 추세 모드 승률 {trend_win*100:.1f}% - 더 많은 추세 신호를 탐지하세요")
        
        reversal_trades = all_trades[all_trades['mode'] == 'reversal']
        if len(reversal_trades) > 0:
            rev_win = len(winners[winners['mode'] == 'reversal']) / len(reversal_trades)
            if rev_win < 0.3:
                recommendations.append(f"⚠️ 반전 모드 승률 {rev_win*100:.1f}% - 반전 조건을 더 엄격히 하세요")
        
        return recommendations


# 전역 인스턴스
collector = DataCollector()
analyzer = TradeAnalyzer()


if __name__ == "__main__":
    # 테스트
    collector.record_price_data(
        symbol="ETH/USDT",
        open=1800, high=1820, low=1795, close=1810, volume=1000,
        rsi=45.5, bb_pct=0.45, trend_5m="UP", market_mode="trend"
    )
    
    collector.record_trade({
        'trade_id': 1,
        'type': 'LONG',
        'mode': 'trend',
        'entry_price': 1800,
        'exit_price': 1860,
        'pnl': 60,
        'pnl_pct': 3.5,
        'entry_rsi': 55.5,
        'entry_bb_pct': 0.58,
        'exit_reason': 'TP'
    })
    
    print("\n✅ 데이터 수집 시스템 테스트 완료!")
