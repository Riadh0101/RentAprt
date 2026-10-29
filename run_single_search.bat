@echo off
chcp 65001 > nul
echo ========================================================
echo   HERMES RENTAL MONITOR - تشغيل دورة بحث فورية
echo ========================================================
cd /d "%~dp0"
.venv\Scripts\python.exe main.py run-once
pause
