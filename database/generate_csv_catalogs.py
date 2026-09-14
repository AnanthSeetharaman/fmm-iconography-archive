#!/usr/bin/env python3
"""
Five Metal Masonry (FMM) Iconography Archive
Catalog CSV Exporter (generate_csv_catalogs.py)

Generates doc_catalog.csv and doc_ref_catalog.csv combining series, studies, 
Agamic dictionary entries, taxonomy categories, search aliases, historical places, 
and textual references into simple, complete relational catalog tables.
"""

import os
import sys
import csv
import sqlite3

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DB_PATH = os.path.join(os.path.dirname(__file__), "fmm_archive.db")
DOC_CATALOG_CSV = os.path.join(os.path.dirname(__file__), "doc_catalog.csv")
DOC_REF_CATALOG_CSV = os.path.join(os.path.dirname(__file__), "doc_ref_catalog.csv")

def generate_csvs():
    print(f"[FMM Catalog CSV Generator]")
    print(f"Connecting to database: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Build doc_catalog.csv
    doc_catalog_headers = [
        "SERIES_NAME",
        "STUDY_NAME",
        "AGAMIC_DICT_LIST_SEED",
        "TAXONOMY_CATEGORIES",
        "ALIASES",
        "SYNONYMS",
        "HISTORICAL_PLACES_OR_TEMPLES",
        "DYNASTIES_OR_EPOCH",
        "DOC_REF",
        "STATIC_EXPLANATIONS"
    ]

    # Gather data from database
    cur.execute("SELECT name FROM series ORDER BY sort_order")
    all_series = [r[0] for r in cur.fetchall()]

    cur.execute("SELECT headword, iast_headword FROM dictionary_entries")
    dict_entries = [f"{r[0]} ({r[1]})" for r in cur.fetchall()]
    dict_seed_str = "; ".join(dict_entries)

    cur.execute("SELECT name FROM taxonomy_types")
    tax_cats = [r[0] for r in cur.fetchall()]
    tax_cats_str = "; ".join(tax_cats)

    cur.execute("SELECT alias FROM term_aliases LIMIT 15")
    aliases = [r[0] for r in cur.fetchall()]
    aliases_str = "; ".join(aliases)

    synonyms_list = [
        "Lord of Beginnings", "Royal Ease Stance", "Three-Trunked", "Comfortable Posture",
        "Auspicious Seat", "Elephant Mount", "Peacock Mount", "Ananda Tandava"
    ]
    synonyms_str = "; ".join(synonyms_list)

    cur.execute("SELECT name, town_city FROM places")
    places = [f"{r[0]} ({r[1]})" for r in cur.fetchall()]
    places_str = "; ".join(places)

    cur.execute("SELECT name, time_span FROM periods_dynasties")
    periods = [f"{r[0]} ({r[1]})" for r in cur.fetchall()]
    periods_str = "; ".join(periods)

    doc_refs_list = ["Mānasāra Śilpa Śāstra", "Śilparatna of Śrīkumāra", "Kāraṇāgama", "Mayamata"]
    doc_ref_str = "; ".join(doc_refs_list)

    # Master Study Records
    cur.execute("""
        SELECT ser.name, s.title, s.subtitle, s.total_slides
        FROM studies s
        JOIN series ser ON s.series_id = ser.id
    """)
    studies_rows = cur.fetchall()

    doc_catalog_data = []

    # Active Seeded Studies
    for ser_name, st_title, st_sub, total_slides in studies_rows:
        doc_catalog_data.append([
            ser_name,
            st_title,
            dict_seed_str,
            tax_cats_str,
            aliases_str,
            synonyms_str,
            places_str,
            periods_str,
            doc_ref_str,
            f"Active monograph with {total_slides} visual carousel plates. {st_sub or ''}"
        ])

    # Series without active studies yet (Catalog Shells for future monographs)
    existing_series = {r[0] for r in studies_rows}
    for ser_name in all_series:
        if ser_name not in existing_series:
            doc_catalog_data.append([
                ser_name,
                f"Full Monograph Series: {ser_name}",
                dict_seed_str if ser_name in ["Dictionary of Iconography", "Majors Iconography"] else "Asina; Lalitasana",
                tax_cats_str,
                "Ganesh; Mooshika; Lalitasana; Nataraja",
                "Sacred Bronze Study; Iconometric Proportion",
                "Brihadisvara Temple, Thanjavur",
                "Chola (9th-13th C CE); Pallava",
                doc_ref_str,
                f"Editorial series taxonomy shell for {ser_name}. Preserves carousel visual studies."
            ])

    with open(DOC_CATALOG_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(doc_catalog_headers)
        writer.writerows(doc_catalog_data)

    print(f"  [+] Created doc_catalog.csv ({len(doc_catalog_data)} rows)")

    # 2. Build doc_ref_catalog.csv
    doc_ref_headers = [
        "DOC_REF",
        "DOC_NAME",
        "CORPUS",
        "SECTION",
        "AUTHOR_OR_TRADITION",
        "LANGUAGE",
        "APPLICABILITY_TO_ICONOGRAPHY"
    ]

    doc_ref_data = [
        [
            "DOC_REF_001",
            "Mānasāra Śilpa Śāstra",
            "Agama & Vastu Shastra Corpus",
            "Chapter 51-56: Tālamāna & Pratima Lakshana",
            "Maharshi Mānasāra",
            "Sanskrit (IAST)",
            "Foundational text for iconometric proportions (Navatala, Dasatala) and divine bronze casting."
        ],
        [
            "DOC_REF_002",
            "Śilparatna",
            "South Indian Silpa Corpus",
            "Part II: Iconography of Devas & Devis",
            "Śrīkumāra of Kerala (16th C CE)",
            "Sanskrit",
            "Detailed treatises on mudras, ayudhas, postures, and Panchaloha alloy mixing formulas."
        ],
        [
            "DOC_REF_003",
            "Kāraṇāgama",
            "Saiva Agamic Corpus",
            "Kriya Pada: Murti Laksana",
            "Saiva Siddhanta Tradition",
            "Sanskrit (Grantha Script)",
            "Prescribes ritual dimensions, postures, and iconographic marks for Siva, Ganesha, and Skanda."
        ],
        [
            "DOC_REF_004",
            "Mayamata",
            "Vastu & Silpa Shastra Corpus",
            "Chapters 34-36: Sculptural Proportions",
            "Mayamuni",
            "Sanskrit",
            "Comprehensive manual on architectural sculpture, bronze casting, and iconographic symmetry."
        ],
        [
            "DOC_REF_005",
            "Elements of Hindu Iconography",
            "Modern Epigraphical Corpus",
            "Volumes I & II",
            "T.A. Gopinatha Rao (1914)",
            "English / Sanskrit Citations",
            "Pioneering academic baseline reference cross-referencing Agamic texts with Chola/Pallava bronzes."
        ]
    ]

    with open(DOC_REF_CATALOG_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(doc_ref_headers)
        writer.writerows(doc_ref_data)

    print(f"  [+] Created doc_ref_catalog.csv ({len(doc_ref_data)} rows)")

    conn.close()
    print("Catalog CSV Export Complete!\n")

if __name__ == "__main__":
    generate_csvs()
