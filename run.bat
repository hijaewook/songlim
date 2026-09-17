@echo off
setlocal
cd /d %~dp0
where py >nul 2>nul
if %errorlevel%==0 (
  set PY=py
) else (
  set PY=python
)
if not exist .venv (
  %PY% -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.
echo Game server: http://127.0.0.1:8000
echo Close this window to stop the server.
echo.
python -m uvicorn app:app --host 127.0.0.1 --port 8000
pause
