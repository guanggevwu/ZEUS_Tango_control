@echo off
setlocal

for %%a in ("%~dp0..\..") do set "REPO_ROOT=%%~fa"
cd /d "%REPO_ROOT%" || exit /b 1

set "PY=%REPO_ROOT%\venv\Scripts\python.exe"
set "GUI=%REPO_ROOT%\Newmark\GUI.py"
if not exist "%PY%" exit /b 1
if not exist "%GUI%" exit /b 1
if not defined TANGO_HOST set "TANGO_HOST=192.168.131.39:10000"

rem Fixed startup delay; this does not check that the servers are ready.
timeout /t 15 /nobreak >nul
start "Newmark combined GUI" /min "%PY%" "%GUI%" "laser/newmark/PW_grating_1"

endlocal
exit /b 0