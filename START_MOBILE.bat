@echo off
cd /d "%~dp0"
set PATH=C:\Program Files (x86)\cloudflared;C:\Program Files\cloudflared;%PATH%
if exist ACCESS_URL.txt del /f /q ACCESS_URL.txt
python dev_bridge.py
pause
