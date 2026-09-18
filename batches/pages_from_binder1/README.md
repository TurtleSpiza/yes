# Batch pages_from_binder1 — GREEN, ready to capture

97 pages, 96 documents, one supplier (Play Force Australia Pty Ltd), $222,957.66 ex GST. Declared GREEN and
computes **GREEN** under the v7.3 gate.

    python3 toolkit/pswp/pswp_corpus_gate.py batches/pages_from_binder1/corpus_pages_from_binder1_as_received.json

## It computed RED first, and the gate was wrong

Under v7.2 as received this corpus computed RED on five documents: INV-7978, INV-7983, INV-7985, INV-3856 and
INV-3915, all on "zero PRICED lines". **Every one of the five is a repeated copy of an invoice inside the
binder**, carrying `duplicate_of`, with every row typed `DUPLICATE_COPY` and its arithmetic fields null, which is
exactly what 4.0 rung 2 requires of a duplicate copy and never a parse failure.

The v7.2 amendment to P1 (zero priced lines is P1 whatever subtotal is recorded) was right about Woodmans and
over-broad. v7.3 exempts a document carrying `duplicate_of`. Woodmans 6431345 is not a duplicate and still
fails, so the exemption is discriminating rather than a weakening.

A check that returns sound work is a defect in the check, and this corpus is the evidence.

## Match table built, capture BLOCKED on the binder

`pbr_match_table.py` run against v23: **17 of the 96 documents match a register line**, every one an exact tie
on a Park Services 73123 line narrated "Standing Order 2026/27", variant `standard` on all 17. 5 are duplicate
copies and are skipped. **74 carry no line on this register, $218,185.66 ex GST**, listed in
`outside_pages_from_binder1_v6.json`; the binder is the vendor's own file and is not cut to this register's
year, the same shape as `playforce_new` at v13.

So the capture would add 17 green blocks, not 96.

**It cannot run, and one thing unblocks it: `Pages from Binder1.pdf`.** Two hard rules both need the binder:

1. **The masked-row screen.** `pbr_mask_screen.py --corpus <corpus> <binder.pdf>` must run on every binder
   before capture. A row filled black on the page is not a row the document prints, but the text sits under the
   fill and `pdftotext` returns it, so no text-layer gate can see it. Without the PDF the screen cannot run at
   all.
2. **The verbatim check.** `pswp_shingle_check.py` returns **UNVERIFIABLE** on all 96 documents, because the
   corpus retains no `page_text`: 580 shingles tested, 0 failing, 96 unverifiable. UNVERIFIABLE is not a pass.

`prep_supplied_corpus.py` rebuilds `page_text` from the corpus's own `line_text` rows (line 476). That makes the
shingle check runnable but not independent: the haystack becomes the captured text itself and the test cannot
fail. It satisfies the shape of the rule and not the rule, so it is not used here to manufacture a pass.
