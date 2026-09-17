@echo off
setlocal
cd /d "%~dp0"
echo Checking deploy files...
set ERR=0

for %%F in (app.py requirements.txt Dockerfile render.yaml static\index.html) do (
  if not exist "%%F" (
    echo [MISSING] %%F
    set ERR=1
  ) else (
    echo [OK] %%F
  )
)

echo.
if "%ERR%"=="0" (
  echo Deployment package looks complete.
  echo You can now run deploy_to_render.bat
) else (
  echo Some required files are missing.
)
echo.
pause
