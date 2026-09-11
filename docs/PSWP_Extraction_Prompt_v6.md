# PSWP Invoice Extraction Prompt v6 (11-Sep-2026)

Supersedes v5 (9-Sep-2026), which superseded v4 and v3.1. For extraction of supplier-invoice binders to a structured JSON corpus for the PS/WP and Parks Branch Transaction Registers, Logan City Council, Parks Branch.

v5 is kept here in full and **amended, not rewritten**. That is deliberate: v4 broke things by rewriting v3.1, v5 said so, and the same mistake is not worth making twice. Everything v5 ruled still stands unless this file says otherwise.

**What v6 changes, and why.** v5 has the right rule for classifying a priced row and no way to tell whether you followed it. Two v5 runs on this project, `mix22` (40 invoices, four suppliers) and `Binder11111` (13 invoices, one supplier), both declared RED and between them left **34 printed rows carrying an amount typed NARRATIVE**, so 18 documents captured less than they printed and 13 captured nothing at all. Every one of those rows had its amount sitting in the item table's amount band, which is exactly what v5 section 4.2 says makes a row PRICED. The rule was not wrong. It was unenforceable, because neither run recorded the column bands section 4.1 asks for, and nothing checked that they had.

So v6 is mostly about **making v5's rules checkable**: bands are mandatory and gated, the amount band alone decides, the retry ladder has to show its work, the header block has to add up, and the line-type list is closed. Then, because the failures were spread across every layout the project meets, v6 adds **Annexe A, a template compatibility table** covering the 36 layouts seen to date (35 vendor templates, one of which prints two), with each one's header signature, amount band and known trap.

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

## 1. Declare your runtime (it sets your gates)

State this in the manifest as `runtime` before you do anything else, because three gates scale off it.

| Runtime | What you have | OCR gate | Fidelity audit |
|---|---|---|---|
| **A, code-capable** (terminal, Python, poppler, tesseract) | `pdftotext -layout`, `pdftoppm`, `tesseract`, `pypdf` annotations | Section 8 applies in full | Section 10, per-page multiset diff |
| **B, chat-only** (M365 Copilot, no terminal) | Document reading only | OCR is `not_available`, and P6 **does not fire** | Section 10, five-word shingle self-check on a stated sample |

**Runtime B is the normal case for this project and is not a degraded run.** Reading the PDF and transcribing every line of every page verbatim is the bulk of the value and is fully achievable. What you must not do in runtime B is pretend: do not report OCR you did not run, do not report a token-level audit you could not compute, and do not substitute a summary for the parts you cannot do. State in one list what a runtime A capture would add that you cannot supply: image-borne letterhead text and ABNs, hyperlink targets, scanned-page transcription, and the token-level completeness audits.

**New in v6.** Runtime B does not relax section 4. The band offsets of section 4.1 are read off the printed header row, which you can see; they are not a code artefact. A runtime B run that emits `"bands": {}` is P11, in both runtimes.

---

## 2. Two-pass architecture

Classification and arithmetic in one pass is why a misclassified line was never revisited.

**Pass 1, layout.** For each document: establish the page range, find the table header row, **record its column bands**, then emit one line record for every printed layout row with a provisional `line_type`.

**Pass 2, arithmetic.** For each document: sum the PRICED lines, compare to the printed subtotal, and if it does not tie, **run the retry ladder in section 6 before you are permitted to write `"self_tie": "OUT"`.** Reclassification during pass 2 is expected and correct. `line_text` is never edited in pass 2; only `line_type` and the numeric fields may change.

A document is emitted only after pass 2 completes on it. See section 7 for the emit protocol, which is what stops a long binder running out of budget mid-document.

---

## 3. Document boundary detection

A binder is many invoices in one file. **Split it before anything else is meaningful.**

1. Run supplier-specific invoice-number patterns over each page.
2. A page carrying exactly one identifier belongs to that document.
3. A page carrying **no** identifier inherits the previous page's document. That is correct for terms pages, payment advice pages and blank pages.
4. **A page can carry two documents.** Where one invoice's totals block is followed on the same page by another's letterhead, the page belongs to both: record it in both `page_range`s and say so in `notes`. A page range is inclusive and page ranges may overlap by one page for this reason only.
5. **Verify the split against page footers.** Xero and similar print `1 of 3`. If your split gives four pages where the footer says three, your split is wrong, not the footer.
6. **Two non-adjacent page runs resolving to the same identifier is a duplicate copy, not a split error.** Section 11.
7. **Report every identifier you find**, including any you cannot classify. Ledger matching is a later session's job, so an unrecognised identifier is reported, never dropped.
8. Assert before emitting: the union of all `page_range`s covers every page of the source, and no page is unaccounted for.
9. **NEW v6. Every page inside a document's own range carries at least one line record, even when the page is blank.** A blank page gets one `BLANK` record; a page you could read but chose not to transcribe is a full-capture breach. `Binder11111` left six pages with no record at all, across five of its thirteen documents, which is P3, and P3 cannot be repaired downstream: there is nothing to restate from. This is the cheapest pathology in the list to prevent and one of the few that cannot be fixed without re-extraction.

Known identifier patterns from prior batches:

| Supplier | Pattern |
|---|---|
| Savco Vegetation Services | `\b(SV\d{6})\b` |
| Xero-templated (Heritage Tree, Weis, Total Environmental, F82/Flavell-Dau, Play Force, MPDT, Certified Mowing, Coast2Coast) | `\b(INV-\d{3,5})\b`, credit notes `\b(CN-\d{5})\b` |
| Burly Holdings | `Tax Invoice #\s*(\d+)` |
| Link Resources Training | `\b(LR\d{4,6})\b` |
| Vinton Tree Services (RST Systems) | `Invoice No\.:\s*(\d{5})`, `Invoice number:\s*(\d{5})` |
| Greenway Turf Solutions | `\b(SI-\d{6,9})\b` |
| Q Power | `TAX INVOICE NO\.\s*(\d+)` |
| Harpley Services | `\b(000\d{5})\b`, **leading zeros are part of the number** |
| SECUREcorp | `\b(QLDPSI\d{7})\b` |
| Kachel Cleaning | `TAX INVOICE\s+No\.(\d{4})`, **a bare four-digit number, no prefix** |

**Trap:** the Total Environmental Concepts layout prints `Invoice Number` and the number on different physical lines with other text between, so `Invoice Number\s+(\d{4})` fails. Detect that supplier by name and read the number positionally. See 5.2, which generalises this.

**Trap:** `doc_ref` is the supplier's invoice number **exactly as printed, leading zeros included**. Downstream matching is on that string, and the ledger truncates long numbers (TCS 17118059 posts as `171180`), so a stripped or normalised `doc_ref` silently fails to match. The `C`-number in a file name is the TechOne document image id, a different fact: record it in `notes`, never in `doc_ref`.

---

## 4. Column anchoring: how to decide a line is PRICED

**This is the rule that failed on `mix1`, and then failed again on `mix22` and `Binder11111` for a different reason: v5 stated it and did not make it checkable.** Do not classify priced lines by whether the row starts with a number, and do not classify them by whether the row ends with a number. Both heuristics fail on real Parks invoices.

### 4.1 Find the header row first, and RECORD ITS BANDS

Every priced table has a header row printing some subset of: `Description`, `Item`, `Details`, `Quantity`, `Qty`, `HRS`, `Unit Price`, `Rate`, `Unit`, `GST`, `TAX CODE`, `Amount`, `Amount AUD`, `EX AMOUNT`, `Total`, `Total Price`, `Ex GST`, `Price`, `Price (Ex. GST)`.

- Record its page and row, its verbatim text, and the **character offset at which each column label begins**. Those offsets are the column bands.
- **NEW v6: `bands` is mandatory, not decorative.** A document with one or more PRICED lines and an empty or absent `bands` object is **P11** and the corpus is RED. Both v5 runs on this project emitted `table_headers` with `page`, `row` and `text` and no `bands`, and both then fell back to an unstated guess. Writing the offsets down is what forces you to test against them.
- Type the header row `TABLE_HEADER`. **It is not TOTALS.** On `mix1` the row `Description Quantity Unit Price GST Amount AUD` was typed TOTALS, which destroyed the only anchor the document had.
- **NEW v6: the first header-shaped row on the page is not always the item table's header.** Savco prints `INVOICE NO. | DATE | TOTAL DUE | DUE DATE | TERMS | ENCLOSED` as a header-shaped row twenty rows above the real one, `DESCRIPTION | QTY | RATE | GST | AMOUNT`. The item table's header is the one immediately above the priced rows and above the totals block. Record both if you wish; anchor on the second.
- More than one table means more than one header: record each and scope its bands to the rows beneath it.
- If no header row prints at all (Kachel), say so in `notes`, set `"bands": {"amount": <offset>}` from the totals block's own amount column, which is the same band, and fall back to 4.3.

### 4.2 Classify body rows by column occupancy

For each row beneath a header, test which column bands contain a numeric token, allowing a few characters of drift either side of the band start.

- **A row with a numeric token in the amount band is PRICED. That test is SUFFICIENT on its own.** Whatever the row begins with, whatever else it does or does not carry. `Darlington Parklands 1.00 63.46 10% 63.46` is PRICED. It begins with a word and contains a percentage. Neither disqualifies it.
- **NEW v6, and this is the v6 amendment that matters most. You may not add any of these conditions to the test:**
  1. **Do not require a quantity.** Savco prints `CREW 3: 3 MEN WITH TRUCK AND CHIPPER 26-05-2026    3    308.88    GST    926.64`. The quantity is `3`, an integer with no decimal point, and on `mix22` every Savco row with an integer quantity was dropped while every row with `1.25` or `1.75` was kept. Eleven Savco invoices captured nothing at all for that reason. Vinton's `DESCRIPTION | EX AMOUNT | TAX CODE` layout prints **no quantity column whatsoever**, and both its zero-capture documents on `Binder11111` were single-row invoices of $6,800.00 and $5,150.00.
  2. **Do not require two decimal places outside the amount band.** Play Force prints `1.00  MISC1  Weekly Inspection/Maintenance on going  1355  1355.00`: the unit price is `1355`, bare. Four invoices of $1,355.00 each captured nothing on `mix22` for that reason alone.
  3. **Do not require a unit price at all.** Kachel prints description and amount with nothing between them; Higgins, Glascott and Levai print `DESCRIPTION OF SUPPLY | AMOUNT`, a two-band table.
- A row with numerics only in the quantity or unit-price bands and nothing in the amount band is PRICED **if** the amount is derivable as printed elsewhere on the row; otherwise it is PRICED with a null amount and a `note`, and the document goes to the retry ladder.
- A row with no numeric in any band is NARRATIVE.
- A row sitting entirely left of the first numeric band and continuing a description above it is NARRATIVE with `"note": "wrapped description"`.
- **Zero-amount priced rows are real.** Xero prints `Contract # PAR329B2021  1.00  0.00  0.00` and site-address rows at `1.00 ... 0.00`. They carry the full column structure, so they are PRICED at 0.00. They cannot disturb the tie and the register needs them (rule 16).
- **NEW v6: a tax CODE in the tax band is not an amount and not a disqualifier.** Savco prints the literal `GST` between the rate and the amount; ETSol prints `GST` in a column headed `TAX`; Vinton prints `GST` in a column headed `TAX CODE`; Xero prints `10%`. None of these is money, and none of them stops the row being PRICED. Record it in `gst_rate_printed`, never in `gst`.

### 4.3 When there is no header row

Use the trailing-amount test, with these exclusions applied **before** testing:

- **GST rate tokens.** `10%`, `10.0%`, `GST 10%` are rates, never amounts. This is the most common false negative and the reason the `mix1` Play Force documents failed.
- **Date tokens.** `dd.mm.yyyy`, `dd.mm.yy`, `dd/mm/yyyy`, `dd Mon yyyy`.
- **Reference tokens.** Bare integers of six digits or more with no decimal point and no currency symbol, where the surrounding text names a reference, order, contract or account. **NEW v6:** a bank account number in the payment block is one of these. Play Force prints `Account: 10367833` next to `Account: PK000477`, and a corpus supplied to this project took the bank account as a PK on two documents.
- **Quantities.** A lone `1.00` at the start of a row is a quantity, not an amount.
- **`SUBTOTAL:` contains `TOTAL:`.** Match totals keywords before priced ones and use a negative lookbehind, `(?<!SUB)TOTAL:`. **NEW v6: `GST TOTAL` contains `TOTAL` too.** See 5.1.

Accept variable decimals: `$3,660`, `65.1`, `1,234.00` are all amounts.

### 4.4 The invariant that makes this checkable

**`line_type == "PRICED"` if and only if `line_ex_gst` is a number (or `stated_amt` on a GST-inclusive template).** These are not two independent assertions; one determines the other. Assert it both ways before emitting a document. A PRICED line with a null amount, and an amount-bearing line typed NARRATIVE, are each emit-blocking defects.

### 4.5 NEW v6. The residue test, which you run on every document

Before you emit a document, list every row that is (a) typed NARRATIVE, (b) positioned between the item table's header row and the first row of the totals block, and (c) carrying a money token inside the amount band.

**That list must be empty.** If it is not, you have not finished classifying: go back to 4.2. A non-empty residue on an emitted document is **P12**, and unlike a tie failure it is not a matter of judgement, because the row, its band and its amount are all in your own output.

This is the single check that would have caught all 34 dropped rows in both v5 runs, and you can run it in either runtime by reading your own line records.

---

## 5. Header amounts

One figure per labelled line. Never take a header amount from an unlabelled position.

- **`printed_total_incl_gst`** comes from `Total`, `TOTAL AUD`, `Balance Due`, `Amount Due`, `Total Outstanding`, `Total price including GST`. **Never** from `Subtotal`, and **never from `GST TOTAL`** (5.1). If the total is a bare `$` amount under `PLUS 10% GST` or `Sub Total:`, take it and say so.
- **`printed_gst`** comes from the `GST`, `TOTAL GST 10%`, `PLUS 10% GST` or `GST TOTAL` line. Never the Subtotal, never the Total. Where the GST line interleaves with the payment block, match by label, not position.
- **`printed_subtotal_ex_gst`** comes from `Subtotal` / `Sub Total`. If only the total and GST print, derive it as total less GST and set `"subtotal_basis": "derived from total less GST"`.
- **`invoice_date`** comes from the token labelled `DATE` or `INVOICE DATE`. Where a header prints `PLEASE PAY BY | AMOUNT | INVOICE DATE` on one row, the LAST date is the invoice date and the FIRST is the due date. Never a work-note or completion date.
- **Totals can print on the last page only.** Search every page of the document before recording a null. That is a capture note, not an extraction loss.
- **A null header field is a defect,** not an omission. Restate it from the page, or explain in `notes` why the layout does not carry it and record `"(not printed)"`.
- **Credit notes are negative.** A credit note or adjustment note carries negative `line_ex_gst`, `printed_subtotal_ex_gst`, `printed_gst` and `printed_total_incl_gst`, and `"doc_kind": "CREDIT_NOTE"`. Never record a credit as a positive and never flip the sign to make a tie work. The printed figures stay positive in `line_text`, which is never edited.

### 5.1 NEW v6. The label-substring trap, stated as a rule

`GST TOTAL` ends in `TOTAL`. On the Savco layout the totals block prints, in this order:

```
                          SUBTOTAL        4,522.50
                          GST TOTAL         452.25
                          TOTAL           4,974.75
                          BALANCE DUE
                                       A$4,974.75
```

On `mix22` the extractor took `printed_total_incl_gst` from the `GST TOTAL` row on **all thirteen** Savco documents, recording $452.25 as the total of a $4,974.75 invoice. Match the longest label first, or use a negative lookbehind on both: `(?<!SUB)(?<!GST )TOTAL`. The same care applies to `TOTAL GST 10%` (Xero), `Total (inc-GST)` (Vinton), `Total Payable` (Treescape) and `REMAINING CREDIT` (5.3).

### 5.2 NEW v6. The label-above-value rule, generalised

Xero and several other templates stack the label over its value and print an unrelated block to the right of both, so reading "the rest of the label's line" finds the letterhead:

```
                                    Invoice Number             MOSSMAN QLD 4873
              Logan City Council     INV-13892                 07 4098 8264
```

Read the label row, then take the **first matching value in the next four rows within the label's own band**. The gap can be two rows: on the Heritage credit-note layout `Credit Note Number` sits two rows above `CN-48535`. Record which row supplied each header figure in `header_sources` (section 9), so a wrong read is auditable rather than invisible.

### 5.3 NEW v6. The credit-advice trap

The Heritage credit-note layout closes with a credit advice printing `Credit Amount 0.00`. That is the credit **remaining after this note has been applied to an invoice**, not the value of the note. The note itself prints `Subtotal 408.33`, `TOTAL GST 10% 40.83`, `TOTAL AUD 449.16`, and the ledger posts $408.33 as a credit. Taking the advice figure yields a $0.00 credit note that ties nothing and matches nothing. The same shape appears as `Less Credit to Invoice(s)` and `REMAINING CREDIT`: both are applications, not values.

### 5.4 NEW v6. The header block must add up, and it is a gate

After reading the three header figures, test:

```
round(abs(printed_subtotal_ex_gst + printed_gst - printed_total_incl_gst), 2) <= 0.02
```

If it fails, **you have misread one of the three**: re-read the totals block before going any further, because every downstream check is built on these. If it still fails after a re-read, the invoice itself is defective: keep the figures as printed, record it as a finding under section 14.1 with the three amounts, and say which row supplied each.

An unexplained failure of this test is **P10**. It costs one subtraction and it would have turned all thirteen Savco misreads RED at extraction time rather than at build time.

---

## 6. The arithmetic gate and the retry ladder

For every document, in pass 2:

```
captured = sum(line_ex_gst for PRICED lines)
tie      = round(abs(captured - printed_subtotal_ex_gst), 2) <= 0.02
```

If `tie` is false, **you may not write `"self_tie": "OUT"` until you have run all four rungs and recorded the result of each in `retry_log`.**

**Rung 1, missed priced rows. NEW v6: this rung is evidenced, not asserted.** Run the residue test of 4.5 and write the result into `retry_log` as a list of row numbers with their amounts:

```json
{"rung": 1, "found": "residue test: rows 33, 34, 36, 37 carry 926.64, 531.36, 1544.40, 912.60 in the amount band",
 "rows": [33, 34, 36, 37]}
```

`"rung": 1, "found": "Candidate amount-band rows rechecked."` is not a result. It is a sentence about a result, and on `mix22` it was recorded on a document that had four such rows sitting in its own output. **A `retry_log` rung 1 entry with no `rows` key, on a document at OUT, is P12.** If the list is empty, say so explicitly: `"rows": []`.

**Rung 2, GST-inclusive template.** Test whether the captured lines instead tie the printed **total including GST**. If they do, set `"tie_basis": "incl_gst"` and `"line_amount_basis": "incl_gst"`, record it, and the document ties. Harpley template B (the `Your Order No:` header) and the Coast2Coast `INCLUDES GST 10%` layout are the standing examples.

**Rung 3, rate-versus-amount confusion.** Check whether any captured amount is actually a GST rate, a quantity, or a unit price read into `line_ex_gst`. Recompute from the correct band.

**Rung 4, split or continued table.** Check whether the table continues on a following page, whether a second table sits beneath a second header, and whether its rows were attributed to the wrong document. Check the page range against section 3.

Only if all four fail: `"self_tie": "OUT"`, with `retry_log` recording what each rung found and `notes` stating in one sentence what the analyst should look at.

**NEW v6: a document at OUT with zero PRICED lines is never a tie failure.** It is P1, it is a parse failure, and rung 1 is where it gets fixed.

---

## 7. Emit protocol and budget

A 317-page binder will exhaust your budget before it exhausts the work. Plan for that from the first document rather than discovering it at page 83.

1. **Emit per document, not per binder.** Complete pass 1 and pass 2 on one document, emit its record, then move on. Never hold 112 documents open and write at the end.
2. **Chunk the output so the pieces concatenate.** If the corpus will not fit one message, emit it as `part 1 of n` and so on, each a fenced block, each containing whole document records, the manifest last. Say plainly which documents are in which part.
3. **Keep a live counter.** `coverage.documents_complete` and `documents_total` are updated as you go, not estimated at the end.
4. **Stop at a document boundary.** If you are running short, stop cleanly, emit what you have with `"gate": "AMBER"`, and give `resume_point` as the exact first uncaptured page and document identifier. **Never emit a partial run as though it were whole.** An honest AMBER at document 60 of 112 is buildable; a silent stop at page 83 is not.
5. **No interim status reports.** One report at the end, per section 15.

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
    "prompt_version": "v6",
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
  "header_sources": {"printed_subtotal_ex_gst": {"page": 1, "row": 39},
                     "printed_gst": {"page": 1, "row": 40},
                     "printed_total_incl_gst": {"page": 1, "row": 41}},
  "header_adds_up": true,
  "captured_ex_gst": 0.00,
  "line_amount_basis": "ex_gst | incl_gst",
  "tie_basis": "ex_gst | incl_gst",
  "self_tie": "TIE | OUT",
  "retry_log": [{"rung": 1, "found": "...", "rows": []}],
  "table_headers": [{"page": 1, "row": 17, "text": "<verbatim>",
                     "bands": {"description": 0, "quantity": 47, "unit_price": 67,
                               "gst": 87, "amount": 99},
                     "is_item_table": true}],
  "work_orders": [], "contract_refs": [], "po_refs": [], "pk_refs": [],
  "printed_account_codes": [],
  "evidence_stem": "<Supplier, short what-for, Mon-YYYY, amount>",
  "duplicate_of": null, "duplicate_copy_pages": [],
  "findings": [{"code": "F1", "detail": "...", "amount": 0.00}],
  "notes": "<face codes, references, oddities, which row supplied each header figure>",
  "lines": [ ]
}
```

**NEW v6 fields:** `header_sources` and `header_adds_up` (section 5), `duplicate_copy_pages` (section 11.4), `bands` and `is_item_table` inside `table_headers` (section 4.1), `rows` inside a rung 1 `retry_log` entry (section 6).

`printed_account_codes` captures an account or cost code **printed on the face**, verbatim. It replaces v4's `nat_acct_should`, which asked the extractor for a coding judgement. Coding is the register's ruling, made against the chart of accounts on sighted evidence, and an extractor's guess arriving in the corpus is a matching aid at best and a contaminant at worst.

### Line record, one per printed layout row

```json
{
  "source": "TEXT | OCR | ANNOT", "page": 1, "line_no": 1,
  "line_text": "<verbatim, leading whitespace preserved>",
  "line_type": "PRICED | NARRATIVE | TABLE_HEADER | TOTALS | FOOTER | TERMS | BLANK | PAYMENT_ADVICE | OCR_DUPLICATE | IMAGE_TEXT | ANNOTATION | DUPLICATE_COPY",
  "ocr_only": false, "ocr_status": "run | not_required | not_available | outstanding", "ocr_reason": null,
  "qty": null, "unit": null, "unit_price_ex_gst": null,
  "line_ex_gst": null, "gst": null, "gst_rate_printed": null, "stated_amt": null,
  "band_hits": [], "work_order": null, "note": null
}
```

**NEW v6: `line_type` is a CLOSED list.** Those twelve values and nothing else. `Binder11111` emitted 245 rows typed `DUPLICATE`, which is not one of them, so every downstream screen for `DUPLICATE_COPY` missed them. A value outside the list is **P13**.

`band_hits` names which column bands carried a numeric on this row. It is the evidence for the classification and makes a wrong call auditable after the fact. `gst_rate_printed` carries a printed rate or tax code (`10%`, `GST`, `FRE`); `gst` carries a printed GST **amount** and nothing else.

---

## 10. Verbatim fidelity

`line_text` is the layout row exactly as printed, including leading whitespace, which carries the column positions section 4 depends on. Never trim, never normalise, never collapse runs of spaces. `rstrip()` only, never `strip()`.

**Runtime A.** Report the multiset difference **per page**, both directions, and list up to twenty actual differing tokens with page numbers in `manifest.text_layer_diffs`. A bare count is unactionable: `45` tells the analyst nothing. A difference caused by a ligature, a soft hyphen or an encoding artefact is recorded and dismissed with a reason. Any difference not so dismissed is a P3-class concern and must be named in the report.

**Runtime B.** Re-read a stated sample and check five-word shingles against your captured text: every document where you captured fewer than 40 lines, and at least one document per supplier otherwise. Record `shingle_checks_run` and `shingle_failures`, and state the sample rule you applied. Do not report `text_layer_diffs` you could not compute; leave the array empty.

**NEW v6.** `shingle_checks_run: 0` on a runtime B corpus of 40 documents is not a pass, it is an omission, and both v5 runs on this project reported exactly that. If you did not run the check, the report says so in those words rather than reporting a zero that reads like a clean result.

---

## 11. Standing rules

1. **Verbatim only.** A summary row in place of line capture is a critical failure.
2. **Full page representation.** Every page appears; every text-layer row appears. OCR content is typed `OCR_DUPLICATE` on text-layer pages and `IMAGE_TEXT` for image-borne content such as letterheads.
3. **The ABN is the SUPPLIER's,** from the letterhead or footer. LCC's own ABN `21 627 796 435` prints in the bill-to block. Capture the printed grouping verbatim, even where mis-grouped. An ABN present only as pixels is legible on the page and not a defect, but it is invisible to a text check, so flag `abn_source`.
4. **Duplicate copy pages.** Capture both copies. Type every line of the second `DUPLICATE_COPY` with arithmetic fields nulled, and **NEW v6** list those pages in `duplicate_copy_pages`. Where the duplicate is a second copy of the same invoice inside one page range, that field is the whole record of it and `duplicate_of` stays null; where it is a separate document record, set `duplicate_of` to the first record's page range. Report it as a finding rather than housekeeping. Saying in the report that duplicates were "excluded from arithmetic" while leaving both fields empty, as `Binder11111` did, leaves the build unable to see what was excluded.
5. **GST-inclusive-only templates:** capture ex GST as printed total less printed GST, record the treatment, and do not invent ex-GST priced lines.
6. **Wrapped descriptions** get their own NARRATIVE record and are never truncated mid-phrase or rejoined. `pdftotext -layout` splitting a description across physical lines is correct behaviour. On Xero layouts a numeric-only row belongs to the description line immediately **above** it; description lines **below** the numbers are continuation text and stay NARRATIVE.
7. **Face codes and references** (PK numbers, CR and WO numbers, contract refs, POs) are captured verbatim in their fields AND left verbatim in `line_text`. Record a PK typo as printed; normalisation happens on join, not here. MPDT prints `PK#00047` and `PK#0000477` on consecutive invoices, both PK000477 on the ledger, and `PK00042` for PK000042 has been seen; capturing the printed form is what lets the register raise the finding.
8. **Correspondence in a binder is evidence.** Capture it, type it `FOOTER` or `NARRATIVE`, set `doc_kind` to `CORRESPONDENCE` where it stands alone, and never discard it.
9. **One invoice can span several sections and natural accounts.** Never record a section or account at document level; they are line-level facts.
10. **Rounding.** Some suppliers compute GST on the subtotal rather than per line, so per-line GST at 10% can differ by a cent or two. Record as printed, never adjust, and list the differences.
11. **A printed per-line GST of $0.00 alongside a non-zero amount is a GST-free supply, not an error.** Accredited training and some trust-structure suppliers are the standing cases. Do not compute a GST-inclusive figure or a check result into the corpus; those are live formulas in the destination workbook.

---

## 12. Evidence stem rule

`Business Name, What it was For, Date, Amount`, 40 characters maximum, no extension. Amount is the invoice incl-GST total, two decimals, no dollar sign, **negative for a credit note**. Degrade in this order and never trim the amount: full date `D-Mon-YYYY`, then `Mon-YYYY`, then a shorter purpose, then a shorter business name.

**Stems must be unique across the batch.** Two invoices from one supplier on one day for one amount will collide; break the tie by appending the last three digits of the invoice number to the purpose, then re-run the ladder.

---

## 13. Pathologies that force a gate

These are not tie failures. They are parse failures, and a corpus containing an unresolved one is RED.

| Code | Condition | Why it is fatal |
|---|---|---|
| **P1** | `printed_subtotal_ex_gst` non-zero and zero PRICED lines | The document was not parsed at all. `mix1` shipped 15, `mix22` 11, `Binder11111` 2. |
| **P2** | `line_type == "PRICED"` with null amount, or an amount-bearing row typed NARRATIVE | Breaks the 4.4 invariant |
| **P3** | A page inside a completed document's range with no line records | Full-capture breach, and **not repairable downstream**: there is nothing to restate from. Pages beyond `resume_point` in an AMBER run are not P3. |
| **P4** | `supplier_abn` equals the LCC ABN `21 627 796 435` in any grouping | The bill-to ABN was read as the supplier's |
| **P5** | Null `printed_total_incl_gst` where a Total line demonstrably prints | Header-amount breach |
| **P6** | `ocr_pages_outstanding > 0` (runtime A only) | The corpus is not multi-source. Does not fire in runtime B. |
| **P7** | Two documents sharing a `doc_ref` with neither marked `duplicate_of` | Duplicate screening breach |
| **P8** | A number emitted as a string, or carrying `$` or a thousands separator | Every downstream check has to be repaired before it can run |
| **P9** | Page ranges that leave a gap, or overlap by more than the one page 3.4 permits | The split is wrong, and every amount attributed from it is suspect |
| **P10 (NEW v6)** | `printed_subtotal + printed_gst != printed_total` beyond 2c, with no finding explaining it | A header figure was read off the wrong labelled row. Caught all 13 Savco misreads on `mix22`. |
| **P11 (NEW v6)** | A document with PRICED lines whose item-table header carries no `bands` | Section 4 was not anchored, so every classification on the document is a guess |
| **P12 (NEW v6)** | The 4.5 residue is non-empty, or a rung 1 `retry_log` entry on an OUT document carries no `rows` | The rows are sitting in your own output, unclassified or unexamined |
| **P13 (NEW v6)** | A `line_type` outside the closed list in section 9 | Every downstream screen for that type silently misses the rows |

Set `"gate": "RED"`, list every pathology in `manifest.pathologies` with the affected `doc_ref` and page, and say plainly in the report that the corpus must not be built from. **A RED corpus is a useful, honest output. A GREEN corpus containing a P1 is a fabrication.**

---

## 14. Findings to raise, not bury

The register turns these into numbered Open Items, so a finding you notice and do not record is work the analyst repeats. Record each on the document's `findings` array and repeat it in the report with the document reference and the dollar amount.

1. **Tax invoice defects.** Missing GST amount or total on a document over $1,000, missing ABN, missing supplier identity, and **NEW v6** a header block that does not add up after a re-read (5.4). Note separately where an ABN exists **only as pixels**.
2. **Documents that do not support the line they appear to be filed against**, so far as that is visible from the document itself: wrong amount, wrong year, wrong party.
3. **Fuel levy lines**, flagged for verification against the stepped and capped model.
4. **Coding candidates**, where a PK or account code printed on the face looks wrong, and documents stating **no PK at all**. A PK not of the `PK000000` form is one of these.
5. **Referenced but absent documents**: tip dockets, cost breakdowns, quotes, fixed-fee schedules, site photographs. The evidence pack is not complete until they are requested.
6. **Duplicate copies and blank pages.**

**NEW v6: do not raise an evidence finding on a document that failed to parse.** On `mix22`, seven of the nine findings raised were "pricing is stated as per quote, but the supporting quote is not in this binder" on documents that had captured $0.00 of a printed $8,920.00. The finding may well be true, but it is not the finding: the parse is. Fix the parse, then judge the evidence.

---

## 15. Capture report

Close with a short report, in this order:

1. **Gate: GREEN, AMBER or RED**, on its own line, first.
2. Runtime, A or B, and the extraction tool and model.
3. Pathologies by code with document references, or the word "none".
4. Pages represented of pages total; documents complete of documents total.
5. Documents at TIE and OUT, every OUT named with its retry ladder outcome **and its rung 1 row list**.
6. Line records by type, and captured ex GST total.
7. Identifiers found, and any unclassified.
8. OCR: pages run, not required, not available, outstanding.
9. Fidelity: per-page diffs with dismissals reasoned (runtime A), or shingle checks run and failed with the sample rule stated (runtime B). If none were run, say so in words.
10. Findings from section 14, each with its reference and amount.
11. Resume point, if AMBER.

**Lead with the gate.** The build session reads that line first and stops there if it is not GREEN.

---

## 16. Worked examples

### 16.1 The `mix1` failure (kept from v5)

Play Force invoice INV-3880, page 1. The binder printed:

```
Description                    Quantity        Unit Price      GST        Amount AUD
Darlington Parklands           1.00            63.46           10%        63.46
                                                               Subtotal   63.46
                                                            TOTAL GST 10%  6.35
                                                              TOTAL AUD   69.81
```

**v3.1 produced:** the header row typed TOTALS, the body row typed NARRATIVE with a null amount, zero PRICED lines, `captured_ex_gst: 0.00`, `self_tie: OUT`. The document shipped.

**v5 and v6 produce:** the header row typed `TABLE_HEADER` with bands recorded; the body row tested against the amount band, found to carry `63.46`, typed PRICED with `line_ex_gst: 63.46`, `band_hits: ["quantity","unit_price","amount"]`; captured $63.46; ties the printed subtotal; `self_tie: TIE`.

### 16.2 NEW v6. The `mix22` Savco failure

Invoice SV007794, page 1, printed:

```
DESCRIPTION                                            QTY      RATE      GST     AMOUNT
CREW 3: 3 MEN WITH TRUCK AND CHIPPER 25-05-2026       1.25    308.88      GST     386.10
CREW 6: SUPPLY EWP ( 18MTO 23M) WITH OPERATOR         1.25    177.12      GST     221.40
CREW 3: 3 MEN WITH TRUCK AND CHIPPER 26-05-2026          3    308.88      GST     926.64
CREW 6: SUPPLY EWP ( 18MTO 23M) WITH OPERATOR            3    177.12      GST     531.36
CREW 3: 3 MEN WITH TRUCK AND CHIPPER 24-06-2026          5    308.88      GST   1,544.40
CREW 7: SUPPLY EWP ( TOW ALONG OMNI - SPIDER -           5    182.52      GST     912.60
                                                    SUBTOTAL                    4,522.50
                                                    GST TOTAL                      452.25
                                                    TOTAL                       4,974.75
```

**v5 produced:** the first two rows PRICED, the other four NARRATIVE, `captured_ex_gst: 607.50` against a printed subtotal of $4,522.50, `printed_total_incl_gst: 452.25`, `self_tie: OUT`, and a `retry_log` recording `"rung": 1, "found": "Candidate amount-band rows rechecked."`

Two separate defects, both mechanical. The four dropped rows differ from the two kept rows in exactly one respect: their quantity prints as an integer. And the total was taken from the `GST TOTAL` row.

**v6 produces:** all six rows PRICED on the amount-band test alone, because 4.2 forbids requiring a quantity format; captured $4,522.50, which ties. The header block is tested under 5.4: $4,522.50 + $452.25 = $4,974.75, which is the `TOTAL` row, not the `GST TOTAL` row. And if the rows had still been missed, the 4.5 residue test names them before the document can be emitted, and the rung 1 entry has to carry `"rows": [33, 34, 36, 37]`.

### 16.3 NEW v6. The `Binder11111` Vinton failure

Invoice 19900, page 23, printed:

```
DESCRIPTION                                                    EX AMOUNT      TAX CODE
CR #3897268, PK #000477, 17 Veivers Rd Woolffdene              $6,800.00      GST
Completed 05/08/2026
```

**v5 produced:** zero PRICED lines, `captured_ex_gst: 0.00` against a printed subtotal of $6,800.00, P1, and a rung 1 entry reading `"Amount-band rows rechecked."`

This layout has **no quantity column and no unit price column at all**. A classifier that wants three numeric bands before it will call a row PRICED can never parse it.

**v6 produces:** the row PRICED on the amount band alone, `band_hits: ["amount"]`, `gst_rate_printed: "GST"`, captured $6,800.00, which ties.

---

## Annexe A. Template compatibility

Every layout this project has met, with the item table's header signature as printed, the band that carries the line amount, and the trap that catches an extractor. **A layout not in this table is not a reason to stop**: work it with sections 4 and 5, which are template-agnostic, and add a row here in the same session (rule 19.1).

| Template | Item table header, as printed | Amount band | Trap |
|---|---|---|---|
| SAVCO | `DESCRIPTION \| QTY \| RATE \| GST \| AMOUNT` | rightmost `AMOUNT` | Quantities print as bare integers. `GST TOTAL` sits above `TOTAL` (5.1). `BALANCE DUE` prints its figure on the NEXT row. A header-shaped `INVOICE NO. \| DATE \| TOTAL DUE ...` row prints 20 rows higher. |
| HERITAGE | `Description \| Quantity \| Unit Price \| GST \| Amount AUD` | `Amount AUD` | The `Contract #` row prints `1.00 0.00 0.00` and is a real zero-amount priced row. |
| HERITAGE_CN | same, credit note | `Amount AUD` | The credit advice prints `Credit Amount 0.00`, the credit REMAINING, not the value (5.3). Face figures are positive; capture negative. |
| PLAYFORCE | `Qty \| Item \| Description \| Unit Price \| Price (Ex. GST)` | `Price (Ex. GST)` | Unit price can print with no decimals (`1355`). `Account: 10367833` in the payment block is a bank account, not a PK. Some invoices print the literal word `undefined` in the Account field. 220 fixed template rows per document. |
| KACHEL | none printed | rightmost money column under `Rate $` | No item table header at all. Zone rows print `PK000028  19,716.00` with no quantity. |
| VINTON (A) | `DESCRIPTION \| EX AMOUNT \| TAX CODE` | `EX AMOUNT` | No quantity and no unit price columns exist. |
| VINTON (B) | `HRS \| DESCRIPTION \| UNIT PRICE (ex-GST) \| TOTAL PRICE (ex-GST)` | `TOTAL PRICE` | The `GST:` label and its amount print on different physical rows, and the bank block interleaves with the totals block. |
| MPDT | `Description \| Quantity \| Unit Price \| GST \| Amount AUD` | `Amount AUD` | Header labels stack above their values (5.2). PK prints malformed: `PK#00047`, `PK#0000477`. |
| PPG (SAP) | `Item No \| Material \| Item Description \| Quantity \| Unit Price \| Net Value` | `Net Value` | **No row is labelled Subtotal**: the ex-GST total is `PRODUCT TOTAL` plus `FREIGHT` plus `PAINTBACK LEVY`, each printed separately. The unit price prints to FOUR decimals (191.1400). No PK prints on the face; the line description is a price-change reason code and `MIXED MERCHANDSE`. Terms of sale fill page 2. |
| ETSOL | `Description \| Qty \| Rate \| TAX \| Amount` | `Amount` | The `TAX` column prints the literal `GST`, a code, not money. Negative rows appear for partial deletions. |
| GLASCOTT | `Invoice No` face plus an attached schedule | schedule `Ex GST` column | The face total and the attached schedule total can differ (Open Item B-019). Schedule rows carry no amount in the face table. |
| GLASCOTT_LM, HIGGINS, LEVAI | `DESCRIPTION OF SUPPLY \| AMOUNT` / `DESCRIPTION \| AMOUNT` | `AMOUNT` | A two-band table: no quantity, no unit price. |
| C2C | `Description \| Quantity \| Price \| Tax \| Amount` | `Amount` | Fuel levy surcharge posts to a separate PK and service (split posting). |
| C2C_INCL | `Description \| Quantity \| Unit Price \| GST \| Amount AUD` | `Amount AUD`, **GST inclusive** | Unit Price and Amount columns are GST INCLUSIVE; the description states the ex-GST base. Foot prints `INCLUDES GST 10%`. |
| CERTIFIED | `Description \| Quantity \| Unit Price \| GST \| Amount AUD` | `Amount AUD` | Main-roads and parks split across two PKs on one invoice. |
| ELEMENTAL | `Item Code \| Description \| Unit Price \| Quantity \| GST \| Total` | `Total`, **GST inclusive** | `Total` column is GST inclusive; ex = Total less GST. Quantity sits to the RIGHT of unit price. |
| QPOWER | `Part # \| Item \| Quantity \| Unit Price \| GST \| Total` | `Total` | Wide simPRO layout; item names wrap onto the rows above AND below at column 177. |
| HARPLEY | `QUANTITY \| DESCRIPTION \| UNIT PRICE(ex-GST) \| TOTAL PRICE(ex-GST)` | `TOTAL PRICE` | Template B is GST INCLUSIVE (rung 2). Invoice numbers keep leading zeros (`000\d{5}`). Two-page with a How-to-pay page. |
| ORIGIN | consolidated site rows | per-site `Amount` | Council-wide consolidated invoice, 47-48 sites; Parks carries a subset (PARTIAL-SCOPE). CR credits capture negative. Per-site GST prints. |
| SEACRETE | `Code \| Description \| Quantity \| Rate \| Amount` | `Amount` | Small single-site water-park invoices. |
| POOLSHOP | `Description \| Quantity \| Price \| Tax \| Amount` (old) and `... \| Unit Price \| GST \| Amount AUD` (new Xero) | `Amount` | Two layout vintages from one supplier. |
| WEIS | both Xero vintages, as POOLSHOP | `Amount` | Prints its ABN grouped on one template and ungrouped on the other. |
| FLAVELL, FLAVELL_ATT | Xero vintages | `Amount` | On the attachment layout a row can print `description 10% amount` with no quantity. |
| BURLY | `DESCRIPTION \| QTY \| UNIT PRICE \| TOTAL PRICE` | `TOTAL PRICE` | Amounts print with a `$` inside the band. |
| PROVAC | `Item \| Description \| Quantity \| Unit Price \| GST \| Amount AUD` | `Amount AUD` | Cemetery grave-dig dockets; `Amount Due` is the total label. |
| TREESCAPE | wide Xero-like | `Amount` | Total label is `Total Payable`, printed on a following row. |
| BUSHCARE | `DESCRIPTION \| QTY \| RATE \| AMOUNT \| GST` | `AMOUNT`, **left of the GST column** | The amount band is NOT rightmost: `GST` prints to its right. Total label is `BALANCE DUE A$`. |
| AUSTSPRAY | `Item \| Total` | `Total` | Item row figures differ from the "plus gst" figure in the description (Open Item B-021). |
| AUSTCARE | job table with Job No, Site Name, PK | `$` column | Column collision in `-layout`; needs word-level bounding boxes to assign site names to job rows. |
| EMU, TEC, ACTIVECO, GURU | `Description \| Quantity \| Unit Price \| GST \| Amount AUD` | `Amount AUD` | GURU prints two vintages. TEC prints `Invoice Number` and its value on non-adjacent rows (5.2). |
| SECUREcorp | wide, wrapped | `Amount` | A printed line wraps over several physical rows: rate and amount print on the first, quantity on the second. |

---

## Annexe B. The two v5 runs that produced v6

Both are on file in this project and both are worth reading before a big binder.

| | `mix22` | `Binder11111` |
|---|---|---|
| Suppliers | Savco, Heritage, Play Force, Kachel | RST Systems t/a Vinton |
| Documents | 40 | 13 |
| Declared gate | RED, 11 × P1 | RED, 2 × P1 |
| Documents at OUT | 16 of 40 | 2 of 13 |
| Captured ex GST as extracted | $109,059.92 | $40,295.05 |
| Captured ex GST after restatement | $166,863.84 | $52,245.05 |
| Value dropped by the classifier | **$57,803.92, 35% of the batch** | **$11,950.00, 23% of the batch** |
| Rows carrying an amount typed NARRATIVE | 32 | 2 |
| Header misreads | 13 (`GST TOTAL` read as `TOTAL`) | 0 |
| `bands` recorded | none | none |
| `shingle_checks_run` | 0 | 0 |
| Repairable downstream? | Yes: every dropped row was in the retained text | **No.** Six pages, across five documents, carried no line record at all (P3), so the batch is held for re-extraction |

The difference between those last two rows is the whole argument for v6. A misclassified row is recoverable, because the evidence is still in the corpus. A page you did not transcribe is gone, and the binder has to be read again.

---

## 17. What changed from v5

- **Bands are mandatory and gated (4.1, P11).** v5 asked for them, the schema showed them, nothing checked them, and neither v5 run produced any. That is why the rule that was right was not followed.
- **The amount band alone decides (4.2),** with three named prohibitions: do not require a quantity, do not require two decimals outside the amount band, do not require a unit price. Each of these dropped real money in a v5 run.
- **The residue test (4.5, P12).** Before emitting, list every NARRATIVE row between the item header and the totals block carrying money in the amount band. It must be empty. This one check catches all 34 v5 failures, in either runtime.
- **Rung 1 must show its rows (6, P12).** A sentence about a recheck is not a recheck.
- **The header block must add up (5.4, P10),** with the `GST TOTAL` substring trap (5.1), the label-above-value rule generalised (5.2) and the credit-advice trap (5.3) stated.
- **`line_type` is a closed list (9, P13),** after 245 rows shipped as `DUPLICATE`.
- **Every page inside a document's range carries a record, blank ones included (3.9),** because P3 is the one pathology that cannot be repaired downstream.
- **`header_sources`, `header_adds_up`, `duplicate_copy_pages`, `is_item_table` and rung 1 `rows` added to the schema**, so each new check leaves its evidence in the corpus.
- **Findings discipline (14).** No evidence finding on a document that failed to parse.
- **Fidelity honesty (10).** `shingle_checks_run: 0` is stated as an omission, not left to read as a pass.
- **Annexe A, template compatibility,** covering the 36 layouts met to date, and Annexe B, the two failures that produced this version.
- Kept unchanged in substance from v5: the runtime declaration, two-pass architecture, document boundary detection, the misroute guard, the exclusion list, the 4.4 invariant, the four-rung ladder, header-amount rules, OCR-by-need in runtime A, the emit protocol, the evidence stem rule, the findings register and the gate-first report.
