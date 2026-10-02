"""
FMM Study-Grouping Inference Service.

Given a bulk batch of OCR'd plates, infer which STUDY each plate belongs to so a
single upload can be split into multiple studies (series -> studies -> plates).

Design (confirmed with product owner):
  - HEADER-PRIMARY: every plate's header carries the study name; that is the
    primary grouping signal and is always present.
  - TOC-OPTIONAL: a Table-of-Contents plate, when present and complete, is used
    only to canonicalize study titles / numbers / order. Never required
    (ongoing series may have a partial or absent TOC).
  - EXISTING-STUDY ATTACH: a plate header matching a study already in the series
    attaches to that study instead of creating a duplicate (incremental loads).
  - ENGINE: Gemini performs the grouping when a key is reachable; otherwise a
    deterministic text/regex heuristic runs over the already-OCR'd text (incl.
    Windows-OCR text). OCR image->text is a separate, unchanged pipeline.
"""
import re
import json
from typing import List, Dict, Any, Optional

from database import get_db, get_param
from embedding_service import normalize_indic_phonetics, trigram_similarity

try:
    from ocr_service import get_gemini_api_key
except Exception:  # pragma: no cover - defensive
    def get_gemini_api_key() -> str:
        return ""

try:
    from config import LLM_MODEL
except Exception:  # pragma: no cover
    LLM_MODEL = "gemini-2.5-flash"

_FRONT_MATTER_HINTS = (
    "table of contents", "contents", "introduction", "preface",
    "foreword", "acknowledg", "copyright", "title page", "index",
)
_TOC_HINTS = ("table of contents", "contents")


def extract_study_header(raw_text: Optional[str], cleaned_text: Optional[str]) -> str:
    """
    Best-effort extraction of the study-name header from a plate.
    Prefers the first meaningful line of the RAW OCR (which preserves line breaks);
    falls back to the first few words of the cleaned text (whitespace-collapsed).
    """
    candidate = ""
    if raw_text:
        lines = [ln.strip() for ln in re.split(r"[\r\n]+", raw_text) if ln.strip()]
        for ln in lines:
            # Skip pure page/plate markers and lines with too few letters
            if len(re.sub(r"[^A-Za-z]", "", ln)) >= 3:
                candidate = ln
                break
    if not candidate and cleaned_text:
        candidate = " ".join(cleaned_text.split()[:8])

    # Strip leading plate/page/figure markers and trailing page numbers
    candidate = re.sub(r"^(plate|pl\.?|page|p\.?|fig\.?|figure|no\.?)\s*\d+[:.\-)]?\s*", "", candidate, flags=re.I)
    candidate = re.sub(r"\s*\b\d{1,4}\b\s*$", "", candidate)
    candidate = " ".join(candidate.split()[:9])
    return candidate.strip(" .:-\u2013\u2014\u2022\t")


def _norm_key(text: str) -> str:
    """Normalized comparison key for header/title matching."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", normalize_indic_phonetics(text)).strip()


def _is_front_matter(raw_text: str, cleaned_text: str) -> bool:
    blob = f"{raw_text or ''} {cleaned_text or ''}".lower()
    return any(h in blob for h in _FRONT_MATTER_HINTS)


def _parse_toc(plate_text: str) -> List[Dict[str, Any]]:
    """
    Heuristic TOC parse: lines of the form '<Study Title> .... <page>'.
    Returns [{title, start_page}] in document order. Empty when not parseable.
    """
    entries: List[Dict[str, Any]] = []
    if not plate_text:
        return entries
    for ln in re.split(r"[\r\n]+", plate_text):
        ln = ln.strip()
        if not ln:
            continue
        m = re.match(r"^(.*?)[\.\s]{2,}(\d{1,4})\s*$", ln)
        if not m:
            m = re.match(r"^(.+?)\s+(\d{1,4})\s*$", ln)
        if m:
            title = m.group(1).strip(" .:-\u2013\u2014\t")
            if len(re.sub(r"[^A-Za-z]", "", title)) >= 3:
                entries.append({"title": title, "start_page": int(m.group(2))})
    return entries


def _load_existing_studies(conn, series_id: Optional[int]) -> List[Dict[str, Any]]:
    try:
        if series_id is not None:
            rows = conn.execute(
                "SELECT id, title, study_number FROM studies WHERE series_id = ? ORDER BY study_number ASC",
                (series_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, title, study_number FROM studies ORDER BY study_number ASC"
            ).fetchall()
    except Exception:
        rows = []
    return [{"id": r[0], "title": r[1] or "", "study_number": r[2] or "", "key": _norm_key(r[1] or "")} for r in rows]


def _match_existing(header_key: str, existing: List[Dict[str, Any]], threshold: float = 0.62):
    """Return the best existing study matching this header key, or None."""
    if not header_key:
        return None
    best, best_score = None, 0.0
    for st in existing:
        if not st["key"]:
            continue
        if header_key == st["key"] or header_key in st["key"] or st["key"] in header_key:
            return st
        score = trigram_similarity(header_key, st["key"])
        if score > best_score:
            best, best_score = st, score
    return best if best_score >= threshold else None


def _heuristic_grouping(plates: List[Dict[str, Any]], existing: List[Dict[str, Any]], toc: List[Dict[str, Any]]):
    """
    Header-primary deterministic grouping. Returns (groups, engine_used).
    Each group: {study_id?, study_title, study_number, is_front_matter, plate_indices[]}.
    """
    toc_keys = [{"title": t["title"], "key": _norm_key(t["title"])} for t in toc]
    groups: List[Dict[str, Any]] = []
    key_to_group: Dict[str, Dict[str, Any]] = {}
    new_study_seq = 0

    for p in plates:
        header = extract_study_header(p.get("raw_ocr"), p.get("cleaned_ocr"))
        hkey = _norm_key(header)
        front = _is_front_matter(p.get("raw_ocr", ""), p.get("cleaned_ocr", ""))

        # 1. Attach to an existing study in the series
        match = _match_existing(hkey, existing) if hkey else None
        if match:
            gid = f"existing::{match['id']}"
            grp = key_to_group.get(gid)
            if not grp:
                grp = {
                    "study_id": match["id"],
                    "study_title": match["title"],
                    "study_number": match["study_number"],
                    "is_front_matter": False,
                    "plate_indices": [],
                }
                key_to_group[gid] = grp
                groups.append(grp)
            grp["plate_indices"].append(p["index"])
            continue

        # 2. Group with other batch plates sharing the header
        gid = hkey or (f"frontmatter" if front else f"ungrouped::{p['index']}")
        grp = key_to_group.get(gid)
        if not grp:
            # Canonicalize title via TOC when a close match exists
            title = header or ("Front Matter" if front else "Untitled Study")
            if toc_keys and hkey:
                best_t, best_s = None, 0.0
                for t in toc_keys:
                    s = trigram_similarity(hkey, t["key"]) if t["key"] else 0.0
                    if s > best_s:
                        best_t, best_s = t, s
                if best_t and best_s >= 0.6:
                    title = best_t["title"]
            new_study_seq += 1
            grp = {
                "study_id": None,
                "study_title": title,
                "study_number": f"Study {new_study_seq:03d}",
                "is_front_matter": front,
                "plate_indices": [],
            }
            key_to_group[gid] = grp
            groups.append(grp)
        grp["plate_indices"].append(p["index"])

    return groups, "heuristic (fallback)"


def _gemini_grouping(plates, existing, toc):
    """
    Gemini-powered grouping. Returns (groups, 'gemini') or raises/falls through to None.
    """
    api_key = get_gemini_api_key()
    if not api_key:
        return None
    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        headers = [
            {
                "index": p["index"],
                "header": extract_study_header(p.get("raw_ocr"), p.get("cleaned_ocr")),
                "text_preview": (p.get("cleaned_ocr") or "")[:200],
            }
            for p in plates
        ]
        prompt = (
            "You are grouping scanned plates of a scholarly iconography series into STUDIES.\n"
            "Each plate's header carries its study name. Group plates that belong to the same study.\n"
            "Prefer attaching to an EXISTING study title when a plate clearly belongs to it.\n\n"
            f"EXISTING studies in this series: {json.dumps([e['title'] for e in existing])}\n"
            f"Optional table-of-contents titles (may be incomplete): {json.dumps([t['title'] for t in toc])}\n\n"
            f"PLATES: {json.dumps(headers)}\n\n"
            "Return ONLY JSON: {\"groups\":[{\"study_title\":str,\"existing\":bool,"
            "\"is_front_matter\":bool,\"plate_indices\":[int,...]}]}. "
            "Order groups by first appearance; keep every plate index exactly once."
        )
        resp = client.models.generate_content(model=LLM_MODEL, contents=[prompt])
        txt = (resp.text or "").strip()
        txt = re.sub(r"^```(?:json)?\s*", "", txt, flags=re.I)
        txt = re.sub(r"\s*```$", "", txt).strip()
        data = json.loads(txt)

        existing_by_key = {e["key"]: e for e in existing}
        groups = []
        seen = set()
        seq = 0
        for g in data.get("groups", []):
            title = (g.get("study_title") or "Untitled Study").strip()
            idxs = [int(i) for i in g.get("plate_indices", []) if isinstance(i, (int, float, str)) and str(i).isdigit()]
            idxs = [i for i in idxs if i not in seen]
            if not idxs:
                continue
            seen.update(idxs)
            match = existing_by_key.get(_norm_key(title)) or _match_existing(_norm_key(title), existing)
            if match:
                groups.append({
                    "study_id": match["id"], "study_title": match["title"],
                    "study_number": match["study_number"], "is_front_matter": False,
                    "plate_indices": idxs,
                })
            else:
                seq += 1
                groups.append({
                    "study_id": None, "study_title": title,
                    "study_number": f"Study {seq:03d}",
                    "is_front_matter": bool(g.get("is_front_matter")),
                    "plate_indices": idxs,
                })
        # Any plate the model dropped -> append as its own group so nothing is lost
        leftover = [p["index"] for p in plates if p["index"] not in seen]
        if leftover:
            seq += 1
            groups.append({
                "study_id": None, "study_title": "Unassigned Plates",
                "study_number": f"Study {seq:03d}", "is_front_matter": False,
                "plate_indices": leftover,
            })
        if not groups:
            return None
        return groups, "gemini"
    except Exception as e:
        print(f"Gemini grouping failed, falling back to heuristic: {e}")
        return None


def infer_study_groupings(series_id: Optional[int], plates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Main entry point. `plates` is a list of dicts with at least:
      index (int), slide_number (int, optional), raw_ocr (str), cleaned_ocr (str).
    Returns {engine_used, front_matter_count, groups:[...]} with suggested_public per plate index.
    """
    conn = get_db()
    try:
        try:
            front_n = int(float(get_param(conn, "public_front_matter_count", "3") or 3))
        except Exception:
            front_n = 3
        existing = _load_existing_studies(conn, series_id)
    finally:
        conn.close()

    # Order plates by slide_number when present so "first N" is series order
    ordered = sorted(plates, key=lambda p: (p.get("slide_number") if p.get("slide_number") is not None else p.get("index", 0)))
    for i, p in enumerate(ordered):
        p.setdefault("index", i)

    # Detect + parse an optional TOC plate (first plate whose text looks like a TOC)
    toc: List[Dict[str, Any]] = []
    for p in ordered:
        blob = f"{p.get('raw_ocr','')} {p.get('cleaned_ocr','')}".lower()
        if any(h in blob for h in _TOC_HINTS):
            toc = _parse_toc(p.get("raw_ocr") or p.get("cleaned_ocr") or "")
            if toc:
                break

    result = _gemini_grouping(ordered, existing, toc)
    if result is None:
        groups, engine_used = _heuristic_grouping(ordered, existing, toc)
    else:
        groups, engine_used = result

    # Suggested public: first N plate indices in series order
    first_n_indices = {p["index"] for p in ordered[:max(0, front_n)]}
    for g in groups:
        g["suggested_public"] = sorted(i for i in g["plate_indices"] if i in first_n_indices)

    return {
        "engine_used": engine_used,
        "front_matter_count": front_n,
        "toc_detected": bool(toc),
        "existing_studies": [{"id": e["id"], "title": e["title"], "study_number": e["study_number"]} for e in existing],
        "groups": groups,
    }
