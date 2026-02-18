@echo off 
cd /d "%%~dp0backend" 
python -u telegram_capture_bot.py > ..\bot-log-renamed.txt 2>&1 
