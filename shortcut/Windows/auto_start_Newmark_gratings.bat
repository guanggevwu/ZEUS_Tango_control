@echo off
setlocal

for %%a in ("%~dp0..\..") do set "REPO_ROOT=%%~fa"
cd /d "%REPO_ROOT%" || exit /b 1

set "PY=%REPO_ROOT%\venv\Scripts\python.exe"
set "SERVER=%REPO_ROOT%\Newmark\server.py"
if not exist "%PY%" exit /b 1
if not exist "%SERVER%" exit /b 1
if not defined TANGO_HOST set "TANGO_HOST=192.168.131.39:10000"

rem Run once at login. Do not run again while these servers are already running.
start "Newmark PW_grating_1" /min "%PY%" "%SERVER%" "PW_grating_1"
start "Newmark PW_grating_2" /min "%PY%" "%SERVER%" "PW_grating_2"

rem This script waits 15 seconds before opening the combined GUI.
call "%~dp0start_Newmark_GUI.bat"
endlocal
exit /b 0