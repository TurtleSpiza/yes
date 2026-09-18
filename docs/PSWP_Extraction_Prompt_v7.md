# PSWP Invoice Extraction Prompt v7.6 (18-Sep-2026; the duplicate_of standing rule and the description layer as a separate axis)

Supersedes v6 (11-Sep-2026), which superseded v5, v4 and v3.1. For extraction of supplier-invoice binders to a structured JSON corpus for the PS/WP and Parks Branch Transaction Registers, Logan City Council, Parks Branch.

**Version sequence.** v7 as supplied is dated 18-Sep-2026 and the v7.1 amendments were applied on 17-Sep-2026,
which reads as a point release predating its parent. It is a timezone artefact and not a reordering: the
sequence is v7, v7.1, v7.2, v7.3, v7.4, and Annexes D, D1 and D2 record them in that order. Where two versions
share a date, the annexe order governs.

**v6 is kept here in full and amended, not rewritten, and every v6 section number, pathology code and cross-reference still means what it meant.** v4 broke things by rewriting v3.1; v5 said so; v6 said so again. New material lands as new sub-sections inside the existing numbering (4.0, 4.6, 5.5, 5.6, 6.0, 9.1, 13.0, 14.7, 15.1, Annexe C). Nothing in the capture or verification standard is relaxed.

**What v7 changes, and why.** v6 made v5's rules checkable. It did not make them fast, and it left four mechanical routes to a wrong answer that no gate could see.

1. **A band recorded as a single offset cannot match a right-aligned money column.** v6 says record the offset where the label begins and allow "a few characters of drift". On the conformance invoice at 16.4 the label `AMOUNT` ends at column 116 while its values end at 118, 119 and 120, and their left edges range over six columns because the amounts are of different widths. A left-edge test with small drift rejects the very rows it exists to catch. v7 records each band as a **span** and tests by **overlap** (4.1, 4.2).
2. **No stated order of classification.** A totals row carries money in the amount band too. v6 states "match totals keywords before priced ones" once, inside 4.3, which applies only when there is no header row. v7 promotes it to a closed decision ladder run in one order on every row (4.0).
3. **The gate words were never defined.** GREEN, AMBER and RED are used throughout v6 and defined nowhere, so a corpus with a legitimate OUT document could ship GREEN. v7 defines them in a truth table (13.0).
4. **The corpus tied at 2c while the destination workbook checks at 1c** (register rule 17), so a GREEN corpus could fail the build. v7 ties at **1c** and sends the 1c to 2c band to AMBER with a finding (6.0, F7).

On speed, v7 adds the **run sheet** below, a fast path off Annexe A (2.1), a reference algorithm for runtime A (4.6), and per-document evidence fields a script can check without a human reading the corpus (9.1). Annexe C lists every amendment against its v6 section. Every addition either removes a decision you would otherwise make from first principles, or replaces a claim with evidence.

---

## RUN SHEET, read this first, then section 1

Per document, in this order. A step you skip is a pathology, and the code is named.

| # | Step | Gate if skipped or failed |
|---|---|---|
| 1 | Declare `runtime` in the manifest, once per corpus (section 1) | Report is unreadable without it |
| 2 | Split the binder; verify against page footers; every page lands in exactly one range (section 3) | P9, P3 |
| 3 | Identify the template against Annexe A; if listed, take its amount band, total label and tie basis as your starting hypothesis (2.1) | Speed only, never a substitute for step 4 |
| 4 | Find the item table header; record each band as a **span**; calibrate the amount band against a real priced row and record which row (4.1) | P11 |
| 5 | Transcribe every printed row of every page in range, verbatim, one line record each, blanks included (3.9, section 10) | P3 |
| 6 | Classify every row on the ladder in 4.0, amount-band overlap deciding PRICED (4.0, 4.2) | P2, P13 |
| 7 | Read the three header figures by label precedence, record `header_sources`, test that they add up (5.0, 5.4) | P5, P10 |
| 8 | Run the residue test and emit `residue_rows`, empty list included (4.5) | P12 |
| 9 | Tie captured PRICED lines to the printed subtotal at 1c; if it fails, run all four rungs and record each (6.0, section 6) | P1, P12 |
| 10 | Sign check on credit notes; stem built and checked unique (5.0, section 12) | P14, P15 |
| 11 | Emit the document, then move on. Never hold the binder open to the end (section 7) | AMBER at best |

Corpus level, once: page coverage assertion, `doc_ref` uniqueness, stem uniqueness, gate decided on the 13.0 truth table, report written per section 15.

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

**Runtime B does not relax section 4** (v6). Bands are read off the printed header row, which you can see; they are not a code artefact. A runtime B run that emits `"bands": {}` is P11, in both runtimes.

**NEW v7. Bands are offsets into your own `line_text` strings, in both runtimes.** This is what makes them checkable by a script and identical across runtimes: you emit `line_text` verbatim with leading whitespace preserved (section 10), so column positions exist inside your own output whether or not you ran `pdftotext`. Count characters in the strings you emit, never in a rendering nobody else can see. A band offset that does not correspond to your own `line_text` is worse than no band, because it passes P11 and misleads the build.

---

## 2. Two-pass architecture

Classification and arithmetic in one pass is why a misclassified line was never revisited.

**Pass 1, layout.** For each document: establish the page range, find the table header row, **record its column bands as spans and calibrate them**, then emit one line record for every printed layout row with a provisional `line_type` from the 4.0 ladder.

**Pass 2, arithmetic.** For each document: sum the PRICED lines, compare to the printed subtotal, and if it does not tie, **run the retry ladder in section 6 before you are permitted to write `"self_tie": "OUT"`.** Reclassification during pass 2 is expected and correct. `line_text` is never edited in pass 2; only `line_type` and the numeric fields may change.

A document is emitted only after pass 2 completes on it. See section 7 for the emit protocol, which is what stops a long binder running out of budget mid-document.

### 2.1 NEW v7. The Annexe A fast path

Before pass 1, match the letterhead and the header signature against Annexe A. Where the template is listed you already know its amount band, its total label, its tie basis and its standing trap, so pass 1 becomes transcription rather than discovery, and rung 2 of the ladder is tested first rather than fourth on the templates known to be GST inclusive (Harpley B, C2C_INCL, ELEMENTAL).

**The fast path sets a hypothesis, never a result.** You still record the bands you actually observe, still calibrate them against a real priced row, and still run every gate. Where the document disagrees with Annexe A, the document wins and you add or amend the Annexe row in the same session (rule 19.1). A template not in Annexe A is not a reason to stop: sections 4 and 5 are template agnostic.

---

## 3. Document boundary detection

A binder is many invoices in one file. **Split it before anything else is meaningful.**

1. Run supplier-specific invoice-number patterns over each page.
2. A page carrying exactly one identifier belongs to that document.
3. A page carrying **no** identifier inherits the previous page's document. That is correct for terms pages, payment advice pages and blank pages.
4. **A page can carry two documents.** Where one invoice's totals block is followed on the same page by another's letterhead, the page belongs to both: record it in both `page_range`s and say so in `notes`. A page range is inclusive and page ranges may overlap by one page for this reason only.
5. **Verify the split against page footers.** Xero and similar print `1 of 3`. If your split gives four pages where the footer says three, your split is wrong, not the footer. **NEW v7:** where a footer prints `Page m of n`, assert `n` equals the length of that document's page range and record the footer text in `notes`. A mismatch is P9.
6. **Two non-adjacent page runs resolving to the same identifier is a duplicate copy, not a split error.** Section 11.
7. **Report every identifier you find**, including any you cannot classify. Ledger matching is a later session's job, so an unrecognised identifier is reported, never dropped.
8. Assert before emitting: the union of all `page_range`s covers every page of the source, and no page is unaccounted for. **NEW v7:** emit the evidence, `manifest.coverage.pages_covered`, as the sorted list of page numbers carrying at least one line record. A count on its own is not the assertion.
9. **Every page inside a document's own range carries at least one line record, even when the page is blank** (v6). A blank page gets one `BLANK` record; a page you could read but chose not to transcribe is a full-capture breach. That is P3, and P3 cannot be repaired downstream: there is nothing to restate from. This is the cheapest pathology in the list to prevent and one of the few that cannot be fixed without re-extraction.

Known identifier patterns from prior batches:

| Supplier | Pattern |
|---|---|
| Savco Vegetation Services | `\b(SV\d{6})\b` |
| Xero-templated (Heritage Tree, Weis, Total Environmental, F82/Flavell-Dau, Play Force, MPDT, Certified Mowing, Coast2Coast, T & H Levai) | `\b(INV-\d{3,5})\b`, credit notes `\b(CN-\d{5})\b` |
| Burly Holdings | `Tax Invoice #\s*(\d+)` |
| Link Resources Training | `\b(LR\d{4,6})\b` |
| Vinton Tree Services (RST Systems) | `Invoice No\.:\s*(\d{5})`, `Invoice number:\s*(\d{5})` |
| Greenway Turf Solutions | `\b(SI-\d{6,9})\b` |
| Q Power | `TAX INVOICE NO\.\s*(\d+)` |
| Harpley Services | `\b(000\d{5})\b`, **leading zeros are part of the number** |
| SECUREcorp | `\b(QLDPSI\d{7})\b` |
| Kachel Cleaning | `TAX INVOICE\s+No\.(\d{4})`, **a bare four-digit number, no prefix** |

**Trap:** the Total Environmental Concepts layout prints `Invoice Number` and the number on different physical lines with other text between, so `Invoice Number\s+(\d{4})` fails. Detect that supplier by name and read the number positionally. See 5.2, which generalises this.

**Trap:** `doc_ref` is the supplier's invoice number **exactly as printed, leading zeros included**. Downstream matching is on that string, and the ledger truncates long numbers (TCS 17118059 posts as `171180`), so a stripped or normalised `doc_ref` silently fails to match. **NEW v7, stated concretely:** a file named `C00291494_4.pdf` carries the TechOne document image id `C00291494` and the EzeScan sequence suffix `_4`. Neither is a `doc_ref`. Record the file name and the C-number in `notes` and take `doc_ref` off the printed face.

---

## 4. Column anchoring: how to decide a line is PRICED

**This is the rule that failed on `mix1`, and then failed again on `mix22` and `Binder11111` for a different reason: v5 stated it and did not make it checkable.** v6 made it checkable and left the test itself imprecise. Do not classify priced lines by whether the row starts with a number, and do not classify them by whether the row ends with a number. Both heuristics fail on real Parks invoices.

### 4.0 NEW v7. The classification ladder, run in this order on every row

One order, top to bottom, first match wins. The ladder exists because a totals row carries money in the amount band too, and a band test run before a label test will type it PRICED.

1. The row is empty or whitespace only, and inside a document's range: `BLANK`.
2. The row is a copy of a page already captured in this document: `DUPLICATE_COPY`, arithmetic fields null (11.4).
3. The row matches a **totals label** from the 5.0 precedence table (`Subtotal`, `Sub Total`, `GST`, `TOTAL GST 10%`, `GST TOTAL`, `PLUS 10% GST`, `Total`, `TOTAL AUD`, `Total price including GST`, `Total (inc-GST)`, `Total Payable`, `Amount Due`, `Balance Due`, `Paid to Date`, `Less Credit to Invoice(s)`, `REMAINING CREDIT`, `Credit Amount`): `TOTALS`. Longest label first, always (5.1).
4. The row is inside a payment, remittance or bank block (`Bank Details`, `BSB`, `Account:`, `Name:`, `How to pay`, `Payment Advice`, `Please pay by`): `PAYMENT_ADVICE`. **A figure in this block is never an amount and never a PK** (4.3).
5. The row is the item table's header or another table's header: `TABLE_HEADER` (4.1). **It is not TOTALS.**
6. The row carries a numeric money token whose character span **overlaps the amount band** (4.2): `PRICED`. This test is sufficient on its own.
7. The row is terms, conditions or fine print: `TERMS`. The page footer or letterhead: `FOOTER`. Image-borne text: `IMAGE_TEXT`. An annotation or stamp: `ANNOTATION`. OCR text duplicating a text-layer row: `OCR_DUPLICATE`.
8. **NEW v7.1.** The row is a schedule row scoped to a different document by a cost account, PK, invoice number or period printed on the row itself: `ATTACHMENT`, amount kept, excluded from the tie (9, rule 16d). Rung 6 runs first, so a row that belongs to THIS document is PRICED before this rung is reached.
9. Anything else: `NARRATIVE`.

**One physical row can carry two blocks.** On interleaved layouts the bank block prints to the left of the totals block, so `BSB: 064 194 ... GST (10%) 4,655.00` is one row carrying a payment label and a totals label. The money decides: type it `TOTALS`, and note the interleave. A row carrying a payment label and no money is `PAYMENT_ADVICE`.

Rungs 3 and 4 run **before** rung 6 deliberately, because a totals row carries money in the amount band too. Rung 6 runs **before** rung 8 just as deliberately: a row belongs to THIS document unless something printed on the row says otherwise, so the band decides before the scoping test is reached. And rung 9 is last because NARRATIVE is the residue of the ladder, not a judgement about whether a row looks like a line item.

### 4.1 Find the header row first, and RECORD ITS BANDS

Every priced table has a header row printing some subset of: `Description`, `Item`, `Details`, `Quantity`, `Qty`, `HRS`, `Unit Price`, `Rate`, `Unit`, `GST`, `TAX CODE`, `Amount`, `Amount AUD`, `EX AMOUNT`, `Total`, `Total Price`, `Ex GST`, `Price`, `Price (Ex. GST)`.

- Record its page and row, its verbatim text, and each column's band.
- **NEW v7: a band is a SPAN, `[start, end]`, not a single offset.** Both are 0-based inclusive character offsets into your own `line_text` for that row. Initialise each band from its label's own span, then **widen the amount band to cover the money tokens you actually observe beneath it**, and emit the widened span. Right-aligned money columns are ragged: on the Levai layout the label `AMOUNT` occupies 111 to 116 while its values occupy 111 to 119 and 117 to 120. A single offset with "a few characters of drift" rejects the short values, which is the same class of failure as requiring a quantity.
- **NEW v7: calibrate, and record the calibration.** Name the page and row of one real priced row whose money token overlaps the amount band, in `table_headers[].bands_calibrated_on`. A document with PRICED lines and no calibration record is **P11**, exactly as an empty `bands` is. Both v5 runs fell back to an unstated guess; a band nobody tested against a row is still a guess.
- **`bands` is mandatory, not decorative** (v6). A document with one or more PRICED lines and an empty or absent `bands` object is **P11** and the corpus is RED.
- Type the header row `TABLE_HEADER`. **It is not TOTALS.** On `mix1` the row `Description Quantity Unit Price GST Amount AUD` was typed TOTALS, which destroyed the only anchor the document had.
- **The first header-shaped row on the page is not always the item table's header** (v6). Savco prints `INVOICE NO. | DATE | TOTAL DUE | DUE DATE | TERMS | ENCLOSED` as a header-shaped row twenty rows above the real one, `DESCRIPTION | QTY | RATE | GST | AMOUNT`. The item table's header is the one immediately above the priced rows and above the totals block. Record both, set `is_item_table` on the second.
- More than one table means more than one header: record each and scope its bands to the rows beneath it.
- If no header row prints at all (Kachel), say so in `notes`, set the amount band from the totals block's own money column, which is the same band, calibrate it against a priced row as above, and fall back to 4.3.

### 4.2 Classify body rows by column occupancy

For each row beneath a header that reached rung 6 of the ladder, test the money tokens on the row against the bands.

- **NEW v7, the test itself: a row is PRICED if a money token's character span overlaps the amount band's span by at least one character.** Overlap, not left-edge proximity. It is correct for left-aligned columns, right-aligned columns, ragged widths, `$` prefixes inside the band (Burly) and an amount band that is not rightmost (Bushcare, where `GST` prints to its right).
- **A row with a money token overlapping the amount band is PRICED. That test is SUFFICIENT on its own.** Whatever the row begins with, whatever else it does or does not carry. `Darlington Parklands 1.00 63.46 10% 63.46` is PRICED. It begins with a word and contains a percentage. Neither disqualifies it.
- **You may not add any of these conditions to the test** (v6, the amendment that matters most):
  1. **Do not require a quantity.** Savco prints `CREW 3: 3 MEN WITH TRUCK AND CHIPPER 26-05-2026    3    308.88    GST    926.64`. The quantity is `3`, an integer with no decimal point, and on `mix22` every Savco row with an integer quantity was dropped while every row with `1.25` or `1.75` was kept. Eleven Savco invoices captured nothing at all for that reason. Vinton's `DESCRIPTION | EX AMOUNT | TAX CODE` layout prints **no quantity column whatsoever**, and both its zero-capture documents on `Binder11111` were single-row invoices of $6,800.00 and $5,150.00.
  2. **Do not require two decimal places outside the amount band.** Play Force prints `1.00  MISC1  Weekly Inspection/Maintenance on going  1355  1355.00`: the unit price is `1355`, bare. Four invoices of $1,355.00 each captured nothing on `mix22` for that reason alone.
  3. **Do not require a unit price at all.** Kachel prints description and amount with nothing between them; Higgins, Glascott, Levai print `DESCRIPTION OF SUPPLY | AMOUNT` or `DESCRIPTION | AMOUNT`, a two-band table.
  4. **NEW v7. Do not require the amount to sit on the row where its description begins.** Levai prints a five-row description block (name, contract, PK, blank, quote and site reference) and the amount on the **last** row of the block. The rows above are NARRATIVE with `"note": "wrapped description"`; the row carrying the money is PRICED, and the description it belongs to is the block, which the register reassembles. Never move an amount onto another row, and never merge rows to make one look tidier.
- A row with numerics only in the quantity or unit-price bands and nothing in the amount band is PRICED **if** the amount is derivable as printed elsewhere on the row; otherwise it is PRICED with a null amount and a `note`, and the document goes to the retry ladder.
- A row with no money token overlapping any band is NARRATIVE.
- A row sitting entirely left of the first numeric band and continuing a description above it is NARRATIVE with `"note": "wrapped description"`.
- **Zero-amount priced rows are real.** Xero prints `Contract # PAR329B2021  1.00  0.00  0.00` and site-address rows at `1.00 ... 0.00`. They carry the full column structure, so they are PRICED at 0.00. They cannot disturb the tie and the register needs them (rule 16).
- **A tax CODE in the tax band is not an amount and not a disqualifier** (v6). Savco prints the literal `GST` between the rate and the amount; ETSol prints `GST` in a column headed `TAX`; Vinton prints `GST` in a column headed `TAX CODE`; Xero prints `10%`. None of these is money, and none of them stops the row being PRICED. Record it in `gst_rate_printed`, never in `gst`.

### 4.3 When there is no header row

Use the trailing-amount test, with these exclusions applied **before** testing:

- **GST rate tokens.** `10%`, `10.0%`, `GST 10%` are rates, never amounts. This is the most common false negative and the reason the `mix1` Play Force documents failed.
- **Date tokens.** `dd.mm.yyyy`, `dd.mm.yy`, `dd/mm/yyyy`, `dd Mon yyyy`.
- **Reference tokens.** Bare integers of six digits or more with no decimal point and no currency symbol, where the surrounding text names a reference, order, contract, quote or account. A bank account number in the payment block is one of these: Play Force prints `Account: 10367833` next to `Account: PK000477`, and a corpus supplied to this project took the bank account as a PK on two documents. **NEW v7:** so are `YOUR REF 715913` and `Quote No. 657712` in a header or description block, and a spaced account number such as `Account: 101 540 21`.
- **Quantities.** A lone `1.00` at the start of a row is a quantity, not an amount.
- **`SUBTOTAL:` contains `TOTAL:`.** Match totals keywords before priced ones and use a negative lookbehind, `(?<!SUB)TOTAL:`. **`GST TOTAL` contains `TOTAL` too.** See 5.1.

Accept variable decimals: `$3,660`, `65.1`, `1,234.00` are all amounts.

### 4.4 The invariant that makes this checkable

**`line_type == "PRICED"` if and only if `line_ex_gst` is a number (or `stated_amt` on a GST-inclusive template).** These are not two independent assertions; one determines the other. Assert it both ways before emitting a document. A PRICED line with a null amount, and an amount-bearing line typed NARRATIVE, are each emit-blocking defects.

**NEW v7.1, the one exception, stated so it cannot be read as a loophole.** `ATTACHMENT` also carries an amount (9, rule 16d), so the "only if" direction runs over PRICED **and** ATTACHMENT, and nothing else. Every other type carrying an amount is P2. This does not weaken the test the invariant exists for: a dropped line item is typed NARRATIVE, and NARRATIVE with an amount stays fatal.

### 4.5 The residue test, which you run on every document

Before you emit a document, list every row that is (a) typed NARRATIVE, (b) positioned between the item table's header row and the first row of the totals block, and (c) carrying a money token overlapping the amount band.

**That list must be empty, and you emit the list.** Write it to `residue_rows`: `[]` when clean, page and row and amount for each entry when not. If it is not empty, you have not finished classifying: go back to 4.0. A non-empty residue on an emitted document is **P12**, and so is an absent `residue_rows` key, because a test whose result you did not write down is a test you cannot show you ran.

**NEW v7, the window on layouts with no header and on multi-table documents.** Where no item-table header prints (Kachel), the window runs from the first body row of the page to the first row of the totals block. Where a document has more than one priced table, run the test once per table, scoped to that table's own header and bands, and concatenate the results.

This is the single check that would have caught all 34 dropped rows in both v5 runs, and you can run it in either runtime by reading your own line records.

### 4.6 NEW v7. Reference algorithm, runtime A

Twenty lines, deterministic, and it is the fast path once written. Runtime B follows the same order by hand.

```python
hdr   = find_item_table_header(page_rows)            # 4.1, second header on Savco
bands = {lab: [s, e] for lab, s, e in label_spans(hdr)}
amt   = bands[amount_label]                          # Annexe A names it per template

# CALIBRATE FIRST. The label span is not the value span: on the conformance invoice AMOUNT ends at 116 and its
# values end at 118, 119 and 120. Widening after the loop classifies every row against the un-widened label and
# defeats the whole of 4.1, which is what v7 was written to fix.
amt, calibrated_row = widen(amt, money_spans_under(hdr, amt))    # 4.1
assert calibrated_row is not None                    # P11

for r in body_rows_under(hdr):                       # 4.0 ladder, all nine rungs, in order
    if is_blank(r):            t = "BLANK"                       # 1
    elif is_repeat_of_captured_page(r):                          # 2
                               t = "DUPLICATE_COPY"              #   arithmetic null, 11.4
    elif is_totals_label(r):   t = "TOTALS"          # 3, longest label first, 5.1
    elif in_payment_block(r):  t = "PAYMENT_ADVICE"  # 4
    elif is_header_shaped(r):  t = "TABLE_HEADER"    # 5
    elif any(overlap(tok.span, amt) for tok in money_tokens(r)):
                               t = "PRICED"          # 6, overlap decides
    elif is_fine_print(r):     t = "TERMS"           # 7, with FOOTER, IMAGE_TEXT, ANNOTATION, OCR_DUPLICATE
    elif scoped_to_another_document(r):              # 8, a cost account, PK, invoice no or period
                               t = "ATTACHMENT"      #   ON THE ROW; amount kept, out of the tie, rule 16d
    else:                      t = "NARRATIVE"       # 9, the residue of the ladder
    emit(r, t, band_hits=[b for b in bands if hit(r, bands[b])])

assert residue(body_rows, amt) == []                 # 4.5, P12
assert abs(sum(priced) - printed_subtotal) <= 0.01   # 6.0, else run the ladder
```

`money_tokens` excludes the 4.3 token classes before it returns. `overlap(a, b)` is `a[0] <= b[1] and b[0] <= a[1]`.

**Rungs 2 and 8 are in this listing because without them it cannot emit `DUPLICATE_COPY` or `ATTACHMENT`,** and
those are the two types v7.1 and v7.3 turn on. An extractor following an algorithm that omits them produces
neither, so the 11.4 standing rule, which reads `duplicate_of` off rows typed at rung 2, would be unreachable
through this document's own fast path.

---

## 5. Header amounts

One figure per labelled line. Never take a header amount from an unlabelled position.

### 5.0 NEW v7. Label precedence, as a table

Read down each column and take the **first label that prints**. Never take a figure from a lower row of the column when a higher one printed.

| Field | Take from, in this order | Never from |
|---|---|---|
| `printed_total_incl_gst` | `Total` / `TOTAL AUD` / `Total price including GST` / `Total (inc-GST)` / `Total Payable`, then `Amount Due` / `Total Outstanding`, then `Balance Due` | `Subtotal`, `GST TOTAL`, `TOTAL GST 10%`, `Paid to Date`, `Credit Amount`, `REMAINING CREDIT`, `Less Credit to Invoice(s)`, `ENCLOSED` |
| `printed_gst` | `GST` / `GST (10%)` / `TOTAL GST 10%` / `PLUS 10% GST` / `GST TOTAL` | `Subtotal`, any `Total` |
| `printed_subtotal_ex_gst` | `Subtotal` / `Sub Total`, else derived as total less GST with `"subtotal_basis": "derived from total less GST"` | any `Total` where a `Subtotal` prints |

- **`Balance Due` is a fallback, not a synonym for the total** (v7, amending v6, which listed it as an equal source). Where both `Total` and `Balance Due` print, take `Total`. Where they differ, the invoice is part paid: take `Total`, record `Balance Due` and `Paid to Date` in `notes`, and raise F1. A part-paid invoice whose `Balance Due` was taken as the total fails 5.4 for a reason that has nothing to do with the invoice.
- **NEW v7.2. GST is read, never silently derived.** v7 allowed the SUBTOTAL to be derived as total less GST. The reverse, deriving the GST as total less subtotal, is banned unless it is declared, because it makes 5.4 pass by construction: subtotal plus a derived GST equals the total whatever the total is. On `Binder1666` an extractor derived the GST on 29 documents and recorded totals of $6.00, $7.00 and $8.00 (fuel levy line amounts on Vinton, and a `Total GST 10%` figure on Heritage) against real totals from $1,586.75 to $3,771.61. Every one added up, and P10 saw nothing. So:
  1. Read the GST from its own label (5.0 precedence).
  2. Where the label prints with no value on its row, take the first value in its band in the next four rows (5.2).
  3. Where it prints nowhere, derive it and record `"gst_basis": "derived from printed total less printed subtotal"` with `"header_adds_up": "derived"`. P16 then polices the derivation, which is the only check left that can.
  4. A derived GST that is not a tenth of the subtotal within the P16 tolerance is not a derivation, it is a misread total.
- **`Paid to Date` is never an amount for any field.** It is a payment history figure. It prints in the totals block on the Xero and Levai layouts, immediately above `Balance Due`.
- If the only total prints as a bare `$` amount under `PLUS 10% GST` or `Sub Total:`, with no `Total` label anywhere on the document, take it and record `"total_basis": "bare amount under <label>"`. **NEW v7: that clause is scoped to documents with no `Total` label at all.** v6's wording read as a general permission to take a total off a `Sub Total:` row, which contradicts the never-from column above.
- **`invoice_date`** comes from the token labelled `DATE` or `INVOICE DATE`. Where a header prints `PLEASE PAY BY | AMOUNT | INVOICE DATE` on one row, the LAST date is the invoice date and the FIRST is the due date. Never a work-note or completion date. Where `DATE` and `DUE DATE` both print, `DUE DATE` is never `invoice_date`.
- **Totals can print on the last page only.** Search every page of the document before recording a null. That is a capture note, not an extraction loss.
- **A null header field is a defect,** not an omission. Restate it from the page, or explain in `notes` why the layout does not carry it and record `"(not printed)"`.
- **Credit notes are negative.** A credit note or adjustment note carries negative `line_ex_gst`, `printed_subtotal_ex_gst`, `printed_gst` and `printed_total_incl_gst`, and `"doc_kind": "CREDIT_NOTE"`. Never record a credit as a positive and never flip the sign to make a tie work. The printed figures stay positive in `line_text`, which is never edited. **NEW v7:** a `CREDIT_NOTE` carrying a positive `printed_total_incl_gst`, or a `TAX_INVOICE` carrying a negative one with no printed minus, is **P14**.

### 5.1 The label-substring trap, stated as a rule

`GST TOTAL` ends in `TOTAL`. On the Savco layout the totals block prints, in this order:

```
                          SUBTOTAL        4,522.50
                          GST TOTAL         452.25
                          TOTAL           4,974.75
                          BALANCE DUE
                                       A$4,974.75
```

On `mix22` the extractor took `printed_total_incl_gst` from the `GST TOTAL` row on **all thirteen** Savco documents, recording $452.25 as the total of a $4,974.75 invoice. Match the longest label first, or use a negative lookbehind on both: `(?<!SUB)(?<!GST )TOTAL`. **NEW v7.2: the trap also runs the other way.** Woodmans prints `GST Ex Total`, `GST` and `GST Inc Total`: two of those three are totals labels that BEGIN with `GST`, so a GST matcher keyed on the word takes a total, and a totals matcher that excludes anything containing `GST` takes nothing. Match the full label. The same care applies to `TOTAL GST 10%` (Xero), `Total (inc-GST)` (Vinton), `Total Payable` (Treescape), `Paid to Date` and `Balance Due` (Levai, Xero) and `REMAINING CREDIT` (5.3). Note also that Savco prints `BALANCE DUE` with its figure on the **next** row: a label whose own row carries no money takes the first money token below it in its own band (5.2).

### 5.2 The label-above-value rule, generalised

Xero and several other templates stack the label over its value and print an unrelated block to the right of both, so reading "the rest of the label's line" finds the letterhead:

```
                                    Invoice Number             MOSSMAN QLD 4873
              Logan City Council     INV-13892                 07 4098 8264
```

Read the label row, then take the **first matching value in the next four rows within the label's own band**. The gap can be two rows: on the Heritage credit-note layout `Credit Note Number` sits two rows above `CN-48535`. Record which row supplied each header figure in `header_sources` (section 9), so a wrong read is auditable rather than invisible.

### 5.3 The credit-advice trap

The Heritage credit-note layout closes with a credit advice printing `Credit Amount 0.00`. That is the credit **remaining after this note has been applied to an invoice**, not the value of the note. The note itself prints `Subtotal 408.33`, `TOTAL GST 10% 40.83`, `TOTAL AUD 449.16`, and the ledger posts $408.33 as a credit. Taking the advice figure yields a $0.00 credit note that ties nothing and matches nothing. The same shape appears as `Less Credit to Invoice(s)` and `REMAINING CREDIT`: both are applications, not values.

### 5.4 The header block must add up, and it is a gate

After reading the three header figures, test:

```
round(abs(printed_subtotal_ex_gst + printed_gst - printed_total_incl_gst), 2) <= 0.02
```

If it fails, **you have misread one of the three**: re-read the totals block before going any further, because every downstream check is built on these. If it still fails after a re-read, the invoice itself is defective: keep the figures as printed, record it as F1 (section 14) with the three amounts, and say which row supplied each.

An unexplained failure of this test is **P10**. It costs one subtraction and it would have turned all thirteen Savco misreads RED at extraction time rather than at build time.

**NEW v7, two refinements.** The 2c allowance exists for per-line GST rounding (11.10), so a gap **above 1c** is recorded in `notes` with the reason even when it passes. And where `printed_subtotal_ex_gst` was **derived** as total less GST, the test is tautological: set `"header_adds_up": "derived"`, not `true`, so the build is not given a false assurance. `true` is reserved for three independently printed figures.

### 5.5 NEW v7. What to do when the header block fails and you cannot resolve it

Do not guess, do not adjust, and do not hold the document. Emit it with the figures as printed, `"header_adds_up": false`, F1 on the findings array with the three amounts and their source rows, and the document counted in the AMBER column of the gate table. A defective invoice is a finding for the register, not a reason to fail the batch, provided you say which row supplied each figure.

### 5.6 NEW v7. The GST-free and mixed-supply case

A printed GST of $0.00 against a non-zero total is a GST-free supply (11.11), not a misread, and 5.4 still passes because subtotal equals total. Record `"gst_basis": "GST-free as printed"`. Where a document prints GST on some lines and not others, record the printed per-line GST as printed, never recompute, and raise F1 only if the header block itself fails.

---

## 6. The arithmetic gate and the retry ladder

### 6.0 NEW v7. Tolerance, restated to match the destination

The register's rule 17 checks run at 1c. A corpus that ties at 2c can pass extraction and fail the build, which costs a whole build session. So:

```
captured = sum(line_ex_gst for PRICED lines)
gap      = round(abs(captured - printed_subtotal_ex_gst), 2)
tie      = gap <= 0.01
```

- `gap <= 0.01`: `"self_tie": "TIE"`, `"tie_tolerance": "1c"`.
- `0.01 < gap <= 0.02`: `"self_tie": "TIE"`, `"tie_tolerance": "2c"`, **finding F7**, and the corpus gate is at best **AMBER**. State in `notes` which rounding convention explains the cent, per 11.10.
- `gap > 0.02`: run the ladder below.

Use `Decimal` with `ROUND_HALF_UP`, which is what the destination workbook does. Binary floating point rounding half to even is how a 1c difference becomes an argument.

For every document, in pass 2, if `gap > 0.02`, **you may not write `"self_tie": "OUT"` until you have run all four rungs and recorded the result of each in `retry_log`.**

**Rung 1, missed priced rows. This rung is evidenced, not asserted.** Run the residue test of 4.5 and write the result into `retry_log` as a list of row numbers with their amounts:

```json
{"rung": 1, "found": "residue test: rows 33, 34, 36, 37 carry 926.64, 531.36, 1544.40, 912.60 in the amount band",
 "rows": [33, 34, 36, 37]}
```

`"rung": 1, "found": "Candidate amount-band rows rechecked."` is not a result. It is a sentence about a result, and on `mix22` it was recorded on a document that had four such rows sitting in its own output. **A `retry_log` rung 1 entry with no `rows` key, on a document at OUT, is P12.** If the list is empty, say so explicitly: `"rows": []`.

**Rung 2, GST-inclusive template.** Test whether the captured lines instead tie the printed **total including GST**. If they do, set `"tie_basis": "incl_gst"` and `"line_amount_basis": "incl_gst"`, record it, and the document ties. Harpley template B (the `Your Order No:` header), the Coast2Coast `INCLUDES GST 10%` layout and Elemental are the standing examples, and on those three Annexe A tells you to try this rung first (2.1).

**Rung 3, rate-versus-amount confusion.** Check whether any captured amount is actually a GST rate, a quantity, or a unit price read into `line_ex_gst`. Recompute from the correct band.

**Rung 4, split or continued table.** Check whether the table continues on a following page, whether a second table sits beneath a second header, and whether its rows were attributed to the wrong document. Check the page range against section 3.

**NEW v7: every rung carries a structured result, not only rung 1.** Rung 2 records the incl-GST gap it computed; rung 3 names the rows it re-read and the band it took them from; rung 4 names the pages it checked. A rung with no numeric or row evidence is not a rung that ran.

Only if all four fail: `"self_tie": "OUT"`, with `retry_log` recording what each rung found and `notes` stating in one sentence what the analyst should look at.

**A document at OUT with zero PRICED lines is never a tie failure.** It is P1, it is a parse failure, and rung 1 is where it gets fixed.

---

## 7. Emit protocol and budget

A 317-page binder will exhaust your budget before it exhausts the work. Plan for that from the first document rather than discovering it at page 83.

1. **Emit per document, not per binder.** Complete pass 1 and pass 2 on one document, emit its record, then move on. Never hold 112 documents open and write at the end.
2. **Chunk the output so the pieces concatenate.** If the corpus will not fit one message, emit it as `part 1 of n` and so on, each a fenced block, each containing whole document records, the manifest last. Say plainly which documents are in which part.
3. **Keep a live counter.** `coverage.documents_complete` and `documents_total` are updated as you go, not estimated at the end.
4. **Stop at a document boundary.** If you are running short, stop cleanly, emit what you have with `"gate": "AMBER"`, and give `resume_point` as the exact first uncaptured page and document identifier. **Never emit a partial run as though it were whole.** An honest AMBER at document 60 of 112 is buildable; a silent stop at page 83 is not.
5. **No interim status reports.** One report at the end, per section 15.
6. **NEW v7, the budget arithmetic, so you can plan rather than discover.** Cost per document is dominated by line records, not by pages: a Play Force document is 220 fixed template rows and a Levai document is about 40. Count the rows on the first document of each template, multiply by the document count, and if the binder will not fit, say so in the first message and run it as a phase split (project rule 19.3) rather than starting a run you cannot finish. Boilerplate rows are still captured in full; they are simply typed `TERMS` or `FOOTER` on the ladder without further analysis, which is where the time is saved.

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

**NEW v7.** EzeScan and similar Council scanning servers emit an AcroForm wrapper with a clean text layer. Presence of a form does not imply an image-only page and does not trigger OCR on its own. In runtime A, read annotations with `pypdf` and type them `ANNOTATION` where they carry a reference, date or approval.

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
    "prompt_version": "v7.6",                       // MANDATORY: the gate scopes its checks on this (13.2)
    "page_text_independent": true,                  // MANDATORY: see 10.1
    "page_text_basis": "<where page_text came from>",
    "gate": "GREEN | AMBER | RED",
    "pathologies": [{"code": "P1", "doc_ref": "...", "page": 0, "detail": "..."}],
    "coverage": {"documents_complete": 0, "documents_total": 0,
                 "pages_represented": 0, "pages_total": 0,
                 "pages_covered": []},
    "corpus_checks": {"page_coverage_complete": true,
                      "doc_refs_unique": true,
                      "stems_unique": true,
                      "line_types_in_closed_list": true},
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
  "template": "<Annexe A key, or NEW:<name>>",
  "supplier": "<printed, verbatim>",
  "supplier_abn": "<printed, verbatim including its printed grouping>",
  "abn_source": "text_layer | ocr | footer | absent",
  "invoice_no": "<printed>", "invoice_date": "<printed, verbatim format>",
  "printed_subtotal_ex_gst": 0.00, "gst_basis": "<read off a GST label | derived as total less subtotal>",   // 5.0 step 3, 5.6; P17 and the gate read it
  "subtotal_basis": "printed | derived from total less GST",
  "printed_gst": 0.00, "printed_total_incl_gst": 0.00,
  "header_sources": {"printed_subtotal_ex_gst": {"page": 1, "row": 32},
                     "printed_gst": {"page": 1, "row": 34},
                     "printed_total_incl_gst": {"page": 1, "row": 35}},
  "header_adds_up": true,
  "captured_ex_gst": 0.00,
  "line_amount_basis": "ex_gst | incl_gst",
  "tie_basis": "ex_gst | incl_gst",
  "self_tie": "TIE | OUT",
  "tie_tolerance": "1c | 2c",
  "residue_rows": [],
  "retry_log": [{"rung": 1, "found": "...", "rows": []}],
  "table_headers": [{"page": 1, "row": 23, "text": "<verbatim>",
                     "bands": {"description": [1, 11], "amount": [111, 120]},
                     "bands_calibrated_on": {"page": 1, "row": 29},
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

**v6 fields:** `header_sources`, `header_adds_up`, `duplicate_copy_pages`, `bands` and `is_item_table`, `rows` inside a rung 1 `retry_log` entry.
**NEW v7 fields:** `template` (2.1), `tie_tolerance` (6.0), `residue_rows` (4.5), `bands_calibrated_on` (4.1), `manifest.coverage.pages_covered` and `manifest.corpus_checks` (9.1). Bands are now spans, `[start, end]`.

`printed_account_codes` captures an account or cost code **printed on the face**, verbatim. It replaces v4's `nat_acct_should`, which asked the extractor for a coding judgement. Coding is the register's ruling, made against the chart of accounts on sighted evidence, and an extractor's guess arriving in the corpus is a matching aid at best and a contaminant at worst.

### Line record, one per printed layout row

```json
{
  "source": "TEXT | OCR | ANNOT", "page": 1, "line_no": 1,
  "line_text": "<verbatim, leading whitespace preserved>",
  "line_type": "PRICED | ATTACHMENT | NARRATIVE | TABLE_HEADER | TOTALS | FOOTER | TERMS | BLANK | PAYMENT_ADVICE | OCR_DUPLICATE | IMAGE_TEXT | ANNOTATION | DUPLICATE_COPY",
  "ocr_only": false, "ocr_status": "run | not_required | not_available | outstanding", "ocr_reason": null,
  "qty": null, "unit": null, "unit_price_ex_gst": null,
  "line_ex_gst": null, "gst": null, "gst_rate_printed": null, "stated_amt": null,
  "band_hits": [], "work_order": null, "note": null
}
```

**`line_type` is a CLOSED list.** Those thirteen values and nothing else. `Binder11111` emitted 245 rows typed `DUPLICATE`, which is not one of them, so every downstream screen for `DUPLICATE_COPY` missed them. A value outside the list is **P13**.

**NEW v7.1. `ATTACHMENT`, the schedule row (register rule 16d).** A schedule attached to an invoice is not always cut to that invoice. Glascott prints one site schedule across a set of invoices, every row carrying its own cost account, so on invoice 012192 the single `PK000382` row is the line item and the twenty-five `PK000378` rows belong to other invoices in the same set. Those rows print an amount and must not enter the tie. Type them `ATTACHMENT`, keep the printed amount in `line_ex_gst`, and they are excluded from the arithmetic gate and from register rule 17 check 1 by rule 16d.

`ATTACHMENT` is not an escape hatch for a row you could not classify. It is for a row that is **demonstrably scoped to a different document**, by a cost account, PK, invoice number or period printed on the row itself. State the basis in `notes`. A row you merely could not tie is a residue-test failure (4.5), not an attachment.

`band_hits` names which column bands carried a money token on this row, by band key. It is the evidence for the classification and makes a wrong call auditable after the fact. `gst_rate_printed` carries a printed rate or tax code (`10%`, `GST`, `FRE`); `gst` carries a printed GST **amount** and nothing else.

### 9.1 NEW v7. Row and offset conventions, stated once

- `line_no` is **1-based within its page**, counting every layout row including blanks. Every `row` reference in `table_headers`, `header_sources`, `residue_rows` and `retry_log.rows` is a `line_no` and carries its `page` alongside. An unqualified row number in a multi-page document is ambiguous and therefore useless.
- Band offsets are **0-based inclusive character positions in the emitted `line_text`** (section 1).
- `manifest.corpus_checks` carries the four corpus-level assertions as booleans. They are cheap, a script re-runs them in a second, and a `false` shipped honestly is worth more than a `true` nobody computed.

---

## 10. Verbatim fidelity

`line_text` is the layout row exactly as printed, including leading whitespace, which carries the column positions section 4 depends on. Never trim, never normalise, never collapse runs of spaces. `rstrip()` only, never `strip()`.

**Runtime A.** Report the multiset difference **per page**, both directions, and list up to twenty actual differing tokens with page numbers in `manifest.text_layer_diffs`. A bare count is unactionable: `45` tells the analyst nothing. A difference caused by a ligature, a soft hyphen or an encoding artefact is recorded and dismissed with a reason. Any difference not so dismissed is a P3-class concern and must be named in the report.

**Runtime B.** Re-read a stated sample and check five-word shingles against your captured text: every document where you captured fewer than 40 lines, and at least one document per supplier otherwise. Record `shingle_checks_run` and `shingle_failures`, and state the sample rule you applied. Do not report `text_layer_diffs` you could not compute; leave the array empty.

`shingle_checks_run: 0` on a runtime B corpus of 40 documents is not a pass, it is an omission, and both v5 runs on this project reported exactly that. If you did not run the check, the report says so in those words rather than reporting a zero that reads like a clean result.

**NEW v7.** A unit symbol is part of the text: `190m³` is captured as printed, not as `190m3`, and where your reader cannot represent a character, record what you emitted and note the substitution. A silent character substitution inside `line_text` breaks the shingle check on a later run for no reason anyone can see.

---

### 10.1 NEW v7.4. Declare where the page text came from, because it decides whether this section means anything

The shingle check is the only test in this standard that reads a WORD rather than an amount, and it needs a
haystack the capture did not write. Where page text is rebuilt from the corpus's own `line_text` rows, the check
still runs and **cannot fail**, because the haystack has become the captured text. A corpus can then tie to the
cent on every invoice and carry a description the page never printed.

So the manifest carries two fields and both are mandatory:

- **`page_text_independent`**, a boolean. True only where `page_text` is a parse of the source PDF. False where
  it was rebuilt from the corpus's own rows, or where no page text is retained at all.
- **`page_text_basis`**, one sentence saying where it came from. Prose only; nothing reads it to decide.

A boolean, not a phrase, because a gate that sniffed the prose for "rebuilt" read a basis line saying "**not**
rebuilt from the corpus rows" as a rebuild.

**The description layer never changes the gate word.** It is reported beside it as a qualifier, VERIFIED,
UNVERIFIED or UNSTATED (13.0), so a corpus that ties to the cent with an unread description layer is not
confused with one that stopped mid-binder. The limitation is on the record rather than inside a helper script,
and it is what an unverified corpus is held on when a build session decides what to trust.

---

## 11. Standing rules

1. **Verbatim only.** A summary row in place of line capture is a critical failure.
2. **Full page representation.** Every page appears; every text-layer row appears. OCR content is typed `OCR_DUPLICATE` on text-layer pages and `IMAGE_TEXT` for image-borne content such as letterheads.
3. **The ABN is the SUPPLIER's,** from the letterhead or footer. LCC's own ABN `21 627 796 435` prints in the bill-to block. Capture the printed grouping verbatim, even where mis-grouped. An ABN present only as pixels is legible on the page and not a defect, but it is invisible to a text check, so flag `abn_source`.
4. **Duplicate copy pages.** Capture both copies. Type every line of the second `DUPLICATE_COPY` with arithmetic fields nulled, and list those pages in `duplicate_copy_pages`. Where the duplicate is a second copy of the same invoice inside one page range, that field is the whole record of it and `duplicate_of` stays null; where it is a separate document record, set `duplicate_of` to the first record's page range. Report it as a finding rather than housekeeping.
5. **GST-inclusive-only templates:** capture ex GST as printed total less printed GST, record the treatment, and do not invent ex-GST priced lines.
6. **Wrapped descriptions** get their own NARRATIVE record and are never truncated mid-phrase or rejoined. `pdftotext -layout` splitting a description across physical lines is correct behaviour. On Xero layouts a numeric-only row belongs to the description line immediately **above** it; description lines **below** the numbers are continuation text and stay NARRATIVE. **NEW v7:** where the amount prints on the last row of a multi-row description block (Levai, Higgins), the money row is the PRICED row and every row above it in the block is NARRATIVE with `"note": "wrapped description"`.
7. **Face codes and references** (PK numbers, CR and WO numbers, contract refs, POs, quote numbers) are captured verbatim in their fields AND left verbatim in `line_text`. Record a PK typo as printed; normalisation happens on join, not here. MPDT prints `PK#00047` and `PK#0000477` on consecutive invoices, both PK000477 on the ledger, and `PK00042` for PK000042 has been seen; capturing the printed form is what lets the register raise the finding.
8. **Correspondence in a binder is evidence.** Capture it, type it `FOOTER` or `NARRATIVE`, set `doc_kind` to `CORRESPONDENCE` where it stands alone, and never discard it.
9. **One invoice can span several sections and natural accounts.** Never record a section or account at document level; they are line-level facts.
10. **Rounding.** Some suppliers compute GST on the subtotal rather than per line, so per-line GST at 10% can differ by a cent or two. Record as printed, never adjust, and list the differences.
11. **A printed per-line GST of $0.00 alongside a non-zero amount is a GST-free supply, not an error.** Accredited training and some trust-structure suppliers are the standing cases. Do not compute a GST-inclusive figure or a check result into the corpus; those are live formulas in the destination workbook.

---

**NEW v7.6, a standing rule: every uniqueness and completeness check exempts `duplicate_of`.** A repeated copy
of an invoice inside a binder is the same document, so it shares its original's identifiers by construction. It
has no priced lines because its arithmetic is null (4.0 rung 2), and it shares the original's `evidence_stem`
because it is the same evidence. Four checks have now needed this exemption one at a time, P1 and P15 among
them, each discovered by a correct corpus being failed. State it once: a check that asks "is this unique" or
"did this parse" does not ask it of a row or a document carrying `duplicate_of`. P7 is the exception and is
meant to be, because it exists to find a duplicate that was NOT marked.

## 12. Evidence stem rule

`Business Name, What it was For, Date, Amount`, 40 characters maximum, no extension. Amount is the invoice incl-GST total, two decimals, no dollar sign, **negative for a credit note**. Degrade in this order and never trim the amount: full date `D-Mon-YYYY`, then `Mon-YYYY`, then a shorter purpose, then a shorter business name.

**Stems must be unique across the batch.** Two invoices from one supplier on one day for one amount will collide; break the tie by appending the last three digits of the invoice number to the purpose, then re-run the ladder. **NEW v7: uniqueness is asserted, not assumed.** Set `manifest.corpus_checks.stems_unique`; a collision left in the corpus is **P15**.

---

## 13. Gate semantics and pathologies

### 13.0 NEW v7. What GREEN, AMBER and RED mean

v6 used these three words on every page and defined none of them. The build session acts on the word, so it is defined here.

| Gate | Condition | What the build does |
|---|---|---|
| **GREEN** | Every document complete; no pathology; every document at TIE at 1c; every corpus check true | Builds |
| **AMBER** | No pathology, and one or more of: the run stopped at a document boundary with `resume_point` set; a document at OUT after all four rungs; a tie in the 1c to 2c band (F7); a header block that fails 5.4 and is recorded as F1; citation drift recorded as F8 (14); a mixed supply exempted from P16 (13.1) | Builds what is complete, HOLDs the named documents |
| **RED** | Any unresolved pathology **P1 to P17** | Does not build. The corpus is returned for re-extraction |

AMBER is a normal, useful outcome and is not a failure. RED is also a useful, honest output. **A GREEN corpus containing a P1 is a fabrication.**

**NEW v7.6. The description layer is a SEPARATE AXIS and never changes the word.** It is printed as a qualifier
beside the gate, `GREEN (description layer UNVERIFIED)`, and takes one of three values from 10.1: VERIFIED,
UNVERIFIED or UNSTATED. It is reported and not folded in because the two things a reader needs are independent:
whether the arithmetic and the structure hold, and whether any captured description has been read against a
page. Demoting on it was tried and withdrawn in the same day. It took GREEN off every corpus in the branch
repository at once, including the section 16.4 conformance fixture, which left the self-test with no passing
reference so an extractor could no longer tell conformance from a defect, and it gave a corpus that ties to the
cent the same word as one that stopped mid-binder. A GREEN that nothing can reach carries no more information
than a RED that fires on a non-failure.


### 13.1 Pathologies that force a gate

These are not tie failures. They are parse failures, and a corpus containing an unresolved one is RED.

| Code | Condition | Why it is fatal |
|---|---|---|
| **P1 (amended v7.2, exempted v7.3)** | A `TAX_INVOICE` or `CREDIT_NOTE` with zero PRICED lines, **whatever subtotal is recorded**, UNLESS it carries `duplicate_of` | The document was not parsed at all. `mix1` shipped 15, `mix22` 11, `Binder11111` 2. v7's non-zero-subtotal condition was itself a loophole: `Binder1666` document 6431345 recorded a subtotal of 0.00, a total of $39.99 (which is the first line item's price) and zero priced lines against a printed `GST Ex Total` of $268.00, and every gate slept. A tax invoice with no priced line is a parse failure by definition. A repeated copy carries `duplicate_of`, every row typed `DUPLICATE_COPY` with null arithmetic by 4.0 rung 2, so zero PRICED lines is correct for it. Without the exemption the amendment returns a sound corpus: on `Pages_from_Binder1` it fired on five documents and all five were duplicate copies. |
| **P2** | `line_type == "PRICED"` with null amount, or an amount-bearing row typed anything but PRICED or ATTACHMENT (v7.1) | Breaks the 4.4 invariant |
| **P3** | A page inside a completed document's range with no line records | Full-capture breach, and **not repairable downstream**: there is nothing to restate from. Pages beyond `resume_point` in an AMBER run are not P3. |
| **P4** | `supplier_abn` equals the LCC ABN `21 627 796 435` in any grouping | The bill-to ABN was read as the supplier's |
| **P5** | Null `printed_total_incl_gst` where a Total line demonstrably prints | Header-amount breach |
| **P6** | `ocr_pages_outstanding > 0` (runtime A only) | The corpus is not multi-source. Does not fire in runtime B. |
| **P7** | Two documents sharing a `doc_ref` with neither marked `duplicate_of` | Duplicate screening breach |
| **P8** | A number emitted as a string, or carrying `$` or a thousands separator | Every downstream check has to be repaired before it can run |
| **P9** | Page ranges that leave a gap, overlap by more than the one page 3.4 permits, or contradict a printed `Page m of n` footer | The split is wrong, and every amount attributed from it is suspect |
| **P10** | `printed_subtotal + printed_gst != printed_total` beyond 2c, with no finding explaining it | A header figure was read off the wrong labelled row. Caught all 13 Savco misreads on `mix22`. |
| **P11** | A document with PRICED lines whose item-table header carries no `bands`, **or no `bands_calibrated_on`** (v7) | Section 4 was not anchored, or the anchor was never tested against a real row, so every classification on the document is a guess |
| **P12** | `residue_rows` non-empty or absent, or a rung 1 `retry_log` entry on an OUT document carries no `rows` | The rows are sitting in your own output, unclassified or unexamined |
| **P13** | A `line_type` outside the closed list in section 9 | Every downstream screen for that type silently misses the rows |
| **P14 (NEW v7)** | `doc_kind == "CREDIT_NOTE"` with a positive `printed_total_incl_gst`, or a sign that contradicts the printed face | A credit posted as a debit ties nothing and reverses the register total |
| **P15 (NEW v7)** | Two documents sharing an `evidence_stem` | Evidence files collide on save and one overwrites the other |
| **P16 (NEW v7.2, mixed supply exempted v7.5)** | Where a GST amount is recorded and is not zero, `printed_gst` is not a tenth of `printed_subtotal_ex_gst` within **max(1% of the GST, 2c)**, or its sign opposes the subtotal's, **unless the priced lines print a GST amount each and those sum to the printed GST**, which is a mixed supply (5.6) and not a defect | P10 cannot see a swap or a derived GST, because addition survives both. This is the only check that reads the two figures against each other rather than against their sum. On `Binder1666` it flagged 30 of 100 documents and every one was a true positive: 27 Vinton, 2 Heritage, 1 Tennyson. The tolerance is relative because a supplier computing GST per line rather than on the subtotal lands cents off a tenth on a large invoice, and that is rule 11.10, not an error |
| **P17 (NEW v7.2)** | A header figure is not printed on the row its `header_sources` entry cites, or cites a row that carries no line record | `header_sources` was added in v6 so a wrong read would be auditable. Nothing audited it, so on `Binder1666` a GST of -$1,887.75 cited a row reading `Completed 22/06/2026`. The figure and the row are both in your own output, so this costs one string search. A derived figure (`gst_basis` or `subtotal_basis` saying so) is exempt from the value test |

Set `"gate": "RED"`, list every pathology in `manifest.pathologies` with the affected `doc_ref` and page, and say plainly in the report that the corpus must not be built from.

---


### 13.2 NEW v7. The gate is computed, not declared

**NEW v7.4. The gate applies the checks the corpus could have satisfied, and says which.** A RED verdict stops
carrying information the moment it fires on a field that did not exist when the corpus was extracted. So the
gate reads `manifest.prompt_version`, which is **mandatory** for this reason, and skips a check only where the
corpus predates the FIELD or CONVENTION that check reads. The scope is on the evidence, never on the version
alone: scoping by version would let a corpus declaring v6 escape P14, P15 and P16, none of which needs anything
v6 lacks, so an extraction could dodge three checks by understating itself.

| Evidence a check reads | From | Checks scoped to it |
|---|---|---|
| `bands_calibrated_on` | v7 | the P11 calibration limb only |
| `residue_rows` as a KEY | v7 | the P12 "absent" limb only; a non-empty residue is v6 |
| `bands` | v6 | P11 proper |
| `header_sources` citing a 9.1 `line_no` | v7 | P17. The field is v6 but every v6 corpus writes `"row": 0` as a placeholder, so the convention and not the field is what P17 needs |
| `doc_kind`, `evidence_stem`, `printed_gst` | v5 | P14, P15, P16 apply to **every** corpus |

P1's v7.2 amendment is not scoped either: a document that parsed nothing was a parse failure under v5 too,
whatever the prompt said at the time.



`pswp_corpus_gate.py` (session zip) reads a corpus and computes the gate from the corpus itself: every pathology above that is computable without the PDF, plus the 13.0 table. Where your declared gate and the computed gate differ, **the computed gate stands**, and the difference is itself the finding.

Run it before you write the report if your runtime can (runtime A, one command, `python3 pswp_corpus_gate.py corpus_<batch_id>.json`). In runtime B you cannot, so write the corpus as though it will be run, because it will be: the build session runs it on arrival and returns anything RED unbuilt.

What it cannot see, and what therefore stays yours: verbatim fidelity against the page, whether a band matches the printed column, and a money row typed NARRATIVE **outside** the residue window. Those three are why sections 4, 5 and 10 are written the way they are.

## 14. Findings to raise, not bury

The register turns these into numbered Open Items, so a finding you notice and do not record is work the analyst repeats. Record each on the document's `findings` array with its code, and repeat it in the report with the document reference and the dollar amount.

| Code | Finding |
|---|---|
| **F1** | **Tax invoice defects.** Missing GST amount or total on a document over $1,000, missing ABN, missing supplier identity, a header block that does not add up after a re-read (5.4), or a part-paid invoice where `Balance Due` differs from `Total` (5.0). Note separately where an ABN exists **only as pixels**. |
| **F2** | **Documents that do not support the line they appear to be filed against**, so far as that is visible from the document itself: wrong amount, wrong year, wrong party. |
| **F3** | **Fuel levy lines**, flagged for verification against the stepped and capped model. |
| **F4** | **Coding candidates**, where a PK or account code printed on the face looks wrong, and documents stating **no PK at all**. A PK not of the `PK000000` form is one of these. |
| **F5** | **Referenced but absent documents**: tip dockets, cost breakdowns, quotes, fixed-fee schedules, site photographs. A face reading `Quote No. 657712` with no quote in the binder is an F5. The evidence pack is not complete until they are requested. |
| **F6** | **Duplicate copies and blank pages.** |
| **F7 (NEW v7)** | **A tie that lands between 1c and 2c** (6.0), with the rounding convention that explains it. The corpus gate goes AMBER. |
| **F8 (NEW v7.2)** | **Citation drift on a header figure**: the value is printed on the document but not on the row it cites, or two header fields cite one row, or a cited row is typed anything other than `TOTALS`. The figure may well be right; the evidence trail is not. The corpus gate goes AMBER. On `Binder1666`, 68 documents carried at least one of these, most of them totals rows typed `PAYMENT_ADVICE` or `NARRATIVE` where the bank block interleaves with the totals block (4.0). |

**Do not raise an evidence finding on a document that failed to parse.** On `mix22`, seven of the nine findings raised were "pricing is stated as per quote, but the supporting quote is not in this binder" on documents that had captured $0.00 of a printed $8,920.00. The finding may well be true, but it is not the finding: the parse is. Fix the parse, then judge the evidence.

---

## 15. Capture report

Close with a short report, in this order:

1. **Gate: GREEN, AMBER or RED**, on its own line, first, with the 13.0 condition that set it.
2. Runtime, A or B, and the extraction tool and model.
3. Pathologies by code with document references, or the word "none".
4. Pages represented of pages total; documents complete of documents total; the four `corpus_checks` booleans.
5. Documents at TIE and OUT, every OUT named with its retry ladder outcome **and its rung 1 row list**; every 2c tie named with its gap.
6. Line records by type, and captured ex GST total.
7. Identifiers found, and any unclassified.
8. OCR: pages run, not required, not available, outstanding.
9. Fidelity: per-page diffs with dismissals reasoned (runtime A), or shingle checks run and failed with the sample rule stated (runtime B). If none were run, say so in words.
10. Findings by code, each with its reference and amount.
11. Resume point, if AMBER.
12. **NEW v7.** Any template not already in Annexe A, with its header signature, amount band and trap, ready to paste into the Annexe (rule 19.1).

**Lead with the gate.** The build session reads that line first and stops there if it is not GREEN.

**NEW v7.2: nothing later in the report may contradict that line.** The `Binder1666` report opened `Gate: AMBER` and closed with "the corpus is GREEN and can proceed to the build session", on a corpus that computes RED. Write the gate once, at the top, from 13.0, and close with the resume point or the new templates, never with a second opinion. A finding's text must also match its own figures: the same report recorded `F7, 19975: Self-tie gap 68.92 falls in the 1c to 2c band`, which is not a 1c to 2c gap by three orders of magnitude.

### 15.1 NEW v7. Report length

One page of figures and a findings list. The report is read by a build session that then reads the corpus, so prose explaining what an extractor did is cost without benefit. Every number in the report exists in the corpus; the report exists so nobody has to open the corpus to see the shape of the run.

---

## 16. Worked examples

### 16.1 The `mix1` failure

Play Force invoice INV-3880, page 1. The binder printed:

```
Description                    Quantity        Unit Price      GST        Amount AUD
Darlington Parklands           1.00            63.46           10%        63.46
                                                               Subtotal   63.46
                                                            TOTAL GST 10%  6.35
                                                              TOTAL AUD   69.81
```

**v3.1 produced:** the header row typed TOTALS, the body row typed NARRATIVE with a null amount, zero PRICED lines, `captured_ex_gst: 0.00`, `self_tie: OUT`. The document shipped.

**v5 onwards produce:** the header row typed `TABLE_HEADER` with bands recorded; the body row tested against the amount band, found to carry `63.46`, typed PRICED with `line_ex_gst: 63.46`, `band_hits: ["quantity","unit_price","amount"]`; captured $63.46; ties the printed subtotal; `self_tie: TIE`.

### 16.2 The `mix22` Savco failure

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

**v6 and v7 produce:** all six rows PRICED on the amount-band test alone, because 4.2 forbids requiring a quantity format; captured $4,522.50, which ties. The header block is tested under 5.4: $4,522.50 + $452.25 = $4,974.75, which is the `TOTAL` row, not the `GST TOTAL` row. If the rows had still been missed, the 4.5 residue test names them before the document can be emitted, and the rung 1 entry has to carry `"rows": [33, 34, 36, 37]`.

### 16.3 The `Binder11111` Vinton failure

Invoice 19900, page 23, printed:

```
DESCRIPTION                                                    EX AMOUNT      TAX CODE
CR #3897268, PK #000477, 17 Veivers Rd Woolffdene              $6,800.00      GST
Completed 05/08/2026
```

**v5 produced:** zero PRICED lines, `captured_ex_gst: 0.00` against a printed subtotal of $6,800.00, P1, and a rung 1 entry reading `"Amount-band rows rechecked."`

This layout has **no quantity column and no unit price column at all**. A classifier that wants three numeric bands before it will call a row PRICED can never parse it.

**v6 and v7 produce:** the row PRICED on the amount band alone, `band_hits: ["amount"]`, `gst_rate_printed: "GST"`, captured $6,800.00, which ties.

### 16.4 NEW v7. The conformance example, T & H Levai INV-38967

A single-page Xero-family invoice, `C00291494_4.pdf`, scanned by EzeScan. Every v7 amendment shows on this one page, so run it as your self-test before a big binder. Rows are `line_no` within page 1 of the `pdftotext -layout` text.

```
23| DESCRIPTION                                                                                                   AMOUNT
24| Rene Harreman
25| PAR/335L/2023
26| PK000441
27|
28| Quote No. 657712 - CR#3864941 - Darlington Parklands (Ref: 35382) - Top up Takura (190m³)
29| Supply and install 190 m3 of Takura softfall mulch to the playground area.                                    46,550.00
30|
32|Bank Details                                                                                    Subtotal      46,550.00
34|BSB: 064 194                                                                                   GST (10%)       4,655.00
35|Account: 101 540 21                                                                                 Total     51,205.00
36|Name: T AND H LEVAI PTY LTD                                                                  Paid to Date            0.00
37|                                                                                             Balance Due      51,205.00
```

What each amendment does here:

- **Bands as spans (4.1).** The label `AMOUNT` on row 23 occupies `[111, 116]`. The value on row 29 occupies `[111, 119]` and `Paid to Date`'s `0.00` occupies `[117, 120]`. A left-edge test with small drift accepts one and rejects the other; the amount band is recorded widened, `"amount": [111, 120]`, and calibrated on page 1 row 29.
- **The ladder (4.0).** Rows 32 to 37 all carry money overlapping that band. Every one is caught at rung 3 as `TOTALS` before the band test is reached, and rows 33 to 36 also match the payment block at rung 4. Run the band test first and this document reports five extra priced lines and a $153,615 capture.
- **Label precedence (5.0).** `Total` 51,205.00 is the total, not `Balance Due` and never `Paid to Date`, even though all three print the same layout shape and two print the same figure.
- **Header add-up (5.4).** 46,550.00 + 4,655.00 = 51,205.00, exact, `"header_adds_up": true`.
- **Amount on the last row of a description block (4.2.4, 11.6).** Rows 24 to 28 are NARRATIVE with `"note": "wrapped description"`; row 29 is the only PRICED row, `line_ex_gst: 46550.00`, `band_hits: ["amount"]`.
- **Reference exclusions (4.3).** `715913` on row 17 is `YOUR REF`, `657712` on row 28 is a quote number, `35382` is a site reference, `101 540 21` on row 35 is a bank account. None is an amount and none is a PK. The PK is `PK000441`, printed alone on row 26.
- **doc_ref (section 3).** `INV-38967` off the face. `C00291494` is the TechOne image id and goes in `notes`.
- **Findings.** F5 on the referenced but absent `Quote No. 657712`.
- **Residue (4.5).** `"residue_rows": []`, emitted, not assumed.
- **Tie (6.0).** captured 46,550.00 against printed subtotal 46,550.00, gap 0.00, `"tie_tolerance": "1c"`.
- **Stem (section 12).** `Levai, Takura mulch Darlington, May-2026, 51205.00` is 50 characters. Degrade in the section 12 order, not by inventing an abbreviation: the date is already `Mon-YYYY`, so shorten the purpose. `Levai, mulch Darlington, May-2026, 51205.00` is 43, still over; `Levai, mulch, May-2026, 51205.00` is 32 and ships. Never trim the amount, and never shorten the year to make a longer purpose fit.

---

## Annexe A. Template compatibility

Every layout this project has met, with the item table's header signature as printed, the band that carries the line amount, and the trap that catches an extractor. **A layout not in this table is not a reason to stop**: work it with sections 4 and 5, which are template agnostic, and add a row here in the same session (rule 19.1). Report new rows under section 15, item 12.

| Template | Item table header, as printed | Amount band | Trap |
|---|---|---|---|
| SAVCO | `DESCRIPTION \| QTY \| RATE \| GST \| AMOUNT` | rightmost `AMOUNT` | Quantities print as bare integers. `GST TOTAL` sits above `TOTAL` (5.1). `BALANCE DUE` prints its figure on the NEXT row. A header-shaped `INVOICE NO. \| DATE \| TOTAL DUE ...` row prints 20 rows higher. |
| HERITAGE | `Description \| Quantity \| Unit Price \| GST \| Amount AUD` | `Amount AUD` | The `Contract #` row prints `1.00 0.00 0.00` and is a real zero-amount priced row. `TOTAL GST 10%` prints ABOVE `Total` and was taken as the total on two `Binder1666` documents (5.1). Some vintages print `Subtotal` and `TOTAL GST 10%` on the last rows of page n and `Total` on page n+1. |
| HERITAGE_CN | same, credit note | `Amount AUD` | The credit advice prints `Credit Amount 0.00`, the credit REMAINING, not the value (5.3). Face figures are positive; capture negative (P14). |
| PLAYFORCE | `Qty \| Item \| Description \| Unit Price \| Price (Ex. GST)` | `Price (Ex. GST)` | Unit price can print with no decimals (`1355`). `Account: 10367833` in the payment block is a bank account, not a PK. Some invoices print the literal word `undefined` in the Account field. 220 fixed template rows per document: budget for it (7.6). |
| KACHEL | none printed | rightmost money column under `Rate $` | No item table header at all. Zone rows print `PK000028  19,716.00` with no quantity. Residue window starts at the first body row (4.5). |
| VINTON (A) | `DESCRIPTION \| EX AMOUNT \| TAX CODE` | `EX AMOUNT` | No quantity and no unit price columns exist. |
| VINTON (B) | `HRS \| DESCRIPTION \| UNIT PRICE (ex-GST) \| TOTAL PRICE (ex-GST)` | `TOTAL PRICE` | **The `GST:` label prints with no value anywhere in its band**, so the GST is derived under 5.0 with `gst_basis` recorded, never silently. The totals block interleaves with the bank block: `Subtotal:` shares a row with `RST Systems Pty Ltd`, `Total (inc-GST):` with the remittance email address. `Balance Due:` repeats the total, and the how-to-pay page repeats it a third time, so two sources always agree. A fuel levy line of $6.00 to $8.00 sits near the totals block and was taken as the invoice total on 27 documents in `Binder1666`. |
| MPDT | `Description \| Quantity \| Unit Price \| GST \| Amount AUD` | `Amount AUD` | Header labels stack above their values (5.2). PK prints malformed: `PK#00047`, `PK#0000477`. |
| PPG (SAP) | `Item No \| Material \| Item Description \| Quantity \| Unit Price \| Net Value` | `Net Value` | **No row is labelled Subtotal**: the ex-GST total is `PRODUCT TOTAL` plus `FREIGHT` plus `PAINTBACK LEVY`, each printed separately. The unit price prints to FOUR decimals (191.1400). No PK prints on the face; the line description is a price-change reason code and `MIXED MERCHANDSE`. Terms of sale fill page 2. |
| ETSOL | `Description \| Qty \| Rate \| TAX \| Amount` | `Amount` | The `TAX` column prints the literal `GST`, a code, not money. Negative rows appear for partial deletions. |
| GLASCOTT | `Invoice No` face plus an attached schedule | schedule `Ex GST` column | The face total and the attached schedule total can differ (Open Item B-019). **Schedule rows PRINT an amount and are typed `ATTACHMENT`** (9, rule 16d): the schedule is written across a SET of invoices and each row carries its own cost account, so a row belongs to whichever invoice its account names. Keep the amount, leave it out of the tie. Until v7.6 this row read "schedule rows carry no amount in the face table", which contradicted rule 16d and told an extractor reading the 2.1 fast path to do the thing v7.1 was written to stop. |
| GLASCOTT_LM, HIGGINS, LEVAI | `DESCRIPTION OF SUPPLY \| AMOUNT` / `DESCRIPTION \| AMOUNT` | `AMOUNT`, right aligned and ragged | A two-band table: no quantity, no unit price. **Levai (Xero vintage, `INV-\d{5}`):** the amount prints on the LAST row of a multi-row description block whose upper rows carry the payee name, the `PAR/...` contract, the PK and the quote and CR references (4.2.4). Totals block prints `Subtotal`, `GST (10%)`, `Total`, `Paid to Date`, `Balance Due` in that order: take `Total` (5.0). Bank block interleaves to the left of the totals block. |
| C2C | `Description \| Quantity \| Price \| Tax \| Amount` | `Amount` | Fuel levy surcharge posts to a separate PK and service (split posting). |
| C2C_INCL | `Description \| Quantity \| Unit Price \| GST \| Amount AUD` | `Amount AUD`, **GST inclusive** | Unit Price and Amount columns are GST INCLUSIVE; the description states the ex-GST base. Foot prints `INCLUDES GST 10%`. Try rung 2 first (2.1). |
| CERTIFIED | `Description \| Quantity \| Unit Price \| GST \| Amount AUD` | `Amount AUD` | Main-roads and parks split across two PKs on one invoice. |
| ELEMENTAL | `Item Code \| Description \| Unit Price \| Quantity \| GST \| Total` | `Total`, **GST inclusive** | `Total` column is GST inclusive; ex = Total less GST. Quantity sits to the RIGHT of unit price. Try rung 2 first (2.1). |
| QPOWER | `Part # \| Item \| Quantity \| Unit Price \| GST \| Total` | `Total` | Wide simPRO layout; item names wrap onto the rows above AND below at column 177. |
| HARPLEY | `QUANTITY \| DESCRIPTION \| UNIT PRICE(ex-GST) \| TOTAL PRICE(ex-GST)` | `TOTAL PRICE` | Template B is GST INCLUSIVE (rung 2, try first). Invoice numbers keep leading zeros (`000\d{5}`). Two-page with a How-to-pay page. |
| ORIGIN | consolidated site rows | per-site `Amount` | Council-wide consolidated invoice, 47-48 sites; Parks carries a subset (PARTIAL-SCOPE). CR credits capture negative. Per-site GST prints. |
| SEACRETE | `Code \| Description \| Quantity \| Rate \| Amount` | `Amount` | Small single-site water-park invoices. |
| POOLSHOP | `Description \| Quantity \| Price \| Tax \| Amount` (old) and `... \| Unit Price \| GST \| Amount AUD` (new Xero) | `Amount` | Two layout vintages from one supplier. |
| WEIS | both Xero vintages, as POOLSHOP | `Amount` | Prints its ABN grouped on one template and ungrouped on the other. |
| FLAVELL, FLAVELL_ATT | Xero vintages | `Amount` | On the attachment layout a row can print `description 10% amount` with no quantity. |
| BURLY | `DESCRIPTION \| QTY \| UNIT PRICE \| TOTAL PRICE` | `TOTAL PRICE` | Amounts print with a `$` inside the band: the overlap test handles it, a left-edge test does not. |
| PROVAC | `Item \| Description \| Quantity \| Unit Price \| GST \| Amount AUD` | `Amount AUD` | Cemetery grave-dig dockets; `Amount Due` is the total label. |
| TREESCAPE | wide Xero-like | `Amount` | Total label is `Total Payable`, printed on a following row. |
| BUSHCARE | `DESCRIPTION \| QTY \| RATE \| AMOUNT \| GST` | `AMOUNT`, **left of the GST column** | The amount band is NOT rightmost: `GST` prints to its right. Total label is `BALANCE DUE A$`. |
| AUSTSPRAY | `Item \| Total` | `Total` | Item row figures differ from the "plus gst" figure in the description (Open Item B-021). |
| AUSTCARE | job table with Job No, Site Name, PK | `$` column | Column collision in `-layout`; needs word-level bounding boxes to assign site names to job rows. |
| EMU, TEC, ACTIVECO, GURU | `Description \| Quantity \| Unit Price \| GST \| Amount AUD` | `Amount AUD` | GURU prints two vintages. TEC prints `Invoice Number` and its value on non-adjacent rows (5.2). |
| TENNYSON | `Job \| Quantity \| Description \| Net Price \| GST` | `Net Price`, **not rightmost**: `GST` prints to its right | A two-money-column item table, so the amount and its GST sit side by side and the rightmost token is the GST. Totals print as `Net $`, `GST $`, `Total $` down the right of the page with the delivery note and bank block to the left. No PK prints on the face; `Order No:` and `Account: LOG107` are Council references, not PKs. |
| WOODMANS | `SKU \| Description \| Qty \| UM \| Price Ex GST \| Disc % \| GST \| Total Inc GST` | `Total Inc GST`, **GST inclusive**; the ex-GST unit price is in `Price Ex GST` | The header wraps over three physical rows (`Price`/`Disc`/`Tot`, then `SKU Description Qty UM`, then `Ex GST`/`Inc`), so the band row is the union of the three. Each item wraps over two to four rows with the description continuing below the priced row. Totals are `GST Ex Total`, `GST` and `GST Inc Total`, all three beginning with `GST` (5.1). Discounts print as a percentage in their own band. |
| SECUREcorp | wide, wrapped | `Amount` | A printed line wraps over several physical rows: rate and amount print on the first, quantity on the second. |

---

---

---


## Annexe B. The two v5 runs that produced v6

| | `mix22` | `Binder11111` |
|---|---|---|
| Suppliers | Savco, Heritage, Play Force, Kachel | RST Systems t/a Vinton |
| Documents | 40 | 13 |
| Declared gate | RED, 11 x P1 | RED, 2 x P1 |
| Documents at OUT | 16 of 40 | 2 of 13 |
| Captured ex GST as extracted | $109,059.92 | $40,295.05 |
| Captured ex GST after restatement | $166,863.84 | $52,245.05 |
| Value dropped by the classifier | **$57,803.92, 35% of the batch** | **$11,950.00, 23% of the batch** |
| Rows carrying an amount typed NARRATIVE | 32 | 2 |
| Header misreads | 13 (`GST TOTAL` read as `TOTAL`) | 0 |
| `bands` recorded | none | none |
| `shingle_checks_run` | 0 | 0 |
| Repairable downstream? | Yes: every dropped row was in the retained text | **No.** Six pages, across five documents, carried no line record at all (P3), so the batch is held for re-extraction |

The difference between those last two rows is the whole argument for the v6 and v7 gates. A misclassified row is recoverable, because the evidence is still in the corpus. A page you did not transcribe is gone, and the binder has to be read again.

---

---

---


## Annexe C. What changed from v6

Everything below is an amendment inside v6's numbering. No v6 rule was deleted and no section was renumbered.

| Change | Where | What it prevents |
|---|---|---|
| Bands are spans and are calibrated against a real priced row | 4.1, P11 | A right-aligned ragged money column rejecting its own short values. On the conformance example the label span is `[111, 116]` and the values run to 120 |
| Overlap decides, not left-edge proximity | 4.2 | `$` prefixes inside the band (Burly), non-rightmost bands (Bushcare), variable-width amounts everywhere |
| One closed classification ladder, totals and payment blocks before the band test | 4.0 | A totals row or a bank figure typed PRICED. On the conformance example that is five false rows and a threefold capture |
| Amount on the last row of a description block is explicitly PRICED | 4.2.4, 11.6 | The Levai and Higgins shape being read as a narrative block with no price |
| Residue test emits `residue_rows`, and its window is defined for no-header and multi-table documents | 4.5, P12 | A test claimed rather than run, and an undefined window on Kachel |
| Label precedence table; `Balance Due` demoted to a fallback; `Paid to Date` excluded | 5.0 | A part-paid invoice's balance read as its total, which then fails 5.4 for the wrong reason |
| The "bare amount under Sub Total" clause scoped to documents with no Total label | 5.0 | A direct contradiction inside v6 section 5 |
| `header_adds_up: "derived"` where the subtotal was derived | 5.4 | A tautological check reported as an independent one |
| Tie tolerance 1c, with the 1c to 2c band ties plus F7 plus AMBER | 6.0, F7 | A GREEN corpus that fails the workbook's rule 17 checks at build time |
| Every rung carries structured evidence, not only rung 1 | 6 | Three of the four rungs remaining assertions |
| Gate truth table | 13.0 | GREEN, AMBER and RED used everywhere and defined nowhere |
| P14 credit-note sign, P15 stem collision | 13.1 | A credit posted as a debit; two evidence files overwriting each other |
| Findings numbered F1 to F7 to match the schema's `code` field | 14 | A schema field the instructions never populated |
| `line_no` is per page, band offsets are into `line_text`, corpus checks emitted as booleans | 9.1 | Ambiguous row references and unverifiable offsets, in both runtimes |
| Run sheet, Annexe A fast path, reference algorithm, budget arithmetic | Run sheet, 2.1, 4.6, 7.6 | Discovery work repeated per document, and a binder started that cannot be finished |
| Footer `Page m of n` asserted against the page range | 3.5, P9 | A silent split error |
| Conformance example with real offsets | 16.4 | A self-test before a large binder, covering every amendment above |

---

---

---


## Annexe C1. What changed from v7 (v7.1, 17-Sep-2026)

Two amendments, both found by running `pswp_corpus_gate.py` over the twenty-nine corpora already held in the branch repository. Neither relaxes a capture or verification standard.

| v7 section | Amendment | Why |
|---|---|---|
| 9, closed list | `ATTACHMENT` added, thirteen values | The type is already in use (77 rows over `attach_4` and `mixed_1`) and the branch build depends on it: register rule 16d excludes attachment rows from rule 17 check 1. v7's list dropped it, so every one of those rows read P13. |
| 4.0 ladder, 4.4, P2 | The amount-bearing test runs over PRICED and ATTACHMENT | `playforce_vinton_glascott_20260916` typed 103 Glascott schedule rows NARRATIVE and kept their amounts. They are correctly outside the tie, proven: all five documents tie their printed subtotal exactly on their PRICED rows alone, and adding the schedule rows would break every tie, $124,347.79 in all. Under v7 as written the corpus was RED on rows that were right to exclude; under v7.1 the type says so. |

**Not amended, and why.** `HEADER`, 8 rows in `mixed_1`, stays P13. It is a mis-typing of `TABLE_HEADER` and nothing downstream reads it, so the fix belongs in that corpus, not in the list.

---

---

---


## Annexe D. What changed from v7, and the run that produced it

`Binder1666`, 100 documents over 141 pages, seven suppliers, declared AMBER by its extractor and closed with the sentence "the corpus is GREEN and can proceed to the build session". Gated under v7 it computed RED on one document. Gated under v7.2 it computes RED on 31, and the corpus understated the incl-GST value of those documents by **$52,390.66**.

| Change | Where | What it prevents |
|---|---|---|
| GST may not be derived silently; a derived GST carries `gst_basis` and `header_adds_up: "derived"` | 5.0 | The failure mode that defeated v7's header gate on 29 documents at once: derive the GST from a wrong total and the block adds up by construction |
| P16, GST must be a tenth of the subtotal, relative tolerance | 13.1 | A swapped, derived or misread GST that P10 cannot see, because addition survives a swap |
| P17, a header figure must be printed on the row it cites | 13.1 | A figure invented or taken from a row that says `Completed 22/06/2026`, with `header_sources` recording it and nothing reading it back |
| F8, citation drift and cited rows not typed `TOTALS` | 14 | A right figure with a wrong evidence trail, and the interleaved-totals typing breach that produces most of them |
| P1 amended: zero PRICED lines on a tax invoice is P1 whatever subtotal is recorded | 13.1 | A total parse failure hiding behind a recorded subtotal of 0.00 |
| `GST Ex Total` and `GST Inc Total` named as totals labels | 5.1 | The substring trap in reverse, on the Woodmans layout |
| The report may not contradict its own gate line, and a finding may not contradict its own figures | 15 | A RED corpus arriving at a build session under a sentence saying it is GREEN |
| TENNYSON and WOODMANS added; VINTON (B) and HERITAGE traps restated from this run | Annexe A | The three layouts that failed here |

---

---


## Annexe D1. What changed from v7.2 (v7.3, 18-Sep-2026)

| v7 section | Amendment | Why |
|---|---|---|
| 13.1, P1 | The v7.2 amendment is exempted where the document carries `duplicate_of` | Found on arrival of `Pages_from_Binder1`, 96 Play Force documents declared GREEN. The amended P1 computed RED on five of them; every one was a repeated copy inside the binder, every row typed `DUPLICATE_COPY`, arithmetic null exactly as 4.0 rung 2 requires. With the exemption that corpus computes GREEN and Woodmans 6431345, which is not a duplicate, still fails. A check that returns sound work is a defect in the check. |

---

---

---


## Annexe D2. What changed from v7.3 (v7.4, 18-Sep-2026)

Two structural amendments, neither of them a new pathology. Both came out of assessing the standard rather than
out of a corpus failing.

| Area | Amendment | Why |
|---|---|---|
| 13.2, the computed gate | **The gate applies the checks the corpus could have satisfied, scoped on the FIELD or CONVENTION each check reads** (13.2). Scoping on the declared VERSION alone was the first cut and was a loophole: it let a corpus escape P14, P15 and P16 by declaring v6, none of which needs anything v6 lacks, and the report names the set it applied. `manifest.prompt_version` is therefore mandatory, not decorative. | A RED verdict stops carrying information the moment it fires on a field that did not exist when the corpus was extracted. Run unscoped over the 34 corpora held in the branch repository, 31 read RED and almost all of them on P11 and P12 alone, because no corpus predating v7 carries `bands_calibrated_on` or `residue_rows`: neither field is in the v5 or the v6 prompt. Scoped on the evidence, and after the later amendments, a sweep on 18-Sep-2026 over the 35 corpora then held read 7 GREEN, 21 AMBER, 7 RED, and four of the 7 RED are archival snapshots gated as though live. The figure of 8 quoted when this annexe was written came from the looser version-only scope and from a smaller denominator; it is superseded. An intermediate figure of 11 RED of 37, published in the assessment, was written before the description-layer demotion was withdrawn and never re-swept; it is superseded too. |
| 10, verbatim fidelity | **The manifest carries `page_text_independent`, a boolean, and `page_text_basis`, the sentence explaining it.** A corpus whose page text was rebuilt from its own `line_text` rows is reported as an UNVERIFIED description layer. (It demoted the gate when this annexe was written; v7.6 withdrew that and made it a qualifier, see Annexe D4.) | The shingle check is the only test in this standard that reads a word rather than an amount, and it needs a haystack the capture did not write. Rebuilding page text from the corpus's own rows makes the check runnable and **unfailable**, because the haystack becomes the captured text. A corpus can tie to the cent on every invoice and carry a description the page never printed. Of the 34 corpora held, exactly one has an independently parsed page text, and it is the one batch where the binder was supplied. |

**What the second amendment cost, and why v7.6 withdrew it.** Demoting on the description layer took GREEN off
every corpus at once, the conformance fixture included, which left the 16.4 self-test with no passing reference.
v7.6 makes it a qualifier printed beside the gate instead. The cost was predicted in review before this
amendment was written, which is the point recorded in Annexe D4.

---


## Annexe D3. What changed from v7.4 (v7.5, 18-Sep-2026)

| v7 section | Amendment | Why |
|---|---|---|
| 13.1, P16 | **A mixed supply is exempt.** Where the priced lines each print a GST amount and those sum to the printed GST, the header is proved by the lines and the document-level ratio is explained by the mix. | Woodmans 6431345, page 48 of `Binder1666`, supplied 18-Sep-2026. It prints $268.00 ex GST, $22.80 GST and $290.80 inc over seven rows, one of them GST-free, so a tenth of the subtotal is $26.80 and P16 as written failed a correct invoice. 5.6 already covered the case in prose; nothing enforced it. |

Third amendment in three days forced by a document rather than by reasoning, and the second to remove a false
positive rather than catch a defect. Both false positives, P1 on duplicate copies and P16 on a mixed supply,
were introduced by an amendment written to catch a real defect in the same week.

---

---


## Annexe D4. What changed from v7.5 (v7.6, 18-Sep-2026)

| v7 section | Amendment | Why |
|---|---|---|
| 11.4 | **A standing rule: every uniqueness and completeness check exempts `duplicate_of`.** P7 is the deliberate exception, because it exists to find a duplicate that was NOT marked. | Four checks had needed the same exemption one at a time, P1 at v7.3 and P15 at v7.6 among them, each found by a correct corpus being failed. Writing it once stops the fifth. |
| 13.0, 10.1 | **The description layer becomes a separate axis**, printed as a qualifier beside the gate and never folded into the word. | Demoting on it, at v7.4, took GREEN off every corpus in the branch repository at once, including the 16.4 conformance fixture. That left the self-test with no passing reference, so an extractor could not tell conformance from a defect, and it gave a corpus that ties to the cent the same word as one that stopped mid-binder. **This cost was predicted in review before v7.6 was written.** |

**Two process notes, both earned.**

**No version number changes until the section it names has changed.** v7.4 shipped as an annexe and a title with
its two amendments nowhere in the body, so no corpus produced against it would have carried either field. v7.6
shipped the same way on its second amendment: the title said "separate axis" and 13.0 still demoted. Three
releases running, the metadata moved ahead of the document. The rule is now stated: the version line is written
last, after the section it names reads the new way.

**An annexe is filed in ascending order, and the newest is written, not prepended.** v7.6 corrected C1 filing
before C and introduced D3 before D2 in the same pass. The order is A, B, C, C1, D, D1, D2, D3, D4.
