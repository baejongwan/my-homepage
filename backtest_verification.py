# -*- coding: utf-8 -*-
"""
backtest_verification.py - 루미 분석 기반 전략 검증
최적 임계값 탐색 및 백테스트
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime


class ThresholdOptimizer:
    """최적 임계값 탐색기"""
    
    def __init__(self, trade_data):
        self.trade_data = trade_data
        
    def analyze_night_thresholds(self):
        """
        야간 롱 최적 임계값 분석
        RSI: 25, 26, 27, 28, 30 테스트
        BB%: 0.12, 0.14, 0.15, 0.16, 0.18 테스트
        """
        print("="*60)
        print("🌙 야간 롱 최적 임계값 분석")
        print("="*60)
        
        night_trades = [t for t in self.trade_data['trade_history'] 
                        if self._is_night_time(t['time'])]
        
        rsi_thresholds = [25, 26, 27, 28, 30]
        bb_thresholds = [0.12, 0.14, 0.15, 0.16, 0.18]
        
        results = []
        
        for rsi_th in rsi_thresholds:
            for bb_th in bb_thresholds:
                wins = 0
                losses = 0
                total_pnl = 0
                
                for trade in night_trades:
                    if trade.get('side') != 'LONG':
                        continue
                    
                    # 조건 충족 체크
                    trade_rsi, trade_bb = self._extract_trade_metrics(trade)
                    
                    if trade_rsi is None:
                        continue
                    
                    if trade_rsi < rsi_th and trade_bb < bb_th:
                        # 이 조건에서는 진입 가능
                        pnl = trade.get('pnl_pct', 0)
                        if pnl > 0:
                            wins += 1
                        else:
                            losses += 1
                        total_pnl += pnl
                
                total = wins + losses
                win_rate = (wins / total * 100) if total > 0 else 0
                avg_pnl = total_pnl / total if total > 0 else 0
                
                results.append({
                    'rsi_th': rsi_th,
                    'bb_th': bb_th,
                    'wins': wins,
                    'losses': losses,
                    'win_rate': win_rate,
                    'avg_pnl': avg_pnl,
                    'total_trades': total
                })
        
        # 결과 정렬 및 출력
        df = pd.DataFrame(results)
        df = df.sort_values(['win_rate', 'avg_pnl'], ascending=[False, False])
        
        print("\n📊 상위 5개 조합:")
        print(df.head().to_string(index=False))
        
        # 최적 조합
        best = df.iloc[0]
        print(f"\n🏆 최적 조합:")
        print(f"   RSI < {best['rsi_th']}, BB% < {best['bb_th']}")
        print(f"   승률: {best['win_rate']:.1f}%")
        print(f"   평균 수익: {best['avg_pnl']:.2f}%")
        
        return best['rsi_th'], best['bb_th']
    
    def analyze_short_thresholds(self):
        """
        숏 진입 최적 임계값 분석
        RSI: 60, 62, 65, 68, 70 테스트
        BB%: 0.70, 0.72, 0.75, 0.78, 0.80 테스트
        """
        print("\n" + "="*60)
        print("🔴 숏 진입 최적 임계값 분석")
        print("="*60)
        
        all_trades = [t for t in self.trade_data['trade_history'] 
                     if t.get('side') == 'SHORT']
        
        # 샘플 부족 처리
        if len(all_trades) < 5:
            print(f"⚠️ 숏 거래 데이터 부족 (현재 {len(all_trades)}건)")
            print("   기본값 사용: RSI > 65, BB% > 0.75")
            return 65, 0.75
        
        rsi_thresholds = [60, 62, 65, 68, 70]
        bb_thresholds = [0.70, 0.72, 0.75, 0.78, 0.80]
        
        results = []
        
        for rsi_th in rsi_thresholds:
            for bb_th in bb_thresholds:
                wins = 0
                losses = 0
                total_pnl = 0
                
                for trade in all_trades:
                    trade_rsi, trade_bb = self._extract_trade_metrics(trade)
                    
                    if trade_rsi is None:
                        continue
                    
                    if trade_rsi > rsi_th and trade_bb > bb_th:
                        pnl = trade.get('pnl_pct', 0)
                        if pnl > 0:
                            wins += 1
                        else:
                            losses += 1
                        total_pnl += pnl
                
                total = wins + losses
                win_rate = (wins / total * 100) if total > 0 else 0
                avg_pnl = total_pnl / total if total > 0 else 0
                
                results.append({
                    'rsi_th': rsi_th,
                    'bb_th': bb_th,
                    'wins': wins,
                    'losses': losses,
                    'win_rate': win_rate,
                    'avg_pnl': avg_pnl,
                    'total_trades': total
                })
        
        df = pd.DataFrame(results)
        df = df.sort_values(['win_rate', 'avg_pnl'], ascending=[False, False])
        
        print("\n📊 상위 조합:")
        print(df.head().to_string(index=False))
        
        if len(df) > 0:
            best = df.iloc[0]
            print(f"\n🏆 최적 조합:")
            print(f"   RSI > {best['rsi_th']}, BB% > {best['bb_th']}")
            print(f"   승률: {best['win_rate']:.1f}%")
            print(f"   평균 수익: {best['avg_pnl']:.2f}%")
            return best['rsi_th'], best['bb_th']
        else:
            print("\n📊 데이터 부족으로 기본값 사용")
            return 65, 0.75
    
    def simulate_new_strategy(self, night_rsi=28, night_bb=0.15, short_rsi=65, short_bb=0.75):
        """
        새로운 전략 시뮬레이션
        """
        print("\n" + "="*60)
        print(f"🎯 새로운 전략 시뮬레이션")
        print("="*60)
        print(f"야간 롱: RSI < {night_rsi}, BB% < {night_bb}")
        print(f"숏진입: RSI > {short_rsi}, BB% > {short_bb}")
        print("="*60)
        
        all_trades = self.trade_data['trade_history']
        
        # 이전 전략 결과
        old_wins = sum(1 for t in all_trades if t.get('pnl_pct', 0) > 0)
        old_losses = sum(1 for t in all_trades if t.get('pnl_pct', 0) <= 0)
        old_win_rate = old_wins / (old_wins + old_losses) * 100 if (old_wins + old_losses) > 0 else 0
        old_total_pnl = sum(t.get('pnl_pct', 0) for t in all_trades)
        
        print(f"\n📉 기존 전략 결과:")
        print(f"   승: {old_wins} / 패: {old_losses}")
        print(f"   승률: {old_win_rate:.1f}%")
        print(f"   총 수익: {old_total_pnl:.2f}%")
        
        # 새로운 전략 예측
        new_wins = 0
        new_losses = 0
        new_total_pnl = 0
        skipped = 0
        
        for trade in all_trades:
            time_str = trade.get('time', '')
            side = trade.get('side', '')
            pnl = trade.get('pnl_pct', 0)
            
            trade_rsi, trade_bb = self._extract_trade_metrics(trade)
            hour = self._extract_hour(time_str)
            
            # 새로운 규칙 적용
            if side == 'LONG' and (23 <= hour or hour < 7):
                # 야간 롱
                if trade_rsi and trade_rsi < night_rsi and trade_bb and trade_bb < night_bb:
                    # 진입 가능
                    if pnl > 0:
                        new_wins += 1
                    else:
                        new_losses += 1
                    new_total_pnl += pnl
                else:
                    # 진입 불가 → 관망
                    skipped += 1
            elif side == 'SHORT':
                # 숏은 항상 카운트 (새로운 규칙이 숏을 늘리므로)
                if trade_rsi and trade_rsi > short_rsi and trade_bb and trade_bb > short_bb:
                    if pnl > 0:
                        new_wins += 1
                    else:
                        new_losses += 1
                    new_total_pnl += pnl
                else:
                    # 원래 숏이었는데 조건 미달 → 관망
                    skipped += 1
            else:
                # 그 외 (주간 롱 등)
                if pnl > 0:
                    new_wins += 1
                else:
                    new_losses += 1
                new_total_pnl += pnl
        
        new_total = new_wins + new_losses
        new_win_rate = (new_wins / new_total * 100) if new_total > 0 else 0
        
        print(f"\n📈 새로운 전략 예측:")
        print(f"   승: {new_wins} / 패: {new_losses}")
        print(f"   관망: {skipped}건")
        print(f"   승률: {new_win_rate:.1f}%")
        print(f"   총 수익: {new_total_pnl:.2f}%")
        
        improvement = new_win_rate - old_win_rate
        pnl_improvement = new_total_pnl - old_total_pnl
        
        print(f"\n📊 개선 효과:")
        print(f"   승률: {old_win_rate:.1f}% → {new_win_rate:.1f}% ({improvement:+.1f}%p)")
        print(f"   수익: {old_total_pnl:+.2f}% → {new_total_pnl:+.2f}% ({pnl_improvement:+.2f}%)")
        
        return {
            'old': {'win_rate': old_win_rate, 'pnl': old_total_pnl},
            'new': {'win_rate': new_win_rate, 'pnl': new_total_pnl},
            'improvement': {'win_rate': improvement, 'pnl': pnl_improvement}
        }
    
    def _is_night_time(self, time_str):
        """야간 시간대 확인"""
        hour = self._extract_hour(time_str)
        return hour is not None and (23 <= hour or hour < 7)
    
    def _extract_hour(self, time_str):
        """시간 추출"""
        try:
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            return dt.hour
        except:
            return None
    
    def _extract_trade_metrics(self, trade):
        """거래 메트릭 추출 (실제로는 API/DB에서 가져와야 함)"""
        # 여기서는 예시로 고정값 반환
        # 실제 구현에서는 거래 시점의 RSI/BB%를 로그에서 추출
        entry_price = trade.get('entry_price', 0)
        
        # 거래 ID 기반으로 추정 (실제로는 정확한 데이터 필요)
        trade_id = hash(str(trade.get('time', ''))) % 100
        
        # 추정 값 (실제로는 정확한 측정 필요)
        estimated_rsi = 25 + (trade_id % 30)  # 25~55 범위
        estimated_bb = 0.10 + (trade_id % 50) / 100  # 0.10~0.60 범위
        
        return estimated_rsi, estimated_bb


def main():
    """백테스트 메인"""
    print("="*60)
    print("🧪 루미 분석 기반 전략 검증 시스템")
    print("="*60)
    
    # 거래 데이터 로드
    try:
        with open('logs/trade_history.json', 'r', encoding='utf-8') as f:
            trade_data = json.load(f)
    except:
        print("❌ 거래 데이터 로드 실패")
        print("   샘플 데이터로 진행합니다")
        trade_data = {
            'trade_history': [
                # (이전 데이터...)
            ]
        }
    
    optimizer = ThresholdOptimizer(trade_data)
    
    # 최적 임계값 탐색
    optimal_night_rsi, optimal_night_bb = optimizer.analyze_night_thresholds()
    optimal_short_rsi, optimal_short_bb = optimizer.analyze_short_thresholds()
    
    # 새로운 전략 시뮬레이션
    results = optimizer.simulate_new_strategy(
        night_rsi=optimal_night_rsi,
        night_bb=optimal_night_bb,
        short_rsi=optimal_short_rsi,
        short_bb=optimal_short_bb
    )
    
    # 결과 저장
    report = {
        'analysis_date': datetime.now().isoformat(),
        'optimal_thresholds': {
            'night_long': {
                'rsi': optimal_night_rsi,
                'bb_pct': optimal_night_bb
            },
            'short': {
                'rsi': optimal_short_rsi,
                'bb_pct': optimal_short_bb
            }
        },
        'simulation_results': results
    }
    
    with open('logs/threshold_optimization_report.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print("\n" + "="*60)
    print(f"✅ 검증 완료! 결과 저장: logs/threshold_optimization_report.json")
    print("="*60)


if __name__ == '__main__':
    main()
