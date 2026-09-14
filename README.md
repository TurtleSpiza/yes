# LCC Parks transaction registers

Two Excel registers for Logan City Council Parks Branch expenditure, and the Python toolkit that builds and verifies them.

| Register | File | Scope |
|---|---|---|
| Park Services & Water Parks | `registers/PS_WP_Transaction_Register_3FY_v127_CANDIDATE.xlsx` | Sections 4090240 and 4090260, FY2023/24 to FY2026/27 (three assessed years plus a memo year). The record for the three-year audit. |
| Parks Branch FY2026/27 | `registers/Parks_Branch_Transaction_Register_FY2627_v12.xlsx` | Branch 4090000, all sections, FY2026/27 P1-3 at O110-O115. Inherits the PS/WP FY2026/27 analysis line by line and classifies the other sections itself. |

Both registers follow the same column map (PS/WP schema, 146 columns; the branch register adds two), the same rule set (`docs/PSWP_Project_Instructions_v11__1_.md`) and the same verification standard: a sighted invoice is captured at line level, every printed detail sits on the register line, and three live checks return TRUE before a line is Confirmed.

## Layout

- `registers/` the workbooks. Each is self-contained (source exports, evidence, instructions and controls embedded).
- `toolkit/pswp/` the PS/WP toolkit (`pswp_build_batch.py` and companions, `lo_recalc.sh`).
- `toolkit/branch/` the branch register toolkit: `pbr_stage.py` (load, inherit, identify from creditor histories, classify, capture), `pbr_build.py` (write, recalc, verify, ship), `pbr_capture.py` (rule 16/17 capture from a gated corpus), `pbr_rules_v1.json` (classification rules as data), `pbr_histories_v4.json` (APLEDGER creditor histories as data: file, code, label, ABN), `parse_mixed1.py`, `parse_mixed_new.py`, `parse_attach1.py` and `parse_attach2.py` (raw-text invoice parsers), `prep_code_corpus.py` and `prep_supplied_corpus.py` (prepare, restate from the retained rows where a header field is wrong, and fidelity-check a supplied third-party corpus), `pbr_recon_batch.py` (the Document Reconstruction journal route, rule 21), `pbr_unidentified_queue.py` and `pbr_journal_pull_report.py` (the identification queue and journal pull list reports).
- `batches/` per batch: the Copilot v5 corpus and report as received, the raw-text v6 corpus (page text retained, gate GREEN), the match table, capture report or hold record.
- `docs/` project instructions, PS/WP schema and history, the invoice extraction prompt (v6 is current; v5 is retained because two held batches were extracted under it), branch schema.
- `data/inputs_2026-09-11/` the 27SLACT ledger export (periods 1 to 3) and four SE2 exports the branch register was first built from; `data/inputs_2026-09-15/` the period 3 refresh and the two SE2 views re-pulled with it; `creditor_histories/` the twenty-six APLEDGER creditor history exports (v4 to v10); `journal_pulls/` the TechOne Document Line Table exports embedded on Journal_Sources; `reconstructions/` the TechOne Document Reconstruction exports embedded on Reconstruction_Sources.
- `reports/` derived reports regenerated from the shipped register: `Unidentified_Contractors_v12.md/.xlsx`, the identification queue with one invoice to sight per supplier series; `Journal_Pull_v12.md/.xlsx`, the rule 21 journal pull list, one row per TechOne document file.
- `cache/` scratch (calamine pickles, recalc output). Not committed.

## Session setup

Every web session provisions itself. `.claude/hooks/session-start.sh` runs before the session starts and
installs what the chain needs, then proves it:

| Dependency | Why |
|---|---|
| `python-calamine` | every workbook read (rule 19.8) |
| `openpyxl` | every workbook write |
| `lxml` | recovers rule 17 formula text from the v127 sheet XML |
| `cffi` | supplies `_cffi_backend` to the container's Debian cryptography; without it any cryptography import (pdfplumber makes one) panics the interpreter and takes the env check down |
| `poppler-utils` | `pdftotext -layout` and `pdfinfo`, the raw-text invoice route |
| `libreoffice-calc` | the convert-route recalc |

Pins are in `requirements.txt`, with an optional PDF-inspection set in `requirements-optional.txt` that
never blocks a session. The hook is idempotent: about four seconds on a warm container, and it installs
system packages only when they are absent. It exports `PYTHONPATH` for the two toolkit directories, so
`import pbr_stage` works from anywhere.

Verify the chain at any time, and after changing any dependency:

```
python3 toolkit/branch/pbr_env_check.py --all
```

It writes a workbook with a live formula, recalculates it through LibreOffice, reads it back with
calamine, round-trips a probe PDF through poppler, imports every toolkit module and byte-compiles the
toolkit. Seventeen checks, under two seconds, and it names the fix for whatever fails. **`libreoffice-core`
alone is not enough**: without the Calc component every conversion fails with "source file could not be
loaded", which reads like a corrupt workbook and is not.

## Rebuilding the branch register

Requirements are installed by the session hook above; `python3 toolkit/branch/pbr_env_check.py --all` confirms them.

```
python3 toolkit/branch/pbr_build.py
```

One script runs the whole chain: stage, write, LibreOffice convert-route recalc (isolated profile, `OOXMLRecalcMode=0`), calamine verify of the recalculated file, ship to `registers/`. It ships only on a clean verify (93 controls, every sighted line's three checks, the register total and a whole-workbook error sweep). A partial run is discarded, never resumed. About 35 to 40 seconds from a warm cache. Set `PBR_OUTDIR` to ship elsewhere; `PBR_INPUTS` and `PBR_V127` override the input locations.

## Capturing a new invoice batch

1. Copilot chat produces headers only for tabular invoices (see `batches/*/capture_report_*_v5.md`). Run the raw-text route instead: `PDF=path/to/binder.pdf OUT=batches/<batch>/corpus_<batch>_v6.json python3 toolkit/branch/parse_mixed_new.py` (add a vendor template if the binder carries a new layout). A corpus supplied under extraction prompt v6 runtime A (binder not supplied) goes through `python3 toolkit/branch/prep_supplied_corpus.py <batch> batches/<batch>/corpus_<batch>_as_supplied.json batches/<batch>` instead: register the batch and its vendor templates there, and it stamps the md5, restates only what the retained rows decide (R1 to R4, each logged per document), gates, and runs the per-vendor fidelity check.
2. Gate it: `pswp_json_repair.repair_and_gate` must return GREEN; run the five-word shingle check against the retained page text (`toolkit/pswp/pswp_shingle_check.py --corpus ... --out batches/<batch>/shingles_<batch>_v6.json`).
3. Author `notes_<batch>_v6.json` (coding note, verdict and follow-up per invoice; `nature_category` and `theme_v3` where the vendor prints several kinds of work), build the match table against the register with `pbr_match_table.py` (exact, SUM-TIE, derivation incl/1.1, one-cent tolerance, split-posting or partial-scope by LineKey), add the batch to `BATCHES` in `pbr_stage.py`, its stamp to `pbr_capture.py` (and to `SUPPLIED_GREEN` in `pbr_build.py` for a supplied corpus), run `pbr_build.py`, then regenerate `reports/` with `pbr_unidentified_queue.py` and `pbr_journal_pull_report.py`.

## Adding a creditor history

Drop the APLEDGER export (Ledger Accounts Transactions Table, Default Ledger Type = AP, one Account) into `data/inputs_2026-09-11/creditor_histories/` and add an entry to `toolkit/branch/pbr_histories_v4.json` (file, creditor code, canonical label, 11-digit ABN, label basis). The stage screens the md5 (rule 12), asserts the code and dominant ABN, embeds the history verbatim on Creditor_Lines and identifies every AP line whose reference, incl-GST amount (document net x 1.1 within 2c) and date (within 120 days) match exactly one creditor. Then run `pbr_build.py` and `pbr_unidentified_queue.py`.

## Capturing a journal batch

TechOne Document Line Table exports are the evidence route for a journal that carries no attachment (rule 21). Drop the exports into `data/inputs_2026-09-11/journal_pulls/`, run `python3 toolkit/branch/pbr_journal_batch.py`, author `batches/journal_1/notes_journal_1_v6.json` with what each document answers, then `pbr_build.py`. The driver screens every md5 (rule 12), keeps one copy of a duplicate export, maps each leg to its register line, proves each document nets to $0.00 and that every in-scope leg sum ties its journal reference's register net, and audits any document already embedded in the PS & WP register leg by leg rather than re-capturing it. The legs are embedded verbatim on `Journal_Sources`.

## Capturing a reconstruction batch

TechOne Document Reconstruction exports are the second evidence route into a journal (rule 21), and the one that reaches the Council-side counterparty legs. Drop the exports into `data/inputs_2026-09-11/reconstructions/`, run `python3 toolkit/branch/pbr_recon_batch.py`, author `batches/recon_1/notes_recon_1_v9.json` with what each document answers, then `pbr_build.py`. The driver screens every md5 (rule 12), keeps one copy of a duplicate export, maps each leg to its register line on the register's own `Src Account`, proves each document nets to $0.00 and that every journal reference it reaches has its in-scope legs tie that reference's register net with every register line matched, and audits any document already embedded on `Journal_Sources` from a Document Line Table pull rather than re-capturing it. The legs are embedded verbatim on `Reconstruction_Sources`.

Use a reconstruction where the pull list says a document carries no attachment and every branch leg is already narrated on the register: the Document Line Table adds nothing there, and the reconstruction adds the other side. Key each export to the journal's own Document Cross Reference, not to the document file, or the pull reaches one reference and leaves the rest of the file unevidenced (open item "Journal pull taken with a Document filter").

## State at v12 (15-Sep-2026)

Register total $5,066,518.69 across 6,872 lines, tied to both 27SLACT exports and to the SE2 by Branch and by Section views; 99 of 99 controls TRUE. 416 sighted lines over 409 invoices. Twenty-six APLEDGER creditor histories embedded (72,596 lines on Creditor_Lines). Confirmed $3,585,494.04; Partial $1,096,007.93; Pending evidence $385,016.72. Contractor unidentified $363,975.06 over 190 lines in 81 series; the queue with one invoice to sight per series is `reports/Unidentified_Contractors_v12.md`.

**v12** refreshed period 3. P3 was still open at the 11-Sep-2026 pull, so 27SLACT was re-taken for period 3 alone on the identical criteria and supersedes the P3 block of the first export. The register is the first export's periods 1 and 2 plus the whole of the second: 6,872 lines, $5,066,518.69, up 189 lines and $155,952.01. The substitution is gated before it is made: every one of the 1,124 superseded P3 rows must be present in the refresh verbatim across all 35 columns or the build stops, and all 1,124 were, so the refresh is purely additive. Register column ES (Source pull) names the export each line came in on, and no line in the refresh carries a reference already on Evidence_Invoices, so the 416 green blocks are untouched.

Only two of the five SE2 views were re-pulled. Branch and Section carry $5,066,518.69 and the control total ties to both; natural account, WO Task and service still carry $4,910,566.68, so Coverage panels A to C count only the 6,683 lines the 11-Sep pull carried and say so in their own headings (rule 11, declared asymmetry). Re-pulling those three views is the first item on the Data_Acquisition gaps queue.

The refresh answers three open items. **B-035** is resolved: GJ080985 reverses Kachel invoice 7719 off PK000028 and re-posts $3,530.00 to PK000429 and $630.00 to PK000028, the split the face prints, though the Tully Memorial Park share went to PK000429 (the 20394 overnight-stays WO Task used for the identical claim on 7712, PSWP-86) rather than the printed PK000030. **B-032** is resolved: GJ081002 recodes the last four Vinton fuel levy lines to PK000514 on 74189, so all eight sighted levy invoices are now on the levy account; the rate question behind it stands. New finding **B-036:** GJ080985 also splits the September zone claim (reference 7717, $54,186.00) across the five zone PKs its face prints, while the identical July claim, 7710, still sits whole on PK000028. A re-pull of the GXO001 creditor history was received and audited row by row against the copy embedded at v8: identical, so not re-captured (rule 12). Build and report dates now come from Brisbane time, the timezone every TechOne export is stamped in, rather than the container's UTC day.

**v11** captured batch `ksadasd`, 67 invoices over 71 pages (54 T & H Levai, 14 Weis Contractors, plus one repeated copy of INV-39506 typed DUPLICATE_COPY and not captured twice), $80,227.76 ex GST, one to one against 67 Park Services lines at 73123. The supplied corpus arrived GREEN with every document at TIE and no amount restated; two header fields were restated from the retained rows and logged per document: the due date every face prints, which the extraction omitted, and on all 14 Weis invoices the invoice date, where the extraction had carried the printed due date (new family R4 in `prep_supplied_corpus.py`; every restated date agrees with the ledger document date). Shingle check PASS on 325 corpus shingles and 326 workbook shingles; per-vendor fidelity PASS against the Levai and Weis page text parsed at v2 and v3. Nature category is now data per invoice where a vendor prints several kinds of work under one contract (match-table keys `nature_category` and `theme_v3`): the batch splits into fence and bollard repairs (26), scheduled and reactive pressure cleaning (24), softfall (8), furniture and signs (5) and singletons. The Levai header parser had fixed the Spring Mountain Reserve bush-track job on every Levai invoice since v2, so five v3 captures (INV-39437, INV-39435, INV-39475, INV-39495, INV-39542) carried the wrong site, work and category; the parser now reads the job row, and those five are corrected in this build. The gate, the rule 16 reconciliation and the match table now honour `duplicate_of` (extraction prompt v6 11.4). Findings: Weis INV-2614 prints PK000022 for Kilkenny Park and is charged PK000391 (verdict Review, folded into the printed-PK open item); Levai INV-39440 and INV-39561 print no PK (follow-up on each line). Handover gains the change-log rows v8 to v11 and a source row per supplied corpus; Data_Acquisition gains F58 (pla073_1) and F59 (ksadasd), which v10 had not recorded.

**v10** captured batch `pla073_1`, 47 Play Force Australia invoices over 144 pages, $40,411.30 ex GST, one to one against 47 register lines. It is the first supplied corpus to arrive GREEN with nothing to repair: prep does only housekeeping, every amount and line count is identical to the corpus as supplied (retained beside it), the shingle check passes on 427 shingles and the independent per-vendor fidelity check passes on 217 constant template rows. Printed PK agrees with the PK charged on 41 of 47 and differs on none; six print no PK at all. Two more creditor histories, QPO001 and KAC001. New finding **B-035:** Kachel invoice 7719 allocates $3,530.00 to Tully Memorial Park PK000030 and $630.00 to Croydon Park PK000028 on its face, and TechOne posts the whole $4,160.00 to PK000028.

**v9** added the Document Reconstruction journal route. A Document Line Table is keyed to a document file and prints the external account (PK000092); a Document Reconstruction is keyed to a Document Cross Reference and prints the internal one (1-20361-73422), so it reaches the Council-side counterparty legs a pull taken inside the branch never shows. The register already holds the internal account verbatim in its grey source block, so a leg reaches a register line with no crosswalk invented; the one document held in both forms proves the mapping. `Reconstruction_Sources` carries 4,534 legs from four documents; all five documents net to $0.00 and every reference ties its register net to the cent. Journal_Pull gains Tier F and Tier A falls from 7 documents and $329,026.00 to 5 and $4,023.20. Findings **B-036** (the internal plant hire SLA is a fixed monthly charge per plant unit, not a usage recharge: sixteen of seventeen branch cost centres take an identical amount in Period 1 and Period 2) and **B-037** (document file 1252466 still only two of eight references evidenced).

**v8** added seven APLEDGER creditor histories with a sighted invoice behind each label and ABN, taking identification from 1,053 lines to 1,218 and clearing twelve supplier series. Findings **B-033** (Worssell prints no registered entity name) and **B-034** (creditor code INT036 does not match the printed entity Chalcedony Investments Pty Ltd).

**v7** built the two binders that v6 had held, `mix222` (29 Harpley Services invoices) and `binder11111` (13 RST Systems invoices, the $11,950.00 the v5 extraction dropped included). Both gate GREEN and both pass the shingle check. Findings **B-031** (no RST Systems invoice prints an ABN or entity name) and **B-032** (eight carry an LCC Fuel Levy - Diesel line totalling $829.03, four recoded to 74189 and four left on 73212, the printed rate taking three values in six weeks without being monotonic in date).

Open item numbers are positional: Open_Items renumbers whenever a section's contractor identification item resolves, so stored text names an item by its title rather than its number.

Other open items: the PS_WP port (B-020, B-024), printed-versus-charged PKs (B-025, B-026), the Coast2Coast fuel levy over-claim (B-027), the plant hire re-post to a single PK (B-028), the partial journal pull on document file 1252466 (B-029) and the fuel levy coded to the cleaning account (B-030).

## The extraction prompt

`docs/PSWP_Extraction_Prompt_v6.md` is current and supersedes v5. v6 was written from the mix22 and binder11111 failures: it makes the item table's column bands mandatory and gated, makes the amount band the sole sufficient test for a priced row, adds a residue test that must be empty before a document is emitted, gates the header block's own arithmetic, closes the `line_type` list, and carries a template compatibility annexe covering the 36 invoice layouts this project has met.
