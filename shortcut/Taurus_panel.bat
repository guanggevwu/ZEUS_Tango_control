@echo off
setlocal

set "REPO_ROOT="
for %%a in ("%~dp0..") do set "REPO_ROOT=%%~fa"
cd /d "%REPO_ROOT%"

if exist ".\venv\Scripts\taurus.exe" (
	".\venv\Scripts\taurus.exe" panel %*
) else (
	taurus panel %*
)

endlocal