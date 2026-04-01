@echo off
echo ===============================================
echo GenTwin Setup Script - Python 3.12 Environment
echo ===============================================
echo.

REM Check if Python 3.12 is available
py -3.12 --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.12 not found!
    echo.
    echo Please install Python 3.12 from: https://www.python.org/downloads/
    echo.
    echo After installing, run this script again.
    pause
    exit /b 1
)

echo Found Python 3.12! Creating virtual environment...
echo.

REM Create virtual environment with Python 3.12
py -3.12 -m venv venv

echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo ===============================================
echo Setup Complete!
echo ===============================================
echo.
echo Your virtual environment is now activated.
echo To activate it in the future, run:
echo   .\venv\Scripts\activate
echo.
echo To run the project:
echo   python setup_and_test.py
echo.
pause
