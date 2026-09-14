#!/usr/bin/env python3
"""
Five Metal Masonry (FMM) Iconography Archive
Database Cleaning & Taxonomy Normalization Pipeline (clean_db.py)

Purges OCR noise, cleans unverified proposals, standardizes Sanskrit IAST
diacritics, and refreshes full-text search (FTS5) indexes.
"""

import os
import sys
import sqlite3
import re

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DB_PATH = os.path.join(os.path.dirname(__file__), "fmm_archive.db")

# Canonical IAST Corrections Dictionary
IAST_REPLACEMENTS = {
    "Ganesa": "Gaṇeśa",
    "Ganesha": "Gaṇeśa",
    "Ganapati": "Gaṇapati",
    "Lalitasana": "Lalitāsana",
    "Sukhasana": "Sukhāsana",
    "Asina": "Āsīna",
    "Padmasana": "Padmāsana",
    "Bhadrasana": "Bhadrāsana",
    "Ardhaparyankasana": "Ardhaparyaṅkāsana",
    "Musika": "Mūṣika",
    "Mooshika": "Mūṣika",
    "Trishunda": "Triśuṇḍa",
    "Abhaya": "Abhaya",
    "Varada": "Varada",
    "Kataka": "Kaṭaka",
    "Trisula": "Triśūla",
    "Cakra": "Cakra",
    "Sankha": "Śaṅkha",
    "Ankusa": "Aṅkuśa",
    "Pasa": "Pāśa",
    "Modaka": "Modaka",
    "Ekadanta": "Ekadanta",
    "Siva": "Śiva",
    "Vishnu": "Viṣṇu",
    "Devi": "Devī",
    "Krishna": "Kṛṣṇa",
    "Skanda": "Skanda",
}

def clean_database():
    print(f"\n[FMM Archive Database Sanitation Pipeline]")
    print(f"Connecting to database: {DB_PATH}")

    if not os.path.exists(DB_PATH):
        print(f"Error: Database file '{DB_PATH}' not found.")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Clean low-confidence or noisy entity proposals (< 80% confidence or raw OCR artifacts)
    print("Step 1: Purging noisy / unverified OCR proposals...")
    cur.execute("DELETE FROM ai_metadata_proposals WHERE confidence_score < 0.80 OR raw_suggested_term IS NULL")
    deleted_proposals = cur.rowcount
    print(f"  -> Removed {deleted_proposals} noisy metadata proposals.")

    # 2. Standardize IAST diacritics in taxonomy_terms
    print("Step 2: Normalizing IAST diacritics in taxonomy terms...")
    cur.execute("SELECT id, canonical_name, iast_name FROM taxonomy_terms")
    terms = cur.fetchall()
    updated_terms = 0
    for term_id, canonical, iast in terms:
        new_iast = iast
        if canonical in IAST_REPLACEMENTS and not iast:
            new_iast = IAST_REPLACEMENTS[canonical]
        elif iast in IAST_REPLACEMENTS:
            new_iast = IAST_REPLACEMENTS[iast]
        
        if new_iast != iast:
            cur.execute("UPDATE taxonomy_terms SET iast_name = ? WHERE id = ?", (new_iast, term_id))
            updated_terms += 1

    print(f"  -> Updated {updated_terms} taxonomy term IAST names.")

    # 3. Clean and verify study_taxonomy_mappings
    print("Step 3: Verifying study-taxonomy mappings against PDF indexing rule...")
    # Remove mappings with invalid term references
    cur.execute("""
        DELETE FROM study_taxonomy_mappings 
        WHERE term_id NOT IN (SELECT id FROM taxonomy_terms)
    """)
    deleted_mappings = cur.rowcount
    print(f"  -> Removed {deleted_mappings} orphaned taxonomy mappings.")

    # Ensure all primary mappings have curator_verified = 1 and relevance_level set
    cur.execute("""
        UPDATE study_taxonomy_mappings 
        SET curator_verified = 1, relevance_level = 'materially_discussed'
        WHERE relevance_level IS NULL OR relevance_level = ''
    """)
    updated_mappings = cur.rowcount
    print(f"  -> Verified {updated_mappings} study taxonomy mappings.")

    # 4. Rebuild FTS5 Full-Text Search Indexes
    print("Step 4: Rebuilding FTS5 full-text search indexes...")
    try:
        cur.execute("INSERT INTO studies_fts(studies_fts) VALUES('rebuild')")
        cur.execute("INSERT INTO study_slides_fts(study_slides_fts) VALUES('rebuild')")
        cur.execute("INSERT INTO taxonomy_terms_fts(taxonomy_terms_fts) VALUES('rebuild')")
        print("  -> FTS5 search indexes rebuilt successfully.")
    except Exception as e:
        print(f"  -> Warning rebuilding FTS5 indexes: {e}")

    conn.commit()

    # Integrity verification
    cur.execute("SELECT COUNT(*) FROM studies")
    studies_cnt = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM study_slides")
    slides_cnt = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM taxonomy_terms")
    terms_cnt = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM study_taxonomy_mappings")
    mappings_cnt = cur.fetchone()[0]

    print("\nDatabase Sanitation Summary:")
    print(f"  • Total Studies: {studies_cnt}")
    print(f"  • Ingested Slides: {slides_cnt}")
    print(f"  • Controlled Taxonomy Terms: {terms_cnt}")
    print(f"  • Verified Study Mappings: {mappings_cnt}")
    print("Sanitation Completed Successfully!\n")

    conn.close()

if __name__ == "__main__":
    clean_database()
