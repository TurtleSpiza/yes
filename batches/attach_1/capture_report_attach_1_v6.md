# Batch attach_1 capture report (raw-text route, branch v4, 11-Sep-2026)

## 1.0 Gate

**GREEN** (pswp_json_repair.repair_and_gate, zero repairs, zero pathologies). Rule 19.2 shingle check: 254 five-word shingles tested against the retained page text, 0 misses (`shingles_attach_1_v6.json`).

## 2.0 Source and tool

- Five single-invoice TechOne attachment PDFs (EzeScan Server21 exports; the file name is the TechOne attachment id). Not embedded (rule 15); md5s on Data_Acquisition F15 to F19 of the v4 workbook and in the corpus manifest.
- Extraction: `toolkit/branch/parse_attach1.py`, pdftotext 24.02.0 `-layout`, page text retained per page, five vendor templates (ETSOL, GLASCOTT_LM, PROVAC, SAVCO, HERITAGE).
- Gate amendment shipped with this batch: the P9 page-coverage pathology now tests per source file when a corpus carries several files (`pswp_json_repair.py`); the two earlier corpora still gate GREEN.

## 3.0 Documents

| Invoice | Vendor | File | Pages | Printed ex GST | Captured | Tie | Priced lines | Register line | Variant |
|---|---|---|---|---:|---:|---|---:|---|---|
| 11913 | ETSol Pty Ltd t/a Eco Technology Solutions | C00312585.pdf | 3 | 10,229.97 | 10,229.97 | TIE | 26 | 7fa7c620-73126-PK000422-01 | standard |
| 012313 | Glascott Landscape and Civil Pty Limited | C00319690_1.pdf | 1 | 56,454.33 | 56,454.33 | TIE | 1 | 18a1c8e9-73126-PK000015-01 | standard |
| INV-00042754 | Provac Australia Pty Ltd | C00306835.pdf | 2 | 880.00 | 880.00 | TIE | 1 | 74ad1f7b-73212-PK000402-01 | standard |
| SV007924 | Savco Vegetation Services Pty Ltd | C00309459.pdf | 1 | 16,800.00 | 16,800.00 | TIE | 1 | 448750f0-73212-PK000482-01 | standard |
| INV-47435 | Heritage Tree Services Pty Ltd ATF Rowan Family Trust | C00307253_2.pdf | 2 | 22,800.00 | 22,800.00 | TIE | 2 | f55cece3-73212-PK000477-01 | standard |

Total captured $107,164.30 ex GST; every invoice reconciles to its printed subtotal to the cent and its printed GST is 10% of the subtotal. All five register lines were Tier 3 Unidentified at v3 and are Confirmed, Tier 1 at v4 with all three rule 17 checks TRUE.

## 4.0 Findings

1. **Printed PK versus PK charged (three invoices).** 11913 prints PK000400 (the Zone 6 mowing task) for Zone 1 works charged to PK000422; INV-00042754 prints PK000446 (not a FY2026/27 branch WO Task) against PK000402 Cemeteries; SV007924 prints PK000477 (roadside trees) for Oak Park works charged to PK000482 (parks trees). In each case the invoice text supports the PK charged; recorded in the coding note and Open_Items, verdict Correct, no financial effect.
2. **Glascott entity.** The letterhead prints Technigro ABN 97 001 281 572; APLEDGER GLA009 carries the same ABN, so the creditor record is Glascott Landscape and Civil Pty Limited (resolves the entity limb of B-019).
3. **Savco ABN printed ungrouped** (78161366749); the register carries the grouped form, the green block the printed form.
4. **ETSol continuation rows.** Site addresses and qualifiers wrap onto the row below the priced row; they are NARRATIVE with a continuation note (Xero trap, schema section 8). Negative "partial deletion" lines are captured as printed and net inside the subtotal.
5. **Duplicate screen (rule 12).** None of the five invoice numbers exists in the branch or PS_WP v127 Evidence_Invoices; none of the file md5s had been received before.
