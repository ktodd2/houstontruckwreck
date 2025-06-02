@echo off
echo 🚛 Houston Traffic Monitor - GitHub Update
echo ========================================
echo.

echo Adding Replit configuration files...
git add .replit
git add replit.nix
git add main.py
git add REPLIT_SETUP.md

echo.
echo Committing changes...
git commit -m "Add Replit deployment configuration and setup guide"

echo.
echo Pushing to GitHub...
git push

echo.
echo ✅ Replit files pushed to GitHub successfully!
echo.
echo Next steps:
echo 1. Go to Replit.com
echo 2. Create new repl from GitHub
echo 3. Import your repository
echo 4. Configure Secrets (email settings)
echo 5. Click Run!
echo.
echo See REPLIT_SETUP.md for detailed instructions.
pause
