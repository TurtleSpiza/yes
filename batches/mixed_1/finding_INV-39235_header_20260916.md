# Finding: INV-39235 printed total, captured off the wrong labelled row

**Verdict: a capture error in this project's register, now repaired. The supplier invoice is correct and
the TechOne posting is correct. No money moved and no GST was misstated outside our own record.**

## 1.0 What was wrong

`Evidence_Invoices` carried, for T & H Levai Pty Ltd INV-39235 (30-Jun-2026, ABN 65 100 395 480):

| Field | Held | Should be |
|---|---:|---:|
| Ex GST | $33,570.00 | $33,570.00 |
| GST | $3,357.00 | $3,357.00 |
| **Incl GST** | **$33,570.00** | **$36,927.00** |

The incl-GST field repeated the ex-GST figure, so the header was out by **$3,357.00**. It was captured at
branch v2 under Batch `mixed_1` and rode every build from v2 to v20.

## 2.0 What the document actually prints

`Mixed_1.pdf` pages 1 to 2, supplied 16-Sep-2026:

- **Page 1**, foot: `Subtotal 33,570.00`, `GST (10%) 3,357.00`. The page ends there.
- **Page 2**, head: `Total 36,927.00`, `Paid to Date 0.00`, `Balance Due 36,927.00`.

The total prints on the SECOND page, which is what makes this the prompt v6 section 5.2 trap: the
capture took the last labelled figure it could see on page 1 and used it as the total.

## 3.0 Independently corroborated from the ledger

TechOne Document Reconstruction, cross reference 202607011100620000000001, transaction 37101, pulled
16-Sep-2026 (`data/inputs_2026-09-16/reconstructions/`):

| Leg | Ledger | Account | Amount |
|---|---|---|---:|
| 1 | APLEDGER | LEV002 T & H Levai | CR $36,927.00 |
| 2 | 27SLACT | 1-20561-73212 Major Contracts (Quote 657867) | DR $14,670.00 |
| 3 | 27SLACT | 1-20561-73212 Major Contracts (Quote 657861) | DR $18,900.00 |
| 4 | 27GLACT | **1330-1-14211 GST Acquisition** | **DR $3,357.00** |

The GST leg is system generated at "GST Rate Code C Rate Amt 0.1". Council recognised $3,357.00 of input
tax credit against a $33,570.00 expense and paid the creditor $36,927.00. **The posting is correct.**

## 4.0 What it did and did not affect

- **Did not affect** the control total, any register line amount, the section summaries or any report.
  Every register amount is ex GST, and the ex-GST figure was right throughout.
- **Did affect** the printed-total field on `Evidence_Invoices`, which is what a reader checks an invoice
  against, and which the rule 17 header arithmetic is supposed to prove.

## 5.0 Why no gate caught it, and what changed

P10 (the header block must add up) was written into `docs/PSWP_Extraction_Prompt_v6.md` section 5.4 as an
**extractor** obligation. It was therefore tested once, at extraction, by whichever runtime produced the
corpus, and never again. `mixed_1` was extracted before v6 existed, so nothing ever tested it, and
`pswp_json_repair.assess()` emitted P1 to P9 only.

On 16-Sep-2026 P10 was implemented in the gate, so it is now a standing check over every corpus, old and
new, on every run. F1 was extended at the same time: where the header does not add up and the document's
own Balance Due / Total row carries subtotal plus GST exactly, the total is restated from that row, which
is a restatement from the retained text rather than an inference. Here it restated $36,927.00 from page 2
row 57, and the corpus gates GREEN with no pathology. Where no such row is retained, nothing is changed
and P10 fires.
