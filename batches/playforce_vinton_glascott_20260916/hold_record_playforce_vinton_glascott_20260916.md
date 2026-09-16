# Hold record: playforce_vinton_glascott_20260916

**Status: HELD. Not built from.** The corpus as received gated RED. It has been restated and now gates
GREEN, and it is still held, because rule 8 identity is unestablished on 22 of its 61 documents and the
binder that would settle it was not supplied.

## 1.0 What was received

| Artefact | File |
|---|---|
| Corpus as received | `corpus_playforce_vinton_glascott_20260916_as_received.json` |
| Capture report as received | `capture_report_playforce_vinton_glascott_20260916_as_received.md` |
| Restated corpus | `corpus_playforce_vinton_glascott_20260916_v6.json` |
| Masked-row screen | `mask_screen_playforce_vinton_glascott_20260916.json` |

- Runtime A, extraction prompt v6, M365 Copilot with `pdftotext -layout`.
- 61 documents, 140 of 140 pages, 8,643 line records, two source files.
- Suppliers: Play Force Australia 28, R.S.T. Systems 22, Glascott Landscape and Civil 11.
- Binders: `97 001 281 572.pdf` (16 pages, md5 `007e24fb685834aa109a08eebcc9f1cd`) supplied.
  `play force and vinton.pdf` (124 pages) **not supplied**.

## 2.0 The gate as received

RED on four P1 pathologies, confirmed independently by running this project's own gate over a copy: it
applied 92 repairs (70 F13, 22 F1) and stayed RED. Ten documents sat at OUT. P10, P11 and P13 were clean:
every header added up, bands were anchored on all 57 priced documents, and no line type fell outside the
closed list. The extraction was well formed. The failures were classification, not structure.

## 3.0 The three defects, and why each was restatable

**3.1 Masked rows read from the text layer (M1, five Glascott documents).**
The Glascott attachment is one workbook exported once per portion, with every row outside that invoice's
scope filled black. The text stays in the cell underneath, so `pdftotext` returns rows the page does not
display. Rendering the binder finds filled bands on pages 5, 7, 9, 13 and 15, and on no other page of
either binder. Those five pages are the second page of the five two-page documents, which are exactly the
five Glascott documents at OUT. The correspondence is one to one in both directions.

This is not merely an overstatement. Invoice 012193's single masked row is the row 012194 bills on its own
face, so capturing a masked row counts the same work twice inside one binder.

| Document | Page | Masked priced rows | Masked value | Captured | Printed |
|---|---:|---:|---:|---:|---:|
| 012192 | 5 | 25 | $32,477.92 | $32,951.44 | $473.52 |
| 012196 | 7 | 21 | $35,866.01 | $36,339.53 | $473.52 |
| 012194 | 9 | 28 | $30,167.88 | $31,405.54 | $1,237.66 |
| 012199 | 13 | 28 | $25,835.98 | $27,073.64 | $1,237.66 |
| 012193 | 15 | 1 | $1,237.66 | $31,405.54 | $30,167.88 |

Each ties to its printed subtotal once the masked rows are dropped. The rows are retained on the corpus,
retyped NARRATIVE and flagged `masked_on_page`, never deleted: nothing is lost and the restatement is
auditable. Screened by `toolkit/branch/pbr_mask_screen.py`.

**3.2 The item row typed NARRATIVE (F14, four Play Force documents).**
`INV-3917`, `INV-3905`, `INV-3898` and `INV-3915` carried a non-zero printed subtotal and no priced line at
all, which is the P1 shape. On each, the item row prints its quantity, unit price, GST rate and amount, and
the amount sits inside the item table's own `amount` band. That is the 4.5 residue test failing, which the
prompt calls P2. Restating it reads the column the document's own printed header row defines; it infers
nothing.

- `INV-3917` row 26: 13.00 x $220.50, amount $2,866.50 at offset 116, band 111.
- `INV-3905` and `INV-3898` row 26: 30.00 x $94.06, amount $2,821.80 at offset 105, band 100.
- `INV-3915` rows 26 and 28: $494.50 and $2,431.20, both inside band 110.

**3.3 One invoice printed twice (F15, one Play Force document).**
`INV-7604` spans pages 39 to 44, and pages 42 to 44 repeat pages 39 to 41 verbatim, 258 rows against 258
rows. The priced row $2,862.60 appears once in each copy, so captured came to $5,725.20 against a printed
$2,862.60. `duplicate_of` was null and `duplicate_copy_pages` empty: the 11.4 screen had not been applied.
The second copy is retyped `DUPLICATE_COPY` and recorded, which is the treatment `binder11111` already
carries on 19827 and 19997.

## 4.0 The gate after restatement

GREEN. 61 of 61 TIE, none OUT, no pathologies. Captured **$332,240.69** against printed subtotals of
**$332,240.69**, tying to the cent across the whole batch.

## 5.0 Why it is still held

**Rule 8 identity is unestablished on 22 documents.** Every R.S.T. Systems document carries
`supplier_abn: "(not printed)"` and `abn_source: "absent"`.

- This project already holds the supplier: `pbr_histories_v4.json` VIN003, canonical label
  **Vinton Tree Services**, ABN **84 008 552 538**, entity "R. S. T. Systems Pty. Limited Trading as Vinton
  Tree Services", established at branch v15 across 42 `vinton_new` invoices.
- That history records why this batch failed: the Vinton letterhead prints as an IMAGE and carries nothing
  into the text layer, so the `vinton_new` binder had to be rendered at 300 and 400 dpi and read twice.
- This corpus reports `ocr_pages_run: 0`, `ocr_pages_not_required: 140`. OCR was declared unnecessary on the
  very pages whose ABN is known to be image-only.
- The label the corpus does carry, `RST Systems Pty Ltd`, is genuinely printed in a footer, but it is not
  the canonical label. Written to a COUNTIF-keyed column it trips the case-variant trap.

**The fix needs the binder.** `toolkit/branch/ocr_image_letterhead.py` is the tool, and it needs
`play force and vinton.pdf`, which was not supplied to the session that wrote this record.

## 6.0 Open items carried forward

1. **Supply `play force and vinton.pdf`** and run
   `python3 toolkit/branch/ocr_image_letterhead.py playforce_vinton_glascott_20260916 <binder.pdf>`.
   Until then the batch stays held.
   - `vinton new.pdf` (84 pages, md5 `1b12cfee3fc669c389bf874e59f875ec`) was supplied on 16-Sep-2026 and is
     NOT this binder: it is the source for the shipped `vinton_new` batch, whose 42 documents (19402 to 20022)
     share none of the 22 doc_refs held here. It cannot carry an ABN onto these lines. It was screened for
     masked rows and is clean (`batches/vinton_new/mask_screen_vinton_new.json`).
2. **The 124 unscreened pages.** `pbr_mask_screen.py` has not seen that binder, so the 50 Play Force and
   Vinton documents carry no M1 verdict either way. Re-run the screen when it arrives.
3. **Rule 12 overlap.** `INV-7613` and `INV-8009` are already embedded from `playforce_new`. Printed
   subtotal and printed total are identical in both corpora ($23,718.00 / $26,089.80 and
   $20,700.00 / $22,770.00). They are audited against the embedded copy and NOT re-captured.
4. **17 fuel levy lines, $888.56**, across the Vinton invoices, for the stepped and capped model once
   identity is settled.
5. **14 documents print no PK, $178,456.83**, three of them the large Glascott invoices (011964 $62,058.77,
   011965 $39,272.75, 012314 $39,409.60).
6. **The verbatim fidelity check cannot run (rule 19.2).** No document in this corpus retains
   `page_text`. All 17 batches already in this repository retain it on every document; this corpus and
   the two others received on 16-Sep-2026 are the only ones that do not. `pswp_shingle_check.py` returns
   **UNVERIFIABLE** rather than PASS, because with no retained page text the only haystack is the
   captured text itself. Retain the page text when `play force and vinton.pdf` is supplied.
7. **Masked row text is retained in this repository.** The rows are Council's own park maintenance billing
   detail from other invoices in the same binder, retained so the restatement can be audited. If that
   retention is not wanted, drop the flagged rows from the corpus and re-gate.
