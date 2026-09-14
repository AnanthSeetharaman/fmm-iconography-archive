-- ============================================================================
-- FIVE METAL MASONRY (FMM) ICONOGRAPHY ARCHIVE
-- Comprehensive Seed Data & Reference Taxonomy (v1.2)
-- 
-- Compatible with both PostgreSQL and SQLite.
-- Contains:
-- 1. All 19 Series (Completed, Ongoing, Upcoming)
-- 2. Taxonomy Types & Controlled Taxonomy Hierarchy
-- 3. Rich Term Aliases (IAST, Anglicized, Vernacular, Common Spellings)
-- 4. Dictionary of Iconography Seed Entries
-- 5. Places & Temples (Thilatharpanapuri, Pune, Jaipur, etc.)
-- 6. Complete Real Study Record: "Ganesa: Variations in Iconography"
--    with 4 carousel slides, extracted OCR text, and curated mappings.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. EDITORIAL SERIES (All 19 Series from Framework v1.2)
-- ----------------------------------------------------------------------------
INSERT INTO series (id, slug, name, scope, status, sort_order) VALUES
-- Completed Series
(1, 'panchaloha-primer', 'Panchaloha Primer', 'An introduction to the Panchaloha bronze art form.', 'completed', 1),
(2, 'dictionary-of-iconography', 'Dictionary of Iconography', 'Glossary of terms related to iconography.', 'completed', 2),
(3, 'tala', 'Tala', 'Series on iconometry and proportional systems.', 'completed', 3),
(4, 'bronzecast', 'BronzeCast', 'Studies and notes on bronze and the bronze tradition.', 'completed', 4),
(5, 'mythics', 'Mythics', 'Iconography of mythical characters.', 'completed', 5),
(6, '108-tandava', '108 Tandava', 'Iconography of the 108 dance poses of Siva.', 'completed', 6),
(7, 'ayudha', 'Ayudha', 'Visual study of weapons and attributes held by divinities.', 'completed', 7),

-- Ongoing Series
(8, 'roopam', 'Roopam', 'Iconography of minor and lesser-known divine forms.', 'ongoing', 8),
(9, 'god-is-in-the-details', 'God is in the Details', 'Detailed visual iconographic study of museum and temple bronzes.', 'ongoing', 9),
(10, '5mm-iconography-quiz', '5MM Iconography Quiz', 'Quiz-based engagement and learning around iconography.', 'ongoing', 10),
(11, 'majors-iconography', 'Majors Iconography', 'Detailed thematic studies of major divinities; approximately 70 studies to date.', 'ongoing', 11),
(12, 'mudra', 'Mudra', 'Visual study of hand gestures, mudras and hastas.', 'ongoing', 12),
(13, '108-divya-desams', '108 Divya Desams', 'Iconography of Vishnu across the 108 Vaishnava shrines.', 'ongoing', 13),
(14, 'abharana', 'Abharana', 'Visual study of ornamentation and attire.', 'ongoing', 14),
(15, 'temple-iconography', 'Temple Iconography', 'Visual study of temple architecture and sculptures.', 'ongoing', 15),
(16, 'iconography-shelf', 'Iconography Shelf', 'A guided view of books on iconography.', 'ongoing', 16),

-- Upcoming Series
(17, 'padimam', 'Padimam', 'Visual study of stone sculptures in temples.', 'upcoming', 17),
(18, 'vahana', 'Vahana', 'Visual study of the mounts of divinities.', 'upcoming', 18),
(19, 'asana', 'Asana', 'Study of postures.', 'upcoming', 19);

-- ----------------------------------------------------------------------------
-- 2. TAXONOMY TYPES
-- ----------------------------------------------------------------------------
INSERT INTO taxonomy_types (id, code, name, description) VALUES
(1, 'divinity', 'Divinity', 'Primary and secondary divine figures (Siva, Vishnu, Ganesha, etc.)'),
(2, 'form', 'Form', 'Specific identifiable iconographic forms and manifestations'),
(3, 'iconographic_element', 'Iconographic Element', 'Attributes, gestures, postures, attire, ornaments, anatomical traits'),
(4, 'place', 'Place / Temple', 'Geographical locations, historical shrines, and temple complexes'),
(5, 'period_dynasty', 'Period / Dynasty', 'Historical era and sculptural patronage dynasties'),
(6, 'source_reference', 'Source / Reference', 'Classical Agamas, Shilpa Shastras, and museum collections');

-- ----------------------------------------------------------------------------
-- 3. PLACES & TEMPLES
-- ----------------------------------------------------------------------------
INSERT INTO places (id, slug, name, native_name, temple_name, deity_enshrined, tradition, town_city, district, state, notes) VALUES
('p1111111-0000-0000-0000-000000000001', 'adi-vinayaka-thilatharpanapuri', 'Adi Vinayaka Temple, Thilatharpanapuri', 'ஆதி விநாயகர்', 'Muktheeswarar Temple complex', 'Nara-mukha (human-faced) Ganesha', 'Saiva / Ganapatya', 'Thilatharpanapuri', 'Tiruvarur', 'Tamil Nadu', 'Famous for the rare human-faced form of Ganesha without an elephant head.'),
('p1111111-0000-0000-0000-000000000002', 'trishund-ganapati-pune', 'Trishund Mayureshwar Ganapati, Pune', 'त्रिशुंड गणपती', 'Trishund Ganapati Temple', 'Three-trunked, multi-armed Ganesha on peacock', 'Ganapatya', 'Pune', 'Pune', 'Maharashtra', 'Historic 18th-century temple in Somwar Peth featuring Ganesha with 3 trunks seated on a peacock (mayura).'),
('p1111111-0000-0000-0000-000000000003', 'garh-ganesh-jaipur', 'Garh Ganesh Temple, Jaipur', 'गढ़ गणेश', 'Garh Ganesh Mandir', 'Vigraha of Ganesha in trunkless form (Vigraha Purusha)', 'Ganapatya', 'Jaipur', 'Jaipur', 'Rajasthan', 'Historic hilltop temple near Nahargarh Fort showing Ganesha in child-like trunkless form.'),
('p1111111-0000-0000-0000-000000000004', 'brihadisvara-thanjavur', 'Brihadisvara Temple, Thanjavur', 'பெரிய கோவில்', 'Rajarajeswaram', 'Siva / Nataraja / Devi', 'Saiva', 'Thanjavur', 'Thanjavur', 'Tamil Nadu', 'Chola monumental temple with celebrated Chola bronzes and stone iconography.');

-- ----------------------------------------------------------------------------
-- 4. HISTORICAL PERIODS & DYNASTIES
-- ----------------------------------------------------------------------------
INSERT INTO periods_dynasties (id, slug, name, time_span, region, description) VALUES
(1, 'chola', 'Chola', '9th - 13th Century CE', 'Tamil Nadu', 'Golden age of South Indian bronze casting and temple architecture.'),
(2, 'pallava', 'Pallava', '6th - 9th Century CE', 'Northern Tamil Nadu & Andhra', 'Pioneering rock-cut temples, early cave sculpture, and distinct early iconography.'),
(3, 'pandya', 'Pandya', '7th - 14th Century CE', 'Southern Tamil Nadu', 'Distinct structural and cave temples in Madurai and Tirunelveli regions.'),
(4, 'vijayanagara', 'Vijayanagara', '14th - 17th Century CE', 'Deccan & South India', 'Intricate multi-pillar mandapas, monumental gopuras, composite mythological animal sculptures.'),
(5, 'nayaka', 'Nayaka', '16th - 18th Century CE', 'Madurai, Tanjavur, Senji', 'Dramatic lifelike portrait sculptures, elaborately painted wooden & stone ceilings.');

-- ----------------------------------------------------------------------------
-- 5. DICTIONARY OF ICONOGRAPHY SEED ENTRIES
-- ----------------------------------------------------------------------------
INSERT INTO dictionary_entries (id, slug, headword, iast_headword, part_of_speech, etymology, definition, extended_notes) VALUES
('d1111111-0000-0000-0000-000000000001', 'asina', 'Asina', 'Āsīna', 'participle / adjective', 'From Sanskrit root ās (to sit, abide, rest)', 'Seated posture; a generic term for any iconographic form depicted in a sitting position, comprising multiple specific leg configurations.', 'Contrasts with sthānaka (standing) and nṛtta (dancing). Includes padmāsana, sukhāsana, lalitāsana, ardhaparyaṅkāsana, and bhadrāsana.'),
('d1111111-0000-0000-0000-000000000002', 'lalitasana', 'Lalitasana', 'Lalitāsana', 'noun, neuter', 'From Sanskrit lalita (charming, lovely, playful) + āsana (seat)', 'The posture of royal ease, wherein one leg is folded flat on the seat while the other hangs down gracefully, often resting on a lotus or pedestal.', 'A quintessential posture for benevolent divinities including Ganesha, Devi, and Bodhisattvas.'),
('d1111111-0000-0000-0000-000000000003', 'sukhasana', 'Sukhasana', 'Sukhāsana', 'noun, neuter', 'From Sanskrit sukha (comfort, ease, happiness) + āsana', 'Comfortable seated posture; one leg is bent and placed flat on the seat while the other hangs down, or both legs are simply crossed in an informal, relaxed manner.', 'Commonly observed in bronze and stone sculptures of Siva as Somaskanda or Sukhasanamurti.'),
('d1111111-0000-0000-0000-000000000004', 'ardhaparyankasana', 'Ardhaparyankasana', 'Ardhaparyaṅkāsana', 'noun, neuter', 'From ardha (half) + paryaṅka (couch / cross-legged seat) + āsana', 'A seated posture with one leg folded upon the seat (often with the knee raised slightly) and the other leg dangling downwards.', 'Frequently used interchangeably in some texts with lalitāsana, but distinguished by the higher knee elevation in strict iconometry.'),
('d1111111-0000-0000-0000-000000000005', 'bhadrasana', 'Bhadrasana', 'Bhadrāsana', 'noun, neuter', 'From bhadra (auspicious, fortunate) + āsana', 'A majestic seated posture where both legs hang down with feet resting on a stool/support, or arranged symmetrically with soles touching.', 'Referred to in classical Agamas as an auspicious imperial sitting posture.'),
('d1111111-0000-0000-0000-000000000006', 'trishunda', 'Trishunda', 'Triśuṇḍa', 'adjective / noun', 'From tri (three) + śuṇḍā (elephant trunk)', 'Possessing three elephant trunks; an exceptionally rare iconographic depiction of Ganesha.', 'Exemplified in the Trishund Ganapati temple of Pune, where Ganesha is shown with three interconnected trunks.');

-- ----------------------------------------------------------------------------
-- 6. CONTROLLED TAXONOMY TERMS
-- ----------------------------------------------------------------------------

-- Divinities (Type 1)
INSERT INTO taxonomy_terms (id, taxonomy_type_id, canonical_name, iast_name, slug, description, display_order) VALUES
('t1111111-0000-0000-0000-000000000001', 1, 'Ganesha', 'Gaṇeśa', 'ganesha', 'Lord of beginnings and remover of obstacles, depicted with elephant head.', 1),
('t1111111-0000-0000-0000-000000000002', 1, 'Siva', 'Śiva', 'siva', 'Supreme deity in the Saiva tradition, master of dance and asceticism.', 2),
('t1111111-0000-0000-0000-000000000003', 1, 'Vishnu', 'Viṣṇu', 'vishnu', 'The preserver deity of the Hindu pantheon, master of avatars.', 3),
('t1111111-0000-0000-0000-000000000004', 1, 'Devi', 'Devī', 'devi', 'The divine feminine and cosmic mother goddess.', 4),
('t1111111-0000-0000-0000-000000000005', 1, 'Krishna', 'Kṛṣṇa', 'krishna', 'Eighth avatar of Vishnu, divine cowherd and speaker of the Gita.', 5),
('t1111111-0000-0000-0000-000000000006', 1, 'Skanda', 'Skanda', 'Skanda', 'Commander of the divine forces, Murugan, Subrahmanya.', 6);

-- Parent Iconographic Groups (Type 3)
INSERT INTO taxonomy_terms (id, taxonomy_type_id, parent_id, canonical_name, iast_name, slug, description, display_order) VALUES
('t2222222-0000-0000-0000-000000000001', 3, NULL, 'Asana & Sthana', 'Āsana & Sthāna', 'asana-sthana', 'Postures (seated, standing, dancing) and proportional bodily dispositions.', 1),
('t2222222-0000-0000-0000-000000000002', 3, NULL, 'Physical / Anatomical Feature', 'Śārīrika-lakṣaṇa', 'anatomical-features', 'Diagnostic physical forms, heads, arms, trunk directions, tusks.', 2),
('t2222222-0000-0000-0000-000000000003', 3, NULL, 'Vahana', 'Vāhana', 'vahana', 'Animal mounts and divine conveyances.', 3),
('t2222222-0000-0000-0000-000000000004', 3, NULL, 'Ayudha & Attribute', 'Āyudha', 'ayudha-attributes', 'Weapons, sacred emblems, implements, and held objects.', 4),
('t2222222-0000-0000-0000-000000000005', 3, NULL, 'Mudra & Hasta', 'Mudrā & Hasta', 'mudra-hasta', 'Hand gestures, signs, and symbolic hand positions.', 5),
('t2222222-0000-0000-0000-000000000006', 3, NULL, 'Abharana', 'Ābharaṇa', 'abharana', 'Jewellery, crowns, garlands, and sacred ornaments.', 6);

-- Child Terms under Asana & Sthana
INSERT INTO taxonomy_terms (id, taxonomy_type_id, parent_id, canonical_name, iast_name, slug, description, dictionary_entry_id, display_order) VALUES
('t3333333-0000-0000-0000-000000000001', 3, 't2222222-0000-0000-0000-000000000001', 'Asina', 'Āsīna', 'asina', 'General seated posture.', 'd1111111-0000-0000-0000-000000000001', 1),
('t3333333-0000-0000-0000-000000000002', 3, 't2222222-0000-0000-0000-000000000001', 'Sthanaka', 'Sthānaka', 'sthanaka', 'Standing posture.', NULL, 2),
('t3333333-0000-0000-0000-000000000003', 3, 't2222222-0000-0000-0000-000000000001', 'Nrtta', 'Nṛtta', 'nrtta', 'Dancing posture (e.g. Nrtta Ganapati, Nataraja).', NULL, 3),
('t3333333-0000-0000-0000-000000000004', 3, 't2222222-0000-0000-0000-000000000001', 'Lalitasana', 'Lalitāsana', 'lalitasana', 'Posture of royal ease with one leg pendant.', 'd1111111-0000-0000-0000-000000000002', 4),
('t3333333-0000-0000-0000-000000000005', 3, 't2222222-0000-0000-0000-000000000001', 'Sukhasana', 'Sukhāsana', 'sukhasana', 'Comfortable, relaxed sitting posture.', 'd1111111-0000-0000-0000-000000000003', 5),
('t3333333-0000-0000-0000-000000000006', 3, 't2222222-0000-0000-0000-000000000001', 'Padmasana', 'Padmāsana', 'padmasana', 'Full lotus posture with locked legs.', NULL, 6),
('t3333333-0000-0000-0000-000000000007', 3, 't2222222-0000-0000-0000-000000000001', 'Ardhaparyankasana', 'Ardhaparyaṅkāsana', 'ardhaparyankasana', 'Half-cross-legged posture with one knee raised.', 'd1111111-0000-0000-0000-000000000004', 7),
('t3333333-0000-0000-0000-000000000008', 3, 't2222222-0000-0000-0000-000000000001', 'Bhadrasana', 'Bhadrāsana', 'bhadrasana', 'Formal seated posture with both feet supported or symmetrical.', 'd1111111-0000-0000-0000-000000000005', 8);

-- Child Terms under Physical / Anatomical Features
INSERT INTO taxonomy_terms (id, taxonomy_type_id, parent_id, canonical_name, iast_name, slug, description, dictionary_entry_id, display_order) VALUES
('t4444444-0000-0000-0000-000000000001', 3, 't2222222-0000-0000-0000-000000000002', 'Dvibhuja', 'Dvibhuja', 'dvibhuja', 'Two-armed representation.', NULL, 1),
('t4444444-0000-0000-0000-000000000002', 3, 't2222222-0000-0000-0000-000000000002', 'Caturbhuja', 'Caturbhuja', 'caturbhuja', 'Four-armed representation (most familiar).', NULL, 2),
('t4444444-0000-0000-0000-000000000003', 3, 't2222222-0000-0000-0000-000000000002', 'Sadbhuja', 'Ṣaḍbhuja', 'sadbhuja', 'Six-armed representation.', NULL, 3),
('t4444444-0000-0000-0000-000000000004', 3, 't2222222-0000-0000-0000-000000000002', 'Astabhuja', 'Aṣṭabhuja', 'astabhuja', 'Eight-armed representation.', NULL, 4),
('t4444444-0000-0000-0000-000000000005', 3, 't2222222-0000-0000-0000-000000000002', 'Dasabhuja', 'Daśabhuja', 'dasabhuja', 'Ten-armed representation.', NULL, 5),
('t4444444-0000-0000-0000-000000000006', 3, 't2222222-0000-0000-0000-000000000002', 'Sodasabhuja', 'Ṣoḍaśabhuja', 'sodasabhuja', 'Sixteen-armed representation.', NULL, 6),
('t4444444-0000-0000-0000-000000000007', 3, 't2222222-0000-0000-0000-000000000002', 'Dvimukha', 'Dvimukha', 'dvimukha', 'Two-headed form.', NULL, 7),
('t4444444-0000-0000-0000-000000000008', 3, 't2222222-0000-0000-0000-000000000002', 'Trimukha', 'Trimukha', 'trimukha', 'Three-headed form.', NULL, 8),
('t4444444-0000-0000-0000-000000000009', 3, 't2222222-0000-0000-0000-000000000002', 'Pancamukha', 'Pañcamukha', 'pancamukha', 'Five-headed form (e.g. Heramba Ganapati).', NULL, 9),
('t4444444-0000-0000-0000-000000000010', 3, 't2222222-0000-0000-0000-000000000002', 'Vamavarta', 'Vāmāvarta', 'vamavarta', 'Left-turning trunk (edampuri).', NULL, 10),
('t4444444-0000-0000-0000-000000000011', 3, 't2222222-0000-0000-0000-000000000002', 'Daksinavarta', 'Dakṣiṇāvarta', 'daksinavarta', 'Right-turning trunk (valampuri).', NULL, 11),
('t4444444-0000-0000-0000-000000000012', 3, 't2222222-0000-0000-0000-000000000002', 'Trishunda', 'Triśuṇḍa', 'trishunda', 'Three elephant trunks.', 'd1111111-0000-0000-0000-000000000006', 12),
('t4444444-0000-0000-0000-000000000013', 3, 't2222222-0000-0000-0000-000000000002', 'Human-headed Form', 'Naramukha', 'human-headed', 'Human face before receiving the elephant head (Adi Vinayaka).', NULL, 13),
('t4444444-0000-0000-0000-000000000014', 3, 't2222222-0000-0000-0000-000000000002', 'Trunkless Form', 'Ashunda', 'trunkless', 'Form without an elephant trunk (Garh Ganesh).', NULL, 14);

-- Child Terms under Vahana
INSERT INTO taxonomy_terms (id, taxonomy_type_id, parent_id, canonical_name, iast_name, slug, description, display_order) VALUES
('t5555555-0000-0000-0000-000000000001', 3, 't2222222-0000-0000-0000-000000000003', 'Musika', 'Mūṣika', 'musika', 'The mouse mount of Ganesha.', 1),
('t5555555-0000-0000-0000-000000000002', 3, 't2222222-0000-0000-0000-000000000003', 'Mayura', 'Mayūra', 'mayura', 'The peacock mount (associated with Skanda and Trishunda Ganapati).', 2),
('t5555555-0000-0000-0000-000000000003', 3, 't2222222-0000-0000-0000-000000000003', 'Simha', 'Siṃha', 'simha', 'The lion mount (associated with Heramba Ganapati and Durga).', 3);

-- Specific Forms (Type 2)
INSERT INTO taxonomy_terms (id, taxonomy_type_id, parent_id, canonical_name, iast_name, slug, description, place_id, display_order) VALUES
('t6666666-0000-0000-0000-000000000001', 2, NULL, 'Adi Vinayaka', 'Ādi Vināyaka', 'adi-vinayaka', 'The human-headed primordial form of Ganesha.', 'p1111111-0000-0000-0000-000000000001', 1),
('t6666666-0000-0000-0000-000000000002', 2, NULL, 'Trishund Ganapati', 'Triśuṇḍa Gaṇapati', 'trishund-ganapati', 'Three-trunked form mounted upon a peacock.', 'p1111111-0000-0000-0000-000000000002', 2),
('t6666666-0000-0000-0000-000000000003', 2, NULL, 'Garh Ganesh', 'Gaṛh Gaṇeśa', 'garh-ganesh', 'Trunkless form of Ganesha from Jaipur.', 'p1111111-0000-0000-0000-000000000003', 3),
('t6666666-0000-0000-0000-000000000004', 2, NULL, 'Heramba Ganapati', 'Heramba Gaṇapati', 'heramba-ganapati', 'Five-headed protector form riding a lion.', NULL, 4);

-- ----------------------------------------------------------------------------
-- 7. TERM ALIASES (Synonyms, Transliterations, Misspellings & OCR Artifacts)
-- ----------------------------------------------------------------------------
INSERT INTO term_aliases (id, term_id, alias, alias_type, is_searchable) VALUES
-- Ganesha aliases
('a1111111-0000-0000-0000-000000000001', 't1111111-0000-0000-0000-000000000001', 'Ganesa', 'spelling_variant', 1),
('a1111111-0000-0000-0000-000000000002', 't1111111-0000-0000-0000-000000000001', 'Gaṇeśa', 'iast_transliteration', 1),
('a1111111-0000-0000-0000-000000000003', 't1111111-0000-0000-0000-000000000001', 'Ganapati', 'spelling_variant', 1),
('a1111111-0000-0000-0000-000000000004', 't1111111-0000-0000-0000-000000000001', 'Vinayaka', 'spelling_variant', 1),
('a1111111-0000-0000-0000-000000000005', 't1111111-0000-0000-0000-000000000001', 'Pillayar', 'regional_vernacular', 1),
('a1111111-0000-0000-0000-000000000006', 't1111111-0000-0000-0000-000000000001', 'Elephant God', 'english_translation', 1),
('a1111111-0000-0000-0000-000000000007', 't1111111-0000-0000-0000-000000000001', 'GaQeSa', 'ocr_artifact', 1),

-- Asina / Seated aliases
('a2222222-0000-0000-0000-000000000001', 't3333333-0000-0000-0000-000000000001', 'Seated', 'english_translation', 1),
('a2222222-0000-0000-0000-000000000002', 't3333333-0000-0000-0000-000000000001', 'Sitting', 'english_translation', 1),
('a2222222-0000-0000-0000-000000000003', 't3333333-0000-0000-0000-000000000001', 'Āsīna', 'iast_transliteration', 1),
('a2222222-0000-0000-0000-000000000004', 't3333333-0000-0000-0000-000000000001', 'ÄsTna', 'ocr_artifact', 1),
('a2222222-0000-0000-0000-000000000005', 't3333333-0000-0000-0000-000000000001', 'äsrna', 'ocr_artifact', 1),

-- Musika aliases
('a3333333-0000-0000-0000-000000000001', 't5555555-0000-0000-0000-000000000001', 'Mushika', 'spelling_variant', 1),
('a3333333-0000-0000-0000-000000000002', 't5555555-0000-0000-0000-000000000001', 'Mūṣika', 'iast_transliteration', 1),
('a3333333-0000-0000-0000-000000000003', 't5555555-0000-0000-0000-000000000001', 'Mouse', 'english_translation', 1),
('a3333333-0000-0000-0000-000000000004', 't5555555-0000-0000-0000-000000000001', 'Rat', 'english_translation', 1),
('a3333333-0000-0000-0000-000000000005', 't5555555-0000-0000-0000-000000000001', 'Mushika Vahana', 'spelling_variant', 1),
('a3333333-0000-0000-0000-000000000006', 't5555555-0000-0000-0000-000000000001', 'Mü$kavähana', 'ocr_artifact', 1),

-- Specific Asanas
('a4444444-0000-0000-0000-000000000001', 't3333333-0000-0000-0000-000000000004', 'Royal ease', 'english_translation', 1),
('a4444444-0000-0000-0000-000000000002', 't3333333-0000-0000-0000-000000000004', 'lalitäsana', 'ocr_artifact', 1),
('a4444444-0000-0000-0000-000000000003', 't3333333-0000-0000-0000-000000000005', 'sukhäsana', 'ocr_artifact', 1),
('a4444444-0000-0000-0000-000000000004', 't3333333-0000-0000-0000-000000000006', 'padmäsana', 'ocr_artifact', 1),
('a4444444-0000-0000-0000-000000000005', 't3333333-0000-0000-0000-000000000007', 'ardhaparyahkäsana', 'ocr_artifact', 1),
('a4444444-0000-0000-0000-000000000006', 't3333333-0000-0000-0000-000000000008', 'bhadräsana', 'ocr_artifact', 1),

-- Trishunda aliases
('a5555555-0000-0000-0000-000000000001', 't4444444-0000-0000-0000-000000000012', 'Three trunks', 'english_translation', 1),
('a5555555-0000-0000-0000-000000000002', 't4444444-0000-0000-0000-000000000012', 'Triśuṇḍa', 'iast_transliteration', 1),
('a5555555-0000-0000-0000-000000000003', 't4444444-0000-0000-0000-000000000012', 'TriSuQ4a', 'ocr_artifact', 1),
('a5555555-0000-0000-0000-000000000004', 't4444444-0000-0000-0000-000000000012', 'Trishund', 'spelling_variant', 1),

-- Trunk orientations
('a6666666-0000-0000-0000-000000000001', 't4444444-0000-0000-0000-000000000010', 'Left turning trunk', 'english_translation', 1),
('a6666666-0000-0000-0000-000000000002', 't4444444-0000-0000-0000-000000000010', 'Edampuri', 'regional_vernacular', 1),
('a6666666-0000-0000-0000-000000000003', 't4444444-0000-0000-0000-000000000011', 'Right turning trunk', 'english_translation', 1),
('a6666666-0000-0000-0000-000000000004', 't4444444-0000-0000-0000-000000000011', 'Valampuri', 'regional_vernacular', 1);

-- ----------------------------------------------------------------------------
-- 8. THE STUDY RECORD (Fundamental Unit: Ganesa Variations Carousel)
-- ----------------------------------------------------------------------------
INSERT INTO studies (
    id,
    slug,
    title,
    subtitle,
    study_number,
    series_id,
    content_type,
    access_level,
    status,
    summary_markdown,
    original_publication_date,
    cover_image_url,
    total_slides,
    search_keywords,
    curator_notes
) VALUES (
    's1111111-0000-0000-0000-000000000001',
    'ganesa-variations-in-iconography',
    'Ganesa: Variations in Iconography',
    'Postural/Compositional, Anatomical, and Regional Distinctive Forms',
    'Study 001',
    11, -- Majors Iconography series
    'study',
    'public',
    'published',
    'A foundational iconography study examining visible variations in Ganesa icons across postures (āsīna, sthānaka, nṛtta), arm numbers (dvibhuja through ṣoḍaśabhuja), multi-headed forms, trunk disposition, and rare regional manifestations like Adi Vinayaka and Trishund Ganapati.',
    '2026-09-11',
    'Images-archieve/WhatsApp Image 2026-09-11 at 7.29.35 AM (1).jpeg',
    4,
    'Ganesa, Ganesha, Ganapati, Asina, Lalitasana, Padmasana, Sukhasana, Ardhaparyankasana, Bhadrasana, Trishunda, Adi Vinayaka, Garh Ganesh, Vamavarta, Daksinavarta',
    'Curated from the 4-slide carousel in Images-archieve. Preserves full carousel unit.'
);

-- ----------------------------------------------------------------------------
-- 9. CAROUSEL SLIDES (With Extracted OCR & Cleaned Scholarly Text)
-- ----------------------------------------------------------------------------

-- Slide 1: Introduction
INSERT INTO study_slides (
    id,
    study_id,
    slide_number,
    slide_title,
    image_url,
    thumbnail_url,
    caption,
    extracted_ocr_text,
    cleaned_text,
    visual_elements_summary,
    sort_order
) VALUES (
    'sl111111-0000-0000-0000-000000000001',
    's1111111-0000-0000-0000-000000000001',
    1,
    'Variations in Iconography: Scope & Methodology',
    'Images-archieve/WhatsApp Image 2026-09-11 at 7.29.35 AM (1).jpeg',
    'Images-archieve/WhatsApp Image 2026-09-11 at 7.29.35 AM (1).jpeg',
    'Introductory scope outlining visible variations in posture, composition, arms, faces, trunk orientation, and regional configurations.',
    'ICONOGRAPHY VARIATIONS IN ICONOGRAPHY The iconography of Ganesa presents considerable variation in posture, composition and anatomical form. This study examines these visible variations— including the number of arms and faces, disposition of the trunk and distinctive regional configurations—rather than presenting another prescribed set of forms. Some of these variations occur within the well- known 32 forms of GaQeSa (covered earlier) and are revisited here specifically to -illustrate their distinctive iconographic features. This study considers variations that are visibly rather than expressed in the icon itself, distinctions based solely on epithets, legends or sthala-puräQa traditions. FIVE METAL MASONRY fivemetalmasonry.com',
    'The iconography of Gaṇeśa presents considerable variation in posture, composition and anatomical form. This study examines these visible variations—including the number of arms and faces, disposition of the trunk and distinctive regional configurations—rather than presenting another prescribed set of forms. Some of these variations occur within the well-known 32 forms of Gaṇeśa (covered earlier) and are revisited here specifically to illustrate their distinctive iconographic features. This study considers variations that are visibly expressed in the icon itself, rather than distinctions based solely on epithets, legends or sthala-purāṇa traditions.',
    'Title parchment with Five Metal Masonry hand emblem logo.',
    1
);

-- Slide 2: Structured Classification Outline
INSERT INTO study_slides (
    id,
    study_id,
    slide_number,
    slide_title,
    image_url,
    thumbnail_url,
    caption,
    extracted_ocr_text,
    cleaned_text,
    visual_elements_summary,
    sort_order
) VALUES (
    'sl111111-0000-0000-0000-000000000002',
    's1111111-0000-0000-0000-000000000001',
    2,
    'Taxonomy of Ganesa Variations: Postural, Anatomical, Regional',
    'Images-archieve/WhatsApp Image 2026-09-11 at 7.29.35 AM (2).jpeg',
    'Images-archieve/WhatsApp Image 2026-09-11 at 7.29.35 AM (2).jpeg',
    'Complete systematic breakdown: Postural & Compositional, Anatomical (Bahu-bheda, Mukha-bheda, Sunda-bheda), Regional forms, and Vahana variations.',
    'ICONOGRAPHY QAN ESA VARIATIONS IN ICONOGRAPHY 1. POSTURAL & COMPOSITIONAL VARIATIONS • ÄsTna — seated; several variations in leg disposition occur. • Sthänaka — standing • Nrtta — dancing • Mü$kavähana — mounted/seated upon the mü#ika • With Devi/Devis • Samkara Murtis - ganesa combined with another divinity 2. ANATOMICAL VARIATIONS Bähu-bheda — number of arms • Dvibhuja — two-armed representations • Caturbhuja — four-armed; the most familiar depiction. • Sadbhuja, A#Cabhuja, Dagabhuja and other multi-armed forms Mukha-bheda — number of heads/faces • Ekamukha single-headed, the usual form. • Dvimukha / Trimukha / Paficamukha — clearly established forms Sundä-bheda — orientation of the trunk • Left-turning • Right-turning • Central/descending 3. REGIONAL / DISTINCTIVE FORMS FIVE METAL MASONRY fivemetalmasonry.com • Ädi Vinäyaka, Thilatharpanapuri — human-headed form • TriSuQ4a GaQapati, Pune— three-trunked form • Garh Ganesh, Jaipur - trunkless form VAHANA VARIATION Distinctive vähanas are covered under their respective forms — Heramba Ganapati, the paöcamukha form, with the lion; and TriSutpda Ganapati, with the peacock.',
    '1. Postural & Compositional Variations: Āsīna (seated), Sthānaka (standing), Nṛtta (dancing), Mūṣikavāhana (mounted upon mūṣika), With Devi/Devis, Saṅkara Mūrtis (combined with another divinity). 2. Anatomical Variations: Bāhu-bheda (arms: Dvibhuja, Caturbhuja, Ṣaḍbhuja, Aṣṭabhuja, Daśabhuja), Mukha-bheda (heads: Ekamukha, Dvimukha, Trimukha, Pañcamukha), Śuṇḍā-bheda (trunk: Left-turning, Right-turning, Central/descending). 3. Regional / Distinctive Forms: Ādi Vināyaka, Thilatharpanapuri (human-headed), Triśuṇḍa Gaṇapati, Pune (three-trunked), Garh Ganesh, Jaipur (trunkless). Vāhana Variation: Heramba Gaṇapati with lion (siṃha); Triśuṇḍa Gaṇapati with peacock (mayūra).',
    'Comprehensive classification list on aged parchment background.',
    2
);

-- Slide 3: Visual Plate of 20 Variations
INSERT INTO study_slides (
    id,
    study_id,
    slide_number,
    slide_title,
    image_url,
    thumbnail_url,
    caption,
    extracted_ocr_text,
    cleaned_text,
    visual_elements_summary,
    sort_order
) VALUES (
    'sl111111-0000-0000-0000-000000000003',
    's1111111-0000-0000-0000-000000000001',
    3,
    'Comparative Plate: 20 Iconographic Variations of Ganesa',
    'Images-archieve/WhatsApp Image 2026-09-11 at 7.29.35 AM.jpeg',
    'Images-archieve/WhatsApp Image 2026-09-11 at 7.29.35 AM.jpeg',
    'Illustrated comparative plate demonstrating the 20 visual variations drawn from bronzes, stone sculptures, and classical iconometry.',
    'ICONOGRAPHY VARIATIONS IN ICONOGRAPHY POSTURAL/COMPOSITIONAL • ANATOMICAL • REGIONAL POSTURAL & COMPOSITIONAL VARIATIONS ASINA SAD-BHUJA STANA ASTA-BHUJA MUSHIKA VAHANA ANATOMICAL VARIATIONS ASA-BHUJA SODASA-BÅUJA REGIONAL DISTINCTIVE FORMS DEVI SAHITA AMKARA MURTI ATUR-BHUJ DAKSINAVARTL•: FIVE METAL MASONRY fivemetalmasonry.com ADI- TN TRISHUND PANA''fi, PUNE GARH GANAPTI, JAIPUR',
    'Visual comparative iconography plate illustrating: Row 1 (Postural): Āsīna, Sthānaka, Nṛtta, Mūṣika Vāhana, Devi Sahita, Saṅkara Mūrtis. Row 2 & 3 (Anatomical): Dvi-mukha, Tri-mukha, Pañca-mukha, Dvi-bhuja, Catur-bhuja, Ṣaḍ-bhuja, Aṣṭa-bhuja, Daśa-bhuja, Ṣoḍaśa-bhuja, Vāmāvarta, Dakṣiṇāvarta. Row 4 (Regional): Ādi-Vināyaka (Tamil Nadu, Human Form), Trishund Ganapati (Pune, Three Trunked), Garh Ganapati (Jaipur, Trunkless).',
    '20 detailed hand-drawn iconographic line drawings in 4 registers.',
    3
);

-- Slide 4: Deep Dive on Asina / Sitting Postures
INSERT INTO study_slides (
    id,
    study_id,
    slide_number,
    slide_title,
    image_url,
    thumbnail_url,
    caption,
    extracted_ocr_text,
    cleaned_text,
    visual_elements_summary,
    sort_order
) VALUES (
    'sl111111-0000-0000-0000-000000000004',
    's1111111-0000-0000-0000-000000000001',
    4,
    'Postural Variations: Asina | Sitting Postures in Detail',
    'Images-archieve/WhatsApp Image 2026-09-11 at 7.29.36 AM.jpeg',
    'Images-archieve/WhatsApp Image 2026-09-11 at 7.29.36 AM.jpeg',
    'Deep iconographic reading of seated forms: padmasana, sukhasana, lalitasana, ardhaparyankasana, and bhadrasana.',
    'ICONOGRAPHY POSTURAL VARIATIONS ÄSiNA I SITTING In the äsrna form, Ganesa is represented seated in a stable and composed posturer with the legs arranged in several ways according to the specific iconographic form. He in padmäsana (lotus may sit posture), sukhäsana (easy posture), lalitäsana (posture of royal ease), or ardhaparyahkäsana (with one leg — pendant and the other drawn up). He may also be shown in bhadräsana (a formal seated posture, generally with both feet placed on a support or with the legs arranged symmetrically). The characteristic elephant head, large ears and prominent rounded belly are retained, while the number ¯ of arms, gestures and attributes may vary according to the specific iconographic form. FIVE METAL MASONRY fivemetalmasonry.com',
    'In the āsīna form, Gaṇeśa is represented seated in a stable and composed posture, with the legs arranged in several ways according to the specific iconographic form. He may sit in padmāsana (lotus posture), sukhāsana (easy posture), lalitāsana (posture of royal ease), or ardhaparyaṅkāsana (with one leg pendant and the other drawn up). He may also be shown in bhadrāsana (a formal seated posture, generally with both feet placed on a support or with the legs arranged symmetrically). The characteristic elephant head, large ears and prominent rounded belly are retained, while the number of arms, gestures and attributes may vary according to the specific iconographic form.',
    'Line drawing of Caturbhuja Ganesha seated in Lalitasana on a padmapitha holding pasa and ankusa with modaka on trunk.',
    4
);

-- ----------------------------------------------------------------------------
-- 10. STUDY TAXONOMY MAPPINGS (Layer 3 Curated Associations)
-- ----------------------------------------------------------------------------
-- Indexing Rule: Index what is studied or materially discussed, not merely visible.

INSERT INTO study_taxonomy_mappings (
    id, study_id, term_id, relevance_level, confidence_score, slide_numbers, curator_verified, curator_notes
) VALUES
-- Primary Divinity
('m1111111-0000-0000-0000-000000000001', 's1111111-0000-0000-0000-000000000001', 't1111111-0000-0000-0000-000000000001', 'primary_subject', 1.000, '[1, 2, 3, 4]', 1, 'Primary deity of this entire visual study.'),

-- Postures Materially Discussed
('m1111111-0000-0000-0000-000000000002', 's1111111-0000-0000-0000-000000000001', 't3333333-0000-0000-0000-000000000001', 'materially_discussed', 1.000, '[2, 3, 4]', 1, 'Asina posture analyzed extensively in slide 2, 3, 4.'),
('m1111111-0000-0000-0000-000000000003', 's1111111-0000-0000-0000-000000000001', 't3333333-0000-0000-0000-000000000004', 'materially_discussed', 1.000, '[4]', 1, 'Lalitasana explicitly described and illustrated in slide 4.'),
('m1111111-0000-0000-0000-000000000004', 's1111111-0000-0000-0000-000000000001', 't3333333-0000-0000-0000-000000000005', 'materially_discussed', 1.000, '[4]', 1, 'Sukhasana defined in slide 4.'),
('m1111111-0000-0000-0000-000000000005', 's1111111-0000-0000-0000-000000000001', 't3333333-0000-0000-0000-000000000006', 'materially_discussed', 1.000, '[4]', 1, 'Padmasana defined in slide 4.'),
('m1111111-0000-0000-0000-000000000006', 's1111111-0000-0000-0000-000000000001', 't3333333-0000-0000-0000-000000000007', 'materially_discussed', 1.000, '[4]', 1, 'Ardhaparyankasana defined in slide 4.'),
('m1111111-0000-0000-0000-000000000007', 's1111111-0000-0000-0000-000000000001', 't3333333-0000-0000-0000-000000000008', 'materially_discussed', 1.000, '[4]', 1, 'Bhadrasana defined in slide 4.'),
('m1111111-0000-0000-0000-000000000008', 's1111111-0000-0000-0000-000000000001', 't3333333-0000-0000-0000-000000000002', 'materially_discussed', 1.000, '[2, 3]', 1, 'Sthanaka listed and drawn in plate.'),
('m1111111-0000-0000-0000-000000000009', 's1111111-0000-0000-0000-000000000001', 't3333333-0000-0000-0000-000000000003', 'materially_discussed', 1.000, '[2, 3]', 1, 'Nrtta dancing form listed and drawn in plate.'),

-- Anatomical Variations
('m1111111-0000-0000-0000-000000000010', 's1111111-0000-0000-0000-000000000001', 't4444444-0000-0000-0000-000000000012', 'materially_discussed', 1.000, '[2, 3]', 1, 'Trishunda (three-trunked form) discussed in slide 2 and drawn in slide 3.'),
('m1111111-0000-0000-0000-000000000011', 's1111111-0000-0000-0000-000000000001', 't4444444-0000-0000-0000-000000000010', 'materially_discussed', 1.000, '[2, 3]', 1, 'Vamavarta trunk orientation.'),
('m1111111-0000-0000-0000-000000000012', 's1111111-0000-0000-0000-000000000001', 't4444444-0000-0000-0000-000000000011', 'materially_discussed', 1.000, '[2, 3]', 1, 'Daksinavarta trunk orientation.'),
('m1111111-0000-0000-0000-000000000013', 's1111111-0000-0000-0000-000000000001', 't4444444-0000-0000-0000-000000000013', 'materially_discussed', 1.000, '[2, 3]', 1, 'Human-headed Adi Vinayaka form.'),
('m1111111-0000-0000-0000-000000000014', 's1111111-0000-0000-0000-000000000001', 't4444444-0000-0000-0000-000000000014', 'materially_discussed', 1.000, '[2, 3]', 1, 'Trunkless Garh Ganesh form.'),

-- Specific Forms & Regional Manifestations
('m1111111-0000-0000-0000-000000000015', 's1111111-0000-0000-0000-000000000001', 't6666666-0000-0000-0000-000000000001', 'materially_discussed', 1.000, '[2, 3]', 1, 'Adi Vinayaka form of Thilatharpanapuri.'),
('m1111111-0000-0000-0000-000000000016', 's1111111-0000-0000-0000-000000000001', 't6666666-0000-0000-0000-000000000002', 'materially_discussed', 1.000, '[2, 3]', 1, 'Trishund Ganapati of Pune.'),
('m1111111-0000-0000-0000-000000000017', 's1111111-0000-0000-0000-000000000001', 't6666666-0000-0000-0000-000000000003', 'materially_discussed', 1.000, '[2, 3]', 1, 'Garh Ganesh of Jaipur.'),

-- Vahana & Mounts
('m1111111-0000-0000-0000-000000000018', 's1111111-0000-0000-0000-000000000001', 't5555555-0000-0000-0000-000000000001', 'materially_discussed', 1.000, '[2, 3]', 1, 'Musika mount discussed in slide 2 and drawn in slide 3.'),
('m1111111-0000-0000-0000-000000000019', 's1111111-0000-0000-0000-000000000001', 't5555555-0000-0000-0000-000000000002', 'secondary_reference', 0.900, '[2]', 1, 'Peacock mount referenced for Trishund Ganapati.'),
('m1111111-0000-0000-0000-000000000020', 's1111111-0000-0000-0000-000000000001', 't5555555-0000-0000-0000-000000000003', 'secondary_reference', 0.900, '[2]', 1, 'Lion mount referenced for Heramba Ganapati.');

-- ----------------------------------------------------------------------------
-- 11. AI METADATA PROPOSALS (Layer 2 Workflow Seed Records)
-- ----------------------------------------------------------------------------
INSERT INTO ai_metadata_proposals (
    id, study_id, slide_id, slide_number, suggested_taxonomy_type, raw_suggested_term, mapped_term_id, confidence_score, evidence_snippet, review_status, curator_notes
) VALUES
('pr111111-0000-0000-0000-000000000001', 's1111111-0000-0000-0000-000000000001', 'sl111111-0000-0000-0000-000000000001', 1, 'divinity', 'Ganesa', 't1111111-0000-0000-0000-000000000001', 0.995, 'The iconography of Ganesa presents considerable variation in posture...', 'approved', 'Matched to canonical divinity Ganesha via spelling variant.'),
('pr111111-0000-0000-0000-000000000002', 's1111111-0000-0000-0000-000000000001', 'sl111111-0000-0000-0000-000000000002', 2, 'iconographic_element', 'Mü$kavähana', 't5555555-0000-0000-0000-000000000001', 0.940, 'Mü$kavähana — mounted/seated upon the mü#ika', 'approved', 'OCR artifact mapped to Musika vahana.'),
('pr111111-0000-0000-0000-000000000003', 's1111111-0000-0000-0000-000000000001', 'sl111111-0000-0000-0000-000000000002', 2, 'iconographic_element', 'TriSuQ4a GaQapati', 't4444444-0000-0000-0000-000000000012', 0.965, 'TriSuQ4a GaQapati, Pune— three-trunked form', 'approved', 'OCR artifact recognized as Trishunda Ganapati.'),
('pr111111-0000-0000-0000-000000000004', 's1111111-0000-0000-0000-000000000001', 'sl111111-0000-0000-0000-000000000004', 4, 'iconographic_element', 'lalitäsana', 't3333333-0000-0000-0000-000000000004', 0.990, 'or lalitäsana (posture of royal ease)', 'approved', 'Direct match to Lalitasana.');

-- ----------------------------------------------------------------------------
-- 12. POPULATE INITIAL FTS VIRTUAL TABLES (For SQLite)
-- ----------------------------------------------------------------------------
-- Insert studies into FTS
INSERT OR IGNORE INTO studies_fts(study_id, title, subtitle, summary_markdown, series_name, divinities, taxonomy_elements, aliases)
VALUES (
    's1111111-0000-0000-0000-000000000001',
    'Ganesa: Variations in Iconography',
    'Postural/Compositional, Anatomical, and Regional Distinctive Forms',
    'A foundational iconography study examining visible variations in Ganesa icons across postures (asina, sthanaka, nrtta), arm numbers (dvibhuja through sodasabhuja), multi-headed forms, trunk disposition, and rare regional manifestations like Adi Vinayaka and Trishund Ganapati.',
    'Majors Iconography',
    'Ganesha, Gaṇeśa, Ganapati, Vinayaka',
    'Asina, Sthanaka, Nrtta, Lalitasana, Sukhasana, Padmasana, Ardhaparyankasana, Bhadrasana, Trishunda, Vamavarta, Daksinavarta, Musika, Adi Vinayaka, Garh Ganesh',
    'Ganesa, Pillayar, Elephant God, Seated, Sitting, Mouse, Rat, Three trunks, Left-turning trunk, Edampuri, Right-turning trunk, Valampuri'
);

-- Insert slides into FTS
INSERT OR IGNORE INTO study_slides_fts(slide_id, study_id, slide_number, slide_title, caption, extracted_ocr_text, cleaned_text)
SELECT id, study_id, slide_number, slide_title, caption, extracted_ocr_text, cleaned_text FROM study_slides;

-- Insert taxonomy terms into FTS
INSERT OR IGNORE INTO taxonomy_terms_fts(term_id, canonical_name, iast_name, category, aliases)
SELECT 
    t.id, 
    t.canonical_name, 
    COALESCE(t.iast_name, ''), 
    tt.name,
    COALESCE((SELECT GROUP_CONCAT(alias, ', ') FROM term_aliases WHERE term_id = t.id), '')
FROM taxonomy_terms t
JOIN taxonomy_types tt ON t.taxonomy_type_id = tt.id;
