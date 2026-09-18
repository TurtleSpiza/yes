# Batch binder1666, cleared to AMBER on 18-Sep-2026. Not yet captured.

141 pages, 100 documents, 7 suppliers. Declared AMBER on arrival; the gate computed **RED**, twice, on two
different documents. Both are now restated from their source pages and the corpus computes **AMBER**, which
under 13.0 builds while holding the named documents.

| | as received | after R1666-1 | after R1666-2 |
|---|---|---|---|
| gate computed | RED | RED | **AMBER** |
| captured ex GST | $599,063.81 | $599,321.21 | **$599,589.21** |

    python3 batches/binder1666/pswp_header_restate.py     # R1666-1, 30 documents
    python3 batches/binder1666/restate_woodmans.py        # R1666-2, Woodmans 6431345
    python3 toolkit/pswp/pswp_corpus_gate.py batches/binder1666/corpus_binder1666_v7_5.json

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

## Woodmans 6431345, page 48: cleared, and it changed the standard

Zero priced lines, no table header, no bands, subtotal recorded $0.00 and total $39.99, which is the first line
item's unit price. The face prints GST Ex Total $268.00 and GST Inc Total $290.80 over seven rows. Nothing fired
on it before v7.2 because P1 required a non-zero recorded subtotal, so recording zero disarmed it, and P11 only
fires where priced lines exist.

It could not be restated from retained text: `line_text` is truncated at the right edge, the Total Inc column is
cut from every item row and the totals read `$268.0` and `$290.8`. **Page 48 was supplied on 18-Sep-2026** and
is retained here as `Pages_from_Binder1666_p48.pdf`.

**The line ex-GST is the printed Total Inc GST less the printed GST, not quantity times the unit price.** That
distinction was the whole of the ambiguity: on the rake, 2 x 22.27 is 44.54 and Inc less GST is 44.55, and only
the second reconciles. Derived that way all three printed totals tie exactly with nothing left over: $268.00,
$22.80 and $290.80. `restate_woodmans.py` applies R1666-2 and asserts all three before writing.

**It is also a mixed supply, and that changed P16.** B601927 carries GST 0.00 on a $39.99 line, so a tenth of
the $268.00 subtotal is $26.80 against a printed $22.80, and P16 as written failed a correct invoice. Prompt
5.6 already covered the case in prose and nothing enforced it. **v7.5 exempts a document whose priced lines each
print a GST amount that sums to the printed GST.** On this corpus the exemption is discriminating: it clears
Woodmans and leaves all 58 of the real derived-GST flags standing.

The truncated totals rows are restated from the page verbatim and typed TOTALS, and `header_sources` is
repointed at them, because P17 was right to fail citations to rows that did not print the figures.

## Findings that stay open

97 documents hit **F8** (citation drift), because the bank block interleaves with the totals block on Levai,
Savco and Higgins and the extractor typed the shared rows by their left-hand label. F8 is AMBER, not a
pathology: either re-run the ladder typing or carry the 97 as Open Items at the build.
