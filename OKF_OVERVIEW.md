# Five Metal Masonry (FMM) - Open Knowledge Framework (OKF) Master Overview

This repository has been structured in compliance with the **Open Knowledge Foundation (OKF)** standards, providing open, machine-readable, and academically rigorous data packages for classical Indian sacred art and iconographic scholarship.

---

## 📦 1. Artifacts Generated in this OKF Package

| Artifact | Format | Purpose |
|---|---|---|
| **[datapackage.json](file:///C:/Users/anant/Downloads/FMM/datapackage.json)** | JSON (OKF Frictionless Standard) | The official Open Knowledge Foundation Data Package descriptor defining metadata, licensing, 20 resources (tables), field types, and constraints. |
| **[domain_skills.md](file:///C:/Users/anant/Downloads/FMM/domain_skills.md)** | Agent Skill / Markdown | Authoritative domain knowledge framework detailing Panchaloha metallurgy, Shilpa Shastra canons, 6 iconographic taxonomies, and raw post ingestion workflows. |
| **[db_skills.md](file:///C:/Users/anant/Downloads/FMM/db_skills.md)** | Agent Skill / Markdown | Authoritative database architecture framework detailing DuckDB Medallion tiers, table dictionary, cascading foreign keys, and hybrid search algorithms. |
| **[ddl.sql](file:///C:/Users/anant/Downloads/FMM/app/ddl.sql)** | ANSI / DuckDB SQL | Complete DDL script recreating all 20 tables with primary keys, foreign keys, and default values. |
| **[dml.sql](file:///C:/Users/anant/Downloads/FMM/app/dml.sql)** | SQL Inserts | Master reference seed data populating series, studies, slides, taxonomy terms, aliases, and Sanskrit definitions. |
| **[retrieval_arch_orverview.md](file:///C:/Users/anant/Downloads/FMM/app/retrieval_arch_orverview.md)** | Architectural Spec / Mermaid | Comprehensive trace of the hybrid retrieval pipeline with exact query logs for `'mooshika'`. |

---

## 🤖 2. Antigravity Agent Skill Integration

Both skills have been installed directly into `.agents/skills/` so that AI agents and pair programmers working in this repository automatically activate domain and database expertise:
- **`fmm-domain`**: `.agents/skills/fmm-domain/SKILL.md`
- **`fmm-database`**: `.agents/skills/fmm-database/SKILL.md`

Whenever you prompt the agent about iconographic terms (e.g. *Lalitasana*, *Triśuṇḍa*, *Mūṣika*, *Ananda Tandava*) or database operations (e.g. DuckDB tables, queries, migrations), the agent seamlessly uses these specifications.
