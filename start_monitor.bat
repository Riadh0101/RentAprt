@echo off
chcp 65001 > nul
echo ========================================================
echo   HERMES RENTAL MONITOR - بدء المراقبة المستمرة
echo ========================================================
cd /d "%~dp0"
.venv\Scripts\python.exe main.py monitor
pause
