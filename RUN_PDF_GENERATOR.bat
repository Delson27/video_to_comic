@echo off
REM ============================================
REM Comic PDF Generator - Quick Launcher
REM ============================================
REM Just double-click this file to generate PDF!
REM All parameters are in generate_comic_pdf.py
REM ============================================

cd /d "%~dp0"

echo.
echo ============================================
echo Comic PDF Generator
echo ============================================
echo.

"%~dp0venv\Scripts\python.exe" generate_comic_pdf.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================
    echo PDF generated successfully!
    echo ============================================
    echo.
    pause
) else (
    echo.
    echo PDF generation FAILED!
    echo.
    pause
)
