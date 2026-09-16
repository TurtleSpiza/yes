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

1. Retype rows 31 (INV-48542) and 33 (INV-48599) and re-gate to GREEN. This is the only outstanding
   verification item. It needs no binder and no re-extraction. It is deliberately left undone here: the
   repair belongs in a named gate family rather than a hand edit to a corpus, and no existing family
   covers a zero-amount row inside the item table. No shipped corpus carries one, so the family has no
   precedent to follow and wants a decision rather than an invention.
2. Then the normal capture pipeline: author notes, build the match table, register the batch, build.
