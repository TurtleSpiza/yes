# Parks Branch Register Schema (v4 workbook, 11-Sep-2026)

Working aid for `Parks_Branch_Transaction_Register_FY2627_v4.xlsx`. Config is authoritative for positions (one occurrence per key); Method states structure (rule 14).

## 1. Identity
- Scope: Branch 4090000, LCC OP/AP O110-O115, expense type 1, 27SLACT P1-3 (pulled 11-Sep-2026 10:11). Control total $4,910,566.68, 6,683 lines.
- Register header row 4, data 5:6687, total row 6689 col T (unchanged since v1). 148 columns: PS & WP map 1-146 unchanged, 147 (EQ) Src Note, 148 (ER) Register provenance ("Inherited from PS_WP register v127" | "New at branch v1 (not in the PS_WP register)").
- 26 sheets. Controls last, 82 controls at v4 (78 through v3, plus group 7 creditor histories), master verdict Controls!B4.

## 2. Build chain (rule 19.7)
`python3 pbr_build.py` runs stage (pbr_stage.py, rules in pbr_rules_v1.json, creditor histories in pbr_histories_v4.json) -> openpyxl write-only -> convert-route recalc (OOXMLRecalcMode=0) -> calamine verify -> ship. Scratch is wiped at start; nothing ships without a clean verify. Chain ~35 s at v4 (Creditor_Lines carries 19,703 history rows). Needs `libreoffice-calc` and `poppler-utils` installed, not just `libreoffice-core`; a missing Calc component fails the convert route with "source file could not be loaded" on any file. Launch detached with `(setsid nohup python3 -u pbr_build.py > build.log 2>&1 < /dev/null &)`; a plain `nohup ... &` is killed when the tool call returns.

## 3. Inheritance (Method 5.0)
- Key: Document Unique ID + full account + NA + Work Order + amount + Details (newlines as " | "). One-for-one. 3,365 of 3,372 v127 FY2026/27 lines; 7 absent (Inheritance_Log).
- Account string is in the key on purpose: a payroll line re-mapped from 20361 to 20151 matched on everything else and would have carried the wrong section.
- Rule 17 check formulas regenerated from v127 shapes with row references remapped; Register col 28 and EI col 13 restated from the EvID maps; v127 EI text kept in EI col 33.

## 4. Classification engine for new lines (Method 6.0)
Source type -> contractor/basis/tier/status/verdict; account governs single-purpose NAs; on contract NAs (73111, 73123, 73126, 73128, 73211, 73212) narration class, then service class (P1S service governs, branch extension), then P6. Journal pairing by reference across the branch in Decimal. AP never Confirmed. Tier 2 routes: creditor line (ref + incl within 2c), narration-named payee/company, supplier named in a Council recode journal corroborated by equal-and-opposite reversal legs or by a fuel-levy recode off the same PK.

## 5. Taxonomy extensions (Method 7.0)
Theme_Map v2 rows 32-54: 23 categories, new themes T14 People, training & corporate; T15 Trees & natural areas; T16 Cemeteries. Theme_Map_v3 rows 32-36: groups 10 Trees & natural areas, 11 Cemeteries, 12 People & corporate, 13 Refunds & recoveries.

## 6. Traps found this build
- A controls sweep over Handover is circular (Handover cites Controls!B4). Never sweep a sheet that reads the master verdict.
- Blank criteria: blank WO Task is written as "(no WO Task)" in col P so SUMIFS never needs an empty-cell criterion; the SE2 blank-key row ties to it.
- Wildcards: purchase-card merchant labels carry `*` (MYO*AUSTRALASIAN CEMET). Vendor_Series criteria are escaped (~ * ?) in col B and grouped case-insensitively.
- Evidence Tier arrived as 2.0, "2" and "Tier 1" on inherited lines; canonicalised to integers or COUNTIF double counts.
- The monthly accrual narration prints "July 2027" for FY2026/27; FY (Service) reads the posting year on new lines, 34 inherited lines still read FY2027/28 (Open Item B-015).

## 7. v2, Batch mixed_1 capture (11-Sep-2026)
- 29 invoices, 30 green blocks (INV-39235 SUM-TIE pair), 413 evidence lines (358 priced, 55 Glascott ATTACHMENT rows with no col G amount), 13 new BP: keys (BP:LEV-P1 reused from v127 by text match). Sighted 141 rows over 139 invoices. Control total unchanged. Chain 18 s, 78 of 78 controls TRUE.
- Capture is brief-driven: `pbr_capture.py` reads `corpus_mixed_1_v6.json` and `match_mixed_1_v6.json`; categories, EvID prefixes, header-field extractors and boilerplate are data per vendor template. Formulas per variant in `pbr_capture.formulas`.
- Match precedence (trap): exact, then SUM-TIE, then derivation equality (incl/1.1), then 1c tolerance. A 2c difference that is exactly incl/1.1 is a derivation case, not a tolerance case (INV-0600 failed check 2 under the wrong label on the first run).
- Check 3 per-line rounding basket variant: `ROUND(SUMPRODUCT((EIL_Invoice=CJr)*ROUND(EIL_Amount*0.1,2)),2)` evaluates under LibreOffice; used on 7 documents.
- BP: keys must be screened against the inherited Vendor_Boilerplate keys by text before numbering, or the same vendor gets a second key for identical text.
- Evidence_Invoices carries a 33rd column, provenance, for every row (v127 row and original verification text, or the capturing batch).

## 8. v3, Batch mixed_new_26_27 capture (11-Sep-2026)
- 33 invoices, 35 green blocks (Coast2Coast INV-11834/11835 split-posting pairs, Origin 1026099/1026231 partial-scope), 632 evidence lines total across both batches, 26 new BP: keys. Sighted 176 rows over 172 invoices. Control total unchanged. Chain 23 s in the session, 37 s from a cold cache. 78 of 78 controls TRUE.
- Rule 12 re-sightings skipped: Sea-Crete 7558 (SC-7558, inherited) and Austspray 158853 (v2). Origin 1026231 duplicate occurrence (pages 11-15) marked duplicate_of.
- 31 of the 35 green blocks sit on lines inherited from PS_WP v127 (Park Services and Water Parks). Register col ER reads "Inherited from PS_WP register v127; sighted at branch v3 (port the capture to PS_WP v128)". Open Item raised: port them so the two registers agree.
- New variants: check 2 by LineKey (`SUMIFS(EIL_Amount, EIL_Invoice, CJ, EIL_LineKey, A)`) for split-posting and partial scope; Origin check 2 derivation on the site row (`(ex + site GST)/1.1`) and check 3 per-site GST (`SUMIF(EIL_Invoice, CJ, EIL_GST)`), with each site's printed GST captured in Evidence_Invoice_Lines column F. Consolidated-invoice lines outside Parks scope carry the LineKey text "(outside Parks scope, not a register line)".
- Templates added in `parse_mixed_new.py`: Origin consolidated (site rows, CR credits captured negative), Sea-Crete, Pool Shop (old and new Xero), Q Power (wide simPRO layout; item names wrap onto the rows above and below at column 177), Play Force (item table plus two T&C pages), Flavell-Dau (old and new Xero), Weis (old and new Xero), Elemental (Total column is GST inclusive; ex = Total less GST), Higgins, Harpley (two-page with How-to-pay page; header block captured to cols 100-109), Coast2Coast (new Xero), Kachel (four-way PK split plus sanitary bins).
- Trap: a numeric-only Xero row belongs to the description line immediately above it; description lines below the numbers are continuation text and stay NARRATIVE.
- Trap: Weis prints its ABN grouped on the old template and ungrouped on the new one; Vendor_Series shows both strings on one label. Canonicalise at the next housekeeping build.

## 9. v4, APLEDGER creditor histories and Batch attach_1 (11-Sep-2026)
- Eight APLEDGER creditor histories (TechOne Ledger Accounts Transactions Table, Default Ledger Type AP, one Account per export) under `data/inputs_2026-09-11/creditor_histories/`, listed with code, label, ABN and label basis in `toolkit/branch/pbr_histories_v4.json`: GLA009 Glascott, ECO031 ETSol t/a Eco Technology Solutions, HAR073 Harpley, PRO066 Provac, HER025 Heritage Tree Services, SAV012 Savco, TRE010 Treescape, VIN003 Vinton Tree Services. 19,703 lines embedded verbatim on Creditor_Lines rows 378-20080 (col AB = export row, col AC = Y where matched); Config CREDITOR_LINES gives the split.
- Match rule (Method 12.0): reference equal; history incl GST within 2c of the document net x 1.1 summed over the Document Unique ID; history date within 120 days of the doc date; exactly one creditor code. The date test matters: numeric references collide across creditors (Harpley and Eco Technology Solutions both issued 11913). Tier 1 with the 11-digit ABN. Result: 786 lines, $1,368,141.33 ex GST, 0 ambiguous, 0 label conflicts; unidentified fell from $1,778,748.05 (1,218 lines) to $711,974.74 (538 lines, branch-wide label) or $748,185.75 (590 lines, every Unidentified label).
- Inherited PS/WP lines carried as Unidentified, series-inferred or vendor-inferred are identified too (49 Harpley lines, col ER "contractor identified at branch v4", Open Item B-026 port to PS_WP v128). A sighted invoice on the same line supersedes the identification (one line). Sighted lines are never re-identified.
- Rule 12 at v4: every history and PDF md5 screened against the PS_WP v127 Data_Acquisition and this register's inputs in the stage (gate, raises). HAR073 re-pull audited against the v127 embedded history: 1,463 rows in both, 0 v127-only, 4,232 new-only (2017 to Mar-2023 and Jul to Aug-2026), so a clean superset.
- Batch attach_1: five single-invoice TechOne attachment PDFs (EzeScan; the file name is the attachment id) parsed by `parse_attach1.py` (pdftotext -layout, templates ETSOL, GLASCOTT_LM, PROVAC, SAVCO, HERITAGE), gate GREEN, 254 shingles clean, `match_attach_1_v6.json` with coding verdict, note and follow-up per invoice as data. 5 green blocks, all standard, 181 sighted rows over 177 invoices. Corpus schema addition: `source_md5` per document; `pbr_capture` cites the document's own `source_file`.
- Gate amendment: `pswp_json_repair` P9 tests page coverage per source file when a corpus carries several files (a one-PDF-per-document batch used to fail P9 on overlapping page ranges). Earlier corpora unchanged, still GREEN.
- Correction to the v3 match table: register line f386b8d0-73212-PK000415-01 (00015225, $240.00) had been tagged a cents companion of Q Power 15225; it is on another TechOne document and HAR073 shows it is Harpley invoice 00015225. Tag withdrawn (evid_note on the entry); the line is now Harpley, Tier 1, Partial.
- Printed PK versus PK charged on three of the five invoices (11913 PK000400 v PK000422; INV-00042754 PK000446 v PK000402; SV007924 PK000477 v PK000482): invoice text supports the charge each time; coding note on the line, Open Item B-027, verdict Correct. PK Charged never moves off the ledger Work Order (rule 1).
- Trap: two COUNTIF calls with "Y" and "y" double count (case-insensitive); one control shipped FALSE on the first run for that reason. One criterion per case-insensitive value.
- Trap: a line identified in the stage and captured later in the same stage would carry both flags; the sighted flag must win before the build counts provenance (ident_v4 popped when col CJ is set).
- Identification queue: `toolkit/branch/pbr_unidentified_queue.py` reads the shipped register and writes `reports/Unidentified_Contractors_<ver>.md/.xlsx`: every Unidentified line grouped into (section, service, reference shape) series with one invoice to sight per series (largest line with a TechOne attachment: Document File, reference, date, amount, PK). Regenerate after every build.
