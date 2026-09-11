# Mixed 1 capture report, v6 (raw-text route, 11-Sep-2026)

## 1.0 Gate
GREEN (pswp_json_repair.repair_and_gate: 0 pathologies; 31 F11 header retypes, 1 F13 stem collision on the duplicate INV-0110 occurrence).

## 2.0 Runtime and coverage
- Runtime A: parse_mixed1.py, pdftotext -layout with page text retained on every document; Aust Care rows rebuilt from word positions (pdftotext -bbox). Seven vendor templates. No OCR required (text layer on all 61 pages; the three scanned Bushcare invoices carry an OCR text layer with letter-spacing artefacts, captured as printed).
- Source Mixed_1.pdf md5 b9ddf7fd6c56188a22181921b7b2c8ab, 61 of 61 pages covered.
- 30 occurrences, 29 unique (INV-0110 pages 30-31 is an exact duplicate of pages 28-29, marked duplicate_of).
- Arithmetic tie 30 of 30 at line level: 371 PRICED lines, 55 ATTACHMENT lines (Glascott schedules, rule 16d), 2,166 lines total.
- Unique ex-GST total $1,177,803.37, same as the v5 header-only figure.
- Verbatim fidelity: 2,374 five-word shingles checked cell-wise against each line's own page text, 0 failures. 24 shingles spanning Aust Care wrapped-cell boundaries are not contiguous on the page by construction; every fragment is.

## 3.0 Register match (branch register v1, Natural Areas and Park Maintenance AP lines)
- 24 documents match one AP line exactly; 2 within one cent (INV-9360, INV-0600).
- INV-39235 (Levai): SUM-TIE, two AP rows $18,900.00 and $14,670.00, each with its own printed quote line.
- 18788 and 18789 (Bushcare): register carries incl/1.1 ($22,888.29 and $21,743.90) because the printed GST is not 10% of the subtotal; check 2 derivation-equality variant, check 3 rounding variant.
- Five documents post with a cents companion AP line (INV-0569 -0.01, 18751 -0.05, 18750 -0.06, 26230 -0.01, 26231 +0.01): TechOne incl/1.1 rounding legs, not green-blocked, cross-referenced in the coding note.
- EvID overrides: GDW-INV-0111 and GDW-INV-0112 (Guru Dirt Works), because those Xero ids are already held for Flavell-Dau in PS_WP v127 (Method 34.2). All Guru ids use the GDW- prefix for consistency.

## 4.0 Findings carried to the build brief
1. Glascott 012191: attached schedule $32,951.44 against the face $32,477.92 (difference $473.52); 012197: $27,073.64 against $25,217.15 (difference $1,856.49). The face is what was billed; the schedules include PK000382, PK000383 and PK000379 rows outside PK000378.
2. INV-9360 (Activeco) is dated 31-Mar-2026 and due 30-Apr-2026 but bills July 2026 treatments on a Jul-2026 register line: printed-date error on the supplier side; FY (Service) FY2026/27.
3. Austspray 158592 prints $81,732.39 on the item row against "$75,345.91 plus gst" in the description; the -$6,449.98 Elwyn Drive variation nets to the subtotal. 158850 prints $57,618.11 on the item row and $57,631.44 in the description; the $13.33 variation nets. 158853 prints $75,345.91 against $75,377.98 in the description; two variations net. All three tie.
4. Aust Care 26231 mixes orders 801672, 702342 and 801671 on one invoice; 26230 and 26302 are single-order.
5. Printed GST differs from 10% of the subtotal by 1c to 7c on 9 documents (per-line rounding baskets): check 3 rounding-tolerance variant.
6. Bushcare 18750 and 18788 print "Out of Scope" against the contract header block; captured as narrative.
7. Three scanned Bushcare invoices (18751, 18750, 18788) carry OCR letter-spacing in the text layer (e.g. "J D R 6"); captured as the text layer prints, the image reads "JDR6".

## 5.0 Next step
Build session: author the batch brief from match_mixed_1_v6.json and extend the rule 20 driver to read the branch register Config (positions differ from PS_WP: Register cols 148, EI/EIL/EIL_Controls at the branch layout). 29 green blocks, $1,177,803.37, all Natural Areas and Park Maintenance.
