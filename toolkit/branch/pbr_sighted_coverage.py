"""pbr_sighted_coverage.py - sighted-invoice coverage per section per financial year, across BOTH registers.

WHAT IT ANSWERS. How much of each section's spend, in each financial year, rests on an invoice this project
has actually sighted and captured at line level under rule 17, and how much rests on something weaker. The
existing Evidence_Coverage sheet cuts the same question by THEME and over the assessed years only; this cuts
it by the two axes a section leader reads, their own section and their own year, and it spans all four years
and all ten sections.

THE DENOMINATOR IS THE ARGUMENT. A sighted invoice is a supplier document, so only a creditor-ledger line can
ever carry one: on both registers every line with Nature Basis "Sighted invoice line" is Source = AP, with no
exceptions. The base is `pbr_contractor_pull.AP_SOURCES`, AP and CT, the two ledgers a supplier tax invoice
posts through, so this report and the contractor pull measure the same universe. A journal leg, an inventory
issue, an internal billing charge or a payroll line cannot be closed by sighting a supplier invoice however
long anyone looks, so measuring coverage against total section spend understates it by whatever share of that
section happens to be internal. Both figures are reported: coverage of AP spend is the one to act on,
coverage of all spend is the one that reconciles to the register total.

THE TWO REGISTERS PARTITION, THEY DO NOT MERGE. FY2026/27 comes from the Parks Branch register, which covers
all ten sections; FY2023/24 to FY2025/26 come from the newest shipped PS & WP register, which covers Park
Services and Water Parks only. The branch register inherits the PS & WP FY2026/27 block line by line and
supersedes it, so that block is never read here and nothing is counted twice. The report is named for the
branch version, as the other pull reports are, and names both files it read.

SECTION IS NOT CODED ON THE TWO EARLIEST YEARS. The PS & WP register leaves Section Code blank on every
FY2023/24 and FY2024/25 line. It is not missing data: the register's scope is 4090240 and 4090260, and each
of those lines carries a Service No that the section-coded years map to exactly one section. The map is built
from the register's own coded rows and a service that maps to two sections ABORTS rather than picking one.
Rows resolved this way are counted under the derived section and the count is stated on the report, so no
figure here rests on a derivation the reader cannot see.

Usage: python3 pbr_sighted_coverage.py [branch.xlsx] [pswp.xlsx] [outdir]
"""
import collections, datetime as dt, os, re, sys
from decimal import Decimal, ROUND_HALF_UP

from python_calamine import CalamineWorkbook
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
import pbr_reports
from pbr_contractor_pull import AP_SOURCES   # ('AP', 'CT'): the ledgers a supplier tax invoice posts
                                             # through. Imported rather than restated so this report and the
                                             # contractor pull can never disagree on what AP spend is.

D = lambda x: Decimal(str(x or 0)).quantize(Decimal('0.01'), ROUND_HALF_UP)
SIGHTED = 'Sighted invoice line'
BRANCH_FY = 'FY2026/27'
HDR = PatternFill('solid', fgColor='1F3864')
SUB = PatternFill('solid', fgColor='D9E1F2')
WHITE = Font(color='FFFFFF', bold=True)


def pct(part, whole):
    return float(part) / float(whole) if whole else 0.0


def read_register(path):
    """Register rows, the header index, the version and the data span, read with calamine (rule 19.8)."""
    wb = CalamineWorkbook.from_path(path)
    cfg = {r[0]: r[1] for r in wb.get_sheet_by_name('Config').to_python(skip_empty_area=False) if r and r[0]}
    a, b = (int(x) for x in str(cfg['REGISTER_DATA']).split(':'))
    R = wb.get_sheet_by_name('Register').to_python(skip_empty_area=False)
    ix = {h: i for i, h in enumerate(R[3])}
    return {'file': os.path.basename(path), 'ver': version_of(cfg, path),
            'span': f'{a}:{b}', 'ix': ix, 'rows': R[a - 1:b]}


def version_of(cfg, path):
    """The version this workbook actually IS.

    `WORKBOOK_VERSION` is not reliably the answer on the PS & WP side: the v127 candidate carries v123 there
    and records every later version under its own `WORKBOOK_VERSION_V<n>` key, so reading the plain key alone
    labels the report with a version three builds behind the file. Take the highest version any Config key
    carries, and fall back to the filename where Config carries none.
    """
    best = -1
    for k, v in cfg.items():
        if str(k).upper().startswith('WORKBOOK_VERSION'):
            m = re.fullmatch(r'v(\d+)', str(v).strip(), re.I)
            if m and int(m.group(1)) > best:
                best = int(m.group(1))
    if best < 0:
        m = re.search(r'_v(\d+)', os.path.basename(path))
        return f'v{m.group(1)}' if m else 'v?'
    return f'v{best}'


def service_map(reg):
    """Service No -> section, learned from this register's own section-coded rows.

    A service that appears under two different sections is not resolvable and aborts: guessing which one a
    blank-section row belongs to would put spend in a section that never incurred it.
    """
    ix = reg['ix']
    seen = collections.defaultdict(set)
    for r in reg['rows']:
        sec, code = str(r[ix['Section']]).strip(), str(r[ix['Section Code']]).strip().split('.')[0]
        if sec:
            seen[str(r[ix['Service No']]).strip().split('.')[0]].add((code, sec))
    out = {}
    for svc, pairs in seen.items():
        if len(pairs) > 1:
            raise SystemExit(f'service {svc} maps to {len(pairs)} sections {sorted(pairs)}: not resolvable')
        out[svc] = next(iter(pairs))
    return out


def sections_of(reg, rows, smap):
    """(section code, section name, derived?) per row: the coded value where there is one, else the service map."""
    ix = reg['ix']
    for r in rows:
        sec = str(r[ix['Section']]).strip()
        code = str(r[ix['Section Code']]).strip().split('.')[0]
        if sec:
            yield r, code, sec, False
            continue
        svc = str(r[ix['Service No']]).strip().split('.')[0]
        hit = smap.get(svc)
        yield (r, hit[0], hit[1], True) if hit else (r, 'NOT CODED', 'Section not coded', True)


def cell(reg, rows):
    """The five figures every cell of this report carries, plus the invoices behind the sighted ones."""
    ix = reg['ix']
    ap = [r for r in rows if str(r[ix['Source']]).strip() in AP_SOURCES]
    sig = [r for r in rows if str(r[ix['Nature Basis']]).strip() == SIGHTED]
    inv = {str(r[ix['Ev Invoice ID']]).strip() for r in sig if str(r[ix['Ev Invoice ID']]).strip()}
    return {'lines': len(rows), 'amount': sum(D(r[ix['Amount ex GST']]) for r in rows),
            'ap_lines': len(ap), 'ap_amount': sum(D(r[ix['Amount ex GST']]) for r in ap),
            'sighted_lines': len(sig), 'sighted_amount': sum(D(r[ix['Amount ex GST']]) for r in sig),
            'invoices': frozenset(inv)}


def add(a, b):
    """Fold two cells. Invoice IDs UNION rather than add: one invoice posted across two sections or two
    years is one invoice, and summing the per-cell counts would report it twice in every total above it."""
    return {k: (a[k] | b[k]) if isinstance(a[k], frozenset) else a[k] + b[k] for k in a}


ZERO = {'lines': 0, 'amount': Decimal('0.00'), 'ap_lines': 0, 'ap_amount': Decimal('0.00'),
        'sighted_lines': 0, 'sighted_amount': Decimal('0.00'), 'invoices': frozenset()}


def collect(branch, pswp):
    """One cell per (section, FY), drawn from whichever register owns that year."""
    cells, derived = {}, 0
    owner, carries = {}, collections.defaultdict(set)   # which register owns a year; which years it covers
    for reg, keep in ((branch, lambda f: f == BRANCH_FY), (pswp, lambda f: f != BRANCH_FY)):
        ix = reg['ix']
        smap = service_map(reg)
        rows = [r for r in reg['rows'] if keep(str(r[ix['FY (Doc)']]).strip())]
        buckets = collections.defaultdict(list)
        for r, code, name, was_derived in sections_of(reg, rows, smap):
            fy = str(r[ix['FY (Doc)']]).strip()
            buckets[(code, name, fy)].append(r)
            owner[fy] = reg['file']
            derived += 1 if was_derived else 0
        for (code, name, fy), rs in buckets.items():
            cells[(code, name, fy)] = cell(reg, rs)
            carries[(code, name)].add(reg['file'])
    return cells, derived, owner, carries


def money(x):
    return f'{x:,.2f}'


def main():
    argv = sys.argv[1:]
    b_path = argv[0] if len(argv) > 0 else pbr_reports.latest('Parks_Branch_Transaction_Register_FY2627_v*.xlsx')
    p_path = argv[1] if len(argv) > 1 else pbr_reports.latest('PS_WP_Transaction_Register_3FY_v*.xlsx')
    out = argv[2] if len(argv) > 2 else os.path.join(ROOT, 'reports')
    if not b_path or not p_path:
        raise SystemExit(f'cannot find a shipped register: branch={b_path} pswp={p_path}')
    pbr_reports.assert_sources(b_path, p_path, tool='sighted coverage')

    B, P = read_register(b_path), read_register(p_path)
    ver = B['ver']
    cells, derived, owner, carries = collect(B, P)

    years = sorted({fy for (_, _, fy) in cells})
    secs = sorted({(c, n) for (c, n, _) in cells}, key=lambda cn: (cn[0] == 'NA', cn[0] == 'NOT CODED', cn[0]))
    get = lambda c, n, fy: cells.get((c, n, fy), dict(ZERO))
    row_tot = {(c, n): _fold([get(c, n, fy) for fy in years]) for c, n in secs}
    col_tot = {fy: _fold([get(c, n, fy) for c, n in secs]) for fy in years}
    grand = _fold(list(col_tot.values()))

    os.makedirs(out, exist_ok=True)
    stamp = dt.date.today().strftime('%d-%b-%Y')
    md = _markdown(B, P, ver, stamp, years, secs, get, row_tot, col_tot, grand, derived,
                   _absent(years, secs, cells, owner, carries))
    with open(os.path.join(out, f'Sighted_Coverage_{ver}.md'), 'w') as fh:
        fh.write('\n'.join(md) + '\n')
    _workbook(os.path.join(out, f'Sighted_Coverage_{ver}.xlsx'), B, P, ver, stamp,
              years, secs, get, row_tot, col_tot, grand)
    print(f'sighted coverage {ver}: {len(secs)} section(s) x {len(years)} year(s), '
          f'{grand["sighted_lines"]:,} sighted lines ${money(grand["sighted_amount"])} of '
          f'${money(grand["ap_amount"])} AP spend ({pct(grand["sighted_amount"], grand["ap_amount"]):.1%})')
    return 0


def _span(fys):
    return fys[0] if len(fys) == 1 else f'{fys[0]} to {fys[-1]}'


def _fold(cs):
    t = dict(ZERO)
    for c in cs:
        t = add(t, c)
    return t


def _absent(years, secs, cells, owner, carries):
    """Sections with no line in a year the register that owns that year does carry them in.

    A blank cell is not zero coverage and must not be read as one: Water Parks appears in the PS & WP register
    only from FY2025/26, and reporting it at 0% for the two years before that would invent an exposure.
    """
    gaps = []
    for c, n in secs:
        miss = [fy for fy in years if (c, n, fy) not in cells and owner.get(fy) in carries[(c, n)]]
        if miss:
            gaps.append(f'{n} ({c}) has no line in {" or ".join(miss)}')
    return '; '.join(gaps)


def _markdown(B, P, ver, stamp, years, secs, get, row_tot, col_tot, grand, derived, absent):
    cover = pct(grand['sighted_amount'], grand['ap_amount'])
    worst = sorted(((c, n, fy, get(c, n, fy)) for c, n in secs for fy in years),
                   key=lambda t: -(t[3]['ap_amount'] - t[3]['sighted_amount']))
    md = [f'# Sighted invoice coverage by section and year, both registers ({stamp})', '',
          f'**Position:** {cover:.1%} of AP-ledger spend across the {len(years)} financial years rests on a '
          f'sighted invoice: '
          f'${money(grand["sighted_amount"])} of ${money(grand["ap_amount"])} over {grand["sighted_lines"]:,} '
          f'captured lines and {len(grand["invoices"]):,} invoices. Against total register spend of '
          f'${money(grand["amount"])}, which includes journals, internal charges and inventory issues that no '
          f'supplier document can close, the same capture covers {pct(grand["sighted_amount"], grand["amount"]):.1%}.', '',
          '## What counts as covered', '',
          'A line is covered here only where Nature Basis reads "Sighted invoice line", which on both registers '
          'means the invoice was captured at line level under rule 17, all three checks returned TRUE and the '
          'line reads Confirmed. Nothing weaker is counted: a matched creditor history, a vendor inference and a '
          'line narration all leave the line uncovered on this report however firmly the register itself treats '
          'them as identified.', '',
          'Every sighted line on both registers is Source = AP, and the creditor ledger is the denominator to '
          'read. The AP base is Source AP or CT, the two ledgers a supplier tax invoice posts through, which is '
          'the same base the contractor pull list uses. A journal leg, an inventory issue, an internal billing '
          'charge and a payroll line cannot be closed by sighting a supplier invoice, so they sit outside that '
          'base and are visible as the difference between the two coverage columns.', '',
          '## Population', '',
          '| Register | Scope | Lines | $ ex GST |', '|---|---|---:|---:|',
          f'| `{B["file"]}` {B["ver"]} | FY2026/27, branch 4090000, all sections | '
          f'{col_tot[BRANCH_FY]["lines"]:,} | {money(col_tot[BRANCH_FY]["amount"])} |',
          f'| `{P["file"]}` {P["ver"]} | {_span([f for f in years if f != BRANCH_FY])}, Park Services and '
          f'Water Parks | {sum(col_tot[f]["lines"] for f in years if f != BRANCH_FY):,} | '
          f'{money(sum(col_tot[f]["amount"] for f in years if f != BRANCH_FY))} |',
          f'| **Combined** | {len(years)} financial years, nothing counted twice | **{grand["lines"]:,}** | '
          f'**{money(grand["amount"])}** |', '',
          'The branch register inherits the PS & WP FY2026/27 block line by line and supersedes it, so that '
          'block is not read here.', '',
          '## Coverage by section and year', '',
          '| Section | FY | Lines | $ ex GST | AP lines | $ AP | Sighted lines | $ sighted | Cover, AP $ | '
          'Cover, all $ | Invoices |',
          '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for c, n in secs:
        for fy in years:
            s = get(c, n, fy)
            if not s['lines']:
                continue
            md.append(f'| {n} ({c}) | {fy} | {s["lines"]:,} | {money(s["amount"])} | {s["ap_lines"]:,} | '
                      f'{money(s["ap_amount"])} | {s["sighted_lines"]:,} | {money(s["sighted_amount"])} | '
                      f'{pct(s["sighted_amount"], s["ap_amount"]):.1%} | '
                      f'{pct(s["sighted_amount"], s["amount"]):.1%} | {len(s["invoices"]):,} |')
        t = row_tot[(c, n)]
        md.append(f'| **{n} ({c}), all years** | | **{t["lines"]:,}** | **{money(t["amount"])}** | '
                  f'**{t["ap_lines"]:,}** | **{money(t["ap_amount"])}** | **{t["sighted_lines"]:,}** | '
                  f'**{money(t["sighted_amount"])}** | **{pct(t["sighted_amount"], t["ap_amount"]):.1%}** | '
                  f'**{pct(t["sighted_amount"], t["amount"]):.1%}** | **{len(t["invoices"]):,}** |')
    md += ['', '## Coverage by year', '',
           '| FY | Sections | Lines | $ ex GST | $ AP | $ sighted | Cover, AP $ | Cover, all $ | Invoices |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for fy in years:
        t = col_tot[fy]
        live = sum(1 for c, n in secs if get(c, n, fy)['lines'])
        md.append(f'| {fy} | {live} | {t["lines"]:,} | {money(t["amount"])} | {money(t["ap_amount"])} | '
                  f'{money(t["sighted_amount"])} | {pct(t["sighted_amount"], t["ap_amount"]):.1%} | '
                  f'{pct(t["sighted_amount"], t["amount"]):.1%} | {len(t["invoices"]):,} |')
    md.append(f'| **All years** | | **{grand["lines"]:,}** | **{money(grand["amount"])}** | '
              f'**{money(grand["ap_amount"])}** | **{money(grand["sighted_amount"])}** | '
              f'**{pct(grand["sighted_amount"], grand["ap_amount"]):.1%}** | '
              f'**{pct(grand["sighted_amount"], grand["amount"]):.1%}** | **{len(grand["invoices"]):,}** |')
    md += ['', '## The largest uncovered AP positions', '',
           'Ranked on AP spend with no sighted invoice behind it, which is the figure a capture session moves.', '',
           '| # | Section | FY | $ AP | $ sighted | $ uncovered | Cover, AP $ |', '|---|---|---|---:|---:|---:|---:|']
    for k, (c, n, fy, s) in enumerate(worst[:15], 1):
        gap = s['ap_amount'] - s['sighted_amount']
        if gap <= 0:
            break
        md.append(f'| {k} | {n} ({c}) | {fy} | {money(s["ap_amount"])} | {money(s["sighted_amount"])} | '
                  f'**{money(gap)}** | {pct(s["sighted_amount"], s["ap_amount"]):.1%} |')
    md += ['', '## Reading the figures', '',
           '1. **Cover, AP $ is the actionable rate.** It is the share of supplier spend in that cell resting on '
           'an invoice captured at line level. Its complement is the capture queue, not an error.',
           f'2. **Cover, all $ is the reconciling rate.** Its denominator is every register line in the cell, '
           f'so the $ ex GST column adds to ${money(grand["amount"])}: the branch control total '
           f'${money(col_tot[BRANCH_FY]["amount"])} in full, plus the '
           f'{_span([f for f in years if f != BRANCH_FY])} part of the PS & WP register.',
           '3. **A low rate on a section whose spend is mostly internal is not a finding.** Read the two rates '
           'together: a wide gap between them means the section is carried by journals and internal charges, '
           'which belong to the rule 21 journal pull list rather than to a capture session.',
           '4. **Invoices counts distinct Ev Invoice IDs.** One invoice posted across several lines or PKs is '
           'counted once, and every total unions the invoice IDs beneath it rather than adding the counts, so '
           'an invoice touching two sections or two years is counted once in the total above them and the '
           'column does not add down the page.',
           f'5. **{derived:,} line(s) carry no Section Code** and are placed by their Service No through the '
           "map the register's own section-coded rows establish. A service resolving to two sections aborts the "
           'report rather than picking one.',
           '6. **A section missing from a year had no line in it**, not zero coverage: '
           + (absent or 'every section carries lines in every year its register covers') + '.', '',
           f'Sources: `{B["file"]}` Register rows {B["span"]}; `{P["file"]}` Register rows {P["span"]}. '
           'Generated by `toolkit/branch/pbr_sighted_coverage.py`.']
    return md


def _workbook(path, B, P, ver, stamp, years, secs, get, row_tot, col_tot, grand):
    wb = Workbook()
    money_fmt, pct_fmt = '#,##0.00', '0.0%'

    def head(ws, title, cols):
        ws['A1'] = title
        ws['A1'].font = Font(bold=True, size=13)
        ws['A2'] = (f'Sighted invoice coverage {ver}, {stamp}. Sources: {B["file"]} rows {B["span"]}; '
                    f'{P["file"]} rows {P["span"]}.')
        ws['A2'].alignment = Alignment(wrap_text=False)
        for i, (h, w) in enumerate(cols, 1):
            c = ws.cell(row=4, column=i, value=h)
            c.fill, c.font = HDR, WHITE
            ws.column_dimensions[c.column_letter].width = w
        ws.freeze_panes = 'A5'

    ws = wb.active
    ws.title = 'Coverage'
    head(ws, 'Sighted invoice coverage by section and year',
         [('Section code', 14), ('Section', 34), ('FY', 11), ('Lines', 9), ('$ ex GST', 14), ('AP lines', 10),
          ('$ AP', 14), ('Sighted lines', 13), ('$ sighted', 14), ('$ uncovered AP', 15),
          ('Cover, AP $', 12), ('Cover, all $', 12), ('Invoices', 10)])
    r = 5
    for c, n in secs:
        for fy in years:
            s = get(c, n, fy)
            if not s['lines']:
                continue
            _line(ws, r, [c, n, fy, s['lines'], s['amount'], s['ap_lines'], s['ap_amount'], s['sighted_lines'],
                          s['sighted_amount'], s['ap_amount'] - s['sighted_amount'],
                          pct(s['sighted_amount'], s['ap_amount']), pct(s['sighted_amount'], s['amount']),
                          len(s['invoices'])], money_fmt, pct_fmt)
            r += 1
        t = row_tot[(c, n)]
        _line(ws, r, [c, n, 'All years', t['lines'], t['amount'], t['ap_lines'], t['ap_amount'],
                      t['sighted_lines'], t['sighted_amount'], t['ap_amount'] - t['sighted_amount'],
                      pct(t['sighted_amount'], t['ap_amount']), pct(t['sighted_amount'], t['amount']),
                      len(t['invoices'])], money_fmt, pct_fmt, bold=True)
        r += 1

    ws = wb.create_sheet('Years')
    head(ws, 'Sighted invoice coverage by year',
         [('FY', 12), ('Sections', 10), ('Lines', 9), ('$ ex GST', 14), ('$ AP', 14), ('$ sighted', 14),
          ('$ uncovered AP', 15), ('Cover, AP $', 12), ('Cover, all $', 12), ('Invoices', 10)])
    r = 5
    for fy in list(years) + ['All years']:
        t = col_tot[fy] if fy != 'All years' else grand
        live = sum(1 for c, n in secs if get(c, n, fy)['lines']) if fy != 'All years' else len(secs)
        _line(ws, r, [fy, live, t['lines'], t['amount'], t['ap_amount'], t['sighted_amount'],
                      t['ap_amount'] - t['sighted_amount'], pct(t['sighted_amount'], t['ap_amount']),
                      pct(t['sighted_amount'], t['amount']), len(t['invoices'])],
              money_fmt, pct_fmt, bold=(fy == 'All years'))
        r += 1

    ws = wb.create_sheet('Matrix')
    head(ws, 'Cover, AP $: section down, year across',
         [('Section', 36)] + [(fy, 13) for fy in years] + [('All years', 13)])
    r = 5
    for c, n in secs:
        ws.cell(row=r, column=1, value=f'{n} ({c})')
        for i, fy in enumerate(years, 2):
            s = get(c, n, fy)
            cl = ws.cell(row=r, column=i, value=pct(s['sighted_amount'], s['ap_amount']) if s['ap_lines'] else None)
            cl.number_format = pct_fmt
        t = row_tot[(c, n)]
        cl = ws.cell(row=r, column=len(years) + 2, value=pct(t['sighted_amount'], t['ap_amount']))
        cl.number_format, cl.font = pct_fmt, Font(bold=True)
        r += 1
    ws.cell(row=r, column=1, value='All sections').font = Font(bold=True)
    for i, fy in enumerate(years, 2):
        t = col_tot[fy]
        cl = ws.cell(row=r, column=i, value=pct(t['sighted_amount'], t['ap_amount']))
        cl.number_format, cl.font = pct_fmt, Font(bold=True)
    cl = ws.cell(row=r, column=len(years) + 2, value=pct(grand['sighted_amount'], grand['ap_amount']))
    cl.number_format, cl.font = pct_fmt, Font(bold=True)
    wb.save(path)


def _line(ws, r, vals, money_fmt, pct_fmt, bold=False):
    for i, v in enumerate(vals, 1):
        c = ws.cell(row=r, column=i, value=float(v) if isinstance(v, Decimal) else v)
        if isinstance(v, Decimal):
            c.number_format = money_fmt
        elif isinstance(v, float):
            c.number_format = pct_fmt
        if bold:
            c.font, c.fill = Font(bold=True), SUB


if __name__ == '__main__':
    sys.exit(main())
