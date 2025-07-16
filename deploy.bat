@echo off
pause
cd /d %~dp0
echo =======================================
echo 🚀 Uploading changes to GitHub...
echo =======================================

set /p message=🔹 Commit message: 
git add .
git commit -m "%message%"
git push origin main

echo.
echo ✅ Okay, your order is successfully delivered 🚀
pause
