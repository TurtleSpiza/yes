# Sighted documents held: T & H Levai, 16-Sep-2026

Eight TechOne C-images, all **T & H Levai Pty Ltd, ABN 65 100 395 480** (LEV002, embedded since branch
v4): INV-39371, INV-39377, INV-39457, INV-39461, INV-39502, INV-39507, INV-39548, INV-39557.

**Status: HELD for a future capture batch.** None is in the `heritage_tree_services_20260916` corpus and
none is captured elsewhere. Identity is already settled, so what they would add is nature (rule 17),
which needs a gated corpus, authored notes and a match table. They are a different supplier from the
Heritage batch built at v22 and belong in their own batch.

## Header and GST tests: all eight pass

Run 17-Sep-2026 against the Levai layout's own labelled rows (`Subtotal`, `GST (10%)`, `Total`).

| Invoice | Date | Ex GST | GST | Total | Header | GST |
|---|---|---:|---:|---:|---|---|
| INV-39371 | 30-Jul-2026 | $480.00 | $48.00 | $528.00 | adds up | 10% exact |
| INV-39377 | 31-Jul-2026 | $480.00 | $48.00 | $528.00 | adds up | 10% exact |
| INV-39457 | 27-Aug-2026 | $482.45 | $48.25 | $530.70 | adds up | 10% exact |
| INV-39461 | 27-Aug-2026 | $489.77 | $48.98 | $538.75 | adds up | 10% exact |
| INV-39502 | 31-Aug-2026 | $480.00 | $48.00 | $528.00 | adds up | 10% exact |
| INV-39507 | 31-Aug-2026 | $600.00 | $60.00 | $660.00 | adds up | 10% exact |
| INV-39548 | 09-Sep-2026 | $480.31 | $48.03 | $528.34 | adds up | 10% exact |
| INV-39557 | 09-Sep-2026 | $480.00 | $48.00 | $528.00 | adds up | 10% exact |

**Eight of eight add up, and eight of eight carry GST at exactly 10%**, including the half-cent roundings
($482.45 to $48.25, $489.77 to $48.98, $480.31 to $48.03). Total $3,972.53 ex GST.

This was recorded because pull request #15 stated these documents passed the header and GST tests before
the tests had been run. They have now been run and the statement holds.

## The layout trap to expect

Same series as INV-39235, the document whose header error produced the P10 gate work on 16-Sep-2026.
Whoever extracts these should retain the page text and expect the two-page layout that put that trap
there: Subtotal and GST print at the foot of page 1, the Total and Balance Due at the head of page 2.
