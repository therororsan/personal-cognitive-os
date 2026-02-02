@echo off
setlocal

REM Ensure consistent imports regardless of launch location
cd /d "%~dp0"

echo ===========================================================
echo [run_digest] %date% %time%
echo [run_digest] cwd: %cd%
echo [run_digest] python on PATH:
where python 2>nul
python --version 2>nul
echo -----------------------------------------------------------
echo [run_digest] running: python -m jobs.run_digest
echo -----------------------------------------------------------

python -m jobs.run_digest
set "RC=%ERRORLEVEL%"

echo -----------------------------------------------------------
echo [run_digest] exit_code: %RC%
echo ===========================================================

exit /b %RC%
