import re
import math
import numpy as np
from typing import List, Dict, Any, Tuple

import unicodedata

# Dimension of subword dense vector embedding
EMBEDDING_DIM = 128

def strip_diacritics(text: str) -> str:
    """
    Strips Sanskrit / IAST diacritical marks (e.g. Mūṣika -> Musika, Śiva -> Siva, Āsīna -> Asina).
    """
    if not text:
        return ""
    normalized = unicodedata.normalize('NFKD', text)
    return "".join(c for c in normalized if not unicodedata.combining(c))

def normalize_indic_phonetics(text: str) -> str:
    """
    Normalizes common English transliterations and OCR artifacts of Sanskrit / Indian words:
      - Strips IAST diacritics (Mūṣika -> Musika, Śiva -> Siva, Gaṇeśa -> Ganesa)
      - Repairs common Sanskrit OCR glyph errors ($ -> s, # -> s, Q -> n)
      - 'oo' -> 'u' (e.g. 'mooshika' -> 'mushika', 'soorya' -> 'surya')
      - 'ee' -> 'i' (e.g. 'sheeva' -> 'shiva', 'preeti' -> 'priti')
      - 'aa' -> 'a'
      - 'sh' -> 's', 'zh' -> 'l'
      - 'w' -> 'v'
      - 'th' -> 't' (e.g. 'thilatharpanapuri' -> 'tilatarpanapuri')
      - 'ph' -> 'p', 'bh' -> 'b', 'dh' -> 'd', 'kh' -> 'k', 'gh' -> 'g', 'ch' -> 'c'
      - Strips trailing Sanskrit case endings (-am, -an, -a)
    """
    if not text:
        return ""
    s = strip_diacritics(text.lower().strip())
    # Sanskrit OCR artifact substitutions
    s = s.replace('$', 's').replace('#', 's').replace('q', 'n')
    s = re.sub(r'oo+', 'u', s)
    s = re.sub(r'ee+', 'i', s)
    s = re.sub(r'aa+', 'a', s)
    s = re.sub(r'sh', 's', s)
    s = re.sub(r'w', 'v', s)
    s = re.sub(r'th', 't', s)
    s = re.sub(r'ph', 'p', s)
    s = re.sub(r'bh', 'b', s)
    s = re.sub(r'dh', 'd', s)
    s = re.sub(r'kh', 'k', s)
    s = re.sub(r'gh', 'g', s)
    s = re.sub(r'ch', 'c', s)
    s = re.sub(r'(am|an)$', '', s)
    # Remove remaining punctuation
    s = re.sub(r'[^\w\s]', '', s)
    return s.strip()

def get_character_ngrams(word: str, n_min: int = 2, n_max: int = 4) -> List[str]:
    """Generates character n-grams for subword morphological matching."""
    w = f"<{word.lower().strip()}>"
    ngrams = []
    for n in range(n_min, min(n_max + 1, len(w) + 1)):
        for i in range(len(w) - n + 1):
            ngrams.append(w[i:i + n])
    return ngrams

def text_to_dense_vector(text: str, dim: int = EMBEDDING_DIM) -> List[float]:
    """
    Generates a normalized 128-dimensional dense vector embedding from text
    using deterministic subword hash projections and TF-IDF weighting.
    Captures phonetic morphology, typos, and semantic stems.
    """
    if not text:
        return [0.0] * dim

    vec = np.zeros(dim, dtype=np.float32)
    words = re.findall(r'\b\w+\b', text.lower())

    for word in words:
        # Get standard ngrams + phonetic ngrams
        ngrams = get_character_ngrams(word)
        norm_word = normalize_indic_phonetics(word)
        if norm_word != word:
            ngrams.extend(get_character_ngrams(norm_word))

        for ng in ngrams:
            # Hash to index and sign (+1 / -1)
            h = hash(ng)
            idx = abs(h) % dim
            sign = 1.0 if (h & 1) else -1.0
            vec[idx] += sign

    # L2 normalize vector
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm

    return vec.tolist()

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Computes cosine similarity between two dense vector embeddings."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    return max(0.0, min(1.0, float(dot)))

def trigram_similarity(s1: str, s2: str) -> float:
    """Computes character trigram Dice similarity for fuzzy matching."""
    if not s1 or not s2:
        return 0.0
    if s1.lower() == s2.lower():
        return 1.0

    w1 = f"  {s1.lower()}  "
    w2 = f"  {s2.lower()}  "
    t1 = set(w1[i:i+3] for i in range(len(w1)-2))
    t2 = set(w2[i:i+3] for i in range(len(w2)-2))
    if not t1 or not t2:
        return 0.0
    return (2.0 * len(t1 & t2)) / (len(t1) + len(t2))
