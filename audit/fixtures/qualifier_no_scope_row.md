# Fixture: a qualifier with no row in the 13.2 scoping table

Reproduces finding #31.

### 13.2 The gate is computed, not declared

| Evidence a check reads | From | Checks scoped to it |
|---|---|---|
| `archival` | v7.7 | no check is scoped to it. It tags the report, never the verdict |

The description layer is a separate axis and takes three values from 10.1: VERIFIED, UNVERIFIED, UNSTATED.

Expected: one L-class MEDIUM finding, the description layer has no scoping row.
