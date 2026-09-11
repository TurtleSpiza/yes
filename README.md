# LCC Parks transaction registers

Two Excel registers for Logan City Council Parks Branch expenditure, and the Python toolkit that builds and verifies them.

| Register | File | Scope |
|---|---|---|
| Park Services & Water Parks | `registers/PS_WP_Transaction_Register_3FY_v127_CANDIDATE.xlsx` | Sections 4090240 and 4090260, FY2023/24 to FY2026/27 (three assessed years plus a memo year). The record for the three-year audit. |
| Parks Branch FY2026/27 | `registers/Parks_Branch_Transaction_Register_FY2627_v6.xlsx` | Branch 4090000, all sections, FY2026/27 P1-3 at O110-O115. Inherits the PS/WP FY2026/27 analysis line by line and classifies the other sections itself. |

Both registers follow the same column map (PS/WP schema, 146 columns; the branch register adds two), the same rule set (`docs/PSWP_Project_Instructions_v11__1_.md`) and the same verification standard: a sighted invoice is captured at line level, every printed detail sits on the register line, and three live checks return TRUE before a line is Confirmed.

## Layout

- `registers/` the workbooks. Each is self-contained (source exports, evidence, instructions and controls embedded).
- `toolkit/pswp/` the PS/WP toolkit (`pswp_build_batch.py` and companions, `lo_recalc.sh`).
- `toolkit/branch/` the branch register toolkit: `pbr_stage.py` (load, inherit, identify from creditor histories, classify, capture), `pbr_build.py` (write, recalc, verify, ship), `pbr_capture.py` (rule 16/17 capture from a gated corpus), `pbr_rules_v1.json` (classification rules as data), `pbr_histories_v4.json` (APLEDGER creditor histories as data: file, code, label, ABN), `parse_mixed1.py`, `parse_mixed_new.py`, `parse_attach1.py` and `parse_attach2.py` (raw-text invoice parsers), `prep_code_corpus.py` (prepares and fidelity-checks a supplied third-party corpus), `pbr_unidentified_queue.py` and `pbr_journal_pull_report.py` (the identification queue and journal pull list reports).
- `batches/` per batch: the Copilot v5 corpus and report as received, the raw-text v6 corpus (page text retained, gate GREEN), the match table, capture report or hold record.
- `docs/` project instructions, PS/WP schema and history, the invoice extraction prompt (v6 is current; v5 is retained because two held batches were extracted under it), branch schema.
- `data/inputs_2026-09-11/` the 27SLACT ledger export and four SE2 exports the branch register was built from; `creditor_histories/` the seventeen APLEDGER creditor history exports (v4 to v6); `journal_pulls/` the TechOne Document Line Table exports embedded on Journal_Sources.
- `reports/` derived reports regenerated from the shipped register: `Unidentified_Contractors_v6.md/.xlsx`, the identification queue with one invoice to sight per supplier series; `Journal_Pull_v6.md/.xlsx`, the rule 21 journal pull list, one row per TechOne document file.
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

One script runs the whole chain: stage, write, LibreOffice convert-route recalc (isolated profile, `OOXMLRecalcMode=0`), calamine verify of the recalculated file, ship to `registers/`. It ships only on a clean verify (92 controls, every sighted line's three checks, the register total and a whole-workbook error sweep). A partial run is discarded, never resumed. About 35 to 40 seconds from a warm cache. Set `PBR_OUTDIR` to ship elsewhere; `PBR_INPUTS` and `PBR_V127` override the input locations.

## Capturing a new invoice batch

1. Copilot chat produces headers only for tabular invoices (see `batches/*/capture_report_*_v5.md`). Run the raw-text route instead: `PDF=path/to/binder.pdf OUT=batches/<batch>/corpus_<batch>_v6.json python3 toolkit/branch/parse_mixed_new.py` (add a vendor template if the binder carries a new layout).
2. Gate it: `pswp_json_repair.repair_and_gate` must return GREEN; run the five-word shingle check against the retained page text.
3. Build the match table against the register (exact, SUM-TIE, derivation incl/1.1, one-cent tolerance, split-posting or partial-scope by LineKey; coding verdict, note and follow-up per invoice are data on the entry), add the batch to `BATCHES` in `pbr_stage.py` and its stamp to `pbr_capture.py`, run `pbr_build.py`.

## Adding a creditor history

Drop the APLEDGER export (Ledger Accounts Transactions Table, Default Ledger Type = AP, one Account) into `data/inputs_2026-09-11/creditor_histories/` and add an entry to `toolkit/branch/pbr_histories_v4.json` (file, creditor code, canonical label, 11-digit ABN, label basis). The stage screens the md5 (rule 12), asserts the code and dominant ABN, embeds the history verbatim on Creditor_Lines and identifies every AP line whose reference, incl-GST amount (document net x 1.1 within 2c) and date (within 120 days) match exactly one creditor. Then run `pbr_build.py` and `pbr_unidentified_queue.py`.

## Capturing a journal batch

TechOne Document Line Table exports are the evidence route for a journal that carries no attachment (rule 21). Drop the exports into `data/inputs_2026-09-11/journal_pulls/`, run `python3 toolkit/branch/pbr_journal_batch.py`, author `batches/journal_1/notes_journal_1_v6.json` with what each document answers, then `pbr_build.py`. The driver screens every md5 (rule 12), keeps one copy of a duplicate export, maps each leg to its register line, proves each document nets to $0.00 and that every in-scope leg sum ties its journal reference's register net, and audits any document already embedded in the PS & WP register leg by leg rather than re-capturing it. The legs are embedded verbatim on `Journal_Sources`.

## State at v6 (11-Sep-2026)

Register total $4,910,566.68 across 6,683 lines, tied to the ledger export and all four SE2 views; 93 of 93 controls TRUE. 260 sighted lines over 253 invoices. Seventeen APLEDGER creditor histories embedded (44,410 lines on Creditor_Lines) identify $1,231,762.13 ex GST at Tier 1. Confirmed $3,395,636.55; Partial $1,051,927.10; Pending evidence $463,003.03. Contractor unidentified $358,887.70; the queue with one invoice to sight per series is `reports/Unidentified_Contractors_v6.md` (340 lines, 91 series).

v6 is the merge of two sessions' work on this register. From this branch: the first journal batch, with three TechOne Document Line Tables embedded verbatim on the new `Journal_Sources` sheet (92 legs) and one re-pull audited against the PS & WP v127 embed and not re-captured. Those pulls answered the blank narrations on GJ080153 (the June 2026 Plant & Fleet accrual reversal) and Open Item B-012 for GJ080309, which also raised B-030: $51,091.59 of plant hire re-posted to PK000068 that the original GJ080188 legs assign to PK000435 and PK000396 on their plant references. Batches mix22 (40 invoices) and attach_3 (8 TechOne attachments) were captured; batches binder11111 and mix222 are held on pages carrying no line record (P3), which cannot be repaired downstream. From `claude/new-session-w6zxj2`: five more APLEDGER creditor histories at v6 (NUW001, LEV002, GRE083, WAT088 there, MPD001 here), the session-start toolchain hook and the environment self-test.

Other open items: the PS_WP port (B-022, B-026), printed-versus-charged PKs (B-027, B-028), the Coast2Coast fuel levy over-claim (B-029), the partial journal pull on document file 1252466 (B-031) and a fuel levy coded to the cleaning account (B-032).

## The extraction prompt

`docs/PSWP_Extraction_Prompt_v6.md` is current and supersedes v5. v6 was written from the mix22 and binder11111 failures: it makes the item table's column bands mandatory and gated, makes the amount band the sole sufficient test for a priced row, adds a residue test that must be empty before a document is emitted, gates the header block's own arithmetic, closes the `line_type` list, and carries a template compatibility annexe covering the 36 invoice layouts this project has met.
