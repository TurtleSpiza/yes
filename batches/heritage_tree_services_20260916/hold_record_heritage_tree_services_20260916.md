# Hold record: heritage_tree_services_20260916

**Status: HELD.** The capture report states `Gate: GREEN` and `Pathologies: None`. This project's own
gate returns **RED** on two P2 pathologies. A supplied GREEN is not a verified GREEN, and the corpus is
held until it is re-gated clean.

## 1.0 The disagreement

`pswp_json_repair.repair_and_gate` raises:

| Code | Document | Page | Detail |
|---|---|---:|---|
| P2 | INV-48542 | 47 | amount-bearing row 31 typed NARRATIVE |
| P2 | INV-48599 | 49 | amount-bearing row 33 typed NARRATIVE |

Both rows are a quantity of 1 at **$0.00**, sitting in the item table above the priced crew row:

    INV-48542 r31    1        0.00
    INV-48599 r33    1        0.00

**They cost nothing arithmetically.** Both documents TIE exactly, and retyping a $0.00 row PRICED moves
no value. The gate is still right to stop: the 4.4 invariant is asserted both ways, and a corpus that
fails its own gate is logged and held, never part-built from. The fix is to retype the two rows and
re-gate; it needs no binder and no re-extraction.

These pathologies are not an artefact of the F14 and F15 families added on 16-Sep-2026. The gate as it
stood before those families raises exactly the same two.

## 2.0 What is otherwise sound

- **Arithmetic exact.** 26 of 26 TIE, none OUT. Captured **$62,940.19** against printed subtotals of
  **$62,940.19**. Only repairs were 29 F13 evidence stems.
- **P10, P11, P13 clean.** Headers add up, bands anchored, line types legal.
- **Identity holds.** All 26 print ABN `32 416 129 034` in the text layer, supplier
  **Heritage Tree Services Pty Ltd ATF Rowan Family Trust**.
- **No overlap** with any of the 17 batches already in this repository, so no rule 12 question arises.
- 26 documents over 52 pages, one invoice plus one payment advice each.

## 3.0 Also held on the same ground as the other 16-Sep-2026 batches

**No document retains `page_text`**, so `pswp_shingle_check.py` returns **UNVERIFIABLE**: the only
haystack is the captured text itself and the test cannot fail. The binder `Heritage.pdf` (52 pages) was
not supplied, so neither the verbatim fidelity check nor `pbr_mask_screen.py` can be run.

## 4.0 To release it

1. Retype rows 31 (INV-48542) and 33 (INV-48599) and re-gate to GREEN.
2. Supply `Heritage.pdf`, screen it for masked rows, retain the page text and re-run the shingle check
   until it returns PASS.
3. Then the normal capture pipeline.
