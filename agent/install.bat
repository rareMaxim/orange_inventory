@echo off
chcp 65001 >nul 2>&1
title Orange Inventory Agent - Installation

:: Check admin privileges
reg query "HKU\S-1-5-19" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Run this script as Administrator!
    echo Right-click - Run as administrator
    pause
    exit /b 1
)

set "INSTALL_DIR=%ProgramData%\OrangeInventory"
set "SCRIPT_DIR=%~dp0"

echo ==========================================
echo  Orange Inventory Agent - Installation
echo ==========================================
echo.

:: Create installation directory
if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%"
    echo [OK] Created: %INSTALL_DIR%
) else (
    echo [OK] Directory exists: %INSTALL_DIR%
)

:: Copy agent binary
if not exist "%SCRIPT_DIR%orange_agent.exe" (
    echo [ERROR] orange_agent.exe not found in %SCRIPT_DIR%
    pause
    exit /b 1
)
copy /Y "%SCRIPT_DIR%orange_agent.exe" "%INSTALL_DIR%\orange_agent.exe" >nul
echo [OK] Copied orange_agent.exe

:: Copy config
if not exist "%SCRIPT_DIR%config.json" (
    echo [ERROR] config.json not found in %SCRIPT_DIR%
    echo Create config.json before running this script.
    pause
    exit /b 1
)
copy /Y "%SCRIPT_DIR%config.json" "%INSTALL_DIR%\config.json" >nul
echo [OK] Copied config.json

echo.
echo Installing scheduled tasks...
echo.

:: Run agent installer
"%INSTALL_DIR%\orange_agent.exe" --install

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Installation failed.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo  Installation completed successfully!
echo  Directory: %INSTALL_DIR%
echo ==========================================
echo.
echo Running first monitoring cycle...
echo.

"%INSTALL_DIR%\orange_agent.exe"

if %errorlevel% equ 0 (
    echo.
    echo [OK] First report sent successfully!
) else (
    echo.
    echo [WARNING] First report failed. Check config.json and server connectivity.
)

pause
