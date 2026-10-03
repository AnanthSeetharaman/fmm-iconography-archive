"""
Five Metal Masonry (FMM) Iconography Archive
Centralized Curatorial CRUD & Audit Service
Provides full Create, Read, Update, Delete with persistent audit logging,
relational integrity guards, foreign-key resolution, and cascade deletion.
"""

import uuid
import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from database import get_db

# ---------------------------------------------------------------------------
# MEDALLION ENTITY CONFIGURATION (20 DuckDB Tables)
# ---------------------------------------------------------------------------
ENTITY_CONFIG = {
    "param_config": {
        "table": "param_config",
        "pk": "id",
        "pk_type": "str",
        "layer": "syst",
        "label": "T_SYST_PARAM_CONFIG (Application Configuration)",
        "fields": [
            "param_group", "param_key", "param_value", "value_type",
            "description", "is_sensitive"
        ],
        "search_cols": ["param_group", "param_key", "param_value", "description"]
    },

    # ── BRONZE LAYER: T_RAW (Append-only / Engine Ingest) ──────────────────
    "study_slides": {
        "table": "study_slides",
        "pk": "id",
        "pk_type": "str",
        "layer": "raw",
        "label": "T_RAW_PLATES (Plates: image, OCR, tags, visibility)",
        "fields": [
            "study_id", "slide_number", "slide_title", "image_url",
            "thumbnail_url", "caption", "extracted_ocr_text", "cleaned_text",
            "visual_elements_summary", "sort_order", "is_public", "tags",
            "ocr_engine", "word_count", "confidence_avg"
        ],
        "search_cols": ["slide_title", "caption", "extracted_ocr_text", "cleaned_text", "tags"]
    },
    "ai_metadata_proposals": {
        "table": "ai_metadata_proposals",
        "pk": "id",
        "pk_type": "str",
        "layer": "raw",
        "label": "T_RAW_AI_PROPOSALS (AI Taxonomy Proposals)",
        "fields": [
            "study_id", "slide_id", "slide_number", "suggested_taxonomy_type",
            "raw_suggested_term", "mapped_term_id", "confidence_score",
            "evidence_snippet", "review_status", "curator_notes"
        ],
        "search_cols": ["raw_suggested_term", "evidence_snippet", "curator_notes"]
    },

    # ── SILVER LAYER: T_ODS (Curated Canonical Knowledge) ──────────────────
    "series": {
        "table": "series",
        "pk": "id",
        "pk_type": "int",
        "layer": "ods",
        "label": "T_ODS_SERIES (Curatorial Series)",
        "fields": ["slug", "name", "scope", "status", "cover_image_url", "sort_order"],
        "search_cols": ["name", "scope", "slug"]
    },
    "studies": {
        "table": "studies",
        "pk": "id",
        "pk_type": "str",
        "layer": "ods",
        "label": "T_ODS_STUDIES (Research Monographs)",
        "fields": [
            "slug", "title", "subtitle", "study_number", "series_id",
            "content_type", "access_level", "status", "summary_markdown",
            "original_publication_date", "cover_image_url", "total_slides",
            "search_keywords", "curator_notes"
        ],
        "search_cols": ["title", "subtitle", "slug", "search_keywords"]
    },
    "dictionary": {
        "table": "dictionary_entries",
        "pk": "id",
        "pk_type": "str",
        "layer": "ods",
        "label": "T_ODS_DICTIONARY (IAST Sanskrit Glossary)",
        "fields": [
            "slug", "headword", "iast_headword", "part_of_speech",
            "etymology", "definition", "extended_notes"
        ],
        "search_cols": ["headword", "iast_headword", "definition", "etymology"]
    },
    "catalog": {
        "table": "doc_ref_catalog",
        "pk": "doc_ref",
        "pk_type": "str",
        "layer": "ods",
        "label": "T_ODS_DOC_CATALOG (Primary Text Reference Catalog)",
        "fields": [
            "doc_ref", "doc_name", "corpus", "section",
            "author_or_tradition", "language", "applicability_to_iconography"
        ],
        "search_cols": ["doc_ref", "doc_name", "corpus", "author_or_tradition", "applicability_to_iconography"]
    },
    "taxonomy_terms": {
        "table": "taxonomy_terms",
        "pk": "id",
        "pk_type": "str",
        "layer": "ods",
        "label": "T_ODS_TAXONOMY_TERMS (Canonical Mudras, Asanas, Vahanas)",
        "fields": [
            "canonical_name", "iast_name", "slug", "taxonomy_type_id",
            "parent_id", "description", "dictionary_entry_id", "place_id",
            "period_id", "is_active", "display_order"
        ],
        "search_cols": ["canonical_name", "iast_name", "slug", "description"]
    },
    "taxonomy_types": {
        "table": "taxonomy_types",
        "pk": "id",
        "pk_type": "int",
        "layer": "ods",
        "label": "T_ODS_TAXONOMY_TYPES (Taxonomy Classification Types)",
        "fields": ["code", "name", "description"],
        "search_cols": ["code", "name", "description"]
    },
    "term_aliases": {
        "table": "term_aliases",
        "pk": "id",
        "pk_type": "str",
        "layer": "ods",
        "label": "T_ODS_TERM_ALIASES (Multilingual Spellings & Script Variants)",
        "fields": ["term_id", "alias", "alias_type", "is_searchable"],
        "search_cols": ["alias", "alias_type"]
    },
    "places": {
        "table": "places",
        "pk": "id",
        "pk_type": "str",
        "layer": "ods",
        "label": "T_ODS_PLACES (Temples & Sites Registry)",
        "fields": [
            "slug", "name", "native_name", "temple_name", "deity_enshrined",
            "tradition", "town_city", "district", "state", "country", "notes"
        ],
        "search_cols": ["name", "native_name", "temple_name", "deity_enshrined", "town_city", "state"]
    },
    "periods": {
        "table": "periods_dynasties",
        "pk": "id",
        "pk_type": "int",
        "layer": "ods",
        "label": "T_ODS_PERIODS (Dynasties & Historical Eras)",
        "fields": ["slug", "name", "time_span", "region", "description"],
        "search_cols": ["name", "time_span", "region", "description"]
    },
    "study_taxonomy_mappings": {
        "table": "study_taxonomy_mappings",
        "pk": "id",
        "pk_type": "str",
        "layer": "ods",
        "label": "T_ODS_STUDY_TAXONOMY (Verified Taxonomy Bridges)",
        "fields": [
            "study_id", "term_id", "relevance_level", "confidence_score",
            "slide_numbers", "curator_verified", "curator_notes"
        ],
        "search_cols": ["relevance_level", "curator_notes"]
    },

    # ── GOLD LAYER: T_SYST (System Operations, Telemetry, IAM) ─────────────
    "users": {
        "table": "users",
        "pk": "id",
        "pk_type": "str",
        "layer": "syst",
        "label": "T_SYST_USERS (Scholar & Staff IAM)",
        "fields": ["email", "full_name", "avatar_url", "role", "google_sub"],
        "search_cols": ["email", "full_name", "role"]
    },
    "user_subscriptions": {
        "table": "user_subscriptions",
        "pk": "id",
        "pk_type": "str",
        "layer": "syst",
        "label": "T_SYST_SUBSCRIPTIONS (Subscription Contracts)",
        "fields": [
            "user_id", "tier", "status", "billing_cycle", "amount_inr",
            "payment_due_amount", "last_payment_date", "next_billing_date", "payment_method"
        ],
        "search_cols": ["user_id", "tier", "status"]
    },
    "user_downloads": {
        "table": "user_downloads",
        "pk": "id",
        "pk_type": "str",
        "layer": "syst",
        "label": "T_SYST_DOWNLOADS (Licensed High-Res Receipts)",
        "fields": [
            "user_id", "study_id", "slide_id", "license_ref",
            "resolution", "ip_address", "downloaded_at"
        ],
        "search_cols": ["user_id", "study_id", "license_ref"]
    },
    "premium_download_requests": {
        "table": "premium_download_requests",
        "pk": "id",
        "pk_type": "str",
        "layer": "syst",
        "label": "T_SYST_DOWNLOAD_REQ (GPay Payment Verifications)",
        "fields": [
            "study_id", "user_email", "payment_method", "transaction_ref",
            "amount_inr", "status"
        ],
        "search_cols": ["study_id", "user_email", "transaction_ref", "status"]
    },
    "user_behavior_logs": {
        "table": "user_behavior_logs",
        "pk": "id",
        "pk_type": "str",
        "layer": "syst",
        "label": "T_SYST_BEHAVIOR_LOG (Scholarly Telemetry Event Stream)",
        "fields": [
            "user_id", "session_id", "event_type", "resource_id",
            "event_payload_json", "ip_address", "user_agent"
        ],
        "search_cols": ["event_type", "resource_id", "user_id"]
    },
    "audit_logs": {
        "table": "audit_logs",
        "pk": "id",
        "pk_type": "str",
        "layer": "syst",
        "label": "T_SYST_AUDIT_LOG (Immutable Mutation Trail)",
        "fields": [
            "table_name", "record_id", "action", "user_email",
            "user_role", "changed_fields_json"
        ],
        "search_cols": ["table_name", "record_id", "action", "user_email"]
    }
}

def _log_audit(conn, table_name: str, record_id: str, action: str,
               user_email: str, user_role: str,
               changed_fields: Optional[Dict[str, Any]] = None,
               prev_state: Optional[Dict[str, Any]] = None,
               new_state: Optional[Dict[str, Any]] = None):
    audit_id = f"aud_{uuid.uuid4().hex[:12]}"
    conn.execute("""
        INSERT INTO audit_logs (
            id, table_name, record_id, action, user_email, user_role,
            changed_fields_json, previous_state_json, new_state_json, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (
        audit_id,
        table_name,
        str(record_id),
        action,
        user_email or "curator",
        user_role or "curator",
        json.dumps(changed_fields or {}, default=str),
        json.dumps(prev_state or {}, default=str),
        json.dumps(new_state or {}, default=str)
    ))

def get_fk_options(field_name: str) -> List[Dict[str, Any]]:
    """
    Returns id/label pairs for foreign key dropdowns in the CRUD studio.
    """
    conn = get_db()
    opts = []
    try:
        if field_name == "series_id":
            rows = conn.execute("SELECT id, name FROM series ORDER BY sort_order ASC, name ASC").fetchall()
            opts = [{"value": r[0], "label": f"{r[1]} (Series #{r[0]})"} for r in rows]
        elif field_name == "study_id":
            rows = conn.execute("SELECT id, title, study_number FROM studies ORDER BY study_number ASC, title ASC").fetchall()
            opts = [{"value": r[0], "label": f"{r[1]} ({r[2] or r[0]})"} for r in rows]
        elif field_name == "slide_id":
            rows = conn.execute("SELECT id, slide_title, slide_number, study_id FROM study_slides ORDER BY study_id, slide_number").fetchall()
            opts = [{"value": r[0], "label": f"Slide {r[2]}: {r[1] or 'Untitled'} [{r[3]}]"} for r in rows]
        elif field_name == "taxonomy_type_id":
            rows = conn.execute("SELECT id, name, code FROM taxonomy_types ORDER BY name ASC").fetchall()
            opts = [{"value": r[0], "label": f"{r[1]} ({r[2]})"} for r in rows]
        elif field_name == "term_id" or field_name == "parent_id":
            rows = conn.execute("SELECT id, canonical_name, iast_name FROM taxonomy_terms ORDER BY canonical_name ASC").fetchall()
            opts = [{"value": r[0], "label": f"{r[1]} ({r[2] or r[0]})"} for r in rows]
        elif field_name == "dictionary_entry_id":
            rows = conn.execute("SELECT id, headword, iast_headword FROM dictionary_entries ORDER BY headword ASC").fetchall()
            opts = [{"value": r[0], "label": f"{r[1]} ({r[2] or ''})"} for r in rows]
        elif field_name == "place_id":
            rows = conn.execute("SELECT id, name, town_city FROM places ORDER BY name ASC").fetchall()
            opts = [{"value": r[0], "label": f"{r[1]} - {r[2] or ''}"} for r in rows]
        elif field_name == "period_id":
            rows = conn.execute("SELECT id, name, time_span FROM periods_dynasties ORDER BY name ASC").fetchall()
            opts = [{"value": r[0], "label": f"{r[1]} ({r[2] or ''})"} for r in rows]
        elif field_name == "user_id":
            rows = conn.execute("SELECT id, email, full_name, role FROM users ORDER BY email ASC").fetchall()
            opts = [{"value": r[0], "label": f"{r[1]} ({r[2] or r[3]})"} for r in rows]
    finally:
        conn.close()
    return opts

def list_records(entity: str, page: int = 1, page_size: int = 10,
                 search: Optional[str] = None, sort_by: Optional[str] = None,
                 sort_dir: str = "desc") -> Dict[str, Any]:
    if entity not in ENTITY_CONFIG:
        raise ValueError(f"Unknown entity: {entity}")
    
    cfg = ENTITY_CONFIG[entity]
    table = cfg["table"]
    pk = cfg["pk"]
    
    conn = get_db()
    where_clauses = []
    params = []
    
    if search:
        search_terms = []
        for col in cfg["search_cols"]:
            search_terms.append(f"LOWER(CAST({col} AS VARCHAR)) LIKE ?")
            params.append(f"%{search.lower()}%")
        where_clauses.append(f"({' OR '.join(search_terms)})")
    
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    
    # Count total
    count_sql = f"SELECT COUNT(*) FROM {table} {where_sql}"
    total_rows = conn.execute(count_sql, params).fetchone()[0]
    
    # Sort
    valid_cols = cfg["fields"] + [pk]
    if "created_at" in valid_cols:
        default_sort = "created_at"
    elif "sort_order" in valid_cols:
        default_sort = "sort_order"
    else:
        default_sort = pk
        
    order_col = sort_by if sort_by and sort_by in valid_cols else default_sort
    order_direction = "ASC" if sort_dir.lower() == "asc" else "DESC"
    
    offset = (page - 1) * page_size
    query_sql = f"""
        SELECT * FROM {table}
        {where_sql}
        ORDER BY {order_col} {order_direction}
        LIMIT ? OFFSET ?
    """
    query_params = params + [page_size, offset]
    
    cursor = conn.execute(query_sql, query_params)
    cols = [desc[0] for desc in cursor.description]
    rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
    conn.close()
    
    total_pages = (total_rows + page_size - 1) // page_size if total_rows > 0 else 1
    
    return {
        "entity": entity,
        "table": table,
        "page": page,
        "page_size": page_size,
        "total_rows": total_rows,
        "total_pages": total_pages,
        "rows": rows
    }

def get_record(entity: str, record_id: Any) -> Optional[Dict[str, Any]]:
    if entity not in ENTITY_CONFIG:
        raise ValueError(f"Unknown entity: {entity}")
    
    cfg = ENTITY_CONFIG[entity]
    table = cfg["table"]
    pk = cfg["pk"]
    
    conn = get_db()
    cursor = conn.execute(f"SELECT * FROM {table} WHERE {pk} = ?", (record_id,))
    cols = [desc[0] for desc in cursor.description]
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    return dict(zip(cols, row))

def create_record(entity: str, data: Dict[str, Any],
                  user_email: str = "curator", user_role: str = "curator") -> Dict[str, Any]:
    if entity not in ENTITY_CONFIG:
        raise ValueError(f"Unknown entity: {entity}")
    
    cfg = ENTITY_CONFIG[entity]
    table = cfg["table"]
    pk = cfg["pk"]
    
    conn = get_db()
    
    # Generate PK if string type and not provided
    if cfg["pk_type"] == "str" and pk not in data:
        if entity == "studies":
            prefix = "s_"
            base = re.sub(r'[^a-zA-Z0-9_]', '', data.get("slug", "study").lower())[:20]
            data[pk] = f"{prefix}{base}_{uuid.uuid4().hex[:4]}"
        elif entity == "dictionary":
            prefix = "dic_"
            base = re.sub(r'[^a-zA-Z0-9_]', '', data.get("slug", "entry").lower())[:20]
            data[pk] = f"{prefix}{base}_{uuid.uuid4().hex[:4]}"
        elif entity == "param_config":
            data[pk] = f"cfg_{uuid.uuid4().hex[:6]}"
        elif entity == "catalog":
            count = conn.execute("SELECT COUNT(*) FROM doc_ref_catalog").fetchone()[0]
            data[pk] = f"DOC_REF_{count + 1:03d}"
        else:
            data[pk] = f"{entity[:4]}_{uuid.uuid4().hex[:8]}"
    elif cfg["pk_type"] == "int" and pk not in data:
        max_id = conn.execute(f"SELECT COALESCE(MAX({pk}), 0) FROM {table}").fetchone()[0]
        data[pk] = max_id + 1
        
    record_id = data[pk]
    
    cols = []
    vals = []
    placeholders = []
    
    # Check what columns table actually has
    table_cols = [c[0] for c in conn.execute(f"DESCRIBE {table}").fetchall()]
    
    for f in cfg["fields"]:
        if f in data:
            val = data[f]
            if f == "is_sensitive":
                if isinstance(val, str):
                    val = val.lower() in ("true", "1", "yes")
                else:
                    val = bool(val)
            cols.append(f)
            vals.append(val)
            placeholders.append("?")
            
    cols.append(pk)
    vals.append(record_id)
    placeholders.append("?")
    
    # Add audit fields if table supports them
    if "created_at" in table_cols:
        cols.append("created_at")
        placeholders.append("CURRENT_TIMESTAMP")
    if "created_by" in table_cols:
        cols.append("created_by")
        vals.append(user_email)
        placeholders.append("?")
    if "updated_at" in table_cols:
        cols.append("updated_at")
        placeholders.append("CURRENT_TIMESTAMP")
    if "updated_by" in table_cols:
        cols.append("updated_by")
        vals.append(user_email)
        placeholders.append("?")
        
    sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"
    conn.execute(sql, vals)
    
    # Audit logging
    _log_audit(conn, table, str(record_id), "CREATE", user_email, user_role,
               changed_fields=data, prev_state=None, new_state=data)
    
    conn.close()
    return get_record(entity, record_id)

def update_record(entity: str, record_id: Any, data: Dict[str, Any],
                  user_email: str = "curator", user_role: str = "curator") -> Dict[str, Any]:
    if entity not in ENTITY_CONFIG:
        raise ValueError(f"Unknown entity: {entity}")
    
    cfg = ENTITY_CONFIG[entity]
    table = cfg["table"]
    pk = cfg["pk"]
    
    prev = get_record(entity, record_id)
    if not prev:
        raise ValueError(f"Record {record_id} not found in {table}")
        
    conn = get_db()
    table_cols = [c[0] for c in conn.execute(f"DESCRIBE {table}").fetchall()]
    
    set_clauses = []
    vals = []
    changed_fields = {}
    
    for f in cfg["fields"]:
        if f in data:
            val = data[f]
            if f == "is_sensitive":
                if isinstance(val, str):
                    val = val.lower() in ("true", "1", "yes")
                else:
                    val = bool(val)
            prev_val = prev.get(f)
            
            # Handle empty string from form vs None in DB
            if val == "" and prev_val is None:
                val = None
                
            # Handle numeric types (DuckDB returns int/float, UI sends str)
            if prev_val is not None and isinstance(val, str):
                if isinstance(prev_val, int):
                    try: val = int(val)
                    except ValueError: pass
                elif isinstance(prev_val, float):
                    try: val = float(val)
                    except ValueError: pass

            if val != prev_val:
                set_clauses.append(f"{f} = ?")
                vals.append(val)
                changed_fields[f] = {"old": prev_val, "new": val}
            
    if not set_clauses:
        conn.close()
        return prev  # Nothing changed
        
    # Update audit fields if supported
    if "updated_at" in table_cols:
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")
    if "updated_by" in table_cols:
        set_clauses.append("updated_by = ?")
        vals.append(user_email)
    
    vals.append(record_id)
    sql = f"UPDATE {table} SET {', '.join(set_clauses)} WHERE {pk} = ?"
    conn.execute(sql, vals)
    
    # Audit logging
    _log_audit(conn, table, str(record_id), "UPDATE", user_email, user_role,
               changed_fields=changed_fields, prev_state=prev, new_state=data)
    
    conn.close()
    return get_record(entity, record_id)

def get_cascade_impact(entity: str, record_id: Any) -> Dict[str, Any]:
    """
    Returns a tree of all dependent records that would be affected
    if the given record is deleted. Does NOT perform any deletions.
    """
    if entity not in ENTITY_CONFIG:
        raise ValueError(f"Unknown entity: {entity}")

    cfg = ENTITY_CONFIG[entity]
    table = cfg["table"]
    pk = cfg["pk"]
    conn = get_db()

    # Fetch the record label for display
    cursor = conn.execute(f"SELECT * FROM {table} WHERE {pk} = ?", (record_id,))
    cols = [d[0] for d in cursor.description]
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Record not found in {table}: {record_id}")

    rec = dict(zip(cols, row))
    label = (rec.get("name") or rec.get("title") or rec.get("canonical_name") or
             rec.get("headword") or rec.get("doc_name") or rec.get("slide_title") or
             rec.get("email") or str(record_id))

    children = []
    total_cascade = 0

    if entity == "series":
        n_studies = conn.execute("SELECT COUNT(*) FROM studies WHERE series_id = ?", (record_id,)).fetchone()[0]
        if n_studies > 0:
            study_ids = [r[0] for r in conn.execute("SELECT id FROM studies WHERE series_id = ?", (record_id,)).fetchall()]
            study_children = []
            for sid in study_ids:
                n_slides = conn.execute("SELECT COUNT(*) FROM study_slides WHERE study_id = ?", (sid,)).fetchone()[0]
                n_taxmap = conn.execute("SELECT COUNT(*) FROM study_taxonomy_mappings WHERE study_id = ?", (sid,)).fetchone()[0]
                n_proposals = conn.execute("SELECT COUNT(*) FROM ai_metadata_proposals WHERE study_id = ?", (sid,)).fetchone()[0]
                if n_slides > 0:
                    study_children.append({
                        "table": "study_slides",
                        "count": n_slides,
                        "children": []
                    })
                    total_cascade += n_slides
                if n_taxmap > 0:
                    study_children.append({"table": "study_taxonomy_mappings", "count": n_taxmap, "children": []})
                    total_cascade += n_taxmap
                if n_proposals > 0:
                    study_children.append({"table": "ai_metadata_proposals", "count": n_proposals, "children": []})
                    total_cascade += n_proposals
            children.append({"table": "studies", "count": n_studies, "children": study_children})
            total_cascade += n_studies

    elif entity == "studies":
        n_slides = conn.execute("SELECT COUNT(*) FROM study_slides WHERE study_id = ?", (record_id,)).fetchone()[0]
        n_taxmap = conn.execute("SELECT COUNT(*) FROM study_taxonomy_mappings WHERE study_id = ?", (record_id,)).fetchone()[0]
        n_proposals = conn.execute("SELECT COUNT(*) FROM ai_metadata_proposals WHERE study_id = ?", (record_id,)).fetchone()[0]
        if n_slides > 0:
            children.append({
                "table": "study_slides",
                "count": n_slides,
                "children": []
            })
            total_cascade += n_slides
        if n_taxmap > 0:
            children.append({"table": "study_taxonomy_mappings", "count": n_taxmap, "children": []})
            total_cascade += n_taxmap
        if n_proposals > 0:
            children.append({"table": "ai_metadata_proposals", "count": n_proposals, "children": []})
            total_cascade += n_proposals

    elif entity == "study_slides":
        n_proposals = conn.execute("SELECT COUNT(*) FROM ai_metadata_proposals WHERE slide_id = ?", (record_id,)).fetchone()[0]
        if n_proposals > 0:
            children.append({"table": "ai_metadata_proposals", "count": n_proposals, "children": []})
            total_cascade += n_proposals

    elif entity == "taxonomy_terms":
        n_aliases = conn.execute("SELECT COUNT(*) FROM term_aliases WHERE term_id = ?", (record_id,)).fetchone()[0]
        n_mappings = conn.execute("SELECT COUNT(*) FROM study_taxonomy_mappings WHERE term_id = ?", (record_id,)).fetchone()[0]
        n_child_terms = conn.execute("SELECT COUNT(*) FROM taxonomy_terms WHERE parent_id = ?", (record_id,)).fetchone()[0]
        if n_aliases > 0:
            children.append({"table": "term_aliases", "count": n_aliases, "children": []})
            total_cascade += n_aliases
        if n_mappings > 0:
            children.append({"table": "study_taxonomy_mappings", "count": n_mappings, "children": []})
            total_cascade += n_mappings
        if n_child_terms > 0:
            children.append({"table": "taxonomy_terms (sub-terms)", "count": n_child_terms, "children": []})
            total_cascade += n_child_terms

    elif entity == "taxonomy_types":
        n_terms = conn.execute("SELECT COUNT(*) FROM taxonomy_terms WHERE taxonomy_type_id = ?", (record_id,)).fetchone()[0]
        if n_terms > 0:
            children.append({"table": "taxonomy_terms", "count": n_terms, "children": []})
            total_cascade += n_terms

    elif entity == "dictionary":
        n_terms = conn.execute("SELECT COUNT(*) FROM taxonomy_terms WHERE dictionary_entry_id = ?", (record_id,)).fetchone()[0]
        if n_terms > 0:
            children.append({"table": "taxonomy_terms (referencing glossary)", "count": n_terms, "children": []})
            total_cascade += n_terms

    elif entity == "places":
        n_terms = conn.execute("SELECT COUNT(*) FROM taxonomy_terms WHERE place_id = ?", (record_id,)).fetchone()[0]
        if n_terms > 0:
            children.append({"table": "taxonomy_terms (referencing site)", "count": n_terms, "children": []})
            total_cascade += n_terms

    elif entity == "periods":
        n_terms = conn.execute("SELECT COUNT(*) FROM taxonomy_terms WHERE period_id = ?", (record_id,)).fetchone()[0]
        if n_terms > 0:
            children.append({"table": "taxonomy_terms (referencing dynasty)", "count": n_terms, "children": []})
            total_cascade += n_terms

    elif entity == "users":
        n_subs = conn.execute("SELECT COUNT(*) FROM user_subscriptions WHERE user_id = ?", (record_id,)).fetchone()[0]
        n_downs = conn.execute("SELECT COUNT(*) FROM user_downloads WHERE user_id = ?", (record_id,)).fetchone()[0]
        n_logs = conn.execute("SELECT COUNT(*) FROM user_behavior_logs WHERE user_id = ?", (record_id,)).fetchone()[0]
        if n_subs > 0:
            children.append({"table": "user_subscriptions", "count": n_subs, "children": []})
            total_cascade += n_subs
        if n_downs > 0:
            children.append({"table": "user_downloads", "count": n_downs, "children": []})
            total_cascade += n_downs
        if n_logs > 0:
            children.append({"table": "user_behavior_logs", "count": n_logs, "children": []})
            total_cascade += n_logs

    conn.close()
    return {
        "entity": entity,
        "table": table,
        "record_id": str(record_id),
        "record_label": label,
        "children": children,
        "total_cascade_deletes": total_cascade
    }

def delete_record(entity: str, record_id: Any, cascade: bool = False,
                  user_email: str = "curator", user_role: str = "curator") -> Dict[str, Any]:
    """
    Deletes a record. If cascade=False and child records depend on it,
    aborts and raises ValueError with dependency summary.
    If cascade=True, deletes dependent records atomically.
    """
    if entity not in ENTITY_CONFIG:
        raise ValueError(f"Unknown entity: {entity}")
    
    cfg = ENTITY_CONFIG[entity]
    table = cfg["table"]
    pk = cfg["pk"]
    
    prev = get_record(entity, record_id)
    if not prev:
        raise ValueError(f"Record '{record_id}' not found in {table}")

    impact = get_cascade_impact(entity, record_id)
    total_children = impact.get("total_cascade_deletes", 0)

    if total_children > 0 and not cascade:
        breakdown = ", ".join([f"{c['count']} in {c['table']}" for c in impact.get("children", [])])
        raise ValueError(
            f"Relational Guard Alert: Cannot delete {entity} '{record_id}' because {total_children} dependent records exist ({breakdown}). "
            f"Please confirm cascade deletion to remove this record and all its child references."
        )

    conn = get_db()
    deleted_counts = {table: 1}

    # Execute cascade deletions
    if entity == "series":
        study_ids = [r[0] for r in conn.execute("SELECT id FROM studies WHERE series_id = ?", (record_id,)).fetchall()]
        for sid in study_ids:
            slide_ids = [r[0] for r in conn.execute("SELECT id FROM study_slides WHERE study_id = ?", (sid,)).fetchall()]
            for slid in slide_ids:
                conn.execute("DELETE FROM ai_metadata_proposals WHERE slide_id = ?", (slid,))
            conn.execute("DELETE FROM study_slides WHERE study_id = ?", (sid,))
            conn.execute("DELETE FROM study_taxonomy_mappings WHERE study_id = ?", (sid,))
            conn.execute("DELETE FROM ai_metadata_proposals WHERE study_id = ?", (sid,))
        conn.execute("DELETE FROM studies WHERE series_id = ?", (record_id,))

    elif entity == "studies":
        slide_ids = [r[0] for r in conn.execute("SELECT id FROM study_slides WHERE study_id = ?", (record_id,)).fetchall()]
        for slid in slide_ids:
            conn.execute("DELETE FROM ai_metadata_proposals WHERE slide_id = ?", (slid,))
        conn.execute("DELETE FROM study_slides WHERE study_id = ?", (record_id,))
        conn.execute("DELETE FROM study_taxonomy_mappings WHERE study_id = ?", (record_id,))
        conn.execute("DELETE FROM ai_metadata_proposals WHERE study_id = ?", (record_id,))

    elif entity == "study_slides":
        conn.execute("DELETE FROM ai_metadata_proposals WHERE slide_id = ?", (record_id,))

    elif entity == "taxonomy_terms":
        conn.execute("DELETE FROM term_aliases WHERE term_id = ?", (record_id,))
        conn.execute("DELETE FROM study_taxonomy_mappings WHERE term_id = ?", (record_id,))
        conn.execute("UPDATE taxonomy_terms SET parent_id = NULL WHERE parent_id = ?", (record_id,))

    elif entity == "taxonomy_types":
        conn.execute("UPDATE taxonomy_terms SET taxonomy_type_id = NULL WHERE taxonomy_type_id = ?", (record_id,))

    elif entity == "dictionary":
        conn.execute("UPDATE taxonomy_terms SET dictionary_entry_id = NULL WHERE dictionary_entry_id = ?", (record_id,))

    elif entity == "places":
        conn.execute("UPDATE taxonomy_terms SET place_id = NULL WHERE place_id = ?", (record_id,))

    elif entity == "periods":
        conn.execute("UPDATE taxonomy_terms SET period_id = NULL WHERE period_id = ?", (record_id,))

    elif entity == "users":
        conn.execute("DELETE FROM user_subscriptions WHERE user_id = ?", (record_id,))
        conn.execute("DELETE FROM user_downloads WHERE user_id = ?", (record_id,))
        conn.execute("DELETE FROM user_behavior_logs WHERE user_id = ?", (record_id,))

    # Finally delete the primary record
    conn.execute(f"DELETE FROM {table} WHERE {pk} = ?", (record_id,))

    action_label = "CASCADE_DELETE" if total_children > 0 else "DELETE"
    _log_audit(conn, table, str(record_id), action_label, user_email, user_role,
               changed_fields={"cascade": cascade, "purged_children_count": total_children},
               prev_state=prev, new_state=None)

    conn.close()
    return {
        "status": "success",
        "message": f"Successfully deleted {entity} record '{record_id}'" + (f" and {total_children} cascaded child records." if total_children > 0 else "."),
        "record_id": str(record_id),
        "cascade_applied": cascade,
        "total_purged_children": total_children
    }

def list_audit_logs(limit: int = 50, offset: int = 0,
                    table_name: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db()
    where_sql = "WHERE table_name = ?" if table_name else ""
    params = [table_name] if table_name else []
    
    sql = f"""
        SELECT * FROM audit_logs
        {where_sql}
        ORDER BY timestamp DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    cursor = conn.execute(sql, params)
    cols = [desc[0] for desc in cursor.description]
    logs = [dict(zip(cols, row)) for row in cursor.fetchall()]
    conn.close()
    return logs
