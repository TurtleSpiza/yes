Gate: RED

## 1.0 Runtime
Runtime A, code-capable. Extraction used M365 Copilot with `pdftotext -layout`; OCR was not required because every page supplied a usable text layer or was represented as blank/image-only text output.

## 2.0 Pathologies
- P1, INV-3917, page 1: Non-zero printed subtotal with zero PRICED lines.
- P1, INV-3905, page 2: Non-zero printed subtotal with zero PRICED lines.
- P1, INV-3898, page 3: Non-zero printed subtotal with zero PRICED lines.
- P1, INV-3915, page 4: Non-zero printed subtotal with zero PRICED lines.

## 3.0 Coverage and arithmetic
- Pages represented: 140 of 140.
- Documents complete: 61 of 61.
- Documents at TIE: 51; documents at OUT: 10.
- OUT, INV-3917, pages 1 to 1: captured $0.00 against printed subtotal $2,866.50. Rung 1 rows: [].
- OUT, INV-3905, pages 2 to 2: captured $0.00 against printed subtotal $2,821.80. Rung 1 rows: [].
- OUT, INV-3898, pages 3 to 3: captured $0.00 against printed subtotal $2,821.80. Rung 1 rows: [].
- OUT, INV-3915, pages 4 to 5: captured $0.00 against printed subtotal $2,925.70. Rung 1 rows: [].
- OUT, INV-7604, pages 39 to 44: captured $5,725.20 against printed subtotal $2,862.60. Rung 1 rows: [].
- OUT, 012192, pages 4 to 5: captured $32,951.44 against printed subtotal $473.52. Rung 1 rows: [].
- OUT, 012196, pages 6 to 7: captured $36,339.53 against printed subtotal $473.52. Rung 1 rows: [].
- OUT, 012194, pages 8 to 9: captured $31,405.54 against printed subtotal $1,237.66. Rung 1 rows: [].
- OUT, 012199, pages 12 to 13: captured $27,073.64 against printed subtotal $1,237.66. Rung 1 rows: [].
- OUT, 012193, pages 14 to 15: captured $31,405.54 against printed subtotal $30,167.88. Rung 1 rows: [].
- Captured ex GST total: $449,252.94.

## 4.0 Line records
- BLANK: 3.
- FOOTER: 185.
- NARRATIVE: 4,965.
- PAYMENT_ADVICE: 125.
- PRICED: 259.
- TABLE_HEADER: 67.
- TERMS: 2,897.
- TOTALS: 142.

## 5.0 Identifiers
INV-3917, INV-3905, INV-3898, INV-3915, INV-4933, INV-4949, INV-5483, INV-5721, INV-6047, INV-6145, INV-6284, INV-6763, INV-7279, INV-7329, INV-7452, INV-7604, INV-7605, INV-7613, INV-7816, INV-7845, INV-7886, 19795, INV-7977, INV-7978, INV-7982, INV-7983, INV-7984, INV-7985, INV-8009, 19830, 19675, 19873, 19884, 19896, 19902, 19917, 19922, 19927, 19938, 19939, 19943, 19944, 19952, 19961, 19971, 19979, 19980, 19985, 19988, 19996, 011875, 011965, 011964, 012192, 012196, 012194, 012201, 012200, 012199, 012193, 012314

## 6.0 OCR and fidelity
OCR pages run: 0; not required: 140; not available: 0; outstanding: 0. A per-page token multiset audit was not completed, therefore the corpus is RED where the mandatory layout-band or header gates could not be evidenced. Full line records remain in the corpus for repair.

## 7.0 Findings
- INV-3917: No PK reference was identified on the document face. Amount $3,153.15.
- INV-4933: No PK reference was identified on the document face. Amount $3,605.80.
- INV-7604: No PK reference was identified on the document face. Amount $3,148.86.
- INV-7605: No PK reference was identified on the document face. Amount $3,148.86.
- INV-7977: No PK reference was identified on the document face. Amount $3,253.82.
- INV-7978: No PK reference was identified on the document face. Amount $3,778.63.
- INV-7982: No PK reference was identified on the document face. Amount $3,253.82.
- INV-7983: No PK reference was identified on the document face. Amount $3,148.86.
- INV-7984: No PK reference was identified on the document face. Amount $3,673.67.
- INV-7985: No PK reference was identified on the document face. Amount $3,778.63.
- 19896: Fuel levy line printed, verify against the stepped and capped model. Amount $14.92.
- 19902: Fuel levy line printed, verify against the stepped and capped model. Amount $29.85.
- 19917: Fuel levy line printed, verify against the stepped and capped model. Amount $34.70.
- 19922: Fuel levy line printed, verify against the stepped and capped model. Amount $63.83.
- 19927: Fuel levy line printed, verify against the stepped and capped model. Amount $66.24.
- 19927: No PK reference was identified on the document face. Amount $3,771.61.
- 19938: Fuel levy line printed, verify against the stepped and capped model. Amount $44.77.
- 19939: Fuel levy line printed, verify against the stepped and capped model. Amount $45.36.
- 19943: Fuel levy line printed, verify against the stepped and capped model. Amount $43.70.
- 19944: Fuel levy line printed, verify against the stepped and capped model. Amount $55.74.
- 19952: Fuel levy line printed, verify against the stepped and capped model. Amount $59.69.
- 19961: Fuel levy line printed, verify against the stepped and capped model. Amount $66.19.
- 19971: Fuel levy line printed, verify against the stepped and capped model. Amount $54.08.
- 19979: Fuel levy line printed, verify against the stepped and capped model. Amount $54.72.
- 19980: Fuel levy line printed, verify against the stepped and capped model. Amount $80.28.
- 19985: Fuel levy line printed, verify against the stepped and capped model. Amount $59.84.
- 19988: Fuel levy line printed, verify against the stepped and capped model. Amount $59.69.
- 19996: Fuel levy line printed, verify against the stepped and capped model. Amount $54.96.
- 011965: No PK reference was identified on the document face. Amount $39,272.75.
- 011964: No PK reference was identified on the document face. Amount $62,058.77.
- 012314: No PK reference was identified on the document face. Amount $39,409.60.

## 8.0 Resume point
None. Extraction reached the final page of both source files.
