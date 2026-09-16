# Sighted documents held: Environmental Management Unit and Q Power, 16-Sep-2026

**Status: HELD for a future capture batch. Not built from, and they close no identification gap.**
**Every one passes the header and GST tests.**

## 1.0 Environmental Management Unit Pty Ltd, ABN 57 679 181 447 (ENV064)

| File | Invoice | Ex GST | GST | Total | Header | GST rate |
|---|---|---:|---:|---:|---|---|
| `C00319748.pdf` | INV-0645 | $450.24 | $45.02 | $495.26 | adds up | 10% exact |
| `C00318129.pdf` | INV-0640 | $2,251.20 | $225.12 | $2,476.32 | adds up | 10% exact |
| `C00314626_1.pdf` | INV-0621 | $2,251.20 | $225.12 | $2,476.32 | adds up | 10% exact |
| `C00308963_1.pdf` | INV-0569 | $91,232.61 | $9,123.25 | $100,355.86 | adds up | see below |

- **INV-0621 and INV-0569 are already captured** on the register (both in Evidence_Invoices at v21).
  These copies corroborate them; INV-0621 agrees to the cent with what was captured.
- **INV-0569's GST is one cent under 10%** of its subtotal ($9,123.25 charged, $9,123.26 exact). That is
  the per-line rounding case already identified in the FY2026/27 GST audit, and it is lawful.
- **INV-0640 and INV-0645 are new**, and neither appears in the v21 identification queue.
- INV-0640 carries the same figures as INV-0621 ($2,251.20 at 30.00 hours x $75.04, LCC Weed Control).
  Different invoice numbers, same recurring monthly service. Not a duplicate; worth an eye at capture.

## 2.0 Q Power (Qld) Pty Ltd, ABN 82 067 507 591 (QPO001)

Eight invoices, the wide simPRO layout the branch schema already names as a parse template.

| File | Invoice | PK | Ex GST | GST | Total inc GST |
|---|---|---|---:|---:|---:|
| `C00313268 (5).pdf` | 15222 | - | $5,327.94 | $532.79 | $5,860.73 |
| `C00314631 (1).pdf` | 15227 | PK000412 | $555.00 | $55.50 | $610.50 |
| `C00315133.pdf` | 15233 | PK000412 | $835.75 | $83.58 | $919.33 |
| `C00315139.pdf` | 15234 | - | $2,177.80 | $217.78 | $2,395.58 |
| `C00315203.pdf` | 15236 | PK000412 | $469.50 | $46.95 | $516.45 |
| `C00317193 (2).pdf` | 15252 | - | $3,681.68 | $368.17 | $4,049.85 |
| `C00318886 (1).pdf` | 15265 | PK000412 | $647.50 (see note) | $64.75 | $712.25 |
| `C00319916.pdf` | 15267 | PK000441 | $628.75 | $62.88 | $691.63 |

- **All eight add up and all eight carry GST at exactly 10%**, including the half-cent roundings
  ($835.75 to $83.58, $3,681.68 to $368.17, $628.75 to $62.88). None is in the v21 queue.
- **15265 prints no figure on its `Sub-Total ex GST` row**; the value does not land on that layout line.
  Total less GST gives $647.50 and 10% of that is exactly the $64.75 charged, so the document is sound.
  At capture this is F1's existing case, "derive a null subtotal as total less GST".

## 3.0 Why they are held

**Identity is already settled for both.** ENV064 and QPO001 are embedded, and none of the twelve appears
in the v21 identification queue. What these would add is nature (rule 17), which needs a gated corpus,
authored notes and a match table. A raw PDF supplies none of those.

**Neither supplier is a priority.** The v21 contractor pull puts both at Spot-check:

- Environmental Management Unit: 2 invoices sighted covering **96%** of $125,098.79 of AP spend.
- Q Power: 142 invoices sighted covering **87%** of $244,784.71.

Play Force at 63% of $1,617,233.22 remains the batch worth capturing first.

## 4.0 One thing to look at, unrelated to these documents

The v21 contractor pull carries a second Q Power row, **"Q Power (Qld) Pty Ltd (series-inferred)
(flagged)"**, alongside the identified one. A series-inferred label sitting beside a supplier that has an
embedded creditor record and 142 sightings is worth resolving, so the two rows do not double-count the
same counterparty in the pull list.

## 5.0 Method note

The first pass of this triage reported all eight Q Power documents as header mismatches. That was a
regex fault in the triage script, not a fault in the documents: the pattern matched the subtotal figure
for both the ex-GST and the GST field, so every document appeared to have GST equal to its subtotal. The
figures above come from the layout's own labelled rows (`Sub-Total ex GST`, `GST`, `Total inc GST`) and
every one reconciles. Recorded because a false GST finding on eight invoices would have been worse than
none at all.
