@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  set "PY=py"
) else (
  set "PY=python"
)

if not exist ".venv" %PY% -m venv .venv
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ============================================================
echo PROJECT WRECKED ONLINE
echo Local: http://127.0.0.1:8000
echo LAN  : http://YOUR_IPV4:8000
echo ============================================================
echo.
python -m uvicorn app:app --host 0.0.0.0 --port 8000
pause
