@echo off
setlocal

for %%a in ("%~dp0..\..") do set "REPO_ROOT=%%~fa"
cd /d "%REPO_ROOT%" || exit /b 1

set "PY=%REPO_ROOT%\venv\Scripts\python.exe"
if not exist "%PY%" (
    echo Python virtual environment not found: "%PY%"
    pause
    exit /b 1
)

"%PY%" -m ConditionSetter.condition_setter %*
if errorlevel 1 (
    echo Condition setter failed to start or exited with an error.
    pause
    exit /b 1
)

endlocal