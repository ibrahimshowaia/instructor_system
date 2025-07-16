@echo off
cd /d %~dp0
echo =======================================
echo 🚀 Uploading changes to GitHub...
echo =======================================

set /p message=🔹 Commit message: 
if "%message%"=="" (
    echo ⚠️ Commit message is required!
    pause
    exit /b
)

git add .
git commit -m "%message%"
git push origin main

echo.
echo ✅ Okay, your update has been uploaded 🚀
pause
