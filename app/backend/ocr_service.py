from embedding_service import text_to_dense_vector
import os
import sys
import re
import json
import uuid
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from database import get_db
from config import (
    IMAGES_STORAGE_DIR,
    LLM_MODEL,
    LLM_LODEL,
    PROMPT_OCR,
    PROMPT_ICONOGRAPHY_VALIDATION,
    PROMPT_VALIDATION,
)

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

def get_gemini_api_key() -> str:
    """
    Retrieves the Google Gemini Vision API key with hierarchical resolution:
    1. Database param_config table (param_key = 'gemini_api_key')
    2. Environment variable (GEMINI_API_KEY)
    """
    try:
        conn = get_db()
        row = conn.execute(
            "SELECT param_value FROM param_config WHERE param_key = 'gemini_api_key' AND param_value IS NOT NULL AND TRIM(param_value) != ''"
        ).fetchone()
        conn.close()
        if row and row[0] and row[0].strip():
            return row[0].strip()
    except Exception as e:
        pass

    return os.environ.get("GEMINI_API_KEY", "").strip()


def validate_iconography_image(image_path: str) -> Tuple[bool, str]:
    """
    Validates with Google Gemini Vision whether the uploaded image belongs to the domain
    of sacred iconography, Shilpa Shastra, Hindu/Buddhist/Jain sculptures, sacred bronzes (Panchaloha),
    temple architecture, mudras, asanas, or epigraphic study plates.
    Rejects unrelated images (such as selfies, personal portraits, domestic animals, receipts, vehicles, everyday objects).
    Returns (is_valid: bool, reason: str).
    """
    api_key = get_gemini_api_key()
    if not api_key:
        print("Gemini Iconography Validation: GEMINI_API_KEY not found; skipping image domain verification.")
        return True, "Domain validation bypassed (offline/no API key configured)."

    try:
        from google import genai
        from PIL import Image

        client = genai.Client(api_key=api_key)
        img = Image.open(image_path)

        response = client.models.generate_content(
            model=LLM_MODEL,
            contents=[img, PROMPT_ICONOGRAPHY_VALIDATION]
        )

        resp_text = (response.text or "").strip()
        if not resp_text:
            return True, "Empty validation response received from Gemini."

        # Strip optional markdown code fences
        cleaned_json = re.sub(r"^```(?:json)?\s*", "", resp_text, flags=re.IGNORECASE)
        cleaned_json = re.sub(r"\s*```$", "", cleaned_json).strip()

        try:
            data = json.loads(cleaned_json)
            is_valid = bool(data.get("is_valid", False))
            reason = data.get("reason", "Validation check completed.")
            return is_valid, reason
        except Exception:
            # Fallback regex extraction if JSON is wrapped in commentary
            m = re.search(r'"is_valid"\s*:\s*(true|false)', cleaned_json, re.IGNORECASE)
            r_m = re.search(r'"reason"\s*:\s*"([^"]+)"', cleaned_json, re.IGNORECASE)
            reason = r_m.group(1) if r_m else resp_text
            if m:
                is_valid = m.group(1).lower() == "true"
                return is_valid, reason

            if "false" in resp_text.lower() and ("reject" in resp_text.lower() or "not related" in resp_text.lower() or "invalid" in resp_text.lower()):
                return False, resp_text

            return True, reason
    except Exception as e:
        print(f"Gemini Iconography Validation error: {e}")
        return True, f"Validation warning: {e}"


def run_gemini_vision_ocr(image_path: str) -> str:
    """
    Executes Google Gemini Vision OCR using the configured LLM_MODEL with specialized Shilpa Shastra prompt.
    Preserves Sanskrit IAST transliterations, canonical titles, and iconometric descriptions.
    """
    try:
        api_key = get_gemini_api_key()
        if not api_key:
            print("Gemini Vision: GEMINI_API_KEY not found in param_config or environment")
            return ""
        
        from google import genai
        from PIL import Image
        
        client = genai.Client(api_key=api_key)
        img = Image.open(image_path)
        
        response = client.models.generate_content(
            model=LLM_MODEL,
            contents=[img, PROMPT_OCR]
        )
        if response and response.text:
            return response.text.strip()
        return ""
    except Exception as e:
        print(f"Gemini Vision OCR error: {e}")
        return ""

def run_gcp_vision_ocr(image_path: str) -> str:
    """
    Executes Google Cloud Vision Document Text Detection (99.5%+ scholar-grade OCR).
    Automatically uses GCP Cloud Run Service Account credentials.
    """
    try:
        from google.cloud import vision
        client = vision.ImageAnnotatorClient()

        with open(image_path, "rb") as image_file:
            content = image_file.read()

        image = vision.Image(content=content)
        response = client.document_text_detection(image=image)

        if response.error.message:
            print(f"GCP Vision OCR warning: {response.error.message}")
            return ""

        return response.full_text_annotation.text or ""
    except Exception as e:
        print(f"GCP Vision API not initialized: {e}")
        return ""

def run_windows_native_ocr(image_path: str) -> str:
    """
    Executes Windows Native OCR (Windows.Media.Ocr) through PowerShell.
    Works out-of-the-box on Windows 10/11 with 0 external dependencies.
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
        print(f"Windows OCR warning: {e}")
        return ""

def perform_ocr(image_path: str, engine: str = "gemini_vision") -> Tuple[str, str, str]:
    """
    Dual-Engine Scholar OCR Dispatcher:
    1. 'gemini_vision' (Default): Uses Google Gemini Flash Vision Model (configured via LLM_MODEL)
       for scholar-grade accuracy & IAST.
       Falls back to Google Cloud Vision or Windows Native OCR if offline or API key missing.
    2. 'windows_native': Uses local Windows.Media.Ocr subsystem (offline).
    Returns: (raw_ocr_text, cleaned_ocr_text, engine_name_used)
    """
    engine_used = engine
    raw_ocr = ""

    if engine == "gemini_vision":
        raw_ocr = run_gemini_vision_ocr(image_path)
        if raw_ocr:
            engine_used = LLM_MODEL
        else:
            print("Gemini Vision returned empty or failed, attempting fallbacks...")
            # Fallback 1: GCP Cloud Vision (ideal for GCP Cloud Run / Linux runtime)
            raw_ocr = run_gcp_vision_ocr(image_path)
            if raw_ocr:
                engine_used = "google_cloud_vision (fallback)"
            else:
                # Fallback 2: Windows Native OCR (offline Windows runtime)
                raw_ocr = run_windows_native_ocr(image_path)
                engine_used = "windows_media_ocr (fallback)"
    elif engine == "windows_native":
        raw_ocr = run_windows_native_ocr(image_path)
        engine_used = "windows_media_ocr"
    else:
        raw_ocr = run_gemini_vision_ocr(image_path)
        if not raw_ocr:
            raw_ocr = run_gcp_vision_ocr(image_path) or run_windows_native_ocr(image_path)
        engine_used = LLM_MODEL

    cleaned = clean_ocr_text(raw_ocr) if raw_ocr else ""
    return raw_ocr, cleaned, engine_used

def clean_ocr_text(raw_text: str) -> str:
    """Normalizes OCR text and fixes common diacritic encoding artifacts."""
    text = raw_text
    for pattern, replacement in OCR_CORRECTION_RULES:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def extract_candidate_proposals(cleaned_text: str) -> List[Dict[str, Any]]:
    """
    Extracts Layer 2 candidate entities from slide text matching against DuckDB taxonomy.
    """
    conn = get_db()
    # Load taxonomy terms and aliases
    terms = conn.execute("""
        SELECT t.id, t.canonical_name, t.iast_name, tt.name AS category
        FROM taxonomy_terms t
        JOIN taxonomy_types tt ON t.taxonomy_type_id = tt.id
    """).fetchall()

    aliases = conn.execute("""
        SELECT a.alias, a.term_id, t.canonical_name, t.iast_name, tt.name
        FROM term_aliases a
        JOIN taxonomy_terms t ON a.term_id = t.id
        JOIN taxonomy_types tt ON t.taxonomy_type_id = tt.id
        WHERE a.is_searchable = TRUE
    """).fetchall()
    conn.close()

    proposals = []
    text_lower = cleaned_text.lower()
    matched_term_ids = set()

    # 1. Match aliases
    for row in aliases:
        alias_str, term_id, canon, iast, cat = row
        if re.search(r"\b" + re.escape(alias_str.lower()) + r"\b", text_lower):
            if term_id not in matched_term_ids:
                matched_term_ids.add(term_id)
                idx = text_lower.find(alias_str.lower())
                start = max(0, idx - 40)
                end = min(len(cleaned_text), idx + len(alias_str) + 40)
                snippet = cleaned_text[start:end].strip()

                proposals.append({
                    "id": f"prop_{uuid.uuid4().hex[:8]}",
                    "term_id": term_id,
                    "canonical_name": canon,
                    "iast_name": iast,
                    "category": cat,
                    "matched_alias": alias_str,
                    "confidence": 0.95,
                    "evidence_snippet": f"...{snippet}...",
                    "approved": True
                })

    # 2. Match canonical terms
    for row in terms:
        term_id, canon, iast, cat = row
        if term_id not in matched_term_ids:
            if re.search(r"\b" + re.escape(canon.lower()) + r"\b", text_lower):
                matched_term_ids.add(term_id)
                idx = text_lower.find(canon.lower())
                start = max(0, idx - 40)
                end = min(len(cleaned_text), idx + len(canon) + 40)
                snippet = cleaned_text[start:end].strip()

                proposals.append({
                    "id": f"prop_{uuid.uuid4().hex[:8]}",
                    "term_id": term_id,
                    "canonical_name": canon,
                    "iast_name": iast,
                    "category": cat,
                    "matched_alias": None,
                    "confidence": 0.98,
                    "evidence_snippet": f"...{snippet}...",
                    "approved": True
                })


    # 3. AUTONOMOUS ICONOGRAPHY PATTERN DISCOVERY (Self-Learning Layer)
    # Detects newly introduced Mudras, Asanas, Vahanas, and Ayudhas not yet in taxonomy
    iconography_patterns = [
        # Mudra / Hasta pattern (e.g. "Sikhara literally means upright thumb...", "Abhaya hasta", "Jnana mudra")
        (r"\b([A-Z][a-zāīūṛśṣñṭḍṇ]+)\s+(?:literally\s+means|mudrā|mudra|hasta|gesture)", "Iconographic Element", "Mudra"),
        (r"\b([A-Z][a-zāīūṛśṣñṭḍṇ]+āsana|asina|sthānaka|tribhaṅga|tribhanga|lalitāsana)\b", "Iconographic Element", "Postural Asana"),
        (r"\b([A-Z][a-zāīūṛśṣñṭḍṇ]+vāhana|mūṣika|mooshika|garuda|nandi|mayura)\b", "Iconographic Element", "Vahana Mount"),
        (r"\b(prabhāvaḷi|prabhavali|triśūla|chakra|aṅkuśa|pāśa|damaru|agni|veṇu|flute)\b", "Iconographic Element", "Ayudha Attribute")
    ]

    for pat, cat, subcat in iconography_patterns:
        matches = re.finditer(pat, cleaned_text, re.IGNORECASE)
        for m in matches:
            raw_entity = m.group(1).capitalize()
            # Clean up suffix if needed
            clean_entity = re.sub(r'(literally|means)', '', raw_entity, flags=re.I).strip()
            if len(clean_entity) < 3:
                continue

            # Standardize entity title
            if subcat == "Mudra" and not clean_entity.lower().endswith("mudra") and not clean_entity.lower().endswith("hasta"):
                canonical_candidate = f"{clean_entity} Mudra"
            else:
                canonical_candidate = clean_entity

            # Check if already matched
            already_matched = any(p["canonical_name"].lower() == canonical_candidate.lower() for p in proposals)
            if not already_matched:
                new_term_id = f"t_{clean_entity.lower().replace(' ', '_')}"
                idx = m.start()
                start = max(0, idx - 40)
                end = min(len(cleaned_text), idx + 60)
                snippet = cleaned_text[start:end].strip()

                proposals.append({
                    "id": f"prop_auto_{uuid.uuid4().hex[:6]}",
                    "term_id": new_term_id,
                    "canonical_name": canonical_candidate,
                    "iast_name": canonical_candidate,
                    "category": cat,
                    "matched_alias": clean_entity,
                    "confidence": 0.94,
                    "evidence_snippet": f"...{snippet}...",
                    "is_new_discovery": True,
                    "subcat": subcat,
                    "approved": True
                })

    return proposals

def get_ocr_context() -> Dict[str, Any]:
    """
    Returns existing studies, series, and taxonomy categories to populate
    the Target Monograph selector and proposal category editors.
    """
    conn = get_db()
    try:
        studies_raw = conn.execute("""
            SELECT s.id, s.title, s.slug, s.study_number, s.series_id, ser.name AS series_name, s.total_slides, s.access_level
            FROM studies s
            LEFT JOIN series ser ON s.series_id = ser.id
            ORDER BY s.study_number ASC, s.title ASC
        """).fetchall()
        studies = []
        for r in studies_raw:
            studies.append({
                "id": r[0],
                "title": r[1],
                "slug": r[2],
                "study_number": r[3] or r[0],
                "series_id": r[4],
                "series_name": r[5] or "General Series",
                "total_slides": r[6] or 0,
                "access_level": r[7] or "public"
            })

        series_raw = conn.execute("SELECT id, name, slug FROM series ORDER BY sort_order ASC, name ASC").fetchall()
        series = [{"id": r[0], "name": r[1], "slug": r[2]} for r in series_raw]

        categories = [
            {"code": "Mudra", "name": "Mudra / Hasta (Hand Gesture)"},
            {"code": "Asana", "name": "Asana (Posture / Stance)"},
            {"code": "Divinity", "name": "Divinity (Deity / Manifestation)"},
            {"code": "Ayudha", "name": "Ayudha (Weapon / Sacred Attribute)"},
            {"code": "Vahana", "name": "Vahana (Sacred Mount)"},
            {"code": "Form", "name": "Form (Murti Bheda)"},
            {"code": "Iconographic Element", "name": "Iconographic Element / Ornament"}
        ]
        return {"studies": studies, "series": series, "categories": categories}
    finally:
        conn.close()

def create_new_study(title: str, subtitle: Optional[str] = None, series_id: int = 1, access_level: str = "member_only") -> Dict[str, Any]:
    """
    Creates a new research iconograph study in the studies table with proper foreign keys.
    Default access level is 'member_only' (premium).
    """
    conn = get_db()
    try:
        # Validate foreign key series_id
        ser_row = conn.execute("SELECT id, name FROM series WHERE id = ?", (series_id,)).fetchone()
        if not ser_row:
            raise ValueError(f"Foreign key violation: series_id {series_id} not found in series table.")

        clean_slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
        if not clean_slug:
            clean_slug = f"study-{uuid.uuid4().hex[:6]}"

        existing_slug = conn.execute("SELECT id FROM studies WHERE slug = ?", (clean_slug,)).fetchone()
        if existing_slug:
            clean_slug = f"{clean_slug}-{uuid.uuid4().hex[:4]}"

        study_id = f"s_{clean_slug[:24]}"
        existing_id = conn.execute("SELECT id FROM studies WHERE id = ?", (study_id,)).fetchone()
        if existing_id:
            study_id = f"s_{uuid.uuid4().hex[:12]}"

        count_studies = conn.execute("SELECT COUNT(*) FROM studies").fetchone()[0]
        study_num = f"Study {count_studies + 1:03d}"
        sub = subtitle or f"Iconographical research iconograph on {title}"
        summary = f"# {title}\n\n{sub}\n\nCurated research iconograph in the Five Metal Masonry Sacred Iconography Archive."
        study_vec = text_to_dense_vector(f"{title} {sub} {ser_row[1]}")

        car_tier = "free" if access_level == "public" else "scholar_pro"
        conn.execute("""
            INSERT INTO studies (
                id, series_id, slug, title, subtitle, study_number, summary_markdown,
                access_level, total_slides, cover_image_url, required_tier, embedding
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, '/storage/images/default_cover.jpg', ?, ?)
        """, (study_id, series_id, clean_slug, title, sub, study_num, summary, access_level, car_tier, study_vec))

        return {
            "id": study_id,
            "title": title,
            "slug": clean_slug,
            "study_number": study_num,
            "series_id": series_id,
            "series_name": ser_row[1],
            "total_slides": 0,
            "access_level": access_level
        }
    finally:
        conn.close()

def create_new_series(name: str, scope: Optional[str] = None) -> Dict[str, Any]:
    """
    Creates a new editorial series in the series table.
    """
    conn = get_db()
    try:
        clean_slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
        existing = conn.execute("SELECT id FROM series WHERE slug = ? OR LOWER(name) = LOWER(?)", (clean_slug, name.strip())).fetchone()
        if existing:
            raise ValueError(f"An editorial series named '{name}' already exists.")

        max_row = conn.execute("SELECT COALESCE(MAX(id), 0) FROM series").fetchone()
        new_id = max_row[0] + 1
        scope_val = scope or f"Archival research iconograph series covering {name}"
        ser_vec = text_to_dense_vector(f"{name} {scope_val}")

        conn.execute("""
            INSERT INTO series (id, slug, name, scope, status, sort_order, embedding)
            VALUES (?, ?, ?, ?, 'active', ?, ?)
        """, (new_id, clean_slug, name.strip(), scope_val, new_id, ser_vec))

        return {
            "id": new_id,
            "name": name.strip(),
            "slug": clean_slug
        }
    finally:
        conn.close()

def commit_curator_approval(
    study_id: str,
    slide_number: Optional[int],
    slide_title: str,
    image_rel_url: str,
    raw_ocr: str,
    cleaned_ocr: str,
    approved_proposals: List[Dict[str, Any]],
    ocr_engine: str = LLM_MODEL,
    is_public: bool = False,
    study_title: Optional[str] = None,
    study_number: Optional[str] = None,
    access_level: str = "member_only"
) -> Dict[str, Any]:
    """
    Commits an approved slide and its edited proposals into DuckDB.
    Strictly verifies and populates foreign key relations across:
      studies -> study_slides (self-contained OCR + tags + embeddings)
      studies + taxonomy_terms -> study_taxonomy_mappings
      studies + study_slides + taxonomy_terms -> ai_metadata_proposals
      taxonomy_types -> taxonomy_terms -> term_aliases
    """
    conn = get_db()
    slide_id = f"sl_{uuid.uuid4().hex[:12]}"

    # Check if study exists; auto-create if missing to avoid orphan FK.
    # Uses caller-provided study_title/study_number/access_level so one bulk
    # batch can create multiple distinct studies (series -> studies -> plates).
    study_row = conn.execute("SELECT id, total_slides FROM studies WHERE id = ?", (study_id,)).fetchone()
    if not study_row:
        clean_title = study_title or slide_title or "Curated Iconography Study"
        acc = access_level if access_level in ("public", "member_only", "scholar_tier", "premium") else "member_only"
        stud_num = study_number or "Study 001"
        study_vec = text_to_dense_vector(f"{clean_title} {slide_title} {cleaned_ocr}")
        clean_slug = re.sub(r'[^a-z0-9]+', '-', study_id.lower()).strip('-')
        car_tier = "free" if acc == "public" else "scholar_pro"
        conn.execute("""
            INSERT INTO studies (id, series_id, slug, title, subtitle, study_number, summary_markdown, access_level, total_slides, cover_image_url, required_tier, embedding)
            VALUES (?, 1, ?, ?, ?, ?, 'Curated Research Iconograph', ?, 0, ?, ?, ?)
        """, (study_id, clean_slug, clean_title, f"Iconograph on {clean_title}", stud_num, acc, image_rel_url, car_tier, study_vec))

    # Calculate actual sequential slide number
    cur_count = conn.execute("SELECT COUNT(*) FROM study_slides WHERE study_id = ?", (study_id,)).fetchone()[0]
    effective_slide_number = cur_count + 1

    # 1. Insert the plate (study_slides) — self-contained: OCR + embeddings + tags + visibility.
    slide_vec = text_to_dense_vector(f"{slide_title} {cleaned_ocr}")
    plate_tags = []
    for _p in (approved_proposals or []):
        _nm = (_p.get("canonical_name") or "").strip()
        if _nm:
            plate_tags.append(_nm)
    tags_vec = text_to_dense_vector(" ".join(plate_tags) if plate_tags else slide_title)
    conn.execute("""
        INSERT INTO study_slides (
            id, study_id, slide_number, slide_title, image_url, thumbnail_url,
            caption, extracted_ocr_text, cleaned_text, visual_elements_summary, sort_order,
            embedding, is_public, tags, tags_embedding, ocr_engine, language_tag, word_count, confidence_avg, tokens_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'en-US', ?, 0.98, '{}')
    """, (
        slide_id, study_id, effective_slide_number, slide_title, image_rel_url, image_rel_url,
        f"Curated plate {effective_slide_number}", raw_ocr, cleaned_ocr, "High-resolution iconography plate",
        effective_slide_number, slide_vec, bool(is_public), plate_tags, tags_vec, ocr_engine, len((cleaned_ocr or "").split())
    ))

    # 3. Update studies.total_slides and cover_image_url
    conn.execute("""
        UPDATE studies 
        SET total_slides = ?, cover_image_url = COALESCE(cover_image_url, ?)
        WHERE id = ?
    """, (effective_slide_number, image_rel_url, study_id))

    # 4. Insert approved proposals, auto-create new taxonomy terms, and link study mappings
    mappings_count = 0
    new_terms_count = 0
    new_aliases_count = 0

    for p in approved_proposals:
        canon_name = (p.get("canonical_name") or "").strip()
        if not canon_name:
            continue

        cat_name = (p.get("category") or "Iconographic Element").strip()
        iast_name = (p.get("iast_name") or canon_name).strip()
        evidence = (p.get("evidence_snippet") or f"Curated iconographic reference for {canon_name}").strip()
        conf_val = float(p.get("confidence") or 0.95)

        term_id = p.get("term_id")
        if not term_id:
            slug_stem = re.sub(r'[^a-z0-9]+', '_', canon_name.lower()).strip('_')
            term_id = f"t_{slug_stem}"

        # Resolve taxonomy_type_id to guarantee valid foreign key (1 to 6)
        cat_lower = cat_name.lower()
        if "divin" in cat_lower or "deity" in cat_lower or "god" in cat_lower:
            type_id = 1
        elif "form" in cat_lower or "murti" in cat_lower:
            type_id = 2
        elif "place" in cat_lower or "temple" in cat_lower:
            type_id = 4
        elif "period" in cat_lower or "dynasty" in cat_lower:
            type_id = 5
        elif "source" in cat_lower or "shastra" in cat_lower:
            type_id = 6
        else:
            type_id = 3  # Iconographic Element (Mudra, Asana, Ayudha, Vahana, etc.)

        # Check if term exists; if not, create it with foreign key to taxonomy_types
        term_exists = conn.execute("SELECT id FROM taxonomy_terms WHERE id = ?", (term_id,)).fetchone()
        if not term_exists:
            term_slug = re.sub(r'[^a-z0-9]+', '-', canon_name.lower()).strip('-')
            term_vec = text_to_dense_vector(f"{canon_name} {iast_name} {cat_name}")
            conn.execute("""
                INSERT INTO taxonomy_terms (id, taxonomy_type_id, canonical_name, iast_name, slug, description, embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (term_id, type_id, canon_name, iast_name, term_slug, f"Curated {cat_name} plate concept", term_vec))
            new_terms_count += 1

            # Auto-seed searchable aliases
            alias_list = [canon_name]
            if iast_name and iast_name != canon_name:
                alias_list.append(iast_name)
            if "mudra" in canon_name.lower():
                alias_list.append(canon_name.lower().replace("mudra", "hasta").strip().title())
            for a in set(alias_list):
                if len(a) >= 3:
                    aid = f"al_{term_id}_{re.sub(r'[^a-z0-9]+', '_', a.lower())}"
                    # check alias exists
                    if not conn.execute("SELECT id FROM term_aliases WHERE id = ?", (aid,)).fetchone():
                        conn.execute("""
                            INSERT INTO term_aliases (id, term_id, alias, alias_type, is_searchable)
                            VALUES (?, ?, ?, 'canonical_variant', TRUE)
                        """, (aid, term_id, a))
                        new_aliases_count += 1

        # Insert into ai_metadata_proposals (FK: study_id, slide_id, mapped_term_id)
        prop_id = f"pr_{uuid.uuid4().hex[:8]}"
        conn.execute("""
            INSERT INTO ai_metadata_proposals VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, 'approved', 'Approved and verified by curator in Visual Ingestion Studio'
            )
        """, (
            prop_id, study_id, slide_id, effective_slide_number,
            cat_name.lower(), canon_name, term_id, conf_val, evidence
        ))

        # Insert into study_taxonomy_mappings (FK: study_id, term_id)
        map_id = f"m_{uuid.uuid4().hex[:8]}"
        conn.execute("""
            INSERT INTO study_taxonomy_mappings VALUES (
                ?, ?, ?, 'materially_discussed', ?, ?, TRUE, 'Curator approved via Visual OCR Studio'
            )
        """, (
            map_id, study_id, term_id, conf_val, json.dumps([effective_slide_number])
        ))
        mappings_count += 1

    conn.close()

    # Build List of Tables Impacted audit
    tables_impacted = [
        {
            "table_name": "study_slides",
            "operation": "INSERT",
            "rows_impacted": 1,
            "description": f"Plate {effective_slide_number} recorded in '{study_id}' (URI: {image_rel_url})"
        },
        {
            "table_name": "studies",
            "operation": "UPDATE",
            "rows_impacted": 1,
            "description": f"Study '{study_id}' total_slides updated to {effective_slide_number}"
        },
        {
            "table_name": "ai_metadata_proposals",
            "operation": "INSERT",
            "rows_impacted": mappings_count,
            "description": f"{mappings_count} curator-edited proposals committed with evidence"
        },
        {
            "table_name": "study_taxonomy_mappings",
            "operation": "INSERT",
            "rows_impacted": mappings_count,
            "description": f"{mappings_count} controlled Layer 3 taxonomy connections mapped"
        }
    ]

    if new_terms_count > 0:
        tables_impacted.append({
            "table_name": "taxonomy_terms",
            "operation": "INSERT",
            "rows_impacted": new_terms_count,
            "description": f"{new_terms_count} newly discovered controlled terms added to taxonomy"
        })
    if new_aliases_count > 0:
        tables_impacted.append({
            "table_name": "term_aliases",
            "operation": "INSERT",
            "rows_impacted": new_aliases_count,
            "description": f"{new_aliases_count} phonetic and spelling aliases registered"
        })

    return {
        "status": "success",
        "message": f"Plate {effective_slide_number} successfully ingested into DuckDB!",
        "slide_id": slide_id,
        "study_id": study_id,
        "effective_slide_number": effective_slide_number,
        "image_url": image_rel_url,
        "tables_impacted": tables_impacted
    }

