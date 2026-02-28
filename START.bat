@echo off
cd "C:\Users\qmsdl\OneDrive\바탕 화면\tii"
echo ================================================
echo  LUMI HYBRID PRO v2.1 - 모듈화 버전 실행
echo ================================================
echo.
echo [1/3] 캐시 삭제 중...
if exist modules\__pycache__ rmdir /s /q modules\__pycache__
if exist __pycache__ rmdir /s /q __pycache__
echo       캐시 삭제 완료!
echo.
echo [2/3] 환경변수 로드 중...
if exist .env (
    echo       .env 파일 로드 완료
) else (
    echo       WARNING: .env 파일 없음
)
echo.
echo [3/3] 봇 시작...
echo.
echo ================================================

REM Python 실행 (모듈 경로 설정)
python -m main

echo.
echo ================================================
echo  실행 종료
echo ================================================
pause
