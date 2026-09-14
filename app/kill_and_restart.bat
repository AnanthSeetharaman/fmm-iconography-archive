@echo off
REM ==============================================================================
REM Five Metal Masonry (FMM) - Kill & Restart Server (One-Click Launcher)
REM ==============================================================================
title FMM Archive Server - Kill and Restart
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0kill_and_restart.ps1"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Script exited with code %ERRORLEVEL%.
    pause
)
