# Batch binder1666 — RED on arrival, restated to AMBER

141 pages, 100 documents, 7 suppliers. Declared AMBER by the extraction; the gate computed **RED** on arrival,
and under prompt v7 section 13.2 the computed gate stands. One document was at fault. The source page was
supplied, the document is restated from its own retained text against the bands that page prints, and the
corpus now computes **AMBER**, which under 13.0 builds while holding the named documents.

| | as received | restated |
|---|---|---|
| gate computed | RED | AMBER |
| captured ex GST | $599,063.81 | $599,321.21 |

    python3 batches/binder1666/restate_binder1666.py                                  # R1666-1
    python3 toolkit/pswp/pswp_corpus_gate.py batches/binder1666/corpus_binder1666_v7.json

## The one document that fails, and it fails twice

**Tennyson Group 60203, page 80, printed $314.60.** It is the only document of the hundred that records no
`table_headers` and therefore no bands, which is P11. With the amount column never anchored, two things went
wrong on the same page and both are in the capture:

- The item row prints `30212  4  Parks Corflute Signs  286.00  28.60`. The GST column was taken as the line
  amount, so `line_ex_gst` is **28.60** where the row prints **286.00**.
- The header figures were taken off the wrong labelled rows: captured subtotal 28.60, GST 286.00, total 314.60,
  where the face prints Net $286.00, GST $28.60, Total $314.60.

The document therefore understates by **$257.40** and still declared `"self_tie": "TIE"`, because the mis-read
line matches the mis-read subtotal exactly. `header_adds_up` also read true, because 28.60 + 286.00 = 314.60
whichever way round the two are.

That is what P16 was added for (prompt v7.2): the header block adding up does not prove the figures sit on the
right labels, and a swap is invisible to P10. On this corpus P16 fires on exactly this document, and on the
twenty-nine corpora already held it fires on none.

## Everything else is sound

100 of 100 documents at TIE, 141 of 141 pages covered, `residue_rows` present and empty on every document, all
four corpus checks true, doc refs and evidence stems unique, and the captured total reconciles to the manifest
to the cent. 98 of the 100 documents carry bands AND `bands_calibrated_on`. Findings raised: 21 F3 fuel levy,
10 F5 referenced but absent, 7 F4 coding candidates, 2 F1, 1 F7.

Two documents sit at AMBER on a header block that does not add up and is recorded as F1, which is correct
behaviour under 13.0: 19975 out by $137.84 and 6431345 out by $39.99.

## How it was cleared

`C00309400_2.pdf`, the source page, is retained here. It prints the bands that settle the document:

    header row 11   Net Price label [89,97], its value 286.00 at [93,98]   -> amount band [89,98]
                    GST       label [102,104], its value 28.60 at [107,111] -> gst band [102,111]
    priced row 13   '   30212    4   Parks Corflute Signs        286.00        28.60'
    totals          row 26 Net $ 286.00, row 28 GST $ 28.60, row 30 Total $ 314.60

**28.60 spans [107,111] and does not overlap the amount band at all.** A band recorded and calibrated as 4.1
requires would have made the mis-read impossible, which is the whole of P11's case.

`restate_binder1666.py` applies R1666-1 to that one document and nothing else: the line amount and the three
header figures are taken from those bands, the item table's header row is typed TABLE_HEADER, and the bands are
recorded with the priced row they were calibrated against. Every figure is asserted against the retained text
before it is written, so the script fails rather than guesses if the row is not what it expects. The corpus
total rises by exactly $257.40, which is the understatement.
