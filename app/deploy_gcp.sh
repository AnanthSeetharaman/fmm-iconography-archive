#!/usr/bin/env bash
# ==============================================================================
# Five Metal Masonry (FMM) Iconography Archive
# 1-Click Automated Deployment Script for Google Cloud Run (Free Tier)
# ==============================================================================
set -e

PROJECT_ID=${1:-$(gcloud config get-value project 2>/dev/null)}
REGION="us-central1"
SERVICE_NAME="fmm-iconography-archive"

echo "================================================================================"
echo "  FIVE METAL MASONRY — GOOGLE CLOUD RUN AUTOMATED DEPLOYMENT"
echo "================================================================================"

if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" = "(unset)" ]; then
    read -p "Enter your Google Cloud Project ID (e.g. fmm-archive-12345): " PROJECT_ID
fi

if [ -z "$PROJECT_ID" ]; then
    echo "[ERROR] Project ID is required."
    exit 1
fi

echo "[1/4] Setting active GCP project to: $PROJECT_ID"
gcloud config set project "$PROJECT_ID"

echo "[2/4] Enabling required APIs..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

echo "[3/4] Building and deploying to Google Cloud Run (Free Tier)..."
gcloud run deploy "$SERVICE_NAME" \
    --source . \
    --platform managed \
    --region "$REGION" \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 2 \
    --set-env-vars HOST=0.0.0.0,PORT=8080

echo "[4/4] Fetching Live Production Cloud URL..."
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format "value(status.url)")

echo "================================================================================"
echo "  SUCCESS! FMM ARCHIVE DEPLOYED TO GOOGLE CLOUD FREE TIER"
echo "================================================================================"
echo "  LIVE ARCHIVE URL : $SERVICE_URL"
echo "  SWAGGER API DOCS : $SERVICE_URL/docs"
echo "  HEALTH CHECK     : $SERVICE_URL/api/health"
echo "================================================================================"
