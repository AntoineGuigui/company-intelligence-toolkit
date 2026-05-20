@echo off
echo ============================================================
echo   Company Profile Generator - Setup & Launch
echo ============================================================
echo.

REM Install dependencies
echo Installing dependencies...
pip install flask pandas openpyxl python-pptx Pillow requests beautifulsoup4 scikit-learn scipy lxml python-dotenv 2>nul

echo.
echo Starting the server...
echo Open http://localhost:8080 in your browser
echo.
python app.py

pause
