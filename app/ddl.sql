-- =============================================================================
-- FIVE METAL MASONRY (FMM) - CANONICAL ARCHIVAL DATABASE SCHEMA (DDL)
-- Database Engine: DuckDB / ANSI SQL Compatible
-- Architecture: Medallion 3-Tier (Bronze Raw, Silver ODS, Gold Operations)
-- =============================================================================

-- =============================================================================
-- TIER 1: 🟤 BRONZE LAYER (Raw OCR, Ingested Slides & Machine Proposals)
-- =============================================================================

-- 1.1 Ingested Study Slides & High-Res Plates (T_RAW_STUDY_SLIDES)
CREATE TABLE IF NOT EXISTS study_slides (
    id VARCHAR PRIMARY KEY,
    study_id VARCHAR NOT NULL,
    slide_number INTEGER NOT NULL,
    slide_title VARCHAR,
    image_url VARCHAR NOT NULL,
    thumbnail_url VARCHAR,
    caption VARCHAR,
    extracted_ocr_text VARCHAR,
    cleaned_text VARCHAR,
    visual_elements_summary VARCHAR,
    sort_order INTEGER DEFAULT 0
);

-- 1.2 Deep Machine OCR Output & Token Coordinates (T_RAW_SLIDE_OCR)
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

-- 1.3 Autonomous AI Metadata & Taxonomy Proposals (T_RAW_AI_PROPOSALS)
CREATE TABLE IF NOT EXISTS ai_metadata_proposals (
    id VARCHAR PRIMARY KEY,
    study_id VARCHAR,
    slide_id VARCHAR REFERENCES study_slides(id),
    slide_number INTEGER,
    suggested_taxonomy_type VARCHAR NOT NULL,
    raw_suggested_term VARCHAR NOT NULL,
    mapped_term_id VARCHAR,
    confidence_score DOUBLE DEFAULT 0.85,
    evidence_snippet VARCHAR,
    review_status VARCHAR DEFAULT 'pending',
    curator_notes VARCHAR
);

-- =============================================================================
-- TIER 2: 🔵 SILVER LAYER (Curated Operational Data Store - ODS)
-- =============================================================================

-- 2.1 Archival Series (T_ODS_SERIES)
CREATE TABLE IF NOT EXISTS series (
    id INTEGER PRIMARY KEY,
    slug VARCHAR UNIQUE,
    name VARCHAR NOT NULL,
    scope VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    cover_image_url VARCHAR,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR DEFAULT 'curator',
    updated_by VARCHAR DEFAULT 'curator'
);

-- 2.2 Scholarly Research Monographs & Studies (T_ODS_STUDIES)
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR DEFAULT 'curator',
    updated_by VARCHAR DEFAULT 'curator'
);

-- 2.3 Taxonomy Category Types (T_ODS_TAXONOMY_TYPES)
CREATE TABLE IF NOT EXISTS taxonomy_types (
    id INTEGER PRIMARY KEY,
    code VARCHAR UNIQUE NOT NULL,
    name VARCHAR NOT NULL,
    description VARCHAR
);

-- 2.4 Canonical Iconography Taxonomy Terms (T_ODS_TAXONOMY_TERMS)
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
    display_order INTEGER DEFAULT 0
);

-- 2.5 Multilingual Script & Transliteration Aliases (T_ODS_TERM_ALIASES)
CREATE TABLE IF NOT EXISTS term_aliases (
    id VARCHAR PRIMARY KEY,
    term_id VARCHAR REFERENCES taxonomy_terms(id),
    alias VARCHAR NOT NULL,
    alias_type VARCHAR DEFAULT 'spelling_variant',
    is_searchable BOOLEAN DEFAULT TRUE
);

-- 2.6 Verified Study-to-Taxonomy Relational Knowledge Bridges (T_ODS_STUDY_TAXONOMY)
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

-- 2.7 Sacred Temples & Geographic Provenance (T_ODS_PLACES)
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

-- 2.8 Historical Chronologies & Dynastic Eras (T_ODS_PERIODS)
CREATE TABLE IF NOT EXISTS periods_dynasties (
    id INTEGER PRIMARY KEY,
    slug VARCHAR UNIQUE NOT NULL,
    name VARCHAR NOT NULL,
    time_span VARCHAR,
    region VARCHAR,
    description VARCHAR
);

-- 2.9 Sanskrit Lexicon & Agamic Definitions (T_ODS_DICTIONARY)
CREATE TABLE IF NOT EXISTS dictionary_entries (
    id VARCHAR PRIMARY KEY,
    slug VARCHAR UNIQUE NOT NULL,
    headword VARCHAR NOT NULL,
    iast_headword VARCHAR,
    part_of_speech VARCHAR,
    etymology VARCHAR,
    definition VARCHAR NOT NULL,
    extended_notes VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR DEFAULT 'curator',
    updated_by VARCHAR DEFAULT 'curator'
);

-- 2.10 Primary Source Textual Catalog (T_ODS_DOC_CATALOG)
CREATE TABLE IF NOT EXISTS doc_ref_catalog (
    doc_ref VARCHAR PRIMARY KEY,
    doc_name VARCHAR NOT NULL,
    corpus VARCHAR,
    section VARCHAR,
    author_or_tradition VARCHAR,
    language VARCHAR,
    applicability_to_iconography VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR DEFAULT 'curator',
    updated_by VARCHAR DEFAULT 'curator'
);

-- 2.11 Granular DRM & Access Tier Rules (T_ODS_CONTENT_RULES)
CREATE TABLE IF NOT EXISTS content_access_rules (
    id VARCHAR PRIMARY KEY,
    study_id VARCHAR REFERENCES studies(id),
    required_tier VARCHAR DEFAULT 'free',
    allow_preview BOOLEAN DEFAULT TRUE,
    allow_high_res_download BOOLEAN DEFAULT FALSE,
    is_blocked BOOLEAN DEFAULT FALSE,
    block_reason VARCHAR
);

-- =============================================================================
-- TIER 3: 🟡 GOLD LAYER (System Identity, Security, Monetization & Audits)
-- =============================================================================

-- 3.1 Scholar Identities & RBAC Roles (T_SYST_USERS)
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

-- 3.2 Scholar Pro Recurring Subscriptions (T_SYST_SUBSCRIPTIONS)
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

-- 3.3 High-Resolution 300 DPI Download Receipts (T_SYST_DOWNLOADS)
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

-- 3.4 Premium GPay Monograph Unlocks (T_SYST_DOWNLOAD_REQ)
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

-- 3.5 Real-Time Telemetry & Behavior Audit Stream (T_SYST_BEHAVIOR_LOG)
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

-- 3.6 Curatorial Audit Ledger for Historical Accountability (T_SYST_AUDIT_LOG)
CREATE TABLE IF NOT EXISTS audit_logs (
    id VARCHAR PRIMARY KEY,
    table_name VARCHAR NOT NULL,
    record_id VARCHAR NOT NULL,
    action VARCHAR NOT NULL,
    user_email VARCHAR NOT NULL,
    user_role VARCHAR NOT NULL,
    changed_fields_json VARCHAR,
    previous_state_json VARCHAR,
    new_state_json VARCHAR,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
