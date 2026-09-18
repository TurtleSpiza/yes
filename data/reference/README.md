# Reference documents

Two Council reference documents, their source PDFs, and the structured data the register work reads.

| What | File | Basis |
|---|---|---|
| Stores products from the requisition export, 1,235 | `stores_requisition_products.json` | `pbr_stores_resolver.py` over TechOne My Requisition Lines |
| Chart of accounts, 679 accounts | `chart_of_accounts.json` | from the `lcc-coding-review` skill bundle |
| Marsden Stores inventory, 746 items | `marsden_stores_inventory.json` | from the `lcc-coding-review` skill bundle |
| FBT reason codes A to L | `fbt_reason_codes.md` | from the same bundle |
| Source PDFs, retained | `Chart_of_Accounts_Consultancy_FBT_Travel.pdf`, `Marsden_Stores_Catalogue_2026.pdf` | as supplied |

Both are HELD: no build reads either and no control depends on them.

## Three sources name a Stores product, and they are not equal

Scored against the v24 register on the register's own truncated narration:

| Source | agree | disagree | absent |
|---|---:|---:|---:|
| **TechOne requisition export** | **163** | 41 | **3** |
| Stores inventory (skill bundle) | 117 | 44 | 46 |
| Catalogue PDF captured here | 101 | 60 | 46 |

The requisition export wins because it is the record of the issue itself rather than a catalogue of what Stores
sells: it names the 44 clothing and PPE products the 2026 catalogue does not list at all, which is most of what
Parks draws. `JACKET HOODIE Y/N REFLECTIVE 3XL` and `PANTS L/WEIGHT NON REFLECT 112R` appear in no catalogue
here. The residual 41 disagreements are the register truncating the item and the supplier naming the brand
("VEST SAFET" against "Prime Mover 100% Cotton Day/Night Vest"), not a wrong resolution. Only three product
numbers the register charges are absent from the export.

So the export is the resolver, the inventory adds the category, and the PDF capture is last.

    python3 toolkit/branch/pbr_stores_resolver.py verify data/reference/stores_requisition_products.json registers/<newest>.xlsx

## Why the skill data and not the PDF captures

This repository first captured both PDFs with its own parsers, `pbr_chart_of_accounts.py` and
`pbr_stores_catalogue.py`. The `lcc-coding-review` bundle then arrived carrying both already structured, and it
is better on the only test that matters here, which is agreement with the register itself.

| Test, against the v24 register | repo capture | skill data |
|---|---:|---:|
| Stores lines resolved and the narration agrees | 101 | **117** |
| Stores lines resolved and the narration disagrees | 60 | **44** |
| Natural account titles agreeing with the register | 58 | **60** |
| Register accounts carrying a definition | 57 | **62** |

The skill data is therefore the reference, and the parsers stay only as the re-capture route for a NEW PDF.
Both parsers keep a `--verify` mode that scores any capture against the register the same way:

    python3 toolkit/branch/pbr_chart_of_accounts.py --verify data/reference/chart_of_accounts.json registers/<newest>.xlsx
    python3 toolkit/branch/pbr_stores_catalogue.py --verify data/reference/marsden_stores_inventory.json registers/<newest>.xlsx

## Why they join the register

**The chart of accounts.** The register prints a natural account on every line but only TechOne's fifteen
character truncation of its name ("Landscapers & G"). 62 of the 63 accounts this register uses are in the guide
and all 62 carry a definition. **74189 Fuel Levy Surcharge is in neither the list nor the dictionary** and is the
one open question.

**The stores inventory.** Every LCC Stores line is an internal inventory issue narrated

    Despatch Stock Requisition '100231'-ALLSTORE/CHAMBERS/206999/BF42/VEST SAFET-STKISS

so the product number prints in full and the description is cut to ten characters. 161 of the 207 Stores lines
resolve against the inventory.

## What is still not settled

- **Three product numbers the register charges are in neither the export nor the inventory.** Everything else
  resolves.
- **44 resolved lines where the narration and the inventory disagree.** Most are naming convention and are not
  errors: "BOOTS MONG" against "MONGREL 461050 WHEAT UK13" is the register leading with the item and the
  inventory with the brand; "SAND BAGS" against "SANDBAGS" is spacing. A handful are real questions, notably
  174951 which the register calls a water bottle and the inventory a thermos flask, and 207623 which the
  register calls a cream hat and the inventory a straw hat in an alternate range.
- **The two chart disagreements are the register abbreviating, not errors**: 73313 "Telecom Service" against
  "Telecommunication Services", and 73412 "Ref of Op Contr" against "Refund of Operational Contributions".
