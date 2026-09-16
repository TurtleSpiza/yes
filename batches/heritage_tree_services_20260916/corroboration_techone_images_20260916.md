# Corroboration: 22 TechOne C-images against the captured Heritage batch

**Every one of the 22 documents supplied on 16-Sep-2026 is already in this batch. None is new, and none
disagrees with what was captured.**

## 1.0 Result

- **22 of 22 are Heritage Tree Services Pty Ltd ATF Rowan Family Trust**, ABN 32 416 129 034 (ENV code
  ARB not applicable; creditor identity already settled).
- **0 are new.** Every invoice number appears in `corpus_heritage_tree_services_20260916_v6.json`.
- **19 parsed on the Xero template and every figure agrees to the cent** with the captured header.
- **3 print their totals on a layout this triage's pattern did not read** (INV-48542, INV-48599,
  INV-48601). Their printed subtotals were read directly and agree: $2,638.44, $2,146.35 and $2,146.35.
- **Header test: all pass.** Subtotal plus GST equals the printed total on every document parsed.
- **GST test: all pass.** Exactly 10% on 21 of 22.

## 2.0 The one apparent exception, which is not an error

**INV-47816** prints subtotal $2,544.21 with GST $254.43, where 10% of the subtotal is $254.42. One cent.

`pbr_match_table.py` classifies this document independently as **"check 2 derivation equality"**: the
register holds $2,544.22 against the printed subtotal $2,544.21, because the printed total $2,798.64
divided by 1.1 is $2,544.2181. That is the settled derivation variant, not a GST error, and the toolkit's
own variant precedence reached it without being told. The GST flag and the match table agree on the same
document and the match table's reading is the correct one.

## 3.0 Match table built

`python3 toolkit/branch/pbr_match_table.py heritage_tree_services_20260916 <v21 register>`

    26 documents matched, 0 held by the rule 12 evidence screen, 0 duplicate copies skipped
    variants: standard 25, check 2 derivation equality 1

**All 26 documents in the batch match register lines.** Nothing is held and nothing is a duplicate.
`match_heritage_tree_services_20260916_v6.json` is written.

## 4.0 Why the contractor pull still shows 24% coverage

The v21 contractor pull puts Heritage at **"Continue the capture": 15 invoices sighted, 24% of
$364,056.85 of AP spend on a green block.** That figure is correct for v21 and regenerating the report
will not change it.

The reason is that this batch is **verified and now fully matched, but not built into the register**. Its
26 sightings do not exist on `Evidence_Invoices` yet, so no report can count them. Only a capture build
moves that number.

## 5.0 What the build still needs, and the one thing that blocks it

Registration in `BATCHES` (`pbr_stage.py`) and a stamp in `pbr_capture.py` are mechanical.
`notes_heritage_tree_services_20260916_v6.json` is not yet written, and one field in it is a live trap.

- **`coding_note` is a restatement**, not a judgement: the trees_new readme states that each note
  restates what the invoice face prints and that no amount is inferred. That is mechanisable here.
- **`nature_category` and `theme_v3` are carried from the register row**, not decided, per the capture
  rule that a capture build proves what a document says and is not a re-categorisation build.
- **The vocabularies do not match, and that is the blocker.** The register's Heritage lines carry Nature
  Category **"Tree operations"** (409 of 410) and Theme group (v3 L1) **"10 Trees & natural areas"** (409
  of 410). The `trees_new` notes file carries `theme_v3` as **"Trees & arboriculture"**, which is neither
  string. Writing the wrong one into a COUNTIF-keyed column is the exact case-variant trap the standing
  rules name, so the value is not guessed here.

## 6.0 A separate finding, on the register rather than these documents

**One Heritage register line out of 410 carries Nature Category "Contract mowing" and Theme group
"2 Park asset maintenance & renewal"**, against "Tree operations" and "10 Trees & natural areas" on the
other 409. On a tree-maintenance contract that reads like a miscoding. A capture build carries the row's
own category unchanged and would not correct it, so it is recorded here as its own question.
