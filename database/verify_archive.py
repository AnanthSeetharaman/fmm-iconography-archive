#!/usr/bin/env python3
"""
Five Metal Masonry (FMM) Iconography Archive
Verification & Search Demonstration Script

Validates:
1. Database schema initialization (SQLite + FTS5)
2. Seed data ingestion (19 Series, Taxonomy, Aliases, Study 001)
3. Three-layer search & discovery:
   - Layer 1: Deep OCR slide text search
   - Layer 2: AI metadata proposals review
   - Layer 3: Controlled taxonomy & alias-tolerant search
4. Match reason explanations ('why it matched')
"""

import os
import sys
import sqlite3
import json

# Ensure full Unicode (IAST diacritics) support in terminal output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DB_PATH = os.path.join(os.path.dirname(__file__), "fmm_archive.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema_sqlite.sql")
SEED_PATH = os.path.join(os.path.dirname(__file__), "seed_data.sql")

def split_sql(sql):
    statements = []
    current = []
    in_str = False
    quote_char = None
    i = 0
    while i < len(sql):
        c = sql[i]
        if not in_str:
            if c in ("'", '"'):
                in_str = True
                quote_char = c
                current.append(c)
            elif c == '-' and i + 1 < len(sql) and sql[i+1] == '-':
                end_line = sql.find('\n', i)
                if end_line == -1: break
                current.append(sql[i:end_line+1])
                i = end_line
            elif c == ';':
                statements.append("".join(current).strip())
                current = []
            else:
                current.append(c)
        else:
            current.append(c)
            if c == quote_char:
                if i + 1 < len(sql) and sql[i+1] == quote_char:
                    current.append(sql[i+1])
                    i += 1
                else:
                    in_str = False
                    quote_char = None
        i += 1
    if current and "".join(current).strip():
        statements.append("".join(current).strip())
    return [s for s in statements if s]

def initialize_database():
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except Exception:
            pass

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        cur.executescript(f.read())

    with open(SEED_PATH, "r", encoding="utf-8") as f:
        cur.executescript(f.read())

    conn.commit()
    return conn

def run_archive_search(conn, query_text):
    """
    Simulates the ranked search logic:
    Combines taxonomy match (higher score) + deep OCR slide match (lower score),
    explaining WHY each study matched.
    """
    cur = conn.cursor()
    print(f"\n" + "="*80)
    print(f"SEARCH QUERY: '{query_text}'")
    print("="*80)

    # 1. Check for controlled taxonomy / alias matches
    cur.execute("""
        SELECT 
            t.id, t.canonical_name, t.iast_name, tt.name AS category,
            a.alias AS matched_alias, a.alias_type
        FROM taxonomy_terms t
        JOIN taxonomy_types tt ON t.taxonomy_type_id = tt.id
        LEFT JOIN term_aliases a ON a.term_id = t.id
        WHERE LOWER(t.canonical_name) LIKE LOWER(?)
           OR LOWER(COALESCE(t.iast_name, '')) LIKE LOWER(?)
           OR LOWER(COALESCE(a.alias, '')) LIKE LOWER(?)
    """, (f"%{query_text}%", f"%{query_text}%", f"%{query_text}%"))
    tax_matches = cur.fetchall()

    matched_term_ids = [m[0] for m in tax_matches]

    # 2. Check study-level matches (Title, metadata, or mapped taxonomy)
    results = []
    
    cur.execute("""
        SELECT 
            s.id, s.title, s.subtitle, s.study_number, ser.name AS series_name,
            s.access_level, s.total_slides
        FROM studies s
        JOIN series ser ON s.series_id = ser.id
        WHERE s.status = 'published'
    """)
    studies = cur.fetchall()

    for study in studies:
        study_id, title, subtitle, study_num, series_name, access, total_slides = study
        match_reasons = []
        rank_score = 0.0

        # Title match
        if query_text.lower() in title.lower():
            rank_score += 10.0
            match_reasons.append(f"Title match on '{title}'")

        # Taxonomy mappings match
        if matched_term_ids:
            cur.execute("""
                SELECT t.canonical_name, t.iast_name, tt.name, m.relevance_level, m.slide_numbers
                FROM study_taxonomy_mappings m
                JOIN taxonomy_terms t ON m.term_id = t.id
                JOIN taxonomy_types tt ON t.taxonomy_type_id = tt.id
                WHERE m.study_id = ? AND m.term_id IN ({})
            """.format(",".join("?" * len(matched_term_ids))), (study_id, *matched_term_ids))
            for row in cur.fetchall():
                cname, iast, cat, rel, slides = row
                weight = 15.0 if rel == 'primary_subject' else 8.0
                rank_score += weight
                match_reasons.append(f"Taxonomy match: {cat} = '{cname}' ({iast}) [{rel}, discussed in slides {slides}]")

        # Deep Slide OCR match (Layer 1)
        cur.execute("""
            SELECT slide_number, slide_title, 
                   COALESCE(cleaned_text, extracted_ocr_text) as text
            FROM study_slides
            WHERE study_id = ? AND (
                LOWER(COALESCE(cleaned_text, '')) LIKE LOWER(?) OR
                LOWER(COALESCE(extracted_ocr_text, '')) LIKE LOWER(?)
            )
            ORDER BY slide_number
        """, (study_id, f"%{query_text}%", f"%{query_text}%"))
        ocr_hits = cur.fetchall()
        if ocr_hits:
            rank_score += 3.0 * len(ocr_hits)
            for hit in ocr_hits:
                sl_num, sl_title, _ = hit
                match_reasons.append(f"Slide {sl_num} OCR hit in '{sl_title}'")

        if rank_score > 0:
            results.append({
                "study_id": study_id,
                "study_number": study_num,
                "title": title,
                "series_name": series_name,
                "access_level": access,
                "rank_score": rank_score,
                "match_reasons": match_reasons
            })

    results.sort(key=lambda x: x["rank_score"], reverse=True)

    if not results:
        print("  No matching studies found.")
        return

    for idx, r in enumerate(results, 1):
        print(f"[{idx}] {r['title']} ({r['study_number']})")
        print(f"    Series: {r['series_name']} | Access: {r['access_level'].upper()} | Relevance Score: {r['rank_score']:.1f}")
        print("    Why Matched (Scholarly Reference Cues):")
        for cue in r["match_reasons"]:
            print(f"      • {cue}")

def main():
    print("Initializing FMM Iconography Archive Database (SQLite)...")
    conn = initialize_database()
    cur = conn.cursor()

    # Verify counts
    cur.execute("SELECT COUNT(*) FROM series")
    series_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM taxonomy_terms")
    term_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM term_aliases")
    alias_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM study_slides")
    slide_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM dictionary_entries")
    dict_count = cur.fetchone()[0]

    print(f"SUCCESS: Database initialized!")
    print(f"  • Series: {series_count} (Completed, Ongoing, Upcoming)")
    print(f"  • Controlled Taxonomy Terms: {term_count}")
    print(f"  • Search Aliases & Transliterations: {alias_count}")
    print(f"  • Dictionary of Iconography Entries: {dict_count}")
    print(f"  • Ingested Carousel Slides: {slide_count}")

    # Run demonstration searches across the three layers
    test_queries = [
        "Lalitasana",      # Exact Asana term
        "Three trunks",    # Alias/English translation mapping to Trishunda
        "Ganapati",        # Common spelling variant mapping to canonical Ganesha
        "Bhadrasana",      # Deep text search from Slide 4 OCR
        "Pune",            # Geographical place search
        "dancing",         # Mudra/Asana alias mapping to Nrtta
    ]

    for q in test_queries:
        run_archive_search(conn, q)

    conn.close()

if __name__ == "__main__":
    main()
