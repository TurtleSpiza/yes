# Batch code capture report (supplied corpus, prepared and fidelity-checked, branch v5, 11-Sep-2026)

## 1.0 Gate

**GREEN** in container (`pswp_json_repair.repair_and_gate`, zero repairs, zero pathologies, rule 16 reconciliation clean on all 22). The supplier of the corpus also declared GREEN; rule 19.2 requires the container's own gate, which is what this records.

## 2.0 Source

- `code.pdf`, 66 pages, 22 Play Force Australia Pty Ltd invoices INV-8060 to INV-8760. **The binder itself was not supplied**; what was supplied is the extraction corpus `corpus_code.json` (md5 e256555fc9d22d46a9cce80f8e7bbe3b) and its capture report (`capture_report_code_v5.md`, kept in this folder as received).
- Declared extraction tool: M365 Copilot, pdftotext layout, Tesseract OCR 5.3.0 (4 pages OCR control sample). Every pdftotext layout row is retained as a line record: 6,016 records, of which 46 PRICED, 22 TABLE_HEADER, 66 TOTALS, 66 FOOTER, 459 NARRATIVE, 4,488 TERMS, 272 OCR_DUPLICATE, 597 BLANK.

## 3.0 Preparation (prep_code_corpus.py, four repairs, each restated from the retained rows)

1. **page_text rebuilt** per document from the retained layout rows, so the corpus is self-checking and the capture driver can read printed header fields.
2. **findings restated as text** (the corpus states them as objects).
3. **pk_refs restricted to the PK000000 form.** On INV-8486 and INV-8548 the corpus had taken `Account: 10367833`, the payment block bank account, as a PK. Those two documents print no PK; the register charges PK000411.
4. **invoice_date and due_date restated as ISO** (the corpus prints them as 01-Jul-2026).

## 4.0 Rule 19.2 verbatim fidelity: PASS, against an independent source

The corpus retains no page text of its own, so a shingle check against itself would be circular. Instead every layout row present in all five Play Force documents whose page text this project retained at branch v3 (parsed here from the real PDF, `corpus_mixed_new_26_27_v6.json`) was taken as the fixed template: **220 rows**. All 220 appear verbatim in **all 22** documents of this batch, no document is missing any, and a full 109-row terms page matches as an **identical ordered sequence**. No TERMS, FOOTER or TABLE_HEADER row in this batch is absent from the independent source.

**Scope of the check.** It proves the fixed template and boilerplate are verbatim and the row order is intact. It cannot independently prove the per-invoice description text, which appears on no other document. That rests on three other legs: the retained layout rows, the arithmetic tie on every invoice, and the APLEDGER PLA073 creditor history on the register line. If the binder is supplied later, run the standard per-document shingle check against it.

## 5.0 Register match

22 invoices, $33,372.54 ex GST, one register line each, exact on the printed subtotal, all standard variant. Every line was Play Force at Tier 1 already (creditor history) and is now Confirmed under rule 17. No invoice number is a re-sighting of a branch or PS_WP v127 capture (rule 12).

## 6.0 Findings

1. **INV-8502 prints PK000338, charged PK000388** (Village Green, Logan Village). PK000338 is not a WO Task in the FY2026/27 branch. Same printed-PK pattern as PS & WP Open Item PSWP-83 (INV-8068). Verdict Review.
2. **INV-8564 prints "Account: undefined"** and the only description is "as per Quote 692442"; the quote is not in the binder. $4,556.00 charged to PK000510. Verdict Review, quote to be obtained.
3. **INV-8733 prints "Account: undefined"**; the work-order row names 3922122 MTN Hanlon Park, Tanah Merah, consistent with the charge to PK000023.
4. **INV-8486 and INV-8548** are Division 7 and Division 8 operational playground inspections billed against purchase order 717527 with no Account row printed; 44 and 36 inspections at $99.81 each, charged to PK000411.
5. Open Items B-027 and B-028 carry findings 1 to 3 at branch level.
