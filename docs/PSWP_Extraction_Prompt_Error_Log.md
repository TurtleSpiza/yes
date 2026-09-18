# PSWP extraction prompt: error log

**Standing rule: every error found in or around the extraction prompt is logged here, prior, current and
future.** One row per error, newest at the bottom of its section so the sequence reads forward. An error is
logged whether it was found by a reviewer, by a corpus failing, by a script asserting, or by me noticing.
Nothing is removed once logged; a corrected entry is amended in place and says so.

**What counts as an error here.** Anything that made the standard, the gate, a corpus or a report say
something untrue: a rule that was wrong, a rule that was right and not written down, a check with a hole, a
figure that did not reconcile, an amendment claimed and not landed. A design decision that was later revised
on new evidence is not an error and is not logged; Annexes C to D5 carry those.

**Columns.** `Found` is how it surfaced, which is the part worth reading: the same class of error keeps being
found the same way. `Cost` is what it was worth in dollars or in wrong verdicts where that can be said.

---

## A. Errors in the STANDARD (the prompt itself)

| # | Version | Error | Found | Cost | Fixed |
|---|---|---|---|---|---|
| A1 | v4 | v4 rewrote v3.1 and broke it. | The v5 authors; recorded again in v6. | The whole of v4. | v5 restored it, and "nothing is ever rewritten again" has been a standing rule since. |
| A2 | v6 | **A band recorded as a single offset cannot match a right-aligned money column.** v6 said record the offset where the label begins and allow "a few characters of drift". | The conformance invoice at 16.4: `AMOUNT` ends at column 116, its values at 118 to 120. A left-edge test with drift rejects the rows it exists to catch. | Unknown; every v6 corpus classified on a test that could not work as written. | v7: bands are spans, tested by overlap (4.1, 4.2). |
| A3 | v6 | **No stated order of classification.** "Match totals keywords before priced ones" appeared once, inside 4.3, which applies only when there is no header row. | A totals row carries money in the amount band too, so the order was load-bearing and undeclared. | Unknown. | v7: the 4.0 ladder, one order, every row. |
| A4 | v6 | **GREEN, AMBER and RED were used throughout and defined nowhere.** | Asked what the build should do with an AMBER corpus and finding no answer in the document. | A corpus with a legitimate OUT document could ship GREEN. | v7: the 13.0 truth table. |
| A5 | v6 | **The corpus tied at 2c while the destination workbook checks at 1c** (register rule 17). | Comparing the two standards. | A GREEN corpus could fail the build. | v7: tie at 1c, the 1c to 2c band to AMBER as F7 (6.0). |
| A6 | v7 | **`ATTACHMENT` was in use on 77 rows and in no version of the closed list**, so every one of them read P13. | Running the gate over the 29 corpora already held. | 77 rows RED on a type the branch build depends on. | v7.1: added to the closed list, a ladder rung, and 4.4's "only if" scoped over PRICED and ATTACHMENT. |
| A7 | v7 | **P1 required a non-zero subtotal**, which is a loophole: a document that parsed nothing and recorded subtotal $0.00 passed. | `Binder1666` 6431345: subtotal $0.00, total $39.99 (the first line item's price), zero priced lines, against a printed `GST Ex Total` of $268.00. Every gate slept. | 1 document, and the class. | v7.2: P1 fires whatever subtotal is recorded. |
| A8 | v7 | **No check read the two GST figures against each other.** P10 tests that subtotal + GST = total, which passes by construction wherever GST was derived as total less subtotal. | `Binder1666`: 29 documents recorded `printed_gst` as total less subtotal, so P10 was blind by design. Vinton totals of $6.00 to $8.00 against real totals of $1,586.75 to $3,771.61. | **$52,390.66** understated across 30 documents. | v7.2: P16, P17, F8 and the `gst_basis` rule. |
| A9 | v7.2 | **P1's amendment was over-broad**: it fired on repeated copies, which correctly have zero priced lines because 4.0 rung 2 nulls their arithmetic. | `Pages_from_Binder1`: 96 documents declared GREEN, computed RED on five, all five repeated copies. | 5 false RED. | v7.3: P1 exempts `duplicate_of`. |
| A10 | v7 to v7.4 | **The gate applied checks to corpora that could not have satisfied them.** No corpus predating v7 carries `bands_calibrated_on` or `residue_rows`, because neither field existed. | Running it unscoped: 31 of 34 corpora RED, almost all on P11 and P12 alone. | A RED verdict carrying no information. | v7.4: 13.2, scoped on the evidence each check reads. |
| A11 | v7.4 | **The first cut of that scoping was itself a loophole.** Scoping on the VERSION a check was introduced in let a corpus escape P14, P15 and P16 by declaring v6, none of which needs anything v6 lacks. | Reading my own fix adversarially before shipping it. | None: caught before release. | Scope moved to the FIELD or CONVENTION each check reads. |
| A12 | v7.4 | **13.0 authorised RED only for P1 to P15 while the gate failed corpora on P16 and P17.** | Review. | The gate was enforcing a condition the standard did not authorise. | v7.4: the range reads P1 to P17. |
| A13 | v7.4 | **GREEN was made to require a verified description layer, and became unreachable on every corpus at once**, including the 16.4 conformance fixture. | Review, after the amendment shipped. | The self-test lost its passing reference, so an extractor could no longer tell conformance from a defect, and a clean corpus and a half-built one got the same word. | v7.6: the description layer is a separate axis, reported as a qualifier and never folded into the verdict. |
| A14 | v7 to v7.6 | **Four checks each needed the `duplicate_of` exemption separately**, P1 and P15 among them, each discovered by a correct corpus being failed. | The fourth one. | 4 rounds of false RED. | v7.6: standing rule 11.4, stated once for every uniqueness and completeness check. |
| A15 | v7 to v7.6 | **Annexe A told an extractor the Glascott schedule rows carry no amount**, contradicting rule 16d and the 2.1 fast path. | Reading Annexe A against section 9 while writing D4. | An extractor on the fast path would have done the thing v7.1 was written to stop. | v7.6: the row is corrected and quotes the old wording. |
| A16 | v7 to v7.7 | **4.4 and 4.5 were ambiguous: global or windowed.** The invariant read globally in 4.4 and P2 and the equivalent test was scoped to the residue window in 4.2, 4.5 and 13.2. v7.1 resolved the case in front of it by adding a type rather than settling which reading governs. | Carried open from v7. No corpus forced it; it was worked as the oldest debt. | Unquantified: the hole was real and populated. 108 UNACCOUNTED rows over 24 live corpora. | v7.7: 4.7. They are two tests reading different things, and `pswp_money_screen.py` closes the row neither reaches. |
| A17 | v7 to v7.7 | **A retained snapshot was gated as though live**, so its verdict was read as work outstanding. | Reporting the RED count and finding 5 of the 7 were snapshots. | The outstanding-defect count overstated by five, in every report of it. | v7.7: rule 11.12 and `manifest.archival`. |

---

## B. Errors in the TOOLKIT (checks that did not check)

| # | Script | Error | Found | Cost | Fixed |
|---|---|---|---|---|---|
| B1 | `pswp_corpus_gate.py` | **P16 shipped with a `gst > 0` guard** meant to skip GST-free supplies. It silently excluded every NEGATIVE GST, which is the exact shape of the defect the check was written for. | The web session, reading the code. | It caught 1 of 29 defects on `Binder1666` and I reported the corpus as one document short of clean: **$52,390.66** understated. | The sign-aware version. See C2 for the claim I made about testing it. |
| B2 | `pbr_stage.py`, `pbr_match_table.py` | **Both asserted the DECLARED gate was GREEN**, enforcing a rule the standard does not state, and would block every corpus whose only mark is an unverified description layer. | Reading the assert while fixing something else. | Would have blocked correct corpora. | Both assert on pathologies now. |
| B3 | `pswp_corpus_gate.py` | **P15 fired on a duplicate copy**, the fourth check to need the `duplicate_of` exemption. | A correct corpus being failed. | 1 false RED, and it produced A14. | Standing rule 11.4. |
| B4 | `pswp_line_restructure.py` | `_band_start()` absent, so a v7 `[start, end]` span raised `TypeError`. | The build chain crashing. | A crash, not a wrong answer. | Added. |
| B5 | `pbr_capture.py` | Register check 3 **could not represent a mixed supply**, and the register line derived ex-GST as incl/1.1. | Woodmans. | **$3.64** understated on one line, and a check that could not pass on a correct document. | A mixed-supply variant of check 3. |
| B6 | `pswp_money_screen.py` | The first cut read **156 UNACCOUNTED** with four unnamed false-positive classes in it. | Tracing rows to the page instead of trusting the count. | Would have sent 48 correct captures for restatement. | Four classes named in the output, not filtered silently. 108. |
| B7 | `pswp_money_screen.py` | The first cut of the mixed_new restatement matched a figure row **only when money was ALONE on the row**, so row 42 (`$56,534.10   0   47`, the GST figure beside the site counts) was skipped. It paired four rows, not five, **and reported success**. | The arithmetic assertion, on the next document. | None: caught before writing. It is why the count is now asserted rather than trusted. | Match on a row that STARTS with money; assert the count. |
| B8 | `pswp_shingle_check.py` | **Page text was keyed on the bare page number**, so on a multi-source corpus page 5 of one binder and page 5 of another are the same key. | Supplying both Glascott binders at once: five Play Force documents at binder pages 1 to 16 were tested against the Glascott binder's pages 1 to 16 and reported FAIL. | 5 false FAILs. **The false PASS is the worse half**: two binders sharing boilerplate would have passed the check this script exists to be. | A qualified key `"<source_file>\|<page>"`, and a bare-keyed file is now REFUSED on a multi-source corpus rather than colliding quietly. |
| B9 | `restate_origin_summary.py` | Read `$52.91 Cr` as **positive**. | The arithmetic assertion: the component sum came out $105.82 over the printed subtotal, which is exactly twice $52.91. | None: caught before writing. | A trailing `Cr` negates. |
| B10 | `pswp_mark_archival.py` | Wrote the flag with a `json.load`/`json.dump` round trip, **reserialising all 11 snapshots at a different indent: a 1.3 million line diff over the audit trail**. | `git diff --stat`. | None: reverted before commit. | The key is inserted textually, matching each file's own indentation. A one-line diff per file. |

---

## C. Errors in MY REPORTING (claims that were not true)

These are logged because they are the class the reviewer has caught most often, and because a wrong figure in
a report is as costly as a wrong figure in a corpus.

| # | Claim | What was true | Found |
|---|---|---|---|
| C1 | "The other 99 documents need nothing", on `Binder1666`. | 41 of 100 carried a pathology. | The web session. |
| C2 | P16 was "mutation tested". | The swap case was tested. The negative case never was, and that is the case it shipped broken on (B1). | The web session. |
| C3 | v7.4's amendment was landed. | Only the title and Annexe D2 changed, 18 lines. The amendment did not exist in the body. | The web session. |
| C4 | v7.6's amendment was landed. | The same failure again: the title said "separate axis", 13.0 still demoted, and "separate axis" appeared exactly once in 962 lines, in the title. | The web session. |
| C5 | §4.1's closure paragraph was in the assessment, for three rounds. | A Python `.replace()` whose pattern never matched, failing silently each time. | The web session. Every replacement is now preceded by `assert old in s`. |
| C6 | "6 GREEN, 20 AMBER, 11 RED across 37 corpora", in a commit message. | 7 GREEN, 21 AMBER, 7 RED across 35. The text was written before the description-layer demotion was withdrawn and was never re-swept. | Myself, re-running the sweep after pushing. |
| C7 | "Four snapshots should carry `manifest.archival: true`", in the assessment. | **Eleven**, and 5 of the 7 RED were among them, not four. | Marking them. |
| C8 | "Three P15 stem collisions". | Seven collision groups over 22 documents, every one in an archival snapshot. | Enumerating them to apply the remedy. |
| C9 | The prompt was "946 lines", then "962", then "1,027". | Each was stated from memory rather than from `wc -l`. | The web session, twice. Line counts are now read off the file in the same command that reports them. |

---

## D. What the pattern says

Read down the `Found` column and three things repeat.

1. **A check written for a defect class was tested against one shape of it.** A8, B1, B6, B7. The rule that
   came out of it: a check written for a defect class is tested against **every sign and shape** of that class
   before it is trusted, and a claim of testing names the cases tested.
2. **An amendment was announced before it was written.** A13, C3, C4, C6. The rule that came out of it, now in
   Annexe D4: **no version number changes until the section it names has changed**, and the title is edited
   last. Every figure in a report is read off the file in the same command that reports it.
3. **A scope was narrowed to make a check pass, and the narrowing was the bug.** A7, A10, A11, B1, B8. A guard
   that excludes cases is the first place to look when a check reports clean.

**And one that is not an error but is worth stating.** The assertions in the restatement scripts caught B7 and
B9 before either was written to a corpus. An assertion that proves a pairing against an independent figure is
worth more than a comment saying the pairing looks right.
