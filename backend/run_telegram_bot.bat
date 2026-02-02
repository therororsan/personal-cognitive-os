@echo off
setlocal EnableExtensions

echo ===========================================================
echo [run_telegram_bot] %DATE% %TIME%
echo [run_telegram_bot] cwd: %CD%
echo ===========================================================

if "%TELEGRAM_BOT_TOKEN%"=="" (
  echo [run_telegram_bot] ERROR: TELEGRAM_BOT_TOKEN is not set in this cmd.exe window.
  echo [run_telegram_bot] Fix: set TELEGRAM_BOT_TOKEN=YOUR_TOKEN  then rerun.
  exit /b 2
)

if "%PCO_API_KEY%"=="" (
  echo [run_telegram_bot] ERROR: PCO_API_KEY is not set in this cmd.exe window.
  echo [run_telegram_bot] Fix: set PCO_API_KEY=YOUR_KEY  then rerun.
  exit /b 2
)

if "%PCO_BACKEND_URL%"=="" (
  echo [run_telegram_bot] PCO_BACKEND_URL not set; defaulting to http://127.0.0.1:8000
)

echo -----------------------------------------------------------
echo [run_telegram_bot] running: python telegram_capture_bot.py
echo -----------------------------------------------------------

python telegram_capture_bot.py
set "EXITCODE=%ERRORLEVEL%"

echo -----------------------------------------------------------
echo [run_telegram_bot] exit_code: %EXITCODE%
echo ===========================================================

endlocal & exit /b %EXITCODE%
