# PSWP v5 Capture Report: Mixed 1

## 1.0 Gate

**AMBER**

## 2.0 Runtime and coverage

- Runtime: B, chat-only text-layer extraction.
- Pages represented: 61 of 61.
- Invoice occurrences: 30.
- Unique invoices: 29.
- Exact duplicate occurrences: 1.
- Arithmetic TIE: 30 of 30.
- Unique-document ex-GST total: $1,177,803.37.
- All-occurrence ex-GST total, including the duplicate: $1,188,123.37.

## 3.0 Material findings

1. **Duplicate:** INV-0110 appears on pages 28 to 29 and again on pages 30 to 31. The second occurrence is excluded from the unique-document total.
2. **Invoice 012191 attachment mismatch:** Header subtotal $32,477.92 versus schedule total $32,951.44, difference $473.52 ex GST.
3. **Invoice 012197 attachment mismatch:** Header subtotal $25,217.15 versus schedule total $27,073.64, difference $1,856.49 ex GST.
4. **INV-9360 period anomaly:** Invoice date is 31 March 2026 while descriptions refer to July treatments.
5. **Invoice 158592 text anomaly:** A line-level amount of $81,732.39 conflicts with the printed subtotal, although subtotal, GST and total reconcile.
6. **Invoice 26231 order mix:** Lines reference order numbers 801672, 702342 and 801671.

## 4.0 Scope limitation

The available Runtime B extraction flattened some multi-column layouts. Document boundaries, identifiers and printed totals were captured, however strict row-by-row band evidence, OCR comparison and full shingle fidelity cannot be certified from the available chat text alone. The gate is therefore AMBER, not GREEN.
