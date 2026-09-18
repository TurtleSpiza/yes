# FBT Reason Codes (LCC)

Source: Chart of Accounts PDF, page 69 (Hospitality & Entertainment Guide, Reason Codes section).
Authority: FBT Act and Local Government Regulation 2012 s.196.
Contact: FinancialAccounting@logan.qld.gov.au

These reason codes attach to every transaction posted to a hospitality, entertainment, or employee-benefit natural account. The code documents WHY the FBT call was made, not just the dollar amount.

## A — Work-related purpose
Food is provided for a work-related purpose rather than an entertainment purpose.
Default account: **73512** (Entertainment & Hospitality Non-FBT).

## B — Refreshment, not entertainment
Food is provided for the purpose of refreshment rather than an entertainment purpose.
Default account: **73512**.

## C — Social function (FBT applies)
Social function (recreation or meal entertainment). These are subject to FBT.
Default account: **73511** (Entertainment & Hospitality FBT).
GST code: typically **P**.

## D — < $300 minor benefit
Expense benefits with a value of < $300 (including GST). These are **minor benefits if provided infrequently** and are exempt.
Default account: **73513** (Employee Reward and Recognition) or **73514/7B223** for employee functions.

## E — ≥ $300 expense benefit
Expense benefits with a value of $300 or more. These are subject to FBT.
Default account: **73513** with FBT, or **73514/7B223**.

## F — Light refreshments with work-related training
Light refreshments provided with work-related training.
Default account: **73512** (refreshment portion). Training fee itself goes to **73544** (Training & Development) or **73541** (Conferences & Seminar Fees).

## G — Non work-related meal entertainment / gift
Non work-related meal entertainment (e.g. for guest speaker, volunteer) or gift.
Default account: **73512**.

## H — Requires assessment of four factors
Requires assessment of a combination of factors:

1. **Purpose food or drink is provided:**
   - Refreshment only (i.e. light lunch & teas) → **73512**
   - Social → **73511**

2. **Type of food or drink provided:**
   - Tea / light or finger lunch → **73512**
   - Elaborate meal / alcohol → **73511**

3. **When provided:**
   - During work / over time likely → **73512**
   - Outside of work likely → **73511**

4. **Where provided:**
   - On business premises likely → **73512**
   - Off site or function room likely → **73511**

If any single factor pushes the call to 73511 (off-site, alcohol, elaborate, social), the whole event is 73511.

## I — Years of Service gift < $500
Years of Service Gift < $500. **FBT exempt**.
Default account: **73514/7B223**. GST code: **NA**.

## J — Years of Service gift > $500
Years of Service Gift > $500. Subject to FBT.
Default account: **73514/7B223**. GST code: **NA**.

## K — Community / non-employee event or gift
Event or gift for community members/non-employees. **Exempt from FBT**.
Default account: **73553** (Promotional Items).

## L — Presenter / entertainer fee (community event)
Presenter, speaker, entertainer's fee — **non-FBT if for a community event**. Exempt from FBT.
Default account: **73515** (Presenter and Entertainer Fees — Non-FBT).

## 50/50 method (meal entertainment)

Council uses the **50/50 method** to determine FBT liability for meal entertainment. All meal entertainment (whether for employees or non-employees) is subject to FBT at 50% of the value of the cost. Using the 50/50 method removes the need to analyse actual expenditure.

Operationally this means: Finance posts a single 50/50 batch journal each period that splits hospitality balances between FBT and non-FBT treatment. **Do not treat 50/50 batch movements as miscodes.** See `fbt_5050_batch_identifiers.md` for batch detection.

## Internal catering (LEC, Logan Metro InSports)

Where catering is provided by Council owned and operated facilities (Logan Entertainment Centre and Logan Metro InSports):

- **7B221** — catering with FBT
- **7B222** — catering without FBT

Internal invoices quoting 7B221/7B222 must include purpose for catering, internal/external attendees, and specifics of food and drink. Authorised per Instrument of Authorisation AUTH0009 (Financial Authorisation Limits) and AUTH0012 (General Authorisations).

## GST codes

The two main GST codes are:

- **C** — Standard taxable supply with credit. Most allocations carry C.
- **P** — Generally used for 73511 allocations (no input tax credit claimable).

GST is highly complex and is best left to the Finance Branch to assess. The default rule of thumb: **P for 73511, C elsewhere.** Final code depends on whether the supplier is registered for GST, the GST status of the supply, and whether FBT applies.

## Cross-references

- `fbt_classification.json` — machine-readable allocation table including all 19 numbered scenarios from the LCC Hospitality Guide.
- `hospitality_scenarios.md` — the same 19 scenarios as a markdown table.
- `fbt_data.json` — operational allocation lookup used by the v7 HTML AI tool (24 entries).
- `fbt_5050_batch_identifiers.md` — Finance 50/50 batch detection rules.
- `accts.json` / `full_chart_of_accounts.json` — account descriptions for 73511, 73512, 73513, 73514, 73515, 73544, 73541, 73553, 7B221, 7B222, 7B223.
