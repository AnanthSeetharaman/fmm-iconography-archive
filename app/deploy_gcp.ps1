# ==============================================================================
# Five Metal Masonry (FMM) Iconography Archive
# 1-Click Automated Deployment Script for Google Cloud Run (Free Tier)
# ==============================================================================

param (
    [string]$ProjectId = "",
    [string]$Region = "us-central1",
    [string]$ServiceName = "fmm-iconography-archive"
)

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  FIVE METAL MASONRY - GOOGLE CLOUD RUN AUTOMATED DEPLOYMENT" -ForegroundColor Yellow
Write-Host "================================================================================" -ForegroundColor Cyan

# 1. Locate gcloud.cmd (CMD script to bypass PowerShell execution restrictions)
$gcloudExecutable = ""

$knownPaths = @(
    "$env:LOCALAPPDATA\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
    "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
    "C:\Program Files\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd",
    "$env:USERPROFILE\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
)

foreach ($path in $knownPaths) {
    if (Test-Path $path) {
        $gcloudExecutable = $path
        break
    }
}

if (-not $gcloudExecutable) {
    $cmdLookup = Get-Command "gcloud.cmd" -ErrorAction SilentlyContinue
    if ($cmdLookup) {
        $gcloudExecutable = $cmdLookup.Source
    }
}

if (-not $gcloudExecutable) {
    Write-Host ""
    Write-Host "[ERROR] Google Cloud SDK ('gcloud.cmd') was not found on your system." -ForegroundColor Red
    Write-Host ""
    Write-Host "To install Google Cloud SDK on Windows, run this in PowerShell:" -ForegroundColor Yellow
    Write-Host "  winget install Google.CloudSDK" -ForegroundColor White
    Write-Host ""
    Write-Host "Or download the official Windows installer directly from:" -ForegroundColor Yellow
    Write-Host "  https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe" -ForegroundColor White
    Write-Host ""
    exit 1
}

Write-Host "[OK] Detected gcloud at: $gcloudExecutable" -ForegroundColor Green

# Helper function to invoke gcloud
function Invoke-GCloud {
    param([string[]]$Arguments)
    & $gcloudExecutable $Arguments
}

# 2. Check active Google Cloud authentication
$activeAccount = (& $gcloudExecutable config get-value account 2>$null)
if ([string]::IsNullOrWhiteSpace($activeAccount) -or $activeAccount -eq "(unset)") {
    Write-Host ""
    Write-Host "[!] No active Google Cloud login detected." -ForegroundColor Yellow
    Write-Host "Launching Google Cloud login in your browser..." -ForegroundColor Cyan
    & $gcloudExecutable auth login
    $activeAccount = (& $gcloudExecutable config get-value account 2>$null)
}
Write-Host "[OK] Authenticated Google Account: $activeAccount" -ForegroundColor Green

# 3. Check / Select GCP Project
if ([string]::IsNullOrWhiteSpace($ProjectId)) {
    $currentProject = (& $gcloudExecutable config get-value project 2>$null)
    if (-not [string]::IsNullOrWhiteSpace($currentProject) -and $currentProject -ne "(unset)") {
        $ProjectId = $currentProject
    } else {
        Write-Host ""
        $ProjectId = Read-Host "Enter your Google Cloud Project ID (e.g. fmm-archive-12345)"
    }
}

if ([string]::IsNullOrWhiteSpace($ProjectId) -or $ProjectId -eq "(unset)") {
    Write-Host "[ERROR] A valid Google Cloud Project ID is required to deploy." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[1/4] Setting active GCP project to: $ProjectId" -ForegroundColor Green
& $gcloudExecutable config set project $ProjectId

Write-Host ""
Write-Host "[2/4] Enabling required GCP APIs (Cloud Run, Cloud Build, Artifact Registry)..." -ForegroundColor Green
& $gcloudExecutable services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

Write-Host ""
Write-Host "[3/4] Building container and deploying to Google Cloud Run (Free Tier)..." -ForegroundColor Green
Write-Host "      - Region: $Region" -ForegroundColor Gray
Write-Host "      - Memory: 512Mi (Scale-to-zero for $0.00 idle cost)" -ForegroundColor Gray
Write-Host "      - Embedded DuckDB database initialized inside container" -ForegroundColor Gray

# Pass GEMINI_API_KEY if available in local environment
$runtimeEnvVars = "HOST=0.0.0.0"
if (-not [string]::IsNullOrWhiteSpace($env:GEMINI_API_KEY)) {
    $runtimeEnvVars += ",GEMINI_API_KEY=$($env:GEMINI_API_KEY)"
}

& $gcloudExecutable run deploy $ServiceName `
    --source . `
    --platform managed `
    --region $Region `
    --allow-unauthenticated `
    --memory 512Mi `
    --cpu 1 `
    --min-instances 0 `
    --max-instances 2 `
    --set-env-vars $runtimeEnvVars `
    --port 8000 `
    --quiet

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "[4/4] Fetching Live Production Cloud URL..." -ForegroundColor Green
    $serviceUrl = (& $gcloudExecutable run services describe $ServiceName --region $Region --format "value(status.url)")
    
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host "  SUCCESS! FMM ARCHIVE DEPLOYED TO GOOGLE CLOUD FREE TIER" -ForegroundColor Green
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host "  LIVE ARCHIVE URL : $serviceUrl" -ForegroundColor Yellow
    Write-Host "  SWAGGER API DOCS : $serviceUrl/docs" -ForegroundColor White
    Write-Host "  HEALTH CHECK     : $serviceUrl/api/health" -ForegroundColor White
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host "Next Step: Add '$serviceUrl' to your Google Cloud Console OAuth 2.0 Authorized Origins." -ForegroundColor Gray
} else {
    Write-Host ""
    Write-Host "[ERROR] Cloud Run deployment encountered an issue. Please review the output above." -ForegroundColor Red
}
