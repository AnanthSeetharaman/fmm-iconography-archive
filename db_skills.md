---
name: fmm-database
description: >-
  Authoritative Open Knowledge Framework (OKF) and engineering architecture skill for the Five Metal Masonry (FMM) DuckDB Medallion Database.
  Provides complete technical specifications for all 20 tables across Bronze, Silver, and Gold tiers,
  recursive foreign-key dependency trees, cascading deletion safeguards, Indic phonetic normalization rules,
  128-dimensional dense subword vector ranking, and SQL query patterns.
---

# Five Metal Masonry (FMM) - Database Open Knowledge Framework (OKF)
**Version:** 1.0.0 · **Engine:** DuckDB Columnar OLAP · **Architecture:** 3-Tier Medallion

---

## 🏛️ 1. Medallion Layer Partitioning

The DuckDB database (`backend/data/fmm_archive.duckdb`) is partitioned into 3 distinct medallion layers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 🟤 TIER 1: BRONZE RAW INGESTION                                              │
│ Raw machine OCR outputs, bounding box tokens, high-res photographic plates.  │
│ Tables: study_slides, slide_ocr_data, ai_metadata_proposals                │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Curatorial Verification & OCR Cleanup
┌──────────────────────────────────────▼──────────────────────────────────────┐
│ 🔵 TIER 2: SILVER CURATED ODS (Operational Data Store)                      │
│ Enriched canonical knowledge, Sanskrit glossary, taxonomy relations, DRM.   │
│ Tables: series, studies, taxonomy_types, taxonomy_terms, term_aliases,      │
│         study_taxonomy_mappings, places, periods_dynasties,                 │
│         dictionary_entries, doc_ref_catalog, content_access_rules           │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Identity, Subscriptions & Telemetry
┌──────────────────────────────────────▼──────────────────────────────────────┐
│ 🟡 TIER 3: GOLD SYSTEM OPERATIONS & AUDIT TRAIL                             │
│ IAM user roles, GPay transaction receipts, behavior logs, historical audit. │
│ Tables: users, user_subscriptions, user_downloads,                          │
│         premium_download_requests, user_behavior_logs, audit_logs           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🗄️ 2. Relational Entity Dictionary (20 Tables)

### 2.1 🟤 Bronze Layer
1. **`study_slides` (T_RAW_STUDY_SLIDES)**: High-resolution photographic plates and curated OCR slide transcriptions.
   - PK: `id` (`VARCHAR`)
   - FK: `study_id` $ightarrow$ `studies(id)`
2. **`slide_ocr_data` (T_RAW_SLIDE_OCR)**: Machine engine raw outputs, confidence score averages, and token bounding boxes.
   - PK: `id` (`VARCHAR`)
   - FK: `slide_id` $ightarrow$ `study_slides(id)`
3. **`ai_metadata_proposals` (T_RAW_AI_PROPOSALS)**: Autonomous AI term proposals pending curator review.
   - PK: `id` (`VARCHAR`)
   - FK: `slide_id` $ightarrow$ `study_slides(id)`

### 2.2 🔵 Silver Layer
4. **`series` (T_ODS_SERIES)**: Thematic monograph series (19 series).
   - PK: `id` (`INTEGER`)
5. **`studies` (T_ODS_STUDIES)**: Curated research monographs (7 studies).
   - PK: `id` (`VARCHAR`), FK: `series_id` $ightarrow$ `series(id)`
6. **`taxonomy_types` (T_ODS_TAXONOMY_TYPES)**: 6 high-level categories (Divinity, Murti Form, Element, Place, Period, Tala).
   - PK: `id` (`INTEGER`)
7. **`taxonomy_terms` (T_ODS_TAXONOMY_TERMS)**: Canonical iconography terms with IAST transliteration.
   - PK: `id` (`VARCHAR`), FK: `taxonomy_type_id` $ightarrow$ `taxonomy_types(id)`
8. **`term_aliases` (T_ODS_TERM_ALIASES)**: Multilingual and phonetic aliases (e.g. `Mooshika` $ightarrow$ `Musika`).
   - PK: `id` (`VARCHAR`), FK: `term_id` $ightarrow$ `taxonomy_terms(id)`
9. **`study_taxonomy_mappings` (T_ODS_STUDY_TAXONOMY)**: Verified link between study and taxonomy terms with relevance level.
   - PK: `id` (`VARCHAR`), FKs: `study_id`, `term_id`
10. **`places` (T_ODS_PLACES)**: Sacred temple sites, towns, and districts.
11. **`periods_dynasties` (T_ODS_PERIODS)**: Dynastic chronologies (Pallava, Chola, Vijayanagara).
12. **`dictionary_entries` (T_ODS_DICTIONARY)**: Sanskrit IAST glossary definitions.
13. **`doc_ref_catalog` (T_ODS_DOC_CATALOG)**: Primary textual sources (*Kashyapa Shilpa Shastra*, *Mayamata*).
14. **`content_access_rules` (T_ODS_CONTENT_RULES)**: DRM access tiers per monograph.

### 2.3 🟡 Gold Layer
15. **`users` (T_SYST_USERS)**: IAM identities with Google OAuth roles (`scholar`, `curator`, `admin`).
16. **`user_subscriptions` (T_SYST_SUBSCRIPTIONS)**: Scholar Pro memberships.
17. **`user_downloads` (T_SYST_DOWNLOADS)**: 300 DPI master download audit receipts.
18. **`premium_download_requests` (T_SYST_DOWNLOAD_REQ)**: ₹499 GPay monograph unlock requests.
19. **`user_behavior_logs` (T_SYST_BEHAVIOR_LOG)**: Real-time telemetry search query stream.
20. **`audit_logs` (T_SYST_AUDIT_LOG)**: Curatorial audit ledger capturing old/new JSON state before any delete/update.

---

## 🛡️ 3. Recursive Foreign Key Cascading Safeguards

When deleting records via the Curatorial CRUD suite, the engine enforces strict foreign-key protection:
- **Level 1 (Study Deletion):** Deleting `studies` record recursively warns and purges:
  - `study_slides` (and its dependent `slide_ocr_data` and `ai_metadata_proposals`)
  - `study_taxonomy_mappings`
  - `content_access_rules`
  - `user_downloads`
- **Level 2 (Term Deletion):** Deleting a `taxonomy_terms` record will purge its `term_aliases` and break child taxonomy relations.
- **Level 3 (Safe NULL Updates):** Deleting a `series` warns if active child `studies` exist; deleting a `dictionary_entries` sets `taxonomy_terms.dictionary_entry_id = NULL` safely.

---

## ⚡ 4. Hybrid Retrieval Architecture

```
Query Input
   │
   ├── 1. Indic Phonetic Normalization
   │      - Digraph collapse: 'oo' -> 'u', 'ee' -> 'i'
   │      - Sibilant alignment: 'sh', 'ṣ', 'ś' -> 's'
   │      - Strips diacritics: 'Mūṣika' -> 'musika'
   │
   ├── 2. Subword Dense Vector Cosine Similarity
   │      - 128-dimensional unit vector in character trigram space
   │
   ├── 3. Taxonomy Bridge Disambiguation
   │      - Resolves aliases to canonical Term IDs
   │
   └── 4. Composite Scholar Ranking Formula:
          Rank Score = (Affinity * 50) + (Confidence * 30) + (Text Hit * 20)
```

---

## 💻 5. Standard SQL Query Cookbook

### 5.1 Scholar Thematic Search
```sql
SELECT s.id, s.title, ser.name AS series_name, m.relevance_level, m.slide_numbers
FROM studies s
JOIN series ser ON s.series_id = ser.id
JOIN study_taxonomy_mappings m ON m.study_id = s.id
JOIN taxonomy_terms t ON m.term_id = t.id
WHERE t.id = ? AND s.status = 'published';
```

### 5.2 Fast Autocomplete
```sql
SELECT t.canonical_name, t.iast_name, tt.name AS category
FROM taxonomy_terms t
JOIN taxonomy_types tt ON t.taxonomy_type_id = tt.id
WHERE LOWER(t.canonical_name) LIKE ? OR LOWER(t.iast_name) LIKE ?;
```

### 5.3 Behavior Audit Logging
```sql
INSERT INTO user_behavior_logs (id, user_id, event_type, payload, ip_address, user_agent, created_at)
VALUES (?, ?, 'search_query', ?, ?, ?, CURRENT_TIMESTAMP);
```
