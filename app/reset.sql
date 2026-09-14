-- =============================================================================
-- FIVE METAL MASONRY (FMM) - CANONICAL DATABASE RESET SCRIPT (reset.sql)
-- Database Engine: DuckDB / ANSI SQL Compatible
-- Architecture: Medallion 3-Tier (Bronze Raw, Silver ODS, Gold Operations)
-- =============================================================================
-- PURPOSE:
-- Cleanses all studies, slides, OCR runs, AI candidate proposals, user telemetry,
-- audit ledgers, download receipts, and study child mappings, while STRICTLY PRESERVING:
--   ✓ Sole System Administrator: ananth.seetharaman@gmail.com (Active Patron)
--   ✓ series                   (The 19 thematic monograph series)
--   ✓ taxonomy_types           (6 canonical taxonomy categories)
--   ✓ taxonomy_terms           (41 canonical Sanskrit iconography terms)
--   ✓ term_aliases             (80 multilingual aliases & transliterations)
--   ✓ places                   (Sacred temple sites & geographic provenance)
--   ✓ periods_dynasties        (Dynastic chronologies: Chola, Pallava, etc.)
--   ✓ dictionary_entries       (Agamic & Sanskrit lexical definitions)
--   ✓ doc_ref_catalog          (Primary shastric source texts: Kashyapa Shilpa Shastra, etc.)
--   ✓ param_config             (System configuration parameters & Google OAuth credentials)
--
-- EXECUTION SAFETY:
-- Deletions are ordered strictly in reverse foreign-key dependency order.
-- =============================================================================

-- 1. 🟡 GOLD LAYER: Operational Records, Telemetry, Subscriptions, Users
DELETE FROM user_downloads;
DELETE FROM user_subscriptions WHERE user_id != 'usr_admin_ananth';
DELETE FROM premium_download_requests;
DELETE FROM user_behavior_logs;
DELETE FROM audit_logs;
DELETE FROM users WHERE email != 'ananth.seetharaman@gmail.com';

-- 2. 🟤 BRONZE LAYER & CHILD FOREIGN TABLES
-- Delete OCR data referencing study_slides
DELETE FROM slide_ocr_data;

-- Delete AI metadata proposals referencing study_slides & studies
DELETE FROM ai_metadata_proposals;

-- Delete study taxonomy mappings referencing studies & taxonomy_terms
DELETE FROM study_taxonomy_mappings;

-- Delete content access rules referencing studies
DELETE FROM content_access_rules;

-- Delete study slides referencing studies
DELETE FROM study_slides;

-- Delete studies referencing series
DELETE FROM studies;

-- Verification
SELECT 'users' AS table_name, count(*) AS remaining_rows FROM users
UNION ALL
SELECT 'studies', count(*) FROM studies
UNION ALL
SELECT 'study_slides', count(*) FROM study_slides
UNION ALL
SELECT 'slide_ocr_data', count(*) FROM slide_ocr_data
UNION ALL
SELECT 'ai_metadata_proposals', count(*) FROM ai_metadata_proposals
UNION ALL
SELECT 'study_taxonomy_mappings', count(*) FROM study_taxonomy_mappings
UNION ALL
SELECT 'content_access_rules', count(*) FROM content_access_rules;
