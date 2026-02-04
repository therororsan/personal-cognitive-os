@echo off
setlocal EnableExtensions

REM ===========================================================
REM  run_episode_builder.bat
REM  - Runs: python -m jobs.run_episode_builder
REM  - Prints operator-friendly context
REM  - Appends output to: backend\logs\run_episode_builder_YYYYMMDD.log
REM ===========================================================

echo ===========================================================
echo [run_episode_builder] %DATE% %TIME%
echo [run_episode_builder] cwd: %CD%

REM Ensure logs directory exists (quiet if already present)
if not exist "logs" mkdir "logs" >nul 2>nul

REM Robust date stamp (independent of locale date format)
set "LOGDATE="
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd"') do set "LOGDATE=%%i"
if "%LOGDATE%"=="" set "LOGDATE=unknown_date"

echo [run_episode_builder] python on PATH:
where python 2>nul
python --version 2>nul

echo -----------------------------------------------------------
echo [run_episode_builder] running: python -m jobs.run_episode_builder
echo [run_episode_builder] log: logs\run_episode_builder_%LOGDATE%.log
echo -----------------------------------------------------------

REM Run episode builder, tee-like behavior via appending to log (stdout+stderr)
python -m jobs.run_episode_builder >> "logs\run_episode_builder_%LOGDATE%.log" 2>&1
set "EXITCODE=%ERRORLEVEL%"

echo -----------------------------------------------------------
echo [run_episode_builder] exit_code: %EXITCODE%
echo ===========================================================

endlocal & exit /b %EXITCODE%
