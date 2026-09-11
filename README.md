# LCC Parks transaction registers

Two Excel registers for Logan City Council Parks Branch expenditure, and the Python toolkit that builds and verifies them.

| Register | File | Scope |
|---|---|---|
| Park Services & Water Parks | `registers/PS_WP_Transaction_Register_3FY_v127_CANDIDATE.xlsx` | Sections 4090240 and 4090260, FY2023/24 to FY2026/27 (three assessed years plus a memo year). The record for the three-year audit. |
| Parks Branch FY2026/27 | `registers/Parks_Branch_Transaction_Register_FY2627_v3.xlsx` | Branch 4090000, all sections, FY2026/27 P1-3 at O110-O115. Inherits the PS/WP FY2026/27 analysis line by line and classifies the other sections itself. |

Both registers follow the same column map (PS/WP schema, 146 columns; the branch register adds two), the same rule set (`docs/PSWP_Project_Instructions_v11__1_.md`) and the same verification standard: a sighted invoice is captured at line level, every printed detail sits on the register line, and three live checks return TRUE before a line is Confirmed.

## Layout

- `registers/` the workbooks. Each is self-contained (source exports, evidence, instructions and controls embedded).
- `toolkit/pswp/` the PS/WP toolkit (`pswp_build_batch.py` and companions, `lo_recalc.sh`).
- `toolkit/branch/` the branch register toolkit: `pbr_stage.py` (load, inherit, classify, capture), `pbr_build.py` (write, recalc, verify, ship), `pbr_capture.py` (rule 16/17 capture from a gated corpus), `pbr_rules_v1.json` (classification rules as data), `parse_mixed1.py` and `parse_mixed_new.py` (raw-text invoice parsers).
- `batches/` per batch: the Copilot v5 corpus and report as received, the raw-text v6 corpus (page text retained, gate GREEN), the match table, capture report or hold record.
- `docs/` project instructions, PS/WP schema and history, extraction prompt, branch schema.
- `data/inputs_2026-09-11/` the 27SLACT ledger export and four SE2 exports the branch register was built from.
- `cache/` scratch (calamine pickles, recalc output). Not committed.

## Rebuilding the branch register

Requirements: Python 3.12, `python-calamine`, `openpyxl`, `lxml`, `pandas`, LibreOffice (`soffice`) and `pdftotext` (poppler).

```
pip install python-calamine openpyxl lxml pandas
python3 toolkit/branch/pbr_build.py
```

One script runs the whole chain: stage, write, LibreOffice convert-route recalc (isolated profile, `OOXMLRecalcMode=0`), calamine verify of the recalculated file, ship to `registers/`. It ships only on a clean verify (78 controls, every sighted line's three checks, the register total and a whole-workbook error sweep). A partial run is discarded, never resumed. About 40 seconds from a cold cache. Set `PBR_OUTDIR` to ship elsewhere; `PBR_INPUTS` and `PBR_V127` override the input locations.

## Capturing a new invoice batch

1. Copilot chat produces headers only for tabular invoices (see `batches/*/capture_report_*_v5.md`). Run the raw-text route instead: `PDF=path/to/binder.pdf OUT=batches/<batch>/corpus_<batch>_v6.json python3 toolkit/branch/parse_mixed_new.py` (add a vendor template if the binder carries a new layout).
2. Gate it: `pswp_json_repair.repair_and_gate` must return GREEN; run the five-word shingle check against the retained page text.
3. Build the match table against the register (exact, SUM-TIE, derivation incl/1.1, one-cent tolerance, split-posting or partial-scope by LineKey), add the batch to the loop in `pbr_stage.py`, run `pbr_build.py`.

## State at v3 (11-Sep-2026)

Register total $4,910,566.68 across 6,683 lines, tied to the ledger export and all four SE2 views. 176 sighted lines over 172 invoices. Confirmed $2,939,018.18; contractor unidentified $1,778,748.05 (mostly Trees, Park Maintenance and Natural Areas AP lines awaiting creditor histories). Open items on the Open_Items sheet; the first is porting the 31 Park Services and Water Parks captures from batch mixed_new_26_27 back to the PS/WP register.
