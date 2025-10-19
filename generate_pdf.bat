@echo off
REM ============================================
REM Comic PDF Generator - Easy Execution
REM ============================================

setlocal enabledelayedexpansion

REM Get the script directory
set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

REM Default parameters
set HTML_INPUT=output_template\page.html
set PDF_OUTPUT=output\comic.pdf
set QUALITY=85
set WIDTH=3000
set HEIGHT=3000

REM Parse command line arguments
:parse_args
if "%~1"=="" goto run_converter
if "%~1"=="--quality" (
    set QUALITY=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--output" (
    set PDF_OUTPUT=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--html" (
    set HTML_INPUT=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="--help" (
    goto show_help
)
shift
goto parse_args

:run_converter
echo.
echo ============================================
echo Comic PDF Generator
echo ============================================
echo.
echo HTML Input:  %HTML_INPUT%
echo PDF Output:  %PDF_OUTPUT%
echo Quality:    %QUALITY%%
echo.

REM Run Python converter
"%SCRIPT_DIR%venv\Scripts\python.exe" "tools\html_to_pdf_browser.py" ^
    --html "%HTML_INPUT%" ^
    --out "%PDF_OUTPUT%" ^
    --quality %QUALITY% ^
    --width %WIDTH% ^
    --height %HEIGHT%

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================
    echo SUCCESS! PDF generated: %PDF_OUTPUT%
    echo ============================================
    echo.
) else (
    echo.
    echo FAILED! Check the errors above.
    echo.
)

endlocal
goto end

:show_help
echo.
echo Usage: generate_pdf.bat [OPTIONS]
echo.
echo Options:
echo   --quality VALUE    JPEG quality 1-100 (default: 85)
echo   --output PATH      Output PDF path (default: output\comic.pdf)
echo   --html PATH        Input HTML path (default: output_template\page.html)
echo   --help             Show this help message
echo.
echo Examples:
echo   generate_pdf.bat
echo   generate_pdf.bat --quality 95
echo   generate_pdf.bat --quality 75 --output output\comic_web.pdf
echo.

:end
pause
