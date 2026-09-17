# Batch binder1666 — HELD, RED on arrival

141 pages, 100 documents, 7 suppliers, $599,063.81 ex GST. Declared AMBER by the extraction; the gate computes
**RED**, and under prompt v7 section 13.2 the computed gate stands. Nothing is built from this corpus until it
is re-extracted or restated (CLAUDE.md: a corpus that fails any of its own gates is logged, held and never
part-built from).

    python3 toolkit/pswp/pswp_corpus_gate.py batches/binder1666/corpus_binder1666_as_received.json

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

## To clear it

Re-extract document 60203 alone under v7.2: record the item table's bands, calibrate them against the priced
row, re-read the three header figures by label precedence (5.0) and re-run the gate. The other 99 documents
need nothing.
