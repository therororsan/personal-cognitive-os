@echo off
setlocal EnableExtensions

REM ===========================================================
REM  run_digest.bat
REM  - Runs: python -m jobs.run_digest
REM  - Prints operator-friendly context
REM  - Appends output to: backend\logs\run_digest_YYYYMMDD.log
REM ===========================================================

echo ===========================================================
echo [run_digest] %DATE% %TIME%
echo [run_digest] cwd: %CD%

REM Ensure logs directory exists (quiet if already present)
if not exist "logs" mkdir "logs" >nul 2>nul

REM Robust date stamp (independent of locale date format)
set "LOGDATE="
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd"') do set "LOGDATE=%%i"
if "%LOGDATE%"=="" set "LOGDATE=unknown_date"

echo [run_digest] python on PATH:
where python 2>nul
python --version 2>nul

echo -----------------------------------------------------------
echo [run_digest] running: python -m jobs.run_digest
echo [run_digest] log: logs\run_digest_%LOGDATE%.log
echo -----------------------------------------------------------

REM Run digest, tee-like behavior via appending to log (stdout+stderr)
python -m jobs.run_digest >> "logs\run_digest_%LOGDATE%.log" 2>&1
set "EXITCODE=%ERRORLEVEL%"

echo -----------------------------------------------------------
echo [run_digest] exit_code: %EXITCODE%
echo ===========================================================

endlocal & exit /b %EXITCODE%
