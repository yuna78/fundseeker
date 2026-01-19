@echo off
setlocal enabledelayedexpansion

set "PROJECT_ROOT=%~dp0"
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"
set "VENV_DIR=%PROJECT_ROOT%\.venv"
set "ENTRY_POINT=%PROJECT_ROOT%\.main.py"
set "FORCE_INSTALL="

if /I "%~1"=="repair" (
    set "FORCE_INSTALL=1"
    shift
)

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [FundSeeker] Creating virtual environment...
    py -3 -m venv "%VENV_DIR%"
)

call "%VENV_DIR%\Scripts\activate.bat"

set "NEED_INSTALL=0"
if not exist "%VENV_DIR%\.deps-installed" set "NEED_INSTALL=1"
if defined FORCE_INSTALL set "NEED_INSTALL=1"

if "%NEED_INSTALL%"=="0" (
    "%VENV_DIR%\Scripts\python.exe" -c "import typer" >nul 2>&1
    if errorlevel 1 set "NEED_INSTALL=1"
)

if "%NEED_INSTALL%"=="1" (
    echo [FundSeeker] Installing dependencies...
    pip install -q -r "%PROJECT_ROOT%\requirements.txt" -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo [FundSeeker] Failed to install dependencies. Please check your network/py command.
        exit /b 1
    )
    type nul > "%VENV_DIR%\.deps-installed"
)

if defined FORCE_INSTALL (
    echo [FundSeeker] Repair complete.
    exit /b 0
)

echo [FundSeeker] Launching CLI...
if "%~1"=="" (
    python "%ENTRY_POINT%" menu
) else (
    python "%ENTRY_POINT%" %*
)
