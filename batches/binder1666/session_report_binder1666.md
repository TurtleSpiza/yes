# Capture gate report, Binder1666 (18-Sep-2026)

**Gate: RED. Declared AMBER by the extractor, computed RED, and under prompt 13.2 the computed gate stands. The batch is held and nothing is built from it.**

## 1.0 What the arrival gate found

| | As received | After restatement from retained text |
|---|---|---|
| Computed gate | RED | RED |
| Documents carrying a pathology | 41 of 100 | 1 of 100 |
| P16, GST is not a tenth of the subtotal | 30 | 0 |
| P17, a header figure is not printed on the row it cites | 40 | 1 |
| P11, priced lines with no bands | 1 | 0 |
| P1, zero priced lines on a tax invoice | 1 | 1 |
| Documents carrying F8 citation or typing findings | 97 | 97 |

The extractor's own report declared "Pathologies: none", opened `Gate: AMBER` and closed with "the corpus is GREEN and can proceed to the build session". Three different answers in one document, none of them the computed one.

## 2.0 The systemic failure: a derived GST hides a wrong total

Twenty-nine documents recorded `printed_gst` as the printed total less the printed subtotal. That makes the v7 header check (5.4) pass by construction, because subtotal plus a derived GST equals the total whatever the total is. On every one of them the total was wrong.

- **Vinton (B), 27 documents.** The `GST:` label prints with no value in its band on this layout. The extractor derived the GST and took the total from a fuel levy line: $6.00, $7.00 or $8.00 against real totals of $1,586.75 to $3,771.61. Document 19795 recorded a GST of **-$1,887.75**.
- **Heritage, 2 documents.** `Total GST 10%` was read as `Total`, the 5.1 substring trap that v6 documented after `mix22`. INV-48619 recorded a total of $153.91 against a printed $1,693.00.
- **Tennyson, 1 document (60203).** The only document with no `table_headers` at all, so no bands: the line amount was captured as $28.60, the GST, against a printed Net of $286.00, and the three header figures were read off the wrong labels.

**Money at stake on those 30 documents**

| | Captured | Printed | Difference |
|---|---:|---:|---:|
| GST | -$47,433.15 | $4,837.95 | $52,271.10 |
| Incl-GST value | $826.36 | $53,217.02 | $52,390.66 |

## 3.0 A second parse failure that every v7 gate slept through

Woodmans 6431345, page 48, captured **zero priced lines**, no table header and no bands, and recorded a subtotal of $0.00 with a total of $39.99. The $39.99 is the first line item's price. The document's own retained text prints `GST Ex Total $268.00`, `GST $22.80` and `GST Inc Total $290.80` over seven priced rows.

- **Why nothing fired:** v7's P1 required a non-zero recorded subtotal. Recording the subtotal as zero disarmed it, and P11 only fires where priced lines exist. Recording nothing put every gate to sleep.
- **Consequence:** P1 is amended in v7.2. Zero priced lines on a tax invoice or credit note is P1 whatever subtotal is recorded.
- This document is **held for re-extraction**, not restated: its discount percentages and per-line inc-GST figures cannot be reconstructed from the retained rows without guessing.

## 4.0 What was restated, and what it is worth

`pswp_header_restate.py` restated 30 documents and repointed 10 drifted citations, using only each document's own retained `line_text` (project rule 19.2). Every restatement was validated two ways before it was written: subtotal plus GST equals the printed total to the cent, and the GST is a tenth of the subtotal within the P16 tolerance. On Vinton, two independent labels (`Total (inc-GST):` and `Balance Due:`, plus the how-to-pay page) agreed on the total on all 27.

- Corpus captured ex GST moves from **$599,063.81** to **$599,321.21**, the $257.40 that document 60203 dropped.
- Woodmans adds a further **$268.00** once it is re-extracted.
- The restated corpus computes RED on Woodmans alone, and AMBER on everything else.

## 5.0 Findings carried forward

1. **F8, 97 documents.** Header figures cite rows typed `PAYMENT_ADVICE` or `NARRATIVE`. On Levai, Savco and Higgins the bank block interleaves with the totals block, and this extractor typed the shared rows by their left-hand label. The figures are right; the evidence trail is not. Prompt 4.0 settles the typing: the money decides, so the row is `TOTALS`.
2. **27 documents now carry a declared derived GST** (`gst_basis` recorded, `header_adds_up: "derived"`). That is honest and buildable, but it is not an independently printed GST, and rule 17 check 3 should be run against the derivation, not through it.
3. **6431345 held** for re-extraction under v7.2.
4. **F1, 6431345** is superseded by the P1 above: the header block does not add up because the document was never parsed.
5. **The extractor's F7 on 19975** reads "Self-tie gap 68.92 falls in the 1c to 2c band". A gap of $68.92 is not a 1c to 2c gap; the document's figures were the problem and are now restated to subtotal -$68.92, GST -$6.89, total -$75.81.
6. **Two new templates** are now in Annexe A: TENNYSON and WOODMANS, with their header signatures, amount bands and traps.

## 6.0 To clear the batch

1. Re-extract 6431345 under v7.2 with the WOODMANS Annexe A row in hand.
2. Re-run the ladder typing over the corpus, or accept the F8 findings as AMBER and record them as Open Items.
3. Re-gate. With Woodmans parsed and the typing corrected the corpus computes GREEN, and the 27 derived-GST documents remain AMBER by design until the build session ties them under rule 17.
