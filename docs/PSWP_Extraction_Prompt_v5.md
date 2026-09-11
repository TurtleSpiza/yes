# PSWP Invoice Extraction Prompt v5 (9-Sep-2026)

Supersedes v4 (2-Sep-2026), which superseded v3.1. For extraction of supplier-invoice binders to a structured JSON corpus for the PS/WP Transaction Register, Logan City Council, Parks Branch.

v4 fixed the right thing and lost three things doing it. It fixed classification: column-band anchoring, the retry ladder, the P1 gate that makes the `mix1` failure unshippable. Those are kept here unchanged in substance. What it lost, by rewriting rather than amending, was the operational half of v3.1: **the misroute guard, document boundary detection, and the findings register**. It also shipped one gate that cannot be passed in the runtime it is actually used in, which is worse than no gate: a prompt whose OCR requirement forces RED on every honest M365 Copilot run teaches the operator to ignore the gate line.

**Read section 1 before anything else. It decides which gates apply to you.**

---

## 0. Contract

You produce ONE JSON corpus and one capture report. The corpus is consumed by an automated build that will **refuse** it if any gate is RED. There is no partial credit: a corpus that ships with an unresolved pathology costs more than a corpus that ships late, because the build session that receives it is wasted.

**You may not:** paraphrase, summarise, infer an amount that is not printed, adjust a figure to make it tie, skip a page, or claim a check you did not run.

**You must:** declare your runtime, represent every page, derive every classification from layout evidence you can point to, run the arithmetic gate on every document before you emit it, and declare RED or AMBER rather than ship a known defect.

### 0.1 How to attach this job

Attach the invoice PDFs and this file. **Attach nothing else.** No reference workbook, no TechOne extract, no `.xlsx` of any kind, and start a fresh chat if one is already in context. A spreadsheet in the attachment set is what causes the misroute.

### 0.2 The one thing you must not do

**You are not given a spreadsheet and you must not create one.** No `.xlsx`, no `.xlsm`, no `.csv`, no "let me put this in a table for you", no workbook analysis, no chart. If you find yourself opening, creating or saving a workbook, you have taken the wrong branch: stop, discard that work, and return to section 3. There is no step here that needs a spreadsheet tool, and there is no ledger reconciliation in this session, so a missing workbook is never a reason to pause and ask for one.

**Do not stop and ask whether to proceed at each stage.** Work the pipeline and come back when the gates pass, or when one fails for a reason you cannot resolve.

### 0.3 Deliverables

1. `corpus_<batch_id>.json`, the structured capture, schema at section 9.
2. `capture_report_<batch_id>.md`, the gate line first, then the figures and the findings.

Nothing else. No reformatted copy of the source PDFs, no derived workbook.

---

## 1. Declare your runtime (NEW, and it sets your gates)

State this in the manifest as `runtime` before you do anything else, because three gates scale off it.

| Runtime | What you have | OCR gate | Fidelity audit |
|---|---|---|---|
| **A, code-capable** (terminal, Python, poppler, tesseract) | `pdftotext -layout`, `pdftoppm`, `tesseract`, `pypdf` annotations | Section 8 applies in full | Section 10, per-page multiset diff |
| **B, chat-only** (M365 Copilot, no terminal) | Document reading only | OCR is `not_available`, and P6 **does not fire** | Section 10, five-word shingle self-check on a stated sample |

**Runtime B is the normal case for this project and is not a degraded run.** Reading the PDF and transcribing every line of every page verbatim is the bulk of the value and is fully achievable. What you must not do in runtime B is pretend: do not report OCR you did not run, do not report a token-level audit you could not compute, and do not substitute a summary for the parts you cannot do. State in one list what a runtime A capture would add that you cannot supply: image-borne letterhead text and ABNs, hyperlink targets, scanned-page transcription, and the token-level completeness audits.

---

## 2. Two-pass architecture

Classification and arithmetic in one pass is why a misclassified line was never revisited.

**Pass 1, layout.** For each document: establish the page range, find the table header row, record its column bands, then emit one line record for every printed layout row with a provisional `line_type`.

**Pass 2, arithmetic.** For each document: sum the PRICED lines, compare to the printed subtotal, and if it does not tie, **run the retry ladder in section 6 before you are permitted to write `"self_tie": "OUT"`.** Reclassification during pass 2 is expected and correct. `line_text` is never edited in pass 2; only `line_type` and the numeric fields may change.

A document is emitted only after pass 2 completes on it. See section 7 for the emit protocol, which is what stops a long binder running out of budget mid-document.

---

## 3. Document boundary detection (RESTORED from v3.1, absent from v4)

A binder is many invoices in one file. **Split it before anything else is meaningful.** v4 carried `page_range` in the schema and a retry rung that mentions a split table, but it never told you how to split, which left the single most consequential step of a binder parse undefined.

1. Run supplier-specific invoice-number patterns over each page.
2. A page carrying exactly one identifier belongs to that document.
3. A page carrying **no** identifier inherits the previous page's document. That is correct for terms pages, payment advice pages and blank pages.
4. **A page can carry two documents.** Where one invoice's totals block is followed on the same page by another's letterhead, the page belongs to both: record it in both `page_range`s and say so in `notes`. A page range is inclusive and page ranges may overlap by one page for this reason only.
5. **Verify the split against page footers.** Xero and similar print `1 of 3`. If your split gives four pages where the footer says three, your split is wrong, not the footer.
6. **Two non-adjacent page runs resolving to the same identifier is a duplicate copy, not a split error.** Section 11.
7. **Report every identifier you find**, including any you cannot classify. Ledger matching is a later session's job, so an unrecognised identifier is reported, never dropped.
8. Assert before emitting: the union of all `page_range`s covers every page of the source, and no page is unaccounted for.

Known identifier patterns from prior batches:

| Supplier | Pattern |
|---|---|
| Savco Vegetation Services | `\b(SV\d{6})\b` |
| Xero-templated (Heritage Tree, Weis, Total Environmental, F82, Play Force) | `\b(INV-\d{3,5})\b` |
| Burly Holdings | `Tax Invoice #\s*(\d+)` |
| Link Resources Training | `\b(LR\d{4,6})\b` |
| Vinton Tree Services (RST Systems) | `Invoice No\.:\s*(\d{5})`, `Invoice number:\s*(\d{5})` |
| Greenway Turf Solutions | `\b(SI-\d{6,9})\b` |
| Q Power | `TAX INVOICE NO\.\s*(\d+)` |
| Harpley Services | `\b(000\d{5})\b`, **leading zeros are part of the number** |
| SECUREcorp | `\b(QLDPSI\d{7})\b` |

**Trap:** the Total Environmental Concepts layout prints `Invoice Number` and the number on different physical lines with other text between, so `Invoice Number\s+(\d{4})` fails. Detect that supplier by name and read the number positionally.

**Trap:** `doc_ref` is the supplier's invoice number **exactly as printed, leading zeros included**. Downstream matching is on that string, and the ledger truncates long numbers (TCS 17118059 posts as `171180`), so a stripped or normalised `doc_ref` silently fails to match. The `C`-number in a file name is the TechOne document image id, a different fact: record it in `notes`, never in `doc_ref`.

---

## 4. Column anchoring: how to decide a line is PRICED

**This is the rule that failed on `mix1`.** Do not classify priced lines by whether the row starts with a number, and do not classify them by whether the row ends with a number. Both heuristics fail on real Parks invoices.

### 4.1 Find the header row first

Every priced table has a header row printing some subset of: `Description`, `Item`, `Details`, `Quantity`, `Qty`, `Unit Price`, `Rate`, `Unit`, `GST`, `Amount`, `Amount AUD`, `Total`, `Ex GST`, `Price`.

- Record its page and row, its verbatim text, and the **character offset at which each column label begins**. Those offsets are the column bands.
- Type the header row `TABLE_HEADER`. **It is not TOTALS.** On `mix1` the row `Description Quantity Unit Price GST Amount AUD` was typed TOTALS, which destroyed the only anchor the document had.
- More than one table means more than one header: record each and scope its bands to the rows beneath it.
- If no header row prints, say so in `notes` and fall back to 4.3.

### 4.2 Classify body rows by column occupancy

For each row beneath a header, test which column bands contain a numeric token, allowing a few characters of drift either side of the band start.

- A row with a numeric token in the **amount band** is PRICED, whatever the row begins with. `Darlington Parklands 1.00 63.46 10% 63.46` is PRICED. It begins with a word and contains a percentage. Neither disqualifies it.
- A row with numerics only in the quantity or unit-price bands and nothing in the amount band is PRICED **if** the amount is derivable as printed elsewhere on the row; otherwise it is PRICED with a null amount and a `note`, and the document goes to the retry ladder.
- A row with no numeric in any band is NARRATIVE.
- A row sitting entirely left of the first numeric band and continuing a description above it is NARRATIVE with `"note": "wrapped description"`.
- **Zero-amount priced rows are real.** Xero prints `Contract # PAR329B2021  1.00  0.00  0.00` and site-address rows at `1.00 ... 0.00`. They carry the full column structure, so they are PRICED at 0.00. They cannot disturb the tie and the register needs them (rule 16).

### 4.3 When there is no header row

Use the trailing-amount test, with these exclusions applied **before** testing:

- **GST rate tokens.** `10%`, `10.0%`, `GST 10%` are rates, never amounts. This is the most common false negative and the reason the `mix1` Play Force documents failed.
- **Date tokens.** `dd.mm.yyyy`, `dd.mm.yy`, `dd/mm/yyyy`, `dd Mon yyyy`.
- **Reference tokens.** Bare integers of six digits or more with no decimal point and no currency symbol, where the surrounding text names a reference, order, contract or account.
- **Quantities.** A lone `1.00` at the start of a row is a quantity, not an amount.
- **`SUBTOTAL:` contains `TOTAL:`.** Match totals keywords before priced ones and use a negative lookbehind, `(?<!SUB)TOTAL:`.

Accept variable decimals: `$3,660`, `65.1`, `1,234.00` are all amounts.

### 4.4 The invariant that makes this checkable

**`line_type == "PRICED"` if and only if `line_ex_gst` is a number (or `stated_amt` on a GST-inclusive template).** These are not two independent assertions; one determines the other. Assert it both ways before emitting a document. A PRICED line with a null amount, and an amount-bearing line typed NARRATIVE, are each emit-blocking defects.

---

## 5. Header amounts

One figure per labelled line. Never take a header amount from an unlabelled position.

- **`printed_total_incl_gst`** comes from `Total`, `TOTAL AUD`, `Balance Due`, `Amount Due`, `Total Outstanding`. **Never** from `Subtotal`. If the label and its amount print on different layout rows (Xero), search adjacent rows and record which row supplied the figure in `notes`. If the total is a bare `$` amount under `PLUS 10% GST` or `Sub Total:`, take it and say so.
- **`printed_gst`** comes from the `GST`, `TOTAL GST 10%` or `PLUS 10% GST` line. Never the Subtotal, never the Total. Where the GST line interleaves with the payment block, match by label, not position.
- **`printed_subtotal_ex_gst`** comes from `Subtotal` / `Sub Total`. If only the total and GST print, derive it as total less GST and set `"subtotal_basis": "derived from total less GST"`.
- **`invoice_date`** comes from the token labelled `DATE` or `INVOICE DATE`. Where a header prints `PLEASE PAY BY | AMOUNT | INVOICE DATE` on one row, the LAST date is the invoice date and the FIRST is the due date. Never a work-note or completion date.
- **Totals can print on the last page only.** Search every page of the document before recording a null. That is a capture note, not an extraction loss.
- **A null header field is a defect,** not an omission. Restate it from the page, or explain in `notes` why the layout does not carry it and record `"(not printed)"`.
- **Credit notes are negative.** A credit note or adjustment note carries negative `line_ex_gst`, `printed_subtotal_ex_gst`, `printed_gst` and `printed_total_incl_gst`, and `"doc_kind": "CREDIT_NOTE"`. Never record a credit as a positive and never flip the sign to make a tie work.

---

## 6. The arithmetic gate and the retry ladder

For every document, in pass 2:

```
captured = sum(line_ex_gst for PRICED lines)
tie      = round(abs(captured - printed_subtotal_ex_gst), 2) <= 0.02
```

If `tie` is false, **you may not write `"self_tie": "OUT"` until you have run all four rungs and recorded the result of each in `retry_log`.**

**Rung 1, missed priced rows.** Re-scan every NARRATIVE row in the table region against 4.2. Ask specifically: does this row carry a numeric in the amount band? This rung alone would have fixed all 15 `mix1` failures.

**Rung 2, GST-inclusive template.** Test whether the captured lines instead tie the printed **total including GST**. If they do, set `"tie_basis": "incl_gst"` and `"line_amount_basis": "incl_gst"`, record it, and the document ties. Harpley template B (the `Your Order No:` header) is the standing example.

**Rung 3, rate-versus-amount confusion.** Check whether any captured amount is actually a GST rate, a quantity, or a unit price read into `line_ex_gst`. Recompute from the correct band.

**Rung 4, split or continued table.** Check whether the table continues on a following page, whether a second table sits beneath a second header, and whether its rows were attributed to the wrong document. Check the page range against section 3.

Only if all four fail: `"self_tie": "OUT"`, with `retry_log` recording what each rung found and `notes` stating in one sentence what the analyst should look at.

---

## 7. Emit protocol and budget (NEW, and this is what killed `mix1` as much as OCR did)

A 317-page binder will exhaust your budget before it exhausts the work. Plan for that from the first document rather than discovering it at page 83.

1. **Emit per document, not per binder.** Complete pass 1 and pass 2 on one document, emit its record, then move on. Never hold 112 documents open and write at the end.
2. **Chunk the output so the pieces concatenate.** If the corpus will not fit one message, emit it as `part 1 of n` and so on, each a fenced block, each containing whole document records, the manifest last. Say plainly which documents are in which part.
3. **Keep a live counter.** `coverage.documents_complete` and `documents_total` are updated as you go, not estimated at the end.
4. **Stop at a document boundary.** If you are running short, stop cleanly, emit what you have with `"gate": "AMBER"`, and give `resume_point` as the exact first uncaptured page and document identifier. **Never emit a partial run as though it were whole.** An honest AMBER at document 60 of 112 is buildable; a silent stop at page 83 is not.
5. **No interim status reports.** One report at the end, per section 14.

---

## 8. OCR scope

**Runtime B: OCR is not available.** Set every page `"ocr_status": "not_available"`, report `ocr_pages_not_available`, and **P6 does not fire**. Say in the report that the corpus is single-source and name what that leaves uncaptured (section 1).

**Runtime A: OCR is not required on every page. It is required where the text layer cannot be trusted.** Run OCR on a page if and only if:

1. The page has no text layer, or fewer than five text-layer tokens.
2. The page's text layer lacks a token the arithmetic gate needs (a subtotal, GST or total figure the layout clearly shows).
3. The page carries an ABN in an image-borne letterhead and no ABN appears in the text layer.
4. The page shows a stamp, handwritten annotation, or signature block bearing a reference, date or approval.
5. The page is in the 5% random sample you OCR per binder as a control on the text layer itself.

Every other page gets `"ocr_status": "not_required"` with its reason code. **`not_required` pages count as complete.** Report `ocr_pages_run`, `ocr_pages_not_required`, `ocr_pages_not_available` and `ocr_pages_outstanding`; P6 fires only when `ocr_pages_outstanding > 0`.

---

## 9. Schema

Numbers are JSON numbers: unquoted, no `$`, no thousands separators, two decimals, negative for credits. A quoted amount, a `$` sign or a comma inside a number is a defect the repair script has to fix before anything else can run, and it is free to prevent here.

```json
{
  "manifest": {
    "batch_id": "<given>",
    "source_files": [{"name": "<pdf name>", "pages": 0}],
    "runtime": "A | B",
    "extraction_tool": "<product and model version>",
    "extracted_utc": "<ISO 8601>",
    "prompt_version": "v5",
    "gate": "GREEN | AMBER | RED",
    "pathologies": [{"code": "P1", "doc_ref": "...", "page": 0, "detail": "..."}],
    "coverage": {"documents_complete": 0, "documents_total": 0,
                 "pages_represented": 0, "pages_total": 0},
    "identifiers_found": [], "identifiers_unclassified": [],
    "documents_found": 0, "lines_captured": 0,
    "documents_tie": 0, "documents_out": 0,
    "captured_ex_gst_total": 0.00,
    "ocr_pages_run": 0, "ocr_pages_not_required": 0,
    "ocr_pages_not_available": 0, "ocr_pages_outstanding": 0,
    "text_layer_diffs": [{"page": 0, "raw_minus_captured": [], "captured_minus_raw": [],
                          "dismissed_reason": null}],
    "shingle_checks_run": 0, "shingle_failures": 0,
    "resume_point": null
  },
  "documents": [ ]
}
```

### Document record

```json
{
  "doc_ref": "<invoice number exactly as printed, leading zeros kept>",
  "doc_kind": "TAX_INVOICE | CREDIT_NOTE | STATEMENT | CORRESPONDENCE",
  "source_file": "<pdf>", "page_range": [1, 1],
  "supplier": "<printed, verbatim>",
  "supplier_abn": "<printed, verbatim including its printed grouping>",
  "abn_source": "text_layer | ocr | footer | absent",
  "invoice_no": "<printed>", "invoice_date": "<printed, verbatim format>",
  "printed_subtotal_ex_gst": 0.00, "subtotal_basis": "printed | derived from total less GST",
  "printed_gst": 0.00, "printed_total_incl_gst": 0.00,
  "captured_ex_gst": 0.00,
  "line_amount_basis": "ex_gst | incl_gst",
  "tie_basis": "ex_gst | incl_gst",
  "self_tie": "TIE | OUT",
  "retry_log": [{"rung": 1, "found": "..."}],
  "table_headers": [{"page": 1, "row": 17, "text": "<verbatim>",
                     "bands": {"description": 0, "quantity": 47, "unit_price": 67,
                               "gst": 87, "amount": 99}}],
  "work_orders": [], "contract_refs": [], "po_refs": [], "pk_refs": [],
  "printed_account_codes": [],
  "evidence_stem": "<Supplier, short what-for, Mon-YYYY, amount>",
  "duplicate_of": null,
  "findings": [{"code": "F1", "detail": "...", "amount": 0.00}],
  "notes": "<face codes, references, oddities, which row supplied each header figure>",
  "lines": [ ]
}
```

`printed_account_codes` captures an account or cost code **printed on the face**, verbatim. It replaces v4's `nat_acct_should`, which asked the extractor for a coding judgement. Coding is the register's ruling, made against the chart of accounts on sighted evidence, and an extractor's guess arriving in the corpus is a matching aid at best and a contaminant at worst.

### Line record, one per printed layout row

```json
{
  "source": "TEXT | OCR | ANNOT", "page": 1, "line_no": 1,
  "line_text": "<verbatim, leading whitespace preserved>",
  "line_type": "PRICED | NARRATIVE | TABLE_HEADER | TOTALS | FOOTER | TERMS | BLANK | OCR_DUPLICATE | IMAGE_TEXT | ANNOTATION | DUPLICATE_COPY",
  "ocr_only": false, "ocr_status": "run | not_required | not_available | outstanding", "ocr_reason": null,
  "qty": null, "unit": null, "unit_price_ex_gst": null,
  "line_ex_gst": null, "gst": null, "stated_amt": null,
  "band_hits": [], "work_order": null, "note": null
}
```

`band_hits` names which column bands carried a numeric on this row. It is the evidence for the classification and makes a wrong call auditable after the fact.

---

## 10. Verbatim fidelity

`line_text` is the layout row exactly as printed, including leading whitespace, which carries the column positions section 4 depends on. Never trim, never normalise, never collapse runs of spaces. `rstrip()` only, never `strip()`.

**Runtime A.** Report the multiset difference **per page**, both directions, and list up to twenty actual differing tokens with page numbers in `manifest.text_layer_diffs`. A bare count is unactionable: `45` tells the analyst nothing. A difference caused by a ligature, a soft hyphen or an encoding artefact is recorded and dismissed with a reason. Any difference not so dismissed is a P3-class concern and must be named in the report.

**Runtime B.** Re-read a stated sample and check five-word shingles against your captured text: every document where you captured fewer than 40 lines, and at least one document per supplier otherwise. Record `shingle_checks_run` and `shingle_failures`, and state the sample rule you applied. Do not report `text_layer_diffs` you could not compute; leave the array empty.

---

## 11. Standing rules

1. **Verbatim only.** A summary row in place of line capture is a critical failure.
2. **Full page representation.** Every page appears; every text-layer row appears. OCR content is typed `OCR_DUPLICATE` on text-layer pages and `IMAGE_TEXT` for image-borne content such as letterheads.
3. **The ABN is the SUPPLIER's,** from the letterhead or footer. LCC's own ABN `21 627 796 435` prints in the bill-to block. Capture the printed grouping verbatim, even where mis-grouped. An ABN present only as pixels is legible on the page and not a defect, but it is invisible to a text check, so flag `abn_source`.
4. **Duplicate copy pages.** Capture both copies. Type every line of the second `DUPLICATE_COPY` with arithmetic fields nulled, set `duplicate_of` to the first record's page range, note both ranges, and report it as a finding rather than housekeeping.
5. **GST-inclusive-only templates:** capture ex GST as printed total less printed GST, record the treatment, and do not invent ex-GST priced lines.
6. **Wrapped descriptions** get their own NARRATIVE record and are never truncated mid-phrase or rejoined. `pdftotext -layout` splitting a description across physical lines is correct behaviour.
7. **Face codes and references** (PK numbers, CR and WO numbers, contract refs, POs) are captured verbatim in their fields AND left verbatim in `line_text`. Record a PK typo as printed; normalisation happens on join, not here.
8. **Correspondence in a binder is evidence.** Capture it, type it `FOOTER` or `NARRATIVE`, set `doc_kind` to `CORRESPONDENCE` where it stands alone, and never discard it.
9. **One invoice can span several sections and natural accounts.** Never record a section or account at document level; they are line-level facts.
10. **Rounding.** Some suppliers compute GST on the subtotal rather than per line, so per-line GST at 10% can differ by a cent or two. Record as printed, never adjust, and list the differences.
11. **A printed per-line GST of $0.00 alongside a non-zero amount is a GST-free supply, not an error.** Accredited training and some trust-structure suppliers are the standing cases. Do not compute a GST-inclusive figure or a check result into the corpus; those are live formulas in the destination workbook.

---

## 12. Evidence stem rule (RESTORED, ruled 2-Jul-2026)

`Business Name, What it was For, Date, Amount`, 40 characters maximum, no extension. Amount is the invoice incl-GST total, two decimals, no dollar sign. Degrade in this order and never trim the amount: full date `D-Mon-YYYY`, then `Mon-YYYY`, then a shorter purpose, then a shorter business name.

**Stems must be unique across the batch.** Two invoices from one supplier on one day for one amount will collide; break the tie by appending the last three digits of the invoice number to the purpose, then re-run the ladder.

---

## 13. Pathologies that force a gate

These are not tie failures. They are parse failures, and a corpus containing an unresolved one is RED.

| Code | Condition | Why it is fatal |
|---|---|---|
| **P1** | `printed_subtotal_ex_gst` non-zero and zero PRICED lines | The document was not parsed at all. `mix1` shipped 15 of these. |
| **P2** | `line_type == "PRICED"` with null amount, or an amount-bearing row typed NARRATIVE | Breaks the 4.4 invariant |
| **P3** | A page inside a completed document's range with no line records | Full-capture breach. Pages beyond `resume_point` in an AMBER run are not P3. |
| **P4** | `supplier_abn` equals the LCC ABN `21 627 796 435` in any grouping | The bill-to ABN was read as the supplier's |
| **P5** | Null `printed_total_incl_gst` where a Total line demonstrably prints | Header-amount breach |
| **P6** | `ocr_pages_outstanding > 0` (runtime A only) | The corpus is not multi-source. Does not fire in runtime B. |
| **P7** | Two documents sharing a `doc_ref` with neither marked `duplicate_of` | Duplicate screening breach |
| **P8** | A number emitted as a string, or carrying `$` or a thousands separator | Every downstream check has to be repaired before it can run |
| **P9** | Page ranges that leave a gap, or overlap by more than the one page 3.4 permits | The split is wrong, and every amount attributed from it is suspect |

Set `"gate": "RED"`, list every pathology in `manifest.pathologies` with the affected `doc_ref` and page, and say plainly in the report that the corpus must not be built from. **A RED corpus is a useful, honest output. A GREEN corpus containing a P1 is a fabrication.**

---

## 14. Findings to raise, not bury (RESTORED, absent from v4)

The register turns these into numbered Open Items, so a finding you notice and do not record is work the analyst repeats. Record each on the document's `findings` array and repeat it in the report with the document reference and the dollar amount.

1. **Tax invoice defects.** Missing GST amount or total on a document over $1,000, missing ABN, missing supplier identity. Note separately where an ABN exists **only as pixels**.
2. **Documents that do not support the line they appear to be filed against**, so far as that is visible from the document itself: wrong amount, wrong year, wrong party.
3. **Fuel levy lines**, flagged for verification against the stepped and capped model.
4. **Coding candidates**, where a PK or account code printed on the face looks wrong, and documents stating **no PK at all**.
5. **Referenced but absent documents**: tip dockets, cost breakdowns, quotes, fixed-fee schedules, site photographs. The evidence pack is not complete until they are requested.
6. **Duplicate copies and blank pages.**

---

## 15. Capture report

Close with a short report, in this order:

1. **Gate: GREEN, AMBER or RED**, on its own line, first.
2. Runtime, A or B, and the extraction tool and model.
3. Pathologies by code with document references, or the word "none".
4. Pages represented of pages total; documents complete of documents total.
5. Documents at TIE and OUT, every OUT named with its retry ladder outcome.
6. Line records by type, and captured ex GST total.
7. Identifiers found, and any unclassified.
8. OCR: pages run, not required, not available, outstanding.
9. Fidelity: per-page diffs with dismissals reasoned (runtime A), or shingle checks run and failed with the sample rule stated (runtime B).
10. Findings from section 14, each with its reference and amount.
11. Resume point, if AMBER.

**Lead with the gate.** The build session reads that line first and stops there if it is not GREEN.

---

## 16. Worked example, the `mix1` failure

Play Force invoice INV-3880, page 1. The binder printed:

```
Description                    Quantity        Unit Price      GST        Amount AUD
Darlington Parklands           1.00            63.46           10%        63.46
                                                               Subtotal   63.46
                                                            TOTAL GST 10%  6.35
                                                              TOTAL AUD   69.81
```

**v3.1 produced:** the header row typed TOTALS, the body row typed NARRATIVE with a null amount, zero PRICED lines, `captured_ex_gst: 0.00`, `self_tie: OUT`. The document shipped.

**v5 produces:** the header row typed `TABLE_HEADER` with bands recorded; the body row tested against the amount band, found to carry `63.46`, typed PRICED with `line_ex_gst: 63.46`, `band_hits: ["quantity","unit_price","amount"]`; captured $63.46; ties the printed subtotal; `self_tie: TIE`.

**And if it had still failed:** rung 1 re-scans NARRATIVE rows in the table region and finds it. The document cannot reach OUT with a printed subtotal and no priced lines, because that is P1, and P1 is a gate, not a tie failure.

---

## 17. What changed from v4

- **Runtime declaration (section 1).** Gates now scale to what the runtime can actually do. v4's OCR requirement forced RED on every honest M365 Copilot run, which is the fastest way to teach an operator to ignore a gate line.
- **Document boundary detection restored (section 3),** with the supplier pattern table, the footer cross-check, and two new rules: a page can belong to two documents, and `doc_ref` keeps its leading zeros because the ledger match depends on the string.
- **Misroute guard restored (0.1, 0.2).** Attach nothing but the PDFs and this file; never create a spreadsheet. v4 dropped both and the misroute is the failure that costs a whole session.
- **Emit protocol and budget (section 7).** Per-document emit, chunked output, live counters, clean stop at a boundary. `mix1` ran out of budget as much through holding 112 documents open as through OCR.
- **Findings register restored (section 14)** and given a home in the schema, `document.findings`.
- **Evidence stem rule restored (section 12).** v4 kept the field and dropped the rule that makes it unique.
- **Number format is now a pathology (P8),** as are boundary gaps and overlaps (P9). Both are cheaper to prevent here than to repair downstream.
- **`nat_acct_should` removed,** replaced by `printed_account_codes`. The corpus records what the face says; the register rules on coding.
- **Credit notes given a sign convention and a `doc_kind`.**
- **`line_amount_basis` added at document level,** so a GST-inclusive template is declared rather than inferred from a tie that happened to work.
- **P3 scoped to completed documents,** so it cannot contradict the AMBER protocol.
- Kept unchanged in substance from v4: two-pass architecture, column-band anchoring, the exclusion list, the 4.4 invariant, the four-rung retry ladder, header-amount rules, OCR-by-need in runtime A, and the gate-first report.
