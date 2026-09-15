"""pbr_contractor_pull.py - the pull list cut BY CONTRACTOR, across both registers.

The two existing queues are cut by something other than the supplier. `pbr_unidentified_queue.py` groups the
Tier 3 lines into series (section, service, reference shape) and `pbr_journal_pull_report.py` groups journal lines
by TechOne document file. Neither answers the question a request to Finance or AP actually has to answer: for THIS
supplier, across everything the project holds, what is still unevidenced and what one pull would close it.

Scope: both registers, partitioned so nothing is counted twice.

    FY2023/24, FY2024/25, FY2025/26   the NEWEST shipped PS & WP register (Park Services and Water Parks, the
                                       assessed years). Not the v127 candidate the branch register inherits from:
                                       that pin is the branch build's inheritance source (pbr_stage.V127) and is
                                       deliberately frozen, but a pull list read off it asks Finance for documents
                                       v128 and v129 have already sighted.
    FY2026/27                          Parks Branch register (all ten sections; it inherits the PS & WP FY2026/27
                                       block line by line and supersedes it, so PS & WP FY2026/27 is NOT read here)

The PS & WP FY2026/27 lines the branch pull did not carry are reported as a reconciling note rather than merged,
because they are a known difference between the two pulls (branch Inheritance_Log), not a separate population.

Identity: rule 8, the printed ABN decides. Lines are grouped on the 11-digit ABN wherever the register carries one,
so one supplier is one row even where the two registers spell the label differently or TechOne holds two creditor
codes for it. A group with no ABN anywhere is grouped on its contractor label. "Unidentified ..." labels are not
suppliers and stay separate, one row per label per register: they are a queue, not a counterparty.

Route: only AP-ledger lines can be closed by sighting a supplier document. Journal, inventory, payroll and internal
billing lines are reported in a tail section and belong to the journal pull list (rule 21), not here.

Two gaps live on a contractor row and they are not the same thing, so the route is composed rather than picked
from a ladder. IDENTIFICATION (rule 8) is closed by a creditor history carrying an ABN; NATURE (rule 17) is closed
by sighting the document. A supplier can need both, one or neither:

    Port the PS & WP creditor history   a history is embedded in the other register but not in the branch manifest;
                                        it costs nothing to add, so it is always taken first
    Pull the APLEDGER creditor history  identity rests on a narration or a vendor inference, or is unknown
    Sight one invoice                   nothing has ever been sighted, so nature rests on narration, not a document
    Continue the capture                nature is settled but under half the AP value sits on a green block
    Spot-check                          identity and nature both settled; what is left is uncaptured volume

Usage: python3 pbr_contractor_pull.py [branch register.xlsx] [pswp register.xlsx] [outdir]
"""
import collections, datetime as dt, json, os, re, sys
from decimal import Decimal, ROUND_HALF_UP

from python_calamine import CalamineWorkbook
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pbr_stage

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
D = lambda x: Decimal(str(x or 0)).quantize(Decimal('0.01'), ROUND_HALF_UP)
MONEY = '$#,##0.00;($#,##0.00);"-"'
AP_SOURCES = ('AP', 'CT')       # the ledgers a supplier tax invoice posts through
UNID = 'Unidentified'


def latest_branch():
    import glob
    reg = sorted(glob.glob(os.path.join(ROOT, 'registers', 'Parks_Branch_Transaction_Register_FY2627_v*.xlsx')),
                 key=lambda p: int(re.search(r'_v(\d+)\.xlsx$', p).group(1)))
    assert reg, 'no branch register shipped'
    return reg[-1]


def latest_pswp():
    """The newest shipped PS & WP register. Both registers move independently: v128 ported the branch capture
    programme back (182 invoices) and v129 settled every held document, neither of which touched the branch
    register, so pinning this side freezes the evidence coverage of three of the four financial years."""
    import glob
    reg = glob.glob(os.path.join(ROOT, 'registers', 'PS_WP_Transaction_Register_3FY_v*.xlsx'))
    assert reg, 'no PS & WP register shipped'
    # ties on the same number prefer the shipped file over a CANDIDATE of the same version
    return sorted(reg, key=lambda p: (int(re.search(r'_v(\d+)', os.path.basename(p)).group(1)),
                                      'CANDIDATE' not in os.path.basename(p)))[-1]


def file_ver(path):
    """The version in the shipped filename. The PS & WP workbook's own Config stamp stopped being maintained at
    v123 and v127, v128 and v129 all still carry it, so the filename is the only version marker that moves and
    the one this report must quote: it names the file it actually read."""
    m = re.search(r'_v(\d+)', os.path.basename(path))
    return f'v{m.group(1)}' if m else 'v?'


def txt(v):
    if v is None:
        return ''
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def fmt_d(v):
    return v.strftime('%d-%b-%Y') if isinstance(v, (dt.date, dt.datetime)) else txt(v)


def abn_digits(v):
    d = re.sub(r'\D', '', txt(v))
    return d if len(d) == 11 else ''


def abn_print(d):
    """The grouped form the register and the ABR carry: 65 100 395 480."""
    return f'{d[:2]} {d[2:5]} {d[5:8]} {d[8:]}' if len(d) == 11 else (d or '')


def load_register(path, tag, ver=None):
    wb = CalamineWorkbook.from_path(path)
    cfg = {r[0]: r[1] for r in wb.get_sheet_by_name('Config').to_python(skip_empty_area=False) if r and r[0]}
    R = wb.get_sheet_by_name('Register').to_python(skip_empty_area=False)
    ix = {txt(h): i for i, h in enumerate(R[3])}
    a, b = (int(x) for x in str(cfg['REGISTER_DATA']).split(':'))
    rows = [r for r in R[a - 1:b] if txt(r[0])]
    return dict(tag=tag, path=path, file=os.path.basename(path), ver=ver or txt(cfg.get('WORKBOOK_VERSION', 'v?')),
                cfg=cfg, ix=ix, rows=rows, span=f'{a}:{b}',
                total=sum(D(r[ix['Amount ex GST']]) for r in rows), wb=wb)


def histories_held():
    """Creditor codes with a history embedded: the branch manifest, and the PS & WP Creditor_Lines block."""
    branch = {h['code']: h for h in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pbr_histories_v4.json')))['histories']}
    return branch


def pswp_history_codes(reg):
    codes = collections.defaultdict(collections.Counter)
    for r in reg['wb'].get_sheet_by_name('Creditor_Lines').to_python(skip_empty_area=False)[4:]:
        s = txt(r[0])
        if not s:
            continue
        m = re.match(r'^(\w+)\s*\((.*)\)$', s)
        code, lab = (m.group(1), m.group(2)) if m else (s.split(' ')[0], '')
        codes[code][lab] += 1
    return codes


def main():
    bpath = sys.argv[1] if len(sys.argv) > 1 else latest_branch()
    ppath = sys.argv[2] if len(sys.argv) > 2 else latest_pswp()
    OUT = sys.argv[3] if len(sys.argv) > 3 else os.path.join(ROOT, 'reports')

    B = load_register(bpath, 'Branch FY2026/27')
    P = load_register(ppath, 'PS & WP assessed years', ver=file_ver(ppath))
    ver = B['ver']
    BH = histories_held()
    PH = pswp_history_codes(P)

    # ---------------------------------------------------------------- population partition, stated and proved
    bfy = {txt(r[B['ix']['FY (Doc)']]) for r in B['rows']}
    assert bfy == {'FY2026/27'}, bfy
    p_assessed = [r for r in P['rows'] if txt(r[P['ix']['FY (Doc)']]) != 'FY2026/27']
    p_2627 = [r for r in P['rows'] if txt(r[P['ix']['FY (Doc)']]) == 'FY2026/27']
    pop = [(B, r) for r in B['rows']] + [(P, r) for r in p_assessed]
    combined = sum(D(r[reg['ix']['Amount ex GST']]) for reg, r in pop)

    # ---------------------------------------------------------------- group by identity (rule 8: the ABN decides)
    g = lambda reg, r, k: r[reg['ix'][k]]
    abn_of, label_of = {}, {}
    for reg, r in pop:
        lab = txt(g(reg, r, 'Contractor'))
        a_ = abn_digits(g(reg, r, 'ABN'))
        if a_ and not lab.startswith(UNID):
            abn_of.setdefault(lab, collections.Counter())[a_] += 1
    # one label can be spelled two ways across the registers; the ABN is what joins them
    key_of = {}
    for lab, c in abn_of.items():
        key_of[lab] = ('abn', c.most_common(1)[0][0])

    groups = collections.OrderedDict()
    for reg, r in pop:
        lab = txt(g(reg, r, 'Contractor'))
        if lab.startswith(UNID):
            key = ('unid', f'{reg["tag"]} :: {lab}')
        else:
            key = key_of.get(lab, ('label', lab.lower()))
        groups.setdefault(key, []).append((reg, r))

    def tier(v):
        m = re.search(r'[123]', txt(v))
        return int(m.group(0)) if m else None

    out, tail = [], []
    for key, members in groups.items():
        kind = key[0]
        ap = [(reg, r) for reg, r in members if txt(g(reg, r, 'Source')) in AP_SOURCES]
        labels = collections.Counter(txt(g(reg, r, 'Contractor')) for reg, r in members)
        # the label carried with the ABN in the newer register wins, so one COUNTIF-keyed name per supplier
        blabels = collections.Counter(txt(g(reg, r, 'Contractor')) for reg, r in members if reg is B)
        label = (blabels or labels).most_common(1)[0][0]
        abn = key[1] if kind == 'abn' else abn_digits(next((g(reg, r, 'ABN') for reg, r in members if abn_digits(g(reg, r, 'ABN'))), ''))
        codes = sorted({txt(g(reg, r, 'Creditor Code')) for reg, r in members if txt(g(reg, r, 'Creditor Code'))})
        stats = {}
        for tag, want in (('branch', B), ('pswp', P)):
            mm = [(reg, r) for reg, r in members if reg is want]
            aa = [(reg, r) for reg, r in mm if txt(g(reg, r, 'Source')) in AP_SOURCES]
            uns = [(reg, r) for reg, r in aa if not txt(g(reg, r, 'Ev Invoice ID'))]
            # An unsighted line is not automatically an open question. A utility resting on the system record or a
            # journal leg confirmed by pairing is Confirmed without a green block and the rules do not ask for an
            # invoice (Project_Instructions rule 17). What is open is what the register itself calls Partial or
            # Pending evidence, so the queue is ranked on that and the rest is shown beside it, not hidden.
            openv = sum(D(g(reg, r, 'Amount ex GST')) for reg, r in uns if txt(g(reg, r, 'Status')) != 'Confirmed')
            stats[tag] = dict(lines=len(mm), amount=sum(D(g(reg, r, 'Amount ex GST')) for reg, r in mm),
                              ap_lines=len(aa), ap_amount=sum(D(g(reg, r, 'Amount ex GST')) for reg, r in aa),
                              sighted=len({txt(g(reg, r, 'Ev Invoice ID')) for reg, r in mm if txt(g(reg, r, 'Ev Invoice ID'))}),
                              unsighted=sum(D(g(reg, r, 'Amount ex GST')) for reg, r in uns), unsighted_lines=len(uns),
                              open=openv, open_lines=sum(1 for reg, r in uns if txt(g(reg, r, 'Status')) != 'Confirmed'),
                              confirmed_unsighted=sum(D(g(reg, r, 'Amount ex GST')) for reg, r in uns if txt(g(reg, r, 'Status')) == 'Confirmed'))
        dates = sorted(d_ for d_ in (g(reg, r, 'Doc Date') for reg, r in members) if isinstance(d_, (dt.date, dt.datetime)))
        tiers = [t_ for t_ in (tier(g(reg, r, 'Evidence Tier')) for reg, r in members) if t_]
        rec = dict(kind=kind, label=label, abn=abn, codes=codes,
                   lines=len(members), amount=sum(D(g(reg, r, 'Amount ex GST')) for reg, r in members),
                   ap_lines=len(ap), outstanding=sum(v['unsighted'] for v in stats.values()),
                   outstanding_lines=sum(v['unsighted_lines'] for v in stats.values()),
                   open=sum(v['open'] for v in stats.values()), open_lines=sum(v['open_lines'] for v in stats.values()),
                   confirmed_unsighted=sum(v['confirmed_unsighted'] for v in stats.values()),
                   labels=sorted(labels), statuses=', '.join(f'{k} ({n})' for k, n in collections.Counter(txt(g(reg, r, 'Status')) for reg, r in members).most_common()),
                   sighted=sum(v['sighted'] for v in stats.values()),
                   first=fmt_d(dates[0]) if dates else '', last=fmt_d(dates[-1]) if dates else '',
                   best_tier=min(tiers) if tiers else None, stats=stats,
                   sections=', '.join(f'{k} ({n})' for k, n in collections.Counter(txt(g(reg, r, 'Section')) for reg, r in members).most_common(3)),
                   nas=', '.join(f'{k} ({n})' for k, n in collections.Counter(txt(g(reg, r, 'Natural Account')) for reg, r in members).most_common(3)))
        # Identity hygiene, visible on the row because both registers are in view here and nowhere else.
        flags = []
        if kind == 'abn' and len(rec['labels']) > 1:
            flags.append('label spelled {} ways across the registers ({}); a COUNTIF-keyed column must carry one canonical label'
                         .format(len(rec['labels']), '; '.join(rec['labels'])))
        if len(codes) > 1:
            cc = collections.Counter(txt(g(reg, r, 'Creditor Code')) for reg, r in members if txt(g(reg, r, 'Creditor Code')))
            main, n_main = cc.most_common(1)[0]
            odd_codes = [c_ for c_, _ in cc.most_common()[1:]]
            odd_rows = [(reg, r) for reg, r in members if txt(g(reg, r, 'Creditor Code')) in odd_codes]
            named = '; '.join(f'{txt(g(reg, r, "Creditor Code"))} on {reg["tag"]} LineKey {txt(g(reg, r, "LineKey"))}, reference {txt(g(reg, r, "Reference"))}, '
                              f'{fmt_d(g(reg, r, "Doc Date"))}, ${D(g(reg, r, "Amount ex GST")):,.2f}' for reg, r in odd_rows[:4])
            flags.append(f'one ABN on {len(codes)} creditor codes: {main} carries {n_main} lines and {named}. '
                         f'The narration and the sighted evidence on the odd line(s) decide which creditor record is right')
        rec['flags'] = flags
        rec['members'] = members
        rec['ap_members'] = ap
        if not ap:
            tail.append(rec); continue

        # ---------------- the document to pull: largest unsighted AP line carrying an attachment
        cands = [(reg, r) for reg, r in ap if not txt(g(reg, r, 'Ev Invoice ID'))]
        att = [(reg, r) for reg, r in cands if txt(g(reg, r, 'Src Has Attachment')) == 'Y']
        pool = att or cands or ap
        reg0, r0 = max(pool, key=lambda pr: abs(D(g(pr[0], pr[1], 'Amount ex GST'))))
        rec['target'] = dict(register=reg0['tag'], docfile=txt(g(reg0, r0, 'Src Document File')).replace('.0', ''),
                             ref=txt(g(reg0, r0, 'Reference')), date=fmt_d(g(reg0, r0, 'Doc Date')),
                             amount=D(g(reg0, r0, 'Amount ex GST')), pk=txt(g(reg0, r0, 'PK Charged')),
                             na=txt(g(reg0, r0, 'Natural Account')), linekey=txt(g(reg0, r0, 'LineKey')),
                             attachment='Y' if att else 'N', duid=txt(g(reg0, r0, 'Src Document Unique ID')),
                             narration=txt(g(reg0, r0, 'Narration (GL line)')).replace('\n', ' | ')[:120])

        # ---------------- the route. Two gaps live here and they are not the same thing: IDENTIFICATION (rule 8,
        # closed by a creditor history with an ABN) and NATURE (rule 17, closed by sighting the document). A supplier
        # can need both, one, or neither, so the route is composed rather than picked from a ladder, and the primary
        # action is whichever gap is open and cheapest to close. Porting a history already embedded in the other
        # register costs nothing and is always taken first.
        in_branch = any(c in BH for c in codes)
        in_pswp = any(c in PH for c in codes)
        s_b, s_p = rec['stats']['branch'], rec['stats']['pswp']
        ap_value = s_b['ap_amount'] + s_p['ap_amount']
        rec['coverage'] = (ap_value - rec['outstanding']) / ap_value if ap_value else Decimal(0)
        acts, notes = [], []
        if kind == 'unid':
            acts.append('Pull the APLEDGER creditor history' if codes else 'Identify the creditor, then pull its APLEDGER history')
            notes.append('No contractor evidence on any line (Tier 3). ' +
                         (f'TechOne carries creditor code {", ".join(codes)} on these lines, so the history can be requested directly.'
                          if codes else 'No creditor code is carried on these lines, so an attachment has to name the creditor first.'))
            if s_b['unsighted_lines'] + s_p['unsighted_lines'] > 1:
                notes.append(f'This label is a queue, not one counterparty: {rec["outstanding_lines"]:,} lines that have not been separated into suppliers yet. '
                             f'One sighting does not close it. The series breakdown, one invoice to sight per supplier series, is in Unidentified_Contractors_{ver}.')
        else:
            if not in_branch and in_pswp:
                acts.append('Port the PS & WP creditor history')
                notes.append(f'A history for {", ".join(c for c in codes if c in PH)} is already embedded in the PS & WP register but not in the branch manifest. '
                             f'Add it to toolkit/branch/pbr_histories_v4.json from the copy already held: nothing has to be requested of Finance.')
            elif not in_branch and not in_pswp and rec['best_tier'] and rec['best_tier'] > 1:
                acts.append('Pull the APLEDGER creditor history')
                notes.append(f'Identity rests on a narration or a vendor inference (Tier {rec["best_tier"]}), not on a creditor record with an ABN (rule 8). '
                             + (f'Request the history for {", ".join(codes)}.' if codes else 'No creditor code is carried on the lines; read it from the attachment first.'))
            if rec['open'] == 0 and rec['outstanding'] == 0:
                pass
            elif rec['open'] == 0:
                acts.append('No action')
                notes.append(f'${rec["confirmed_unsighted"]:,.2f} carries no green block but the register already confirms it on another basis '
                             f'(a utility on the system record, or a journal leg confirmed by pairing). Rule 17 does not ask for an invoice there.')
            elif rec['sighted'] == 0:
                acts.append('Sight one invoice')
                notes.append(f'No invoice has ever been sighted for this supplier, so nature rests on narration or the creditor record rather than on a document (rule 17). '
                             f'One sighting settles what the money buys; the rest of the spend then follows the same nature unless a line says otherwise.')
            elif rec['coverage'] < Decimal('0.5') and rec['open']:
                acts.append('Continue the capture')
                notes.append(f'{rec["sighted"]} invoice(s) sighted, but only {rec["coverage"]:.0%} of ${ap_value:,.2f} of AP spend sits on a green block. '
                             f'Nature is settled; what is missing is coverage, so this is a batch to capture rather than a single sighting.')
            else:
                acts.append('Spot-check')
                notes.append(f'{rec["sighted"]} invoice(s) sighted covering {rec["coverage"]:.0%} of ${ap_value:,.2f} of AP spend. Nature and identity are both settled; '
                             f'${rec["outstanding"]:,.2f} is uncaptured volume, not an open question.')
            if s_b['unsighted'] and s_p['unsighted'] and rec['sighted']:
                notes.append(f'Both registers carry unsighted spend: ${s_p["unsighted"]:,.2f} in the assessed years and ${s_b["unsighted"]:,.2f} in FY2026/27.')
            elif s_b['unsighted'] and rec['sighted'] and not s_p['unsighted']:
                notes.append(f'The assessed years are fully captured; the ${s_b["unsighted"]:,.2f} outstanding is all FY2026/27.')
            elif s_p['unsighted'] and rec['sighted'] and not s_b['unsighted']:
                notes.append(f'FY2026/27 is fully captured; the ${s_p["unsighted"]:,.2f} outstanding is all in the assessed years.')
        if not acts and flags:
            acts.append('Housekeeping only')
        rec['route'] = ', then '.join(acts) if acts else 'Nothing outstanding'
        if flags:
            notes.append('Flag: ' + '; '.join(flags) + '.')
        rec['why'] = ' '.join(notes) or 'Every AP line is on a sighted invoice and identity rests on a creditor record with an ABN.'
        rec['history'] = ('both registers' if in_branch and in_pswp else 'branch only' if in_branch
                          else 'PS & WP only' if in_pswp else 'none held')
        out.append(rec)

    named = {s['label'].lower(): s for s in out + tail if s['abn']}
    for s in out + tail:
        if s['abn'] or s['kind'] == 'unid':
            continue
        lab = s['label'].lower()
        hit = next((o for k_, o in named.items() if k_ != lab and (k_.startswith(lab + ' ') or lab.startswith(k_ + ' ') or k_.startswith(lab + ',') or lab.startswith(k_ + ','))), None)
        if hit:
            s['flags'].append(f'no ABN is carried on these {s["lines"]} line(s), and the label reads as a short form of "{hit["label"]}" (ABN {abn_print(hit["abn"])}). '
                              f'They are kept apart here because rule 8 never carries an ABN from one line onto an inferred one: confirm from the creditor record or a sighted '
                              f'invoice, and canonicalise the label if they are the same supplier')
            s['why'] = (s['why'] + ' Flag: ' + s['flags'][-1] + '.').strip()
            if s['route'] == 'Nothing outstanding':
                s['route'] = 'Housekeeping only'
    out.sort(key=lambda s: (-abs(s['open']), -abs(s['outstanding'])))
    # One row per contractor, register and reference: the invoice numbers behind each contractor row. Built once,
    # because both the markdown and the workbook quote it and they must not be able to disagree.
    refs = []
    for rank, s_ in enumerate(out, 1):
        by_ref = collections.OrderedDict()
        for reg, r in s_['ap_members']:
            by_ref.setdefault((reg['tag'], txt(g(reg, r, 'Reference'))), []).append((reg, r))
        block = []
        for (rtag, ref), lines_ in by_ref.items():
            amt = sum(D(g(reg, r, 'Amount ex GST')) for reg, r in lines_)
            evid = sorted({txt(g(reg, r, 'Ev Invoice ID')) for reg, r in lines_ if txt(g(reg, r, 'Ev Invoice ID'))})
            openv = sum(D(g(reg, r, 'Amount ex GST')) for reg, r in lines_
                        if not txt(g(reg, r, 'Ev Invoice ID')) and txt(g(reg, r, 'Status')) != 'Confirmed')
            pull = 'Yes' if openv else ('No, sighted' if evid else 'No, confirmed otherwise')
            dates = sorted(d_ for d_ in (g(reg, r, 'Doc Date') for reg, r in lines_) if isinstance(d_, (dt.date, dt.datetime)))
            block.append(dict(pull=pull, rank=rank, rec=s_, register=rtag, ref=ref, lines=lines_, amount=amt, open=openv,
                              evid=evid, dates=dates,
                              statuses=collections.Counter(txt(g(reg, r, 'Status')) for reg, r in lines_)))
        refs += sorted(block, key=lambda x: (x['pull'] != 'Yes', -abs(x['open']), -abs(x['amount'])))
    nref = len(refs)
    ref_pull = [x['pull'] for x in refs]
    tail.sort(key=lambda s: -abs(s['amount']))
    os.makedirs(OUT, exist_ok=True)
    stamp = pbr_stage.stamp()
    live = [s for s in out if s['route'] != 'Nothing outstanding']
    outstanding = sum(s['outstanding'] for s in out)

    # ---------------------------------------------------------------- markdown
    open_v = sum(s['open'] for s in out)
    conf_v = sum(s['confirmed_unsighted'] for s in out)
    ap_v = sum(s['stats']['branch']['ap_amount'] + s['stats']['pswp']['ap_amount'] for s in out + tail)
    needs = [s for s in out if s['open'] > 0]
    md = [f'# Contractor pull list, both registers ({stamp})', '',
          f'**Position:** {len(out)} contractors carry AP-ledger spend across the two registers. {len(needs)} of them have an open evidence gap worth '
          f'${open_v:,.2f} ex GST over {sum(s["open_lines"] for s in out):,} lines. The table is ranked on that figure, so the top of it is the largest exposure '
          f'the register itself still calls Partial or Pending evidence.', '',
          '## What is and is not outstanding', '',
          '| Measure | Lines | $ ex GST |', '|---|---:|---:|',
          f'| AP-ledger spend, both registers | {sum(s["ap_lines"] for s in out + tail):,} | {ap_v:,.2f} |',
          f'| On a sighted invoice (rule 17 green block) | {sum(s["ap_lines"] for s in out + tail) - sum(s["outstanding_lines"] for s in out + tail):,} | {ap_v - outstanding:,.2f} |',
          f'| No green block, register status Confirmed on another basis | {sum(s["outstanding_lines"] - s["open_lines"] for s in out):,} | {conf_v:,.2f} |',
          f'| **No green block, Partial or Pending evidence: the queue** | **{sum(s["open_lines"] for s in out):,}** | **{open_v:,.2f}** |', '',
          'A line without a green block is not automatically an open question. A utility resting on the system record and a journal leg confirmed by pairing are '
          'Confirmed without an invoice and rule 17 does not ask for one, so they are shown above and excluded from the ranking. What is left is the queue.', '',
          '## Population', '',
          '| Register | Scope | Lines | $ ex GST |', '|---|---|---:|---:|',
          f'| `{B["file"]}` {B["ver"]} | FY2026/27, branch 4090000, all ten sections | {len(B["rows"]):,} | {B["total"]:,.2f} |',
          f'| `{P["file"]}` {P["ver"]} | FY2023/24 to FY2025/26, Park Services and Water Parks | {len(p_assessed):,} | {sum(D(r[P["ix"]["Amount ex GST"]]) for r in p_assessed):,.2f} |',
          f'| **Combined** | four financial years, nothing counted twice | **{len(pop):,}** | **{combined:,.2f}** |', '',
          f'The branch register inherits the PS & WP FY2026/27 block line by line and supersedes it, so the {len(p_2627):,} PS & WP FY2026/27 lines '
          f'(${sum(D(r[P["ix"]["Amount ex GST"]]) for r in p_2627):,.2f}) are not read here. The handful the branch pull did not carry are on the branch Inheritance_Log, '
          'a difference between two pulls rather than a separate population.', '',
          'Identity is the printed ABN (rule 8), so one supplier is one row even where the two registers spell the label differently or TechOne holds two creditor '
          'codes for it. Only AP-ledger lines appear: a journal, an inventory issue or an internal billing line cannot be closed by sighting a supplier document, '
          'and those are listed at the foot and belong to the journal pull list (rule 21).', '',
          '## Contractors with evidence outstanding', '',
          '| # | Contractor | ABN | Codes | History | Lines | $ ex GST | $ open | Sighted | Cover | Route | Pull: register | Document File | Ref | $ line | Att |',
          '|---|---|---|---|---|---:|---:|---:|---:|---:|---|---|---|---|---:|---|']
    for k, s in enumerate(live, 1):
        t_ = s['target']
        md.append(f"| {k} | {s['label'][:46]}{' (flagged)' if s['flags'] else ''} | {abn_print(s['abn']) or '-'} | {', '.join(s['codes']) or '-'} | {s['history']} | {s['lines']:,} | {s['amount']:,.2f} | "
                  f"{s['open']:,.2f} | {s['sighted']} | {s['coverage']:.0%} | {s['route']} | {t_['register']} | **{t_['docfile'] or '-'}** | {t_['ref']} | {t_['amount']:,.2f} | {t_['attachment']} |")
    md += ['', '## Why each row is on the list', '']
    for k, s in enumerate(live, 1):
        md.append(f"{k}. **{s['label']}** ({s['route']}). {s['why']} Spend: {s['stats']['pswp']['lines']:,} lines ${s['stats']['pswp']['amount']:,.2f} in the assessed years, "
                  f"{s['stats']['branch']['lines']:,} lines ${s['stats']['branch']['amount']:,.2f} in FY2026/27, {s['first']} to {s['last']}.")
    flagged = [s for s in out + tail if s.get('flags')]
    if flagged:
        md += ['', '## Identity flags', '',
               'Both registers are in view here and nowhere else, so these show up only on this report.', '']
        for s in flagged:
            md.append(f"- **{s['label']}** (ABN {abn_print(s['abn']) or 'not carried'}): " + '; '.join(s['flags']) + '.')
    done = [s for s in out if s['route'] == 'Nothing outstanding']
    md += ['', '## Contractors with nothing outstanding', '',
           f'{len(done)} contractors carry AP spend with every line on a sighted invoice: '
           + ', '.join(f'{s["label"]} (${s["amount"]:,.2f})' for s in done[:20]) + ('.' if len(done) <= 20 else ', and others.'), '']
    md += ['## Not on this list', '',
           f'{len(tail)} labels carry no AP-ledger line, so no supplier document can close them: '
           + '; '.join(f'{s["label"]} ({s["lines"]:,} lines, ${s["amount"]:,.2f})' for s in tail[:10]) + '. '
           'These are journals, inventory issues, payroll and internal billing. Journals go through the rule 21 journal pull list '
           f'(`Journal_Pull_{ver}.md`); internal charges rest on the system record.', '',
           '## How to use', '',
           '1. Rows are ranked on the open gap, so the top of the table is the largest spend the register itself still calls Partial or Pending evidence.',
           '2. **Port the PS & WP creditor history** needs nothing from Finance: the history is already embedded in the other register and only has to be added to `toolkit/branch/pbr_histories_v4.json`, after which the next build identifies every line on that code (Method 12.0).',
           '3. **Pull the APLEDGER creditor history** is one email: request the Ledger Accounts Transactions Table (Default Ledger Type = AP, one Account) for the creditor codes listed. Where no code is carried, the attachment on the named Document File has to name the creditor first.',
           '4. **Sight one invoice** is one TechOne sighting: open the Document File named, capture the invoice at line level under rule 16, and the green block closes the line and settles the nature of the rest.',
           '5. **Continue the capture** and **Spot-check** need no new request. Identity and nature are settled and what is left is capture volume, so they sit below the rows that need a document even where the dollars are larger.',
           '6. Identity flags are housekeeping, not evidence: they cost nothing to fix and they stop a COUNTIF-keyed panel splitting one supplier in two.',
           '',
           f'## The workbook', '',
           f'`Contractor_Pull_{ver}.xlsx` carries three sheets. **Contractors** is the table above, one row per supplier, filterable. '
           f'**References** is every AP reference behind it, {nref:,} rows over {sum(s_["ap_lines"] for s_ in out):,} register lines: one row per contractor, register and '
           f'invoice number, so a request can be made invoice by invoice. Filter column A on "Yes" for the {sum(1 for x in ref_pull if x == "Yes"):,} references that still carry '
           f'unevidenced value; "$ ex GST" is the whole reference and "$ open" is only the unevidenced part, which sums to ${open_v:,.2f}. '
           f'**Not a contractor route** is the journal, inventory, payroll and internal billing labels no supplier document can close.',
           '', f'Sources: `{B["file"]}` Register rows {B["span"]}; `{P["file"]}` Register rows {P["span"]}. Generated by `toolkit/branch/pbr_contractor_pull.py`.']
    open(os.path.join(OUT, f'Contractor_Pull_{ver}.md'), 'w', encoding='utf-8').write('\n'.join(md) + '\n')

    # ---------------------------------------------------------------- workbook
    xw = Workbook(); ws = xw.active; ws.title = 'Contractors'
    hf = Font(name='Cambria', bold=True, color='FFFFFF'); fill = PatternFill('solid', fgColor='1F3864')
    ws.append([f'Contractor pull list, both registers ({stamp}): {len(out)} contractors on the AP ledger, {len(needs)} with an open evidence gap worth ${open_v:,.2f} ex GST '
               f'of ${ap_v:,.2f} AP spend. A further ${conf_v:,.2f} carries no green block but is Confirmed on another basis (utility on the system record, journal leg '
               f'confirmed by pairing) and is not in the ranking. Branch {B["ver"]} FY2026/27 + PS & WP {P["ver"]} FY2023/24 to FY2025/26, ${combined:,.2f} combined, nothing counted twice.'])
    ws.append([])
    cols = ['#', 'Contractor', 'ABN', 'Creditor codes', 'History held', 'Route', 'Why', 'Lines (both)', '$ ex GST (both)', '$ outstanding', 'Outstanding lines',
            'Invoices sighted', 'Best tier', 'First doc date', 'Last doc date', 'Sections (lines)', 'Natural accounts (lines)',
            'PS&WP lines', 'PS&WP $', 'PS&WP sighted', 'PS&WP $ unsighted', 'Branch lines', 'Branch $', 'Branch sighted', 'Branch $ unsighted',
            'PULL: register', 'PULL: Document File', 'PULL: Reference', 'PULL: Doc date', 'PULL: $ ex GST', 'PULL: PK', 'PULL: NA', 'PULL: Attachment', 'PULL: LineKey', 'PULL: Narration']
    ws.append(cols)
    for c in ws[3]:
        c.font = hf; c.fill = fill
    for k, s in enumerate(out, 1):
        t_ = s['target']; sb = s['stats']['branch']; sp = s['stats']['pswp']
        ws.append([k, s['label'], abn_print(s['abn']), ', '.join(s['codes']), s['history'], s['route'], s['why'], s['lines'], float(s['amount']), float(s['outstanding']),
                   s['outstanding_lines'], s['sighted'], s['best_tier'], s['first'], s['last'], s['sections'], s['nas'],
                   sp['lines'], float(sp['amount']), sp['sighted'], float(sp['unsighted']),
                   sb['lines'], float(sb['amount']), sb['sighted'], float(sb['unsighted']),
                   t_['register'], t_['docfile'], t_['ref'], t_['date'], float(t_['amount']), t_['pk'], t_['na'], t_['attachment'], t_['linekey'], t_['narration']])
        for col in (9, 10, 19, 21, 23, 25, 30):
            ws.cell(ws.max_row, col).number_format = MONEY
    widths = [5, 44, 14, 16, 14, 40, 80, 11, 15, 15, 12, 9, 8, 12, 12, 30, 24, 11, 15, 9, 16, 11, 15, 9, 16, 22, 16, 16, 12, 14, 11, 8, 10, 30, 60]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = w
    ws.freeze_panes = 'C4'
    ws.auto_filter.ref = f'A3:{ws.cell(3, len(cols)).column_letter}{ws.max_row}'

    # ---------------------------------------------------------------- one row per reference (the invoice number)
    # The summary above names one document per contractor. This sheet is every AP reference behind it, so a request
    # can be made invoice by invoice: one row per contractor, register and reference, with the lines of that
    # reference summed. A reference can post as many lines (a consolidated electricity invoice posts as 361), so the
    # line count is carried beside the value and the PKs it hits are listed.
    wr = xw.create_sheet('References')
    rcols = ['Pull?', 'Contractor rank', 'Contractor', 'ABN', 'Route', 'Register', 'FY', 'Reference (invoice number)', 'Doc date', 'Doc type',
             'Lines', '$ ex GST', '$ open (no green block, Partial or Pending)', 'Register status', 'Sighted (Ev Invoice ID)', 'Attachment in TechOne', 'Document File', 'Document Unique ID',
             'Section(s)', 'Natural account(s)', 'PK charged (lines)', 'Creditor code', 'Narration (GL line)', 'Follow-up']
    wr.append([f'Every AP reference behind the contractor list ({stamp}). "Pull?" is the filter: Yes means some of the reference still carries no green block and the register '
               f'calls it Partial or Pending evidence; "No, sighted" means it is captured under rule 17; "No, confirmed otherwise" means a utility on the system record or a journal '
               f'leg confirmed by pairing, which rule 17 does not ask an invoice for. "$ ex GST" is the whole reference; "$ open" is only the part still unevidenced, and that column '
               f'sums to the ${open_v:,.2f} on the Contractors sheet.'])
    wr.append([])
    wr.append(rcols)
    for c in wr[3]:
        c.font = hf; c.fill = fill
    for x in refs:
        lines_ = x['lines']; s_ = x['rec']
        att = 'Y' if any(txt(g(reg, r, 'Src Has Attachment')) == 'Y' for reg, r in lines_) else 'N'
        docf = sorted({txt(g(reg, r, 'Src Document File')).replace('.0', '') for reg, r in lines_ if txt(g(reg, r, 'Src Document File'))})
        duid = sorted({txt(g(reg, r, 'Src Document Unique ID')) for reg, r in lines_ if txt(g(reg, r, 'Src Document Unique ID'))})
        pks = collections.Counter(txt(g(reg, r, 'PK Charged')) for reg, r in lines_)
        fu = sorted({txt(g(reg, r, 'Follow-up')) for reg, r in lines_ if txt(g(reg, r, 'Follow-up'))})
        wr.append([x['pull'], x['rank'], s_['label'], abn_print(s_['abn']), s_['route'], x['register'],
                   ', '.join(sorted({txt(g(reg, r, 'FY (Doc)')) for reg, r in lines_})), x['ref'],
                   fmt_d(x['dates'][0]) if x['dates'] else '',
                   collections.Counter(txt(g(reg, r, 'Doc Type')) for reg, r in lines_).most_common(1)[0][0],
                   len(lines_), float(x['amount']), float(x['open']),
                   ', '.join(f'{k} ({n})' for k, n in x['statuses'].most_common()), ', '.join(x['evid']),
                   att, ', '.join(docf[:3]), ', '.join(duid[:2]),
                   ', '.join(sorted({txt(g(reg, r, 'Section')) for reg, r in lines_})),
                   ', '.join(sorted({txt(g(reg, r, 'Natural Account')) for reg, r in lines_})),
                   ', '.join(f'{k} ({n})' for k, n in pks.most_common(6)),
                   ', '.join(sorted({txt(g(reg, r, 'Creditor Code')) for reg, r in lines_ if txt(g(reg, r, 'Creditor Code'))})),
                   txt(g(lines_[0][0], lines_[0][1], 'Narration (GL line)')).replace('\n', ' | ')[:200], ' | '.join(fu)[:200]])
        wr.cell(wr.max_row, 12).number_format = MONEY; wr.cell(wr.max_row, 13).number_format = MONEY
    for i, w in enumerate([13, 9, 40, 14, 34, 22, 11, 26, 12, 18, 7, 14, 16, 24, 20, 10, 18, 34, 20, 18, 30, 12, 60, 50], 1):
        wr.column_dimensions[wr.cell(1, i).column_letter].width = w
    wr.freeze_panes = 'C4'
    wr.auto_filter.ref = f'A3:{wr.cell(3, len(rcols)).column_letter}{wr.max_row}'

    wt = xw.create_sheet('Not a contractor route')
    wt.append(['Label', 'Lines', '$ ex GST', 'Sections (lines)', 'Natural accounts (lines)', 'First', 'Last', 'Why it is not here'])
    for c in wt[1]:
        c.font = hf; c.fill = fill
    for s in tail:
        wt.append([s['label'], s['lines'], float(s['amount']), s['sections'], s['nas'], s['first'], s['last'],
                   'No AP-ledger line: a journal, inventory issue, payroll or internal billing cannot be closed by sighting a supplier document (rule 21 route).'])
        wt.cell(wt.max_row, 3).number_format = MONEY
    for i, w in enumerate([44, 10, 16, 30, 24, 12, 12, 90], 1):
        wt.column_dimensions[wt.cell(1, i).column_letter].width = w
    wt.freeze_panes = 'A2'
    xw.save(os.path.join(OUT, f'Contractor_Pull_{ver}.xlsx'))

    print(f'{nref:,} references on the References sheet')
    print(f'{len(out)} contractors, {len(needs)} with an open evidence gap, ${open_v:,.2f} of ${ap_v:,.2f} AP spend '
          f'({conf_v:,.2f} unsighted but Confirmed on another basis) -> {OUT}/Contractor_Pull_{ver}.md and .xlsx')
    for s in needs[:12]:
        print(f"  {s['label'][:38]:40} {s['history']:14} open ${s['open']:>12,.2f}  cover {s['coverage']:>4.0%}  {s['route'][:40]:42} DocFile {s['target']['docfile']}")
    if flagged:
        print(f'  identity flags on {len(flagged)}: ' + '; '.join(s['label'][:30] for s in flagged))


if __name__ == '__main__':
    main()
