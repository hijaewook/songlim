@echo off
setlocal
cd /d "%~dp0"

where docker >nul 2>nul
if errorlevel 1 (
    echo Docker was not found.
    echo Install Docker Desktop first, then run this file again.
    pause
    exit /b 1
)

docker build -t coop-roguelike .
if errorlevel 1 pause & exit /b 1

echo.
echo Open http://127.0.0.1:8000
echo.
docker run --rm -p 8000:8000 coop-roguelike
pause
