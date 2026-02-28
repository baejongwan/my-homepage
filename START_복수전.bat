@echo off
chcp 65001 > nul
echo ============================================
echo     LUMI "복수전" 전략 실행
echo ============================================
echo.
echo 2026-02-19 검증된 +321%% 수익 전략
echo.
echo [설정 확인]
echo   - 진입: RSI 60+ (숏) / RSI 30- (롱)
echo   - 청산: RSI 35- (숏청산) / RSI 65+ (롱청산)
echo   - 손절: -1.2%% (10x 시 -12%%)
echo   - 익절: +2.5%% (10x 시 +25%%)
echo   - 투자: 100%%
echo.
echo ============================================
cd "C:\Users\qmsdl\OneDrive\바탕 화면\tii"

echo.
echo 선택하세요:
echo   [1] 전략 테스트 (strategy_revenge.py)
echo   [2] 설정 확인 (config.py)
echo   [3] 백테스트 비교 (backtest_compare.py)
echo.
set /p choice="선택: "

if "%choice%"=="1" goto strategy
if "%choice%"=="2" goto config
if "%choice%"=="3" goto backtest

:strategy
echo.
echo 복수전 전략 테스트 중...
python strategy_revenge.py
goto end

:config
echo.
echo 현재 설정 확인:
echo.
echo [타임프레임]
type config.py | findstr "TIMEFRAMES"
echo.
echo [투자비율]
type config.py | findstr "ENTRY_PERCENT"
echo.
echo [레버리지]
type config.py | findstr "LEVERAGE"
pause
goto end

:backtest
echo.
echo 백테스트 비교 실행...
python backtest_compare.py
pause
goto end

:end
echo.
echo ============================================
echo 완료!
echo ============================================
pause
