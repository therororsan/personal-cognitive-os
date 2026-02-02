@echo off
setlocal

echo ===========================================================
echo [smoke_digest] %DATE% %TIME%
echo [smoke_digest] cwd: %CD%
if "%PCO_API_KEY%"=="" (
  echo [smoke_digest] ERROR: PCO_API_KEY is not set in this cmd.exe window.
  echo [smoke_digest] Fix: set PCO_API_KEY=YOUR_KEY   then rerun smoke_digest.bat
  echo ===========================================================
  exit /b 2
) else (
  echo [smoke_digest] PCO_API_KEY: (set)
)
echo ===========================================================

REM ---- create one raw event (real schema only) ----
echo [smoke_digest] creating raw event...
curl -s -X POST http://127.0.0.1:8000/v1/raw-events -H "Content-Type: application/json" -H "X-API-Key: %PCO_API_KEY%" -d "{\"source\":\"smoke\",\"text\":\"smoke test @ %DATE% %TIME%\"}"
echo.
echo -----------------------------------------------------------

REM ---- run digest ----
echo [smoke_digest] running digest...
python -m jobs.run_digest
echo -----------------------------------------------------------

REM ---- fetch latest digest insight ----
echo [smoke_digest] fetching latest digest...
curl -s http://127.0.0.1:8000/v1/insights/latest -H "X-API-Key: %PCO_API_KEY%"
echo.
echo -----------------------------------------------------------

echo [smoke_digest] done
echo ===========================================================

endlocal