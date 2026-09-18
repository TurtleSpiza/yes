# Extraction prompt: history and assessment, to 18-Sep-2026

Written for review. It records what each version of `PSWP_Extraction_Prompt` changed, what evidence forced the
change, what the change caught, and where the standard is still weak. Every figure here is reproducible from the
corpora in `batches/` and the gate in `toolkit/pswp/pswp_corpus_gate.py`.

**Verdict.** The prompt is now a genuinely checkable standard: seventeen pathologies, eight findings, and a gate
that computes the verdict from the corpus rather than trusting the one declared. Three of the last four
amendments were forced by a corpus that had declared itself clean, which is the pattern worth noting: **every
check in this prompt was written after a defect shipped, and none was predicted.** The two structural weaknesses
below are what I would want a reviewer to attack first.

---

## 1. Version history

| Version | Date | What changed | What forced it |
|---|---|---|---|
| v3.1 | - | The base standard. | - |
| v4 | - | Rewrote v3.1 and broke it. | Recorded in v5 and again in v6 as the reason nothing is ever rewritten again. |
| v5 | - | Restored the standard and said so. | v4. |
| v6 | 11-Sep-2026 | Made v5's rules **checkable**: the closed line-type list, the residue test, the bands requirement, the pathology codes P1 to P13. | Two v5 runs dropped 34 priced rows between them. Annexe B. |
| **v7** | 18-Sep-2026 | Bands become **spans tested by overlap**, not single offsets. The 4.0 **classification ladder** in one fixed order. **13.0** defines GREEN, AMBER and RED in a truth table. Tie moves to **1c** to match register rule 17. P14 credit-note sign, P15 evidence-stem collision. A conformance corpus, Levai INV-38967. | v6 made the rules checkable and left the test imprecise. On the conformance invoice the `AMOUNT` label ends at column 116 and its values at 118 to 120, so a left-edge test with drift rejects the rows it exists to catch. |
| **v7.1** | 17-Sep-2026 | **`ATTACHMENT`** added to the closed list (rule 16d), a ladder rung for it, and the 4.4 invariant scoped to PRICED **or** ATTACHMENT. | Running the gate over the 29 corpora already held. `ATTACHMENT` was in use on 77 rows and the branch build depends on it, but no prompt version had ever written it down, so every one of those rows read P13. Separately, 103 Glascott schedule rows in `playforce_vinton_glascott_20260916` read P2 although they are correctly outside the tie: all five documents tie exactly on their PRICED rows alone and adding the schedule rows would break every tie by $124,347.79. |
| **v7.2** | 18-Sep-2026 | **P16** GST must be a tenth of the subtotal and must not oppose its sign. **P17** a header figure must be printed on the row its `header_sources` entry cites. **F8** citation drift. The `gst_basis` rule: GST may not be derived silently. **P1 amended**: zero priced lines is P1 whatever subtotal is recorded. | `Binder1666`, declared AMBER. 29 documents recorded `printed_gst` as total less subtotal, which makes the 5.4 addition check pass **by construction whatever the total is**, so P10 was blind by design. Vinton totals of $6.00 to $8.00 against real totals of $1,586.75 to $3,771.61. 30 documents understated their incl-GST value by **$52,390.66**. Woodmans 6431345 parsed nothing at all and recorded subtotal $0.00, which disarmed P1. |
| **v7.3** | 18-Sep-2026 | **P1 exempted** where the document carries `duplicate_of`. | `Pages_from_Binder1`, 96 Play Force documents declared GREEN, computed RED on five. All five were repeated copies inside the binder, every row typed `DUPLICATE_COPY` with null arithmetic, exactly as 4.0 rung 2 requires. The amendment was right about Woodmans and over-broad. |

---

## 2. The check set as it stands

**Pathologies, RED.** P1 nothing parsed. P2 the 4.4 invariant. P3 a page with no line record. P4 the LCC
bill-to ABN read as the supplier's. P5 a missing total. P6 OCR outstanding. P7 duplicate `doc_ref`. P8 a number
as a string. P9 page coverage. P10 the header block adds up. P11 bands recorded and calibrated. P12 the residue
test emitted. P13 the closed list. P14 credit-note sign. P15 evidence-stem collision. P16 GST against a tenth of
the subtotal. P17 a header figure printed on the row it cites.

**Findings, AMBER or reported.** F1 tax-invoice defects. F2 a document that does not support its line. F3 fuel
levy. F4 coding candidates. F5 referenced but absent. F6 duplicates and blanks. F7 a 1c to 2c tie. F8 citation
drift.

**The gate is computed, not declared** (13.2). Where the two differ the computed one stands. On the three
corpora that arrived in the last two days the declared gate was wrong every time: `Binder1666` declared AMBER
and computed RED, `Pages_from_Binder1` declared GREEN and computed RED, and the restated `Binder1666` declared
AMBER and computed RED again on a different document.

---

## 3. What the amendments actually caught

| Check | Caught, on real work | Would the previous version have shipped it? |
|---|---|---|
| P11 bands calibrated | Tennyson 60203: no bands, the GST column read as the line amount, $257.40 understated | Yes. It declared TIE and the tie was internally consistent. |
| P16 GST ratio | 29 documents with a derived GST, **$52,390.66** understated incl-GST | Yes. P10 passes by construction on a derived GST. |
| P17 citation | The Vinton GST citing a row reading `Completed 22/06/2026` | Yes. Nothing read the citation. |
| P1 amended | Woodmans 6431345: zero priced lines, $268.00 of goods, recorded subtotal $0.00 | Yes. P1 required a non-zero recorded subtotal. |
| P13 + ATTACHMENT | 77 rows the build depends on that no prompt had defined | The rows shipped; the gate then wrongly failed them. |
| P1 duplicate exemption | Five correct documents the amended P1 wrongly failed | n/a, this one removed a false positive. |

---

## 4. Assessment: two structural weaknesses — BOTH NOW FIXED (v7.4, 18-Sep-2026)

**4.1 The gate cannot tell "extracted before the rule existed" from "failed the rule". FIXED.** Run today over the 34
corpora in `batches/`, 31 read RED, and almost all of them on P11 and P12 alone. No corpus predating v7 carries
`bands_calibrated_on` or `residue_rows`, because neither field existed when it was extracted. Those 1,116 P11s
and 1,188 P12s are a schema gap and say nothing about capture quality, yet they are indistinguishable at the
gate from a genuine failure. **A corpus should record the prompt version it was extracted under and the gate
should apply the check set of that version**, or the RED verdict stops carrying information. This is the single
change I would make next.

**4.2 Every check tests arithmetic or structure. Only one tests words, and it is optional in practice. FIXED.** P1 to
P17 prove amounts, coverage and citation. The shingle check is the only verbatim test, and it returns
UNVERIFIABLE where the corpus retains no `page_text`. `prep_supplied_corpus.py` rebuilds `page_text` from the
corpus's own `line_text` rows, which makes the check runnable but **unfailable**, because the haystack becomes
the captured text. A corpus can tie to the cent on every invoice and carry a description the page never printed.
On `pages_from_binder1` the binder was supplied, the page text was parsed from the PDF, and the check returned a
real PASS on 583 shingles with 0 unverifiable. That is the only Play Force batch where that is true. **The
standard should say plainly that a corpus captured without the binder has an unverified description layer**,
rather than leaving the distinction inside a helper script.

**Fixed at v7.4.** The manifest carries `page_text_independent`, a boolean, and `page_text_basis`, the sentence
explaining it. A corpus whose page text was rebuilt from its own rows reads UNVERIFIED and cannot be GREEN. It
costs GREEN on almost every corpus here, which is the finding rather than a side effect.

---

## 5. Smaller things a reviewer should look at

1. **P16's tolerance is relative, 1% of the GST or 2c.** A flat 2c flagged 14 legitimate per-line GST rounding
   cases across the held corpora. The relative form flags zero. Worth confirming 1% is not too loose for a small
   invoice: on a $50 invoice it permits 5c.
2. **F8 fired on 97 of 100 documents in `Binder1666`**, because the bank block interleaves with the totals block
   on Levai, Savco and Higgins and the extractor typed the shared rows by their left-hand label. A finding that
   fires on 97% of a batch is either a real systemic defect or the wrong test. 4.0 rung 3 already says the money
   decides on an interleaved row, so I read it as the extractor not following the ladder, but it deserves a
   second opinion.
3. **`HEADER` is still P13 in `mixed_1`**, 8 rows, a mis-typing of `TABLE_HEADER`. Not fixed, because the fix
   belongs in that corpus.
4. **P2 and 4.4 versus 4.2, 4.5 and 13.2.** The invariant reads globally in 4.4 and P2, and the equivalent test
   is scoped to the residue window in 4.2, 4.5 and 13.2. v7.1 resolved the case in front of it by adding a type
   rather than by settling which reading governs. That ambiguity is still in the document.

---

## 6. Errors made in this repository, recorded

Two, both mine, both material.

**P16 shipped with a hole that defeated its own purpose.** The first version guarded on `gst > 0` to skip
GST-free supplies. That silently excluded every **negative** GST, which is the exact shape of the defect it was
written for. It caught 1 of 29 documents on `Binder1666` and I reported the corpus as one document short of
clean, understating the problem by **$52,390.66**. I also described the check as mutation tested: the swap case
was tested and the negative case never was. The web session found it.

**The first `Binder1666` report said "the other 99 need nothing".** 41 of 100 carried a pathology. The lesson
worth keeping is that a check written for a defect class should be tested against **every sign and shape** of
that class before it is trusted, and a claim of testing should name the cases tested.

---

## 7. What the register owner's confirmations changed, 18-Sep-2026

Seven Stores product names were confirmed against the goods. All seven were cases where the machine sources
disagreed, so this is not a fair sample, but it is enough to correct the ranking in section 5:

- The requisition export was **exactly right on none of the seven**; the Marsden inventory on two.
- On **196303** the export names a hard hat browguard with an earmuff attachment. The goods are a face shield
  with a clear visor, a different piece of PPE on the same account.
- On **207353** the export names isopropyl wipes, canister of 75. The goods are baby soap wipes, packet of 80.

So the export remains the best source **on coverage** (163 lines resolved against 117, and 3 absent against 46)
and is **not an authority on the name**. Confirmed names live in `stores_confirmed_products.json` and outrank
both machine sources.

## 8. State at this assessment

- Prompt at **v7.3**, 859 lines, 25 pathology and finding rows, Annexes A to D1.
- Gate at v5 of `pswp_corpus_gate.py`, P1 to P17 plus the F7, F8 and `gst_basis` AMBER limbs.
- 34 corpora, 1,581 documents. Conformance corpus GREEN. `pages_from_binder1` captured into register **v24**.
  `binder1666` RED and held on Woodmans 6431345, which needs page 48 of the binder.
- Every ABN across every captured corpus passes the ATO checksum; none equals the LCC bill-to ABN. Verified
  further against the Australian Business Register on 18-Sep-2026 with `abn_bulk_verify.py`: **32 distinct
  ABNs, every one Active, every one GST registered, every supplier name matched to the ABR record, verdict
  VALID on all 32**. `reports/ABN_Verification_v24.xlsx`.
