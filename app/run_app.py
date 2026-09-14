#!/usr/bin/env python3
"""
Five Metal Masonry (FMM) Iconography Archive
One-Click Application Launcher (run_app.py)

Launches the complete FastAPI + DuckDB backend and serves the frontend.
"""

import sys
import os
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure backend directory is in sys.path
APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import uvicorn
from database import init_duckdb_schema

def main():
    print("="*80)
    print("  FIVE METAL MASONRY (FMM) ICONOGRAPHY ARCHIVE")
    print("  FastAPI + DuckDB + Scholar Search & OCR Ingestion System")
    print("="*80)
    
    # Initialize DuckDB
    print("\n[1/2] Initializing DuckDB embedded database...")
    init_duckdb_schema()
    print("      [OK] DuckDB initialized with all 13 archive tables & seed data.")

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8000))

    # Start FastAPI server
    print(f"\n[2/2] Starting FastAPI server on http://{host}:{port} ...")
    print(f"      * Scholar Search: http://{host}:{port}/#search")
    print(f"      * Visual OCR Studio: http://{host}:{port}/#ocr_studio")
    print(f"      * DuckDB Table Studio: http://{host}:{port}/#admin_studio")
    print(f"      * Interactive Swagger API: http://{host}:{port}/docs")
    print("="*80)
    print("Press CTRL+C to stop the server.\n")

    uvicorn.run("main:app", host=host, port=port, reload=False, app_dir=str(BACKEND_DIR))

if __name__ == "__main__":
    main()
