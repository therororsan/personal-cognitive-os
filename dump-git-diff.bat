@echo off
cd /d "%~dp0"

set "DIFF_FILE=last-git-diff.txt"

echo Last git diff captured at %DATE% %TIME% > "%DIFF_FILE%"
echo. >> "%DIFF_FILE%"
echo Branch: >> "%DIFF_FILE%"
git branch --show-current >> "%DIFF_FILE%"
echo. >> "%DIFF_FILE%"
echo Status: >> "%DIFF_FILE%"
git status --short >> "%DIFF_FILE%"
echo. >> "%DIFF_FILE%"
echo. >> "%DIFF_FILE%"
echo === Full diff (what actually changed) === >> "%DIFF_FILE%"
git diff >> "%DIFF_FILE%"

echo.
echo Done. File created: %DIFF_FILE%
echo Now drag %DIFF_FILE% into the chat or copy-paste its content.
pause