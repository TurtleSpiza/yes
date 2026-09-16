# Sighted documents held: Coast2Coast, 16-Sep-2026

**Status: HELD for a future capture batch. Not built from, and they close no identification gap.**

## 1.0 What was supplied

| File | Invoice | Pages | md5 |
|---|---|---:|---|
| `C00317296.pdf` | INV-11822 | 1 | `1898049b9d6cf3bd92ce1183f9aaa5e7` |
| `C00313455.pdf` | INV-11823 | 2 | `942db19630309bdcf422701ec3536ae6` |

Both are Coast2Coast Grounds and Gardens, 35 Leahy Road Caboolture, ABN 24 488 420 203, vendor number
COA030, contract PAR/336E/2024.

## 2.0 Why they are held rather than used

**2.1 Identity is already settled, so they add nothing there.** COA030 has been embedded since branch v5
with this ABN. Neither INV-11822 nor INV-11823 appears in the v19 identification queue, because nothing
about this supplier is unidentified.

**2.2 What they WOULD add is nature (rule 17), and that needs a capture batch.** A sighted invoice only
becomes evidence through a gated corpus, authored notes and a match table. A raw PDF supplies none of
those, and the coding note is judgement about what the invoice buys.

**2.3 The supplier is already well covered.** The v19 contractor pull puts Coast2Coast at **Spot-check**,
the lightest route: 4 invoices already sighted covering 97% of $249,377.72 of AP-ledger spend. These two
would raise coverage at the margin, not close a gap.

## 3.0 Carried forward

- **The ABN-format asymmetry stands.** `pbr_build.py` Method 12 already records that Coast2Coast carries
  "24 488 420 203" on the APLEDGER COA030 record and the v5 capture, against "24488420203 (printed
  ungrouped)" from the branch v3 capture. Both of these documents print the grouped form on the face and
  the ungrouped form in the header block, which is the same asymmetry rather than a new one. Column M
  should hold the grouped form on every line and the green block the printed form; canonicalise in both
  registers at the next housekeeping build.
- **INV-11823 prints a $0.00 line** ("Purchase Order: 717532 / Vendor No: COA030 / Reference:
  PAR/336E/2024", quantity 1.00 at 0.00). If this batch is ever captured, that row is F16's case: a
  zero-amount row inside the item table, retyped PRICED so the 4.4 invariant holds without moving value.
