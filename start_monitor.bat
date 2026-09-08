@echo off
chcp 65001 > nul
echo ========================================================
echo   HERMES RENTAL MONITOR - بدء المراقبة المستمرة (كل 20 دقيقة)
echo ========================================================
cd /d "%~dp0"
.venv\Scripts\python.exe -m src.scheduler
pause
