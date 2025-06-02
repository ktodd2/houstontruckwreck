@echo off
echo 🚛 Houston Traffic Monitor - Git Setup
echo =====================================
echo.

echo Initializing Git repository...
git init

echo.
echo Adding all files to Git...
git add .

echo.
echo Creating initial commit...
git commit -m "Initial commit: Houston Traffic Monitor with custom logo and stall toggle feature"

echo.
echo ✅ Git repository initialized successfully!
echo.
echo Next steps:
echo 1. Create a new repository on GitHub.com
echo 2. Copy the repository URL
echo 3. Run: git remote add origin YOUR_GITHUB_URL
echo 4. Run: git branch -M main
echo 5. Run: git push -u origin main
echo.
echo See GITHUB_SETUP.md for detailed instructions.
pause
