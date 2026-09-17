@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title PROJECT WRECKED ONLINE - Publish

set "REPO=https://github.com/hijaewook/songlim.git"

where git >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Git is not installed.
  pause
  exit /b 1
)

where gh >nul 2>nul
if errorlevel 1 (
  echo [ERROR] GitHub CLI is not installed.
  pause
  exit /b 1
)

gh auth status >nul 2>nul
if errorlevel 1 (
  echo GitHub login is required.
  gh auth login --web --git-protocol https
  if errorlevel 1 pause & exit /b 1
)

if not exist ".git" (
  git init
  git branch -M main
)

git config user.name >nul 2>nul
if errorlevel 1 (
  for /f "delims=" %%U in ('gh api user --jq ".login"') do git config user.name "%%U"
)

git config user.email >nul 2>nul
if errorlevel 1 (
  for /f "delims=" %%U in ('gh api user --jq ".login"') do git config user.email "%%U@users.noreply.github.com"
)

git remote get-url origin >nul 2>nul
if errorlevel 1 (
  git remote add origin "%REPO%"
) else (
  git remote set-url origin "%REPO%"
)

git add -A
git diff --cached --quiet
if errorlevel 1 git commit -m "Convert PROJECT WRECKED to online co-op"

git fetch origin main

REM Record existing GitHub history while keeping this package's exact file tree.
git merge origin/main --allow-unrelated-histories -s ours -m "Merge existing GitHub history" >nul 2>nul

git push -u origin main
if errorlevel 1 (
  echo.
  echo [ERROR] Push failed. Copy the error screen and send it to ChatGPT.
  pause
  exit /b 1
)

echo.
echo ============================================================
echo SUCCESS
echo https://github.com/hijaewook/songlim
echo Render will auto-deploy the new commit.
echo ============================================================
echo.
pause
