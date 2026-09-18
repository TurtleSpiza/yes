# PSWP audit log, for review

**One file, for a reviewer with no access to this repository.** It carries the audit that was run, what it
found, what has since been fixed, what was found to be wrong, and what is still open. Every figure in it was
recomputed on 18-Sep-2026 and carries its denominator and its live/archival split.

---

## 1. Where the standard stands

| | |
|---|---|
| Prompt | `docs/PSWP_Extraction_Prompt_v7.md` **v7.8**, **1,199 lines** (`wc -l`) |
| Annexes | A, B, C, C1, D, D1, D2, D3, D4, D5, D6, in that order |
| Version sequence | Explicit, 1 to 9. **Nine releases share 18-Sep-2026** and v7 is dated after v7.1, so the dates cannot order the history |
| Gate | `pswp_corpus_gate.py` **v12** |
| Money screen | `pswp_money_screen.py` **v2** |
| Auditor | `prompt_audit.py` **v1**, new |
| Corpora | **35**, swept 18-Sep-2026: **24 live** at 3 GREEN, 19 AMBER, **2 RED**; **11 archival** at 4 GREEN, 2 AMBER, 5 RED |
| The 2 live RED | One batch, `playforce_vinton_glascott_20260916` at `_v6` and `_v7`. Nothing else is outstanding |
| Register | v25, control total **$5,066,518.69**, 99 of 99 controls TRUE |

---

## 2. Verdict on the audit

**Ran audit prompt v2 against v7.7. Returned 0 HIGH, 8 MEDIUM, 3 LOW.**

**All eleven are now resolved: 8 fixed at v7.8, 1 withdrawn as wrong, 2 replaced by narrower findings that are
still open.** `prompt_audit.py` re-run against v7.8 returns **0 HIGH, 0 MEDIUM, 0 LOW**, and both regression
fixtures still fail as designed, so the clean run is not a broken checker.

---

## 3. The findings, and what happened to each

| # | Sev | Finding | Outcome |
|---|---|---|---|
| 11 | MED | `header_sources` had no defined shape for a **derived** figure. P17 exempted a derived figure from the value test and **not** from the row-exists limb | **FIXED v7.8.** Shape `{"basis": "derived", "row": null}`, exempt from both limbs, in section 9, 13.1 and gate v12. **Open four releases, longer than anything else in the schema, and never named in a release** |
| 16 | LOW | 4.6's tie assert used float `abs()` where 6.0 mandates `Decimal` with `ROUND_HALF_UP` | **FIXED v7.8.** `Decimal` with `copy_abs()` |
| 25 | MED | Annexe D2 said **four** archival RED; Annexe D5, 13.0 and the assessment said **five**. Same document, same day | **FIXED v7.8.** Five. The gate decided it, not preference |
| 26 | MED | The assessment said F8 fired on **97** of 100 in `Binder1666`; the prompt's F8 row said **68** | **FIXED v7.8. Recomputed: 96.** Neither published figure was right, and both were printed as current |
| 27 | MED | The ABN verification quoted 32 ABNs while the live corpora carried 33, naming one supplier as never verified | **WITHDRAWN. Wrong in both halves.** See section 4 |
| 28 | LOW | Nine versions share one date with no sequence | **FIXED v7.8.** An explicit `seq` table |
| 29 | LOW | The assessment's section 4 heading said "both closed at v7.4" while its own body said 4.2 was corrected at v7.6 | **FIXED v7.8** |
| 30 | MED | v7.2 had no annexe naming it, and it is the largest amendment in the standard's history | **FIXED v7.8.** Annexe D retitled |
| 31 | MED | The description-layer qualifier had no row in 13.2's scoping table; `archival` had one | **FIXED v7.8.** The row exists |
| 32 | MED | Two published gate compositions lacked a sweep date, a denominator or the split | **FIXED v7.8.** Both carry all three |
| 33 | MED | `pswp_money_screen.py` did not read `manifest.archival`, which the gate had read since v11 | **FIXED, in the toolkit.** v2 reads it. Rule 11.12 already said what a snapshot is; one tool had not been told, which is not a drafting problem |
| **34** | MED | **NEW, replacing #27.** One Glascott document records `"supplier_abn": ""`. An empty string is not an absent field, and no check says so | **OPEN** |
| **35** | MED | **NEW.** 28 of 61 Glascott documents remain unsighted, so the batch cannot clear | **OPEN**, needs binder pages 1 to 81 and page 124 |

---

## 4. The finding I got wrong, in full

**#27 said: the live corpora carry 33 supplier ABNs against 32 in `ABN_Verification_v24.xlsx`, so one supplier
has never been verified against the ABR, namely 88 105 899 689, Woodman Beenleigh Pty Ltd trading as Woodmans
Mitre 10 Beenleigh, present only in `binder1666` which entered at register v25.**

**Both halves are false.**

1. **The v24 report does carry that ABN.** I asserted it did not without opening the file. Reading the
   `Results` sheet: 32 ABNs, and 88105899689 is among them.
2. **The live corpora carry 32 real ABNs, not 33.** The 33rd value was an **empty string**. One RST Systems
   document in the held Glascott batch records `"supplier_abn": ""`, and my recount treated it as a distinct
   value because it filtered on presence, not on shape.

**How it was found:** building the input for the v25 re-run, which returned 32 distinct ABNs where the finding
predicted 33.

**What survived, and it was worth having.** The report was named against register v24 while the register had
moved to v25, and the original run **passed no transaction-date column**, so the as-at tests never ran. That
half is now closed: re-run on 18-Sep-2026 with the date supplied, **383 transaction rows over 32 ABNs, every
row VALID**, so `ABN_NOT_ACTIVE_AT_DATE` and `GST_NOT_REGISTERED_AT_DATE` ran for the first time and passed on
every invoice date rather than merely as at the run date. `reports/ABN_Verification_v25.xlsx`.

**What is left of it is #34**, and it is the better finding: an empty string is not an absent field, and
nothing in the standard or the gate currently distinguishes them.

---

## 5. The audit's own defects, all thirteen

Recorded rather than dropped, because an audit that inflates gets ignored. All were caught before publication
except the two marked.

| # | The audit's check | What it got wrong |
|---|---|---|
| 1 | Class A, title claims | Raised a **HIGH** on a literal string match: "archival corpora" in the title against "an archival corpus" in rule 11.12. The matcher now tests the claim's content words |
| 2 to 6 | Class E, schema | Reported five batch ids and tool names as missing schema fields: `attach_4`, `mix22`, `mixed_1`, `pdftotext`, `pypdf`. Fixed by reading the real batch directory names |
| 7 to 9 | Class E, schema | Reported three of the gate's **own output keys** as undeclared corpus fields: `amber_reasons`, `declared_gate`, `description_layer` |
| 10 | Class K, style | Reported a date inside a fenced block. That is quoted page text and restating it would breach rule 11.1 |
| 11 | Class F, figures | Quoted the **denominator** instead of the quantity: "'7' archival RED" where the document says "four of the 7 RED". The finding was right and the number in it was wrong, which is the class of error the check exists to find |
| 12 | Class L, qualifiers | Searched all of 13.2 instead of its **table rows**, so prose mentioning a qualifier counted as a row. Found because a fixture built to fail reported clean |
| 13 | The report itself | **Published.** Section 8 claimed the fixtures run with `--root`. They did not; the mode did not exist. Written so the claim could be true, and a clean fixture now exits 2 |
| 14 | Line counting | **Published.** `str.split("\n")` returns one extra element on a file ending in a newline, so the auditor said 1,200 against `wc -l`'s 1,199, and would have replaced a count wrong by one with a count wrong by one the other way |

---

## 6. What the audit could not verify

1. **The $52,390.66 understatement on `Binder1666`.** Measured against a corpus state that R1666-2 and the v7.2
   amendments have since restated. It is in the commit history and the error log and cannot be recomputed from
   `batches/` today. It should be quoted "as at 18-Sep-2026, before restatement".
2. **28 Glascott documents.** `play force and vinton.pdf` arrived as a **42-page slice of a 124-page binder**,
   binder pages 82 to 123 at a constant +81 offset. Nothing about the other 28 documents' description layer or
   masked rows can be verified. **What would close it: binder pages 1 to 81 and page 124.**
3. **`Mixed_1.pdf`**, md5 `b9ddf7fd6c56188a22181921b7b2c8ab`. Never mask-screened and not in the repository, so
   restatement R-M1-3 stays held. See section 8.
4. **Register rules 16d and 17** as the prompt defers to them. The deferral was checked for consistency; the
   rules themselves are held in the register schema.

---

## 7. What the two supplied binders bought

| | |
|---|---|
| `97 001 281 572.pdf` | **Complete**, 16 of 16 pages, md5 matches the mask-screen record |
| `play force and vinton.pdf` | **42 pages of 124**, binder pages 82 to 123 |
| Fully sighted | **20** documents |
| Partly sighted | 2, `INV-8009` (page 82 of [80,82]) and `19996` (page 123 of [123,124]) |
| Not sighted | **28** |
| Masked rows | **0 pages** across the slice. 20 documents gain a clean M1 verdict they did not have |
| Verbatim check | **840 shingles, 0 failing, 28 unverifiable.** 33 of 61 documents now VERIFIED |
| Gate effect | **None.** The batch stays RED on P11, P12 and P17, which a re-extraction produces and a sighting does not |

**A toolkit defect found while running it.** `pswp_shingle_check.py` keyed page text on the **bare page
number**. This corpus has two source files each numbered from 1, so five Play Force documents at binder pages 1
to 16 were tested against the **Glascott** binder's pages 1 to 16 and reported FAIL. **The false FAIL is the
better half**: two binders sharing boilerplate would have produced a false PASS on the one check that exists to
catch invented descriptions. Fixed with a qualified key `"<source_file>|<page>"`, and a bare-keyed pages file is
now refused on a multi-source corpus.

---

## 8. The held restatement, and why it is held

**R-M1-3, `mixed_1`.** Split by the PK printed on each schedule row:

| Document | PK000378 rows | Sum | Printed subtotal |
|---|---|---|---|
| 012191 | 25 | $32,477.92 | $32,477.92 |
| 012197 | 27 | $25,217.15 | $25,217.15 |

The PK000378 rows sum to their documents' printed subtotals **to the cent**, so they are those invoices' own
line items, and the single PRICED row reading "Please refer to attached sheet for details." holding the whole
subtotal is what **rule 11.1 calls a critical failure: a summary row in place of line capture**.

**It is held because `Mixed_1.pdf` has never been mask-screened.** The same Glascott schedule page in
`97 001 281 572.pdf` masks the **complementary** rows on invoice 012192: 25 rows worth $32,477.92 against the
$473.52 it prints, over the same 26 rows totalling $32,951.44. So the masking on this binder's copy is an open
question with a **$57,695.07** answer, and a masked row is never captured. **A mask verdict comes from
rendering the page, not from reasoning about it.**

What was done instead: all 55 ATTACHMENT rows were given their printed Ex GST, which section 9 has required
since v7.1. No type changed and every tie is asserted unchanged.

---

## 9. What is well built

1. **The gate and the document agree in both directions, with no exceptions.** Every `flag("Pn")` maps to a
   13.1 row and every pathology 13.1 defines is implemented. That is the most valuable property here.
2. **The scoping rule at 13.2 is correct and correctly coded.** It scopes on the evidence a check reads, not
   the version a corpus declares, and the escape test confirms a corpus declaring v6 cannot dodge P14, P15,
   P16 or P17. The first cut was a loophole and the document says so in the same section.
3. **The qualifier discipline.** A verdict says whether the arithmetic holds; a qualifier says what has been
   read against a page. Folding the second into the first cost GREEN on 36 of 37 corpora. Both qualifiers now
   obey it and both have their 13.2 row.
4. **4.6 is conformant to 4.0**, all nine rungs in order, calibration above the loop, with a comment saying why
   rungs 2 and 8 must be there.
5. **Superseded figures are named as superseded rather than deleted.** Three of them. It is what makes the
   numeric ledger auditable at all.
6. **The restatement scripts' assertions are load-bearing and have earned it.** Two defects were caught before
   anything reached a corpus: a matcher that paired four rows and reported success, and `$52.91 Cr` read as
   positive. An assertion proving a pairing against an independent figure beats a comment saying it looks right.

---

## 10. Open, in the order I would work them

1. **#35, the 28 unsighted Glascott documents.** The only thing blocking a batch. Needs binder pages 1 to 81
   and page 124.
2. **R-M1-3**, needs `Mixed_1.pdf`. $57,695.07 turns on the mask verdict.
3. **#34**, `"supplier_abn": ""`. An empty string is not an absent field and no check says so. Small, and it
   already produced one wrong published finding.
4. **`mixed_new_26_27`**, the detached charge values are paired but a re-extraction should join label to figure
   at capture rather than by restatement. Raised as F1.
5. **The name match threshold**, 0.86 similarity on the ABN verification. A review standard, not an exact
   match, and it is the one qualification left on that claim.

Nothing here blocks a build. The register is at v25, VERIFY CLEAN, control total $5,066,518.69.
