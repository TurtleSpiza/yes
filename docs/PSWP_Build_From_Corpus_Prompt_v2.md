# PSWP build-from-corpus prompt, v2 (9-Sep-2026)

The session-facing procedure named in rule 19.1. It travels in the session zip and is read
from disk when a batch is being built. It is written for the session that holds the corpus,
not for the extraction runtime, which has its own prompt (`PSWP_Extraction_Prompt_v5.md`).

**Read this as an order of operations, not a menu.** Each step gates the next, and the
reason a step exists is stated with it, because a step whose reason is forgotten is a step
that gets skipped on a busy day.

---

## 1.0 Before anything: screen

```
python pswp_dup_screen.py <register.xlsx> --corpus <corpus.json> --files <binder.pdf>
```

Rule 12 is a gate, not a courtesy. md5 the upload against `Data_Acquisition`, and screen
every corpus id, vendor aware, against `Evidence_Invoices` column A.

- **NEW** proceed.
- **RE_SIGHTING** do not re-capture. Audit the existing capture to the cent (subtotal, GST,
  total, priced-line count), record the audit, and drop the document from the build.
- **FALSE_MATCH** the digits collide across vendors. This is a new capture, and treating it
  as a duplicate loses real evidence.
- **COLLISION** the id matches but the printed ABN differs. The ABN decides (rule 8). This
  is a decision for you, not for the script.
- **FILE_SEEN** stop. This binder has been through already.

## 2.0 Repair and gate the corpus

```
python pswp_json_repair.py <corpus.json> --out <corpus_repaired.json> --report <report.md> --strict
```

A corpus that fails any of its own gates is logged, held, and NOT part-built from. A RED
gate is not a reason to build the green documents and leave the rest; it is a reason to
repair or re-extract.

The repaired corpus is the one that ships. Never build from the corpus as delivered once a
repair has been applied to it, or the workbook and the archived corpus will disagree about
what the page said.

## 3.0 Prove the wording, not just the arithmetic

```
python pswp_shingle_check.py --corpus <corpus_repaired.json>
```

A green gate proves amounts. It cannot see a description the page never printed. Every
captured invoice is shingle-checked where page text is retained, one per vendor otherwise
(rule 19.2). A failure here is a re-capture, not a normalisation.

## 4.0 Match to the register

Match by reference on AP lines only, truncation aware, and corroborate on amount. Reference
alone is not identification (rule 12).

Produce a match table keyed by `doc_ref` carrying `target_row`, `target_linekey`,
`target_count`, the zero-amount companions on the same reference, and any other non-zero row
on that reference. **A document that does not resolve to exactly one row is held, not
guessed at.**

## 5.0 Author the brief

This is the step that is yours and cannot be automated. The brief carries:

- **Nature Category**, which must exist in `Theme_Map` A5:A31, and **Nature Detail**, which
  must be specific to that invoice. An empty or generic detail leaves the row Partial, and
  the build refuses the upgrade (rule 17 Amendment 1).
- **The series label**, matching `Vendor_Series` exactly.
- **Check variants**, where the ordinary three checks cannot hold: `check1 inclB`,
  `check2 tol1c`, `check2 deriv`, `check2 split`, `check2 sumtie`, `check3 gstfree`,
  `check3 tol1cgst`, `check3 tol2c`. Declaring one writes the `[check variant]` tag.
- **`doc_type_allowed`**, where a sighted face posts as something other than
  `PUR Cred Invoice`, such as a creditor credit note.
- **`held`**, for anything the evidence does not settle. A held row carries no EvID after
  the build.
- **Handover, Method, Data_Acquisition and Open_Items text**, in your voice, not the
  script's.

## 6.0 Dry run, then build

```
python pswp_build_batch.py <brief.json> --dry-run
python pswp_build_batch.py <brief.json>
```

The dry run costs five seconds and runs every pre-write gate. The build then runs the whole
rule 19.7 chain unattended: write, recalc through the convert route, verify against the
recalculated file, ship only on a clean verify. **A partial run is discarded and re-run from
the top, never resumed.**

Expect roughly 210 seconds end to end on a 24MB workbook.

## 7.0 Audit what you built

```
python pswp_verify.py <shipped.xlsx>
python pswp_bounds_audit.py <shipped.xlsx> --strict
python pswp_shingle_check.py --corpus <corpus_repaired.json> --workbook <shipped.xlsx> --prefixes <prefixes.json>
```

Verify proves the controls. The bounds audit proves the controls are still pointed at the
data, which no control can prove about itself. The shingle check proves the workbook holds
what the page printed.

## 8.0 Report

```
python pswp_session_report.py --brief <brief.json> --match <match.json> \
    --verify <verify.json> --bounds <bounds.json> --build-log <log.txt> --out <report.md>
```

Every figure in the report is read from an artefact, so the report and the workbook cannot
drift apart. One report per session (section 6.10).

## 9.0 After any change to the toolkit

```
python pswp_selftest.py --corpus-red <red.json> --corpus-green <green.json> \
    --workbook <reference.xlsx> --ident-config <ident.json>
```

Thirteen tests, about 100 seconds. The toolkit's own defects were not found by reading it.
They were found by running two independent routes at the same evidence and comparing, and by
feeding a build its own output back. **A change that quietly breaks one of those comparisons
is exactly the change that ships a wrong number behind a green check.**

---

## 10.0 What never happens, whatever the pressure

- No summary row in place of line capture. That is a critical failure, not a shortcut.
- No Confirmed status without all three rule 17 checks returning the literal `"TRUE"`.
- No ABN carried from a matched line onto an inferred one.
- No amount inferred, adjusted, or derived by subtraction to make a tie work.
- No column T written on a capture or identification build. The control total is invariant.
- No `recalc.py`. The convert route is the only sanctioned recalc.
