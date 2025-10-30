set "PATH_TWO_LEVELS_UP="
for %%a in ("%~dp0..\..") do set "PATH_TWO_LEVELS_UP=%%~fa"
cd %PATH_TWO_LEVELS_UP%
git pull
".\venv\Scripts\python.exe" ".\register\register_device_server.py"