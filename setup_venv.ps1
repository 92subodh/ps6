# GenTwin Setup Script - PowerShell Version

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host "GenTwin Setup - Python 3.11/3.12 Environment" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Check for Python 3.12 first
$python312 = py -3.12 --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Found Python 3.12!" -ForegroundColor Green
    $pythonCmd = "py -3.12"
} else {
    # Try Python 3.11
    $python311 = py -3.11 --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Found Python 3.11!" -ForegroundColor Green
        $pythonCmd = "py -3.11"
    } else {
        Write-Host "✗ ERROR: Python 3.11 or 3.12 not found!" -ForegroundColor Red
        Write-Host ""
        Write-Host "You currently have Python 3.14, but TensorFlow doesn't support it yet." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Please install Python 3.11 or 3.12 from:" -ForegroundColor White
        Write-Host "  https://www.python.org/downloads/" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "  • Download Python 3.12 (recommended)" -ForegroundColor White
        Write-Host "  • During install, check 'Add Python to PATH'" -ForegroundColor White
        Write-Host "  • Then run this script again" -ForegroundColor White
        Write-Host ""
        pause
        exit 1
    }
}

Write-Host ""
Write-Host "Creating virtual environment..." -ForegroundColor Yellow

# Create venv
& $pythonCmd -m venv venv

Write-Host "✓ Virtual environment created!" -ForegroundColor Green
Write-Host ""
Write-Host "Activating virtual environment..." -ForegroundColor Yellow

# Activate venv
& .\venv\Scripts\Activate.ps1

Write-Host "✓ Virtual environment activated!" -ForegroundColor Green
Write-Host ""
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet

Write-Host "Installing dependencies (this may take a few minutes)..." -ForegroundColor Yellow
pip install -r requirements.txt

Write-Host ""
Write-Host "===============================================" -ForegroundColor Green
Write-Host "✓ Setup Complete!" -ForegroundColor Green
Write-Host "===============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Your virtual environment is now activated." -ForegroundColor White
Write-Host ""
Write-Host "To activate it in the future, run:" -ForegroundColor Yellow
Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "Or on Command Prompt:" -ForegroundColor Yellow
Write-Host "  .\venv\Scripts\activate.bat" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. python setup_and_test.py" -ForegroundColor Cyan
Write-Host "  2. python run_full_pipeline.py" -ForegroundColor Cyan
Write-Host ""
