# -*- coding: utf-8 -*-
"""
LUMI 자기 학습 시스템
수집된 데이터로 전략 자동 개선
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from collections import deque
import statistics

class SelfLearningSystem:
    """자가 학습 시스템"""
    
    def __init__(self):
        self.data_dir = Path("logs") / "collected_data"
        self.learning_file = self.data_dir / "learning_data.json"
        self.insights_file = self.data_dir / "strategy_insights.json"
        self.thesis_file = self.data_dir / "trading_thesis.md"
        
        # 학습 데이터 구조
        self.learning_data = {
            'optimal_entry_rsi': {'long': [], 'short': []},
            'optimal_bb_pct': {'long': [], 'short': []},
            'optimal_volume_ratio': [],
            'best_exit_timing': [],
            'market_regime_performance': {},
            'time_based_patterns': {},
            'day_of_week_stats': {},
            'hourly_win_rates': {}
        }
        
        self.min_samples = 10  # 학습에 필요한 최소 샘플 수
        self.recent_trades_window = 50  # 최근 거래 분석 윈도우
    
    def load_trade_history(self):
        """거래 이력 로드"""
        try:
            files = list(self.data_dir.glob("trade_analysis_*.csv"))
            all_trades = []
            
            for f in files:
                df = pd.read_csv(f)
                all_trades.append(df)
            
            if all_trades:
                return pd.concat(all_trades, ignore_index=True)
            return None
        except Exception as e:
            print(f"거래 이력 로드 오류: {e}")
            return None
    
    def load_price_data(self, hours=168):
        """가격 데이터 로드 (기본: 7일)"""
        try:
            files = list(self.data_dir.glob("price_data_*.csv"))
            all_data = []
            
            for f in files:
                df = pd.read_csv(f)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                all_data.append(df)
            
            if all_data:
                combined = pd.concat(all_data, ignore_index=True)
                # 최근 N시간만
                cutoff = datetime.now() - timedelta(hours=hours)
                return combined[combined['timestamp'] > cutoff]
            return None
        except Exception as e:
            print(f"가격 데이터 로드 오류: {e}")
            return None
    
    def learn_from_trades(self):
        """거래 데이터로부터 학습"""
        df = self.load_trade_history()
        if df is None or len(df) < self.min_samples:
            print(f"⚠️ 학습 데이터 부족 (현재: {len(df) if df is not None else 0}, 필요: {self.min_samples})")
            return None
        
        print(f"📚 {len(df)}개 거래 데이터로 학습 중...")
        
        insights = {
            'generated_at': datetime.now().isoformat(),
            'total_samples': len(df),
            'learning_results': {}
        }
        
        # 1. 롱 진입 최적 조건 학습
        winners = df[df['pnl'] > 0]
        
        if len(winners) > 0:
            # 롱 성공 조건
            long_winners = winners[winners['type'] == 'LONG']
            if len(long_winners) > 0:
                insights['learning_results']['optimal_long_entry'] = {
                    'rsi_range': f"{long_winners['entry_rsi'].quantile(0.25):.1f} ~ {long_winners['entry_rsi'].quantile(0.75):.1f}",
                    'rsi_mean': long_winners['entry_rsi'].mean(),
                    'rsi_std': long_winners['entry_rsi'].std(),
                    'bb_pct_range': f"{long_winners['entry_bb_pct'].quantile(0.25):.2f} ~ {long_winners['entry_bb_pct'].quantile(0.75):.2f}",
                    'bb_pct_mean': long_winners['entry_bb_pct'].mean(),
                    'avg_duration': long_winners['duration_seconds'].mean(),
                    'best_exit_reason': long_winners['exit_reason'].mode()[0] if len(long_winners['exit_reason'].mode()) > 0 else 'unknown'
                }
            
            # 숏 성공 조건
            short_winners = winners[winners['type'] == 'SHORT']
            if len(short_winners) > 0:
                insights['learning_results']['optimal_short_entry'] = {
                    'rsi_range': f"{short_winners['entry_rsi'].quantile(0.25):.1f} ~ {short_winners['entry_rsi'].quantile(0.75):.1f}",
                    'rsi_mean': short_winners['entry_rsi'].mean(),
                    'bb_pct_range': f"{short_winners['entry_bb_pct'].quantile(0.25):.2f} ~ {short_winners['entry_bb_pct'].quantile(0.75):.2f}",
                    'bb_pct_mean': short_winners['entry_bb_pct'].mean(),
                    'avg_duration': short_winners['duration_seconds'].mean()
                }
        
        # 2. 시간대별 패턴
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek  # 0=월, 6=일
        
        hourly_stats = df.groupby('hour').agg({
            'pnl': ['count', 'mean', 'sum'],
            'type': lambda x: (x == 'LONG').sum() / len(x) * 100
        }).reset_index()
        hourly_stats.columns = ['hour', 'trade_count', 'avg_pnl', 'total_pnl', 'long_ratio']
        
        best_hours = hourly_stats[hourly_stats['trade_count'] >= 3].nlargest(3, 'avg_pnl')
        insights['learning_results']['best_trading_hours'] = best_hours.to_dict('records')
        
        # 3. 요일별 패턴
        dow_names = ['월', '화', '수', '목', '금', '토', '일']
        dow_stats = df.groupby('day_of_week').agg({
            'pnl': ['count', 'mean', 'sum']
        }).reset_index()
        dow_stats.columns = ['day', 'trade_count', 'avg_pnl', 'total_pnl']
        dow_stats['day_name'] = dow_stats['day'].apply(lambda x: dow_names[int(x)])
        
        best_days = dow_stats[dow_stats['trade_count'] >= 3].nlargest(3, 'avg_pnl')
        insights['learning_results']['best_trading_days'] = best_days.to_dict('records')
        
        # 4. 시장 환경별 성과
        if 'market_regime' in df.columns:
            regime_stats = df.groupby('market_regime').agg({
                'pnl': ['count', 'mean', 'sum'],
                'mode': lambda x: x.mode()[0] if len(x.mode()) > 0 else 'unknown'
            }).reset_index()
            insights['learning_results']['regime_performance'] = regime_stats.to_dict('records')
        
        # 5. 모드별 최적화
        mode_stats = df.groupby('mode').agg({
            'pnl': ['count', 'mean'],
            'exit_reason': lambda x: x.mode()[0]
        }).reset_index()
        mode_stats.columns = ['mode', 'trade_count', 'avg_pnl', 'common_exit']
        insights['learning_results']['mode_optimization'] = mode_stats.to_dict('records')
        
        # 6. 나쁜 진입 피하기
        losers = df[df['pnl'] <= 0]
        if len(losers) > 0:
            bad_entries = {
                'avg_rsi': losers['entry_rsi'].mean(),
                'rsi_range': f"{losers['entry_rsi'].min():.1f} ~ {losers['entry_rsi'].max():.1f}",
                'avg_bb_pct': losers['entry_bb_pct'].mean(),
                'common_sl': len(losers[losers['exit_reason'] == 'SL']) / len(losers) * 100
            }
            insights['learning_results']['avoid_these_conditions'] = bad_entries
        
        # JSON으로 저장
        with open(self.insights_file, 'w', encoding='utf-8') as f:
            json.dump(insights, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"✅ 학습 완료! 인사이트 저장: {self.insights_file}")
        return insights
    
    def generate_trading_thesis(self):
        """학습된 내용을 바탕으로 트레이딩 논문 작성"""
        insights = self.learn_from_trades()
        if insights is None:
            return None
        
        results = insights.get('learning_results', {})
        
        markdown = f"""# 루미의 트레이딩 논문
## 자동 생성됨: {datetime.now().strftime('%Y-%m-%d %H:%M')}

### 📊 학습 데이터 요약
- 총 거래 수: {insights.get('total_samples', 0)}회
- 분석 기간: 최근 {self.recent_trades_window}회 중심

---

### 🎯 최적 롱 진입 조건
"""
        
        if 'optimal_long_entry' in results:
            long_opt = results['optimal_long_entry']
            markdown += f"""
```
RSI: {long_opt.get('rsi_range', 'N/A')} (평균: {long_opt.get('rsi_mean', 0):.1f})
BB%: {long_opt.get('bb_pct_range', 'N/A')} (평균: {long_opt.get('bb_pct_mean', 0):.2f})
평균 보유시간: {long_opt.get('avg_duration', 0)/60:.1f}분
최고 청산: {long_opt.get('best_exit_reason', 'unknown')}
```
"""
        
        markdown += "\n### 📉 최적 숏 진입 조건\n"
        if 'optimal_short_entry' in results:
            short_opt = results['optimal_short_entry']
            markdown += f"""
```
RSI: {short_opt.get('rsi_range', 'N/A')} (평균: {short_opt.get('rsi_mean', 0):.1f})
BB%: {short_opt.get('bb_pct_range', 'N/A')} (평균: {short_opt.get('bb_pct_mean', 0):.2f})
평균 보유시간: {short_opt.get('avg_duration', 0)/60:.1f}분
```
"""
        
        markdown += "\n### ⏰ 최고의 거래 시간대\n"
        if 'best_trading_hours' in results:
            for hour_data in results['best_trading_hours']:
                markdown += f"- **{int(hour_data['hour'])}시**: 평균 {hour_data['avg_pnl']:+.2f}$ ({int(hour_data['trade_count'])}회)\n"
        
        markdown += "\n### 📅 요일별 성과\n"
        if 'best_trading_days' in results:
            for day_data in results['best_trading_days']:
                markdown += f"- **{day_data['day_name']}요일**: 평균 {day_data['avg_pnl']:+.2f}$ ({int(day_data['trade_count'])}회)\n"
        
        markdown += "\n### ⚠️ 피해야 할 조건\n"
        if 'avoid_these_conditions' in results:
            avoid = results['avoid_these_conditions']
            markdown += f"""
```
평균 RSI: {avoid.get('avg_rsi', 0):.1f}
RSI 범위: {avoid.get('rsi_range', 'N/A')}
SL 비율: {avoid.get('common_sl', 0):.1f}%
```
→ 이런 조건에서는 진입 자제!
"""
        
        markdown += f"""
---

### 💡 루미의 제안
"""
        
        # 자동 제안 생성
        recommendations = self._auto_recommendations(results)
        for rec in recommendations:
            markdown += f"- {rec}\n"
        
        markdown += f"""
---

### 🔄 다음 업데이트
- 매 20회 거래마다 자동 업데이트
- 다음 업데이트 예정: {len(insights.get('total_samples', 0)) if insights else 'N/A'}회 이후

*이 문서는 수집된 실전 데이터를 기반으로 자동 생성됨*
"""
        
        # 파일 저장
        with open(self.thesis_file, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        print(f"✅ 트레이딩 논문 생성: {self.thesis_file}")
        return self.thesis_file
    
    def _auto_recommendations(self, results):
        """자동 제안 생성"""
        recs = []
        
        if 'avoid_these_conditions' in results:
            avoid = results['avoid_these_conditions']
            common_sl = avoid.get('common_sl', 0)
            if common_sl > 60:
                recs.append("🚨 SL 비율이 60% 초과 - 진입 조건을 더 엄격히 하세요")
        
        if 'mode_optimization' in results:
            for mode_data in results['mode_optimization']:
                if mode_data.get('avg_pnl', 0) > 0:
                    recs.append(f"✅ {mode_data['mode']} 모드 수익 중 - 비중 확대 검토")
                else:
                    recs.append(f"⚠️ {mode_data['mode']} 모드 손실 중 - 조건 재검토 필요")
        
        if len(recs) == 0:
            recs.append("📊 더 많은 거래 데이터가 필요합니다 (최소 20회 권장)")
        
        return recs
    
    def suggest_parameter_changes(self):
        """파라미터 변경 제안"""
        df = self.load_trade_history()
        if df is None or len(df) < 15:
            return None
        
        suggestions = []
        
        # SL/TP 최적화
        sl_hits = len(df[df['exit_reason'] == 'SL'])
        tp_hits = len(df[df['exit_reason'] == 'TP'])
        total = len(df)
        
        sl_ratio = sl_hits / total
        tp_ratio = tp_hits / total
        
        if sl_ratio > 0.7:
            suggestions.append({
                'parameter': 'SL_PERCENT',
                'current': 0.012,
                'suggested': 0.015,
                'reason': f'SL 비율 {sl_ratio*100:.1f}% - 너무 빨리 손절 중'
            })
        
        if tp_ratio > 0.6:
            suggestions.append({
                'parameter': 'TP_PERCENT',
                'current': 0.025,
                'suggested': 0.020,
                'reason': f'TP 비율 {tp_ratio*100:.1f}% - 수익 실현이 빠름, 더 빨리 확보'
            })
        
        # RSI 임계값 조정
        long_winners = df[(df['type'] == 'LONG') & (df['pnl'] > 0)]
        if len(long_winners) > 5:
            avg_entry_rsi = long_winners['entry_rsi'].mean()
            if avg_entry_rsi > 35:  # RSI 30보다 높게 성공
                suggestions.append({
                    'parameter': 'RSI_LONG_THRESHOLD',
                    'current': 30,
                    'suggested': int(avg_entry_rsi),
                    'reason': f'성공한 롱의 평균 진입 RSI: {avg_entry_rsi:.1f}'
                })
        
        return suggestions


if __name__ == "__main__":
    learner = SelfLearningSystem()
    
    # 학습 실행
    insights = learner.learn_from_trades()
    
    if insights:
        # 논문 생성
        thesis = learner.generate_trading_thesis()
        print(f"\n✅ 학습 시스템 테스트 완료!")
        print(f"   논문: {thesis}")
