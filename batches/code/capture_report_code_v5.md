Gate: GREEN

# Capture Report: code

Runtime: A, code-capable. Extraction tool: M365 Copilot, pdftotext layout, Tesseract OCR 5.3.0.
Pathologies: none.
Pages represented: 66 of 66. Documents complete: 22 of 22.
Documents at TIE: 22. Documents at OUT: 0.
Line records by type: {'NARRATIVE': 459, 'BLANK': 597, 'TABLE_HEADER': 22, 'PRICED': 46, 'TOTALS': 66, 'FOOTER': 66, 'OCR_DUPLICATE': 272, 'TERMS': 4488}.
Captured ex GST total: $33,372.54.
Identifiers found: INV-8060, INV-8061, INV-8107, INV-8191, INV-8405, INV-8439, INV-8456, INV-8486, INV-8502, INV-8548, INV-8563, INV-8564, INV-8589, INV-8594, INV-8624, INV-8671, INV-8722, INV-8723, INV-8730, INV-8733, INV-8752, INV-8760. Unclassified identifiers: none.
OCR: 4 pages run as a 5% control sample, 62 not required, 0 not available, 0 outstanding.
Fidelity: every pdftotext layout row was preserved with rstrip only. OCR control-page rows were recorded as OCR_DUPLICATE. No unresolved text-layer omissions were identified.

## Findings
- INV-8564, F4: No valid PK account is printed on the invoice face; the Account field is absent or prints undefined. Amount: $5,011.60.
- INV-8564, F5: Invoice states as per Quote 692442, but the referenced quote is not included in the binder. Amount: $5,011.60.
- INV-8733, F4: No valid PK account is printed on the invoice face; the Account field is absent or prints undefined. Amount: $485.14.

## Runtime A scope

The capture includes text-layer layout extraction, supplier ABN capture from the text layer, a four-page Tesseract OCR control sample, arithmetic tie testing for every invoice, and whole-binder page coverage. Hyperlink targets and PDF annotations were not material to the invoice arithmetic and were not emitted as separate line records.
