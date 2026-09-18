# Batch playforce_vinton_glascott_20260916, RED. Needs re-extraction, not more restatement.

61 documents, three suppliers. Extracted under prompt v6, declared GREEN, and it is not. Restatement took it as
far as the retained text allows and the remainder needs the binder and a fresh run under v7.5.

    python3 batches/playforce_vinton_glascott_20260916/restate_schedule_rows.py   # R-PVG-1 and R-PVG-2
    python3 toolkit/pswp/pswp_corpus_gate.py batches/playforce_vinton_glascott_20260916/corpus_playforce_vinton_glascott_20260916_v7.json

## What restatement fixed

**R-PVG-1, the 104 P2 rows.** 103 amount-bearing rows typed NARRATIVE and one DUPLICATE_COPY carrying an
amount. The 103 are not misclassified line items and capturing them as PRICED would be wrong: Glascott prints
ONE site schedule across a set of invoices, every row carrying its own cost account, so on 012192 the single
PK000382 row is the line item and the twenty-five PK000378 rows belong to other invoices in the same set.

That is provable from the corpus without the binder, and the script asserts it before writing: every affected
document ties its printed subtotal EXACTLY on its PRICED rows alone.

| Document | PRICED ties the subtotal | Schedule rows outside it |
|---|---:|---:|
| 012192 | 473.52 | 32,477.92 |
| 012196 | 473.52 | 35,866.01 |
| 012194 | 1,237.66 | 30,167.88 |
| 012199 | 1,237.66 | 25,835.98 |
| 012193 | 30,167.88 | 1,237.66 |

Capturing them would have double counted **$124,347.79**. They are now ATTACHMENT (v7.1 section 9, register rule
16d): amount kept, excluded from the tie. The duplicate-copy amount is nulled per 4.0 rung 2.

**R-PVG-2, the header citations.** All 183 `header_sources` entries recorded a page and left the row null, so
not one header figure could be shown against the row it came from. 129 are repointed to the row whose retained
`line_text` prints the figure. 54 are left null because no unique row prints it, and P17 is allowed to fail
them: guessing which row a figure came from is the defect P17 exists to catch.

## Why it is still RED, and why restatement cannot finish the job

Using ATTACHMENT means declaring v7.1, and **a version is a package**. The moment the corpus claims v7.1 it owes
the rest of v7: `bands_calibrated_on` on every document with priced lines (61 P11) and `residue_rows` emitted
(61 P12), neither of which a v6 extraction ever produced. It cannot have one v7 type without the v7 evidence.

So the choice is real and there is no third option:

- stay at v6, and ATTACHMENT is outside the closed list, so the 103 rows are P13 instead of P2, or
- move to v7.1, and owe the bands, the residue lists and the 54 citations.

**Neither is reachable by restatement**, because bands and a residue test are things only an extraction run can
produce. The batch needs re-extracting from its binder under v7.5. The restated corpus is kept as the head
start: it carries the schedule analysis, the ties that prove it, and 129 repaired citations.
