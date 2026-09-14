@echo off
REM ==============================================================================
REM Five Metal Masonry (FMM) - 1-Click GCP Deployment Launcher (Bypasses PS Policy)
REM ==============================================================================
echo ================================================================================
echo   FIVE METAL MASONRY - GOOGLE CLOUD RUN DEPLOYMENT
echo ================================================================================

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0deploy_gcp.ps1"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Deployment script exited with an error.
    pause
)
