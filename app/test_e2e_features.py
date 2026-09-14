import requests
import json
import duckdb
from pathlib import Path

BASE_URL = "http://localhost:8000"

def test_e2e():
    print("=== STEP 1: GET /api/ocr/context ===")
    r = requests.get(f"{BASE_URL}/api/ocr/context")
    assert r.status_code == 200, f"Context failed: {r.text}"
    context = r.json()
    print(f"Studies count: {len(context['studies'])}")
    print(f"Series count: {len(context['series'])}")
    print(f"Categories count: {len(context['categories'])}")
    assert len(context["series"]) >= 19, "Expected canonical series to be loaded"

    print("\n=== STEP 2: POST /api/ocr/series/create ===")
    series_payload = {
        "title": "Sacred Hastas and Mudras",
        "description": "Comprehensive taxonomic canon of classical Vedic and Agamic mudras."
    }
    r = requests.post(f"{BASE_URL}/api/ocr/series/create", json=series_payload)
    assert r.status_code == 200, f"Series creation failed: {r.text}"
    new_series = r.json()
    series_id = new_series["id"]
    print(f"Created series: ID={series_id}, Title='{new_series['title']}'")

    print("\n=== STEP 3: POST /api/ocr/studies/create ===")
    study_payload = {
        "title": "Chola Mudra Lexicon",
        "subtitle": "Analysis of Chin Mudra and Tarjani Mudra in Chola Bronzes",
        "series_id": series_id,
        "access_tier": "PUBLIC"
    }
    r = requests.post(f"{BASE_URL}/api/ocr/studies/create", json=study_payload)
    assert r.status_code == 200, f"Study creation failed: {r.text}"
    new_study = r.json()
    study_id = new_study["id"]
    study_slug = new_study["slug"]
    print(f"Created study: ID='{study_id}', Slug='{study_slug}', Title='{new_study['title']}'")

    print("\n=== STEP 4: POST /api/ocr/approve (Commit Plate with Edited Proposals) ===")
    # Simulate an approved slide with multiple curator-edited proposals
    approve_payload = {
        "study_id": study_id,
        "study_slug": study_slug,
        "source_filename": "test_e2e_mudra.jfif",
        "image_url": f"/storage/images/{study_slug}/test_e2e_mudra.jfif",
        "cleaned_ocr": "TARJANI MUDRA - FOREFINGER POINTING UPWARDS THREATENING DEMONS",
        "raw_ocr": "TARJANI MUDRA - FOREFINGER POINTING UPWARDS",
        "proposals": [
            {
                "canonical_name": "Tarjani Mudra",
                "iast_name": "tarjanī-mudrā",
                "category": "Mudra",
                "confidence": 0.98,
                "evidence_snippet": "Forefinger pointing upwards in threatening gesture"
            },
            {
                "canonical_name": "Chin Mudra",
                "iast_name": "cin-mudrā",
                "category": "Mudra",
                "confidence": 0.95,
                "evidence_snippet": "Thumb and index finger touching forming a circle of consciousness"
            },
            {
                "canonical_name": "Kashyapa Shilpa Shastra",
                "iast_name": "kāśyapa-śilpa-śāstra",
                "category": "Source / Reference",
                "confidence": 0.92,
                "evidence_snippet": "Canonic proportion rules cited in slide header"
            }
        ]
    }
    r = requests.post(f"{BASE_URL}/api/ocr/approve", json=approve_payload)
    assert r.status_code == 200, f"Approval failed: {r.text}"
    approval_result = r.json()
    print("Approval response:", json.dumps(approval_result, indent=2))
    slide_id = approval_result["slide_id"]
    slide_number = approval_result["slide_number"]
    assert slide_number == 1, f"Expected first slide in new study to be 1, got {slide_number}"

    print("\n=== STEP 5: DUCKDB FOREIGN KEY & DATA INTEGRITY VERIFICATION ===")
    db_path = Path(r"c:\Users\anant\Downloads\FMM\database\fmm_master.duckdb")
    con = duckdb.connect(str(db_path), read_only=True)

    # 1. Verify series exists
    series_row = con.execute("SELECT id, title, slug FROM series WHERE id = ?", [series_id]).fetchone()
    print(f"Verified Series in DB: {series_row}")
    assert series_row is not None

    # 2. Verify study exists and points to series_id
    study_row = con.execute("SELECT id, title, series_id FROM studies WHERE id = ?", [study_id]).fetchone()
    print(f"Verified Study in DB: {study_row}")
    assert study_row is not None
    assert study_row[2] == series_id, f"FK mismatch: study series_id {study_row[2]} != {series_id}"

    # 3. Verify study_slides
    slide_row = con.execute("SELECT id, study_id, slide_number, image_path FROM study_slides WHERE id = ?", [slide_id]).fetchone()
    print(f"Verified Slide in DB: {slide_row}")
    assert slide_row is not None
    assert slide_row[1] == study_id

    # 4. Verify slide_ocr_data
    ocr_row = con.execute("SELECT slide_id, word_count, cleaned_text FROM slide_ocr_data WHERE slide_id = ?", [slide_id]).fetchone()
    print(f"Verified OCR Data in DB: {ocr_row}")
    assert ocr_row is not None

    # 5. Verify ai_metadata_proposals
    proposals_rows = con.execute("SELECT proposed_term, proposed_category, confidence_score, status FROM ai_metadata_proposals WHERE slide_id = ?", [slide_id]).fetchall()
    print(f"Verified Proposals in DB ({len(proposals_rows)}): {proposals_rows}")
    assert len(proposals_rows) == 3

    # 6. Verify study_taxonomy_mappings
    mappings = con.execute("""
        SELECT m.study_id, t.canonical_name, t.iast_name, ty.name 
        FROM study_taxonomy_mappings m
        JOIN taxonomy_terms t ON m.taxonomy_term_id = t.id
        JOIN taxonomy_types ty ON t.taxonomy_type_id = ty.id
        WHERE m.study_id = ?
    """, [study_id]).fetchall()
    print(f"Verified Taxonomy Mappings ({len(mappings)}): {mappings}")
    assert len(mappings) == 3

    con.close()
    print("\n>>> ALL TESTS PASSED SUCCESSFULLY! ALL FOREIGN KEYS VERIFIED AND SATISFIED! <<<")

if __name__ == "__main__":
    test_e2e()
