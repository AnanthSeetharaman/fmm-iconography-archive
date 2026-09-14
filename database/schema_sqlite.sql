-- ============================================================================
-- FIVE METAL MASONRY (FMM) ICONOGRAPHY ARCHIVE
-- Database Schema for SQLite (Portable, Development & Edge, v1.2)
-- 
-- Includes SQLite FTS5 (Full-Text Search) with unicode61 tokenizer,
-- automated synchronization triggers, and three-layer indexing architecture.
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------------------------
-- 1. CORE RELATIONAL TABLES
-- ----------------------------------------------------------------------------

-- Editorial Series (All 19 flat series from Conceptual Framework)
CREATE TABLE IF NOT EXISTS series (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    scope TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('completed', 'ongoing', 'upcoming')),
    cover_image_url TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Studies (The fundamental unit of the archive)
CREATE TABLE IF NOT EXISTS studies (
    id TEXT PRIMARY KEY,                   -- UUID string
    slug TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    subtitle TEXT,
    study_number TEXT,                     -- e.g. "Study 001"
    series_id INTEGER NOT NULL REFERENCES series(id) ON DELETE RESTRICT,
    content_type TEXT NOT NULL DEFAULT 'study' CHECK(content_type IN ('study', 'dictionary_entry', 'quiz', 'book')),
    access_level TEXT NOT NULL DEFAULT 'public' CHECK(access_level IN ('public', 'member_only')),
    status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft', 'in_review', 'published', 'archived')),
    summary_markdown TEXT,
    original_publication_date DATE,
    original_instagram_url TEXT,
    cover_image_url TEXT,
    pdf_attachment_url TEXT,
    total_slides INTEGER NOT NULL DEFAULT 0,
    search_keywords TEXT,
    curator_notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Carousel Slides
CREATE TABLE IF NOT EXISTS study_slides (
    id TEXT PRIMARY KEY,                   -- UUID string
    study_id TEXT NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
    slide_number INTEGER NOT NULL,
    slide_title TEXT,
    image_url TEXT NOT NULL,
    thumbnail_url TEXT,
    caption TEXT,
    extracted_ocr_text TEXT,               -- Layer 1: Raw extracted OCR text
    cleaned_text TEXT,                     -- Cleaned & spell-corrected text
    visual_elements_summary TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(study_id, slide_number)
);

-- Slide OCR Metadata
CREATE TABLE IF NOT EXISTS slide_ocr_data (
    id TEXT PRIMARY KEY,
    slide_id TEXT NOT NULL REFERENCES study_slides(id) ON DELETE CASCADE,
    ocr_engine TEXT NOT NULL,              -- e.g. "windows_media_ocr"
    language_tag TEXT DEFAULT 'en-US',
    raw_ocr_output TEXT NOT NULL,
    normalized_text TEXT NOT NULL,
    word_count INTEGER DEFAULT 0,
    confidence_avg REAL,
    tokens_json TEXT,                      -- JSON string of bounding boxes & words
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Dictionary of Iconography Entries
CREATE TABLE IF NOT EXISTS dictionary_entries (
    id TEXT PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    headword TEXT NOT NULL,
    iast_headword TEXT,
    part_of_speech TEXT,
    etymology TEXT,
    definition TEXT NOT NULL,
    extended_notes TEXT,
    related_terms TEXT,                    -- Comma-separated or JSON array string
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Places / Temples / Shrines
CREATE TABLE IF NOT EXISTS places (
    id TEXT PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    native_name TEXT,
    temple_name TEXT,
    deity_enshrined TEXT,
    tradition TEXT,
    town_city TEXT NOT NULL,
    district TEXT,
    state TEXT NOT NULL,
    country TEXT NOT NULL DEFAULT 'India',
    latitude REAL,
    longitude REAL,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Historical Periods / Dynasties
CREATE TABLE IF NOT EXISTS periods_dynasties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    time_span TEXT,
    region TEXT,
    description TEXT
);

-- Classical Sources & Scholarship References
CREATE TABLE IF NOT EXISTS sources_references (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    author_or_tradition TEXT,
    work_type TEXT,
    publication_year TEXT,
    citation_details TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Study-Source Junction
CREATE TABLE IF NOT EXISTS study_sources (
    study_id TEXT NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
    source_id TEXT NOT NULL REFERENCES sources_references(id) ON DELETE CASCADE,
    specific_page_or_verse TEXT,
    citation_context TEXT,
    PRIMARY KEY(study_id, source_id)
);

-- ----------------------------------------------------------------------------
-- 2. LAYER 3: CONTROLLED SCHOLARLY TAXONOMY
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS taxonomy_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL CHECK(code IN ('divinity', 'form', 'iconographic_element', 'place', 'period_dynasty', 'source_reference')),
    name TEXT NOT NULL,
    description TEXT
);

-- Controlled Taxonomy Terms
CREATE TABLE IF NOT EXISTS taxonomy_terms (
    id TEXT PRIMARY KEY,
    taxonomy_type_id INTEGER NOT NULL REFERENCES taxonomy_types(id) ON DELETE RESTRICT,
    parent_id TEXT REFERENCES taxonomy_terms(id) ON DELETE SET NULL,
    canonical_name TEXT NOT NULL,
    iast_name TEXT,
    slug TEXT NOT NULL,
    description TEXT,
    dictionary_entry_id TEXT REFERENCES dictionary_entries(id) ON DELETE SET NULL,
    place_id TEXT REFERENCES places(id) ON DELETE SET NULL,
    period_id INTEGER REFERENCES periods_dynasties(id) ON DELETE SET NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    display_order INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(taxonomy_type_id, slug)
);

-- Term Aliases & Spelling Variants
CREATE TABLE IF NOT EXISTS term_aliases (
    id TEXT PRIMARY KEY,
    term_id TEXT NOT NULL REFERENCES taxonomy_terms(id) ON DELETE CASCADE,
    alias TEXT NOT NULL,
    alias_type TEXT NOT NULL DEFAULT 'spelling_variant' CHECK(alias_type IN ('spelling_variant', 'iast_transliteration', 'english_translation', 'regional_vernacular', 'common_misspelling', 'ocr_artifact')),
    is_searchable INTEGER NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Study Taxonomy Mappings (Curated Indexing Layer)
CREATE TABLE IF NOT EXISTS study_taxonomy_mappings (
    id TEXT PRIMARY KEY,
    study_id TEXT NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
    term_id TEXT NOT NULL REFERENCES taxonomy_terms(id) ON DELETE RESTRICT,
    relevance_level TEXT NOT NULL DEFAULT 'materially_discussed' CHECK(relevance_level IN ('primary_subject', 'materially_discussed', 'secondary_reference')),
    confidence_score REAL DEFAULT 1.0,
    slide_numbers TEXT,                    -- JSON array string e.g. "[1, 2, 4]"
    curator_verified INTEGER NOT NULL DEFAULT 1,
    curator_notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(study_id, term_id)
);

-- ----------------------------------------------------------------------------
-- 3. LAYER 2: AI INGESTION PROPOSALS & REVIEW WORKFLOW
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS ingestion_batches (
    id TEXT PRIMARY KEY,
    batch_name TEXT NOT NULL,
    source_directory TEXT,
    total_studies INTEGER DEFAULT 0,
    total_slides INTEGER DEFAULT 0,
    status TEXT DEFAULT 'in_progress',
    log_details TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_metadata_proposals (
    id TEXT PRIMARY KEY,
    batch_id TEXT REFERENCES ingestion_batches(id) ON DELETE SET NULL,
    study_id TEXT NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
    slide_id TEXT REFERENCES study_slides(id) ON DELETE CASCADE,
    slide_number INTEGER,
    suggested_taxonomy_type TEXT NOT NULL,
    raw_suggested_term TEXT NOT NULL,
    mapped_term_id TEXT REFERENCES taxonomy_terms(id) ON DELETE SET NULL,
    confidence_score REAL NOT NULL DEFAULT 0.8,
    evidence_snippet TEXT,
    review_status TEXT NOT NULL DEFAULT 'pending' CHECK(review_status IN ('pending', 'approved', 'rejected', 'modified')),
    curator_notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    reviewed_at DATETIME
);

-- ----------------------------------------------------------------------------
-- 4. FULL-TEXT SEARCH (SQLite FTS5)
-- ----------------------------------------------------------------------------

-- FTS5 Table for Studies & Taxonomy
CREATE VIRTUAL TABLE IF NOT EXISTS studies_fts USING fts5(
    study_id UNINDEXED,
    title,
    subtitle,
    summary_markdown,
    series_name,
    divinities,
    taxonomy_elements,
    aliases,
    tokenize = 'unicode61 remove_diacritics 2'
);

-- FTS5 Table for Deep Slide OCR Text (Layer 1)
CREATE VIRTUAL TABLE IF NOT EXISTS study_slides_fts USING fts5(
    slide_id UNINDEXED,
    study_id UNINDEXED,
    slide_number UNINDEXED,
    slide_title,
    caption,
    extracted_ocr_text,
    cleaned_text,
    tokenize = 'unicode61 remove_diacritics 2'
);

-- FTS5 Table for Taxonomy Terms & Aliases (Autocomplete)
CREATE VIRTUAL TABLE IF NOT EXISTS taxonomy_terms_fts USING fts5(
    term_id UNINDEXED,
    canonical_name,
    iast_name,
    category,
    aliases,
    tokenize = 'unicode61 remove_diacritics 2'
);

-- ----------------------------------------------------------------------------
-- 5. VIEWS FOR SEARCH & DISCOVERY
-- ----------------------------------------------------------------------------

CREATE VIEW IF NOT EXISTS v_studies_catalog AS
SELECT 
    s.id AS study_id,
    s.slug,
    s.title,
    s.subtitle,
    s.study_number,
    s.access_level,
    s.status,
    s.total_slides,
    s.cover_image_url,
    s.original_publication_date,
    ser.id AS series_id,
    ser.name AS series_name,
    ser.slug AS series_slug,
    (
        SELECT GROUP_CONCAT(t.canonical_name, ', ')
        FROM study_taxonomy_mappings m
        JOIN taxonomy_terms t ON m.term_id = t.id
        JOIN taxonomy_types tt ON t.taxonomy_type_id = tt.id
        WHERE m.study_id = s.id AND tt.code = 'divinity' AND m.relevance_level = 'primary_subject'
    ) AS primary_divinities,
    (
        SELECT GROUP_CONCAT(t.canonical_name, ', ')
        FROM study_taxonomy_mappings m
        JOIN taxonomy_terms t ON m.term_id = t.id
        WHERE m.study_id = s.id AND m.relevance_level = 'materially_discussed'
    ) AS discussed_elements
FROM studies s
JOIN series ser ON s.series_id = ser.id;

-- ----------------------------------------------------------------------------
-- 6. AUTOMATIC FTS SYNCHRONIZATION TRIGGERS
-- ----------------------------------------------------------------------------

-- Trigger to sync slide OCR to FTS
CREATE TRIGGER IF NOT EXISTS trg_slides_fts_insert AFTER INSERT ON study_slides BEGIN
    INSERT INTO study_slides_fts(slide_id, study_id, slide_number, slide_title, caption, extracted_ocr_text, cleaned_text)
    VALUES (NEW.id, NEW.study_id, NEW.slide_number, NEW.slide_title, NEW.caption, NEW.extracted_ocr_text, NEW.cleaned_text);
END;

CREATE TRIGGER IF NOT EXISTS trg_slides_fts_update AFTER UPDATE ON study_slides BEGIN
    DELETE FROM study_slides_fts WHERE slide_id = OLD.id;
    INSERT INTO study_slides_fts(slide_id, study_id, slide_number, slide_title, caption, extracted_ocr_text, cleaned_text)
    VALUES (NEW.id, NEW.study_id, NEW.slide_number, NEW.slide_title, NEW.caption, NEW.extracted_ocr_text, NEW.cleaned_text);
END;

CREATE TRIGGER IF NOT EXISTS trg_slides_fts_delete AFTER DELETE ON study_slides BEGIN
    DELETE FROM study_slides_fts WHERE slide_id = OLD.id;
END;
