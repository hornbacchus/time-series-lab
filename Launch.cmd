@echo off
setlocal
title Time Series Lab
color 0B

set "PROJECT=C:\Users\matth\OneDrive\Projects\Time Series Lab"
set "ENGINE=%PROJECT%\engine"
set "XLL_DIR=%PROJECT%\src\TSL.AddIn\bin\x64\Release\net48"
set "XLL=%XLL_DIR%\TimeSeriesLab-AddIn64.xll"
set "EXCEL=C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE"

:: ---------------------------------------------------------------
:: Pre-flight checks
:: ---------------------------------------------------------------
if not exist "%XLL%" (
    echo.
    echo  [ERROR] Add-in not found: %XLL%
    echo.
    echo  Run "Install Time Series Lab.cmd" first to build the project.
    echo.
    pause
    exit /b 1
)

if not exist "%EXCEL%" (
    echo.
    echo  [ERROR] Excel not found: %EXCEL%
    echo.
    pause
    exit /b 1
)

echo.
echo  Starting Time Series Lab...
echo.

:: ---------------------------------------------------------------
:: Allow unsigned add-ins (suppresses the "Enable" security prompt)
:: ---------------------------------------------------------------
reg add "HKCU\Software\Microsoft\Office\16.0\Excel\Security" /v "RequireAddinSig" /t REG_DWORD /d 0 /f >nul 2>&1

:: ---------------------------------------------------------------
:: Skip the Start screen — open directly to a blank workbook
:: ---------------------------------------------------------------
reg add "HKCU\Software\Microsoft\Office\16.0\Excel\Options" /v "DisableBootToOfficeStart" /t REG_DWORD /d 1 /f >nul 2>&1

:: ---------------------------------------------------------------
:: Register XLL to auto-load with Excel (via OPEN registry key)
:: This way Excel opens normally with a blank workbook + add-in.
:: ---------------------------------------------------------------
set "EXCEL_OPTS=HKCU\Software\Microsoft\Office\16.0\Excel\Options"

:: Check if already registered
reg query "%EXCEL_OPTS%" 2>nul | find /i "TimeSeriesLab" >nul
if %errorlevel% equ 0 goto :xll_registered

:: Not registered - find first available OPEN slot
reg query "%EXCEL_OPTS%" /v "OPEN" >nul 2>&1
if %errorlevel% neq 0 (
    reg add "%EXCEL_OPTS%" /v "OPEN" /t REG_SZ /d "/R \"%XLL%\"" /f >nul 2>&1
    echo  [OK] Registered add-in for auto-loading.
    goto :xll_registered
)
reg query "%EXCEL_OPTS%" /v "OPEN1" >nul 2>&1
if %errorlevel% neq 0 (
    reg add "%EXCEL_OPTS%" /v "OPEN1" /t REG_SZ /d "/R \"%XLL%\"" /f >nul 2>&1
    echo  [OK] Registered add-in for auto-loading.
    goto :xll_registered
)
reg query "%EXCEL_OPTS%" /v "OPEN2" >nul 2>&1
if %errorlevel% neq 0 (
    reg add "%EXCEL_OPTS%" /v "OPEN2" /t REG_SZ /d "/R \"%XLL%\"" /f >nul 2>&1
    echo  [OK] Registered add-in for auto-loading.
    goto :xll_registered
)

:xll_registered

:: ---------------------------------------------------------------
:: Start Python engine (minimized, in background)
:: ---------------------------------------------------------------
start "TSL Engine" /min python "%ENGINE%\engine_worker.py"

:: Give the engine a moment to start listening on the pipe
timeout /t 2 /nobreak > nul

:: ---------------------------------------------------------------
:: Launch Excel (opens with blank workbook, add-in auto-loads)
:: ---------------------------------------------------------------
start "" "%EXCEL%"

echo  [OK] Time Series Lab is running.
echo       - Python engine started (minimized window)
echo       - Excel opening with add-in loaded
echo.
echo  Look for the "Time Series Lab" ribbon tab in Excel.
echo  Try: =TSL_VERSION() in any cell.
echo.
echo  This window will close in 5 seconds...
timeout /t 5 /nobreak > nul
