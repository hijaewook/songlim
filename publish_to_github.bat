@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

title Coop Roguelike - GitHub Publisher

echo =========================================================
echo   Coop Roguelike - GitHub Auto Publisher
echo =========================================================
echo.
echo This script will:
echo   1. Install Git if missing
echo   2. Install GitHub CLI if missing
echo   3. Sign in to GitHub if needed
echo   4. Create a GitHub repository if needed
echo   5. Commit and push the current project
echo.

where winget >nul 2>nul
if errorlevel 1 (
    echo [ERROR] winget was not found.
    echo Install "App Installer" from Microsoft Store, then run this file again.
    pause
    exit /b 1
)

where git >nul 2>nul
if errorlevel 1 (
    echo [1/5] Git is not installed. Installing Git...
    winget install --id Git.Git -e --source winget --accept-source-agreements --accept-package-agreements
    if errorlevel 1 (
        echo [ERROR] Git installation failed.
        pause
        exit /b 1
    )
    set "PATH=%PATH%;C:\Program Files\Git\cmd;C:\Program Files\Git\bin"
) else (
    echo [1/5] Git already installed.
)

where gh >nul 2>nul
if errorlevel 1 (
    echo [2/5] GitHub CLI is not installed. Installing...
    winget install --id GitHub.cli -e --source winget --accept-source-agreements --accept-package-agreements
    if errorlevel 1 (
        echo [ERROR] GitHub CLI installation failed.
        pause
        exit /b 1
    )
    set "PATH=%PATH%;C:\Program Files\GitHub CLI"
) else (
    echo [2/5] GitHub CLI already installed.
)

where git >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Git was installed but is not visible in this terminal yet.
    echo Close this window and run publish_to_github.bat again.
    pause
    exit /b 1
)

where gh >nul 2>nul
if errorlevel 1 (
    echo [ERROR] GitHub CLI was installed but is not visible in this terminal yet.
    echo Close this window and run publish_to_github.bat again.
    pause
    exit /b 1
)

echo [3/5] Checking GitHub authentication...
gh auth status >nul 2>nul
if errorlevel 1 (
    echo.
    echo A browser login will open. Sign in to your GitHub account.
    echo If asked which protocol to use, HTTPS is recommended.
    echo.
    gh auth login --web --git-protocol https
    if errorlevel 1 (
        echo [ERROR] GitHub login failed.
        pause
        exit /b 1
    )
)

for /f "delims=" %%U in ('gh api user --jq ".login" 2^>nul') do set "GHUSER=%%U"
if not defined GHUSER (
    echo [ERROR] Could not read your GitHub username.
    pause
    exit /b 1
)

echo.
set /p "REPONAME=Repository name [coop-roguelike-prototype]: "
if "%REPONAME%"=="" set "REPONAME=coop-roguelike-prototype"

echo.
choice /C PR /N /M "Repository visibility: [P]ublic / P[R]ivate ? "
if errorlevel 2 (
    set "VISIBILITY=--private"
) else (
    set "VISIBILITY=--public"
)

echo.
echo [4/5] Preparing local Git repository...

if not exist ".git" (
    git init
    git branch -M main
)

git config user.name >nul 2>nul
if errorlevel 1 git config user.name "%GHUSER%"

git config user.email >nul 2>nul
if errorlevel 1 (
    for /f "delims=" %%E in ('gh api user/emails --jq ".[] | select(.primary==true) | .email" 2^>nul') do (
        if not defined GHEMAIL set "GHEMAIL=%%E"
    )
    if not defined GHEMAIL set "GHEMAIL=%GHUSER%@users.noreply.github.com"
    git config user.email "!GHEMAIL!"
)

git add -A
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "Update coop roguelike prototype"
) else (
    echo No local file changes to commit.
)

echo.
echo [5/5] Publishing to GitHub...

gh repo view "%GHUSER%/%REPONAME%" >nul 2>nul
if errorlevel 1 (
    gh repo create "%REPONAME%" %VISIBILITY% --source "." --remote origin --push
    if errorlevel 1 (
        echo [ERROR] Repository creation or push failed.
        pause
        exit /b 1
    )
) else (
    git remote get-url origin >nul 2>nul
    if errorlevel 1 (
        git remote add origin "https://github.com/%GHUSER%/%REPONAME%.git"
    )
    git push -u origin main
    if errorlevel 1 (
        echo [ERROR] Push failed.
        pause
        exit /b 1
    )
)

echo.
echo =========================================================
echo SUCCESS
echo Repository:
echo https://github.com/%GHUSER%/%REPONAME%
echo =========================================================
echo.
echo Future updates:
echo   Just run publish_to_github.bat again.
echo.
pause
