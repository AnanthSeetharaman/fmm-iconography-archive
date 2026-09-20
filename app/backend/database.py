import os
import duckdb
from typing import List, Dict, Any, Optional, Tuple
from config import DB_FILE

def get_db():
    """
    Returns a DuckDB connection to the archive database.
    """
    conn = duckdb.connect(DB_FILE)
    try:
        conn.execute("LOAD fts;")
    except Exception:
        try:
            conn.execute("INSTALL fts; LOAD fts;")
        except Exception:
            pass
    return conn

def init_duckdb_schema():
    """
    Initializes all DuckDB tables, indexes, and initial reference data.
    """
    conn = get_db()

    # 1. Core Content Tables
    conn.execute("""
    CREATE TABLE IF NOT EXISTS series (
        id INTEGER PRIMARY KEY,
        slug VARCHAR UNIQUE,
        name VARCHAR NOT NULL,
        scope VARCHAR NOT NULL,
        status VARCHAR NOT NULL,
        cover_image_url VARCHAR,
        sort_order INTEGER DEFAULT 0,
        embedding FLOAT[128]
    );

    CREATE TABLE IF NOT EXISTS studies (
        id VARCHAR PRIMARY KEY,
        slug VARCHAR UNIQUE NOT NULL,
        title VARCHAR NOT NULL,
        subtitle VARCHAR,
        study_number VARCHAR,
        series_id INTEGER REFERENCES series(id),
        content_type VARCHAR DEFAULT 'study',
        access_level VARCHAR DEFAULT 'public',
        status VARCHAR DEFAULT 'published',
        summary_markdown VARCHAR,
        original_publication_date DATE,
        cover_image_url VARCHAR,
        total_slides INTEGER DEFAULT 0,
        search_keywords VARCHAR,
        curator_notes VARCHAR,
        embedding FLOAT[128]
    );

    CREATE TABLE IF NOT EXISTS study_slides (
        id VARCHAR PRIMARY KEY,
        study_id VARCHAR REFERENCES studies(id),
        slide_number INTEGER NOT NULL,
        slide_title VARCHAR,
        image_url VARCHAR NOT NULL,
        thumbnail_url VARCHAR,
        caption VARCHAR,
        extracted_ocr_text VARCHAR,
        cleaned_text VARCHAR,
        visual_elements_summary VARCHAR,
        sort_order INTEGER DEFAULT 0,
        embedding FLOAT[128]
    );

    CREATE TABLE IF NOT EXISTS slide_ocr_data (
        id VARCHAR PRIMARY KEY,
        slide_id VARCHAR REFERENCES study_slides(id),
        ocr_engine VARCHAR NOT NULL,
        language_tag VARCHAR DEFAULT 'en-US',
        raw_ocr_output VARCHAR NOT NULL,
        normalized_text VARCHAR NOT NULL,
        word_count INTEGER DEFAULT 0,
        confidence_avg DOUBLE DEFAULT 0.95,
        tokens_json VARCHAR
    );

    -- 2. Taxonomy & Dictionary Tables
    CREATE TABLE IF NOT EXISTS taxonomy_types (
        id INTEGER PRIMARY KEY,
        code VARCHAR UNIQUE NOT NULL,
        name VARCHAR NOT NULL,
        description VARCHAR
    );

    CREATE TABLE IF NOT EXISTS taxonomy_terms (
        id VARCHAR PRIMARY KEY,
        taxonomy_type_id INTEGER REFERENCES taxonomy_types(id),
        parent_id VARCHAR,
        canonical_name VARCHAR NOT NULL,
        iast_name VARCHAR,
        slug VARCHAR NOT NULL,
        description VARCHAR,
        dictionary_entry_id VARCHAR,
        place_id VARCHAR,
        period_id INTEGER,
        is_active BOOLEAN DEFAULT TRUE,
        display_order INTEGER DEFAULT 0,
        embedding FLOAT[128]
    );

    CREATE TABLE IF NOT EXISTS term_aliases (
        id VARCHAR PRIMARY KEY,
        term_id VARCHAR REFERENCES taxonomy_terms(id),
        alias VARCHAR NOT NULL,
        alias_type VARCHAR DEFAULT 'spelling_variant',
        is_searchable BOOLEAN DEFAULT TRUE
    );

    CREATE TABLE IF NOT EXISTS study_taxonomy_mappings (
        id VARCHAR PRIMARY KEY,
        study_id VARCHAR REFERENCES studies(id),
        term_id VARCHAR REFERENCES taxonomy_terms(id),
        relevance_level VARCHAR DEFAULT 'materially_discussed',
        confidence_score DOUBLE DEFAULT 1.0,
        slide_numbers VARCHAR,
        curator_verified BOOLEAN DEFAULT TRUE,
        curator_notes VARCHAR
    );

    CREATE TABLE IF NOT EXISTS ai_metadata_proposals (
        id VARCHAR PRIMARY KEY,
        study_id VARCHAR REFERENCES studies(id),
        slide_id VARCHAR REFERENCES study_slides(id),
        slide_number INTEGER,
        suggested_taxonomy_type VARCHAR NOT NULL,
        raw_suggested_term VARCHAR NOT NULL,
        mapped_term_id VARCHAR REFERENCES taxonomy_terms(id),
        confidence_score DOUBLE DEFAULT 0.85,
        evidence_snippet VARCHAR,
        review_status VARCHAR DEFAULT 'pending',
        curator_notes VARCHAR
    );

    CREATE TABLE IF NOT EXISTS places (
        id VARCHAR PRIMARY KEY,
        slug VARCHAR UNIQUE NOT NULL,
        name VARCHAR NOT NULL,
        native_name VARCHAR,
        temple_name VARCHAR,
        deity_enshrined VARCHAR,
        tradition VARCHAR,
        town_city VARCHAR NOT NULL,
        district VARCHAR,
        state VARCHAR NOT NULL,
        country VARCHAR DEFAULT 'India',
        notes VARCHAR
    );

    CREATE TABLE IF NOT EXISTS periods_dynasties (
        id INTEGER PRIMARY KEY,
        slug VARCHAR UNIQUE NOT NULL,
        name VARCHAR NOT NULL,
        time_span VARCHAR,
        region VARCHAR,
        description VARCHAR
    );

    CREATE TABLE IF NOT EXISTS dictionary_entries (
        id VARCHAR PRIMARY KEY,
        slug VARCHAR UNIQUE NOT NULL,
        headword VARCHAR NOT NULL,
        iast_headword VARCHAR,
        part_of_speech VARCHAR,
        etymology VARCHAR,
        definition VARCHAR NOT NULL,
        extended_notes VARCHAR
    );

    CREATE TABLE IF NOT EXISTS premium_download_requests (
        id VARCHAR PRIMARY KEY,
        study_id VARCHAR REFERENCES studies(id),
        user_email VARCHAR NOT NULL,
        payment_method VARCHAR DEFAULT 'gpay',
        transaction_ref VARCHAR,
        amount_inr DOUBLE DEFAULT 499.0,
        status VARCHAR DEFAULT 'completed',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS users (
        id VARCHAR PRIMARY KEY,
        email VARCHAR UNIQUE NOT NULL,
        full_name VARCHAR NOT NULL,
        avatar_url VARCHAR,
        role VARCHAR DEFAULT 'scholar',
        google_sub VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Phase 2 Subscription & Behavioral Tracking Tables
    CREATE TABLE IF NOT EXISTS user_subscriptions (
        id VARCHAR PRIMARY KEY,
        user_id VARCHAR REFERENCES users(id),
        tier VARCHAR DEFAULT 'free',
        status VARCHAR DEFAULT 'active',
        billing_cycle VARCHAR DEFAULT 'monthly',
        amount_inr DOUBLE DEFAULT 0.0,
        payment_due_amount DOUBLE DEFAULT 0.0,
        last_payment_date TIMESTAMP,
        next_billing_date TIMESTAMP,
        payment_method VARCHAR DEFAULT 'gpay',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS user_downloads (
        id VARCHAR PRIMARY KEY,
        user_id VARCHAR REFERENCES users(id),
        study_id VARCHAR REFERENCES studies(id),
        slide_id VARCHAR,
        license_ref VARCHAR,
        resolution VARCHAR DEFAULT '300dpi_master',
        ip_address VARCHAR,
        downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS user_behavior_logs (
        id VARCHAR PRIMARY KEY,
        user_id VARCHAR,
        session_id VARCHAR,
        event_type VARCHAR NOT NULL,
        resource_id VARCHAR,
        event_payload_json VARCHAR,
        ip_address VARCHAR,
        user_agent VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS content_access_rules (
        id VARCHAR PRIMARY KEY,
        study_id VARCHAR REFERENCES studies(id),
        required_tier VARCHAR DEFAULT 'free',
        allow_preview BOOLEAN DEFAULT TRUE,
        allow_high_res_download BOOLEAN DEFAULT FALSE,
        is_blocked BOOLEAN DEFAULT FALSE,
        block_reason VARCHAR
    );

    -- T_SYST_PARAM_CONFIG: Externalized Application Configuration
    CREATE TABLE IF NOT EXISTS param_config (
        id VARCHAR PRIMARY KEY,
        param_group VARCHAR NOT NULL,
        param_key VARCHAR NOT NULL,
        param_value VARCHAR NOT NULL,
        value_type VARCHAR DEFAULT 'string',
        description VARCHAR,
        is_sensitive BOOLEAN DEFAULT FALSE,
        created_by VARCHAR DEFAULT 'system',
        updated_by VARCHAR DEFAULT 'system',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(param_group, param_key)
    );
    """)

    # Ensure users and phase 2 tables exist in pre-existing DB
    ensure_users_table(conn)
    ensure_phase2_tables(conn)
    ensure_secondary_study(conn)
    ensure_vector_columns(conn)
    ensure_canonical_ganesa_study(conn)

    # Check if series is seeded
    res = conn.execute("SELECT COUNT(*) FROM series;").fetchone()
    if res and res[0] == 0:
        seed_duckdb_archive(conn)

    # Ensure expanded aliases for Indic phonetic search (e.g. Mooshika -> Musika)
    ensure_expanded_aliases(conn)

    # Seed param_config if empty
    seed_param_config(conn)

    # Initialize FTS indices if available
    try:
        conn.execute("PRAGMA create_fts_index('studies', 'id', 'title', 'subtitle', 'summary_markdown', 'search_keywords');")
        conn.execute("PRAGMA create_fts_index('study_slides', 'id', 'slide_title', 'caption', 'extracted_ocr_text', 'cleaned_text');")
    except Exception:
        pass

    conn.close()

def ensure_users_table(conn):
    """
    Ensures that the users table exists in the archive database,
    and guarantees that ananth.seetharaman@gmail.com is registered as Super Administrator.
    """
    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id VARCHAR PRIMARY KEY,
        email VARCHAR UNIQUE NOT NULL,
        full_name VARCHAR NOT NULL,
        avatar_url VARCHAR,
        role VARCHAR DEFAULT 'scholar',
        google_sub VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Guarantee Super Admin ananth.seetharaman@gmail.com is seeded with role 'admin'
    admin_row = conn.execute("SELECT id, role FROM users WHERE LOWER(email) = 'ananth.seetharaman@gmail.com';").fetchone()
    if not admin_row:
        conn.execute("""
            INSERT INTO users (id, email, full_name, avatar_url, role)
            VALUES ('usr_admin_ananth', 'ananth.seetharaman@gmail.com', 'Ananth Seetharaman (Admin)', 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100&auto=format&fit=crop&q=80', 'admin');
        """)
    elif admin_row[1] != 'admin':
        conn.execute("UPDATE users SET role = 'admin' WHERE LOWER(email) = 'ananth.seetharaman@gmail.com';")


def ensure_vector_columns(conn):
    """Guarantees that the persistent FLOAT[128] vector embedding column is present."""
    for table in ["series", "studies", "study_slides", "taxonomy_terms"]:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN embedding FLOAT[128];")
        except Exception:
            pass

def ensure_secondary_study(conn):
    """
    Clean slate: do not re-seed Nataraja or any demo studies automatically.
    """
    ensure_vector_columns(conn)
    return
    has_study2 = conn.execute("SELECT COUNT(*) FROM studies WHERE id = 's_nataraja_002';").fetchone()
    if has_study2 and has_study2[0] > 0:
        return

    conn.execute("""
    INSERT INTO studies VALUES (
        's_nataraja_002',
        'nataraja-cosmic-dance-iconometry',
        'Nataraja: Cosmic Dance & Classical Iconometry',
        'Iconography of the Ananda Tandava and Chola Bronzes',
        'Study 002',
        11,
        'study',
        'member_only',
        'published',
        'A comprehensive study analyzing divine geometry, apasmara purusha subjection, agni torch, and prabhamandala flames in Chola bronze masterpieces.',
        '2026-09-12',
        'https://images.unsplash.com/photo-1582510003544-4d00b7f74220?w=600&auto=format&fit=crop&q=80',
        4,
        'Nataraja, Shiva, Tandava, Ananda Tandava, Apasmara, Chola, Bronze, Agni, Damaru',
        'Premium Monograph reserved for Scholar Pro Members'
    );
    """)

def ensure_phase2_tables(conn):
    """
    Ensures Phase 2 subscription, download licensing, behavioral logs,
    and content access control tables are present.
    """
    conn.execute("""
    CREATE TABLE IF NOT EXISTS user_subscriptions (
        id VARCHAR PRIMARY KEY,
        user_id VARCHAR,
        tier VARCHAR DEFAULT 'free',
        status VARCHAR DEFAULT 'active',
        billing_cycle VARCHAR DEFAULT 'monthly',
        amount_inr DOUBLE DEFAULT 0.0,
        payment_due_amount DOUBLE DEFAULT 0.0,
        id_proof_url VARCHAR,
        verification_status VARCHAR DEFAULT 'approved',
        institution_name VARCHAR,
        verified_by VARCHAR,
        verified_at TIMESTAMP,
        last_payment_date TIMESTAMP,
        next_billing_date TIMESTAMP,
        payment_method VARCHAR DEFAULT 'gpay',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS user_downloads (
        id VARCHAR PRIMARY KEY,
        user_id VARCHAR,
        study_id VARCHAR,
        slide_id VARCHAR,
        license_ref VARCHAR,
        resolution VARCHAR DEFAULT '300dpi_master',
        ip_address VARCHAR,
        downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS user_behavior_logs (
        id VARCHAR PRIMARY KEY,
        user_id VARCHAR,
        session_id VARCHAR,
        event_type VARCHAR NOT NULL,
        resource_id VARCHAR,
        event_payload_json VARCHAR,
        ip_address VARCHAR,
        user_agent VARCHAR,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS content_access_rules (
        id VARCHAR PRIMARY KEY,
        study_id VARCHAR,
        required_tier VARCHAR DEFAULT 'free',
        allow_preview BOOLEAN DEFAULT TRUE,
        allow_high_res_download BOOLEAN DEFAULT FALSE,
        is_blocked BOOLEAN DEFAULT FALSE,
        block_reason VARCHAR
    );
    """)

    # Ensure new columns exist if table was already created
    for col_def in [
        ("id_proof_url", "VARCHAR"),
        ("verification_status", "VARCHAR DEFAULT 'approved'"),
        ("institution_name", "VARCHAR"),
        ("verified_by", "VARCHAR"),
        ("verified_at", "TIMESTAMP")
    ]:
        try:
            conn.execute(f"ALTER TABLE user_subscriptions ADD COLUMN {col_def[0]} {col_def[1]};")
        except Exception:
            pass


def seed_param_config(conn):
    """Seeds default application configuration parameters."""
    count = conn.execute("SELECT COUNT(*) FROM param_config").fetchone()[0]
    if count > 0:
        # Update existing parameters with new pricing/trial rules if present
        try:
            conn.execute("UPDATE param_config SET param_value = '15' WHERE param_key = 'trial_duration_days';")
            conn.execute("UPDATE param_config SET param_value = '750' WHERE param_key = 'scholar_monthly_inr';")
            conn.execute("UPDATE param_config SET param_value = '350' WHERE param_key = 'student_monthly_inr';")
            conn.execute("UPDATE param_config SET param_value = '1' WHERE param_key = 'trial_download_limit';")
        except Exception:
            pass
        return

    import uuid
    configs = [
        # Pricing & Monetization
        ("pricing", "student_monthly_inr", "350", "number", "Monthly Student membership price in INR (requires ID review)", False),
        ("pricing", "scholar_monthly_inr", "750", "number", "Monthly Scholar membership price in INR (instant access)", False),
        ("pricing", "scholar_pro_annual_inr", "750", "number", "Monthly Scholar membership price in INR", False),
        ("pricing", "study_license_inr", "199", "number", "Individual study license price in INR", False),
        ("pricing", "trial_duration_days", "15", "number", "Duration of free trial membership in days", False),
        ("pricing", "trial_download_limit", "1", "number", "Maximum PDF downloads allowed during free trial", False),
        ("pricing", "currency_code", "INR", "string", "Default currency code", False),
        ("pricing", "payment_gateway", "gpay", "string", "Primary payment gateway (gpay, razorpay, stripe)", False),

        # Feature Toggles
        ("features", "guest_ocr_snippets", "hidden", "string", "OCR snippet visibility for guests: visible, hidden, truncated", False),
        ("features", "guest_slide_preview_count", "2", "number", "Number of slide previews shown to guests for premium studies", False),
        ("features", "enable_drm_protection", "true", "boolean", "Enable right-click and drag protection on archival plates", False),
        ("features", "enable_watermark", "true", "boolean", "Show watermark overlay on plate images", False),
        ("features", "enable_demo_login", "true", "boolean", "Enable demo login buttons (disable in production)", False),
        ("features", "enable_google_oauth", "true", "boolean", "Enable Google OAuth sign-in", False),
        ("features", "enable_trial_on_google_sso", "true", "boolean", "Auto-provision 30-day Scholar Pro trial on Google SSO sign-in", False),
        ("pricing", "trial_duration_days", "30", "number", "Duration of free trial membership in days", False),

        # Search & Retrieval
        ("search", "default_result_limit", "20", "number", "Default number of search results per page", False),
        ("search", "affinity_weight", "50", "number", "Weight percentage for theme affinity in ranking (0-100)", False),
        ("search", "confidence_weight", "30", "number", "Weight percentage for confidence in ranking (0-100)", False),
        ("search", "text_weight", "20", "number", "Weight percentage for text match in ranking (0-100)", False),
        ("search", "fuzzy_threshold", "0.60", "number", "Trigram similarity threshold for fuzzy matching (0.0-1.0)", False),
        ("search", "vector_threshold", "0.65", "number", "Dense vector cosine similarity threshold (0.0-1.0)", False),

        # OCR & AI
        ("ocr", "ocr_engine", "windows_native", "string", "Default OCR engine: windows_native, tesseract, google_vision", False),
        ("ocr", "ocr_language", "en-US", "string", "Default OCR language tag", False),
        ("ocr", "ai_confidence_threshold", "0.85", "number", "Minimum confidence for AI taxonomy proposals", False),
        ("ocr", "gemini_api_key", os.environ.get("GEMINI_API_KEY", ""), "string", "Google Gemini Vision API Key for scholar-grade epigraphy OCR", True),

        # Branding & Content
        ("branding", "site_title", "Five Metal Masonry", "string", "Site title displayed in header and SEO", False),
        ("branding", "site_subtitle", "Iconography Archive - Scholar Edition", "string", "Site subtitle", False),
        ("branding", "watermark_text", "Five Metal Masonry - Digital Archive", "string", "Watermark text on plates", False),
        ("branding", "admin_email", "ananth.seetharaman@gmail.com", "string", "Primary administrator email", False),

        # Security
        ("security", "session_max_age_hours", "168", "number", "Session cookie max age in hours (7 days = 168)", False),
        ("security", "cors_allowed_origins", "*", "string", "CORS allowed origins (comma-separated, * for all)", True),
        ("security", "rate_limit_per_minute", "60", "number", "API rate limit per IP per minute", False),
        ("security", "csp_enabled", "true", "boolean", "Enable Content Security Policy headers", False),

        # Google Cloud
        ("gcp", "google_client_id", "740115620155-q7r0g6cak77kul4u3te9visjlsiqiluj.apps.googleusercontent.com", "string", "Google OAuth 2.0 Web Client ID", False),
        ("gcp", "google_client_secret", "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", "string", "Google OAuth 2.0 Web Client Secret", True),
        ("gcp", "cloud_run_region", "asia-south1", "string", "GCP Cloud Run deployment region", False),
        ("gcp", "analytics_tracking_id", "", "string", "Google Analytics 4 Measurement ID", True),
    ]

    for group, key, value, vtype, desc, sensitive in configs:
        conn.execute(
            "INSERT INTO param_config (id, param_group, param_key, param_value, value_type, description, is_sensitive) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4())[:8], group, key, value, vtype, desc, sensitive)
        )

    conn.commit()
    print("      [OK] param_config seeded with", len(configs), "default configuration entries.")

def log_behavior(user_id=None, event_type="access", resource_id=None, payload=None, ip_address=None, user_agent=None):
    """
    Logs user interactions, search queries, slide views, and authorization checks.
    """
    try:
        conn = get_db()
        import uuid
        log_id = f"log_{uuid.uuid4().hex[:12]}"
        conn.execute("""
            INSERT INTO user_behavior_logs (id, user_id, session_id, event_type, resource_id, event_payload_json, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (log_id, user_id or "anonymous_guest", None, event_type, resource_id, str(payload or ""), ip_address, user_agent))
        conn.close()
    except Exception:
        pass

def ensure_expanded_aliases(conn):
    """
    Ensures that phonetic transliterations (Mooshika, Shiva, Ganesh)
    and OCR repair aliases are populated in term_aliases.
    """
    has_mooshika = conn.execute("SELECT COUNT(*) FROM term_aliases WHERE LOWER(alias) = 'mooshika';").fetchone()
    if has_mooshika and has_mooshika[0] > 0:
        return

    additional_aliases = [
        ('a23', 't_musika', 'Mooshika', 'phonetic_transliteration', True),
        ('a24', 't_musika', 'Mooshik', 'phonetic_transliteration', True),
        ('a25', 't_musika', 'Mooshikam', 'phonetic_transliteration', True),
        ('a26', 't_musika', 'Mūṣikavāhana', 'compound_iconographic_attribute', True),
        ('a27', 't_musika', 'Musikavahana', 'compound_iconographic_attribute', True),
        ('a28', 't_musika', 'Mooshikavahana', 'compound_iconographic_attribute', True),
        ('a29', 't_musika', 'Mushikavahana', 'compound_iconographic_attribute', True),
        ('a30', 't_musika', 'Mü$kavähana', 'ocr_artifact', True),
        ('a31', 't_musika', 'Mūṣika', 'iast_transliteration', True),
        ('a32', 't_ganesha', 'Ganesh', 'spelling_variant', True),
        ('a33', 't_ganesha', 'Ganapathy', 'spelling_variant', True),
        ('a34', 't_ganesha', 'Vigneshwara', 'spelling_variant', True),
        ('a35', 't_siva', 'Shiva', 'spelling_variant', True),
        ('a36', 't_siva', 'Sheeva', 'phonetic_transliteration', True),
    ]

    for aid, tid, alias, atype, is_s in additional_aliases:
        try:
            conn.execute(
                "INSERT INTO term_aliases (id, term_id, alias, alias_type, is_searchable) VALUES (?, ?, ?, ?, ?);",
                (aid, tid, alias, atype, is_s)
            )
        except Exception:
            pass

def seed_duckdb_archive(conn):
    """
    Seeds initial reference data and Study 001 with storage URIs.
    """
    # 1. 19 Series
    conn.execute("""
    INSERT INTO series VALUES
    (1, 'panchaloha-primer', 'Panchaloha Primer', 'An introduction to the Panchaloha bronze art form.', 'completed', NULL, 1),
    (2, 'dictionary-of-iconography', 'Dictionary of Iconography', 'Glossary of terms related to iconography.', 'completed', NULL, 2),
    (3, 'tala', 'Tala', 'Series on iconometry and proportional systems.', 'completed', NULL, 3),
    (4, 'bronzecast', 'BronzeCast', 'Studies and notes on bronze and the bronze tradition.', 'completed', NULL, 4),
    (5, 'mythics', 'Mythics', 'Iconography of mythical characters.', 'completed', NULL, 5),
    (6, '108-tandava', '108 Tandava', 'Iconography of the 108 dance poses of Siva.', 'completed', NULL, 6),
    (7, 'ayudha', 'Ayudha', 'Visual study of weapons and attributes held by divinities.', 'completed', NULL, 7),
    (8, 'roopam', 'Roopam', 'Iconography of minor and lesser-known divine forms.', 'ongoing', NULL, 8),
    (9, 'god-is-in-the-details', 'God is in the Details', 'Detailed visual iconographic study of museum and temple bronzes.', 'ongoing', NULL, 9),
    (10, '5mm-iconography-quiz', '5MM Iconography Quiz', 'Quiz-based engagement and learning around iconography.', 'ongoing', NULL, 10),
    (11, 'majors-iconography', 'Majors Iconography', 'Detailed thematic studies of major divinities; approximately 70 studies to date.', 'ongoing', NULL, 11),
    (12, 'mudra', 'Mudra', 'Visual study of hand gestures, mudras and hastas.', 'ongoing', NULL, 12),
    (13, '108-divya-desams', '108 Divya Desams', 'Iconography of Vishnu across the 108 Vaishnava shrines.', 'ongoing', NULL, 13),
    (14, 'abharana', 'Abharana', 'Visual study of ornamentation and attire.', 'ongoing', NULL, 14),
    (15, 'temple-iconography', 'Temple Iconography', 'Visual study of temple architecture and sculptures.', 'ongoing', NULL, 15),
    (16, 'iconography-shelf', 'Iconography Shelf', 'A guided view of books on iconography.', 'ongoing', NULL, 16),
    (17, 'padimam', 'Padimam', 'Visual study of stone sculptures in temples.', 'upcoming', NULL, 17),
    (18, 'vahana', 'Vahana', 'Visual study of the mounts of divinities.', 'upcoming', NULL, 18),
    (19, 'asana', 'Asana', 'Study of postures.', 'upcoming', NULL, 19);
    """)

    # 2. Taxonomy Types
    conn.execute("""
    INSERT INTO taxonomy_types VALUES
    (1, 'divinity', 'Divinity', 'Primary and secondary divine figures'),
    (2, 'form', 'Form', 'Specific identifiable iconographic forms'),
    (3, 'iconographic_element', 'Iconographic Element', 'Attributes, gestures, postures, anatomical traits'),
    (4, 'place', 'Place / Temple', 'Geographical and temple sites'),
    (5, 'period_dynasty', 'Period / Dynasty', 'Historical and sculptural era'),
    (6, 'source_reference', 'Source / Reference', 'Classical texts and collections');
    """)

    # 3. Places
    conn.execute("""
    INSERT INTO places VALUES
    ('p1', 'adi-vinayaka-thilatharpanapuri', 'Adi Vinayaka Temple, Thilatharpanapuri', 'ஆதி விநாயகர்', 'Muktheeswarar Temple complex', 'Nara-mukha Ganesha', 'Saiva / Ganapatya', 'Thilatharpanapuri', 'Tiruvarur', 'Tamil Nadu', 'India', 'Human-faced Ganesha without elephant head.'),
    ('p2', 'trishund-ganapati-pune', 'Trishund Mayureshwar Ganapati, Pune', 'त्रिशुंड गणपती', 'Trishund Ganapati Temple', 'Three-trunked Ganesha on peacock', 'Ganapatya', 'Pune', 'Pune', 'Maharashtra', 'India', '18th-century temple in Somwar Peth featuring 3 trunks on peacock mount.'),
    ('p3', 'garh-ganesh-jaipur', 'Garh Ganesh Temple, Jaipur', 'गढ़ गणेश', 'Garh Ganesh Mandir', 'Trunkless Ganesha', 'Ganapatya', 'Jaipur', 'Jaipur', 'Rajasthan', 'India', 'Hilltop temple showing Ganesha in child-like trunkless form.');
    """)

    # 4. Dictionary Entries
    conn.execute("""
    INSERT INTO dictionary_entries VALUES
    ('d1', 'asina', 'Asina', 'Āsīna', 'participle / adjective', 'From Sanskrit root ās (to sit, rest)', 'Seated posture; a generic term for any iconographic form depicted in a sitting position.', 'Contrasts with sthānaka (standing) and nṛtta (dancing). Includes padmāsana, sukhāsana, lalitāsana, ardhaparyaṅkāsana, and bhadrāsana.'),
    ('d2', 'lalitasana', 'Lalitasana', 'Lalitāsana', 'noun, neuter', 'From Sanskrit lalita (charming, graceful) + āsana', 'The posture of royal ease, wherein one leg is folded on seat while the other hangs down gracefully.', 'Quintessential posture for benevolent divinities including Ganesha and Devi.'),
    ('d3', 'sukhasana', 'Sukhasana', 'Sukhāsana', 'noun, neuter', 'From sukha (comfort) + āsana', 'Comfortable seated posture; relaxed informal disposition of legs.', 'Observed in Siva Somaskanda bronzes.'),
    ('d4', 'ardhaparyankasana', 'Ardhaparyankasana', 'Ardhaparyaṅkāsana', 'noun, neuter', 'From ardha + paryaṅka + āsana', 'Seated posture with one leg folded and one knee elevated with pendant foot.', 'Frequently used in Agamic descriptions of meditative royalty.'),
    ('d5', 'bhadrasana', 'Bhadrasana', 'Bhadrāsana', 'noun, neuter', 'From bhadra (auspicious) + āsana', 'Majestic sitting posture where feet rest on a support or soles meet symmetrically.', 'Classical imperial seated posture in Shilpa Shastras.'),
    ('d6', 'trishunda', 'Trishunda', 'Triśuṇḍa', 'adjective / noun', 'From tri (three) + śuṇḍā (trunk)', 'Possessing three elephant trunks; rare iconographic manifestation.', 'Exemplified in Pune Trishund temple.');
    """)

    # 5. Taxonomy Terms
    conn.execute("""
    INSERT INTO taxonomy_terms VALUES
    -- Divinities
    ('t_ganesha', 1, NULL, 'Ganesha', 'Gaṇeśa', 'ganesha', 'Lord of beginnings with elephant head', NULL, NULL, NULL, TRUE, 1),
    ('t_siva', 1, NULL, 'Siva', 'Śiva', 'siva', 'Supreme Saiva deity', NULL, NULL, NULL, TRUE, 2),
    ('t_vishnu', 1, NULL, 'Vishnu', 'Viṣṇu', 'vishnu', 'Preserver deity', NULL, NULL, NULL, TRUE, 3),

    -- Parent Groups
    ('t_asana_group', 3, NULL, 'Asana & Sthana', 'Āsana & Sthāna', 'asana-sthana', 'Postures and bodily dispositions', NULL, NULL, NULL, TRUE, 1),
    ('t_anatomy_group', 3, NULL, 'Physical / Anatomical Feature', 'Śārīrika-lakṣaṇa', 'anatomical-features', 'Diagnostic physical traits', NULL, NULL, NULL, TRUE, 2),
    ('t_vahana_group', 3, NULL, 'Vahana', 'Vāhana', 'vahana', 'Animal mounts', NULL, NULL, NULL, TRUE, 3),

    -- Asana Children
    ('t_asina', 3, 't_asana_group', 'Asina', 'Āsīna', 'asina', 'General seated posture', 'd1', NULL, NULL, TRUE, 1),
    ('t_sthanaka', 3, 't_asana_group', 'Sthanaka', 'Sthānaka', 'sthanaka', 'Standing posture', NULL, NULL, NULL, TRUE, 2),
    ('t_nrtta', 3, 't_asana_group', 'Nrtta', 'Nṛtta', 'nrtta', 'Dancing posture', NULL, NULL, NULL, TRUE, 3),
    ('t_lalitasana', 3, 't_asana_group', 'Lalitasana', 'Lalitāsana', 'lalitasana', 'Royal ease posture', 'd2', NULL, NULL, TRUE, 4),
    ('t_sukhasana', 3, 't_asana_group', 'Sukhasana', 'Sukhāsana', 'sukhasana', 'Comfortable sitting pose', 'd3', NULL, NULL, TRUE, 5),
    ('t_padmasana', 3, 't_asana_group', 'Padmasana', 'Padmāsana', 'padmasana', 'Full lotus posture', NULL, NULL, NULL, TRUE, 6),
    ('t_ardhaparyankasana', 3, 't_asana_group', 'Ardhaparyankasana', 'Ardhaparyaṅkāsana', 'ardhaparyankasana', 'Half cross-legged posture', 'd4', NULL, NULL, TRUE, 7),
    ('t_bhadrasana', 3, 't_asana_group', 'Bhadrasana', 'Bhadrāsana', 'bhadrasana', 'Auspicious symmetrical seated posture', 'd5', NULL, NULL, TRUE, 8),

    -- Anatomy Children
    ('t_dvibhuja', 3, 't_anatomy_group', 'Dvibhuja', 'Dvibhuja', 'dvibhuja', 'Two-armed form', NULL, NULL, NULL, TRUE, 1),
    ('t_caturbhuja', 3, 't_anatomy_group', 'Caturbhuja', 'Caturbhuja', 'caturbhuja', 'Four-armed form', NULL, NULL, NULL, TRUE, 2),
    ('t_sadbhuja', 3, 't_anatomy_group', 'Sadbhuja', 'Ṣaḍbhuja', 'sadbhuja', 'Six-armed form', NULL, NULL, NULL, TRUE, 3),
    ('t_astabhuja', 3, 't_anatomy_group', 'Astabhuja', 'Aṣṭabhuja', 'astabhuja', 'Eight-armed form', NULL, NULL, NULL, TRUE, 4),
    ('t_sodasabhuja', 3, 't_anatomy_group', 'Sodasabhuja', 'Ṣoḍaśabhuja', 'sodasabhuja', 'Sixteen-armed form', NULL, NULL, NULL, TRUE, 5),
    ('t_vamavarta', 3, 't_anatomy_group', 'Vamavarta', 'Vāmāvarta', 'vamavarta', 'Left-turning trunk', NULL, NULL, NULL, TRUE, 6),
    ('t_daksinavarta', 3, 't_anatomy_group', 'Daksinavarta', 'Dakṣiṇāvarta', 'daksinavarta', 'Right-turning trunk', NULL, NULL, NULL, TRUE, 7),
    ('t_trishunda', 3, 't_anatomy_group', 'Trishunda', 'Triśuṇḍa', 'trishunda', 'Three trunks', 'd6', NULL, NULL, TRUE, 8),
    ('t_human_headed', 3, 't_anatomy_group', 'Human-headed Form', 'Naramukha', 'human-headed', 'Human face of Adi Vinayaka', NULL, NULL, NULL, TRUE, 9),
    ('t_trunkless', 3, 't_anatomy_group', 'Trunkless Form', 'Ashunda', 'trunkless', 'Trunkless form of Garh Ganesh', NULL, NULL, NULL, TRUE, 10),

    -- Vahana Children
    ('t_musika', 3, 't_vahana_group', 'Musika', 'Mūṣika', 'musika', 'Mouse / rat mount of Ganesha', NULL, NULL, NULL, TRUE, 1),
    ('t_mayura', 3, 't_vahana_group', 'Mayura', 'Mayūra', 'mayura', 'Peacock mount of Trishunda Ganapati', NULL, NULL, NULL, TRUE, 2),
    ('t_simha', 3, 't_vahana_group', 'Simha', 'Siṃha', 'simha', 'Lion mount of Heramba Ganapati', NULL, NULL, NULL, TRUE, 3),

    -- Forms
    ('t_form_adi_vinayaka', 2, NULL, 'Adi Vinayaka', 'Ādi Vināyaka', 'adi-vinayaka', 'Primordial human-faced form', NULL, 'p1', NULL, TRUE, 1),
    ('t_form_trishund', 2, NULL, 'Trishund Ganapati', 'Triśuṇḍa Gaṇapati', 'trishund-ganapati', 'Three-trunked form on peacock', NULL, 'p2', NULL, TRUE, 2),
    ('t_form_garh_ganesh', 2, NULL, 'Garh Ganesh', 'Gaṛh Gaṇeśa', 'garh-ganesh', 'Trunkless form from Jaipur', NULL, 'p3', NULL, TRUE, 3);
    """)

    # 6. Term Aliases
    conn.execute("""
    INSERT INTO term_aliases VALUES
    ('a1', 't_ganesha', 'Ganesa', 'spelling_variant', TRUE),
    ('a2', 't_ganesha', 'Gaṇeśa', 'iast_transliteration', TRUE),
    ('a3', 't_ganesha', 'Ganapati', 'spelling_variant', TRUE),
    ('a4', 't_ganesha', 'Vinayaka', 'spelling_variant', TRUE),
    ('a5', 't_ganesha', 'Pillayar', 'regional_vernacular', TRUE),
    ('a6', 't_ganesha', 'Elephant God', 'english_translation', TRUE),
    ('a7', 't_ganesha', 'GaQeSa', 'ocr_artifact', TRUE),
    ('a8', 't_asina', 'Seated', 'english_translation', TRUE),
    ('a9', 't_asina', 'Sitting', 'english_translation', TRUE),
    ('a10', 't_asina', 'Āsīna', 'iast_transliteration', TRUE),
    ('a11', 't_asina', 'ÄsTna', 'ocr_artifact', TRUE),
    ('a12', 't_musika', 'Mushika', 'spelling_variant', TRUE),
    ('a13', 't_musika', 'Mouse', 'english_translation', TRUE),
    ('a14', 't_musika', 'Rat', 'english_translation', TRUE),
    ('a15', 't_trishunda', 'Three trunks', 'english_translation', TRUE),
    ('a16', 't_trishunda', 'Triśuṇḍa', 'iast_transliteration', TRUE),
    ('a17', 't_trishunda', 'Trishund', 'spelling_variant', TRUE),
    ('a18', 't_lalitasana', 'Royal ease', 'english_translation', TRUE),
    ('a19', 't_sukhasana', 'Easy pose', 'english_translation', TRUE),
    ('a20', 't_padmasana', 'Lotus pose', 'english_translation', TRUE),
    ('a21', 't_vamavarta', 'Left turning trunk', 'english_translation', TRUE),
    ('a22', 't_daksinavarta', 'Right turning trunk', 'english_translation', TRUE);
    """)

    # 7. Study 001: Ganesa Variations Carousel (Linked to Physical Storage URIs)
    conn.execute("""
    INSERT INTO studies VALUES (
        's_ganesa_001',
        'ganesa-variations-in-iconography',
        'Ganesa: Variations in Iconography',
        'Postural/Compositional, Anatomical, and Regional Distinctive Forms',
        'Study 001',
        11,
        'study',
        'public',
        'published',
        'A foundational iconography study examining visible variations in Ganesa icons across postures (āsīna, sthānaka, nṛtta), arm numbers (dvibhuja through ṣoḍaśabhuja), multi-headed forms, trunk disposition, and rare regional manifestations like Adi Vinayaka and Trishund Ganapati.',
        '2026-09-11',
        '/storage/images/ganesa-variations-in-iconography/slide_1.jpeg',
        4,
        'Ganesa, Ganesha, Ganapati, Asina, Lalitasana, Padmasana, Sukhasana, Ardhaparyankasana, Bhadrasana, Trishunda, Adi Vinayaka, Garh Ganesh',
        'Stored with URI tracking to physical storage folder'
    );
    """)

    # 8. 4 Carousel Slides with Local Storage URIs
    conn.execute("""
    INSERT INTO study_slides VALUES
    ('sl_1', 's_ganesa_001', 1, 'Variations in Iconography: Scope & Methodology', '/storage/images/ganesa-variations-in-iconography/slide_1.jpeg', '/storage/images/ganesa-variations-in-iconography/slide_1.jpeg', 'Introductory scope outlining visible variations in posture, composition, arms, faces, trunk orientation, and regional configurations.', 'ICONOGRAPHY VARIATIONS IN ICONOGRAPHY The iconography of Ganesa presents considerable variation in posture, composition and anatomical form. This study examines these visible variations— including the number of arms and faces, disposition of the trunk and distinctive regional configurations—rather than presenting another prescribed set of forms. Some of these variations occur within the well- known 32 forms of GaQeSa (covered earlier) and are revisited here specifically to -illustrate their distinctive iconographic features. This study considers variations that are visibly rather than expressed in the icon itself, distinctions based solely on epithets, legends or sthala-puräQa traditions. FIVE METAL MASONRY fivemetalmasonry.com', 'The iconography of Gaṇeśa presents considerable variation in posture, composition and anatomical form. This study examines these visible variations—including the number of arms and faces, disposition of the trunk and distinctive regional configurations—rather than presenting another prescribed set of forms. Some of these variations occur within the well-known 32 forms of Gaṇeśa (covered earlier) and are revisited here specifically to illustrate their distinctive iconographic features. This study considers variations that are visibly expressed in the icon itself, rather than distinctions based solely on epithets, legends or sthala-purāṇa traditions.', 'Title parchment with Five Metal Masonry hand emblem logo.', 1),
    ('sl_2', 's_ganesa_001', 2, 'Taxonomy of Ganesa Variations: Postural, Anatomical, Regional', '/storage/images/ganesa-variations-in-iconography/slide_2.jpeg', '/storage/images/ganesa-variations-in-iconography/slide_2.jpeg', 'Complete systematic breakdown: Postural & Compositional, Anatomical (Bahu-bheda, Mukha-bheda, Sunda-bheda), Regional forms, and Vahana variations.', 'ICONOGRAPHY QAN ESA VARIATIONS IN ICONOGRAPHY 1. POSTURAL & COMPOSITIONAL VARIATIONS • ÄsTna — seated; several variations in leg disposition occur. • Sthänaka — standing • Nrtta — dancing • Mü$kavähana — mounted/seated upon the mü#ika • With Devi/Devis • Samkara Murtis - ganesa combined with another divinity 2. ANATOMICAL VARIATIONS Bähu-bheda — number of arms • Dvibhuja — two-armed representations • Caturbhuja — four-armed; the most familiar depiction. • Sadbhuja, A#Cabhuja, Dagabhuja and other multi-armed forms Mukha-bheda — number of heads/faces • Ekamukha single-headed, the usual form. • Dvimukha / Trimukha / Paficamukha — clearly established forms Sundä-bheda — orientation of the trunk • Left-turning • Right-turning • Central/descending 3. REGIONAL / DISTINCTIVE FORMS FIVE METAL MASONRY fivemetalmasonry.com • Ädi Vinäyaka, Thilatharpanapuri — human-headed form • TriSuQ4a GaQapati, Pune— three-trunked form • Garh Ganesh, Jaipur - trunkless form VAHANA VARIATION Distinctive vähanas are covered under their respective forms — Heramba Ganapati, the paöcamukha form, with the lion; and TriSutpda Ganapati, with the peacock.', '1. Postural & Compositional Variations: Āsīna (seated), Sthānaka (standing), Nṛtta (dancing), Mūṣikavāhana (mounted upon mūṣika), With Devi/Devis, Saṅkara Mūrtis (combined with another divinity). 2. Anatomical Variations: Bāhu-bheda (arms: Dvibhuja, Caturbhuja, Ṣaḍbhuja, Aṣṭabhuja, Daśabhuja), Mukha-bheda (heads: Ekamukha, Dvimukha, Trimukha, Pañcamukha), Śuṇḍā-bheda (trunk: Left-turning, Right-turning, Central/descending). 3. Regional / Distinctive Forms: Ādi Vināyaka, Thilatharpanapuri (human-headed), Triśuṇḍa Gaṇapati, Pune (three-trunked), Garh Ganesh, Jaipur (trunkless). Vāhana Variation: Heramba Gaṇapati with lion (siṃha); Triśuṇḍa Gaṇapati with peacock (mayūra).', 'Comprehensive classification list on aged parchment background.', 2),
    ('sl_3', 's_ganesa_001', 3, 'Comparative Plate: 20 Iconographic Variations of Ganesa', '/storage/images/ganesa-variations-in-iconography/slide_3.jpeg', '/storage/images/ganesa-variations-in-iconography/slide_3.jpeg', 'Illustrated comparative plate demonstrating the 20 visual variations drawn from bronzes, stone sculptures, and classical iconometry.', 'ICONOGRAPHY VARIATIONS IN ICONOGRAPHY POSTURAL/COMPOSITIONAL • ANATOMICAL • REGIONAL POSTURAL & COMPOSITIONAL VARIATIONS ASINA SAD-BHUJA STANA ASTA-BHUJA MUSHIKA VAHANA ANATOMICAL VARIATIONS ASA-BHUJA SODASA-BÅUJA REGIONAL DISTINCTIVE FORMS DEVI SAHITA AMKARA MURTI ATUR-BHUJ DAKSINAVARTL•: FIVE METAL MASONRY fivemetalmasonry.com ADI- TN TRISHUND PANA''fi, PUNE GARH GANAPTI, JAIPUR', 'Visual comparative iconography plate illustrating: Row 1 (Postural): Āsīna, Sthānaka, Nṛtta, Mūṣika Vāhana, Devi Sahita, Saṅkara Mūrtis. Row 2 & 3 (Anatomical): Dvi-mukha, Tri-mukha, Pañca-mukha, Dvi-bhuja, Catur-bhuja, Ṣaḍ-bhuja, Aṣṭa-bhuja, Daśa-bhuja, Ṣoḍaśa-bhuja, Vāmāvarta, Dakṣiṇāvarta. Row 4 (Regional): Ādi-Vināyaka (Tamil Nadu, Human Form), Trishund Ganapati (Pune, Three Trunked), Garh Ganapati (Jaipur, Trunkless).', '20 detailed hand-drawn iconographic line drawings in 4 registers.', 3),
    ('sl_4', 's_ganesa_001', 4, 'Postural Variations: Asina | Sitting Postures in Detail', '/storage/images/ganesa-variations-in-iconography/slide_4.jpeg', '/storage/images/ganesa-variations-in-iconography/slide_4.jpeg', 'Deep iconographic reading of seated forms: padmasana, sukhasana, lalitasana, ardhaparyankasana, and bhadrasana.', 'ICONOGRAPHY POSTURAL VARIATIONS ÄSiNA I SITTING In the äsrna form, Ganesa is represented seated in a stable and composed posturer with the legs arranged in several ways according to the specific iconographic form. He in padmäsana (lotus may sit posture), sukhäsana (easy posture), lalitäsana (posture of royal ease), or ardhaparyahkäsana (with one leg — pendant and the other drawn up). He may also be shown in bhadräsana (a formal seated posture, generally with both feet placed on a support or with the legs arranged symmetrically). The characteristic elephant head, large ears and prominent rounded belly are retained, while the number ¯ of arms, gestures and attributes may vary according to the specific iconographic form. FIVE METAL MASONRY fivemetalmasonry.com', 'In the āsīna form, Gaṇeśa is represented seated in a stable and composed posture, with the legs arranged in several ways according to the specific iconographic form. He may sit in padmāsana (lotus posture), sukhāsana (easy posture), lalitāsana (posture of royal ease), or ardhaparyaṅkāsana (with one leg pendant and the other drawn up). He may also be shown in bhadrāsana (a formal seated posture, generally with both feet placed on a support or with the legs arranged symmetrically). The characteristic elephant head, large ears and prominent rounded belly are retained, while the number of arms, gestures and attributes may vary according to the specific iconographic form.', 'Line drawing of Caturbhuja Ganesha seated in Lalitasana on a padmapitha holding pasa and ankusa with modaka on trunk.', 4);
    """)

    # 9. Curated Mappings
    conn.execute("""
    INSERT INTO study_taxonomy_mappings VALUES
    ('m1', 's_ganesa_001', 't_ganesha', 'primary_subject', 1.0, '[1, 2, 3, 4]', TRUE, 'Primary divinity of this visual study'),
    ('m2', 's_ganesa_001', 't_asina', 'materially_discussed', 1.0, '[2, 3, 4]', TRUE, 'Asina posture analyzed extensively'),
    ('m3', 's_ganesa_001', 't_lalitasana', 'materially_discussed', 1.0, '[4]', TRUE, 'Lalitasana illustrated in detail'),
    ('m4', 's_ganesa_001', 't_sukhasana', 'materially_discussed', 1.0, '[4]', TRUE, 'Sukhasana defined in slide 4'),
    ('m5', 's_ganesa_001', 't_padmasana', 'materially_discussed', 1.0, '[4]', TRUE, 'Padmasana defined in slide 4'),
    ('m6', 's_ganesa_001', 't_bhadrasana', 'materially_discussed', 1.0, '[4]', TRUE, 'Bhadrasana defined in slide 4'),
    ('m7', 's_ganesa_001', 't_trishunda', 'materially_discussed', 1.0, '[2, 3]', TRUE, 'Trishunda three-trunked form'),
    ('m8', 's_ganesa_001', 't_vamavarta', 'materially_discussed', 1.0, '[2, 3]', TRUE, 'Left-turning trunk'),
    ('m9', 's_ganesa_001', 't_daksinavarta', 'materially_discussed', 1.0, '[2, 3]', TRUE, 'Right-turning trunk'),
    ('m10', 's_ganesa_001', 't_musika', 'materially_discussed', 1.0, '[2, 3]', TRUE, 'Musika mount');
    """)

    # 10. AI proposals seed
    conn.execute("""
    INSERT INTO ai_metadata_proposals VALUES
    ('pr1', 's_ganesa_001', 'sl_1', 1, 'divinity', 'Ganesa', 't_ganesha', 0.99, 'The iconography of Ganesa presents considerable variation in posture...', 'approved', 'Matched to canonical divinity Ganesha'),
    ('pr2', 's_ganesa_001', 'sl_2', 2, 'iconographic_element', 'Mü$kavähana', 't_musika', 0.95, 'Mü$kavähana — mounted/seated upon the mü#ika', 'approved', 'OCR artifact mapped to Musika'),
    ('pr3', 's_ganesa_001', 'sl_2', 2, 'iconographic_element', 'TriSuQ4a GaQapati', 't_trishunda', 0.98, 'TriSuQ4a GaQapati, Pune— three-trunked form', 'approved', 'OCR artifact mapped to Trishunda'),
    ('pr4', 's_ganesa_001', 'sl_4', 4, 'iconographic_element', 'lalitäsana', 't_lalitasana', 0.99, 'or lalitäsana (posture of royal ease)', 'approved', 'Direct match to Lalitasana');
    """)


def ensure_canonical_ganesa_study(conn):
    """
    Ensures that the canonical Ganesa study s_ganesa_001 and its 4 curated slides
    with 128-d dense vector embeddings are always present in the archive.
    """
    has_slides = conn.execute("SELECT COUNT(*) FROM study_slides WHERE study_id = 's_ganesa_001';").fetchone()
    if has_slides and has_slides[0] >= 4:
        return

    # Clear any incomplete partial state
    try:
        conn.execute("DELETE FROM content_access_rules WHERE study_id = 's_ganesa_001';")
        conn.execute("DELETE FROM study_taxonomy_mappings WHERE study_id = 's_ganesa_001';")
        conn.execute("DELETE FROM slide_ocr_data WHERE slide_id IN (SELECT id FROM study_slides WHERE study_id = 's_ganesa_001');")
        conn.execute("DELETE FROM study_slides WHERE study_id = 's_ganesa_001';")
        conn.execute("DELETE FROM studies WHERE id = 's_ganesa_001';")
    except Exception:
        pass

    # Insert study
    conn.execute("""
    INSERT INTO studies (
        id, slug, title, subtitle, study_number, series_id, content_type, access_level, status,
        summary_markdown, original_publication_date, cover_image_url, total_slides,
        search_keywords, curator_notes
    ) VALUES (
        's_ganesa_001',
        'ganesa-variations-in-iconography',
        'Ganesa: Variations in Iconography',
        'Postural/Compositional, Anatomical, and Regional Distinctive Forms',
        'Study 001',
        1,
        'study',
        'public',
        'published',
        'A foundational iconography study examining visible variations in Ganesa icons across postures (āsīna, sthānaka, nṛtta), arm numbers (dvibhuja through ṣoḍaśabhuja), multi-headed forms, trunk disposition, and rare regional manifestations like Adi Vinayaka and Trishund Ganapati.',
        '2026-09-11',
        '/storage/images/ganesa-variations-in-iconography/slide_1.jpeg',
        4,
        'Ganesa, Ganesha, Ganapati, Asina, Lalitasana, Padmasana, Sukhasana, Ardhaparyankasana, Bhadrasana, Trishunda, Adi Vinayaka, Garh Ganesh, 32 forms',
        'Permanent canonical study'
    );
    """)

    conn.execute("""
    INSERT INTO content_access_rules (id, study_id, required_tier, allow_preview, allow_high_res_download, is_blocked)
    VALUES ('car_pub_s_ganesa_001', 's_ganesa_001', 'free', TRUE, TRUE, FALSE);
    """)

    slides = [
        (
            'sl_1', 's_ganesa_001', 1,
            'Variations in Iconography: Scope & Methodology',
            '/storage/images/ganesa-variations-in-iconography/slide_1.jpeg',
            '/storage/images/ganesa-variations-in-iconography/slide_1.jpeg',
            'Introductory scope outlining visible variations in posture, composition, arms, faces, trunk orientation, and regional configurations.',
            'ICONOGRAPHY VARIATIONS IN ICONOGRAPHY The iconography of Ganesa presents considerable variation in posture, composition and anatomical form. This study examines these visible variations— including the number of arms and faces, disposition of the trunk and distinctive regional configurations—rather than presenting another prescribed set of forms. Some of these variations occur within the well- known 32 forms of GaQeSa (covered earlier) and are revisited here specifically to -illustrate their distinctive iconographic features. This study considers variations that are visibly rather than expressed in the icon itself, distinctions based solely on epithets, legends or sthala-puräQa traditions. FIVE METAL MASONRY fivemetalmasonry.com',
            'The iconography of Gaṇeśa presents considerable variation in posture, composition and anatomical form. This study examines these visible variations—including the number of arms and faces, disposition of the trunk and distinctive regional configurations—rather than presenting another prescribed set of forms. Some of these variations occur within the well-known 32 forms of Gaṇeśa (covered earlier) and are revisited here specifically to illustrate their distinctive iconographic features. This study considers variations that are visibly expressed in the icon itself, rather than distinctions based solely on epithets, legends or sthala-purāṇa traditions.',
            'Title parchment with Five Metal Masonry hand emblem logo.', 1
        ),
        (
            'sl_2', 's_ganesa_001', 2,
            'Taxonomy of Ganesa Variations: Postural, Anatomical, Regional',
            '/storage/images/ganesa-variations-in-iconography/slide_2.jpeg',
            '/storage/images/ganesa-variations-in-iconography/slide_2.jpeg',
            'Complete systematic breakdown: Postural & Compositional, Anatomical (Bahu-bheda, Mukha-bheda, Sunda-bheda), Regional forms, and Vahana variations.',
            'ICONOGRAPHY QAN ESA VARIATIONS IN ICONOGRAPHY 1. POSTURAL & COMPOSITIONAL VARIATIONS • ÄsTna — seated; several variations in leg disposition occur. • Sthänaka — standing • Nrtta — dancing • Mü$kavähana — mounted/seated upon the mü#ika • With Devi/Devis • Samkara Murtis - ganesa combined with another divinity 2. ANATOMICAL VARIATIONS Bähu-bheda — number of arms • Dvibhuja — two-armed representations • Caturbhuja — four-armed; the most familiar depiction. • Sadbhuja, A#Cabhuja, Dagabhuja and other multi-armed forms Mukha-bheda — number of heads/faces • Ekamukha single-headed, the usual form. • Dvimukha / Trimukha / Paficamukha — clearly established forms Sundä-bheda — orientation of the trunk • Left-turning • Right-turning • Central/descending 3. REGIONAL / DISTINCTIVE FORMS FIVE METAL MASONRY fivemetalmasonry.com • Ädi Vinäyaka, Thilatharpanapuri — human-headed form • TriSuQ4a GaQapati, Pune— three-trunked form • Garh Ganesh, Jaipur - trunkless form VAHANA VARIATION Distinctive vähanas are covered under their respective forms — Heramba Ganapati, the paöcamukha form, with the lion; and TriSutpda Ganapati, with the peacock.',
            '1. Postural & Compositional Variations: Āsīna (seated), Sthānaka (standing), Nṛtta (dancing), Mūṣikavāhana (mounted upon mūṣika), With Devi/Devis, Saṅkara Mūrtis (combined with another divinity). 2. Anatomical Variations: Bāhu-bheda (arms: Dvibhuja, Caturbhuja, Ṣaḍbhuja, Aṣṭabhuja, Daśabhuja), Mukha-bheda (heads: Ekamukha, Dvimukha, Trimukha, Pañcamukha), Śuṇḍā-bheda (trunk: Left-turning, Right-turning, Central/descending). 3. Regional / Distinctive Forms: Ādi Vināyaka, Thilatharpanapuri (human-headed), Triśuṇḍa Gaṇapati, Pune (three-trunked), Garh Ganesh, Jaipur (trunkless). Vāhana Variation: Heramba Gaṇapati with lion (siṃha); Triśuṇḍa Gaṇapati with peacock (mayūra).',
            'Comprehensive classification list on aged parchment background.', 2
        ),
        (
            'sl_3', 's_ganesa_001', 3,
            'Comparative Plate: 20 Iconographic Variations of Ganesa',
            '/storage/images/ganesa-variations-in-iconography/slide_3.jpeg',
            '/storage/images/ganesa-variations-in-iconography/slide_3.jpeg',
            'Illustrated comparative plate demonstrating the 20 visual variations drawn from bronzes, stone sculptures, and classical iconometry.',
            'ICONOGRAPHY VARIATIONS IN ICONOGRAPHY POSTURAL/COMPOSITIONAL • ANATOMICAL • REGIONAL POSTURAL & COMPOSITIONAL VARIATIONS ASINA SAD-BHUJA STANA ASTA-BHUJA MUSHIKA VAHANA ANATOMICAL VARIATIONS ASA-BHUJA SODASA-BÅUJA REGIONAL DISTINCTIVE FORMS DEVI SAHITA AMKARA MURTI ATUR-BHUJ DAKSINAVARTL•: FIVE METAL MASONRY fivemetalmasonry.com ADI- TN TRISHUND PANA''fi, PUNE GARH GANAPTI, JAIPUR',
            'Visual comparative iconography plate illustrating: Row 1 (Postural): Āsīna, Sthānaka, Nṛtta, Mūṣika Vāhana, Devi Sahita, Saṅkara Mūrtis. Row 2 & 3 (Anatomical): Dvi-mukha, Tri-mukha, Pañca-mukha, Dvi-bhuja, Catur-bhuja, Ṣaḍ-bhuja, Aṣṭa-bhuja, Daśa-bhuja, Ṣoḍaśa-bhuja, Vāmāvarta, Dakṣiṇāvarta. Row 4 (Regional): Ādi-Vināyaka (Tamil Nadu, Human Form), Trishund Ganapati (Pune, Three Trunked), Garh Ganapati (Jaipur, Trunkless).',
            '20 detailed hand-drawn iconographic line drawings in 4 registers.', 3
        ),
        (
            'sl_4', 's_ganesa_001', 4,
            'Postural Variations: Asina | Sitting Postures in Detail',
            '/storage/images/ganesa-variations-in-iconography/slide_4.jpeg',
            '/storage/images/ganesa-variations-in-iconography/slide_4.jpeg',
            'Deep iconographic reading of seated forms: padmasana, sukhasana, lalitasana, ardhaparyankasana, and bhadrasana.',
            'ICONOGRAPHY POSTURAL VARIATIONS ÄSiNA I SITTING In the äsrna form, Ganesa is represented seated in a stable and composed posturer with the legs arranged in several ways according to the specific iconographic form. He in padmäsana (lotus may sit posture), sukhäsana (easy posture), lalitäsana (posture of royal ease), or ardhaparyahkäsana (with one leg — pendant and the other drawn up). He may also be shown in bhadräsana (a formal seated posture, generally with both feet placed on a support or with the legs arranged symmetrically). The characteristic elephant head, large ears and prominent rounded belly are retained, while the number ¯ of arms, gestures and attributes may vary according to the specific iconographic form. FIVE METAL MASONRY fivemetalmasonry.com',
            'In the āsīna form, Gaṇeśa is represented seated in a stable and composed posture, with the legs arranged in several ways according to the specific iconographic form. He may sit in padmāsana (lotus posture), sukhāsana (easy posture), lalitāsana (posture of royal ease), or ardhaparyaṅkāsana (with one leg pendant and the other drawn up). He may also be shown in bhadrāsana (a formal seated posture, generally with both feet placed on a support or with the legs arranged symmetrically). The characteristic elephant head, large ears and prominent rounded belly are retained, while the number of arms, gestures and attributes may vary according to the specific iconographic form.',
            'Line drawing of Caturbhuja Ganesha seated in Lalitasana on a padmapitha holding pasa and ankusa with modaka on trunk.', 4
        )
    ]

    for sl in slides:
        sl_id, sid, num, title, img, thumb, cap, raw, clean, vis, sort_order = sl
        conn.execute("""
        INSERT INTO study_slides (
            id, study_id, slide_number, slide_title, image_url, thumbnail_url,
            caption, extracted_ocr_text, cleaned_text, visual_elements_summary, sort_order
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (sl_id, sid, num, title, img, thumb, cap, raw, clean, vis, sort_order))

    conn.execute("""
    INSERT INTO study_taxonomy_mappings VALUES
    ('m1', 's_ganesa_001', 't_ganesha', 'primary_subject', 1.0, '[1, 2, 3, 4]', TRUE, 'Primary divinity of this visual study'),
    ('m2', 's_ganesa_001', 't_asina', 'materially_discussed', 1.0, '[2, 3, 4]', TRUE, 'Asina posture analyzed extensively'),
    ('m3', 's_ganesa_001', 't_lalitasana', 'materially_discussed', 1.0, '[4]', TRUE, 'Lalitasana illustrated in detail'),
    ('m4', 's_ganesa_001', 't_sukhasana', 'materially_discussed', 1.0, '[4]', TRUE, 'Sukhasana defined in slide 4'),
    ('m5', 's_ganesa_001', 't_padmasana', 'materially_discussed', 1.0, '[4]', TRUE, 'Padmasana defined in slide 4'),
    ('m6', 's_ganesa_001', 't_bhadrasana', 'materially_discussed', 1.0, '[4]', TRUE, 'Bhadrasana defined in slide 4'),
    ('m7', 's_ganesa_001', 't_trishunda', 'materially_discussed', 1.0, '[2, 3]', TRUE, 'Trishunda three-trunked form'),
    ('m8', 's_ganesa_001', 't_vamavarta', 'materially_discussed', 1.0, '[2, 3]', TRUE, 'Left-turning trunk'),
    ('m9', 's_ganesa_001', 't_daksinavarta', 'materially_discussed', 1.0, '[2, 3]', TRUE, 'Right-turning trunk'),
    ('m10', 's_ganesa_001', 't_musika', 'materially_discussed', 1.0, '[2, 3]', TRUE, 'Musika mount');
    """)

