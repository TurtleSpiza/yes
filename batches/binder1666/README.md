# Batch binder1666 — RED, HELD on one document. Not captured.

141 pages, 100 documents, 7 suppliers. Declared AMBER; the gate computes **RED**, and under 13.2 the computed
gate stands. **Nothing is built from this corpus** (CLAUDE.md: never build from a RED corpus).

    python3 toolkit/pswp/pswp_corpus_gate.py batches/binder1666/corpus_binder1666_v7_2.json

## Correction to the first reading of this batch

The first pass here reported 60203 as the only failure and said "the other 99 need nothing". **That was wrong.**
41 of the 100 documents carried a pathology and 30 understated their incl-GST value by **$52,390.66**.

The cause was a defect in the P16 this repository shipped: it guarded on `gst > 0` to skip GST-free supplies,
which silently excluded every **negative** GST. That is the precise shape of the defect it was written for.
Twenty-nine documents recorded `printed_gst` as total less subtotal, twenty-eight of them negative (19795
recorded -$1,887.75), and the guard let all twenty-eight through. The check was reported as mutation tested; the
swap case was tested and the negative case never was.

| | reported here first | actually true |
|---|---:|---:|
| documents failing | 1 | 41 |
| understated incl-GST | $257.40 | $52,390.66 |

## The systemic defect: a derived GST hides a wrong total

29 documents recorded `printed_gst` as total less subtotal, which makes the 5.4 addition check pass by
construction whatever the total is, so **P10 was blind by design**.

- **Vinton (B), 26 documents.** The `GST:` label prints with no value in its band and the total was taken from a
  fuel levy line: totals of $6.00, $7.00 and $8.00 against real totals of $1,586.75 to $3,771.61.
- **Heritage, 2 documents.** `Total GST 10%` read as `Total`, the 5.1 trap v6 was written for. INV-48619
  recorded $153.91 against a printed $1,693.00.
- **Tennyson 60203.** Subtotal and GST swapped and the line amount taken from the GST band, $257.40 understated,
  confirmed against the source page `C00309400_2.pdf` retained here.

`pswp_header_restate.py` restated 30 documents and repointed 10 drifted citations from each document's own
retained text, validated twice before writing: subtotal plus GST equals the printed total to the cent, and GST
is a tenth of the subtotal within tolerance. Verified independently here: 30 documents changed, the incl-GST
delta is $52,390.66 exactly, and no restated document fails either test.

## Why it is still RED: Woodmans 6431345, page 48

Zero priced lines, no table header, no bands, subtotal recorded $0.00 and total $39.99, which is the first line
item's unit price. The face prints GST Ex Total $268.00 and GST Inc Total $290.80 over seven rows. Nothing fired
on it before v7.2 because P1 required a non-zero recorded subtotal, so recording zero disarmed it, and P11 only
fires where priced lines exist.

**It cannot be restated from retained text.** The retained `line_text` is truncated at the right edge: the Total
Inc column is cut from every item row and the totals read `$268.0` and `$290.8`. The seven Price-column values
sum to $267.98 against a printed $268.0x, and two rows carry percentage discounts (2.50% and 5.00%) whose
treatment the truncated text does not settle. Reconstructing it would be guessing, which rule 19.2 forbids.

**To clear the batch: supply page 48 of Binder1666**, as page 80 was supplied for Tennyson. Re-extract that one
document under v7.3 with the WOODMANS Annexe A row in hand, re-gate, and the corpus computes AMBER on the 27
derived-GST documents, which builds while holding them.

## Findings that stay open

97 documents hit **F8** (citation drift), because the bank block interleaves with the totals block on Levai,
Savco and Higgins and the extractor typed the shared rows by their left-hand label. F8 is AMBER, not a
pathology: either re-run the ladder typing or carry the 97 as Open Items at the build.
