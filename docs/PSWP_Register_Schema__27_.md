# PSWP Register Schema and Build Conventions (LEAN core, v127 workbook, 9-Sep-2026)

Project knowledge file, and the ONLY schema file that belongs there. Build history for v10 to
v122 lives in `PSWP_Register_Schema_HISTORY.md`, which ships in the session zip and is read
only when a historical question arises.

POSITIONS ARE READ FROM THE WORKBOOK CONFIG SHEET (rule 19.6). Every position quoted here is
illustrative; Config is authoritative, and **Config carries duplicate keys, so a reader must
take the LAST occurrence** (`CL_DATA` appears at row 23 as `5:22937` and again at row 937 as
`5:27198`; taking the first addresses 4,261 fewer rows than exist).

Toolkit companions, all shipped in the session zip and none of them in project knowledge
(rule 19.1): `pswp_build_lib.py` (foundation, Config, recalc, citation scanner),
`pswp_json_repair.py` (families F1-F13 and the gate), `pswp_parsers.py` (raw-text route),
`pswp_build_batch.py` (rule 20 capture build), `pswp_ident_batch.py` (identification build),
`pswp_line_restructure.py` (F9), `pswp_verify.py` (verify sweep), `pswp_bounds_audit.py`
(bounds limb), `pswp_shingle_check.py` (rule 19.2 verbatim check), `pswp_dup_screen.py`
(rule 12 screen), `pswp_selftest.py` (regression harness), `pswp_session_report.py`,
`lo_recalc.sh`, and the procedure in `PSWP_Build_From_Corpus_Prompt_v2.md`.

## 1. File identity

- Current: `PS_WP_Transaction_Register_3FY_v127_CANDIDATE.xlsx` (~24MB). Register: 31,360 data
  lines (rows 5:31364), 146 columns, header row 4, control total row 31366 col T =
  $16,905,152.37, which must never change on a capture, identification or enrichment build.
  Assessed scope $15,668,203.13 across 27,988 lines (FY2023/24 and FY2024/25 at service code
  20392 only; FY2025/26 section-wide from v118). FY2026/27 memo $1,236,949.24 across 3,372
  lines, P1-3 both sections.
- **v127 is a CANDIDATE, not a handover version.** The Nature Categories and Details of
  v126 and v127 were authored in their build briefs and have not been ruled on. It passes verify, the bounds audit
  and the shingle check.
- Fonts Cambria; money `$#,##0.00;($#,##0.00);"-"`; dates `d-mmm-yyyy`; live formulas only
  (SUMIFS/COUNTIF/INDEX/MATCH; never XLOOKUP/FILTER/SORT).
- Recalc: LibreOffice convert route only (`soffice --headless --convert-to xlsx`, isolated
  profile, `OOXMLRecalcMode=0`), 75-80 s. `recalc.py` (macro route) hangs and is banned.
  Reads via python-calamine, writes via openpyxl.
- 53 sheets. Handover | Method | Theme_Map | Register | Themes | PK000022 | Vendor_Series |
  Summary | Sites | Site_Crosswalk | Site_Allocation | PK_Listing | Coverage | Open_Items |
  Creditor_Lines | SE2_Budget | FY2526_Wide | Evidence_Invoices | Evidence_Invoice_Lines |
  Data_Acquisition | Config | Project_Instructions | Vendor_Boilerplate | Freeze_Log |
  Council_Sites | Park_Assets | Park_Asset_Items | Site_Equipment | Vendor_Asset_Leads |
  Site_Inspections | Insp_Issues | Insp_Assets | Theme_Map_v3 | Themes_v3 | Line_Kind |
  Charge_Source | Evidence_Coverage | Confirmation_Ladder | Journal_Provenance |
  Unpaired_Accruals | Net_Zero_Journals | Priority_Pull | Journal_Pull | Harpley_Pull |
  Journal_Sources | Clearing_Suspense | Correspondence | Treatment_Decisions |
  Procurement_Route | Theme_Review | Site_Geo | EIL_Controls | Controls.

## 2. Register column map (1-indexed)

Analysis block:
1 LineKey | 2 Section code | 3 Section name | 4 Doc Date | 5 FY loaded | 6 FY posted |
7 FY service | 8 Reference | 9 Doc Type | 10 Source | 11 Creditor Code | 12 Contractor |
13 ABN | 14 Natural Account | 15 Nat Acct Name | 16 PK Header | 17 PK Charged | 18 PK basis |
19 (id) | 20 Amount ex GST | 21 Amount incl GST (est, `=ROUND(T{r}*1.1,2)`) | 22 Narration
(GL line) | 23 Enquiry Narration | 24 Nature Category | 25 Nature Detail | 26 Theme (lookup on
Theme_Map A5:A31) | 27 Nature Basis | 28 Evidence | 29 Evidence Tier | 30 Attachment in
TechOne | 31 Coding Verdict | 32 Coding Note | 33 Status | 34 Follow-up

Parsed references: 35 Contract Ref | 36 DM Ref | 37 Quote Ref | 38 Work Ref | 39 REGO |
40 Toll TAG | 41 Retailer Acct | 42 Site/supply point (hard 40-char TechOne field) |
43 Person Named | 44 Standing Order flag

Enquiry block: 45-53 (Enq Amount incl GST, GST Date, Due Date, Outstanding, Applied, Ageing,
On Hold, Payment Details, Billing System)

Grey source block (verbatim, never touch): 54-87. At v13 the 26SLACT layout mapped by NAME,
not position (CurrencyAmount to 61, ATBatchName to 69, ATDImageFilename to 72).

Green evidence block: 88-127 (`Config!GREEN_BLOCK_COLS`). Site: 129 (DY), site basis 130 (DZ),
Theme group v3 131 (EA).

## 3. Rule 17 green evidence block (cols 88-127, CJ to DW)

88 Ev Invoice ID | 89 Vendor | 90 ABN (verbatim incl. mis-groupings) | 91 ACN | 92 Vendor
address | 93 Vendor phone | 94 Invoice Date | 95 Due Date | 96 Purchase Order | 97 Contract # |
98 Bill To | 99 Ship To | 100 Requesting Officer | 101 Request Date | 102 Request Via |
103 CR/WO # | 104 PK # as printed | 105 PK normalised | 106 Site Details | 107 Site Contact |
108 Work Description | 109 Technician | 110 Line count | 111 Line items (verbatim) |
112 Works carried out | 113 Printed Sub Total ex GST | 114 Printed GST | 115 Printed Total incl
GST | 116 Payments Made | 117 Balance Due | 118 Payment details (or a `BP:` key) | 119 Terms
(or a `BP:` key) | 120 Pages | 121 Lines sum ex GST (live) | 122 Chk lines = printed subtotal |
123 Chk register = printed subtotal | 124 Chk printed GST = 10% | 125 Source file | 126
Captured stamp | 127 Anomalies & capture notes

Conventions:
- Fields printed blank become the literal `(blank as printed)`. Fields the layout does not
  carry become `(not printed)`. Never filled from another source.
- Col 121: `=ROUND(SUMIF(EIL_Invoice,CJ{r},EIL_Amount),2)`. One shape on every sighted row, no
  literal row bound, criteria always relative (v123 onward).
- Col 127: any check-variant line MUST contain the literal tag `[check variant]`. Control
  minimum `VARIANT_TAG_MIN` = 933; the workbook holds 941 at v126.
- Vendor boilerplate is stored once on `Vendor_Boilerplate` and cited by `BP:` key from cols
  118 and 119 (rule 17 Amendment 2). 131 keys at v126, and a control proves every cited key
  exists.
- **OPEN DECISION.** Col 111 currently keeps the whole printed row inside each item string, so
  the amount appears twice, once in the verbatim row and once in the parsed
  `qty @ unit = amount` tail. Verbatim and rule-16 safe, but noisier than the older rows. Trim
  to the text left of the numeric bands, or keep the whole row.

## 4. Check formulas, standard and ratified variants (Method 11.0)

Standard: 122 `=IF(DQ{r}=DI{r},...)` | 123 `=IF(ROUND(T{r},2)=DI{r},...)` |
124 `=IF(DJ{r}=ROUND(DI{r}*0.1,2),...)`.

Variants, each requiring the `[check variant]` tag: check 1 incl-GST basis; check 2 one-cent
tolerance; check 2 derivation equality (incl/1.1); check 2 split-posting (ties by LineKey);
check 2 SUM-TIE (v23); check 2 PARTIAL-SCOPE (v32); check 3 GST-free; check 3 rounding
tolerance (1c, 2c per-line baskets). `pswp_build_batch.chk_formulas()` is authoritative for
the exact shapes and is what a build writes.

TRAP: never write a bare `ABS(x)<=0.01`; binary floats store 0.01 as 0.01000000002. Always
`ROUND(ABS(...),2)<=`.
TRAP: Python `round()` is banker's; Excel ROUND is half away from zero. Pre-compute with
`Decimal(...).quantize(..., ROUND_HALF_UP)`, or a printed GST of $150.54 on a $1,505.35
subtotal falsely flags.

## 5. Evidence sheets (layout; positions from Config)

**Evidence_Invoices**, 32 columns, header row 4. Data `5:3875` (3,871 invoices). Totals row
3877. Rule 17 control block `3888:3901`, twelve controls, all must read TRUE to ship.
Cols: 1 Invoice | 2 Vendor | 3 ABN | 4 Invoice Date | 5 Due Date | 6 LCC Reference |
7 Contract/Quote | 8 Site(s) | 9 Lines | 10 Ex GST | 11 GST | 12 Incl GST | 13 Verification |
14-31 staged register-block fields | 32 Staged source and capture stamp.
Register-captured invoices carry the col-14 marker
`Complete on the register line (green block, columns CJ to DW)`.
EvID prefixes: `INV-000xxxxx` Harpley, `KC-` Kachel, `QP-` Q Power, `DRL-` Robinson, `EDSS-`,
`HT-` Hilltops, `LBL-` Lockwise, `ELM-`, `T2-`, `LED-`, `TCS-`, `MJR-`, `HIG-`, `BW-`, `UFF-`,
`CALDME-`, `BLC-`, `CLM-`. SECUREcorp `QLDPSI...` ids and printed `INV-#` ids stay as printed.

**Evidence_Invoice_Lines**, 13 columns, header row 4. Data `5:9517` (9,513 lines).
A Invoice | B Line | C Description (verbatim) | D Qty | E Unit Price | F GST | G Amount ex GST
| H PK as printed | I PK normalised | J Register LineKey | K Notes | L Site (printed line) |
M Site basis. Template-B amounts in col G are AS PRINTED (GST inclusive) and their recon rows
test against the printed Total Inc GST.

**EIL_Controls** (sheet 52), the rule 17 check-1 per-invoice panel, relocated here from
`Evidence_Invoice_Lines` at v123. Rows `5:3875` (3,871 controls), summary row 3877.
A invoice id | B `ROUND(SUMIF(EIL_Invoice,$A{r},EIL_Amount),2)` |
C `INDEX(EI_ExGST|EI_InclGST,MATCH($A{r},EI_Invoice,0))` | D basis | E the literal TRUE.

**Sighted position at v127:** 3,740 register rows carry Nature Basis `Sighted invoice line`,
every one with an Ev Invoice ID and all three checks TRUE. GST-inclusive allowance
`GSTINC_ALLOWANCE` = $46,420.92.

## 6. Other sheets

- **Theme_Map**: categories A5:A31 to themes B5:B31. Nature Category values written to Register
  col 24 MUST exist in A5:A31, matched EXACTLY (COUNTIF is case insensitive, so a case variant
  counts but reads wrong).
- **Vendor_Series**: labels written to Register col 12 must match exactly. Data blocks with
  totals row 68; dated footnotes carry the identity history.
- **Open_Items**: header row 4. 435 populated rows at v126. **The two items raised by the v126
  build are appended without numbers and need numbering against the live tail.**
- **Data_Acquisition**: single-column text, sections F1 onwards, each logging the source, the
  extraction tool identity and the md5. This is what rule 12 screens against.
- **Coverage**: Panel A rows 7:157, total row 165, panel C to 194.
- **Controls** (sheet 53, last tab): 65 controls in seven groups, rows 8:72, master verdict at
  `Controls!B4`.
- **Config**: key/value, 938 rows. Current positions: `REGISTER_DATA 5:31364`,
  `REGISTER_TOTAL_ROW 31366`, `CONTROL_TOTAL 16905152.37`, `EI_DATA 5:3875`,
  `EI_TOTALS_ROW 3877`, `EI_CONTROL_ROWS 3888:3901`, `EIL_DATA 5:9517`, `EIL_END 9517`,
  `EIL_CONTROLS_SHEET 5:3875 summary 3877`, `RECON_COUNT 3871`, `SIGHTED_COUNT 3740`,
  `CL_DATA 5:27198`, `CONTROLS_COUNT 65`, `BOILERPLATE_KEYS 131`,
  `GSTINC_ALLOWANCE 46420.92`, `VARIANT_TAG_MIN 933`.
  **Two Config defects to clear in the next housekeeping build:** `WORKBOOK_VERSION` still
  reads `v123` while `WORKBOOK_VERSION_V125` reads `v125`, and `VARIANT_TAG_MIN` is 933
  against 941 actual tags.

## 7. Build mechanics (see `pswp_build_lib.py`)

- Read/edit with openpyxl for writes; read values with calamine. Register reads: header row 4,
  data row = index + 5.
- Styles: copy `cell._style` via `copy.copy` from a template row. Setting `.value` on an
  existing cell preserves its style, so analysis-column upgrades need no style work.
- One build script per session (rules 18 and 20), one save, ONE convert-route recalc, one
  verify pass reading the RECALCULATED file and requiring exact `"TRUE"`. **A partial run is
  discarded and re-run from the top, never resumed** (rule 19.7 as amended v11): the driver
  writes to a scratch name and promotes only on a clean verify.
- Duplicate-upload check before any parse: md5 against Data_Acquisition.
- Cell text cap 32,767: condense whitespace runs only, and note where length forced a trim.
- **Memory.** LibreOffice is OOM-killed on a 4GB box if openpyxl's object graph is still
  resident, and an OOM-killed recalc is SILENT: the log simply stops. Drop the workbook and
  collect before converting.

Build cost, measured on v122 and unchanged at v126 (24MB packed, 214,258 live formula cells,
one CPU): openpyxl load 51.8s (30%), openpyxl save 39.8s (23%), convert-route recalc 75.3s
(44%), calamine read 3.5s, verify sweep 4.2s. Full v126 chain: 210s.

## 8. Register-matching logic

- Reference (col 8) carries invoice numbers directly; Harpley keeps leading zeros. References
  can TRUNCATE long numbers (TCS 17118059 posts as `171180`), so check truncation before
  declaring a non-match.
- Green-block AP lines only (`Doc Type = PUR Cred Invoice`). A credit note posts as
  `Creditor credit note` and needs a `doc_type_allowed` exception declared in the brief.
  Journals rest on pairing (rules 6 and T9) and are never green-blocked.
- Target row: the AP row whose amount equals the printed subtotal within a cent, or the
  incl/1.1 derivation. Multi-line postings all get the block with the split variant.
- Zero-amount companion AP rows: no green block; a Coding Note cross-references the sibling
  LineKey, and ONLY where the reference has exactly one non-zero AP row.

## 9. Standing traps and facts

- **Kachel PAR/377/2025** prints a four-way PK split (PK000028 $19,716, PK000029 $16,683,
  PK000026 $6,478, PK000025 $6,066) plus a $5,243 sanitary-bin line carrying no PK, while the
  ledger posts each $54,186.00 invoice whole to a single PK, and which PK varies by month.
- **PoolShop** bills one monthly invoice split across five PKs but the GL charges PK000022 in
  full (Open Items #41, both prior FYs).
- **Hilltops** invoices are GST-FREE; TechOne posts incl/1.1, creating a phantom GST credit.
- **Harpley template B** (`Your Order No:` header) prints line amounts GST INCLUSIVE.
- **SECUREcorp** wraps a patrol line over three physical rows: the rate and amount print on the
  first, `1 Months` on the second, the description tail on the third. Extractors type all three
  NARRATIVE and lose the amounts. Family F12.
- **Kachel** prints dollars and cents in SEPARATE columns (`19,716        00`). The figure is
  reconstructed; the row text is never edited.
- PK typo normalisation: PK00022 = PK000022, recording the printed form alongside.
- LCC's own ABN 21 627 796 435 prints as the bill-to and extractors grab it as the vendor ABN
  (family F3). The vendor ABN is on the letterhead or in the footer.
- PLAY FORCE PTY LTD (69 106 457 176) is not Play Force Australia Pty Ltd (89 677 476 541).
  Same for the two BrizSouth locksmith entities. Xero `INV-#` references are shared across
  vendors and years, so target selection is by amount.
- **The leading-zero false match.** Harpley prints eight-digit ids and Q Power five, so a bare
  `endswith` makes Q Power `14725` look like an already-captured Harpley `00014725`. Screen on
  the vendor as well as the digits, or five real captures are lost (v119).

## 10. Settled decisions (do not relitigate)

- **The recalc is not the bottleneck; openpyxl is.** A second openpyxl open costs 51.8s for an
  answer calamine returns in 3.5.
- **The verify sweep is free and must never be traded**, 4.2s against a 210s chain.
- **The prior-FY formula freeze was tested and rejected**: 3% saving for permanently disabling
  self-testing on 6,565 rows. The pending ratification in Project Instructions section 5 should
  be struck.
- **Direct OOXML part patching** (v123, v125) ran the chain in 73-96s against 167s for the
  openpyxl route. It is a rule 19.8 deviation and must be disclosed each time; verification
  reads stay calamine against the recalculated file.

## 11. v123, defined names, EIL_Controls, the bounds limb

Defined names introduced at v123 (the workbook previously had none but two
`_xlnm._FilterDatabase` entries). At v126:

| Name | Range |
|---|---|
| `Reg_Data` / `Reg_Amount` / `Reg_FY` / `Reg_Site` / `Reg_EvID` | `Register!...$5:$31364` |
| `EIL_Invoice` / `EIL_Amount` / `EIL_GST` / `EIL_LineKey` | `Evidence_Invoice_Lines!...$5:$17000` (headroom beyond data end 9,517) |
| `EI_Invoice` / `EI_ExGST` / `EI_InclGST` | `Evidence_Invoices!$A$/$J$/$L$5:3875`. **No headroom possible**: the totals row sits at 3877 and the control block at 3888:3901 (Open Item 429) |
| `JP_Ref` / `JP_Net` | `Journal_Provenance!$A$/$D$5:349` |
| `ThemeMap_Cat` / `ThemeMap_Group` | `Theme_Map!$A$/$B$5:31` |
| `ThemeMapV3_Cat` / `ThemeMapV3_Group` | `Theme_Map_v3!$A$/$B$5:33` |

**Sites rows 612:622 are data, not subtotals.** They are classification rows that partition the
register alongside panel A; `SITES_PARTITION` 5:622 is the block and the `SITES_GROUP_ROWS`
label is misleading.

**Rule 19.11 sweep.** Any move of a controls region must rewrite every panel citing its
absolute rows, explicitly, never by positional shift or blanket regex.

## 12. v124, the Controls sheet

65 controls in seven groups, rows 8:72, master verdict at `Controls!B4`, TRUE only when no
control reads FALSE **and** the count of TRUE results equals the registered count, so a control
that goes missing fails as loudly as one that breaks. Column E is always a reference or a count
over a control that exists elsewhere, never a restatement.

**TRAP: `COUNTIF(range,"TRUE")` coerces its criteria to a boolean and matches numeric 1s;
`COUNTIF(range,"FALSE")` matches numeric 0s.** Never count control results with COUNTIF. Use
`SUMPRODUCT(--(range="TRUE"))`.

## 13. v125, identification from six APLEDGER creditor histories

249 register lines moved to Tier 1, $1,637,376.52 ex GST, on reference plus amount (incl GST
within 2c of ex GST x 1.1) plus document date. Standing identities added: SEC009 SECUREcorp
(QLD) Pty Ltd 76 108 335 155; HIG010 Higgins Coatings Pty Ltd 50 005 632 708; WEI013 Weis
Contractors 71 812 055 648; ENV051 The Trustee for E W C S Unit Trust (t/a Enviro Sweep)
52 067 331 460; ELE013 Elemental Shade Structures 99 292 107 173; KAC001 Kachel Cleaning
77 083 786 592.

**THE RECALC TRAP.** The convert route does not recalculate unless the isolated profile carries
`OOXMLRecalcMode=0`. A fresh profile has no such setting, LibreOffice loads the cached values,
and the file ships with every formula stale. The first v125 run passed all 65 cached controls
while six Vendor_Series counts still read their pre-build values. **Every verify pass must pin
at least one figure the build is supposed to MOVE**, because a cached pass is otherwise
indistinguishable from a real one.

## 14. v126, batches 11 and 112, and the rebuilt toolkit

**What was written.** 48 documents captured: 25 Harpley Services invoices (Batch 11,
$15,648.02 ex GST) and 23 SECUREcorp and Kachel Cleaning documents (Batch 112, $860,481.57 ex
GST net of credit note QLDPSCR0005135). 481 evidence lines, 48 register green blocks, 48 new
EIL_Controls rows. Control total unchanged. Chain 210 seconds, 65 of 65 controls TRUE.

**Batch 112 shipped RED** on eleven P2 wrapped-description defects and was repaired to GREEN
under family F12 before any build: 23 rows reclassified, $31,375.41 restated from retained page
text. Every evidence stem was also rebuilt, because all 23 had been hard-truncated through the
amount, which breaks the rule that the amount is never trimmed.

**Structural moves.** `EI_DATA` 5:3766 to 5:3814, totals 3768 to 3816, controls 3779:3792 to
3827:3840; `EIL_DATA` 5:8952 to 5:9433; `EIL_CONTROLS` 5:3766 to 5:3814, summary 3768 to 3816;
`SIGHTED_COUNT` 3,633 to 3,681; `RECON_COUNT` 3,762 to 3,810; the three `EI_*` defined names
repointed to 3814.

### Traps found this build

- **A range endpoint inherits its sheet from the endpoint before the colon.** In
  `Register!$DW$5:$DW$31364` the second endpoint carries no prefix but is still on Register.
  Treating it as local stretched two Evidence_Invoices controls 48 rows past the register data
  block. The counts stayed right, nothing failed, and **only the bounds audit saw it.**
- **The group-6 error sweeps cite each sheet from row 1 to its last row**, so after a build they
  stop sweeping exactly the rows the build added. Every Controls formula must be repointed.
- **SPANNING needs a harm test.** A control that sweeps a block for the text `TRUE` and crosses
  a totals row counts no amounts. Only a range that is SUMMED into a total fails.
- **`Flagstone` contains `gst`.** A substring label test types a priced row TOTALS and closes
  the table region on it, losing every row beneath. Match labels on word boundaries. The same
  trap sits under `Mobile Patrols` and a bare `mobile` contact filter.
- **`Contract #: LCC-09-2022` yields -$9.00** if a money token may be glued to a hyphen.

### The verbatim hole, and the check that closes it

A gate proves AMOUNTS, not WORDING. A corpus can tie to the cent on every invoice and still
carry a description the page never printed. Every arithmetic check stays TRUE, rule 16(a) is
broken anyway, and nothing else notices. `pswp_shingle_check.py` cuts every captured
description into five-word shingles and looks for each on its own page. Whitespace is the only
thing normalised: case, punctuation, spelling and the supplier's typos are part of what was
printed. At v126: 2,445 shingles, zero failures, corpus and workbook both verbatim.

### Cross-validation standing at v126

The raw-text route (`pswp_parsers.py`) independently reproduced both binders from page text:
23 and 25 documents, all tying, $860,481.57 and $15,648.02, with page ranges identical document
by document. `pswp_ident_batch.py` re-run against the payload v125 already applied produced
zero new writes. `pswp_selftest.py` runs all thirteen of these checks in about 100 seconds and
should be run after any change to any module.

## 15. v127, batches PLA1 and weis11

**What was written.** 61 documents captured: 27 Play Force Australia invoices ($329,296.11 ex
GST) and 34 Weis Contractors invoices ($300,689.83 ex GST). 84 evidence lines, 59 register
green blocks, two rule 16 holds. Sighted 3,681 to 3,740. Control total unchanged. Chain 195
seconds, 65 of 65 controls TRUE, bounds PASS, shingle check PASS on both batches.

**EvID overrides, Method 34.2.** `WC-2315`, `WC-2372` and `WC-2525`. Those printed ids are
already held as Play Force Australia captures dated Feb and Mar 2025, and the Xero `INV-#`
series is multi-vendor (rule 8). The workbook had no duplicate EvIDs before this build and
still has none. Precedents: WC-1582, CMS-1676, FD-0206, PF-5278. **The override goes on the
colliding id only, not the whole batch.**

**Two rule 16 holds, no green block.** `INV-7613` prints only "As per quote 700172" and
`INV-8009` only "As per emailed Quote"; both quotes are absent from the binder. A generic
printed line cannot restate nature, so the rows stay Partial under rule 17 Amendment 1. Their
Evidence_Invoices col 14 records the hold and its reason rather than the completion marker.

**Categories follow register precedent, not a fresh reading.** Weis "machine clean sand soft
fall" is Playground surfacing (2 of 2 on the register); Play Force rubber and softfall repair
is Playground inspection & repair (9 of 11, and 175 of 178 Play Force rows overall).
Categorising the same work two ways across one vendor is how a thematic series stops being
comparable.

### Traps found this build

- **A printed RATE is not an amount.** Several Weis templates print the GST column as `10%`.
  Family F2 tried to coerce it and **crashed the gate on the first Weis invoice**. Coercing it
  would also have destroyed a printed field (rule 16a). F2 now leaves a rate as printed, and
  a `gst` value that is neither amount nor rate raises P8.
- **An evidence stem can end in the right amount and still be unusable.** PLA1 shipped
  `PlayForce Toped up t 26-Sep-2025 5709.73`, with no separators and a purpose cut mid-word;
  weis11 shipped `WEIS com.au Division 16 Jul 2025 6931.87`, having taken an email domain for
  the business name. Family F13 now also requires the four comma-separated fields, and the
  40-character cap falls on the business name, never the amount.
- **An EvID override has to reach the audit tools too.** The shingle check looked its
  captures up by printed id, found the OTHER vendor's invoice of the same number, and
  reported a verbatim failure that was really a lookup failure. It now takes an EvID map.
