# Hold record: heritage_tree_services_20260916

**Status: VERIFIED. Ready for capture authoring, not yet built from.** The corpus as received gated RED
on this project's own gate while its capture report claimed GREEN with no pathologies. The two rows are
now repaired by a named gate family and every leg passes.

| Leg | Verdict |
|---|---|
| Gate (`pswp_json_repair`) | **GREEN**, no pathologies, 26 of 26 TIE |
| Arithmetic | $62,940.19 against $62,940.19 |
| Masked-row screen (M1) | **CLEAN**, 0 of 52 pages mask rows |
| Verbatim fidelity (rule 19.2) | **PASS**, 311 shingles against real page text |

The repair is **F16**, added 16-Sep-2026: a $0.00 row sitting inside the item table typed NARRATIVE is
retyped PRICED, which satisfies the 4.4 invariant and moves no value by construction. It fires 26 times
here and clears both pathologies. It also fires on `ksadasd` (36 rows) and `savco_new` (16), and on
neither does any manifest figure change, which is the evidence that it cannot disturb a shipped batch.

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

## 3.0 The other two legs, discharged 16-Sep-2026

The binder arrived. `Heritage.pdf`, 52 pages, md5 `dba3b30377dc4f624c70a1a4f4fee24f`.

| Leg | Verdict |
|---|---|
| Masked-row screen (M1) | **CLEAN**, 0 of 52 pages mask rows |
| Verbatim fidelity (rule 19.2) | **PASS**, 311 shingles against real page text |

Page text is now retained on every document in `corpus_heritage_tree_services_20260916_v6.json`, so the
verbatim check is reproducible rather than circular. **The two P2 rows are the only thing still holding
this batch.**

## 4.0 To release it

Verification is complete. What remains is the capture pipeline, and none of it can be mechanised:
author `notes_heritage_tree_services_20260916_v6.json` (a coding note, verdict and follow-up per invoice,
rule 18), build the match table against the register, add the batch to `BATCHES` in `pbr_stage.py` and
its stamp to `pbr_capture.py`, then run `pbr_build.py`.
