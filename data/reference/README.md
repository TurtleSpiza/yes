# Reference documents

Two Council reference documents and their JSON captures. Both are HELD, not wired into any build: the
register does not read either of them and no control depends on them. They are here because both join to
the register on a key it already carries, and both captures are checked against it.

| Document | Capture | Tool |
|---|---|---|
| `Chart_of_Accounts_Consultancy_FBT_Travel.pdf` | `toolkit/branch/pbr_chart_of_accounts_v1.json` | `pbr_chart_of_accounts.py` |
| `Marsden_Stores_Catalogue_2026.pdf` | `toolkit/branch/pbr_stores_catalogue_v1.json` | `pbr_stores_catalogue.py` |

Re-capture and re-verify:

    python3 toolkit/branch/pbr_chart_of_accounts.py data/reference/Chart_of_Accounts_Consultancy_FBT_Travel.pdf
    python3 toolkit/branch/pbr_chart_of_accounts.py --verify toolkit/branch/pbr_chart_of_accounts_v1.json registers/<newest branch register>.xlsx
    python3 toolkit/branch/pbr_stores_catalogue.py data/reference/Marsden_Stores_Catalogue_2026.pdf
    python3 toolkit/branch/pbr_stores_catalogue.py --verify toolkit/branch/pbr_stores_catalogue_v1.json registers/<newest branch register>.xlsx

## Why they join

**The chart of accounts** carries the full title and the definition of every natural account, plus the FBT
reason codes A to L that decide 73511 against 73512. The register prints the account on every line but only
TechOne's fifteen-character truncation of its name ("Landscapers & G"), so what an account is actually for
is not readable from the register today.

**The stores catalogue** carries the full description, issue unit and category of every product. Every LCC
Stores line on the register is an internal inventory issue narrated

    Despatch Stock Requisition '100231'-ALLSTORE/CHAMBERS/206999/BF42/VEST SAFET-STKISS

so the product number prints in full and the description is cut to ten characters. The stage already types
these lines Tier 1 Confirmed on the system record; the catalogue is what would say the $x was a safety vest
rather than "VEST SAFET".

## Where each capture stands, measured against the register

**Chart of accounts, good enough to use, four rows flagged.** Of the 63 natural accounts this register uses,
62 are in the guide, 58 titles agree with the register's own short description and 57 carry a definition.
74189 Fuel Levy Surcharge is not in the guide at all. The four disagreements are 72113, 73313, 7B122 and
73412; 73412 is the register abbreviating "Refund of Operational Contributions" and is not a defect, the
other three are wrap artefacts on pages that print two account columns side by side.

**Stores catalogue, HELD.** 743 products captured over four printed layouts, and 161 of the 207 register
Stores lines resolve. But only 101 of those agree with the register's own truncated narration: 60 disagree,
some only in naming convention ("VEST SAFET" against "SAFETY VEST L/XL", which is the same vest) and some
genuinely wrong (159601 captured as "AXE" where the register charges a mattock handle, 196341 captured with
no description at all). 46 lines charge 32 products the 2026 catalogue does not list, almost all clothing.
Do not read a description out of this file into anything that ships until the 60 are triaged; the
`--verify` run prints every one of them.
