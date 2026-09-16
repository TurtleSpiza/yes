# Hold record: savco_vegetation_20260916

**Status: HELD pending the binder.** Nothing is known to be wrong with this corpus. It gates GREEN on
this project's own gate and its arithmetic is exact. It is held because two of the three verification
legs cannot be run at all without `SAVCO VEGETATION SERVICES PTY LTD.pdf`, which was not supplied.

## 1.0 What was verified, and it passes

- **Gate GREEN**, confirmed by running `pswp_json_repair.repair_and_gate` over a copy: no pathologies,
  and the only repairs were 32 F13 evidence stems.
- **Arithmetic exact.** 32 of 32 TIE, none OUT. Captured **$44,373.97** against printed subtotals of
  **$44,373.97**.
- **P10, P11, P13 clean.** Every header adds up, bands are anchored on all 32 priced documents, no line
  type outside the closed list.
- **The 4.5 residue is empty in substance.** 14 rows sit between the item header and the totals block
  carrying a money token in the amount band, and every one of them is **$0.00**: a
  `CUSTOMER REQUEST NUMBER - CR#...` row. Nothing is uncaptured.
- **Identity holds.** All 32 print ABN `78 161 366 749` in the text layer. It passes the ATO modulus-89
  checksum, matches all 25 documents of the shipped `savco_new` batch, and matches embedded creditor
  history **SAV012, Savco Vegetation Services Pty Ltd**. Rule 8 is satisfied.
- **No rule 12 overlap.** None of the 32 doc_refs appears in `savco_new`.
- **Coverage.** All 32 carry a PK (PK000477 x22, PK000482 x8, PK000325 x2), a work order and contract
  `PAR/329/2021`. No fuel levy line is printed on any of them.

## 2.0 Why it is held

**2.1 The verbatim fidelity check cannot run (rule 19.2).** No document retains `page_text`. All 17
batches already in this repository retain it on every document; this corpus and the two others received
on 16-Sep-2026 are the only ones that do not. Run against it, `pswp_shingle_check.py` returns
**UNVERIFIABLE**, not PASS: with no retained page text the only haystack is the captured text itself, so
the test asks whether the text equals itself and cannot fail. That is the one failure mode the check
exists to catch, and it is invisible in the arithmetic, because a corpus can tie to the cent on every
invoice and still carry a description the page never printed.

**2.2 The masked-row screen cannot run.** `pbr_mask_screen.py` needs the binder. The risk is materially
contained here, because a document that ties to its printed subtotal cannot be over-capturing masked
rows, and all 32 tie. It is not eliminated, and the standing rule asks for the screen before capture.

## 3.0 To release it

1. Supply `SAVCO VEGETATION SERVICES PTY LTD.pdf` (32 pages).
2. `python3 toolkit/branch/pbr_mask_screen.py --corpus <corpus> <binder.pdf>`
3. Retain the page text and re-run
   `python3 toolkit/pswp/pswp_shingle_check.py --corpus <corpus> --pages <pages.json> --out shingles_savco_vegetation_20260916.json`
   until it returns PASS rather than UNVERIFIABLE.
4. Then the normal capture pipeline: author `notes_..._v6.json`, build the match table, add the batch to
   `BATCHES` in `pbr_stage.py` and its stamp to `pbr_capture.py`, and run `pbr_build.py`.

## 4.0 Open item

- **SV007959** prints a work date of **09-10-2026** against an invoice date of **03/08/2026** and a second
  work date of 31-07-2026 on the same document, so the work date is later than the invoice. Read either
  way round, day-month or month-day, it still postdates the invoice. Amount $1,562.22. Verify against the
  source document; it looks like a keying error for 09-07-2026.
