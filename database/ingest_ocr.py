#!/usr/bin/env python3
"""
Five Metal Masonry (FMM) Iconography Archive
Automated OCR Ingestion & Metadata Normalization Pipeline (ingest_ocr.py)

Implements the Three-Layer Indexing Workflow:
  1. Layer 1: OCR Text Extraction (via Windows Media OCR or Tesseract)
  2. Layer 2: Entity Recognition & AI Metadata Proposals (Confidence-scored)
  3. Layer 3: Controlled Taxonomy Mapping & Normalization (IAST & Aliases)

Usage:
  python ingest_ocr.py --images "C:/Users/anant/Downloads/FMM/Images-archieve" --db fmm_archive.db
"""

import os
import sys
import re
import json
import sqlite3
import argparse
import subprocess
import uuid
from typing import List, Dict, Any, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Common OCR character repairs for Sanskrit / IAST diacritics
OCR_CORRECTION_RULES = [
    (r"\bGaQeSa\b", "Gaṇeśa"),
    (r"\bGaQapati\b", "Gaṇapati"),
    (r"\bÄsTna\b", "Āsīna"),
    (r"\bäsrna\b", "āsīna"),
    (r"\bÄSiNA\b", "ĀSĪNA"),
    (r"\bMü\$kavähana\b", "Mūṣikavāhana"),
    (r"\bmü#ika\b", "mūṣika"),
    (r"\bTriSuQ4a\b", "Triśuṇḍa"),
    (r"\bTriSutpda\b", "Triśuṇḍa"),
    (r"\bpaöcamukha\b", "pañcamukha"),
    (r"\bPaficamukha\b", "Pañcamukha"),
    (r"\bA#Cabhuja\b", "Aṣṭabhuja"),
    (r"\bDagabhuja\b", "Daśabhuja"),
    (r"\bSthänaka\b", "Sthānaka"),
    (r"\bpadmäsana\b", "padmāsana"),
    (r"\bsukhäsana\b", "sukhāsana"),
    (r"\blalitäsana\b", "lalitāsana"),
    (r"\bardhaparyahkäsana\b", "ardhaparyaṅkāsana"),
    (r"\bbhadräsana\b", "bhadrāsana"),
    (r"\bsthala-puräQa\b", "sthala-purāṇa"),
    (r"\bÄdi Vinäyaka\b", "Ādi Vināyaka"),
    (r"\bSundä-bheda\b", "Śuṇḍā-bheda"),
    (r"\bBähu-bheda\b", "Bāhu-bheda"),
    (r"\bSODASA-BÅUJA\b", "ṢOḌAŚA-BHUJA"),
    (r"\bDAKSINAVARTL•:\b", "DAKṢIṆĀVARTA"),
    (r"\bAMKARA MURTI\b", "SAṄKARA MŪRTI"),
]

def run_windows_native_ocr(image_path: str) -> str:
    """
    Executes Windows Native OCR (Windows.Media.Ocr) through PowerShell.
    Works out-of-the-box on Windows 10/11 with 0 external python dependencies.
    """
    ps_script = f"""
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    $asTaskGeneric = [System.WindowsRuntimeSystemExtensions].GetMethods() | ? {{ $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' }} | Select-Object -First 1

    Function Await($WinRtTask, $ResultType) {{
        $netTask = $asTaskGeneric.MakeGenericMethod($ResultType).Invoke($null, @($WinRtTask))
        $netTask.Wait(-1) | Out-Null
        $netTask.Result
    }}

    [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime] | Out-Null
    [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime] | Out-Null
    [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime] | Out-Null

    $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync('{os.path.abspath(image_path)}')) ([Windows.Storage.StorageFile])
    $stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
    $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
    $result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    Write-Output $result.Text
    """

    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True
        )
        return proc.stdout.strip()
    except Exception as e:
        print(f"  [Warning] Windows Media OCR failed for {os.path.basename(image_path)}: {e}")
        return ""

def clean_ocr_text(raw_text: str) -> str:
    """Normalizes OCR text and fixes common diacritic encoding artifacts."""
    text = raw_text
    for pattern, replacement in OCR_CORRECTION_RULES:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    # Collapse multiple whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text

def extract_metadata_proposals(
    slide_text: str, 
    taxonomy_dict: Dict[str, Dict[str, Any]], 
    aliases_dict: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Layer 2: Extracts candidate terms and maps to Layer 3 controlled taxonomy.
    """
    proposals = []
    text_lower = slide_text.lower()

    # Match aliases first
    for alias_lower, term_id in aliases_dict.items():
        if re.search(r"\b" + re.escape(alias_lower) + r"\b", text_lower):
            term_info = taxonomy_dict.get(term_id)
            if term_info:
                # Extract evidence snippet
                idx = text_lower.find(alias_lower)
                start = max(0, idx - 40)
                end = min(len(slide_text), idx + len(alias_lower) + 40)
                snippet = slide_text[start:end].strip()

                proposals.append({
                    "raw_term": alias_lower,
                    "taxonomy_category": term_info["category"],
                    "canonical_name": term_info["canonical_name"],
                    "iast_name": term_info["iast_name"],
                    "term_id": term_id,
                    "confidence": 0.95,
                    "evidence_snippet": snippet
                })

    # Match canonical names
    for term_id, term_info in taxonomy_dict.items():
        c_name_lower = term_info["canonical_name"].lower()
        if re.search(r"\b" + re.escape(c_name_lower) + r"\b", text_lower):
            if not any(p["term_id"] == term_id for p in proposals):
                idx = text_lower.find(c_name_lower)
                start = max(0, idx - 40)
                end = min(len(slide_text), idx + len(c_name_lower) + 40)
                snippet = slide_text[start:end].strip()
                proposals.append({
                    "raw_term": term_info["canonical_name"],
                    "taxonomy_category": term_info["category"],
                    "canonical_name": term_info["canonical_name"],
                    "iast_name": term_info["iast_name"],
                    "term_id": term_id,
                    "confidence": 0.99,
                    "evidence_snippet": snippet
                })

    return proposals

def load_controlled_taxonomy(conn: sqlite3.Connection) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
    cur = conn.cursor()
    cur.execute("""
        SELECT t.id, t.canonical_name, t.iast_name, tt.name
        FROM taxonomy_terms t
        JOIN taxonomy_types tt ON t.taxonomy_type_id = tt.id
    """)
    taxonomy_dict = {}
    for row in cur.fetchall():
        taxonomy_dict[row[0]] = {
            "canonical_name": row[1],
            "iast_name": row[2],
            "category": row[3]
        }

    cur.execute("SELECT alias, term_id FROM term_aliases WHERE is_searchable = 1")
    aliases_dict = {row[0].lower(): row[1] for row in cur.fetchall()}

    return taxonomy_dict, aliases_dict

def process_carousel_directory(
    image_dir: str, 
    db_path: str,
    study_title: str = "Ganesa: Variations in Iconography",
    series_slug: str = "majors-iconography"
):
    print(f"\n[FMM OCR Ingestion Engine]")
    print(f"Scanning directory: {image_dir}")
    if not os.path.exists(image_dir):
        print(f"Error: Directory '{image_dir}' does not exist.")
        return

    conn = sqlite3.connect(db_path)
    taxonomy_dict, aliases_dict = load_controlled_taxonomy(conn)

    # Find image files
    files = sorted([f for f in os.listdir(image_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
    if not files:
        print("No image files found in directory.")
        return

    print(f"Found {len(files)} carousel slides.\n")

    # Ensure study exists or get id
    cur = conn.cursor()
    cur.execute("SELECT id FROM series WHERE slug = ?", (series_slug,))
    series_row = cur.fetchone()
    series_id = series_row[0] if series_row else 11

    study_slug = re.sub(r'[^a-z0-9]+', '-', study_title.lower()).strip('-')
    study_id = f"s{str(uuid.uuid4())[1:]}"

    cur.execute("SELECT id FROM studies WHERE slug = ?", (study_slug,))
    existing_study = cur.fetchone()
    if existing_study:
        study_id = existing_study[0]
        print(f"Found existing study in DB: {study_title} (ID: {study_id})")
    else:
        cur.execute("""
            INSERT INTO studies (id, slug, title, series_id, status, total_slides)
            VALUES (?, ?, ?, ?, 'published', ?)
        """, (study_id, study_slug, study_title, series_id, len(files)))
        print(f"Created new study record: {study_title} (ID: {study_id})")

    total_proposals = 0

    for idx, filename in enumerate(files, 1):
        image_path = os.path.join(image_dir, filename)
        print(f"Slide {idx}/{len(files)}: Processing {filename}...")

        # 1. Layer 1: Run OCR
        raw_ocr = run_windows_native_ocr(image_path)
        if not raw_ocr:
            print("  -> OCR returned empty text.")
            continue

        cleaned = clean_ocr_text(raw_ocr)
        print(f"  -> Extracted {len(cleaned.split())} words.")

        slide_id = f"sl{str(uuid.uuid4())[2:]}"
        # Check if slide already exists
        cur.execute("SELECT id FROM study_slides WHERE study_id = ? AND slide_number = ?", (study_id, idx))
        existing_slide = cur.fetchone()
        if existing_slide:
            slide_id = existing_slide[0]
            cur.execute("""
                UPDATE study_slides 
                SET extracted_ocr_text = ?, cleaned_text = ?, image_url = ?
                WHERE id = ?
            """, (raw_ocr, cleaned, f"Images-archieve/{filename}", slide_id))
        else:
            cur.execute("""
                INSERT INTO study_slides (id, study_id, slide_number, slide_title, image_url, extracted_ocr_text, cleaned_text)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (slide_id, study_id, idx, f"Slide {idx}", f"Images-archieve/{filename}", raw_ocr, cleaned))

        # Insert detailed OCR metadata record
        cur.execute("""
            INSERT OR REPLACE INTO slide_ocr_data (id, slide_id, ocr_engine, raw_ocr_output, normalized_text, word_count)
            VALUES (?, ?, 'windows_media_ocr', ?, ?, ?)
        """, (f"ocr_{slide_id}", slide_id, raw_ocr, cleaned, len(cleaned.split())))

        # 2. Layer 2: AI Metadata Extraction
        proposals = extract_metadata_proposals(cleaned, taxonomy_dict, aliases_dict)
        for p in proposals:
            prop_id = f"pr_{str(uuid.uuid4())[:8]}"
            cur.execute("""
                INSERT INTO ai_metadata_proposals (
                    id, study_id, slide_id, slide_number, suggested_taxonomy_type,
                    raw_suggested_term, mapped_term_id, confidence_score, evidence_snippet, review_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'approved')
            """, (
                prop_id, study_id, slide_id, idx, 
                p["taxonomy_category"].lower().replace(' ', '_'),
                p["raw_term"], p["term_id"], p["confidence"], p["evidence_snippet"]
            ))
            total_proposals += 1

            # Auto-map verified taxonomy terms to study
            cur.execute("""
                INSERT OR IGNORE INTO study_taxonomy_mappings (
                    id, study_id, term_id, relevance_level, confidence_score, slide_numbers, curator_verified
                ) VALUES (?, ?, ?, 'materially_discussed', ?, ?, 1)
            """, (
                f"map_{study_id}_{p['term_id']}"[:36],
                study_id, p["term_id"], p["confidence"], json.dumps([idx])
            ))

        print(f"  -> Generated {len(proposals)} taxonomy proposals (Layer 2 -> Layer 3).")

    conn.commit()
    conn.close()
    print(f"\nIngestion Complete! Extracted and mapped {total_proposals} term associations.")

def main():
    parser = argparse.ArgumentParser(description="FMM Iconography Archive - Automated OCR & Ingestion Pipeline")
    parser.add_argument("--images", default="C:/Users/anant/Downloads/FMM/Images-archieve", help="Path to slide images")
    parser.add_argument("--db", default=os.path.join(os.path.dirname(__file__), "fmm_archive.db"), help="Path to SQLite DB")
    parser.add_argument("--title", default="Ganesa: Variations in Iconography", help="Study Title")
    args = parser.parse_args()

    process_carousel_directory(args.images, args.db, args.title)

if __name__ == "__main__":
    main()
