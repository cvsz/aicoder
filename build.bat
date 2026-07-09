@echo off
REM ============================================================================
REM ZAI Coder CLI — Windows Build Script
REM Creates a standalone .exe using PyInstaller
REM ============================================================================
REM Usage:
REM   build.bat              Build executable
REM   build.bat /clean       Clean then build
REM   build.bat /installer   Build + create NSIS installer
REM   build.bat /all         Clean + build + installer
REM ============================================================================

setlocal enabledelayedexpansion

set VERSION=1.23.0
set EXE_NAME=zai-coder.exe
set CLEAN=0
set BUILD_INSTALLER=0

REM Parse arguments
:parse_args
if "%~1"=="" goto :done_args
if /i "%~1"=="/clean" (set CLEAN=1)
if /i "%~1"=="/installer" (set BUILD_INSTALLER=1)
if /i "%~1"=="/all" (set CLEAN=1 & set BUILD_INSTALLER=1)
if /i "%~1"=="--clean" (set CLEAN=1)
if /i "%~1"=="--installer" (set BUILD_INSTALLER=1)
if /i "%~1"=="--help" goto :show_help
if /i "%~1"=="/?" goto :show_help
shift
goto :parse_args
:done_args

echo.
echo ============================================
echo   ZAI Coder CLI v%VERSION% — Windows Build
echo ============================================
echo.

REM ── Clean ──────────────────────────────────────────────────────────────
if %CLEAN%==1 (
    echo [1/5] Cleaning build artifacts...
    if exist "build" rmdir /s /q build
    if exist "dist" rmdir /s /q dist
    for /d /r . %%d in (__pycache__) do (
        if exist "%%d" rmdir /s /q "%%d"
    )
    echo   Done.
    echo.
) else (
    echo [1/5] Skipping clean ^(use /clean to clean first^)
    echo.
)

REM ── Check Python ────────────────────────────────────────────────────────
echo [2/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo   ERROR: Python not found. Install Python 3.9+ from python.org
    echo   Make sure Python is added to PATH during installation.
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do (
    echo   Python %%i found
)
echo.

REM ── Virtual Environment ────────────────────────────────────────────────
echo [3/5] Setting up build environment...
if not exist "build-venv" (
    python -m venv build-venv
    echo   Created virtual environment
)
call build-venv\Scripts\activate.bat
echo   Activated build-venv

REM Install dependencies
python -m pip install --upgrade pip >nul 2>&1
pip install pyinstaller --quiet 2>nul
if exist "requirements.txt" (
    pip install -r requirements.txt --quiet 2>nul
)
pip install anthropic python-dotenv --quiet 2>nul
echo   Dependencies installed
echo.

REM ── Build ───────────────────────────────────────────────────────────────
echo [4/5] Building standalone executable...
echo   This may take 1-3 minutes...
echo.

if not exist "zai-coder.spec" (
    echo   ERROR: zai-coder.spec not found
    pause
    exit /b 1
)

pyinstaller zai-coder.spec --noconfirm --clean

if errorlevel 1 (
    echo.
    echo   ERROR: Build failed
    pause
    exit /b 1
)

echo.

REM ── Verify ─────────────────────────────────────────────────────────────
echo [5/5] Verifying build output...

if exist "dist\%EXE_NAME%" (
    for %%F in ("dist\%EXE_NAME%") do (
        set SIZE=%%~zF
        set /a SIZE_MB=!SIZE! / 1048576
    )
    echo.
    echo   Build successful!
    echo   Output: dist\%EXE_NAME%
    echo.

    REM Quick version check
    echo   Testing: dist\%EXE_NAME% --version
    dist\%EXE_NAME% --version
    echo.
) else (
    echo   ERROR: dist\%EXE_NAME% not found
    pause
    exit /b 1
)

REM ── NSIS Installer (optional) ──────────────────────────────────────────
if %BUILD_INSTALLER%==1 (
    echo   Building NSIS installer...
    if exist "C:\Program Files ^(x86^)\NSIS\makensis.exe" (
        "C:\Program Files ^(x86^)\NSIS\makensis.exe" installer.nsi
        if exist "dist\ZAI-Coder-%VERSION%-Setup.exe" (
            echo   Installer: dist\ZAI-Coder-%VERSION%-Setup.exe
        )
    ) else if exist "C:\Program Files\NSIS\makensis.exe" (
        "C:\Program Files\NSIS\makensis.exe" installer.nsi
        if exist "dist\ZAI-Coder-%VERSION%-Setup.exe" (
            echo   Installer: dist\ZAI-Coder-%VERSION%-Setup.exe
        )
    ) else (
        echo   NSIS not found. Install from https://nsis.sourceforge.io
        echo   Then run: makensis installer.nsi
    )
    echo.
)

REM ── Summary ────────────────────────────────────────────────────────────
echo ============================================
echo   Build Complete
echo ============================================
echo.
echo   Executable: dist\%EXE_NAME%
echo.
echo   Usage:
echo     set ANTHROPIC_API_KEY=sk-ant-...
echo     dist\%EXE_NAME% -p "Write a hello world"
echo     dist\%EXE_NAME% --tui
echo     dist\%EXE_NAME% --help
echo.
pause
goto :eof

:show_help
echo.
echo ZAI Coder CLI v%VERSION% — Windows Build Script
echo.
echo Usage: build.bat [options]
echo.
echo Options:
echo   /clean       Clean build artifacts before building
echo   /installer   Also build NSIS installer (requires NSIS)
echo   /all         Clean + build + installer
echo   /? or --help Show this help
echo.
echo Examples:
echo   build.bat              Build executable only
echo   build.bat /clean       Clean then build
echo   build.bat /all         Full clean build with installer
echo.
goto :eof
