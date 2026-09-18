# Extraction prompt: history and assessment, to 18-Sep-2026

Written for review. It records what each version of `PSWP_Extraction_Prompt` changed, what evidence forced the
change, what the change caught, and where the standard is still weak. Every figure here is reproducible from the
corpora in `batches/` and the gate in `toolkit/pswp/pswp_corpus_gate.py`.

**Verdict.** The prompt is now a genuinely checkable standard: seventeen pathologies, eight findings, and a gate
that computes the verdict from the corpus rather than trusting the one declared. Three of the last four
amendments were forced by a corpus that had declared itself clean, and the pattern is worth scoping precisely:
**every pathology in this prompt, P1 to P17, was written after a defect shipped.** The amendments since are a
different pattern and the more important one: **the standard has begun predicting its own defects, and the first
three predictions were all right.** v7.4's two structural amendments came out of assessing the standard with no
corpus behind them. v7.5 is stronger still: the conflict between P16 and 5.6 was named in review BEFORE Woodmans
page 48 arrived, and the page then produced exactly that failure, one GST-free line and P16 failing a correct
invoice. The third is the strongest, because it predicted the side effect of a FIX rather than a defect in the original:
review said that demoting on the description layer would take GREEN off every corpus including the conformance
fixture and leave the 16.4 self-test with no passing reference, and v7.6 withdrew the demotion for exactly that
reason. The claim to make is not that nothing was predicted; it is that prediction started at v7.4 and has not
yet been wrong.

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
| **v7.4** | 18-Sep-2026 | **13.2** the gate applies the checks the corpus could have satisfied, scoped on the FIELD or CONVENTION each check reads, and `prompt_version` becomes mandatory. **10.1 and section 9** `page_text_independent` and `page_text_basis`. **13.0** GREEN now requires a verified description layer, and the RED range is corrected from P1 to P15 to P1 to P17. | Not a corpus. Assessing the standard: an unscoped gate read 31 of 34 corpora RED on fields that did not exist when they were extracted, and the only check that reads a word was unfailable wherever page text had been rebuilt from the capture. |
| **v7.5** | 18-Sep-2026 | **P16 exempts a mixed supply** where the priced lines each print a GST amount summing to the printed GST. | Woodmans 6431345, page 48 of `Binder1666`: $268.00 ex, $22.80 GST, $290.80 inc over seven rows, one GST-free, so a tenth of the subtotal is $26.80 and P16 failed a correct invoice. 5.6 covered it in prose and nothing enforced it. **Predicted in review before the page arrived.** |
| **v7.6** | 18-Sep-2026 | **A standing rule: every uniqueness and completeness check exempts `duplicate_of`** (11.4). **The description layer becomes a separate axis**: it qualifies the gate line rather than demoting it, so GREEN is reachable again. | Four checks had needed that exemption one at a time, P1 and P15 among them, each found by a correct corpus being failed. And demoting on the description layer took GREEN off all 35 corpora at once, including the conformance fixture, which left the 16.4 self-test with no passing reference and gave a clean corpus and a half-built one the same word. |
| **v7.7** | 18-Sep-2026 | **4.7**: 4.4 and 4.5 are two tests, not one at two scopes. 4.4 is global over the amount RECORDED and is P2; 4.5 is windowed and band-scoped over the money PRINTED. The row neither reaches is closed by `pswp_money_screen.py`. **11.12**: `manifest.archival` marks a retained snapshot, which is never a build input and never repaired. | Neither was forced by a corpus. Both were the oldest open items in the document and were worked as debt. The screen then found the hole populated: 108 UNACCOUNTED rows over 24 live corpora, 89 of them the Glascott schedule rows already restated at v7.1 and reading 0 in the `_v7` corpus. And the archival flag showed 5 of the 7 RED corpora were snapshots, so every report of the RED count had overstated the outstanding defects by five. |
| **v7.8** | 18-Sep-2026 | **The audit's findings worked.** A derived header figure gets a defined `header_sources` shape `{"basis": "derived", "row": null}` and P17 exempts it from **both** limbs (9, 13.1). 4.6 ties in `Decimal`. 13.2 gains a scoping row for the description layer. An explicit version **sequence**, 1 to 9, because nine releases share a date. Annexe D names v7.2. | Not a corpus: `prompt_audit.py` running audit prompt v2 over v7.7, returning 0 HIGH, 8 MEDIUM, 3 LOW. Two of the MEDIUMs were figures contradicting figures inside one repository, and on both the gate said neither published number was right. One finding, #27, was **wrong** and is withdrawn in the same release. |

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

## 4. Assessment: two structural weaknesses, 4.1 closed at v7.4 and 4.2 closed at v7.4 then corrected at v7.6

**4.1 The gate cannot tell "extracted before the rule existed" from "failed the rule". FIXED.** Run at the time of writing over the 34
corpora then in `batches/`, 31 read RED, and almost all of them on P11 and P12 alone. No corpus predating v7 carries
`bands_calibrated_on` or `residue_rows`, because neither field existed when it was extracted. Those 1,116 P11s
and 1,188 P12s are a schema gap and say nothing about capture quality, yet they are indistinguishable at the
gate from a genuine failure. **A corpus should record the prompt version it was extracted under and the gate
should apply the check set of that version**, or the RED verdict stops carrying information.

**Closed at v7.4 in 13.2, and corrected in the same release.** The gate reads `manifest.prompt_version`, now
mandatory, and skips a check only where the corpus predates the FIELD or CONVENTION that check reads. The report
names the set it applied.

**The first cut of that fix was itself a loophole and was caught in review.** Scoping on the VERSION a check was
introduced in would let a corpus escape P14, P15 and P16 by declaring v6, none of which needs anything v6 lacks,
so an extraction could dodge three checks by understating itself. The scope is therefore on the evidence:
`bands_calibrated_on` and the `residue_rows` key are v7, `bands` is v6, P17 is v7 because although
`header_sources` is a v6 field every v6 corpus writes `"row": 0` as a placeholder and it is the 9.1 row
convention P17 reads, and P14, P15 and P16 read `doc_kind`, `evidence_stem` and `printed_gst`, which exist from
v5, so they apply to every corpus. P1's v7.2 amendment is not scoped either: a document that parsed nothing was
a parse failure under v5 too.

**The figures, swept 18-Sep-2026 over the 35 corpora now in `batches/`: 7 GREEN, 21 AMBER, 7 RED, split 24 live
at 3 GREEN, 19 AMBER, 2 RED and 11 archival at 4 GREEN, 2 AMBER, 5 RED.** The 31 above
is the unscoped run over the 34 corpora present when 4.1 was written, and the two denominators are not the same
set, so the pair is a before and after of the scoping rule, not a subtraction. Annexe D2 quoted 8 RED, from the
looser version-only scope and a smaller denominator again; that figure is superseded and the annexe says so.

**4.2 Every check tests arithmetic or structure. Only one tests words, and it is optional in practice. FIXED.** P1 to
P17 prove amounts, coverage and citation. The shingle check is the only verbatim test, and it returns
UNVERIFIABLE where the corpus retains no `page_text`. `prep_supplied_corpus.py` rebuilds `page_text` from the
corpus's own `line_text` rows, which makes the check runnable but **unfailable**, because the haystack becomes
the captured text. A corpus can tie to the cent on every invoice and carry a description the page never printed.
On `pages_from_binder1` the binder was supplied, the page text was parsed from the PDF, and the check returned a
real PASS on 583 shingles with 0 unverifiable. That is the only Play Force batch where that is true. **The
standard should say plainly that a corpus captured without the binder has an unverified description layer**,
rather than leaving the distinction inside a helper script.

**Closed at v7.4 in 10.1 and section 9, and corrected at v7.6 in 13.0.** The manifest carries
`page_text_independent`, a boolean, and `page_text_basis`, the sentence. A corpus whose page text was rebuilt
from its own rows reads UNVERIFIED.

**v7.4 made that demote the gate and v7.6 withdrew it.** Demoting took GREEN off every corpus at once, the 16.4
conformance fixture included, which left the self-test with no passing reference and gave a corpus that ties to
the cent the same word as one that stopped mid-binder. The description layer is now a separate axis printed
beside the gate, `GREEN (description layer UNVERIFIED)`, and never changes the word. A boolean and not a phrase,
because the first implementation sniffed the prose for "rebuilt" and read a basis line saying "not rebuilt from
the corpus rows" as a rebuild.

---

## 5. Smaller things a reviewer should look at

1. **P16's tolerance is relative, 1% of the GST or 2c.** A flat 2c flagged 14 legitimate per-line GST rounding
   cases across the held corpora. The relative form flags zero. Worth confirming 1% is not too loose for a small
   invoice: on a $50 invoice it permits 5c.
2. **F8 fired on 96 of 100 documents in `Binder1666`**, recomputed 18-Sep-2026 against gate v12. This line read
   97 and the prompt's F8 row read 68; both were published as current and neither was right, which the audit
   caught as #26. The cause is that the bank block interleaves with the totals block
   on Levai, Savco and Higgins and the extractor typed the shared rows by their left-hand label. A finding that
   fires on 97% of a batch is either a real systemic defect or the wrong test. 4.0 rung 3 already says the money
   decides on an interleaved row, so I read it as the extractor not following the ladder, but it deserves a
   second opinion.
3. **`HEADER` in `mixed_1`**, 8 rows, a mis-typing of `TABLE_HEADER`. Restated under R-M1-1, and the batch's
   remaining line states were then reviewed under v7.7's screen rather than left unexamined.
   **The corpus is clean on the dangerous class: 0 UNACCOUNTED rows.** Its census is 1,388 NARRATIVE, 361
   PRICED, 85 TOTALS, 55 ATTACHMENT and 39 TABLE_HEADER, and `captured_ex_gst` equals the sum of the PRICED
   lines on all 30 documents. What the screen does find is **20 MISTYPE_CANDIDATE rows**, every one a totals
   or header figure typed NARRATIVE (`Amount Due  56,875.13`, `TOTAL  59,795.62`), plus 3 echoes and 13
   exempt. Each is a wrong rung and none of them moves a dollar, so the batch's arithmetic stands.
   **Two limits to state.** The corpus is v5-era, so it carries no `bands` and no `residue_rows`, and P11 and
   P12 are scoped out of it: the band-based half of 4.5 cannot be run on it at all, and the text screen is the
   only evidence there is. And 55 ATTACHMENT rows carry no recorded amount, where rule 16d exists because an
   ATTACHMENT prints one; those are a retype candidate a re-extraction should settle.
4. **13.0 authorised RED only for P1 to P15 while the gate failed corpora on P16 and P17.** Raised in review
   and corrected at v7.4: the range now reads P1 to P17. Worth recording because the gate was enforcing a
   condition the standard did not authorise, which is the same class of defect as a corpus declaring a gate it
   did not compute.
5. **P2 and 4.4 versus 4.2, 4.5 and 13.2. CLOSED at v7.7, section 4.7.** The invariant read globally in 4.4 and
   P2 and the equivalent test was scoped to the residue window in 4.2, 4.5 and 13.2, and v7.1 had resolved the
   case in front of it by adding a type rather than by settling which reading governs. This was the oldest open
   item in the document.
   **They are two tests, and they read different things.** 4.4 reads the amount the corpus RECORDED, so it is
   global: there is no page to look at and no window to need, and the gate enforces it as P2. 4.5 reads the
   money the page PRINTED, so it is windowed and band-scoped, and only the extractor can run it. The window is
   not a weakening of 4.4: ladder rungs 3 and 4 have already typed the totals block and the payment advice, and
   those rows record no amount, so 4.4 never fires on them and 4.5 never looks at them.
   **The row neither reaches** prints money, is typed NARRATIVE and records nothing. `pswp_money_screen.py`
   now finds it from `line_text` with no PDF, and `reports/Money_Screen_v1.md` has the run.
   **The result is the part worth recording.** 108 UNACCOUNTED rows over 24 live corpora, 89 of them the
   Glascott schedule rows already restated at v7.1 and reading 0 in the `_v7` corpus, which is how the screen
   was shown to track a restatement it knew nothing about. **19 open on current corpora and not one a dropped
   line item**: 10 an energy retailer's summary block where the charge values print one row below their labels
   and a $1.2m account balance is not captured at all, 6 a unit price printed with no extended amount, 3 a
   repeat copy typed NARRATIVE instead of DUPLICATE_COPY. The 6 are **correct captures** and an **F2** finding
   worth $5,915.85 about the invoices, which is worth more than the defect would have been.
   **What is still out of reach is named, not glossed.** The screen reads text, not bands, so it cannot tell
   the amount column from the unit-price column, which is exactly why those 6 read UNACCOUNTED.

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

## 7. State at this assessment

- Prompt at **v7.8**, 1,199 lines, read with `wc -l` in the command that printed this. Annexes A, B, C, C1, D,
  D1, D2, D3, D4, D5, D6 in that order; 4.0 to 4.7 and 13.0 to 13.2 in order. The version **sequence** is
  explicit at the head, 1 to 9, because nine releases share 18-Sep-2026 and the dates cannot order them.
  The previous line here said 1,146 against a file of 1,147: stated from memory, which is the error this
  repository has now made four times and which the line above is written to stop making a fifth.
- Gate at **v12** of `pswp_corpus_gate.py`: P1 to P17 scoped on the evidence each check reads, plus the F7, F8,
  `gst_basis` and mixed-supply AMBER limbs, the v7.8 derived-`header_sources` exemption on both P17 limbs, and
  **two qualifiers that never change the verdict**, the description layer and `[ARCHIVAL]`.
- Second screen at **v2** of `pswp_money_screen.py`, which runs the half of 4.5 the gate cannot reach (4.7) and
  now reads `manifest.archival` as the gate does. `reports/Money_Screen_v1.md`.
- Third tool, new: **`toolkit/pswp/prompt_audit.py` v1**, which audits the standard itself. Read-only, no
  network, deterministic, non-zero exit on any HIGH. `audit/PSWP_Prompt_Audit_20260918.md`.
- **35 corpora: 7 GREEN, 21 AMBER, 7 RED**, swept 18-Sep-2026 and reconciled against the files. An earlier
  draft of this section published 37 corpora and 6 GREEN, 20 AMBER, 11 RED. That was written before the
  description-layer demotion was withdrawn and was never re-swept; it is wrong on the denominator and on all
  three counts, and is corrected here rather than left to stand.
- **Split by `manifest.archival`, landed at v7.7 (rule 11.12): 24 live and 11 archival.**

  | | Corpora | GREEN | AMBER | RED |
  |---|---|---|---|---|
  | **Live** | 24 | 3 | 19 | **2** |
  | **Archival** | 11 | 4 | 2 | 5 |
  | Total | 35 | 7 | 21 | 7 |

  **This section's own earlier recommendation said four snapshots. There are 11, and 5 of the 7 RED were among
  them, not four.** Marking them was worth doing for that reason alone: the outstanding-defect count was
  overstated by five, and the count that was meant to fix it was itself wrong.
  **The 2 live RED are one batch:** `playforce_vinton_glascott_20260916` at `_v6` (104 P2, superseded) and
  `_v7` (61 P11, 61 P12, 54 P17). That is the re-extraction this assessment already books, and nothing else is
  outstanding. The 11 archival keep their verdicts, because a verdict on a snapshot is a true statement about
  what arrived; the flag stops it being read as work.
- **Every P15 evidence-stem collision in the repository is in an archival snapshot, and none is being fixed.**
  5 collision groups over 18 documents in `playforce_vinton_glascott_20260916_as_received`, 2 groups over 4 in
  `trees_new_as_supplied`. No live corpus has one. The only live collision, in `ksadasd_v6`, is a
  `duplicate_of` pair and is correctly exempt under rule 11.4.
  **Section 12's tie-break was the published remedy and it is the wrong remedy here.** A snapshot is the record
  of what was received; applying a remedy to it would falsify the record it exists to be, and rule 12 forbids
  re-capturing an audited document in any case. v7.7 says so in section 12 explicitly, because the remedy being
  available in the abstract is how it would have been applied.
- `binder1666` is **captured**, into register **v25**. Page 48 arrived, Woodmans 6431345 was restated under
  R1666-2, and the batch cleared to AMBER. The binder itself then arrived, so the masked-row screen ran clean
  over all 141 pages and the shingle check returned PASS on 987 shingles with 0 unverifiable: description layer
  VERIFIED, one of only two batches here where that is true.
- Register **v25**: control total $5,066,518.69, 620 sighted rows over 613 invoices, 99 of 99 controls TRUE.
- Every ABN across every captured corpus passes the ATO checksum; none equals the LCC bill-to ABN. **Re-run at
  register v25 on 18-Sep-2026 WITH the transaction date**, which is what closes the first of the two
  qualifications this section used to carry: **383 transaction rows over 32 distinct ABNs, every row VALID**,
  so `ABN_NOT_ACTIVE_AT_DATE` and `GST_NOT_REGISTERED_AT_DATE` ran for the first time and passed on every
  invoice date, not merely as at the run date. `reports/ABN_Verification_v25.xlsx`.
  **One qualification remains**: the name match is a similarity test at a 0.86 threshold, a review standard
  rather than an exact match.
  **And one correction.** The audit raised #27 on this paragraph, saying the live corpora carry 33 ABNs against
  32 verified and naming Woodman Beenleigh Pty Ltd as never checked. **Both halves were wrong**: the v24 report
  carries that ABN, and the 33rd value was an **empty string**. One RST Systems document in the held Glascott
  batch records `"supplier_abn": ""`, which counted as a distinct value in the recount. #27 is withdrawn and
  the empty string is carried as #34: an empty string is not an absent field, and no check currently says so.
