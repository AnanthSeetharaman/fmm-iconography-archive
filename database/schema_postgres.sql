-- ============================================================================
-- FIVE METAL MASONRY (FMM) ICONOGRAPHY ARCHIVE
-- Database Schema for PostgreSQL (Production-Grade, v1.2)
-- 
-- Architecture Principles Implemented:
-- 1. Study as the Fundamental Unit: Multi-slide carousels stored once, discovered via series & taxonomy.
-- 2. Flat Series Structure: 19 peer series (Completed, Ongoing, Upcoming).
-- 3. Three-Layer Indexing Model:
--      Layer 1: Extracted full text from OCR per slide (deep invisible recall).
--      Layer 2: AI-generated metadata proposals with curator approval workflow.
--      Layer 3: Controlled scholarly taxonomy with IAST diacritics & spelling aliases.
-- 4. Scholarly Indexing Rule: Index what is materially discussed (relevance levels).
-- 5. Ranked Search with Reference Cues: Taxonomy matches rank higher than OCR text;
--    transparent match cues explain why results matched.
-- 6. Dictionary Integration: Taxonomy terms link to Dictionary of Iconography definitions.
-- ============================================================================

-- Extensions for Full-Text Search, Trigram Autocomplete, and UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- ----------------------------------------------------------------------------
-- 1. ENUMERATIONS & DOMAINS
-- ----------------------------------------------------------------------------
DO $$ BEGIN
    CREATE TYPE content_type_enum AS ENUM ('study', 'dictionary_entry', 'quiz', 'book');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE access_level_enum AS ENUM ('public', 'member_only');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE series_status_enum AS ENUM ('completed', 'ongoing', 'upcoming');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE study_status_enum AS ENUM ('draft', 'in_review', 'published', 'archived');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE taxonomy_type_enum AS ENUM (
        'divinity',
        'form',
        'iconographic_element',
        'place',
        'period_dynasty',
        'source_reference'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE relevance_level_enum AS ENUM (
        'primary_subject',         -- e.g. Ganesha in "Ganesha Variations"
        'materially_discussed',    -- e.g. Lalitasana, Trishunda, Vamavarta
        'secondary_reference'      -- e.g. Brief comparison to Heramba lion mount
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE proposal_status_enum AS ENUM ('pending', 'approved', 'rejected', 'modified');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE alias_type_enum AS ENUM (
        'spelling_variant',
        'iast_transliteration',
        'english_translation',
        'regional_vernacular',
        'common_misspelling',
        'ocr_artifact'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ----------------------------------------------------------------------------
-- 2. CORE CONTENT STRUCTURE (Series, Content Types, Studies, Slides)
-- ----------------------------------------------------------------------------

-- Editorial Series (Flat structure of all 19 named series)
CREATE TABLE IF NOT EXISTS series (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(150) NOT NULL,
    scope TEXT NOT NULL,
    status series_status_enum NOT NULL DEFAULT 'ongoing',
    cover_image_url VARCHAR(500),
    sort_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Studies: The fundamental unit of the archive (represents one authored carousel)
CREATE TABLE IF NOT EXISTS studies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug VARCHAR(200) UNIQUE NOT NULL,
    title VARCHAR(300) NOT NULL,
    subtitle VARCHAR(500),
    study_number VARCHAR(50),               -- e.g. "Study 001", "Majors 042"
    series_id INT NOT NULL REFERENCES series(id) ON DELETE RESTRICT,
    content_type content_type_enum NOT NULL DEFAULT 'study',
    access_level access_level_enum NOT NULL DEFAULT 'public',
    status study_status_enum NOT NULL DEFAULT 'draft',
    summary_markdown TEXT,
    original_publication_date DATE,
    original_instagram_url VARCHAR(500),
    cover_image_url VARCHAR(500),
    pdf_attachment_url VARCHAR(500),
    total_slides INT NOT NULL DEFAULT 0,
    search_keywords TEXT,                  -- Optional curated search aliases
    curator_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Carousel Slides: Individual slides in the visual study
CREATE TABLE IF NOT EXISTS study_slides (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    study_id UUID NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
    slide_number INT NOT NULL,
    slide_title VARCHAR(300),
    image_url VARCHAR(500) NOT NULL,
    thumbnail_url VARCHAR(500),
    caption TEXT,
    extracted_ocr_text TEXT,               -- Layer 1: Raw / deep OCR text
    cleaned_text TEXT,                     -- Cleaned & spell-corrected text
    visual_elements_summary TEXT,          -- Visual motifs described in slide
    search_vector tsvector,                -- Slide-level full-text vector
    sort_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_study_slide_number UNIQUE (study_id, slide_number)
);

-- Slide OCR Ingestion Details (Layout, word confidence, bounding tokens)
CREATE TABLE IF NOT EXISTS slide_ocr_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slide_id UUID NOT NULL REFERENCES study_slides(id) ON DELETE CASCADE,
    ocr_engine VARCHAR(100) NOT NULL,      -- e.g. "windows_media_ocr", "tesseract_v5"
    language_tag VARCHAR(20) DEFAULT 'en-US',
    raw_ocr_output TEXT NOT NULL,
    normalized_text TEXT NOT NULL,
    word_count INT DEFAULT 0,
    confidence_avg NUMERIC(5, 2),          -- Average OCR confidence 0-100%
    tokens_json JSONB,                     -- Detailed word tokens with bounding boxes {text, x, y, w, h}
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ----------------------------------------------------------------------------
-- 3. DICTIONARY & REFERENCES (Linked to Taxonomy)
-- ----------------------------------------------------------------------------

-- Dictionary of Iconography Entries
CREATE TABLE IF NOT EXISTS dictionary_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug VARCHAR(150) UNIQUE NOT NULL,
    headword VARCHAR(150) NOT NULL,        -- e.g. "Lalitasana"
    iast_headword VARCHAR(150),            -- e.g. "Lalitāsana"
    part_of_speech VARCHAR(50),            -- e.g. "noun, masculine"
    etymology TEXT,                        -- e.g. "From lalita (graceful, charming) + āsana (posture)"
    definition TEXT NOT NULL,              -- Full scholarly definition
    extended_notes TEXT,                   -- Agamic context, iconometric rules
    related_terms TEXT[],                  -- Array of related headwords
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Places / Temples / Shrines (Geographic & Architectural Context)
CREATE TABLE IF NOT EXISTS places (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug VARCHAR(150) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,            -- e.g. "Adi Vinayaka Temple"
    native_name VARCHAR(200),
    temple_name VARCHAR(250),
    deity_enshrined VARCHAR(150),
    tradition VARCHAR(100),                -- e.g. "Vaishnava 108 Divya Desam", "Saiva", "Ganapatya"
    town_city VARCHAR(100) NOT NULL,       -- e.g. "Thilatharpanapuri", "Pune", "Jaipur"
    district VARCHAR(100),
    state VARCHAR(100) NOT NULL,           -- e.g. "Tamil Nadu", "Maharashtra", "Rajasthan"
    country VARCHAR(100) NOT NULL DEFAULT 'India',
    latitude NUMERIC(9, 6),
    longitude NUMERIC(9, 6),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Historical Periods & Dynasties
CREATE TABLE IF NOT EXISTS periods_dynasties (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(150) NOT NULL,            -- e.g. "Chola", "Pallava", "Vijayanagara"
    time_span VARCHAR(100),                -- e.g. "9th - 13th Century CE"
    region VARCHAR(200),                   -- e.g. "Tamil region, South India"
    description TEXT
);

-- Classical Sources & Scholarship References
CREATE TABLE IF NOT EXISTS sources_references (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(300) NOT NULL,           -- e.g. "Elements of Hindu Iconography", "Karanagama"
    author_or_tradition VARCHAR(200),     -- e.g. "T.A. Gopinatha Rao", "Saivagama"
    work_type VARCHAR(100),                -- e.g. "Agama", "Shilpa Shastra", "Museum Catalog", "Monograph"
    publication_year VARCHAR(50),
    citation_details TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Study-to-Source Junction
CREATE TABLE IF NOT EXISTS study_sources (
    study_id UUID NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
    source_id UUID NOT NULL REFERENCES sources_references(id) ON DELETE CASCADE,
    specific_page_or_verse VARCHAR(100),
    citation_context TEXT,
    PRIMARY KEY (study_id, source_id)
);

-- ----------------------------------------------------------------------------
-- 4. LAYER 3: CONTROLLED SCHOLARLY TAXONOMY
-- ----------------------------------------------------------------------------

-- Taxonomy Types Registry
CREATE TABLE IF NOT EXISTS taxonomy_types (
    id SERIAL PRIMARY KEY,
    code taxonomy_type_enum UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT
);

-- Controlled Taxonomy Terms (Supports hierarchical trees like Parent Element -> Child Element)
CREATE TABLE IF NOT EXISTS taxonomy_terms (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    taxonomy_type_id INT NOT NULL REFERENCES taxonomy_types(id) ON DELETE RESTRICT,
    parent_id UUID REFERENCES taxonomy_terms(id) ON DELETE SET NULL,
    canonical_name VARCHAR(200) NOT NULL,  -- e.g. "Lalitasana", "Ganesha", "Caturbhuja"
    iast_name VARCHAR(200),                -- e.g. "Lalitāsana", "Gaṇeśa", "Caturbhuja"
    slug VARCHAR(250) NOT NULL,
    description TEXT,
    dictionary_entry_id UUID REFERENCES dictionary_entries(id) ON DELETE SET NULL,
    place_id UUID REFERENCES places(id) ON DELETE SET NULL,
    period_id INT REFERENCES periods_dynasties(id) ON DELETE SET NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    display_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_taxonomy_term_slug UNIQUE (taxonomy_type_id, slug)
);

-- Term Aliases & Spelling Variants (Synonyms, Transliterations, Misspellings)
CREATE TABLE IF NOT EXISTS term_aliases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    term_id UUID NOT NULL REFERENCES taxonomy_terms(id) ON DELETE CASCADE,
    alias VARCHAR(200) NOT NULL,          -- e.g. "Ganesa", "Ganapati", "Vinayaka", "Pillayar"
    alias_type alias_type_enum NOT NULL DEFAULT 'spelling_variant',
    is_searchable BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Study Taxonomy Mappings (The Curated Indexing Layer)
-- Indexing Rule: Index what is studied or materially discussed, not merely visible
CREATE TABLE IF NOT EXISTS study_taxonomy_mappings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    study_id UUID NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
    term_id UUID NOT NULL REFERENCES taxonomy_terms(id) ON DELETE RESTRICT,
    relevance_level relevance_level_enum NOT NULL DEFAULT 'materially_discussed',
    confidence_score NUMERIC(4, 3) DEFAULT 1.000, -- 1.0 for human-curated
    slide_numbers INT[],                   -- Which slides discuss this feature, e.g. {1, 2, 4}
    curator_verified BOOLEAN NOT NULL DEFAULT TRUE,
    curator_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_study_term UNIQUE (study_id, term_id)
);

-- ----------------------------------------------------------------------------
-- 5. LAYER 2: AI INGESTION PROPOSALS & CURATOR WORKFLOW
-- ----------------------------------------------------------------------------

-- Automated ingestion batches
CREATE TABLE IF NOT EXISTS ingestion_batches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_name VARCHAR(200) NOT NULL,
    source_directory VARCHAR(500),
    total_studies INT DEFAULT 0,
    total_slides INT DEFAULT 0,
    status VARCHAR(50) DEFAULT 'in_progress',
    log_details JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- AI-generated proposals pending curator review
CREATE TABLE IF NOT EXISTS ai_metadata_proposals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_id UUID REFERENCES ingestion_batches(id) ON DELETE SET NULL,
    study_id UUID NOT NULL REFERENCES studies(id) ON DELETE CASCADE,
    slide_id UUID REFERENCES study_slides(id) ON DELETE CASCADE,
    slide_number INT,
    suggested_taxonomy_type taxonomy_type_enum NOT NULL,
    raw_suggested_term VARCHAR(200) NOT NULL,
    mapped_term_id UUID REFERENCES taxonomy_terms(id) ON DELETE SET NULL,
    confidence_score NUMERIC(4, 3) NOT NULL DEFAULT 0.800,
    evidence_snippet TEXT,                 -- Sentence from slide OCR justifying suggestion
    review_status proposal_status_enum NOT NULL DEFAULT 'pending',
    curator_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMPTZ
);

-- ----------------------------------------------------------------------------
-- 6. FULL-TEXT SEARCH AGGREGATION & VECTOR MAINTENANCE
-- ----------------------------------------------------------------------------

-- Add weighted search vector column to studies
ALTER TABLE studies ADD COLUMN IF NOT EXISTS search_vector tsvector;

-- Function to build study-level search vector
-- Weighting Strategy:
-- 'A' (Weight 1.0): Study title, primary divinities, canonical forms
-- 'B' (Weight 0.4): Iconographic elements, dynasties, places, term aliases
-- 'C' (Weight 0.2): Slide titles, study subtitle, curated summary
-- 'D' (Weight 0.1): Extracted OCR text across all slides in the carousel
CREATE OR REPLACE FUNCTION fn_build_study_search_vector(p_study_id UUID)
RETURNS tsvector AS $$
DECLARE
    v_title TEXT;
    v_subtitle TEXT;
    v_summary TEXT;
    v_primary_terms TEXT := '';
    v_secondary_terms TEXT := '';
    v_aliases TEXT := '';
    v_slide_titles TEXT := '';
    v_slide_ocr TEXT := '';
    v_result tsvector;
BEGIN
    -- 1. Study metadata
    SELECT COALESCE(title, ''), COALESCE(subtitle, ''), COALESCE(summary_markdown, '')
    INTO v_title, v_subtitle, v_summary
    FROM studies WHERE id = p_study_id;

    -- 2. Primary taxonomy terms (Divinities, Primary Forms) -> Weight A
    SELECT COALESCE(string_agg(t.canonical_name || ' ' || COALESCE(t.iast_name, ''), ' '), '')
    INTO v_primary_terms
    FROM study_taxonomy_mappings m
    JOIN taxonomy_terms t ON m.term_id = t.id
    WHERE m.study_id = p_study_id AND m.relevance_level = 'primary_subject';

    -- 3. Secondary/Material taxonomy terms (Elements, Places, Dynasties) -> Weight B
    SELECT COALESCE(string_agg(t.canonical_name || ' ' || COALESCE(t.iast_name, ''), ' '), '')
    INTO v_secondary_terms
    FROM study_taxonomy_mappings m
    JOIN taxonomy_terms t ON m.term_id = t.id
    WHERE m.study_id = p_study_id AND m.relevance_level IN ('materially_discussed', 'secondary_reference');

    -- 4. Term Aliases & Alternate Spellings -> Weight B
    SELECT COALESCE(string_agg(a.alias, ' '), '')
    INTO v_aliases
    FROM study_taxonomy_mappings m
    JOIN term_aliases a ON m.term_id = a.term_id
    WHERE m.study_id = p_study_id AND a.is_searchable = TRUE;

    -- 5. Slide titles -> Weight C
    SELECT COALESCE(string_agg(slide_title, ' '), '')
    INTO v_slide_titles
    FROM study_slides WHERE study_id = p_study_id;

    -- 6. Deep OCR text from all slides -> Weight D
    SELECT COALESCE(string_agg(COALESCE(cleaned_text, extracted_ocr_text, ''), ' '), '')
    INTO v_slide_ocr
    FROM study_slides WHERE study_id = p_study_id;

    -- Assemble weighted vector
    v_result := 
        setweight(to_tsvector('english', unaccent(v_title || ' ' || v_primary_terms)), 'A') ||
        setweight(to_tsvector('english', unaccent(v_secondary_terms || ' ' || v_aliases)), 'B') ||
        setweight(to_tsvector('english', unaccent(v_subtitle || ' ' || v_summary || ' ' || v_slide_titles)), 'C') ||
        setweight(to_tsvector('english', unaccent(v_slide_ocr)), 'D');

    RETURN v_result;
END;
$$ LANGUAGE plpgsql;

-- Trigger to re-aggregate study search vector whenever slides or mappings change
CREATE OR REPLACE FUNCTION trg_refresh_study_search_vector()
RETURNS trigger AS $$
DECLARE
    v_study_id UUID;
BEGIN
    IF TG_TABLE_NAME = 'studies' THEN
        v_study_id := NEW.id;
    ELSIF TG_TABLE_NAME = 'study_slides' THEN
        v_study_id := NEW.study_id;
    ELSIF TG_TABLE_NAME = 'study_taxonomy_mappings' THEN
        v_study_id := NEW.study_id;
    END IF;

    UPDATE studies
    SET search_vector = fn_build_study_search_vector(v_study_id),
        updated_at = CURRENT_TIMESTAMP
    WHERE id = v_study_id;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Attach triggers
DROP TRIGGER IF EXISTS trg_update_study_vector_on_slide ON study_slides;
CREATE TRIGGER trg_update_study_vector_on_slide
AFTER INSERT OR UPDATE OF extracted_ocr_text, cleaned_text, slide_title ON study_slides
FOR EACH ROW EXECUTE FUNCTION trg_refresh_study_search_vector();

DROP TRIGGER IF EXISTS trg_update_study_vector_on_mapping ON study_taxonomy_mappings;
CREATE TRIGGER trg_update_study_vector_on_mapping
AFTER INSERT OR UPDATE OR DELETE ON study_taxonomy_mappings
FOR EACH ROW EXECUTE FUNCTION trg_refresh_study_search_vector();

-- ----------------------------------------------------------------------------
-- 7. INDEXES (Full-Text GIN, Trigram pg_trgm, Lookups)
-- ----------------------------------------------------------------------------

-- GIN index for fast full-text search on studies
CREATE INDEX IF NOT EXISTS idx_studies_search_vector ON studies USING GIN(search_vector);

-- GIN index on slide-level OCR text vector
CREATE INDEX IF NOT EXISTS idx_slides_search_vector ON study_slides USING GIN(search_vector);

-- Trigram indexes for typo-tolerant autocomplete on titles and taxonomy terms
CREATE INDEX IF NOT EXISTS idx_studies_title_trgm ON studies USING GIN(title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_taxonomy_canonical_trgm ON taxonomy_terms USING GIN(canonical_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_taxonomy_iast_trgm ON taxonomy_terms USING GIN(iast_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_aliases_trgm ON term_aliases USING GIN(alias gin_trgm_ops);

-- B-Tree lookup indexes
CREATE INDEX IF NOT EXISTS idx_studies_series_id ON studies(series_id);
CREATE INDEX IF NOT EXISTS idx_studies_access_level ON studies(access_level);
CREATE INDEX IF NOT EXISTS idx_studies_status ON studies(status);
CREATE INDEX IF NOT EXISTS idx_slides_study_number ON study_slides(study_id, slide_number);
CREATE INDEX IF NOT EXISTS idx_mappings_study_id ON study_taxonomy_mappings(study_id);
CREATE INDEX IF NOT EXISTS idx_mappings_term_id ON study_taxonomy_mappings(term_id);
CREATE INDEX IF NOT EXISTS idx_proposals_study_id ON ai_metadata_proposals(study_id);
CREATE INDEX IF NOT EXISTS idx_proposals_status ON ai_metadata_proposals(review_status);

-- ----------------------------------------------------------------------------
-- 8. SEARCH & DISCOVERY APIS (Ranked Search & Reference Cues)
-- ----------------------------------------------------------------------------

-- Complete Search Function with "Why Matched" Reference Cues
CREATE OR REPLACE FUNCTION search_archive(
    p_query TEXT,
    p_series_id INT DEFAULT NULL,
    p_divinity_id UUID DEFAULT NULL,
    p_element_id UUID DEFAULT NULL,
    p_place_id UUID DEFAULT NULL,
    p_access_level access_level_enum DEFAULT NULL,
    p_limit INT DEFAULT 20,
    p_offset INT DEFAULT 0
)
RETURNS TABLE (
    study_id UUID,
    slug VARCHAR(200),
    title VARCHAR(300),
    subtitle VARCHAR(500),
    study_number VARCHAR(50),
    series_name VARCHAR(150),
    access_level access_level_enum,
    cover_image_url VARCHAR(500),
    total_slides INT,
    search_score REAL,
    match_cues JSONB,                  -- Explains why this study matched (scholarly reference cues)
    matched_slides INT[]
) AS $$
DECLARE
    v_tsquery tsquery;
BEGIN
    -- Parse query string into flexible tsquery
    IF p_query IS NOT NULL AND TRIM(p_query) <> '' THEN
        v_tsquery := plainto_tsquery('english', unaccent(p_query));
    ELSE
        v_tsquery := NULL;
    END IF;

    RETURN QUERY
    WITH study_matches AS (
        SELECT 
            s.id,
            s.slug,
            s.title,
            s.subtitle,
            s.study_number,
            ser.name AS series_name,
            s.access_level,
            s.cover_image_url,
            s.total_slides,
            CASE 
                WHEN v_tsquery IS NOT NULL THEN ts_rank_cd('{0.1, 0.2, 0.4, 1.0}', s.search_vector, v_tsquery)
                ELSE 1.0
            END AS base_rank,
            -- Check for taxonomy matches
            (
                SELECT jsonb_agg(
                    jsonb_build_object(
                        'type', tt.code,
                        'term', t.canonical_name,
                        'iast', t.iast_name,
                        'relevance', m.relevance_level,
                        'dictionary_link', t.dictionary_entry_id IS NOT NULL
                    )
                )
                FROM study_taxonomy_mappings m
                JOIN taxonomy_terms t ON m.term_id = t.id
                JOIN taxonomy_types tt ON t.taxonomy_type_id = tt.id
                LEFT JOIN term_aliases a ON a.term_id = t.id
                WHERE m.study_id = s.id
                  AND (
                      v_tsquery IS NULL 
                      OR unaccent(t.canonical_name) ILIKE '%' || unaccent(p_query) || '%'
                      OR unaccent(COALESCE(t.iast_name, '')) ILIKE '%' || unaccent(p_query) || '%'
                      OR unaccent(COALESCE(a.alias, '')) ILIKE '%' || unaccent(p_query) || '%'
                  )
            ) AS matched_taxonomy_cues,
            -- Check which individual slides contain the query in extracted OCR text
            (
                SELECT array_agg(sl.slide_number ORDER BY sl.slide_number)
                FROM study_slides sl
                WHERE sl.study_id = s.id
                  AND (
                      v_tsquery IS NOT NULL 
                      AND (
                          sl.search_vector @@ v_tsquery 
                          OR unaccent(COALESCE(sl.cleaned_text, sl.extracted_ocr_text, '')) ILIKE '%' || unaccent(p_query) || '%'
                      )
                  )
            ) AS ocr_slide_matches
        FROM studies s
        JOIN series ser ON s.series_id = ser.id
        WHERE s.status = 'published'
          AND (p_series_id IS NULL OR s.series_id = p_series_id)
          AND (p_access_level IS NULL OR s.access_level = p_access_level)
          AND (
              p_divinity_id IS NULL OR EXISTS (
                  SELECT 1 FROM study_taxonomy_mappings m
                  WHERE m.study_id = s.id AND m.term_id = p_divinity_id
              )
          )
          AND (
              p_element_id IS NULL OR EXISTS (
                  SELECT 1 FROM study_taxonomy_mappings m
                  WHERE m.study_id = s.id AND m.term_id = p_element_id
              )
          )
          AND (
              v_tsquery IS NULL 
              OR s.search_vector @@ v_tsquery
              OR unaccent(s.title) ILIKE '%' || unaccent(p_query) || '%'
          )
    )
    SELECT 
        sm.id,
        sm.slug,
        sm.title,
        sm.subtitle,
        sm.study_number,
        sm.series_name,
        sm.access_level,
        sm.cover_image_url,
        sm.total_slides,
        (sm.base_rank + CASE WHEN sm.matched_taxonomy_cues IS NOT NULL THEN 1.5 ELSE 0.0 END)::REAL AS search_score,
        jsonb_build_object(
            'taxonomy_matches', COALESCE(sm.matched_taxonomy_cues, '[]'::jsonb),
            'ocr_slide_hits', COALESCE(sm.ocr_slide_matches, ARRAY[]::INT[])
        ) AS match_cues,
        sm.ocr_slide_matches AS matched_slides
    FROM study_matches sm
    ORDER BY search_score DESC, sm.title ASC
    LIMIT p_limit OFFSET p_offset;
END;
$$ LANGUAGE plpgsql;

-- Instant Autocomplete & Spelling Tolerance Suggestion Engine
CREATE OR REPLACE FUNCTION get_autocomplete_suggestions(
    p_prefix TEXT,
    p_limit INT DEFAULT 8
)
RETURNS TABLE (
    suggestion_type VARCHAR(50),
    display_label VARCHAR(300),
    iast_label VARCHAR(300),
    slug VARCHAR(250),
    taxonomy_category VARCHAR(100),
    similarity_score REAL
) AS $$
BEGIN
    RETURN QUERY
    -- 1. Exact / Prefix match on Controlled Taxonomy Terms
    SELECT 
        'taxonomy_term'::VARCHAR(50),
        t.canonical_name::VARCHAR(300),
        t.iast_name::VARCHAR(300),
        t.slug::VARCHAR(250),
        tt.name::VARCHAR(100),
        similarity(unaccent(t.canonical_name), unaccent(p_prefix)) AS similarity_score
    FROM taxonomy_terms t
    JOIN taxonomy_types tt ON t.taxonomy_type_id = tt.id
    WHERE t.is_active = TRUE
      AND (
          unaccent(t.canonical_name) ILIKE unaccent(p_prefix) || '%'
          OR unaccent(COALESCE(t.iast_name, '')) ILIKE unaccent(p_prefix) || '%'
          OR similarity(unaccent(t.canonical_name), unaccent(p_prefix)) > 0.3
      )

    UNION ALL

    -- 2. Match on Term Aliases (e.g. user typed "Ganapati" or "mouse" or "asina")
    SELECT 
        'alias'::VARCHAR(50),
        (a.alias || ' → ' || t.canonical_name)::VARCHAR(300),
        t.iast_name::VARCHAR(300),
        t.slug::VARCHAR(250),
        tt.name::VARCHAR(100),
        similarity(unaccent(a.alias), unaccent(p_prefix)) AS similarity_score
    FROM term_aliases a
    JOIN taxonomy_terms t ON a.term_id = t.id
    JOIN taxonomy_types tt ON t.taxonomy_type_id = tt.id
    WHERE a.is_searchable = TRUE
      AND (
          unaccent(a.alias) ILIKE unaccent(p_prefix) || '%'
          OR similarity(unaccent(a.alias), unaccent(p_prefix)) > 0.3
      )

    UNION ALL

    -- 3. Match on Study Titles
    SELECT 
        'study'::VARCHAR(50),
        s.title::VARCHAR(300),
        NULL::VARCHAR(300),
        s.slug::VARCHAR(250),
        'Study'::VARCHAR(100),
        similarity(unaccent(s.title), unaccent(p_prefix)) AS similarity_score
    FROM studies s
    WHERE s.status = 'published'
      AND (
          unaccent(s.title) ILIKE '%' || unaccent(p_prefix) || '%'
          OR similarity(unaccent(s.title), unaccent(p_prefix)) > 0.25
      )

    ORDER BY similarity_score DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;
