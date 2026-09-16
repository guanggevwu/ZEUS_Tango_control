@echo off
setlocal

set "PATH_TWO_LEVELS_UP="
for %%a in ("%~dp0..\..") do set "PATH_TWO_LEVELS_UP=%%~fa"
cd /d "%PATH_TWO_LEVELS_UP%" || exit /b 1

git pull

set "PY=.\venv\Scripts\python.exe"
set "SERVER=.\GX_regulator\server.py"

start "TA1_regulator_1" /min "%PY%" "%SERVER%" "TA1_regulator_1"
start "TA1_regulator_1" /min "%PY%" "%SERVER%" "TA1_regulator_2"
start "TA1_regulator_3" /min "%PY%" "%SERVER%" "TA1_regulator_3"

endlocal
exit /b 0