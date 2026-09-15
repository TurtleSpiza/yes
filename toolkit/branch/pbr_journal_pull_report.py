"""pbr_journal_pull_report.py - the journal pull list as a standalone report, across BOTH registers (rule 21).

Reads the Journal_Pull sheet of the newest shipped register on each side with python-calamine (rule 19.8) and
writes reports/Journal_Pull_<ver>.md and .xlsx. The workbooks are the record; this is the working copy that goes
to Finance with the pull request. Nothing is recomputed here, so the report cannot disagree with either register:
every count, net and gross is the sheet's own figure, summed.

Scope, partitioned the same way as the contractor pull so nothing is counted twice:

    FY2023/24, FY2024/25, FY2025/26   the NEWEST shipped PS & WP register (Park Services and Water Parks), read
                                       off its own Journal_Pull sheet. Not the v127 candidate the branch register
                                       inherits from: a pull list built off that pin asks Finance for documents a
                                       later PS & WP build has already worked.
    FY2026/27                          Parks Branch register (all ten sections). It inherits the PS & WP FY2026/27
                                       block line by line and supersedes it, so the PS & WP FY2026/27 documents
                                       are NOT merged; they are reported as a reconciling note, each one named
                                       against the branch tier it now sits in.

A document file sits in exactly one financial year on both sheets, so the partition is by the FY column and a
file never appears on both sides. Tiers are keyed on their letter: the two sheets spell Tier C differently
("C RJ reversal" / "C RJ reversal, no pull") and Tiers D, E and F exist only on the branch side. The PS & WP
sheet carries no Period, Pull value, Why it matters or Sections columns, so those cells are blank on its rows
rather than invented.

Named for the branch version, as the contractor pull is; the Population table and the Sources line name the
PS & WP file actually read.

Usage: python3 pbr_journal_pull_report.py [branch register.xlsx] [pswp register.xlsx] [outdir]
"""
import collections, os, re, sys
from decimal import Decimal, ROUND_HALF_UP
from python_calamine import CalamineWorkbook
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pbr_stage
from pbr_unidentified_queue import latest_register  # noqa
from pbr_contractor_pull import latest_pswp, file_ver  # noqa

D = lambda x: Decimal(str(x or 0)).quantize(Decimal('0.01'), ROUND_HALF_UP)
MONEY = '$#,##0.00;($#,##0.00);"-"'
FY_BRANCH = 'FY2026/27'
TIER_NAME = {'A': 'A Pull required', 'B': 'B Sight attachment', 'C': 'C RJ reversal, no pull',
             'D': 'D Held, already embedded in PS_WP Journal_Sources', 'E': 'E Pulled and embedded at branch',
             'F': 'F Reconstruction pulled and embedded at branch'}
HDR = ['Register', 'Tier', 'Document file', 'Journal ref(s)', 'FY', 'Period(s)', 'Register lines', 'Net in scope $',
       'Gross in scope $', 'Attachment', 'Pull value', 'Why it matters', 'Sections touched', 'Top accounts', 'Top PKs',
       'Narration (first, verbatim)']


def txt(v):
    if v is None:
        return ''
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def cfg_of(wb):
    return {r[0]: r[1] for r in wb.get_sheet_by_name('Config').to_python(skip_empty_area=False) if r and r[0]}


def span(cfg, key):
    a, b = (int(x) for x in re.match(r'(\d+):(\d+)', str(cfg[key])).groups())
    return a, b


def read_branch(path):
    """Branch Journal_Pull: Tier, Document file, Journal ref(s), Period(s), Register lines, Net, Gross, Attachment,
    Pull value, Why it matters, Sections touched, Top accounts, Top PKs, Narration."""
    wb = CalamineWorkbook.from_path(path)
    cfg = cfg_of(wb)
    JP = wb.get_sheet_by_name('Journal_Pull').to_python(skip_empty_area=False)
    a, b = span(cfg, 'JOURNAL_PULL')
    hdr = [txt(c) for c in JP[3]]
    assert hdr[:3] == ['Tier', 'Document file', 'Journal ref(s)'] and hdr[8] == 'Pull value', hdr
    rows = []
    for r in JP[a - 1:b]:
        if not txt(r[0]):
            continue
        rows.append(dict(reg='Branch', tier=txt(r[0])[0], tier_src=txt(r[0]), doc=txt(r[1]), refs=txt(r[2]), fy=FY_BRANCH,
                         periods=txt(r[3]), lines=int(D(r[4])), net=D(r[5]), gross=D(r[6]), att=txt(r[7]), value=txt(r[8]),
                         why=txt(r[9]), sections=txt(r[10]), accounts=txt(r[11]), pks=txt(r[12]), narr=txt(r[13])))
    ver = txt(cfg.get('WORKBOOK_VERSION', 'v?'))
    return dict(tag='Branch', path=path, file=os.path.basename(path), ver=ver, rows=rows, span=f'{a}:{b}',
                preamble=txt(JP[1][0]))


def read_pswp(path):
    """PS & WP Journal_Pull: Tier, Document file, Journal ref(s), FY, Register lines, Net, Gross, Attachment,
    Top accounts, Top PKs, Narration. The sheet's own control row must read TRUE before anything is read off it."""
    wb = CalamineWorkbook.from_path(path)
    cfg = cfg_of(wb)
    JP = wb.get_sheet_by_name('Journal_Pull').to_python(skip_empty_area=False)
    a, b = span(cfg, 'JOURNAL_PULL_DATA')
    hdr = [txt(c) for c in JP[3]]
    assert hdr[:4] == ['Tier', 'Document file', 'Journal ref(s)', 'FY'] and hdr[7] == 'Attachment', hdr
    chk = int(D(cfg['JOURNAL_PULL_CHECK_ROW']))
    control = [txt(c) for c in JP[chk - 1]]
    assert 'TRUE' in control, f'PS & WP Journal_Pull control row {chk} does not read TRUE: {control}'
    rows = []
    for r in JP[a - 1:b]:
        if not txt(r[0]):
            continue
        rows.append(dict(reg='PS & WP', tier=txt(r[0])[0], tier_src=txt(r[0]), doc=txt(r[1]), refs=txt(r[2]), fy=txt(r[3]),
                         periods='', lines=int(D(r[4])), net=D(r[5]), gross=D(r[6]), att=txt(r[7]), value='', why='',
                         sections='', accounts=txt(r[8]), pks=txt(r[9]), narr=txt(r[10])))
    assert len(rows) == int(D(cfg['JOURNAL_PULL_COUNT'])), (len(rows), cfg['JOURNAL_PULL_COUNT'])
    return dict(tag='PS & WP', path=path, file=os.path.basename(path), ver=file_ver(path), rows=rows, span=f'{a}:{b}',
                control=control[0], preamble=txt(JP[1][0]))


def tier_table(rows):
    t = {}
    for r in rows:
        x = t.setdefault(r['tier'], [0, 0, Decimal(0), Decimal(0)])
        x[0] += 1; x[1] += r['lines']; x[2] += r['net']; x[3] += r['gross']
    return t


def main():
    bpath = sys.argv[1] if len(sys.argv) > 1 else latest_register()
    ppath = sys.argv[2] if len(sys.argv) > 2 else latest_pswp()
    OUT = sys.argv[3] if len(sys.argv) > 3 else os.path.join(ROOT, 'reports')
    B, P = read_branch(bpath), read_pswp(ppath)
    ver, stamp = B['ver'], pbr_stage.stamp()   # Brisbane date (pbr_stage.BNE), not the container's UTC day

    p_assessed = [r for r in P['rows'] if r['fy'] != FY_BRANCH]
    p_2627 = [r for r in P['rows'] if r['fy'] == FY_BRANCH]
    body = B['rows'] + p_assessed
    # the partition must be clean: a document file on one side only, and a known FY on every PS & WP row
    assert all(r['fy'].startswith('FY20') for r in P['rows']), sorted({r['fy'] for r in P['rows']})
    both = {r['doc'] for r in B['rows']} & {r['doc'] for r in p_assessed}
    assert not both, f'document file(s) on both sides of the partition: {sorted(both)}'
    b_by_doc = {r['doc']: r for r in B['rows']}
    body.sort(key=lambda r: (r['tier'], -abs(r['net']), -r['gross']))

    tiers, tB, tP = tier_table(body), tier_table(B['rows']), tier_table(p_assessed)
    A = [r for r in body if r['tier'] == 'A']
    absA = sum(abs(r['net']) for r in A)
    high = [r for r in body if r['tier'] in 'AB' and r['value'] == 'High']
    fy_of = collections.Counter(r['fy'] for r in A)

    md = [f'# Journal pull list, both registers, {ver} ({stamp})', '',
          f'**Position:** {len(body)} TechOne document files carry the {sum(r["lines"] for r in body):,} journal lines across the two registers, four financial years, nothing counted twice. '
          f'{len(A)} sit in Tier A (no attachment, ${absA:,.2f} absolute net): '
          + ', '.join(f'{n} in {fy}' for fy, n in sorted(fy_of.items())) + '. '
          f'{len(high)} branch document(s) across Tiers A and B carry an unanswered question (Pull value High) and are the ones worth working first; '
          f'the PS & WP sheet carries no pull-value judgement, so its {tP.get("A", [0])[0]} Tier A documents rank on absolute net alone.', '',
          'Tier A: no attachment in TechOne, so the Document Line Table IS the evidence route - pull these. Tier B: the document carries a TechOne attachment, so sight the attachment; a pull adds nothing. '
          'Tier C: RJ reversing journals, which net to exactly zero and are read as a pair under rules 5 and 6 - no pull unless a specific accrual question arises. '
          'Tier D (branch only): the document is already embedded in the PS & WP register Journal_Sources; a re-pull is audited leg by leg, never re-captured (rule 12). '
          'Tiers E and F (branch only): pulled and embedded at the branch build, as a Document Line Table or a Document Reconstruction. '
          'Ranked within tier by ABSOLUTE net cost movement into the assessed scope (PS & WP: sections 4090240 and 4090260; branch: O110-O115), not by gross, because gross double-counts both legs of a transfer.', '',
          '## Population', '', '| Register | Scope | Documents | Register lines | Net in scope | Gross in scope |', '|---|---|---:|---:|---:|---:|',
          f'| `{B["file"]}` {B["ver"]} | {FY_BRANCH}, branch 4090000, all ten sections | {len(B["rows"])} | {sum(r["lines"] for r in B["rows"]):,} | {sum(r["net"] for r in B["rows"]):,.2f} | {sum(r["gross"] for r in B["rows"]):,.2f} |',
          f'| `{P["file"]}` {P["ver"]} | FY2023/24 to FY2025/26, Park Services and Water Parks | {len(p_assessed)} | {sum(r["lines"] for r in p_assessed):,} | {sum(r["net"] for r in p_assessed):,.2f} | {sum(r["gross"] for r in p_assessed):,.2f} |',
          f'| **Combined** | four financial years, nothing counted twice | **{len(body)}** | **{sum(r["lines"] for r in body):,}** | **{sum(r["net"] for r in body):,.2f}** | **{sum(r["gross"] for r in body):,.2f}** |', '',
          f'The branch register inherits the PS & WP FY2026/27 block line by line and supersedes it, so the {len(p_2627)} PS & WP FY2026/27 document files '
          f'({sum(r["lines"] for r in p_2627):,} lines, {sum(r["net"] for r in p_2627):,.2f} net) are not merged here; they are reconciled to the branch list at the foot. '
          f'The PS & WP Journal_Pull control row reads `{P["control"]}`.', '',
          '## By tier', '', '| Tier | Documents | of which Branch | of which PS & WP | Register lines | Net in scope | Gross in scope |', '|---|---:|---:|---:|---:|---:|---:|']
    for t in sorted(tiers):
        n, ln, net, gross = tiers[t]
        md.append(f'| {TIER_NAME[t]} | {n} | {tB.get(t, [0])[0]} | {tP.get(t, [0])[0]} | {ln:,} | {net:,.2f} | {gross:,.2f} |')
    for t in sorted(tiers):
        rows = [r for r in body if r['tier'] == t]
        md += ['', f'## {TIER_NAME[t]}', '',
               '| # | Register | Document file | Journal ref(s) | FY | Period(s) | Lines | Net in scope | Gross | Att | Pull value | Why it matters | Sections | Top accounts | Top PKs |',
               '|---|---|---|---|---|---|---:|---:|---:|---|---|---|---|---|---|']
        for k, r in enumerate(rows, 1):
            md.append(f'| {k} | {r["reg"]} | **{r["doc"]}** | {r["refs"]} | {r["fy"]} | {r["periods"]} | {r["lines"]} | {r["net"]:,.2f} | {r["gross"]:,.2f} | {r["att"]} | {r["value"]} | '
                      f'{r["why"][:230]} | {r["sections"][:60]} | {r["accounts"]} | {r["pks"]} |')
    md += ['', f'## Reconciling note: PS & WP {FY_BRANCH} documents', '',
           f'The PS & WP register also tiers {len(p_2627)} document files in {FY_BRANCH}. Each is read here from the branch register instead, which holds the same journal lines and more (every section, not two). '
           'The PS & WP tier is shown against the branch tier so a change of tier is visible: a document the PS & WP sheet still calls Tier A can already be pulled and embedded at the branch (Tier E or F).', '',
           '| # | Document file | Journal ref(s) | PS & WP tier | PS & WP lines | PS & WP net | Branch tier | Branch lines | Branch net |', '|---|---|---|---|---:|---:|---|---:|---:|']
    missing = []
    for k, r in enumerate(sorted(p_2627, key=lambda r: (r['tier'], -abs(r['net']))), 1):
        b = b_by_doc.get(r['doc'])
        if b is None:
            missing.append(r['doc'])
        md.append(f'| {k} | **{r["doc"]}** | {r["refs"]} | {r["tier_src"]} | {r["lines"]} | {r["net"]:,.2f} | '
                  + (f'{b["tier_src"]} | {b["lines"]} | {b["net"]:,.2f} |' if b else 'NOT ON BRANCH LIST | | |'))
    md += ['', ('Every one of them is on the branch list.' if not missing else
                f'{len(missing)} PS & WP FY2026/27 document file(s) are NOT on the branch list ({", ".join(missing)}): the branch pull did not carry those journal lines, see the branch Inheritance_Log.'),
           '', '## How to use', '',
           '1. Work Tier A top down and pull one TechOne Document Line Table per **document file**, not per journal reference: one export covers every reference on the file. Key the export to the Document Cross Reference, not the document file, or the pull reaches one reference and leaves the rest of the file unevidenced.',
           '2. Screen each export against Journal_Sources in BOTH registers before capture; a re-pull is audited leg by leg and never re-captured (rule 12).',
           '3. Embed each new document verbatim with leg-level in-scope flags, prove it nets to zero and that each in-scope leg sum ties its own register lines, then refresh this list (pipeline, per journal batch). A FY2023/24 to FY2025/26 document is captured into the PS & WP register; a FY2026/27 document into the branch register.',
           '4. Tier B needs no pull: sight the TechOne attachment on the document file. Tier C is RJ reversing journals, read as a pair under rules 5 and 6. Tiers D, E and F are already embedded.',
           '', f'Sources: `{B["file"]}` Journal_Pull rows {B["span"]}; `{P["file"]}` Journal_Pull rows {P["span"]}. Generated by `toolkit/branch/pbr_journal_pull_report.py`.']
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, f'Journal_Pull_{ver}.md'), 'w', encoding='utf-8').write('\n'.join(md) + '\n')

    xw = Workbook(); ws = xw.active; ws.title = 'Journal_Pull'
    hf = Font(name='Cambria', bold=True, color='FFFFFF'); fill = PatternFill('solid', fgColor='1F3864')
    ws.append([f'Journal pull list, both registers, {ver} ({stamp}): {len(body)} document files, {len(A)} to pull, ${absA:,.2f} absolute net. '
               f'{FY_BRANCH} from {B["file"]}; FY2023/24 to FY2025/26 from {P["file"]}.'])
    ws.append([md[6]]); ws.append([])
    ws.append(HDR)
    for c in ws[4]:
        c.font = hf; c.fill = fill
    for r in body:
        ws.append([r['reg'], TIER_NAME[r['tier']], r['doc'], r['refs'], r['fy'], r['periods'], r['lines'], float(r['net']), float(r['gross']),
                   r['att'], r['value'], r['why'], r['sections'], r['accounts'], r['pks'], r['narr']])
        ws.cell(ws.max_row, 8).number_format = MONEY; ws.cell(ws.max_row, 9).number_format = MONEY
    for col, w in zip('ABCDEFGHIJKLMNOP', [9, 30, 14, 30, 11, 10, 12, 16, 16, 8, 11, 80, 26, 26, 24, 60]):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = 'A5'
    for c in ws[1] + ws[2]:
        c.alignment = Alignment(wrap_text=False)
    wr = xw.create_sheet('PSWP_FY2627_Reconciled')
    wr.append([f'PS & WP {FY_BRANCH} document files, read from the branch register instead (it inherits and supersedes the PS & WP {FY_BRANCH} block).'])
    wr.append([])
    wr.append(['Document file', 'Journal ref(s)', 'PS & WP tier', 'PS & WP lines', 'PS & WP net $', 'Branch tier', 'Branch lines', 'Branch net $'])
    for c in wr[3]:
        c.font = hf; c.fill = fill
    for r in sorted(p_2627, key=lambda r: (r['tier'], -abs(r['net']))):
        b = b_by_doc.get(r['doc'])
        wr.append([r['doc'], r['refs'], r['tier_src'], r['lines'], float(r['net']), b['tier_src'] if b else 'NOT ON BRANCH LIST',
                   b['lines'] if b else None, float(b['net']) if b else None])
        wr.cell(wr.max_row, 5).number_format = MONEY; wr.cell(wr.max_row, 8).number_format = MONEY
    for col, w in zip('ABCDEFGH', [14, 30, 22, 12, 16, 40, 12, 16]):
        wr.column_dimensions[col].width = w
    wr.freeze_panes = 'A4'
    xw.save(os.path.join(OUT, f'Journal_Pull_{ver}.xlsx'))
    print(f'{len(body)} document files ({len(B["rows"])} branch {B["ver"]}, {len(p_assessed)} PS & WP {P["ver"]}; {len(p_2627)} PS & WP {FY_BRANCH} reconciled, {len(missing)} missing) -> {OUT}/Journal_Pull_{ver}.md and .xlsx')
    for t in sorted(tiers):
        n, ln, net, gross = tiers[t]
        print(f'  {t} {TIER_NAME[t][2:]:48} {n:3} documents  {ln:6,} lines  net ${net:>14,.2f}')
    for r in A + [r for r in body if r['tier'] == 'B' and r['value'] == 'High']:
        print(f"    {r['tier']} {r['reg']:7} {r['value']:6} {r['doc']:9} {r['fy']} {r['refs'][:26]:26} lines {r['lines']:5} net ${r['net']:>13,.2f}  {r['why'][:80]}")


if __name__ == '__main__':
    main()
