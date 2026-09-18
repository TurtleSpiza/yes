# Printed-money screen over NARRATIVE rows, 18-Sep-2026

**Verdict: the 4.4-versus-4.5 hole is real and populated, and not one of the 19 rows open on a current corpus is a dropped line item.**

Run: `python3 toolkit/pswp/pswp_money_screen.py <corpus>` over all 24 live corpora, prompt v7.7 section 4.7.
Archival snapshots (11, rule 11.12) are excluded: they are the record of what arrived and are never repaired.

## What the screen is for

- **4.4** reads the amount your corpus **recorded**, is global, and the gate enforces it as **P2**.
- **4.5** reads the money the page **printed**, is windowed and band-scoped, and only the extractor can run it.
- **Neither reaches** a row that prints money, is typed NARRATIVE and records nothing. The gate is blind by
  construction: the money is on the page and not in the corpus.
- This screen closes that from `line_text` alone, with no PDF.

## Result

| Class | Rows | What it is |
|---|---|---|
| `EXEMPT` (7 named classes) | 781 | A money-shaped token that is not an amount |
| `MISTYPE_CANDIDATE` | 524 | A totals or header label typed NARRATIVE. A wrong rung, no dollar moves |
| `ECHO_OF_A_RECORDED_AMOUNT` | 152 | The value is already in the document. A repeat page or a restated total |
| **`UNACCOUNTED`** | **108** | The value appears nowhere else. **The only class that can be a dropped line item** |

**Of the 108, 89 are in `playforce_vinton_glascott_20260916_v6`,** which the `_v7` corpus supersedes and which
reads **0**. The screen knew nothing about that restatement, so tracking it is the evidence that it tracks the
real thing. **19 are open on current corpora, and every one is traced below.**

## The 19, all traced

### 1. `mixed_new_26_27` (10 rows) — a real capture defect, in a summary block

Two consolidated electricity invoices, `1026099` and `1026231`.

- **The charge values print one row BELOW their labels.** Rows 29 to 31 carry `Network Charges`,
  `Regulated Charges` and `Environmental Charges` typed TOTALS with a null amount; rows 32 to 34 carry
  $195,004.73, $2,325.14 and $31,516.40 typed NARRATIVE with nothing attached. The label and its figure were
  captured as separate rows and never joined.
- **The account balance is not captured at all.** $1,236,014.57 and $1,255,428.76 print beside the current
  charges on row 14 of each invoice, and again on row 150. Nothing in either corpus records them.
- **Consequence:** neither affects the register. The documents tie on their item tables and the control total
  is untouched. But an invoice carrying a brought-forward balance over $1.2m with no record of it is an **F1**
  the analyst should have, and the detached charge values should be joined to their labels on re-extraction.

### 2. `harp_new` (5 rows) and `vinton_new` (1 row) — correct capture, and an F2 finding worth $5,915.85

A unit price printed with **no quantity and no extended amount**, so the printed subtotal correctly excludes it.

| Document | Row | Text | Amount |
|---|---|---|---|
| Higgins 00013885 | p3 r30 | Drain Cleaning - CCTV | $150.00 |
| Higgins 00014397 | p25 r35 | 01-09-25- Paynes Bridge Park | $1,501.50 |
| Higgins 00014397 | p25 r36 | 02-09-25- Glen Logan Lakes | $1,188.00 |
| Higgins 00014397 | p25 r37 | 02-09-25- Mundoolun Community Park | $1,490.50 |
| Higgins 00014640 | p45 r37 | 26-11-25 - Flindersia Park 10,000L | $1,515.25 |
| Vinton 19948 | p45 r36 | LCC Fuel Levy - Diesel | $70.60 |
| | | **Total** | **$5,915.85** |

- **The capture is right.** On 00014397 the six PRICED rows sum to $10,057.85, which is the printed subtotal to
  the cent, and rows 35 to 37 carry their figures in the **unit-price column** with the amount column blank.
  On 19948 the two PRICED rows sum to $2,389.25, again the printed subtotal exactly, and $70.60 sits in the
  unit-price column. Under the 4.0 ladder, rung 6 tests overlap with the **amount** band, so NARRATIVE is the
  correct type and `residue_rows: []` is a correct result.
- **The finding is about the invoice, not the capture.** A line item printed on a tax invoice and left out of
  its total is **F2**. On 00014397 the three are dated 01-09-25 and 02-09-25 under an invoice described as
  "Various Parks July August 2025", so they read as September work listed and not charged.
- **Do not restate these rows.** Record the finding.

### 3. `binder1666` (3 rows) — a rung-2 mistype, no money moves

Vinton 19980, page range [119, 122]. Pages 121 and 122 repeat pages 119 and 120 verbatim, down to the row
numbers. The repeat was typed NARRATIVE instead of `DUPLICATE_COPY` at ladder rung 2. The arithmetic is
correct either way, because the repeated rows carry null amounts and the four PRICED rows on page 119 sum to
$2,117.78, the printed subtotal. The screen reads the rows as UNACCOUNTED only because the **unit prices**
($315.00, $190.00, $180.00) were never recorded on the PRICED rows they belong to.

## The false-positive classes, each found by tracing a row to the page

The first cut read 156 UNACCOUNTED. Four classes were then named, not silently filtered:

1. **`ZERO_OR_UNIT_QTY`** — `1.00   0.00   0.00` across the qty, unit-price and amount columns of a description
   continuation row. 36 rows on `ksadasd`. Typing them PRICED to satisfy rung 6 would be wrong.
2. **`RATE_EXPRESSION`** — `5 visits / 55 trees @ $284.35 = $1,421.75` inside a wrapped description block
   (rule 11.6). Trees 36107's five components sum to $3,145.68, which is its single PRICED row and its printed
   subtotal exactly, so every component is already captured.
3. **`RATE_EXPRESSION_WRAPPED`** — the same, where `pdftotext -layout` splits it so the `@` ends one row and
   `$37.35` is the next. Needs the previous non-blank row, or the second half reads as a bare column amount.
4. **`CONTRACT_TERMS`** — an insurance or indemnity limit in the fine print. 309 rows on `playforce_new`, which
   prints "insurance for an amount not less than $10,000,000" on every invoice. The row should have been typed
   TERMS at rung 7; it is a mistype with no arithmetic consequence.

## What the screen still cannot do

**It reads text, not bands.** It cannot tell the amount column from the unit-price column, which is exactly why
the six F2 rows above read UNACCOUNTED and are correct captures. Separating a dropped line item from a
correctly uncaptured unit price needs the page. An UNACCOUNTED row is a row to look at, not a proven defect.
