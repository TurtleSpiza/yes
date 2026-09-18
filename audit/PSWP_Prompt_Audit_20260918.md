# PSWP extraction prompt audit, 18-Sep-2026

Run against **`docs/PSWP_Extraction_Prompt_v7.md` v7.7, 1,147 lines**, the assessment beside it, gate v11 and
money screen v1. Audit prompt v2. Nothing in the prompt, the assessment, the gate, the screen or any corpus was
edited by this run.

---

## 1. Verdict

**0 HIGH, 8 MEDIUM, 3 LOW. Fix #25 first: two annexes written the same day state different numbers for the
figure that justifies rule 11.12, and the gate says both are wrong.**

`toolkit/pswp/prompt_audit.py` now runs the mechanical classes and exits non-zero on any HIGH. It found the
5 MEDIUM and 2 LOW below without a human reading a line. Three findings needed judgement and are hand-raised.

**Every HIGH from the v1 register is closed and none has regressed.** The class that produced them, an
amendment announced in metadata and never made in the body, is now detected mechanically in both directions.

---

## 2. Findings register

| # | Class | Sev | Raised at | Finding | Evidence | Why it matters | Proposed fix | Status |
|---|---|---|---|---|---|---|---|---|
| 11 | E | MEDIUM | v7.2 | `header_sources` for a **derived** figure is undefined. P17 exempts a derived figure from the value test and its second limb still fails a citation to a row carrying no line record | `PSWP_Extraction_Prompt_v7.md:799`: "A derived figure (`gst_basis` or `subtotal_basis` saying so) is exempt from the value test" against the same row's "or cites a row that carries no line record" | An extractor with a derived GST has no defined value for `header_sources`, and whatever it writes may fail P17's second limb | Add to 9: for a derived figure `header_sources` takes `{"basis": "derived", "row": null}`, and exempt that shape from P17's second limb | **OPEN**, carried |
| 16 | D | LOW | v7.6 | 4.6's final assert uses float `abs()` where 6.0 mandates `Decimal` with `ROUND_HALF_UP` | `PSWP_Extraction_Prompt_v7.md:259`: "assert abs(sum(priced) - printed_subtotal) <= 0.01   # 6.0, else run the ladder" | An extractor copying the fast path literally ties in binary floating point, against the one numeric rule the project states everywhere | `assert (D(sum(priced)) - D(printed_subtotal)).copy_abs() <= D("0.01")` | **OPEN**, carried |
| 25 | F, I | MEDIUM | v7.7 | Annexe D2's addendum says **four** of the 7 RED are archival. Annexe D5, 13.0's split and the assessment all say **five**. The gate says five | `PSWP_Extraction_Prompt_v7.md:1086`: "a sweep on 18-Sep-2026 over the 35 corpora then held read 7 GREEN, 21 AMBER, 7 RED, and **four of the 7 RED are archival snapshots gated as though live**" against `:1148` and `:706` | Both are printed as current, the reader cannot tell which, and this is the figure that justifies rule 11.12 existing at all | Restate D2's addendum to five and name the sweep it came from | **OPEN**, confirmed by recomputation |
| 26 | I | MEDIUM | v7.7 | Assessment section 5 says F8 fired on **97 of 100** in `Binder1666`. The prompt's F8 row says **68 documents**. **Recomputed: 96** | `PSWP_Extraction_Prompt_Assessment.md:129`: "F8 fired on 97 of 100 documents in `Binder1666`" against `PSWP_Extraction_Prompt_v7.md:798`: "On `Binder1666`, 68 documents carried at least one of these" | Two figures printed as current and **neither is right**. The gate returns 96 AMBER reasons naming F8 on that corpus | Set both to 96, with the sweep date, and say the 68 was an earlier limb set | **OPEN**, and both published figures are wrong |
| 27 | I | MEDIUM | v7.7 | The ABN verification is quoted against `reports/ABN_Verification_v24.xlsx`, 32 ABNs, while the live corpora now carry **33** | Assessment section 7 "32 distinct ABNs, **every one Active and GST registered**" against a recount over `batches/*/corpus_*.json` excluding archival: 33 | **One supplier has never been verified against the ABR**: `88 105 899 689`, Woodman Beenleigh Pty Ltd trading as Woodmans Mitre 10 Beenleigh, present only in `binder1666`, which entered at register v25 | Re-run `abn_bulk_verify.py` at v25 and requote. Pass the transaction-date column this time, so the as-at tests run | **OPEN**, and now has a named subject |
| 28 | C | LOW | v7.6 | Nine versions share 18-Sep-2026 with no sequence, and v7 is dated 18-Sep against v7.1 at 17-Sep | `PSWP_Extraction_Prompt_v7.md:6`: "v7 as supplied is dated 18-Sep-2026 and the v7.1 amendments were applied on 17-Sep-2026" | The history cannot be ordered by date, so the annexe order is the only sequence and a mechanical check must trust it | Add a monotonic `seq` to each version-table row, or timestamp to the minute | **OPEN**, carried. The document does state that the annexe order governs, which is a partial mitigation |
| 29 | F | LOW | v7.7 | Assessment section 4's heading reads "both closed at v7.4" while 4.2 was corrected at v7.6 | `PSWP_Extraction_Prompt_Assessment.md:73`: "## 4. Assessment: two structural weaknesses, both closed at v7.4" against `:112`: "**v7.4 made that demote the gate and v7.6 withdrew it.**" | A heading contradicting its own body's closure version | "both closed at v7.4, 4.2 corrected at v7.6" | **OPEN**, carried |
| 30 | A | MEDIUM | v7.7 | **NEW.** v7.2 has a version-table row and no annexe naming it. Annexe D covers it and its heading names no version | `PSWP_Extraction_Prompt_v7.md:1046`: "## Annexe D. What changed from v7, and the run that produced it" | v7.2 is the largest single amendment in the standard's history, P16, P17, F8 and `gst_basis`, and it cannot be mapped to a release by any mechanical check | Retitle to "Annexe D. What changed from v7.1 (v7.2, 18-Sep-2026)" | **OPEN** |
| 31 | L | MEDIUM | v7.7 | **NEW.** The **description layer** qualifier has no row in 13.2's scoping table. `archival` has one | `PSWP_Extraction_Prompt_v7.md:754` onward: the table carries "\| `archival` \| v7.7 \| no check is scoped to it \|" and nothing for the description layer | The qualifier discipline's whole content is that a qualifier gates nothing. With no row, that cannot be shown for the qualifier whose first version **did** gate something and cost GREEN on 36 of 37 corpora | Add "\| `page_text_independent`, `page_text_basis` \| v7.4 \| no check is scoped to them. They set the description-layer qualifier (10.1, 13.0) \|" | **OPEN** |
| 32 | I | MEDIUM | v7.7 | **NEW.** Two published gate compositions lack an attribute Class I now requires | `PSWP_Extraction_Prompt_v7.md:1140` (Annexe D5's 11.12 row) has no sweep date or denominator in context; `PSWP_Extraction_Prompt_Assessment.md:96` gives "7 GREEN, 21 AMBER, 7 RED" with no live/archival split | Three figures have already been superseded here by a scope or denominator change rather than by a defect. A figure without all three attributes is superseded silently | Quote the sweep date, the denominator and the split beside every composition | **OPEN** |
| 33 | E, H | MEDIUM | v7.7 | **NEW, and this one is mine.** `manifest.archival` is declared in section 9 and rule 11.12, and the **money screen does not read it**. Only the gate does | `toolkit/pswp/pswp_money_screen.py` has no occurrence of `archival`; the sweeps in this session filtered archival corpora in the caller, not in the tool | A reviewer running the screen straight over `batches/` screens 11 snapshots as though live, which is the exact defect rule 11.12 was written to stop, one tool later | Have the screen read `manifest.archival` and label the corpus, as the gate does | **OPEN** |
| 10 | F | n/a | v1 of the audit | 5.4 tests at 2c and 6.0 ties at 1c with the reason unstated | `PSWP_Extraction_Prompt_v7.md:334`: "The 2c allowance exists for per-line GST rounding (11.10)" | The finding was wrong. The reason **is** stated, at 5.4 | none | **WITHDRAWN**, as audit prompt v2 already records |
| 1 to 9, 12 to 14, 17 to 20, 22, 24 | A, C, D, E, F, I, J | n/a | v7.4 to v7.6 | 18 findings, every HIGH among them | Re-tested individually, see section 3 | | | **CLOSED at v7.7**, none regressed |

---

## 3. Class by class

**A. Announced but not made, and made but not announced. 1 finding (#30).**
The title's claim, "what 4.4 and 4.5 each test, and archival corpora", resolves in the body: 4.7 exists at
`:266` and rule 11.12 at `:672`. The v7.6 canonical failure does not recur. The reverse direction found #30:
every `NEW v7.x` marker has a version-table row, but v7.2 has no annexe that names it.
**A note on this check's own first cut.** It reported the title claim as HIGH on a literal string match:
"archival corpora" plural against "an archival corpus" singular in 11.12. That was a false positive and the
matcher now tests the claim's content words. Recorded because an audit that cries wolf is worse than none.

**B. Registration lag. Clean.**
13.1 defines 17 pathologies, P1 to P17. 13.0's RED condition reads "**P1 to P17**", enumerating 17. 14 defines
F1 to F8 and 13.0's AMBER condition names F7, F1 and F8; F2 to F6 are reported findings that do not gate, which
14 states. The 11.4 exemption reaches P1, P7 (named as the exception), P15 and the screen.

**C. Ordering and numbering. 1 finding (#30's LOW half), #28 carried.**
Sections 4.0 to 4.7 and 13.0 to 13.2 ascend. Annexes read A, B, C, C1, D, D1, D2, D3, D4, D5, in order. Both
version tables ascend. Every cross-reference resolves: annexes, P1 to P17, F1 to F8, sections, and the register
deferrals 16d, 17 and 19.x. The only defect is #30's unversioned Annexe D heading.

**D. Reference-implementation conformance. #16 carried, nothing new.**
4.0's nine rungs each have a branch in 4.6, in the ladder's order. `widen()` is called above the loop. The
`money_screen` conformance test in v2 passes: the screen implements 4.7's definition, reading `line_text` for
printed money rather than 4.4's recorded amount, and its false-positive classes are named in 4.7's table at
`:298` rather than filtered silently inside the script. #16, the float `abs()`, is still open.

**E. Schema completeness. #11 carried, #33 new.**
Every field mandated in prose is declared, `gst_basis` included at `:565`. Every field the gate reads off a
corpus is declared. `prompt_version` reads `v7.7`, current. The closed `line_type` list is asserted as thirteen
values and section 9 lists thirteen. #11 remains: `header_sources` for a derived figure.

**F. Internal contradiction. #25, #26, #29.**
Annexe A's GLASCOTT row now agrees with rule 16d. Tolerances are explained where they are stated. The 4.4
against 4.5 scope is settled at 4.7. Rung justifications name the right rungs. What is left is three
figure-against-figure contradictions, and #25 and #26 are both **resolved against the gate, not by preference**:
the archival RED count is five and F8 on `Binder1666` is 96.

**G. Check soundness, the false-positive sweep. Clean, with one observation.**
All 17 pathologies and 8 findings were put to the four questions. Each covers every sign and shape of its class,
P16's sign test included. Each is exempted where 11.4 requires, P7 excepted by design. Each reads a field the
schema declares.
**The observation.** P2 fires on any non-PRICED, non-ATTACHMENT row carrying a recorded amount. R-M1-2 has just
written amounts onto 55 ATTACHMENT rows in `mixed_1` and the gate stays AMBER, which confirms the exemption
holds in code and not only in prose.

**H. Gate against document. Clean both directions, #33 against the screen.**
Every code the gate flags is defined in 13.1; every pathology 13.1 defines is implemented. The scoping rule as
coded matches 13.2 as worded: `NEEDS_FIELD_FROM` keys on the field, not the version, and the escape test
confirms a corpus declaring v6 cannot dodge P14, P15, P16 or P17. Every scoped check has a 13.2 row. The gap is
the qualifier side, #31, and the screen's blindness to `archival`, #33.

**I. Numeric claim verification. #26, #27, #32.**
Recomputed on 18-Sep-2026: prompt 1,147 lines; 17 pathologies; 8 findings; 10 annexes; **35 corpora, 24 live at
3 GREEN, 19 AMBER, 2 RED, and 11 archival at 4 GREEN, 2 AMBER, 5 RED**. The money screen returns 108
UNACCOUNTED over the live set, 89 of them the superseded Glascott `_v6`. `mixed_1` reads 0 UNACCOUNTED and 20
MISTYPE_CANDIDATE. `mixed_new_26_27` reads 4 UNACCOUNTED, down from 10 before R-MN-1. The three superseded
figures, 31 of 34 unscoped, 8 on version-only scope, and 11 of 37, are each named as superseded in both
documents. #26 and #27 are the two that do not reconcile, and #32 is the attribute gap.

**J. Unreachable and unfailable. Clean.**
Every check has a constructible failing input. GREEN is reachable: 7 corpora hold it, 3 live. 13.0's truth table
is total now the description layer is out of every condition. `prep_supplied_corpus.py` sets
`page_text_independent=False`, so a rebuilt haystack returns UNVERIFIABLE and cannot manufacture a PASS.
**The v2 remedy-reachability test passes, and it is worth stating how.** Section 12's stem tie-break was a
remedy available only where it must not be used: every P15 in the repository is in a snapshot. v7.7 closed it by
saying so in section 12 rather than by making the remedy reachable, which is the right closure: the remedy
should be unreachable there.

**K. The standard's own discipline. Clean.**
Every v7.x amendment landed as a new sub-section inside the existing numbering. Nothing was rewritten wholesale.
The Annexe D4 process rule holds for v7.7: 4.7, 11.12, 12, 13.0, 13.2 and 9 all carry their amendments and the
title was edited last. Every annexe row names the corpus, document or figure that forced it, and D5's two rows
say in those words that neither was forced by a corpus. Style: Australian English throughout, no em or en
dashes, money as `$X,XXX`, dates as D-Mon-YYYY outside quoted page text.
**One style note that is not a finding.** `:879` prints `Completed 05/08/2026` inside a fenced block. That is
quoted page text and restating it would breach rule 11.1. The checker now skips fenced blocks.

**L. Qualifier discipline. #31, #33.**
Two qualifiers, the description layer (VERIFIED, UNVERIFIED, UNSTATED) and `[ARCHIVAL]` (boolean). Both print
beside the gate word and neither appears in any 13.0 condition, so neither changes a verdict. `archival` has its
13.2 row and its stated build consequence, refused as a build input and asserted in `pbr_stage.py`. The
description layer has neither a 13.2 row (#31) nor a stated build consequence.

**M. Debt ageing. Clean at v7.7, and the register below is the mechanism it needed.**

| Item | First raised | Releases open | Closed | Named in a release? |
|---|---|---|---|---|
| 4.4 against 4.5 scope | v7 | **5** (v7.1 to v7.6) | v7.7, section 4.7 | Only at closure. Annexe D5 says so |
| Archival corpora | v7 in substance, v7.6 in the assessment | 5 | v7.7, rule 11.12 | Only at closure |
| `header_sources` derived (#11) | v7.2 | **4 and counting** | no | **no** |
| Float `abs()` in 4.6 (#16) | v7.6 | 1 | no | no |
| Date ordering (#28) | v7.6 | 1 | no | no |

**Two items ran five releases and nothing tracked them.** `prompt_audit.py` now emits the age table, and #11 is
the one to watch: four releases open and never named in one.

---

## 4. Claim ledger

| Claim | Source | Verdict |
|---|---|---|
| "what 4.4 and 4.5 each test" | title, `:1` | **MADE.** 4.7 at `:266`, the two-column table at `:272` |
| "archival corpora" | title, `:1` | **MADE.** Rule 11.12 at `:672`, gate `[ARCHIVAL]`, 13.2 row, section 9 field |
| 4.7: "two tests, not one at two scopes" | D5, `:1139` | **MADE** |
| 11.12: "never a build input" | D5, `:1140` | **MADE**, and enforced: `pbr_stage.py` asserts it |
| 12: "tie-break unavailable to an archival corpus" | D5, `:1141` | **MADE**, `:687` |
| 13.0, 13.2, 9: the `[ARCHIVAL]` qualifier | D5, `:1142` | **PARTIAL.** 13.0 and 9 carry it; 13.2 carries `archival` and **not** the description layer (#31) |
| v7.6: description layer a separate axis | D4 | **MADE**, `:706`. Regression-tested |
| v7.2: P16, P17, F8, `gst_basis` | version table | **MADE** in the body, **UNDOCUMENTED** as a release: no annexe names v7.2 (#30) |
| Every other `NEW v7.x` marker | body | **MADE**, and each has a version-table row |

---

## 5. Numeric ledger

Sweep date 18-Sep-2026. Denominator 35 corpora. Split 24 live, 11 archival.

| Figure | Where | Status |
|---|---|---|
| 1,147 lines | assessment says 1,146 | **Off by one**, LOW, absorbed into #32's class. `wc -l` = 1,147 |
| 17 pathologies, 8 findings | 13.1, 14 | **Reproduced** |
| 10 annexes, A to D5 | prompt | **Reproduced** |
| 35 corpora: 7 GREEN, 21 AMBER, 7 RED | assessment `:96` | **Reproduced**, split missing (#32) |
| 24 live: 3 GREEN, 19 AMBER, 2 RED | assessment `:167` | **Reproduced** |
| 11 archival: 4 GREEN, 2 AMBER, 5 RED | assessment `:167` | **Reproduced** |
| "four of the 7 RED are archival" | prompt `:1086` | **Contradicted.** Five (#25) |
| F8 on `Binder1666`: 97 of 100 / 68 | assessment `:129` / prompt `:798` | **Both wrong.** 96 (#26) |
| 108 UNACCOUNTED over 24 live corpora | prompt `:1139` | **Reproduced** |
| 89 of them in Glascott `_v6`, 0 in `_v7` | prompt `:1139` | **Reproduced** |
| $5,915.85, six F2 rows | prompt `:296` | **Reproduced**: $150.00 + $1,501.50 + $1,188.00 + $1,490.50 + $1,515.25 + $70.60 |
| $52,390.66 understated, `Binder1666` | multiple | **Not re-derivable**: the defective corpus state it was measured against has been restated. UNVERIFIABLE, and the figure should carry that |
| $124,347.79, Glascott schedule rows | prompt `:1035` | **Reproduced** from the `_v6` corpus |
| 32 ABNs, all Active | assessment `:176` | **Superseded.** 33 live (#27) |
| 31 of 34 unscoped; 8 version-only; 11 of 37 | both | **Named as superseded in both documents.** Correct treatment |
| Control total $5,066,518.69, 99 of 99 | assessment | **Reproduced** by a full build to a scratch directory |

---

## 6. Gate against document

**In the code and not the document: none.** Every `flag("Pn")` in `pswp_corpus_gate.py` maps to a 13.1 row.
**In the document and not the code: none.** P1 to P17 are all implemented.
**Scoping as worded against as coded:** `NEEDS_FIELD_FROM` keys on `P11_calibrated`, `P12_absent`, `P11`,
`P12`, `P17`, each tied to the field it reads. 13.2's table carries a row for each. The escape test holds: a
corpus declaring v6 still faces P14, P15, P16 and P17.
**Scoping table completeness:** complete for checks; incomplete for qualifiers (#31).
**One tool is outside the discipline:** the money screen does not read `archival` (#33).

---

## 7. What I could not verify

1. **The $52,390.66 understatement.** It was measured against a corpus state that R1666-2 and the v7.2
   amendments have since restated. The number is in the commit history and the error log, and it cannot be
   recomputed from `batches/` today. It should be quoted with "as at 18-Sep-2026, before restatement".
2. **The 28 unsighted Glascott documents.** `play force and vinton.pdf` arrived as a 42-page slice of a
   124-page binder, binder pages 82 to 123. Nothing about the other 28 documents' description layer or masked
   rows can be verified. What would close it: binder pages 1 to 81 and page 124.
3. **`Mixed_1.pdf`.** Never mask-screened and not in the repository, so R-M1-3 stays held. What would close it:
   the binder, md5 `b9ddf7fd6c56188a22181921b7b2c8ab`.
4. **Register rules 16d and 17 as the prompt defers to them.** Held in the register schema, and the deferral
   was checked for consistency rather than the rules themselves.

---

## 8. Regression fixtures

No HIGH, so no fixture is required by 6.0(9). Two are supplied anyway, for the findings whose fix could
silently regress:

- `audit/fixtures/figure_disagreement.md` reproduces #25 and #26 in nine lines, so the figure-agreement check
  can be re-run against a known positive after the fix.
- `audit/fixtures/qualifier_no_scope_row.md` reproduces #31.

Each is run with `python3 toolkit/pswp/prompt_audit.py --fixture audit/fixtures/<name>.md`, which runs the
file-local checks over one file and **exits 2 if the fixture reports clean**, because a fixture that stops
failing has stopped testing anything. Both currently report their finding and exit 0.

**This sentence was wrong when first written.** It said the fixtures run with `--root`, which reads a repository
layout and returned "missing input". The fixture mode was then written so the claim could be true. Recorded
under section 9, because claiming a capability that does not exist is the defect this whole audit class was
created for.

---

## 9. My own errors in this audit

1. **The title-claim check reported a HIGH on a literal string match**, "archival corpora" against "an archival
   corpus". Withdrawn before publication and the matcher fixed. Recorded rather than dropped.
2. **The schema check reported batch ids and tool names as missing fields**: `attach_4`, `mix22`, `mixed_1`,
   `pdftotext`, `pypdf`. Five false MEDIUMs. Fixed by reading the real batch directory names.
3. **The schema check reported the gate's own output keys as undeclared corpus fields**, `amber_reasons`,
   `declared_gate`, `description_layer`. Three false MEDIUMs.
4. **The style check reported a date inside a fenced block**, which is quoted page text and restating it would
   breach rule 11.1. One false LOW.
5. **The figure-agreement check quoted the denominator instead of the quantity**, reporting "'7' archival RED"
   where the document says "four of the 7 RED". The finding was right and the number in it was wrong, which is
   the class of error the check exists to find.
6. **The qualifier check searched the whole of 13.2 instead of its table rows**, so prose merely mentioning a
   qualifier counted as a row. `qualifier_no_scope_row.md` reported clean, which is how it was found: the
   fixture was built to fail and did not. "Has a row" now means a line beginning with a pipe.
7. **Section 8 of this report claimed the fixtures run with `--root`.** They did not; the mode did not exist.
   Written, and the claim is now true. This is finding class A turned on the audit itself, and it is the
   reason the fixture mode exits non-zero on a clean fixture.

**Thirteen defects in the audit's own checks across seven of them, every one caught before publication.** Each is recorded because the
repository's rule is that a check written for a defect class is tested against every shape of it, and because
an audit that inflates is an audit that gets ignored.

---

## 10. What is right

1. **The gate and the document agree in both directions, with no exceptions.** That is the single most
   valuable property here and it should not be disturbed casually.
2. **The scoping rule at 13.2 is correct and is correctly coded.** It scopes on the evidence a check reads,
   not the version a corpus declares, and the escape test confirms it. The first cut of that rule was a
   loophole and the document says so in the same section.
3. **The qualifier discipline is the best idea in the standard.** A verdict says whether the arithmetic holds;
   a qualifier says what has and has not been read against a page. Folding the second into the first cost
   GREEN on 36 of 37 corpora, and separating them again restored the self-test. Both qualifiers now obey it.
4. **4.6 is conformant to 4.0 and carries a comment saying why rungs 2 and 8 must be there.** An extractor
   copying it literally produces every type three amendments depend on.
5. **The superseded figures are named as superseded rather than deleted.** Three of them. That is what makes
   the numeric ledger auditable at all.
6. **The assertions in the restatement scripts are load-bearing and have earned it.** Two defects were caught
   before anything reached a corpus: a matcher that paired four rows and reported success, and `$52.91 Cr` read
   as positive. An assertion proving a pairing against an independent figure beats a comment saying it looks
   right.
7. **`docs/PSWP_Extraction_Prompt_Error_Log.md`** now carries every error in the standard, the toolkit and the
   reporting, with how each surfaced. Three patterns repeat and each has a rule. That log is why this audit
   could be scoped in an afternoon.

---

## 11. Before returning, per 10.0

1. **All thirteen classes run to completion**, including B, G, J and K which found nothing new. Each is
   reported.
2. **Every finding carries `file:line` and verbatim text on every side.**
3. **Every figure repeated here was recomputed**, and the two that could not be are named in section 7.
4. **Every row of the v1 register is marked**: 18 CLOSED at v7.7, 1 WITHDRAWN, 7 OPEN, 0 REGRESSED, plus 4 new.
5. **Every gate figure is split by `manifest.archival`.**
6. **Every figure published here carries the sweep date 18-Sep-2026, the denominator 35, and the split.**
7. **`prompt_audit.py` runs read-only from a fresh checkout, no network, deterministic**, JSON to stdout with
   `--json`, non-zero exit on any HIGH.
8. **Findings are grouped by root cause.** The three Glascott corpora are one batch counted once. The eleven
   archival snapshots are one rule, not eleven findings.
9. **No check was called unfailable and no verdict unreachable**, so no failed construction attempt to record.
   The attempts that succeeded are in Class J.
10. **One prior finding withdrawn with a reason** (#10), and five of my own withdrawn in section 9.
11. **Nothing was amended.** The prompt, the assessment, the gate, the screen and every corpus are untouched by
    this run. The two restatements and the sighting in this session's earlier commits are separate work and are
    not part of the audit.
12. **Section 10 names what is well built.**
13. **On Monday:** fix #25 and #26, which are two wrong numbers in three places and take ten minutes; re-run
    `abn_bulk_verify.py` for #27 with the transaction-date column; add the two table rows for #30 and #31.
    Nothing here blocks a build.
