-- =============================================================================
-- FIVE METAL MASONRY (FMM) - CANONICAL DATABASE RESET SCRIPT (reset.sql)
-- Database Engine: DuckDB / ANSI SQL Compatible
-- Architecture: Medallion 3-Tier (Bronze Raw, Silver ODS, Gold Operations)
-- =============================================================================
-- PURPOSE:
-- Cleanses all dynamic operational records, telemetry streams, user identity
-- sessions, transaction receipts, audit ledgers, and machine OCR proposals,
-- while STRICTLY PRESERVING all static reference knowledge base tables:
--   ✓ series                   (The 19 thematic monograph series)
--   ✓ studies                  (The 7 curated scholarly monographs)
--   ✓ taxonomy_types           (6 canonical taxonomy categories)
--   ✓ taxonomy_terms           (37 canonical Sanskrit iconography terms)
--   ✓ term_aliases             (72 multilingual aliases & transliterations)
--   ✓ study_taxonomy_mappings  (Curated relational study knowledge links)
--   ✓ places                   (Sacred temple sites & geographic provenance)
--   ✓ periods_dynasties        (Dynastic chronologies: Chola, Pallava, etc.)
--   ✓ dictionary_entries       (Agamic & Sanskrit lexical definitions)
--   ✓ doc_ref_catalog          (Primary shastric source texts: Kashyapa Shilpa Shastra, etc.)
--   ✓ param_config             (System configuration parameters & Google OAuth credentials)
--   ✓ content_access_rules     (Curated DRM access tiers per study)
--
-- EXECUTION SAFETY:
-- Deletions are ordered strictly in reverse foreign-key dependency order
-- to ensure zero relational integrity constraint violations.
-- =============================================================================

BEGIN TRANSACTION;

-- =============================================================================
-- 1. 🟡 GOLD LAYER: User Activity, Identity, Subscriptions & Telemetry
-- =============================================================================

-- 1.1 Purge High-Resolution 300 DPI Download Receipts (T_SYST_DOWNLOADS)
-- References: users(id), studies(id)
DELETE FROM user_downloads;

-- 1.2 Purge User Memberships & Subscriptions (T_SYST_SUBSCRIPTIONS)
-- References: users(id)
DELETE FROM user_subscriptions;

-- 1.3 Purge Premium GPay Monograph Unlock Requests (T_SYST_DOWNLOAD_REQ)
-- References: studies(id)
DELETE FROM premium_download_requests;

-- 1.4 Purge Real-Time Telemetry & Search Behavior Stream (T_SYST_BEHAVIOR_LOG)
DELETE FROM user_behavior_logs;

-- 1.6 Purge User Accounts & Session Profiles (T_SYST_USERS)
-- Note: All child records in user_downloads and user_subscriptions are purged above.
-- If you wish to preserve the primary system administrator, replace with:
--   DELETE FROM users WHERE email NOT IN ('ananth.seetharaman@gmail.com', 'curator@fivemetalmasonry.com');
DELETE FROM users;


-- =============================================================================
-- 2. BRONZE LAYER: AI Ingestion Proposals & Ingested Plates
-- =============================================================================
-- Note: slide_ocr_data and content_access_rules were removed in the schema
-- refactor (OCR fields + access tier now live on study_slides / studies).

-- 2.2 Purge Autonomous AI Metadata & Taxonomy Proposals (T_RAW_AI_PROPOSALS)
-- References: study_slides(id)
DELETE FROM ai_metadata_proposals;

-- 2.3 Purge Ingested Test Study Slides / Plates (T_RAW_STUDY_SLIDES)
DELETE FROM study_slides;


-- =============================================================================
-- 3. 🔵 SILVER LAYER: Curated Reference & Knowledge Base (PRESERVED)
-- =============================================================================
-- The following static / reference tables are deliberately NOT deleted:
--   • series                   (Monograph Series - PRESERVED)
--   • studies                  (Curated Research Studies - PRESERVED)
--   • study_taxonomy_mappings  (Study-Taxonomy Links - PRESERVED)
--   • taxonomy_types           (Taxonomy Categories - PRESERVED)
--   • taxonomy_terms           (Canonical Iconography Terms - PRESERVED)
--   • term_aliases             (Multilingual Aliases - PRESERVED)
--   • places                   (Temple Sites & Locations - PRESERVED)
--   • periods_dynasties        (Dynastic Eras - PRESERVED)
--   • dictionary_entries       (Agamic Sanskrit Lexicon - PRESERVED)
--   • doc_ref_catalog          (Primary Shastra Texts - PRESERVED)
--   • param_config             (Application Config & OAuth - PRESERVED)
--   • content_access_rules     (Granular DRM Rules - PRESERVED)

COMMIT;

-- =============================================================================
-- 4. VERIFICATION & SANITY CHECK QUERY
-- =============================================================================
-- Run this query to inspect table row counts and verify the clean reset:
--
-- SELECT 'series' AS table_name, COUNT(*) AS remaining_rows FROM series
-- UNION ALL SELECT 'studies', COUNT(*) FROM studies
-- UNION ALL SELECT 'study_taxonomy_mappings', COUNT(*) FROM study_taxonomy_mappings
-- UNION ALL SELECT 'taxonomy_types', COUNT(*) FROM taxonomy_types
-- UNION ALL SELECT 'taxonomy_terms', COUNT(*) FROM taxonomy_terms
-- UNION ALL SELECT 'term_aliases', COUNT(*) FROM term_aliases
-- UNION ALL SELECT 'places', COUNT(*) FROM places
-- UNION ALL SELECT 'periods_dynasties', COUNT(*) FROM periods_dynasties
-- UNION ALL SELECT 'dictionary_entries', COUNT(*) FROM dictionary_entries
-- UNION ALL SELECT 'doc_ref_catalog', COUNT(*) FROM doc_ref_catalog
-- UNION ALL SELECT 'param_config', COUNT(*) FROM param_config
-- UNION ALL SELECT 'content_access_rules', COUNT(*) FROM content_access_rules
-- UNION ALL SELECT 'study_slides', COUNT(*) FROM study_slides
-- UNION ALL SELECT 'slide_ocr_data', COUNT(*) FROM slide_ocr_data
-- UNION ALL SELECT 'ai_metadata_proposals', COUNT(*) FROM ai_metadata_proposals
-- UNION ALL SELECT 'users', COUNT(*) FROM users
-- UNION ALL SELECT 'user_subscriptions', COUNT(*) FROM user_subscriptions
-- UNION ALL SELECT 'user_downloads', COUNT(*) FROM user_downloads
-- UNION ALL SELECT 'premium_download_requests', COUNT(*) FROM premium_download_requests
-- UNION ALL SELECT 'user_behavior_logs', COUNT(*) FROM user_behavior_logs
-- UNION ALL SELECT 'audit_logs', COUNT(*) FROM audit_logs
-- ORDER BY remaining_rows DESC;
