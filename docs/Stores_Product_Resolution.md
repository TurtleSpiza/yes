# Stores product resolution, 18-Sep-2026

How an LCC Stores line on the branch register is resolved to the goods it bought. Separated from the extraction
prompt assessment, where it did not belong: this is register reference data and touches neither the prompt, the
corpora nor the gate.

## What the register owner's confirmations changed

Seven Stores product names were confirmed against the goods. All seven were cases where the machine sources
disagreed, so this is not a fair sample, but it is enough to correct the coverage ranking in `data/reference/README.md`:

- The requisition export was **exactly right on none of the seven**; the Marsden inventory on two.
- On **196303** the export names a hard hat browguard with an earmuff attachment. The goods are a face shield
  with a clear visor, a different piece of PPE on the same account.
- On **207353** the export names isopropyl wipes, canister of 75. The goods are baby soap wipes, packet of 80.

So the export remains the best source **on coverage** (163 lines resolved against 117, and 3 absent against 46)
and is **not an authority on the name**. Confirmed names live in `stores_confirmed_products.json` and outrank
both machine sources.

