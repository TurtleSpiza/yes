# Sighted documents held: Play Force, 16-Sep-2026

**Status: HELD for a future capture batch. Not built from, and they close no identification gap.**

## 1.0 What was supplied

| File | Invoice | Invoice date | Due date | Ex GST | Incl GST | md5 (first 12) |
|---|---|---|---|---:|---:|---|
| `C00220172.pdf` | INV-3884 | not printed | 9 Jul 2025 | $1,222.78 | $1,345.06 | `99ffc96af580` |
| `C00220407.pdf` | INV-4108 | not printed | 04-Aug-2025 | $1,254.10 | $1,379.51 | `168efcb93af3` |
| `C00224575.pdf` | INV-4331 | not printed | 22-Aug-2025 | $1,195.10 | $1,314.61 | `486c9f86e9f5` |
| `C00265987.pdf` | INV-6014 | not printed | 12-Feb-2026 | $1,218.25 | $1,340.08 | `c063c9000ccb` |
| `C00266572.pdf` | INV-6049 | not printed | 13-Feb-2026 | $1,193.69 | $1,313.06 | `d58c05344bcc` |
| `C00302020.pdf` | INV-7980 | not printed | 09-Jul-2026 | $1,240.46 | $1,364.51 | `0efcf99ca392` |

All six are Play Force Australia Pty Ltd, ABN 89 677 476 541, printed in the text layer. Figures are read
from the "Total (Ex. GST)" and "Total (Inc. GST)" lines on the face, and every one reconciles at 10%.
**6 of the 6 print no invoice date on the face**, only a due date; that is a capture note for
whoever extracts them, not a defect in the documents.

## 2.0 Why they are held rather than used

**2.1 Identity is already settled.** PLA073 (Play Force Australia Pty Ltd, ABN 89 677 476 541) is
embedded. None of the six appears in the v20 identification queue, and none is already captured in any
corpus in this repository.

**2.2 What they WOULD add is nature (rule 17), and that needs a capture batch.** A sighted invoice
becomes evidence only through a gated corpus, authored notes and a match table. A raw PDF supplies none
of those, and the coding note is judgement about what the invoice buys.

**2.3 Unlike the Coast2Coast pair, these are materially worth capturing.** The v20 contractor pull puts
Play Force at Spot-check with **345 invoices sighted covering 63% of $1,617,233.22** of AP-ledger spend,
the lowest coverage of any spot-check supplier in the register. The remaining 37% is where six more
sightings actually move the position. Coast2Coast, by contrast, is already at 97%.

## 3.0 To use them

Extract them into a corpus under prompt v6 **retaining the page text**, screen the binder with
`pbr_mask_screen.py`, gate it, run the shingle check against the retained text, then author the rule 18
notes and the match table. All three 16-Sep-2026 corpora omitted `page_text`, which is what made their
verbatim checks unverifiable; do not repeat that here.
