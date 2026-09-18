# Batch levai_conformance

The conformance corpus from PSWP_Extraction_Prompt_v7.md section 16.4: T & H Levai INV-38967,
one page, 42 line records, $46,550.00 ex GST, gate GREEN.

It is not a capture batch and nothing is ever built from it. It is the fixture that proves
`toolkit/pswp/pswp_corpus_gate.py` returns GREEN on a corpus that conforms, so a change to the
gate that starts failing conformant work is caught by one command:

    python3 toolkit/pswp/pswp_corpus_gate.py batches/levai_conformance/corpus_LEVAI_CONFORMANCE_v7.json

Since v7.4 it returns **AMBER, exit 1**, on one count and one only: it retains no `page_text`, so its
description layer has never been read against a page. That is true and is worth leaving true, because the
fixture is the prompt's own worked example and the source PDF was never supplied here. Any PATHOLOGY on this
file is a defect in the gate, not in the corpus.

It is also the worked example for the v7 mechanics that v6 got wrong: a band recorded as a span
and calibrated against a real priced row (`bands_calibrated_on`, page 1 row 29), a five-row
wrapped description whose amount prints on the last row of the block, an interleaved row carrying
the bank block on the left and `GST (10%)` on the right typed TOTALS, and `Account: 101 540 21`
and `YOUR REF 715913` excluded as reference tokens rather than read as money.
