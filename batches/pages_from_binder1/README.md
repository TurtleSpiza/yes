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

## Not yet captured

Capture is its own build with its own gates. Nothing here has been read into the register.
