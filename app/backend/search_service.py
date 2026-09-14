import re
from typing import List, Dict, Any, Optional
from database import get_db
from embedding_service import (
    normalize_indic_phonetics,
    strip_diacritics,
    text_to_dense_vector,
    cosine_similarity,
    trigram_similarity
)

STOP_WORDS = {
    "hi", "hello", "hey", "the", "a", "an", "in", "on", "of", "to", "is", "it", "at", 
    "by", "for", "with", "and", "or", "as", "be", "this", "that", "from", "are", "was",
    "so", "no", "not", "but", "what", "all", "were", "when", "we", "there", "can", "if",
    "into", "do", "how", "why", "who", "which", "where"
}

def matches_term(query: str, target: str) -> bool:
    """
    Precision word-boundary matching to prevent false-positive substring hits
    (e.g., preventing 'hi' from matching 'Mushika', 'Shikhara', 'this', or 'which').
    """
    if not query or not target:
        return False
    q = query.strip().lower()
    t = target.strip().lower()
    if q in STOP_WORDS:
        return False
    if q == t:
        return True
    if len(q) <= 3:
        # Require exact whole word for short tokens
        return bool(re.search(rf"\b{re.escape(q)}\b", t))
    else:
        # Require word boundary prefix or whole word
        return bool(re.search(rf"\b{re.escape(q)}", t))


def extract_context_snippet(text: str, query: str, window_before: int = 35, window_after: int = 65) -> str:
    """
    Extracts an authentic contextual snippet around the matched query phrase or terms.
    E.g. for query '32 forms', extracts:
    "...occur within the well-known 32 forms of Gaṇeśa (covered earlier) and are revisited here specifically..."
    """
    if not text:
        return ""
    text_clean = text.strip()
    text_lower = text_clean.lower()
    q_clean = query.strip().lower()

    # 1. Exact phrase match
    pos = text_lower.find(q_clean)
    match_len = len(q_clean)

    # 2. Normalized Indic match if not found
    if pos == -1:
        q_norm = normalize_indic_phonetics(q_clean)
        text_norm = normalize_indic_phonetics(text_clean)
        pos = text_norm.find(q_norm)
        match_len = len(q_norm)

    # 3. Primary query words fallback
    if pos == -1:
        words = [w for w in q_clean.split() if len(w) >= 2 and w not in STOP_WORDS]
        for w in words:
            p = text_lower.find(w)
            if p != -1:
                pos = p
                match_len = len(w)
                break

    if pos == -1:
        return text_clean[:130] + ("..." if len(text_clean) > 130 else "")

    # Natural start word boundary
    start = max(0, pos - window_before)
    if start > 0:
        sp = text_clean.find(" ", start)
        if sp != -1 and sp < pos:
            start = sp + 1

    # Natural end word boundary
    end = min(len(text_clean), pos + match_len + window_after)
    if end < len(text_clean):
        sp = text_clean.rfind(" ", pos + match_len, end)
        if sp != -1 and sp > pos:
            end = sp

    snippet = text_clean[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text_clean):
        snippet = snippet + "..."
    return snippet


def scholar_search(
    query: Optional[str] = None,
    series_id: Optional[int] = None,
    divinity: Optional[str] = None,
    element: Optional[str] = None,
    access_level: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Executes 'Search Like a Scholar' with multi-tiered hybrid retrieval:
      1. Indic Phonetic Normalization (e.g. 'MOOSHIKA' -> 'musika' matching 'Mūṣika')
      2. 128-dimensional Subword Dense Vector Embedding Cosine Similarity
      3. Character Trigram Fuzzy Similarity
      4. Deep Slide OCR & Parchment Text Hit (with word boundaries)
      5. Affinity Score & Confidence Score Re-ranking:
         - Requires authentic Theme Affinity (> 0%) when searching.
         - Stray OCR substring hits without iconographic affinity are excluded.
    """
    conn = get_db()
    q_clean = query.strip().lower() if query else ""
    q_norm = normalize_indic_phonetics(q_clean) if q_clean else ""

    # Stop words / Conversational greetings check
    if q_clean and q_clean in STOP_WORDS:
        conn.close()
        return {
            "query": query,
            "total_results": 0,
            "limit": limit,
            "offset": offset,
            "results": [],
            "message": f"'{query}' is a non-iconographic stop word. Search for divinities (e.g., Ganesha, Shiva), postures (e.g., Lalitasana), or gestures (e.g., Abhaya Mudra)."
        }

    # Dense vector only for iconographic queries of 4+ characters
    q_vec = text_to_dense_vector(q_clean) if (q_clean and len(q_clean) >= 4 and q_clean not in STOP_WORDS) else None

    # Conceptual Intent Expansion for high-level scholarly categories
    CONCEPT_MAP = {
        "mudra": ["mudra", "hasta", "gesture", "shikhara", "abhaya", "varada", "gajahasta", "chin", "dhyana"],
        "mudras": ["mudra", "hasta", "gesture", "shikhara", "abhaya", "varada", "gajahasta"],
        "hasta": ["hasta", "mudra", "gesture", "hand"],
        "hastas": ["hasta", "mudra", "gesture", "hand"],
        "asana": ["asana", "asina", "lalitasana", "tribhanga", "sthanaka", "posture", "sitting", "standing"],
        "posture": ["asana", "asina", "lalitasana", "tribhanga", "sthanaka", "posture"],
        "postures": ["asana", "asina", "lalitasana", "tribhanga", "sthanaka", "posture"],
        "vahana": ["vahana", "mount", "musika", "mooshika", "nandi", "garuda"],
        "mount": ["vahana", "mount", "musika", "mooshika", "nandi"],
        "weapon": ["ayudha", "weapon", "trishula", "chakra", "bow", "arrow", "ankusha", "pasha"],
        "ayudha": ["ayudha", "weapon", "trishula", "chakra", "bow", "arrow", "ankusha", "pasha"]
    }
    
    expanded_queries = [q_clean]
    if q_clean in CONCEPT_MAP:
        expanded_queries = list(set(expanded_queries + CONCEPT_MAP[q_clean]))

    # 1. Resolve query against controlled taxonomy & aliases using precision word matching
    matched_terms = []
    seen_tids = {}
    if q_clean:
        tax_rows = conn.execute("""
            SELECT t.id, t.canonical_name, t.iast_name, tt.name AS category,
                   COALESCE(a.alias, '') AS alias, COALESCE(a.alias_type, '') AS alias_type,
                   t.embedding
            FROM taxonomy_terms t
            JOIN taxonomy_types tt ON t.taxonomy_type_id = tt.id
            LEFT JOIN term_aliases a ON a.term_id = t.id
        """).fetchall()

        for r in tax_rows:
            tid, cname, iast, cat, alias, atype, stored_emb = r
            cname_str = str(cname or "")
            iast_str = str(iast or "")
            alias_str = str(alias or "")

            cname_norm = normalize_indic_phonetics(cname_str)
            iast_norm = normalize_indic_phonetics(iast_str)
            alias_norm = normalize_indic_phonetics(alias_str)

            match_reason = None
            match_weight = 0.0

            # Tier 1: Direct word / prefix match (not internal random substring)
            if matches_term(q_clean, cname_str) or (iast_str and matches_term(q_clean, iast_str)) or (alias_str and matches_term(q_clean, alias_str)):
                match_reason = f"Exact/scholarly match on '{alias_str or cname_str}'"
                match_weight = 1.0

            # Tier 2: Indic Phonetic Normalization (e.g. mooshika -> musika)
            elif q_norm and len(q_norm) >= 3 and (
                q_norm == cname_norm or 
                q_norm == iast_norm or 
                (alias_norm and q_norm == alias_norm) or
                matches_term(q_norm, cname_norm) or
                (alias_norm and matches_term(q_norm, alias_norm))
            ):
                match_reason = f"Phonetic Transliteration: '{query}' -> '{cname_str}' ({iast_str})"
                match_weight = 0.95

            # Tier 3: Trigram Fuzzy Matching (only for significant queries of 4+ chars)
            elif len(q_clean) >= 4 and alias_str and trigram_similarity(q_clean, alias_str) >= 0.65:
                match_reason = f"Fuzzy similarity match on '{alias_str}'"
                match_weight = 0.85

            # Tier 4: Dense Subword Vector Cosine Similarity using permanently stored DuckDB embedding
            elif q_vec:
                term_vec = stored_emb if stored_emb is not None else text_to_dense_vector(f"{cname_str} {iast_str} {alias_str}")
                sim = cosine_similarity(q_vec, term_vec)
                if sim >= 0.75:
                    match_reason = f"Dense Vector Semantic Affinity ({round(sim*100, 1)}%) with '{cname_str}'"
                    match_weight = float(sim)

            if match_reason:
                if tid not in seen_tids or match_weight > seen_tids[tid]["weight"]:
                    seen_tids[tid] = {
                        "term_id": tid,
                        "canonical_name": cname_str,
                        "iast_name": iast_str,
                        "category": cat,
                        "matched_alias": alias_str,
                        "match_reason": match_reason,
                        "weight": match_weight
                    }

        matched_terms = list(seen_tids.values())

    matched_term_ids = [t["term_id"] for t in matched_terms]

    # 2. Fetch published studies with filters
    base_sql = """
        SELECT s.id, s.slug, s.title, s.subtitle, s.study_number,
               ser.id AS series_id, ser.name AS series_name,
               s.access_level, s.cover_image_url, s.total_slides,
               s.summary_markdown, s.embedding
        FROM studies s
        JOIN series ser ON s.series_id = ser.id
        WHERE s.status = 'published'
    """
    params = []
    if series_id:
        base_sql += " AND s.series_id = ?"
        params.append(series_id)
    if access_level and access_level != 'all':
        base_sql += " AND s.access_level = ?"
        params.append(access_level)

    studies_rows = conn.execute(base_sql, params).fetchall()

    results = []

    for row in studies_rows:
        sid, slug, title, subtitle, study_num, ser_id, ser_name, acc_lvl, cover_img, tot_slides, summary, study_emb = row
        match_cues = []
        affinity_pts = 0.0
        confidence_pts = 0.0
        text_pts = 0.0

        title_norm = normalize_indic_phonetics(title)
        subtitle_norm = normalize_indic_phonetics(subtitle or "")

        # 1. Title / Subtitle Match (Word Boundary & Phonetic)
        if q_clean and (matches_term(q_clean, title) or (q_norm and len(q_norm) >= 3 and matches_term(q_norm, title_norm))):
            text_pts += 1.0
            affinity_pts = max(affinity_pts, 0.95)
            match_cues.append(f"Title match on '{title}'")
        elif q_clean and subtitle and (matches_term(q_clean, subtitle) or (q_norm and len(q_norm) >= 3 and matches_term(q_norm, subtitle_norm))):
            text_pts += 0.6
            affinity_pts = max(affinity_pts, 0.75)
            match_cues.append(f"Subtitle context match on '{subtitle}'")

        # 2. Taxonomy Mappings Match
        mappings = []
        if matched_term_ids:
            placeholders = ",".join(["?"] * len(matched_term_ids))
            mappings = conn.execute(f"""
                SELECT m.term_id, m.relevance_level, m.confidence_score, m.slide_numbers,
                       t.canonical_name, t.iast_name, tt.name AS category
                FROM study_taxonomy_mappings m
                JOIN taxonomy_terms t ON m.term_id = t.id
                JOIN taxonomy_types tt ON t.taxonomy_type_id = tt.id
                WHERE m.study_id = ? AND m.term_id IN ({placeholders})
            """, [sid, *matched_term_ids]).fetchall()

            for m in mappings:
                mtid, mrel, mconf, mslides, cname, iast, cat = m
                term_meta = seen_tids.get(mtid, {})
                reason = term_meta.get("match_reason", "")
                
                if mrel == 'primary_subject':
                    affinity_pts = max(affinity_pts, 1.0)
                    match_cues.append(f"Taxonomy Primary Theme: {cat} = '{cname}' ({iast}) [{reason}]")
                elif mrel == 'materially_discussed':
                    affinity_pts = max(affinity_pts, 0.88)
                    match_cues.append(f"Taxonomy Material Discussion: {cat} = '{cname}' ({iast}) in Slides {mslides} [{reason}]")
                else:
                    affinity_pts = max(affinity_pts, 0.60)
                    match_cues.append(f"Taxonomy Secondary Reference: {cat} = '{cname}' ({iast})")

                confidence_pts = max(confidence_pts, float(mconf or 0.95))

        # 3. Slide Embedded Corpus Search & Context Extraction
        slides_data = conn.execute("""
            SELECT id, slide_number, slide_title, image_url, caption,
                   COALESCE(cleaned_text, extracted_ocr_text) AS text,
                   embedding
            FROM study_slides
            WHERE study_id = ?
            ORDER BY slide_number ASC
        """, (sid,)).fetchall()

        # Collect slide numbers mapped from matched taxonomy terms
        mapped_slide_numbers = set()
        if mappings:
            for m in mappings:
                mslides_str = m[3]
                if mslides_str:
                    try:
                        import json
                        sl_nums = json.loads(mslides_str)
                        mapped_slide_numbers.update(sl_nums)
                    except Exception:
                        pass

        slide_hits = []
        slides_list = []
        best_hit_snippet = None

        for sl in slides_data:
            sl_id, sl_num, sl_title, sl_img, sl_caption, sl_text, sl_emb = sl
            has_hit = False
            hit_detail = ""
            matched_cue_term = q_clean

            if q_clean and sl_text and q_clean not in STOP_WORDS:
                text_lower = sl_text.lower()
                text_norm = normalize_indic_phonetics(sl_text)
                title_lower = (sl_title or "").lower()

                # A. Direct Phrase Match in Embedded Corpus (e.g. "32 forms")
                if q_clean in text_lower or (len(q_clean) >= 3 and q_clean in title_lower):
                    has_hit = True
                    hit_detail = f"Direct match in text corpus: '{q_clean}'"
                    affinity_pts = max(affinity_pts, 0.88)
                    confidence_pts = max(confidence_pts, 0.98)
                    matched_cue_term = q_clean

                # B. Word-boundary Match across Expanded Conceptual Queries
                if not has_hit:
                    for eq in expanded_queries:
                        if eq in STOP_WORDS:
                            continue
                        if matches_term(eq, text_lower):
                            has_hit = True
                            hit_detail = f"Corpus textual hit matching scholarly concept '{eq}'"
                            affinity_pts = max(affinity_pts, 0.80)
                            confidence_pts = max(confidence_pts, 0.95)
                            matched_cue_term = eq
                            break

                # C. Indic Phonetic Transliteration Match
                if not has_hit and q_norm and len(q_norm) >= 3 and matches_term(q_norm, text_norm):
                    has_hit = True
                    hit_detail = f"Phonetic transliteration hit: '{query}' -> '{q_norm}'"
                    affinity_pts = max(affinity_pts, 0.75)
                    confidence_pts = max(confidence_pts, 0.92)
                    matched_cue_term = q_clean

                # D. Dense Vector Cosine Similarity against Slide Embedding
                if not has_hit and q_vec:
                    s_vec = sl_emb if sl_emb is not None else text_to_dense_vector(f"{sl_title} {sl_text}")
                    sim = cosine_similarity(q_vec, s_vec)
                    if sim >= 0.52:
                        has_hit = True
                        hit_detail = f"Dense Vector Semantic Affinity ({round(sim * 100, 1)}%)"
                        affinity_pts = max(affinity_pts, float(sim))
                        confidence_pts = max(confidence_pts, 0.90)
                        matched_cue_term = q_clean

                # E. Taxonomy Mappings for this slide
                if not has_hit and sl_num in mapped_slide_numbers:
                    has_hit = True
                    hit_detail = "Direct taxonomy element illustrated in slide"
                    affinity_pts = max(affinity_pts, 0.70)
                    confidence_pts = max(confidence_pts, 0.92)

            # Generate accurate context window snippet around matched term
            sl_snippet = extract_context_snippet(sl_text, matched_cue_term) if (has_hit and sl_text) else (sl_text[:140] + "..." if sl_text else "")

            if has_hit:
                slide_hits.append(sl_num)
                if not best_hit_snippet:
                    best_hit_snippet = sl_snippet

            slides_list.append({
                "slide_id": sl_id,
                "slide_number": sl_num,
                "slide_title": sl_title,
                "image_url": sl_img,
                "caption": sl_caption,
                "has_term_hit": has_hit,
                "hit_detail": hit_detail,
                "snippet": sl_snippet,
                "matched_snippet": sl_snippet if has_hit else None
            })

        if slide_hits:
            text_pts = max(text_pts, min(0.98, 0.5 + 0.25 * len(slide_hits)))
            if best_hit_snippet:
                match_cues.insert(0, f'Embedded Text Corpus Hit (Plate {slide_hits[0]}): "{best_hit_snippet}"')
            else:
                match_cues.append(f"Deep Slide OCR Hit: Identified in Slide(s) {slide_hits}")
            if confidence_pts == 0:
                confidence_pts = 0.95

        # 4. Dense Vector Semantic Affinity Score using permanently stored DuckDB embedding
        if q_vec:
            s_vec = study_emb if study_emb is not None else text_to_dense_vector(f"{title} {subtitle or ''} {summary or ''}")
            study_sim = cosine_similarity(q_vec, s_vec)
            if study_sim >= 0.75 and not match_cues:
                match_cues.append(f"Dense Vector Semantic Affinity: {round(study_sim * 100, 1)}% cosine similarity")
                affinity_pts = max(affinity_pts, study_sim)
            elif match_cues and study_sim >= 0.45:
                match_cues.append(f"Dense Vector Subword Affinity: {round(study_sim * 100, 1)}% cosine similarity")

        # Filter by divinity or element if specified in params
        if divinity and divinity.lower() not in title.lower():
            has_div = conn.execute("""
                SELECT 1 FROM study_taxonomy_mappings m
                JOIN taxonomy_terms t ON m.term_id = t.id
                WHERE m.study_id = ? AND LOWER(t.canonical_name) = ?
            """, (sid, divinity.lower())).fetchone()
            if not has_div:
                continue

        # If user searched but nothing matched in this study, skip
        if q_clean and not match_cues:
            continue

        # HONOURING SCHOLARLY THEME AFFINITY:
        # If the user searched for an iconographic term, the monograph MUST possess
        # authentic thematic affinity (> 0%). Stray body text words without any
        # iconography relevance are strictly excluded.
        if q_clean and affinity_pts < 0.20:
            continue

        # Default scores when browsing without query
        if not q_clean:
            affinity_pts = 1.0
            confidence_pts = 1.0
            text_pts = 1.0
            match_cues.append("Featured in Archive Collection")

        # Compute Scholar Composite Scores
        if confidence_pts == 0:
            confidence_pts = 0.90

        final_affinity_score = round(affinity_pts * 100, 1)
        final_confidence_score = round(confidence_pts * 100, 1)
        final_rank_score = round((affinity_pts * 50) + (confidence_pts * 30) + (text_pts * 20), 1)

        # Determine subscription requirement from access_level
        needs_sub = acc_lvl in ('scholar_tier', 'premium', 'member_only')

        results.append({
            "study_id": sid,
            "slug": slug,
            "title": title,
            "subtitle": subtitle,
            "study_number": study_num,
            "series_name": ser_name,
            "access_level": acc_lvl,
            "cover_image_url": cover_img,
            "total_slides": tot_slides,
            "summary_markdown": summary,
            "affinity_score": final_affinity_score,
            "confidence_score": final_confidence_score,
            "rank_score": final_rank_score,
            "match_cues": match_cues,
            "requires_subscription": needs_sub,
            "matched_corpus_snippet": best_hit_snippet if slide_hits else None,
            "matched_slide_number": slide_hits[0] if slide_hits else 1,
            "slides": slides_list
        })

    # Sort results by Scholar Composite Rank Score (highest first)
    results.sort(key=lambda x: x["rank_score"], reverse=True)

    conn.close()

    total_count = len(results)
    paginated_results = results[offset:offset + limit]

    return {
        "query": query,
        "total_results": total_count,
        "limit": limit,
        "offset": offset,
        "results": paginated_results
    }

def get_autocomplete(prefix: str, limit: int = 8) -> List[Dict[str, Any]]:
    """Provides autocomplete suggestions across canonical terms, aliases, and phonetic variants."""
    if not prefix or len(prefix.strip()) < 1:
        return []

    p_clean = prefix.strip().lower()
    if p_clean in STOP_WORDS:
        return []

    conn = get_db()
    p_norm = normalize_indic_phonetics(p_clean)
    suggestions = []
    seen = set()

    # 1. Match Taxonomy Terms (Exact & Phonetic)
    terms = conn.execute("""
        SELECT t.canonical_name, t.iast_name, tt.name AS category, t.slug
        FROM taxonomy_terms t
        JOIN taxonomy_types tt ON t.taxonomy_type_id = tt.id
    """).fetchall()

    for r in terms:
        cname, iast, cat, slug = r
        cname_str = str(cname or "")
        iast_str = str(iast or "")
        cname_norm = normalize_indic_phonetics(cname_str)
        
        if cname_str.lower().startswith(p_clean) or (p_norm and len(p_norm) >= 3 and cname_norm.startswith(p_norm)):
            if cname_str not in seen:
                seen.add(cname_str)
                suggestions.append({
                    "type": "taxonomy_term",
                    "label": f"{cname_str} ({iast_str})" if iast_str else cname_str,
                    "term": cname_str,
                    "category": cat
                })
                if len(suggestions) >= limit:
                    break

    # 2. Match Aliases
    if len(suggestions) < limit:
        aliases = conn.execute("""
            SELECT a.alias, t.canonical_name, tt.name AS category
            FROM term_aliases a
            JOIN taxonomy_terms t ON a.term_id = t.id
            JOIN taxonomy_types tt ON t.taxonomy_type_id = tt.id
        """).fetchall()

        for r in aliases:
            alias_str, cname_str, cat = r
            alias_norm = normalize_indic_phonetics(alias_str)
            if alias_str.lower().startswith(p_clean) or (p_norm and len(p_norm) >= 3 and alias_norm.startswith(p_norm)):
                key = f"{alias_str}->{cname_str}"
                if key not in seen:
                    seen.add(key)
                    suggestions.append({
                        "type": "alias",
                        "label": f"{alias_str} → {cname_str}",
                        "term": alias_str,
                        "category": cat
                    })
                    if len(suggestions) >= limit:
                        break

    conn.close()
    return suggestions[:limit]
