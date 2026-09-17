@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Songlim - Render Deploy

set "REPO=https://github.com/hijaewook/songlim"
set "DEPLOY_URL=https://render.com/deploy?repo=https://github.com/hijaewook/songlim"

echo ============================================================
echo  Songlim - Render Deployment Helper
echo ============================================================
echo.
echo GitHub repository:
echo   %REPO%
echo.
echo This file will open Render's deployment page for the repo.
echo.
echo FIRST DEPLOY ONLY:
echo   1. Sign in to Render
echo   2. If asked, connect/authorize GitHub
echo   3. Confirm repository: hijaewook/songlim
echo   4. Review the Blueprint
echo   5. Click "Deploy Blueprint" / "Apply"
echo.
echo After deploy succeeds, Render will show a public URL similar to:
echo   https://songlim.onrender.com
echo.
echo Future GitHub commits will auto-deploy because render.yaml uses:
echo   autoDeployTrigger: commit
echo.
pause

start "" "%DEPLOY_URL%"

echo.
echo Browser opened.
echo.
echo When Render finishes deployment:
echo   - Open the generated onrender.com URL.
echo   - Share that HTTPS URL with your friend.
echo   - The game automatically uses secure WebSocket (wss://).
echo.
echo NOTE:
echo   Render Free web services may sleep after inactivity.
echo   The first connection after sleep can take some time.
echo.
pause
