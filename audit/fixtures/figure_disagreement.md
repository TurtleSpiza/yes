# Fixture: two figures for one quantity, both printed as current

Reproduces findings #25 and #26. `prompt_audit.py --root audit/fixtures` reads it.

| Annexe | Claim |
|---|---|
| D2 | a sweep on 18-Sep-2026 over the 35 corpora then held read 7 GREEN, 21 AMBER, 7 RED, and four of the 7 RED are archival snapshots gated as though live |
| D5 | five of the 7 RED are archival |

F8 fired on 97 of 100 documents in `Binder1666`.
On `Binder1666`, 68 documents carried at least one of these.

Expected: two F-class MEDIUM findings. The gate computes 5 archival RED and 96 F8 documents.
