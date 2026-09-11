"""pbr_build.py - Parks Branch Transaction Register FY2026/27 v1. ONE script, whole chain (rule 19.7):
stage (pbr_stage.main) -> write (openpyxl write-only) -> convert-route recalc -> calamine verify -> ship.
A partial run is discarded: the workbook is written to a scratch name and promoted only on a clean verify.
"""
import collections, datetime as dt, gc, json, os, pickle, re, shutil, subprocess, sys, tempfile, time
from decimal import Decimal
from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.workbook.defined_name import DefinedName
from python_calamine import CalamineWorkbook

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pbr_stage

VER = 'v6'
OUTNAME = f'Parks_Branch_Transaction_Register_FY2627_{VER}.xlsx'
CLTOK = re.compile(r'\{CL:(\d+):(\d+)\}')
SCRATCH = os.path.join(pbr_stage.ROOT, 'cache', 'scratch')
OUTDIR = os.environ.get('PBR_OUTDIR', os.path.join(pbr_stage.ROOT, 'registers'))
BUILD_DATE = '11-Sep-2026'
MONEY = '$#,##0.00;($#,##0.00);"-"'
DATEF = 'd-mmm-yyyy'
T0 = time.time()
LOG = []

def say(s):
    line = f'[{time.time() - T0:6.1f}s] {s}'
    LOG.append(line); print(line, flush=True)

def CL(n):
    s = ''
    while n:
        n, r = divmod(n - 1, 26); s = chr(65 + r) + s
    return s

def D(x):
    return pbr_stage.D(x)

def fmt_money(x):
    x = D(x)
    return f'(${-x:,.2f})' if x < 0 else f'${x:,.2f}'

# ------------------------------------------------------------------------------ styles
F_TITLE = Font(name='Cambria', size=14, bold=True, color='1F3864')
F_SUB = Font(name='Cambria', size=10, italic=True, color='404040')
F_BOLD = Font(name='Cambria', size=10, bold=True)
F_HDR = Font(name='Cambria', size=10, bold=True, color='FFFFFF')
F_INPUT = Font(name='Cambria', size=10, color='0000FF')
FILL = {k: PatternFill('solid', fgColor=c) for k, c in dict(blue='1F3864', grey='595959', green='375623', axis='5B3A7A',
                                                          band='D9E1F2', tot='FFF2CC').items()}
WRAP = Alignment(wrap_text=True, vertical='top')


class Sheet:
    def __init__(self, wb, name, widths=None, freeze=None):
        self.ws = wb.create_sheet(name)
        self.name = name
        self.n = 0
        if widths:
            for k, w in widths.items():
                self.ws.column_dimensions[k].width = w
        if freeze:
            self.ws.freeze_panes = freeze

    def cell(self, v, font=None, fill=None, nf=None, wrap=False):
        c = WriteOnlyCell(self.ws, value=v)
        if font: c.font = font
        if fill: c.fill = FILL[fill]
        if nf: c.number_format = nf
        if wrap: c.alignment = WRAP
        return c

    def row(self, vals=(), style=None, money_cols=(), date_cols=(), input_cols=()):
        out = []
        for j, v in enumerate(vals, 1):
            if v == '':
                v = None
            if style == 'title': out.append(self.cell(v, F_TITLE) if j == 1 else v)
            elif style == 'sub': out.append(self.cell(v, F_SUB) if j == 1 else v)
            elif style in ('blue', 'grey', 'green', 'axis'): out.append(self.cell(v, F_HDR, style))
            elif style == 'tot': out.append(self.cell(v, F_BOLD, 'tot', MONEY if j in money_cols else None))
            elif style == 'bold': out.append(self.cell(v, F_BOLD))
            elif j in money_cols and v is not None: out.append(self.cell(v, F_INPUT if j in input_cols else None, None, MONEY))
            elif j in date_cols and isinstance(v, (dt.date, dt.datetime)): out.append(self.cell(v, None, None, DATEF))
            elif j in input_cols and v is not None: out.append(self.cell(v, F_INPUT))
            else: out.append(v)
        self.ws.append(out)
        self.n += 1
        return self.n

    def blank(self, k=1):
        for _ in range(k):
            self.row([])


def esc(s):
    return re.sub(r'([~*?])', r'~\1', s)


def build(stage):
    rows = stage['rows']; se2 = stage['se2']; L = stage['L']
    N = len(rows); FIRST = 5; LAST = FIRST + N - 1; TOT = LAST + 2
    v127 = pickle.load(open(os.path.join(pbr_stage.CACHE, 'v127.pkl'), 'rb'))
    forms = json.load(open(os.path.join(pbr_stage.CACHE, 'v127_fy2627_forms.json')))
    theme_v2, theme_v3 = stage['theme_v2'], stage['theme_v3']
    TM_LAST = 4 + len(theme_v2); T3_LAST = 4 + len(theme_v3)
    sec_names = stage['sec_names']; svc_names = stage['svc_names']; na_names = stage['na_names']
    SECTIONS = sorted(sec_names, key=lambda c: (c == 'NA', c))
    UNID = pbr_stage.RULES['unidentified_label']
    T9 = [b for a, b in theme_v2 if b.startswith('T9')][0]
    INH, NEW = 'Inherited from PS_WP register v127', 'New at branch v1 (not in the PS_WP register)'
    total = sum(D(r['V'][20]) for r in rows)
    assert total == D('4910566.68')

    # ---------------------------------------------------------------- consistency gates on the analysis keys
    for r in rows:
        V = r['V']
        assert str(V[2]) == str(V[81]), ('section', V[1])
        assert str(V[14]) == str(V[76]), ('na', V[1])
        assert str(V[19]) == str(V[77]), ('svc', V[1])
        want16 = V[84].strip() or '(no WO Task)'
        if str(V[16]) != want16:
            raise AssertionError(('pkheader', V[1], V[16], V[84]))
        if r['meta'].get('ported'):
            V[148] = INH + f'; sighted at branch {r["meta"].get("ported_ver", "v3")} (port the capture to PS_WP v128)'
        elif r['meta'].get('ident_v4'):
            V[148] = INH + f'; contractor identified at branch {r["meta"].get("ident_ver", "v4")} from APLEDGER {r["meta"]["ident_v4"]} (port to PS_WP v128)'
        else:
            V[148] = INH if r['meta']['inherited'] else NEW
    say('gate analysis keys agree with the grey source block on all lines')
    ident_rows = [r for r in rows if r['meta'].get('ident_v4')]

    # ---------------------------------------------------------------- evidence carry maps
    sighted = stage['sighted']; evids = stage['evids']
    EI = v127['Evidence_Invoices']; EIL = v127['Evidence_Invoice_Lines']; EILC = v127['EIL_Controls']; VB = v127['Vendor_Boilerplate']
    evn = stage['ev_new']
    carried = [e for e in evids if e not in evn['ei']]
    ei_rows = {r[0]: (i + 1, r, 'v127 Evidence_Invoices row %d: %s' % (i + 1, r[12])) for i, r in enumerate(EI[4:3875], 4) if r[0] in carried}
    assert len(ei_rows) == len(carried)
    ei_rows.update(evn['ei'])
    ev_order = carried + evn['order']
    assert set(ev_order) == set(evids), set(evids) ^ set(ev_order)
    ei_new = {e: 5 + k for k, e in enumerate(ev_order)}
    eil_lines = []
    for e in carried:
        eil_lines += [list(r[:13]) for r in EIL[4:9517] if r[0] == e]
    eil_lines += evn['eil']
    eil_span = {}
    for k, r in enumerate(eil_lines, 5):
        a, b = eil_span.get(r[0], (k, k)); eil_span[r[0]] = (min(a, k), max(b, k))
    eil_sum = collections.defaultdict(Decimal)
    for r in eil_lines:
        if r[6] not in (None, ''):
            eil_sum[r[0]] += D(r[6])
    for e in ev_order:
        assert D(ei_rows[e][1][9]) == eil_sum[e], e
    eilc_basis = {r[0]: r[3] for r in EILC[4:3875]}; eilc_basis.update(evn['basis'])
    bp_cited = sorted({r['V'][c] for r in sighted for c in (118, 119) if str(r['V'][c]).startswith('BP:')})
    vb_rows = [list(r[:6]) for r in VB[4:] if r[0] in bp_cited] + [row for row in evn['vb'] if row[0] in bp_cited]
    assert len(vb_rows) == len(bp_cited), (len(vb_rows), len(bp_cited))
    assert len({row[0] for row in vb_rows}) == len(vb_rows)
    EI_LAST = 4 + len(ev_order); EIL_LAST = 4 + len(eil_lines)
    say(f'evidence carry: {len(ev_order)} invoices, {len(eil_lines)} lines, {len(vb_rows)} boilerplate keys')

    # ---------------------------------------------------------------- citation restatement (rule 19.10)
    v2new = stage['v2new']
    reg_rows_by_ev = collections.defaultdict(list)
    for r in sighted:
        reg_rows_by_ev[r['V'][88]].append(r['row'])
    strip_pats = [r';?\s*line capture Evidence_Invoice_Lines rows \d+\s*-\s*\d+;\s*reconciliation row \d+\.?',
                  r'\s*Line capture on Evidence_Invoice_Lines;\s*reconciliation row \d+\.?',
                  r';?\s*reconciliation (?:at )?(?:Evidence_Invoice_Lines |EIL_Controls )?row \d+\.?']
    cite_changes = collections.Counter()
    for r in sighted:
        V = r['V']; t = str(V[28] or '')
        for p in strip_pats:
            t, k = re.subn(p, '', t, flags=re.I); cite_changes['col28_clauses_removed'] += k
        a, b = eil_span[V[88]]
        V[28] = (t.rstrip(' .;') + f'. Line capture Evidence_Invoice_Lines rows {a}-{b}; reconciliation EIL_Controls row {ei_new[V[88]]} '
                 f'(citation restated at branch v1 from the EvID maps, rule 19.10).')
        rest = re.sub(r'Evidence_Invoice_Lines rows \d+-\d+; reconciliation EIL_Controls row \d+', '', V[28])
        assert not re.search(r'\brows? \d{3,}', rest), ('stale citation', V[1], V[28][:300])
    sighted_set = {id(r) for r in sighted}
    rowrx = re.compile(r'(?<!Lines )(?<!reconciliation )\b(rows?) (\d{3,5})((?:(?: and |\s*\+\s*|, )\d{3,5})*)')
    def remap_text(t):
        def rep(m):
            nums = re.findall(r'\d{3,5}', m.group(0))
            if not all(int(x) in v2new for x in nums):
                return m.group(0)
            cite_changes['row_citations_remapped'] += len(nums)
            new = ' and '.join(str(v2new[int(x)]) for x in nums)
            return f'Register {m.group(1)} {new} (v127 {m.group(1)} {", ".join(nums)})'
        return rowrx.sub(rep, t)
    for r in rows:
        if not r['meta']['inherited']:
            continue
        V = r['V']
        for c in ((32, 34, 127) if id(r) in sighted_set else (28, 32, 34, 127)):
            if isinstance(V[c], str) and re.search(r'\brows? \d{3,5}', V[c]):
                V[c] = remap_text(V[c])
    say(f'citations: {dict(cite_changes)}')

    # ---------------------------------------------------------------- journal sets
    jref_rows = collections.defaultdict(list)
    for r in rows:
        if r['V'][137]:
            r['V'][137] = pbr_stage.clean_num_text(r['V'][137])
            jref_rows[r['V'][137]].append(r)
    jrefs = sorted(jref_rows)
    for j in jrefs:
        assert not re.search(r'[~*?]', j) and not j.startswith(('=', '<', '>')), j
    JS_LAST = 4 + len(jrefs); JS_TOT = JS_LAST + 2
    jnet = {j: sum(D(r['V'][20]) for r in jref_rows[j]) for j in jrefs}
    js_zero = sum(1 for j in jrefs if jnet[j] == 0)
    reclass = [j for j in jrefs if jnet[j] == 0 and any(r['meta']['inherited'] and (r['V'][33] == 'Partial' or r['V'][31] in ('Review', 'Journal (reversal)')) for r in jref_rows[j])]
    say(f'journal sets {len(jrefs)}, net-zero {js_zero}, inherited open sets now pairing at branch scope {len(reclass)}')

    # ============================================================== Journal_Pull (rule 21)
    jsrc_held = {str(r[1]).replace('.0', '') for r in v127['Journal_Sources'][4:] if r[0] and str(r[1]).replace('.0', '').isdigit()}
    jp_doc = collections.defaultdict(list)
    for r in rows:
        if r['V'][137]:
            jp_doc[pbr_stage.clean_num_text(r['V'][69])].append(r)
    jp_rows = []
    for df, jr in jp_doc.items():
        refs = sorted({str(x['V'][137]) for x in jr})
        net = sum(D(x['V'][20]) for x in jr)
        gross = sum(abs(D(x['V'][20])) for x in jr)
        att = 'Y' if any(str(x['V'][62]).strip() == 'Y' for x in jr) else 'N'
        all_rj = all(r_.startswith('RJ') for r_ in refs)
        acc = acc0 = collections.Counter('%s %s' % (x['V'][14], str(x['V'][15])[:22]) for x in jr)
        tier = ('D Held, already embedded in PS_WP v127' if df in jsrc_held else
                'C RJ reversal, no pull' if all_rj else
                'A Pull required' if att == 'N' else 'B Sight attachment')
        zero = all(jnet[r_] == 0 for r_ in refs)
        why, val = [], 'Low'
        if any(x['V'][31] == 'Review' for x in jr):
            why.append('recode set does not net inside O110-O115, so the balancing leg sits outside this scope and the pull is the only way to find it (Open Item B-012)'); val = 'High'
        if any(x['V'][134] == 'Accrual reversal' and jnet[str(x['V'][137])] != 0 for x in jr):
            why.append('accrual reversal that does not pair inside FY2026/27; read against 26SLACT P12 before any net (rule 5, Open Item B-011)'); val = 'High'
        if any(x['V'][31] == 'Confirm' and x['V'][33] == 'Partial' for x in jr):
            why.append('blank or non-descriptive journal narration, so the nature of the charge is not on the register'); val = 'High'
        if not why:
            internal = all(str(x['V'][136]) != 'External supplier' for x in jr)
            allconf = all(x['V'][33] == 'Confirmed' for x in jr)
            if internal and allconf and len(jr) > 1:
                why.append(f'internal charge allocation on {"; ".join(k for k, _ in acc0.most_common(2))}: every one of the {len(jr):,} legs is already on the register with its own narration, '
                           'so the Document Line Table adds only the Council-side counterparty legs. Pull only if the allocation basis itself is questioned'); val = 'Low'
            elif zero:
                why.append('set nets to $0.00 inside branch scope; pairing is already proven on the register'); val = 'Low'
            elif allconf:
                why.append('operational journal, narration carries the nature on every leg'); val = 'Low'
            else:
                why.append('operational journal not fully evidenced on the register'); val = 'Medium'
        pks = collections.Counter(str(x['V'][17]) for x in jr)
        per = sorted({pbr_stage.clean_num_text(x['V'][56]) for x in jr})
        secs = sorted({sec_names[str(x['V'][2])] for x in jr})
        jp_rows.append(dict(tier=tier, df=df, refs=refs, per=per, n=len(jr), net=net, gross=gross, att=att, zero=zero, secs=secs, val=val,
                            acc=acc, pks=pks, why='; '.join(why),
                            narr=str(jr[0]['V'][22] or '').replace(chr(10), ' | ')[:200]))
    jp_rows.sort(key=lambda x: (x['tier'], -abs(x['net'])))

    # ---------------------------------------------------------------- workbook
    wb = Workbook(write_only=True)
    wb._fonts[0] = Font(name='Cambria', size=10)
    names = {}
    def dn(name, ref):
        names[name] = ref
        wb.defined_names[name] = DefinedName(name, attr_text=ref)

    def reg(col):
        return f'Register!${CL(col)}${FIRST}:${CL(col)}${LAST}'
    for nm, c in dict(Reg_LineKey=1, Reg_Section=2, Reg_Contractor=12, Reg_NA=14, Reg_PKHeader=16, Reg_PK=17, Reg_Service=19,
                      Reg_Amount=20, Reg_Cat=24, Reg_Theme=26, Reg_Basis=27, Reg_Tier=29, Reg_Verdict=31, Reg_Status=33,
                      Reg_EvID=88, Reg_V3Group=131, Reg_V3Cat=132, Reg_LineKind=134, Reg_Charge=136, Reg_JRef=137,
                      Reg_Route=146, Reg_Prov=148).items():
        dn(nm, reg(c))
    dn('ThemeMap_Cat', f'Theme_Map!$A$5:$A${TM_LAST}'); dn('ThemeMap_Group', f'Theme_Map!$B$5:$B${TM_LAST}')
    dn('ThemeMapV3_Cat', f'Theme_Map_v3!$A$5:$A${T3_LAST}'); dn('ThemeMapV3_Group', f'Theme_Map_v3!$B$5:$B${T3_LAST}')
    dn('EIL_Invoice', 'Evidence_Invoice_Lines!$A$5:$A$5000'); dn('EIL_Amount', 'Evidence_Invoice_Lines!$G$5:$G$5000')
    dn('EIL_GST', 'Evidence_Invoice_Lines!$F$5:$F$5000'); dn('EIL_LineKey', 'Evidence_Invoice_Lines!$J$5:$J$5000')
    dn('EI_Invoice', f'Evidence_Invoices!$A$5:$A${EI_LAST}'); dn('EI_ExGST', f'Evidence_Invoices!$J$5:$J${EI_LAST}')
    dn('EI_InclGST', f'Evidence_Invoices!$L$5:$L${EI_LAST}')
    dn('JS_Ref', f'Journal_Sets!$A$5:$A${JS_LAST}'); dn('JS_Net', f'Journal_Sets!$C$5:$C${JS_LAST}')

    controls = []   # (group, sheet, text, kind, formulaE, expected)
    summary_ties = []  # (sheet, cell) totals that must equal the register total

    # ---------------------------------------------------------------- Creditor_Lines layout (rows cited by Register col 28)
    CLv = v127['Creditor_Lines']
    new_ci = {ci for _, ci in stage['cred_new_matches']}
    cl_keep = [(i, r) for i, r in enumerate(CLv[4:], 5) if r[1] == 'FY2026/27' or i in new_ci]
    HISTS = stage['hist']; hist_matches = stage['hist_matches']
    hm_set = {(m['k'], m['i']) for m in hist_matches}
    clrow = {}
    nxt = 5 + len(cl_keep)
    for k_, hh in enumerate(HISTS):
        for i, _ in hh['data']:
            clrow[(k_, i)] = nxt; nxt += 1
    CL_LAST = nxt - 1
    hist_cited = 0
    for r in rows:
        t_ = r['V'][28]
        if isinstance(t_, str) and '{CL:' in t_:
            r['V'][28] = CLTOK.sub(lambda mm: str(clrow[(int(mm.group(1)), int(mm.group(2)))]), t_)
        if isinstance(r['V'][28], str) and 'history pulled 11-Sep-2026' in r['V'][28]:
            hist_cited += 1
    say(f'creditor lines: {len(cl_keep)} carried from v127, {len(clrow)} from the branch v4 to v6 APLEDGER pulls; {hist_cited} register lines cite a branch history row')

    # ============================================================== Handover (content filled from computed facts)
    unid_by_sec = collections.defaultdict(lambda: [0, Decimal(0)])
    for r in rows:
        if r['V'][12] == UNID:
            unid_by_sec[r['V'][2]][0] += 1; unid_by_sec[r['V'][2]][1] += D(r['V'][20])
    status_amt = collections.defaultdict(Decimal)
    for r in rows:
        status_amt[r['V'][33]] += D(r['V'][20])
    inh_amt = sum(D(r['V'][20]) for r in rows if r['meta']['inherited'])
    ho = Sheet(wb, 'Handover', {'A': 34, 'B': 120})
    ho.row([f'Handover, Parks Branch transaction register FY2026/27 O110-O115 ({BUILD_DATE}, {VER})'], 'title')
    ho.row(['Self-contained workbook. Every source export is embedded verbatim; the PS & WP register v127 FY2026/27 analysis is inherited line by line; every figure below is live or restated from the embedded sources.'], 'sub')
    ho.blank()
    ho.row(['Position at handover', ''], 'blue')
    pos = [('Scope', 'Branch 4090000, LCC OP/AP codes O110 to O115, expense type 1, ledger 27SLACT, periods 1 to 3 posted (as pulled 11-Sep-2026 10:11).'),
           ('Register lines', '=COUNT(Reg_Amount)'), ('Register total ex GST (live)', f'=Register!T{TOT}'),
           ('Control total (ledger export and all four SE2 reports)', 4910566.68), ('Master control verdict', '=Controls!B4'),
           ('Lines inherited from PS_WP v127', f'=COUNTIF(Reg_Prov,"{INH}*")'), ('Lines new at branch v1', f'=COUNTIF(Reg_Prov,"{NEW}")'),
           ('$ Confirmed (live)', '=SUMIFS(Reg_Amount,Reg_Status,"Confirmed")'), ('$ Partial (live)', '=SUMIFS(Reg_Amount,Reg_Status,"Partial")'),
           ('$ Pending evidence (live)', '=SUMIFS(Reg_Amount,Reg_Status,"Pending evidence")'),
           ('Sighted invoice lines (rule 17, carried)', '=COUNTIF(Reg_Basis,"Sighted invoice line")'),
           ('$ with contractor unidentified (live)', f'=SUMIFS(Reg_Amount,Reg_Contractor,"{esc(UNID)}")'),
           ('$ identified from the branch APLEDGER histories, v4 to v6 (live, lines still citing the history)', f'=SUMIFS(Reg_Amount,Register!$AB${FIRST}:$AB${LAST},"*history pulled 11-Sep-2026*")')]
    for a, b in pos:
        ho.row([a, b], money_cols=(2,) if (isinstance(b, float) or (isinstance(b, str) and ('SUM' in b or 'T' + str(TOT) in b))) else ())
    ho.blank()
    ho.row(['Source file', 'Where it lives in this workbook'], 'blue')
    ho.row([os.path.basename(pbr_stage.LEDGER), f'Register grey block (cols BB:CI, CX, EQ), all 35 export columns verbatim; md5 {stage["led_md5"]}; Data_Acquisition F1.'])
    for k, s in se2.items():
        ho.row([os.path.basename(s['path']), f'SE2_Budget sheet verbatim (SE2 by {k}); md5 {s["md5"]}; Coverage and Section_Summary tie to it.'])
    ho.row([os.path.basename(pbr_stage.V127), f'Inheritance source only (not embedded): FY2026/27 analysis, green blocks, evidence lines and matched creditor lines; md5 {stage["v127_md5"]}; Inheritance_Log.'])
    for k_, hh in enumerate(HISTS, 7):
        ho.row([os.path.basename(hh['path']), f'Creditor_Lines (APLEDGER {hh["code"]} {hh["label"]}, {hh["n"]:,} lines {hh["first"].strftime("%d-%b-%Y")} to {hh["last"].strftime("%d-%b-%Y")}, verbatim); md5 {hh["md5"]}; Data_Acquisition F{k_}.'])
    for m_ in stage.get('attach_files', []):
        ho.row([m_['file'], f'Evidence_Invoices / Evidence_Invoice_Lines / Register green block (Batch {m_.get("batch", "attach_1")}, corpus_{m_.get("batch", "attach_1")}_v6.json with page text retained); md5 {m_["md5"]}; the PDF itself is not embedded (rule 15).'])
    ho.row(['code.pdf (66 pages, binder not supplied)', 'Evidence_Invoices / Evidence_Invoice_Lines / Register green block (Batch code): supplied corpus corpus_code.json md5 e256555fc9d22d46a9cce80f8e7bbe3b, prepared to corpus_code_v6.json with page text rebuilt from the retained layout rows and the rule 19.2 per-vendor verbatim check run against an independent source (Data_Acquisition).'])
    ho.blank()
    ho.row(['Next steps (priority order, detail on Open_Items)', ''], 'blue')
    top = sorted(unid_by_sec.items(), key=lambda kv: -kv[1][1])[:3]
    steps = [f'1. Contractor identification outside Park Services: {sum(v[0] for v in unid_by_sec.values()):,} AP lines, {fmt_money(sum(v[1] for v in unid_by_sec.values()))} ex GST, carry no creditor evidence. Largest: ' +
             '; '.join(f'{sec_names[k]} {fmt_money(v[1])}' for k, v in top) + '. Request APLEDGER creditor histories for the major series (rule 12), one Finance email.',
             '2. Pair the FY2025/26 EOY AP accrual reversals posted in P1 against 26SLACT P12 for the non-PS/WP sections before reading any section net (rule 5).',
             '3. Re-adjudicate the inherited PS/WP journal sets that now net to zero once the other branch legs are in scope (Open_Items).',
             '4. Confirm the service-to-section mapping for service 20821 (61 lines on Section NA, no WO Task).',
             '5. Load P4 when it closes; this register refreshes as a whole-branch pull, never section by section.',
             f'6. Port to PS_WP v128: the branch v3/v4 captures on inherited lines and the {len(ident_rows)} inherited Park Services lines identified at branch v4 to v6 from the APLEDGER histories (Register col ER).']
    for s_ in steps:
        ho.row(['', s_])
    ho.blank()
    ho.row(['Change log', ''], 'blue')
    _hm = stage['hist_matches']
    _h6 = [h for h in HISTS if h.get('added') == 'v6']; _hm6 = [m for m in _hm if HISTS[m['k']].get('added') == 'v6']
    ho.row([f'{VER}, {BUILD_DATE}', f'Four more APLEDGER creditor histories embedded ({sum(h["n"] for h in _h6):,} lines: ' + ', '.join(f'{h["code"]} {h["label"]}' for h in _h6) + f'), {len(HISTS)} histories and {sum(h["n"] for h in HISTS):,} lines in all on Creditor_Lines. '
            f'{len(_hm6)} register lines identified from the four ({fmt_money(sum(m["amount"] for m in _hm6))} ex GST); {len(_hm)} lines identified from every history ({fmt_money(sum(m["amount"] for m in _hm))} ex GST, rule 8 Tier 1), of which {len(ident_rows)} inherited Park Services lines still carry the identification (port to PS_WP v128). '
            f'LEV002 full history re-pulled and audited against the PS_WP v127 embedded lines (rule 12, Method 12.0). Labels for NUW001, GRE083 and WAT088 rest on the ABR public register read against the ABN on the export (Data_Acquisition); no invoice sighted yet for those three. No capture batch; control total unchanged.'])
    ho.row(['v4 and v5, 11-Sep-2026', 'Twelve APLEDGER creditor histories embedded (eight at v4: GLA009, ECO031, HAR073, PRO066, HER025, SAV012, TRE010, VIN003; four at v5: BUR044, CER006, COA030, THE289), 20,718 lines, identifying 883 register lines, $1,831,834.74 ex GST at v5. '
            'Batch attach_1 (v4): 5 TechOne attachment PDFs (Eco Technology Solutions 11913, Glascott 012313, Provac INV-00042754, Savco SV007924, Heritage Tree Services INV-47435), 5 green blocks. Batches attach_2 and code (v5): 6 attachment PDFs and a supplied corpus, 36 green blocks, Coast2Coast fuel levy finding B-029. Journal_Pull sheet added at v5 (rule 21). Control total unchanged.'])
    ho.row(['v3, 11-Sep-2026', f'Batch mixed_new_26_27 captured: 33 invoices, {sum(1 for r in sighted if r["meta"].get("ported")) + sum(1 for r in sighted if not r["meta"]["inherited"]) - 30} green blocks, Park Services, Water Parks and Park Maintenance. {sum(1 for r in sighted if r["meta"].get("ported"))} of the green blocks sit on lines inherited from PS_WP v127 and must be ported to the PS_WP register at its next build (Open_Items). Origin consolidated invoices 1026099 and 1026231 captured under the PARTIAL-SCOPE variant (Parks carries the Logan Garden Park site row only). Coast2Coast INV-11834/11835 split-posting resolves service 20821 as the mowing fuel levy leg. Control total unchanged.'])
    ho.row(['v2, 11-Sep-2026', f'Batch mixed_1 captured: {len(evn["order"])} invoices, {sum(1 for r in sighted if not r["meta"]["inherited"])} green blocks, {len(evn["eil"])} evidence lines, {fmt_money(sum(D(x[1][9]) for e, x in ei_rows.items() if e in evn["ei"]))} ex GST on Natural Areas and Park Maintenance lines moved to Confirmed, Tier 1 (rule 17). Control total unchanged. Method 9.0 records the variants.'])
    ho.row(['v1, 11-Sep-2026', f'First build. {N:,} lines tie to the ledger export and to all four SE2 views at $4,910,566.68. {stage["inherit_n"]:,} PS/WP lines ({fmt_money(inh_amt)}) inherit v127 analysis unchanged in substance; {N - stage["inherit_n"]:,} lines classified by the branch v1 engine (Method 6.0). Theme maps extended (Method 7.0). 111 rule 17 green blocks, 110 invoices and 484 evidence lines carried with every check live.'])

    # ============================================================== Method
    me = Sheet(wb, 'Method', {'A': 12, 'B': 150})
    me.row([f'Method, Parks Branch transaction register FY2026/27 ({VER})'], 'title')
    me.row(['Numbered sections. Positions are read from Config (rule 19.6); structure is stated here (rule 14).'], 'sub')
    me.blank()
    M = []
    def sec_(h, *paras):
        M.append((h, None)); [M.append((None, p)) for p in paras]
    sec_('1.0 Purpose and scope',
         'Transaction-level register of every FY2026/27 operating expense line in Parks Branch 4090000 at LCC OP/AP codes O110 to O115 (expense type 1): who was paid, what for, on what evidence, whether the coding reads correctly, which PK carries it, and which theme it belongs to. It extends the PS & WP register method (Park Services 4090240 and Water Parks 4090260) to all ten section values: Management, Depots, Natural Areas, Park Maintenance, Park Services, Trees, Water Parks, Cemeteries, Planning Design & Capital Delivery, and lines TechOne carries with Section NA.',
         'Single financial year, so there is no cross-year scope asymmetry (rule 11). Periods 1 to 3 are posted; P3 was still open at the pull (11-Sep-2026 10:11). The standing rules of the PS & WP programme apply unchanged (Project_Instructions sheet); the only departures are the declared extensions in 6.0 and 7.0.')
    sec_('2.0 Sources and control total',
         'One Ledger Accounts Transactions Table export (27SLACT, criteria verbatim on Data_Acquisition F1), 6,683 lines, export total $4,910,566.68. Four SE2 exports on the identical criteria, by Section, Natural Account, WO Task and Service No, each totalling $4,910,566.68 accumulated actual P1-3. The register total ties to all five to the cent (Controls group 1 and 2). The control total must never change on an identification, enrichment or capture build (rule 10).')
    sec_('3.0 Workbook structure',
         'Handover | Method | Theme_Map (v2 axis, extended) | Register | Section_Summary | Summary (status, basis, verdict, tier by section) | Themes (v2 by section) | Themes_v3 (group and category by section) | Axes (Line Kind, Line Kind rule, Charge Source, Procurement route by section) | Coverage (A natural account, B WO Task, C service, each tied to its SE2 view with budget) | PK_Listing | Vendor_Series | Journal_Sets | Journal_Pull | Open_Items | Inheritance_Log | Creditor_Lines | SE2_Budget | Evidence_Invoices | Evidence_Invoice_Lines | EIL_Controls | Vendor_Boilerplate | Data_Acquisition | Config | Project_Instructions | Theme_Map_v3 | Controls.',
         'Not carried from the PS & WP register: site gazetteer, asset, inspection, CRM and pull-queue sheets (Sites through Theme_Review). They are Park Services instruments; the site columns DY:DZ are carried on inherited lines and set to a closed-list site basis on new lines.')
    sec_('4.0 Register column map',
         'Columns 1 to 146 are the PS & WP register map exactly (PSWP_Register_Schema section 2), so every toolkit script reads this register without change: 1-34 analysis, 35-44 parsed references, 45-53 creditor enquiry block, 54-87 grey source block verbatim (BB:CI), 88-127 rule 17 green block (CJ:DW), 128 Src __md5Row, 129-130 site, 131-133 theme v3, 134-136 Line Kind and Charge Source, 137-142 journal provenance, 143 assessment scope, 144 journal type, 145 treatment decision, 146 procurement route.',
         'Two columns are added: 147 (EQ) Src Note, the export LNTNoteNumber column, which the PS & WP layout did not store (rule 3 full capture); 148 (ER) Register provenance, exactly "Inherited from PS_WP register v127" or "New at branch v1 (not in the PS_WP register)". The grey block now stores Details verbatim including line breaks; v127 stored line breaks as " | ".',
         f'Header row 4, data rows {FIRST}:{LAST}, totals row {TOT}. Live formulas per line: U estimate incl GST; Z theme lookup on Theme_Map; DQ:DT rule 17 checks on sighted lines; EA theme group lookup on Theme_Map_v3; EI:EJ journal net and balance class looked up on Journal_Sets; EM scope; EN journal type. Rows are sorted by section, service, WO Task, natural account, document date, reference.')
    sec_('5.0 Inheritance from the PS & WP register v127',
         f'Match key: Document Unique ID + full account string + natural account + Work Order + amount to the cent + Details (line breaks normalised to " | "), consumed one for one. '
         f'{stage["inherit_n"]:,} of the 3,372 v127 FY2026/27 lines match; every one of the {len(sighted)} sighted lines matches. For a matched line the analysis block (1-53), green block (88-127) and axes (129-146) are carried as values, the grey block is written from the new export, and column 30 (attachment) is re-read from the export. Source-derived analysis fields compared with the export: {dict(stage["flags"])}.',
         f'The {len(stage["unmatched_v"])} v127 lines absent from the 11-Sep pull ({fmt_money(sum(D(r[19]) for _, r in stage["unmatched_v"]))} net) are listed on Inheritance_Log and Open_Items: RJ accrual pairs, payroll postings re-mapped to another account, and TBM 00099124, which reappears here as a new line under a different Document Unique ID. A line whose account string changed in TechOne is deliberately not inherited, because its section, service and PK analysis no longer hold. The PS & WP register still carries them.',
         f'Citations restated (rule 19.10). Register column 28 on the 111 sighted lines is rewritten from the EvID maps to cite this workbook (Evidence_Invoice_Lines rows and the EIL_Controls row); Evidence_Invoices column 13 is rewritten the same way and the v127 text is kept verbatim in column 33. Row citations in columns 32, 34 and 127 that point at other v127 FY2026/27 register rows are mapped to this register and the v127 row kept in brackets. Counts: {dict(cite_changes)}. Open Items numbers cited on inherited lines are PS & WP numbers and are carried as PSWP-# rows on Open_Items.',
         'Rule 17 check formulas are regenerated from their v127 shapes with every row reference remapped: 108 standard, 2 SUM-TIE (Kachel 7546), 1 split-posting by LineKey. Evidence Tier values stored as text on inherited lines ("2", "Tier 1") are canonicalised to integers so COUNTIF panels cannot double count. Journal_Provenance is not carried: columns EI:EJ on every journal line now read Journal_Sets at branch scope.')
    sec_('6.0 Classification engine for new lines (branch v1)',
         'Rules are held as data (pbr_rules_v1.json, embedded summary here). Order: (a) source type decides contractor, basis, tier, status and verdict; (b) natural account decides nature where the account is single-purpose (P1 account governs); (c) on contract accounts 73111, 73123, 73126, 73128, 73211, 73212 the line narration decides nature when it names a class (P4 narration, single class), otherwise the service code decides when the service is single-purpose (P1S service governs, a declared extension: mowing, landscape, tree, natural areas, cemetery, rubbish, cleaning and water park services), otherwise Parks maintenance (contract/reactive) with v3 "No invoice sighted" (P6).',
         'Journals (source GL, GJ, BI or a journal document type). Narration showing accrue/accrual, an RJ reference or a Reversing Journal: EOFY accrual reversal, Line Kind Accrual reversal. Narration showing recode, transfer, split, reversal, correct PK, incorrect NA, GST correction or fuel levy PK: Recode journal, Line Kind Recode / transfer journal. Pairing is tested by reference across the whole branch population in Decimal: a set netting to $0.00 is Journal (net-zero), Confirmed; an accrual set that does not net is Journal (reversal), Partial, with a cross-FY follow-up where the narration says End of Year; a recode set that does not net is Review, Partial, because its balancing leg sits outside O110-O115 (rule 21 pull). Other journals are operational: Line narration, Tier 2, Confirmed, Correct, or Partial where the narration is blank.',
         'System records: inventory issues (LCC Stores), Plant & Fleet internal invoices, payroll postings: System record, Tier 1, Confirmed, Correct. Purchase card: merchant from the narration, Line narration, Tier 2, Confirmed. Direct-debit electricity on 73312 and toll tags on 73535: series labels marked confirm, Line narration, Tier 2, Confirmed, Correct (utilities rest on the system record).',
         'AP supplier documents are never Confirmed without rule 17. Contractor: a v127 creditor history line with the same reference whose incl GST amount is within 2c of the document net x 1.1 (Tier 1 with ABN, Tier 2 without); else a payee or company named in the narration (Tier 2, narration-named); else a supplier named in a Council recode journal where the journal corroborates the AP line, either reversal legs naming the invoice number that are equal and opposite to the AP document total within 2c, or a fuel levy recode naming the invoice and moving it off the PK the AP line charges (Tier 2, \"named in recode journal, confirm\"); else "' + UNID + '" (Tier 3). No ABN is ever carried onto an inferred line (rule 8). Status Partial for Tier 1-2, Pending evidence for Tier 3; verdict Confirm. Nature Basis Line narration only where the narration itself names the class or, on a single-purpose account, carries descriptive words; a generic narration ("Standing Order 26/27", "CON ORDER", "Quote 1234") is Vendor inference (unconfirmed) (rule 2) and the Nature Detail says so.',
         'Review flags (verdict Review): recode set not netting in scope; narration class contradicting a single-purpose service; supplier document on an internal 7B/7C account; electricity or toll narration off its account. Follow-ups: every Tier 3 line names its evidence route (attachment on the Document File, or the creditor history); lines with no Work Order are flagged Unallocated (rule 1); Section NA lines flag the missing service-to-section mapping. Narrations printing a month more than three months after posting (the "July 2027" accrual narration) keep the printed text and read FY (Service) from the posting year.')
    sec_('7.0 Theme taxonomy extensions',
         'Theme_Map v2: 23 categories added (rows 32 onward) and three themes added, T14 People, training & corporate, T15 Trees & natural areas, T16 Cemeteries. Without them tree, bushland, cemetery and staff costs, which are most of the non-PS spend, would fall into T1 or T8 and the thematic series would stop meaning anything. Existing categories and their themes are untouched, so every inherited PS/WP line keeps its theme.',
         'Theme_Map_v3: five level-2 categories and four level-1 groups added: 10 Trees & natural areas (Trees & arboriculture; Bushland, weeds & fire), 11 Cemeteries, 12 People & corporate (Staff, training & corporate), 13 Refunds & recoveries. Contract mowing and landscape map to the existing Grounds, turf & vegetation. Single year, so no vintage mixing arises (rule 4).')
    sec_('8.0 Summary sheets and ties',
         'Every summary is live SUMIFS/COUNTIFS over Register defined names (Reg_*). Section_Summary ties each section to the SE2 Section view and carries YTD and annual budget. Coverage ties panel A to SE2 by natural account, panel B to SE2 by WO Task (Register col P; blank WO Task shown as "(no WO Task)" and tied to the SE2 blank-key row), panel C to SE2 by service. Themes, Themes_v3, Axes, Summary, PK_Listing and Vendor_Series each carry a total that must equal the register total (Controls group 3). T9 is shown and excluded from operational spend (rule 5). Vendor_Series criteria are escaped for ~ * ? and grouped case-insensitively (COUNTIF trap).')
    sec_('9.0 Rule 17 evidence carried',
         f'{len(sighted)} register lines carry a green block over {len(ev_order)} invoices: {len(carried)} carried from PS & WP v127 (KC-7546 posts as a SUM-TIE pair) and {len(evn["order"])} captured at branch v2 from Batch mixed_1 (INV-39235 posts as a SUM-TIE pair). Evidence_Invoices holds the headers (no control block below the data, so the EI_* names have no headroom problem), Evidence_Invoice_Lines holds {len(eil_lines)} lines ({sum(1 for l in eil_lines if l[6] in (None, ""))} Glascott attachment rows carry no amount and sit outside check 1, rule 16d), EIL_Controls holds one check-1 reconciliation per invoice, Vendor_Boilerplate holds the {len(vb_rows)} BP: keys the green blocks cite. Controls group 4 proves every sighted line reads TRUE on all three checks and every cited key exists.',
         'Batch mixed_1 (v2). Corpus corpus_mixed_1_v6.json (raw-text route, parse_mixed1.py, page text retained, gate GREEN, 2,374 shingles clean); match table match_mixed_1_v6.json; capture by pbr_capture.py, brief-driven (rule 20): categories, variants, EvID prefixes and notes are data. Variants used: standard 24; check 2 SUM-TIE (INV-39235); check 2 derivation equality incl/1.1 (INV-9360, INV-0600, 18788, 18789); check 3 per-line rounding basket (7 documents) and 1c tolerance (26230, 26231). Cents companion AP lines on five documents are cross-referenced in the coding note and not green-blocked. Guru Dirt Works EvIDs carry a GDW- prefix because INV-0111 and INV-0112 are already held for Flavell-Dau in v127 (Method 34.2). Contractor labels are canonicalised by printed ABN to the label already on the register (Levai).')
    sec_('13.0 Journal pull list (rule 21, branch v5)',
         'Journal_Pull is one row per TechOne document file, because that is the unit a Document Line Table export is pulled by and a document file can carry many journal references (document 1252466 carries eight). '
         f'{len(jp_rows)} document files cover all {sum(len(v_) for v_ in jp_doc.values()):,} journal lines on the Register and total their net movement exactly (Controls group 8).',
         'Tiers: A no attachment in TechOne, so the Document Line Table is the evidence route, pull these; B the document carries an attachment, sight it, a pull adds nothing; C RJ reversing journals, which net to exactly zero and are read as a pair under rules 5 and 6; '
         'D already embedded in the PS & WP register v127 Journal_Sources, where a re-pull is audited leg by leg and never re-captured (rule 12). Ranked within tier by ABSOLUTE net movement into branch O110-O115, never by gross, because gross double-counts both legs of a transfer.',
         'The "Why it matters" column states the question the pull answers: a recode set that does not net inside O110-O115 (Open Item B-012), an accrual reversal that does not pair inside FY2026/27 and must be read against 26SLACT P12 (rule 5, Open Item B-011), or a blank journal narration. A set that already nets to zero in scope has its pairing proven on the register and needs no pull.')
    sec_('10.0 Controls and verify',
         'Controls (last sheet) gathers every control; column E is a live reference or count, F the expected value fixed at build, G the result; the master verdict at Controls!B4 is TRUE only when nothing reads FALSE and the TRUE count equals the registered count. The build runs as one script: stage gates, write, LibreOffice convert-route recalc with an isolated profile carrying OOXMLRecalcMode=0, calamine verify of the recalculated file (master verdict, every control, every sighted check, every coverage tie, register total, whole-workbook error sweep), then ship. openpyxl writes no cached values, so an unrecalculated file cannot pass.')
    sec_('11.0 Known limits (read before relying on a figure)',
         'Outside Park Services and Water Parks there is no creditor history or sighted invoice yet: AP nature on new lines is service- or narration-based and supplier identity is mostly Tier 3. Confirmed $ on new lines is journals, internal charges and utilities only.',
         'Monthly accruals (DM 18989758) reverse in the following period; P3 accruals still open at the pull will net only when P4 loads. The P1 EOY 2025/26 accrual reversals are cross-FY and must not be read as FY2026/27 underspend (rule 5).',
         'Site attribution is not performed for new lines. Supply-point text on electricity lines is parsed into column 42 only.')
    sec_('12.0 Creditor histories (branch v4 to v6)',
         f'{len(HISTS)} APLEDGER creditor histories (TechOne Ledger Accounts Transactions Table, Default Ledger Type AP, one creditor account per export) pulled 11-Sep-2026 and embedded verbatim on Creditor_Lines (the version each was added at in brackets): ' + '; '.join(f'{h["code"]} {h["label"]} ({h.get("added", "v4")}, {h["n"]:,} lines, {h["first"].strftime("%d-%b-%Y")} to {h["last"].strftime("%d-%b-%Y")}, ABN {h["abn"]})' for h in HISTS) + '. Each file md5 is screened against the PS & WP v127 Data_Acquisition and this register\'s inputs before use (rule 12). Re-pulls of histories already embedded in PS_WP v127 are audited against the v127 Creditor_Lines by reference, date and amount and never re-captured: HAR073 (v4) supersedes the 5-Aug-2026 pull and LEV002 (v6) the 2-Sep-2026 re-pull (audit: ' + str(stage.get('hist_audit')) + '; v127 carries only the lines it matched, so new_only counts the unmatched balance as well as the later postings).',
         'Label basis per history is data in the manifest and is restated on Data_Acquisition. At v6 three creditors have no sighted invoice yet (NUW001, GRE083, WAT088): the label is the ABR public register entity name read on 11-Sep-2026 against the 11-digit ABN carried on the export (rule 8 Tier 1, creditor history with ABR ABN), with the trading name where the ABR or the APLEDGER narrations print one; the legal-entity and trading-name form is confirmed from the first sighted invoice. Where an export carries a second ABN on a handful of old lines (2022 to 2023 on LEV002, NUW001 and GRE083) those lines are outside FY2026/27 and no register line takes an ABN from them.',
         'Match rule (pbr_histories_v4.json, held as data): the AP register line reference equals the history Reference; the history Transaction Amount (incl GST) is within 2c of the document net ex GST x 1.1 summed over every register line on the Document Unique ID; the history Date is within 120 days of the register Doc Date; exactly one creditor code satisfies all three (numeric references collide across creditors, e.g. Harpley and Eco Technology Solutions both issue reference 11913). Tier 1 where the history line carries an 11-digit ABN. The register line takes the creditor code (col K), the label from the manifest (col L, canonical per printed ABN), the ABN grouped (col M), the enquiry block (cols W, AS:BA) and an Evidence sentence citing the Creditor_Lines row. Status stays Partial and verdict Confirm: an AP line is never Confirmed without rule 17.',
         f'Inherited Park Services lines carried from PS_WP v127 as Unidentified, series-inferred or vendor-inferred are identified the same way ({len(ident_rows)} lines; a sighted invoice on the same line supersedes the identification); their provenance (col ER) reads "contractor identified at branch v4" (or v5, v6) and the v127 evidence sentence is kept inside the new one. Sighted (Tier 1, rule 17) lines are never re-identified. Label conflicts, where the v127 label named a different vendor: {len(stage["hist_conflicts"])} (Open_Items). Correction carried in the match table: at v3 register line f386b8d0-73212-PK000415-01 (reference 00015225, $240.00) was tagged a cents companion of Q Power 15225; it is on a different TechOne document and HAR073 shows it is Harpley invoice 00015225, so the tag is withdrawn (match_mixed_new_26_27_v6.json evid_note).',
         'Batch attach_1 (v4): five single-invoice TechOne attachment PDFs (EzeScan exports, file name = attachment id) parsed by parse_attach1.py (pdftotext -layout, page text retained, five templates ETSOL, GLASCOTT_LM, PROVAC, SAVCO, HERITAGE), gated GREEN (P9 page-coverage test now runs per source file when a corpus carries several), 254 five-word shingles clean, match table match_attach_1_v6.json (five standard variants, one register line each, coding verdict and note per invoice as data). Printed PK versus PK charged is recorded on three invoices (Eco Technology Solutions 11913, Provac INV-00042754, Savco SV007924); PK Charged stays the ledger Work Order (rule 1).')
    for h, p in M:
        if h:
            me.row([h, ''], 'blue')
        else:
            me.row(['', me.cell(p, wrap=True)])

    # ============================================================== Theme_Map
    tm = Sheet(wb, 'Theme_Map', {'A': 42, 'B': 52, 'C': 30})
    tm.row(['Theme map v2 (editable), branch v1 extension'], 'title')
    tm.row(['Register column Z looks up Nature Category (column X) here. Rows 5-31 are the PS & WP map unchanged; rows 32 onward are the branch v1 extension (Method 7.0).'], 'sub')
    tm.blank()
    tm.row(['Nature Category', 'Theme', 'Origin'], 'blue')
    for k, (a, b) in enumerate(theme_v2):
        tm.row([a, b, 'PS & WP v2' if k < 27 else 'Branch v1 extension'])

    # ============================================================== Register
    rg = Sheet(wb, 'Register', freeze='B5')
    hdr = list(v127['Register'][3][:146]) + ['Src Note (LNTNoteNumber)', 'Register provenance']
    widths = {1: 30, 3: 18, 12: 34, 22: 48, 24: 30, 25: 60, 28: 50, 32: 40, 34: 50, 60: 48, 111: 60, 127: 50}
    for c in range(1, 149):
        rg.ws.column_dimensions[CL(c)].width = widths.get(c, 14)
    rg.row(['Parks Branch transaction register, FY2026/27, LCC OP/AP O110-O115, periods 1-3 (27SLACT pulled 11-Sep-2026)'], 'title')
    rg.row([f'{N:,} lines. Blue headers: register analysis. Grey: source extract verbatim. Green (CJ:DW): rule 17 sighted-invoice capture. Purple: axes and provenance. Column ER says whether a line inherits PS & WP v127 analysis or was classified at branch v1.'], 'sub')
    rg.blank()
    styles = []
    for c in range(1, 149):
        styles.append('grey' if (54 <= c <= 87 or c in (128, 147)) else 'green' if 88 <= c <= 127 else 'axis' if c >= 129 else 'blue')
    rg.ws.append([rg.cell(h, F_HDR, s) for h, s in zip(hdr, styles)]); rg.n += 1
    try:
        rg.ws.auto_filter.ref = f'A4:{CL(148)}{LAST}'
    except Exception:
        pass
    money_cols = {20, 21, 45, 48, 49, 61, 113, 114, 115, 116, 117, 121}
    date_cols = {4, 46, 47, 58, 85}
    gforms = stage['gforms']
    for r in rows:
        V = r['V']; rr = r['row']
        assert rg.n + 1 == rr
        V[21] = None
        inh = r['meta']['inherited']
        if (inh and f"{r['meta']['vrow']}|U" in forms) or (not inh and r['meta'].get('charge') != 'Statutory levy / insurance'):
            V[21] = f'=ROUND(T{rr}*1.1,2)'
        V[26] = f'=IFERROR(INDEX(Theme_Map!$B$5:$B${TM_LAST},MATCH(X{rr},Theme_Map!$A$5:$A${TM_LAST},0)),"Unmapped - add to Theme_Map")'
        if V[88]:
            for col in ('DQ', 'DR', 'DS', 'DT'):
                V[pbr_stage_colnum(col)] = gforms[(rr, col)]
        V[131] = f'=IFERROR(INDEX(Theme_Map_v3!$B$5:$B${T3_LAST},MATCH($EB{rr},Theme_Map_v3!$A$5:$A${T3_LAST},0)),"(not in Theme_Map_v3)")'
        if V[137]:
            V[139] = f'=IFERROR(INDEX(Journal_Sets!$C$5:$C${JS_LAST},MATCH($EG{rr},Journal_Sets!$A$5:$A${JS_LAST},0)),"")'
            V[140] = f'=IFERROR(INDEX(Journal_Sets!$E$5:$E${JS_LAST},MATCH($EG{rr},Journal_Sets!$A$5:$A${JS_LAST},0)),"")'
        else:
            V[139] = None; V[140] = 'Not a journal'
        V[143] = f'=IF($E{rr}="FY2026/27","In scope, FY2026/27 branch register","Out of scope")'
        V[144] = f'=IF($EG{rr}="","Not a journal",IF(LEFT($EG{rr},2)="RJ","RJ system reversing journal","Manual journal, "&LEFT($EG{rr},2)&" series"))'
        vals = []
        for c in range(1, 149):
            v = V[c]
            if v == '':
                v = None
            if isinstance(v, str) and len(v) > 32000:
                v = v[:32000]
            if c in money_cols and isinstance(v, (int, float)) or (c == 21 and v):
                vals.append(rg.cell(v, None, None, MONEY))
            elif c in date_cols and isinstance(v, (dt.date, dt.datetime)):
                vals.append(rg.cell(v, None, None, DATEF))
            else:
                vals.append(v)
        rg.ws.append(vals); rg.n += 1
    rg.blank()
    rg.ws.append([rg.cell('Register total (control total $4,910,566.68)', F_BOLD, 'tot')] + [None] * 18 +
                 [rg.cell(f'=SUM(T{FIRST}:T{LAST})', F_BOLD, 'tot', MONEY)]); rg.n += 1
    assert rg.n == TOT
    controls.append(('1. Control total', 'Register', 'Register total row equals the control total (ledger export total row)', 'value', f'=Register!T{TOT}', 4910566.68))
    controls.append(('1. Control total', 'Register', 'Register data rows carrying an amount', 'count', '=COUNT(Reg_Amount)', N))
    controls.append(('1. Control total', 'Register', 'Lines inherited from PS_WP register v127', 'count', f'=COUNTIF(Reg_Prov,"{INH}*")', stage['inherit_n']))
    controls.append(('1. Control total', 'Register', 'Lines new at branch v1', 'count', f'=COUNTIF(Reg_Prov,"{NEW}")', N - stage['inherit_n']))
    say('register written')

    # ============================================================== Section_Summary
    ss = Sheet(wb, 'Section_Summary', {'A': 10, 'B': 34}, freeze='C7')
    ss.row(['Section summary, FY2026/27 P1-3, with SE2 tie and budget'], 'title')
    ss.row(['Live SUMIFS over the Register. Columns N onward are the SE2 by Section export verbatim (blue). T9 accounting events are shown and excluded from operational spend (rule 5).'], 'sub')
    ss.row(['Reading: Pending evidence is mostly AP spend with no supplier or invoice evidence yet; it is not a coding error. SE2 YTD budget is the 27SLORB phased budget.'], 'sub')
    ss.blank(2)
    hdrs = ['Section code', 'Section', 'Lines', '$ net ex GST', '$ T9 accounting events', '$ operational (excl T9)', '$ Confirmed', '$ Partial',
            '$ Pending evidence', 'Status partition ties', '$ on sighted invoice', '$ contractor unidentified', '% of $ Confirmed',
            'SE2 YTD actual P1-3', 'Register = SE2', 'SE2 YTD budget P1-3', 'YTD variance (budget less actual)', 'SE2 annual budget',
            '% of annual budget spent', 'SE2 annual original budget', 'Lines inherited', 'Lines new']
    ss.row(hdrs, 'blue')
    se2sec = {r[0].split(' - ')[0]: r for r in se2['Section']['body'] if r[0]}
    s0 = ss.n + 1
    for code in SECTIONS:
        rr = ss.n + 1; A = f'$A{rr}'
        e = se2sec[code]
        ss.row([code, sec_names[code], f'=COUNTIF(Reg_Section,{A})', f'=ROUND(SUMIFS(Reg_Amount,Reg_Section,{A}),2)',
                f'=ROUND(SUMIFS(Reg_Amount,Reg_Section,{A},Reg_Theme,"{T9}"),2)', f'=D{rr}-E{rr}',
                f'=ROUND(SUMIFS(Reg_Amount,Reg_Section,{A},Reg_Status,"Confirmed"),2)', f'=ROUND(SUMIFS(Reg_Amount,Reg_Section,{A},Reg_Status,"Partial"),2)',
                f'=ROUND(SUMIFS(Reg_Amount,Reg_Section,{A},Reg_Status,"Pending evidence"),2)', f'=IF(ROUND(G{rr}+H{rr}+I{rr}-D{rr},2)=0,"TRUE","FALSE")',
                f'=ROUND(SUMIFS(Reg_Amount,Reg_Section,{A},Reg_Basis,"Sighted invoice line"),2)',
                f'=ROUND(SUMIFS(Reg_Amount,Reg_Section,{A},Reg_Contractor,"{esc(UNID)}"),2)', f'=IF(D{rr}=0,0,G{rr}/D{rr})',
                e[6], f'=IF(ROUND(D{rr}-N{rr},2)=0,"TRUE","FALSE")', e[7], f'=P{rr}-D{rr}', e[10], f'=IF(R{rr}=0,0,D{rr}/R{rr})', e[11],
                f'=COUNTIFS(Reg_Section,{A},Reg_Prov,"{INH}*")', f'=COUNTIFS(Reg_Section,{A},Reg_Prov,"{NEW}")'],
               money_cols=(4, 5, 6, 7, 8, 9, 11, 12, 14, 16, 17, 18, 20), input_cols=(14, 16, 18, 20))
    s1 = ss.n; st = s1 + 1
    ss.row(['Total', ''] + [f'=SUM({CL(c)}{s0}:{CL(c)}{s1})' if c not in (10, 13, 15, 19) else None for c in range(3, 23)], 'tot', money_cols=(4, 5, 6, 7, 8, 9, 11, 12, 14, 16, 17, 18, 20))
    for c in (13, 19):
        pass
    ss.blank()
    ss.row(['Percent columns M and S format as fractions (0.25 = 25%).'], 'sub')
    summary_ties.append(('Section_Summary', f'D{st}'))
    controls.append(('2. Coverage ties', 'Section_Summary', 'Every section ties to the SE2 by Section export', 'count', f'=SUMPRODUCT(--(Section_Summary!O{s0}:O{s1}="TRUE"))', len(SECTIONS)))
    controls.append(('2. Coverage ties', 'Section_Summary', 'Status partition (Confirmed + Partial + Pending) ties on every section', 'count', f'=SUMPRODUCT(--(Section_Summary!J{s0}:J{s1}="TRUE"))', len(SECTIONS)))
    controls.append(('1. Control total', 'Section_Summary', 'SE2 by Section total equals the control total', 'value', f'=Section_Summary!N{st}', 4910566.68))

    # ============================================================== generic panel writer (value x section)
    def panel(sh, title, values, name, label_hdr, note=None, crit=lambda v: f'"{v}"', value_cell=lambda v: v):
        sh.row([title, ''], 'bold')
        if note:
            sh.row([note], 'sub')
        sh.row([label_hdr] + [f'{c} {sec_names[c]}' if c != 'NA' else 'Section NA' for c in SECTIONS] + ['Total', 'Lines'], 'blue')
        a = sh.n + 1
        for v in values:
            rr = sh.n + 1
            cells = [value_cell(v)]
            for k, code in enumerate(SECTIONS):
                cells.append(f'=ROUND(SUMIFS(Reg_Amount,{name},{crit(v) if not callable(crit) or True else ""},Reg_Section,"{code}"),2)')
            cells.append(f'=SUM(B{rr}:{CL(1 + len(SECTIONS))}{rr})')
            cells.append(f'=COUNTIF({name},{crit(v)})')
            sh.row(cells, money_cols=tuple(range(2, 3 + len(SECTIONS))))
        b = sh.n; t = b + 1
        sh.row(['Total'] + [f'=SUM({CL(c)}{a}:{CL(c)}{b})' for c in range(2, 4 + len(SECTIONS))], 'tot', money_cols=tuple(range(2, 3 + len(SECTIONS))))
        tc = CL(2 + len(SECTIONS))
        summary_ties.append((sh.name, f'{tc}{t}'))
        controls.append(('3. Summary ties', sh.name, f'{title}: total equals the register total', 'value', f"='{sh.name}'!{tc}{t}" if ' ' in sh.name else f'={sh.name}!{tc}{t}', 4910566.68))
        controls.append(('3. Summary ties', sh.name, f'{title}: line count equals the register line count', 'count', f'={sh.name}!{CL(3 + len(SECTIONS))}{t}', N))
        sh.blank()
        return a, b, t

    def distinct(col, key=None):
        seen = collections.OrderedDict()
        for r in rows:
            v = r['V'][col]
            if v is None:
                v = ''
            seen.setdefault(v, 0); seen[v] += 1
        return sorted(seen, key=key or (lambda x: str(x)))

    wide = {'A': 46}
    for c in range(2, 14):
        wide[CL(c)] = 17
    # ============================================================== Summary
    su = Sheet(wb, 'Summary', dict(wide))
    su.row(['Summary by section: status, Nature Basis, coding verdict, evidence tier'], 'title')
    su.row(['Live SUMIFS over the Register. Each panel carries its own total and line count tie (Controls group 3).'], 'sub')
    su.blank()
    panel(su, 'By status', ['Confirmed', 'Partial', 'Pending evidence'], 'Reg_Status', 'Status')
    panel(su, 'By Nature Basis', distinct(27), 'Reg_Basis', 'Nature Basis')
    panel(su, 'By coding verdict', distinct(31), 'Reg_Verdict', 'Coding Verdict')
    tiers = distinct(29)
    assert all(isinstance(t, int) for t in tiers), tiers
    panel(su, 'By evidence tier', tiers, 'Reg_Tier', 'Evidence Tier', crit=lambda v: str(v))

    # ============================================================== Themes
    th = Sheet(wb, 'Themes', dict(wide))
    th.row(['Thematic analysis by section, FY2026/27 P1-3 (Theme_Map v2 axis, branch v1 extension)'], 'title')
    th.row(['Net ex GST. T9 accounting events are shown and must be excluded before reading operational spend (rule 5); the operational row does that.'], 'sub')
    th.blank()
    themes = sorted({b for _, b in theme_v2}, key=lambda s: int(re.match(r'T(\d+)', s).group(1)))
    a, b, t = panel(th, 'Theme by section', themes, 'Reg_Theme', 'Theme')
    rr = th.n + 1
    th.row(['Operational spend excluding T9'] + [f'={CL(c)}{t}-SUMIFS({CL(c)}{a}:{CL(c)}{b},$A{a}:$A{b},"{T9}")' for c in range(2, 3 + len(SECTIONS))], 'tot', money_cols=tuple(range(2, 3 + len(SECTIONS))))
    th.blank()
    cats = [a_ for a_, _ in theme_v2]
    panel(th, 'Nature Category by section', cats, 'Reg_Cat', 'Nature Category')

    # ============================================================== Themes_v3
    t3 = Sheet(wb, 'Themes_v3', dict(wide))
    t3.row(['Theme v3 by section: level-1 group and level-2 category'], 'title')
    t3.row(['Group 0 is off the theme axis; group 9 is a declared evidence state, not a theme. Groups 10-13 are the branch v1 extension.'], 'sub')
    t3.blank()
    groups = sorted({b for _, b, _ in theme_v3}, key=lambda s: int(s.split()[0]))
    panel(t3, 'Level-1 group by section', groups, 'Reg_V3Group', 'Theme group (L1)')
    panel(t3, 'Level-2 category by section', [a_ for a_, _, _ in theme_v3], 'Reg_V3Cat', 'Theme category (L2)')

    # ============================================================== Axes
    ax = Sheet(wb, 'Axes', dict(wide))
    ax.row(['Axes by section: Line Kind, Line Kind rule, Charge Source, Procurement route'], 'title')
    ax.row(['Line Kind carries the rule 5 quarantine on every line; Charge Source says who billed Council; Procurement route is axis 4.'], 'sub')
    ax.blank()
    panel(ax, 'Line Kind', distinct(134), 'Reg_LineKind', 'Line Kind')
    dn('Reg_LKRule', reg(135))
    panel(ax, 'Line Kind rule', distinct(135), 'Reg_LKRule', 'Line Kind rule')
    panel(ax, 'Charge Source', distinct(136), 'Reg_Charge', 'Charge Source')
    panel(ax, 'Procurement route', distinct(146), 'Reg_Route', 'Procurement route')

    # ============================================================== Coverage
    cv = Sheet(wb, 'Coverage', {'A': 16, 'B': 44, **{CL(c): 17 for c in range(3, 15)}})
    cv.row(['Coverage: register against each SE2 view, with evidence position and budget'], 'title')
    cv.row(['Panel A natural account, panel B WO Task, panel C service. Every key in the SE2 export appears, including budget-only keys with no actual. SE2 columns are verbatim (blue).'], 'sub')
    cv.blank()
    def cov_panel(title, kind, regname, keyfn):
        cv.row([title, ''], 'bold')
        cv.row(['Key', 'Name', 'Lines', '$ register net', '$ T9', '$ Confirmed', '$ Pending evidence', 'SE2 YTD actual', 'Register = SE2',
                'SE2 YTD budget', 'YTD variance (budget less actual)', 'SE2 annual budget', '% of annual spent'], 'blue')
        a = cv.n + 1
        body = se2[kind]['body']
        keys_se2 = []
        for e in body:
            if e[0] == '' and not any(isinstance(x, float) for x in e[1:12]):
                continue
            k, nm = keyfn(e[0])
            keys_se2.append((k, nm, e))
        reg_keys = {keyfn_reg(r) for r in rows} if False else None
        for k, nm, e in keys_se2:
            rr = cv.n + 1
            cv.row([k, nm, f'=COUNTIF({regname},$A{rr})', f'=ROUND(SUMIFS(Reg_Amount,{regname},$A{rr}),2)',
                    f'=ROUND(SUMIFS(Reg_Amount,{regname},$A{rr},Reg_Theme,"{T9}"),2)', f'=ROUND(SUMIFS(Reg_Amount,{regname},$A{rr},Reg_Status,"Confirmed"),2)',
                    f'=ROUND(SUMIFS(Reg_Amount,{regname},$A{rr},Reg_Status,"Pending evidence"),2)', e[6], f'=IF(ROUND(D{rr}-H{rr},2)=0,"TRUE","FALSE")',
                    e[7], f'=J{rr}-D{rr}', e[10], f'=IF(L{rr}=0,0,D{rr}/L{rr})'],
                   money_cols=(4, 5, 6, 7, 8, 10, 11, 12), input_cols=(8, 10, 12))
        b = cv.n; t = b + 1
        cv.row(['Total', ''] + [f'=SUM({CL(c)}{a}:{CL(c)}{b})' if c not in (9, 13) else None for c in range(3, 14)], 'tot', money_cols=(4, 5, 6, 7, 8, 10, 11, 12))
        cv.blank()
        controls.append(('2. Coverage ties', 'Coverage', f'{title}: every key ties to its SE2 row', 'count', f'=SUMPRODUCT(--(Coverage!I{a}:I{b}="TRUE"))', b - a + 1))
        controls.append(('2. Coverage ties', 'Coverage', f'{title}: panel total equals the control total', 'value', f'=Coverage!D{t}', 4910566.68))
        controls.append(('2. Coverage ties', 'Coverage', f'{title}: panel line count equals the register line count', 'count', f'=Coverage!C{t}', N))
        return [k for k, _, _ in keys_se2]
    split = lambda s: tuple((s.split(' - ', 1) + [''])[:2])
    na_keys = cov_panel('Panel A, natural account', 'Natural Account', 'Reg_NA', split)
    wo_keys = cov_panel('Panel B, WO Task', 'WO Task', 'Reg_PKHeader', lambda s: (s, '') if s else ('(no WO Task)', 'Blank WO Task in TechOne (SE2 blank-key row)'))
    sv_keys = cov_panel('Panel C, service', 'Service No', 'Reg_Service', split)
    for keyset, col in ((na_keys, 14), (wo_keys, 16), (sv_keys, 19)):
        missing = {str(r['V'][col]) for r in rows} - set(keyset)
        assert not missing, (col, missing)

    # ============================================================== PK_Listing
    pk = Sheet(wb, 'PK_Listing', {'A': 10, 'B': 10, 'C': 36, 'D': 16, 'E': 18, 'F': 10, 'G': 18})
    pk.row(['PK listing: every section, service, WO Task and PK charged combination'], 'title')
    pk.row(['Live COUNTIFS/SUMIFS. PK Charged is the ledger Work Order whenever populated (rule 1).'], 'sub')
    pk.blank()
    pk.row(['Section', 'Service', 'Service name', 'WO Task (PK Header)', 'PK Charged', 'Lines', '$ ex GST net'], 'blue')
    combos = sorted({(str(r['V'][2]), str(r['V'][19]), str(r['V'][16]), str(r['V'][17])) for r in rows})
    a = pk.n + 1
    for s_, sv, h, p in combos:
        rr = pk.n + 1
        pk.row([s_, sv, svc_names.get(sv, ''), h, p, f'=COUNTIFS(Reg_Section,$A{rr},Reg_Service,$B{rr},Reg_PKHeader,$D{rr},Reg_PK,$E{rr})',
                f'=ROUND(SUMIFS(Reg_Amount,Reg_Section,$A{rr},Reg_Service,$B{rr},Reg_PKHeader,$D{rr},Reg_PK,$E{rr}),2)'], money_cols=(7,))
    b = pk.n; t = b + 1
    pk.row(['Total', '', '', '', '', f'=SUM(F{a}:F{b})', f'=SUM(G{a}:G{b})'], 'tot', money_cols=(7,))
    controls.append(('3. Summary ties', 'PK_Listing', 'PK listing total equals the register total', 'value', f'=PK_Listing!G{t}', 4910566.68))
    controls.append(('3. Summary ties', 'PK_Listing', 'PK listing line count equals the register line count', 'count', f'=PK_Listing!F{t}', N))

    # ============================================================== Vendor_Series
    vs = Sheet(wb, 'Vendor_Series', {'A': 58, 'B': 58, 'C': 16, 'D': 10, 'E': 18, 'F': 10, 'G': 40, 'H': 50})
    vs.row(['Contractor and series register, FY2026/27 branch'], 'title')
    vs.row(['Live COUNTIF/SUMIFS by contractor label on the escaped criteria in column B (~ * ? escaped). Labels differing only in case are one row, because COUNTIF is case-insensitive; the variants are named in column H. ABN is shown only where a line carries one (Tier 1).'], 'sub')
    vs.blank()
    vs.row(['Contractor / series label', 'Criteria (escaped)', 'ABN on lines', 'Lines', '$ ex GST (net)', 'Tiers', 'Sections', 'Case variants and provenance'], 'blue')
    grp = collections.OrderedDict()
    for r in rows:
        lab = str(r['V'][12] or '(blank)')
        g = grp.setdefault(lab.casefold(), dict(labels=collections.Counter(), amt=Decimal(0), abn=set(), tiers=set(), secs=set(), inh=0, new=0))
        g['labels'][lab] += 1; g['amt'] += D(r['V'][20])
        if r['V'][13]: g['abn'].add(str(r['V'][13]))
        g['tiers'].add(str(r['V'][29])); g['secs'].add(sec_names[str(r['V'][2])])
        g['inh' if r['meta']['inherited'] else 'new'] += 1
    assert '(blank)' not in grp
    a = vs.n + 1
    for key, g in sorted(grp.items(), key=lambda kv: -abs(kv[1]['amt'])):
        rr = vs.n + 1
        lab = g['labels'].most_common(1)[0][0]
        note = f'{g["inh"]} inherited, {g["new"]} new' + (f'; variants: {" | ".join(g["labels"])}' if len(g['labels']) > 1 else '')
        vs.row([lab, esc(lab), '; '.join(sorted(g['abn'])) or None, f'=COUNTIF(Reg_Contractor,$B{rr})', f'=ROUND(SUMIFS(Reg_Amount,Reg_Contractor,$B{rr}),2)',
                ', '.join(sorted(g['tiers'])), '; '.join(sorted(g['secs'])), note], money_cols=(5,))
    b = vs.n; t = b + 1
    vs.row(['Total', '', '', f'=SUM(D{a}:D{b})', f'=SUM(E{a}:E{b})'], 'tot', money_cols=(5,))
    controls.append(('3. Summary ties', 'Vendor_Series', 'Vendor series total equals the register total', 'value', f'=Vendor_Series!E{t}', 4910566.68))
    controls.append(('3. Summary ties', 'Vendor_Series', 'Vendor series line count equals the register line count', 'count', f'=Vendor_Series!D{t}', N))

    # ============================================================== Journal_Sets
    js = Sheet(wb, 'Journal_Sets', {'A': 16, 'B': 8, 'C': 16, 'D': 16, 'E': 30, 'F': 26, 'G': 24, 'H': 10, 'I': 40, 'J': 12, 'K': 12, 'L': 70})
    js.row(['Journal sets by reference, read at branch scope (rules 5, 6 and 21)'], 'title')
    js.row(['One row per journal reference on the Register (column EG). Net and balance class are live; Register columns EI:EJ look them up here. A set that nets to zero here may still carry a leg outside O110-O115 only if equal and opposite legs are both outside, which a net of zero inside scope cannot show.'], 'sub')
    js.blank()
    js.row(['Journal reference', 'Lines', '$ net in branch scope', '$ debit legs', 'Balance class', 'Journal type', 'Document File(s)', 'Periods', 'Sections touched', 'Lines inherited', 'Lines new', 'First narration'], 'blue')
    for j in jrefs:
        rr = js.n + 1; jr = jref_rows[j]
        jt = 'RJ system reversing journal' if j.startswith('RJ') else f'Manual journal, {j[:2]} series'
        js.row([j, f'=COUNTIF(Reg_JRef,$A{rr})', f'=ROUND(SUMIFS(Reg_Amount,Reg_JRef,$A{rr}),2)', f'=ROUND(SUMIFS(Reg_Amount,Reg_JRef,$A{rr},Reg_Amount,">0"),2)',
                f'=IF(C{rr}=0,"Nets to zero in branch scope","Net movement in branch scope")', jt,
                '; '.join(sorted({pbr_stage.clean_num_text(r['V'][69]) for r in jr}))[:200],
                ', '.join(sorted({pbr_stage.clean_num_text(r['V'][56]) for r in jr})),
                '; '.join(sorted({sec_names[str(r['V'][2])] for r in jr})),
                sum(1 for r in jr if r['meta']['inherited']), sum(1 for r in jr if not r['meta']['inherited']),
                str(jr[0]['V'][22] or '').replace('\n', ' | ')[:200]], money_cols=(3, 4))
    assert js.n == JS_LAST
    js.blank()
    js.row(['Total', f'=SUM(B5:B{JS_LAST})', f'=SUM(C5:C{JS_LAST})', f'=SUM(D5:D{JS_LAST})', f'=COUNTIF(E5:E{JS_LAST},"Nets to zero in branch scope")'], 'tot', money_cols=(3, 4))
    jtot = sum(jnet.values()); jlines = sum(len(v) for v in jref_rows.values())
    controls.append(('5. Journal pairing', 'Journal_Sets', 'Journal sets net total equals the Decimal sum at build', 'value', f'=Journal_Sets!C{JS_TOT}', float(jtot)))
    controls.append(('5. Journal pairing', 'Journal_Sets', 'Journal set line count equals the journal lines on the Register', 'count', f'=Journal_Sets!B{JS_TOT}', jlines))
    controls.append(('5. Journal pairing', 'Journal_Sets', 'Sets netting to zero in branch scope', 'count', f'=Journal_Sets!E{JS_TOT}', js_zero))
    controls.append(('5. Journal pairing', 'Register', 'New lines verdicted Journal (net-zero) whose set does not net to zero (must be 0)', 'count',
                     f'=SUMPRODUCT((Register!$AE${FIRST}:$AE${LAST}="Journal (net-zero)")*(Register!$EJ${FIRST}:$EJ${LAST}<>"Nets to zero in branch scope")*(Register!$ER${FIRST}:$ER${LAST}="{NEW}"))', 0))

    # ============================================================== Journal_Pull sheet (data computed before Method, which cites it)
    jp = Sheet(wb, 'Journal_Pull', {'A': 30, 'B': 14, 'C': 30, 'D': 10, 'E': 12, 'F': 16, 'G': 16, 'H': 10, 'I': 11, 'J': 80, 'K': 26, 'L': 26, 'M': 24, 'N': 60})
    jp.row(['Journal pull list, Parks Branch FY2026/27 (rule 21). One row per TechOne document file, which is the unit a Document Line Table export is pulled by.'], 'title')
    jp.row(['Tier A: no attachment in TechOne, so the Document Line Table IS the evidence route - pull these. Tier B: the document carries a TechOne attachment, so sight the attachment; a pull adds nothing. '
            'Tier C: RJ reversing journals, which net to exactly zero and are read as a pair under rules 5 and 6 - no pull unless a specific accrual question arises. Tier D: the document is already embedded in the PS & WP register v127 Journal_Sources; a re-pull is audited leg by leg, never re-captured (rule 12). '
            'Ranked within tier by ABSOLUTE net cost movement into branch O110-O115, not by gross, because gross double-counts both legs of a transfer.'], 'sub')
    jp.blank()
    jp.row(['Tier', 'Document file', 'Journal ref(s)', 'Period(s)', 'Register lines', 'Net in scope $', 'Gross in scope $', 'Attachment', 'Pull value', 'Why it matters', 'Sections touched', 'Top accounts', 'Top PKs', 'Narration (first, verbatim)'], 'blue')
    JP_A = jp.n + 1
    for x in jp_rows:
        refs = x['refs'][0] if len(x['refs']) == 1 else f'{x["refs"][0]} ... {x["refs"][-1]} ({len(x["refs"])} refs)'
        jp.row([x['tier'], x['df'], refs, ', '.join(x['per']), x['n'], float(x['net']), float(x['gross']), x['att'], x['val'], x['why'], '; '.join(x['secs']),
                '; '.join(k for k, _ in x['acc'].most_common(3)), '; '.join(k for k, _ in x['pks'].most_common(3)), x['narr']], money_cols=(6, 7))
    JP_B = jp.n; JP_TOT = JP_B + 2
    jp.blank()
    jp.row(['TOTAL, every journal document file', '', '', '', f'=SUM(E{JP_A}:E{JP_B})', f'=ROUND(SUM(F{JP_A}:F{JP_B}),2)', f'=ROUND(SUM(G{JP_A}:G{JP_B}),2)'], 'tot', money_cols=(6, 7))
    jp.blank()
    jp.row(['By tier', 'Documents', '', '', 'Register lines', 'Net in scope $', 'Gross in scope $'], 'blue')
    tiers = sorted({x['tier'] for x in jp_rows})
    for t_ in tiers:
        rr = jp.n + 1
        jp.row([t_, f'=COUNTIF($A${JP_A}:$A${JP_B},$A{rr})', '', '', f'=SUMIF($A${JP_A}:$A${JP_B},$A{rr},$E${JP_A}:$E${JP_B})',
                f'=ROUND(SUMIF($A${JP_A}:$A${JP_B},$A{rr},$F${JP_A}:$F${JP_B}),2)', f'=ROUND(SUMIF($A${JP_A}:$A${JP_B},$A{rr},$G${JP_A}:$G${JP_B}),2)'], money_cols=(6, 7))
    jp_tier = collections.Counter(x['tier'] for x in jp_rows)
    jp_absA = sum(abs(x['net']) for x in jp_rows if x['tier'].startswith('A'))
    jp_hi = [x for x in jp_rows if x['val'] == 'High' and x['tier'].startswith(('A', 'B'))]
    jp.blank()
    jp.row([f'Reading: {jp_tier.get("A Pull required", 0)} documents sit in Tier A ({fmt_money(jp_absA)} absolute net) because no attachment exists, and rule 21 ranks them by absolute net. '
            f'The Pull value column is the evidence judgement on top of that ranking: {len(jp_hi)} document(s) across Tiers A and B carry an unanswered question (a recode that does not net, an accrual that does not pair, or a blank narration) and are the ones worth working first; '
            f'the large internal-charge allocations rank high on value but carry every leg on the register already. Pull by document file, not by journal reference: one export covers every reference on the file (document 1252466 alone carries 8).'], 'sub')
    controls.append(('8. Journal pull (rule 21)', 'Journal_Pull', 'Journal document files listed equals the distinct document files on journal lines', 'count', f'=COUNTA(Journal_Pull!$B${JP_A}:$B${JP_B})', len(jp_rows)))
    controls.append(('8. Journal pull (rule 21)', 'Journal_Pull', 'Register lines covered equals the journal lines on the Register', 'count', f'=Journal_Pull!E{JP_TOT}', sum(len(v_) for v_ in jp_doc.values())))
    controls.append(('8. Journal pull (rule 21)', 'Journal_Pull', 'Net in scope totals the journal lines on the Register', 'value', f'=Journal_Pull!F{JP_TOT}', float(sum(D(r['V'][20]) for r in rows if r['V'][137]))))
    say(f'journal pull: {len(jp_rows)} document files, tiers {dict(jp_tier)}, Tier A absolute net {fmt_money(jp_absA)}')

    # ============================================================== Open_Items
    oi = Sheet(wb, 'Open_Items', {'A': 10, 'B': 28, 'C': 16, 'D': 30, 'E': 8, 'F': 16, 'G': 90, 'H': 60})
    oi.row(['Open items, Parks Branch register FY2026/27'], 'title')
    oi.row(['B-### items are this register\'s own. PSWP-# rows carry the PS & WP register items cited on inherited lines, verbatim. Lines and $ are fixed at the v1 build; the Register is the live position.'], 'sub')
    oi.blank()
    oi.row(['#', 'Area', 'Status', 'Section / scope', 'Lines', '$ ex GST (net, v1)', 'Action', 'Basis'], 'blue')
    items = []
    od = stage['oi_data']
    top_pk = collections.defaultdict(lambda: collections.defaultdict(Decimal))
    for r in rows:
        if r['V'][12] == UNID:
            top_pk[str(r['V'][2])][str(r['V'][17])] += D(r['V'][20])
    for code, (n_, amt) in sorted(unid_by_sec.items(), key=lambda kv: -kv[1][1]):
        tp = sorted(top_pk[code].items(), key=lambda kv: -kv[1])[:3]
        items.append(('Contractor identification', 'Pending evidence', sec_names[code], n_, amt,
                      'Request APLEDGER creditor histories for the supplier series behind these PKs (rule 12), or sight TechOne attachments by Document File. Largest PKs: ' + '; '.join(f'{p} {fmt_money(v)}' for p, v in tp) + '.',
                      'AP lines with no creditor history and no narration-named supplier (Tier 3).'))
    eoy = od.get('eoy_reversal', [])
    if eoy:
        items.append(('Cross-FY accrual reversals', 'Open', 'All sections (new lines)', len(eoy), sum(a_ for _, a_ in eoy),
                      'Pair each P1 "End of Year 25/26 AP Accrual" reversal against its FY2025/26 accrual (26SLACT P12, not loaded outside PS/WP). Until paired, read section YTD net of these legs (rule 5).',
                      'Journal narration; reference sets do not net inside FY2026/27.'))
    rec = od.get('recode_open', [])
    if rec:
        refs = sorted({x[2] for x in rec})
        items.append(('Recode sets not netting in scope', 'Review', 'All sections (new lines)', len(rec), sum(x[1] for x in rec),
                      'Pull the Document Line Table for each reference (rule 21) and find the balancing leg outside O110-O115: ' + ', '.join(refs) + '.',
                      'Journal_Sets balance class "Net movement in branch scope" on a recode narration.'))
    nas = od.get('na_section', [])
    if nas:
        items.append(('Service without a section', 'Open', 'Service ' + ', '.join(sorted({x[0] for x in nas})), len(nas), sum(x[1] for x in nas),
                      'Confirm with Finance which section owns service 20821 (PKs ' + ', '.join(sorted({x[2] for x in nas})) + '); the lines carry Section NA and no WO Task, so no WO Task budget can absorb them. The OneCouncil mapping work already lists 20821 as unassigned.',
                      'TechOne account structure on the export (Section NA, WO Task blank).'))
    if reclass:
        n_ = sum(sum(1 for r in jref_rows[j] if r['meta']['inherited']) for j in reclass)
        a_ = sum(sum(D(r['V'][20]) for r in jref_rows[j] if r['meta']['inherited']) for j in reclass)
        items.append(('Inherited journal verdicts to re-adjudicate', 'Review', 'Park Services / Water Parks', n_, a_,
                      f'{len(reclass)} journal sets carried Partial, Review or Journal (reversal) on the PS & WP scope but net to zero once the other branch legs are in scope: ' + ', '.join(reclass[:40]) + ('...' if len(reclass) > 40 else '') + '. Re-adjudicate in the next build (rule 6); v1 carries the v127 verdicts unchanged.',
                      'Journal_Sets at branch scope.'))
    typo_inh = sum(1 for r in rows if r['meta']['inherited'] and r['V'][7] == 'FY2027/28')
    items.append(('Printed-year error in accrual narration', 'Housekeeping', 'All sections', len(stage['typo_rows']) + typo_inh, None,
                  f'The monthly accrual narration prints "July 2027" / "August 2027" for FY2026/27 periods. New lines read FY (Service) from the posting year ({len(stage["typo_rows"])} lines); {typo_inh} inherited PS/WP lines still read FY2027/28 from v127. Restate the inherited lines in the PS & WP register and here together, and ask the accrual preparer to correct the narration template (DM 18989758).',
                  'Narration text against posting period.'))
    um = stage['unmatched_v']
    items.append(('v127 lines absent from the 11-Sep pull', 'Open', 'Park Services / Water Parks', len(um), sum(D(r[19]) for _, r in um),
                  f'{len(um)} FY2026/27 lines held in PS & WP v127 are not in this pull under the same Document Unique ID, account and Details (listed on Inheritance_Log).'
                  ' Confirm they were re-keyed or reversed in TechOne, then retire them from the PS & WP register at its next refresh.',
                  'Inheritance match key (Method 5.0).'))
    se2wo = [(e[0], e) for e in se2['WO Task']['body'] if e[0]]
    nobud = [(k, e) for k, e in se2wo if abs(e[6]) > 0.005 and abs(e[10]) < 0.005]
    if nobud:
        items.append(('Actuals on WO Tasks with no revised budget', 'Open', 'Branch', len(nobud), sum(D(e[6]) for _, e in nobud),
                      'YTD actual posts to WO Tasks carrying no revised annual budget: ' + '; '.join(f'{k} {fmt_money(e[6])} (original budget {fmt_money(e[11])})' for k, e in sorted(nobud, key=lambda x: -x[1][6])[:8]) + '. Where an original budget exists the revised budget has moved to another WO Task on the same service; confirm the PK the budget and the spend should share.',
                      'SE2 by WO Task, 27SLORB against 27SLORI.'))
    zeroytd = [(k, e) for k, e in se2wo if abs(e[7]) < 0.005 and e[10] > 0.005 and e[6] > 1000]
    if zeroytd:
        items.append(('Spend against an unphased budget', 'Housekeeping', 'Branch', len(zeroytd), sum(D(e[6]) for _, e in zeroytd),
                      'WO Tasks with an annual budget but a nil P1-3 phased budget and material spend: ' + '; '.join(f'{k} {fmt_money(e[6])} of {fmt_money(e[10])} annual' for k, e in sorted(zeroytd, key=lambda x: -x[1][6])[:8]) + '. YTD variance on these reads as overspend by construction; review the phasing.',
                      'SE2 by WO Task.'))
    items.append(('Glascott schedule v face', 'Review', 'Natural Areas', 2, 57695.07,
                  'Invoices 012191 and 012197 bill $32,477.92 and $25,217.15 on the face; the attached schedules total $32,951.44 and $27,073.64 ($473.52 and $1,856.49 more) and carry rows on PK000382, PK000383 and PK000379 outside PK000378. Confirm with Natural Areas whether the face or the schedule is the agreed claim, and whether the other-PK rows were billed elsewhere. Letterhead prints Technigro ABN 97 001 281 572 with a Glascott bank account. Entity resolved at v4: APLEDGER GLA009 carries ABN 97001281572, so the creditor record is Glascott Landscape and Civil Pty Limited (rule 8).',
                  'Sighted invoices GLASCOTT 012191/012197 and attachments (rule 16d).'))
    items.append(('Activeco INV-9360 date error', 'Housekeeping', 'Natural Areas', 1, 51704.65,
                  'Invoice dated 31-Mar-2026, due 30-Apr-2026, for July 2026 treatments, posted 24-Jul-2026. Ask Activeco to reissue with the correct date; no financial effect. FY (Service) reads Jul-2026 from the treatment dates.',
                  'Sighted invoice INV-9360.'))
    items.append(('Austspray item-row figures', 'Housekeeping', 'Park Maintenance', 3, 208355.33,
                  '158592, 158850 and 158853 print a different figure on the item row from the "plus gst" figure in the description; the variations reconcile each to the subtotal. Note for the PAR/338A/2025 contract administrator; no financial effect.',
                  'Sighted invoices, check 1 TRUE on all three.'))
    ported = [r for r in sighted if r['meta'].get('ported')]
    if ported:
        items.append(('Port branch v3 captures to the PS_WP register', 'Open', 'Park Services / Water Parks', len(ported), sum(D(r['V'][20]) for r in ported),
                      'Batch mixed_new_26_27 green blocks on lines inherited from PS_WP v127 (Register col ER flags them). The PS_WP register is the record for the three-year audit; port these captures at PS_WP v128 from corpus_mixed_new_26_27_v6.json and match_mixed_new_26_27_v6.json, then re-inherit here so the two registers agree.',
                      'Register provenance column; Method 5.0.'))
    items.append(('Service 20821 is the mowing fuel levy leg', 'Resolved at v3', 'Park Maintenance', 4, 5889.34,
                  'Coast2Coast INV-11834 and INV-11835 print a FUEL LEVY SURCHARGE line of $1,398.11 and $1,523.65; TechOne posts each to PK000513 service 20821 (Section NA) beside the mowing line on the zone PK. Service 20821 belongs to Park Maintenance mowing (fuel levy); ask Finance to map it to 4090230 (supersedes B-013 for these lines).',
                  'Sighted invoices, split-posting by LineKey.'))
    items.append(('Origin consolidated invoices, partial scope', 'Note', 'Water Parks', 2, 5574.72,
                  'Consolidated invoices 1026099 ($565,345.00) and 1026231 ($576,921.08) are Council-wide, 47 to 48 sites; Parks carries only Logan Garden Park (NMI QB10790446 8) at $2,752.17 and $2,822.55. Captured in full under rule 16 (all site rows); register ties by LineKey to the Parks site row.',
                  'Sighted invoices, PARTIAL-SCOPE variant.'))
    items.append(('Case-variant contractor label', 'Housekeeping', 'Vendor_Series', None, None,
                  '"LCC internal billing (Plant & Fleet / Workshop)" and "... / workshop)" are both carried from v127. Vendor_Series groups them; canonicalise in both registers at the next housekeeping build. Same trap on ABN strings at v4 and v5: Treescape Australasia carries "20 117 830 118" (APLEDGER TRE010) against "20-117-830-118 (printed with hyphens)" (branch v2 capture), and Coast2Coast carries "24 488 420 203" (APLEDGER COA030 and the v5 capture) against "24488420203 (printed ungrouped)" (branch v3 capture). Column M should hold the grouped form on every line and the green block the printed form; canonicalise in both registers at the next housekeeping build.',
                  'COUNTIF case-insensitivity trap.'))
    _hm = stage['hist_matches']; _inh = ident_rows
    if _inh:
        items.append(('Port branch v4 identifications to the PS_WP register', 'Open', 'Park Services / Water Parks', len(_inh), sum(D(r['V'][20]) for r in _inh),
                      f'{len(_inh)} inherited lines were Unidentified, series-inferred or vendor-inferred in PS_WP v127 and are now Tier 1 from the APLEDGER histories (Register col ER "identified at branch v4", v5 or v6; ' + ', '.join(f'{c_} {n_}' for c_, n_ in sorted(collections.Counter(r['meta']['ident_v4'] for r in _inh).items())) + '). Port at PS_WP v128 with the same history files (Data_Acquisition F7 onward), then re-inherit here.',
                      'Creditor_Lines (branch v4 block); Method 12.0.'))
    if stage['hist_conflicts']:
        items.append(('Contractor label superseded by an APLEDGER match', 'Review', 'Park Services', len(stage['hist_conflicts']), sum(a_ for _, _, _, a_ in stage['hist_conflicts']),
                      'The PS_WP v127 label named a different vendor on a vendor-inference basis; the APLEDGER history (reference, incl amount, date, ABN) now identifies the creditor: ' + '; '.join(f'{lk} was "{pl}", now {code}' for lk, pl, code, _ in stage['hist_conflicts']) + '. Sight the invoice to settle it and correct PS_WP v128.',
                      'Rule 8: a creditor history with ABN outranks a vendor inference.'))
    if stage['hist_ambiguous']:
        items.append(('Ambiguous history references', 'Note', 'Branch', len(stage['hist_ambiguous']), None,
                      'References where more than one creditor history ties by amount and date, left unidentified: ' + '; '.join(f'{r_} ({", ".join(c_)})' for r_, c_ in stage['hist_ambiguous'][:20]) + '.', 'Match rule, Method 12.0.'))
    _pk = [r for r in sighted if re.match(r'11-Sep-2026, branch v[45]', str(r['V'][126] or '')) and r['V'][104] not in (None, '(not printed)', 'undefined (as printed)') and str(r['V'][104]).replace(' ', '') != str(r['V'][17])]
    if _pk:
        items.append(('Printed PK differs from PK charged (sighted invoices, branch v4 and v5)', 'Housekeeping', '; '.join(sorted({sec_names[str(r['V'][2])] for r in _pk})), len(_pk), sum(D(r['V'][20]) for r in _pk),
                      '; '.join(f'{r["V"][88]} prints {r["V"][104]}, charged {r["V"][17]}' for r in _pk) + '. The invoice text supports the PK charged in each case except Play Force INV-8502, where the printed PK000338 is not a WO Task in this register (see the coding note on that line). Ask each supplier to quote the charged WO Task. No financial effect.',
                      'Sighted invoices, Batches attach_1, attach_2 and code.'))
    _undef = [r for r in sighted if str(r['V'][104]) == 'undefined (as printed)']
    if _undef:
        items.append(('Supplier invoice prints no PK ("undefined")', 'Housekeeping', 'Park Services', len(_undef), sum(D(r['V'][20]) for r in _undef),
                      'Play Force invoices ' + ', '.join(str(r['V'][88]) for r in _undef) + ' print the literal word "undefined" in the Account field, so the invoice face carries no PK; the work-order row names the park and the charge follows it. '
                      'On INV-8564 the only description is "as per Quote 692442" and the quote is not in the binder. Ask Play Force to populate the Account field and obtain quote 692442.',
                      'Sighted invoices, Batch code (capture report findings F4 and F5).'))
    items.append(('Coast2Coast fuel levy computed on a GST-inclusive base', 'Review', 'Park Maintenance / Section NA', 1, 6.82,
                  'INV-11824 prints "$4,475.56 x 0.2477 = $1108.59 x 0.0677 = $75.05", but $4,475.56 is the GST-inclusive figure for work of $4,068.69 ex GST; on the ex-GST base the levy is $68.23, so $6.82 ex GST ($7.50 incl) is over-claimed. '
                  'INV-11833, same supplier, same contract PAR/336E/2024, same month, uses the ex-GST base correctly ($59,796.25 x 0.2477 x 0.0677 = $1,002.74). Raise with the contract administrator, and verify the 0.2477 fuel component and 0.0677 escalation against the current Brisbane diesel TGP band before the next payment.',
                  'Sighted invoices INV-11824 and INV-11833 (Batch attach_2); the levy legs post to PK000513 service 20821.'))
    for k, it in enumerate(items, 1):
        oi.row([f'B-{k:03d}'] + list(it), money_cols=(6,))
    cited = collections.Counter()
    for r in rows:
        if r['meta']['inherited']:
            for c in (25, 28, 32, 34, 127):
                for m in re.findall(r'Open Items? ?#?(\d{1,3})', str(r['V'][c] or '')):
                    cited[int(m)] += 1
    voi = {int(r[0]): r for r in v127['Open_Items'][4:] if isinstance(r[0], float)}
    for num in sorted(cited):
        if num in voi:
            r = voi[num]
            oi.row([f'PSWP-{num}', f'Carried from PS & WP v127 ({cited[num]} citing lines)', r[2], r[3], r[4], r[5], r[6], f'PS & WP FY {r[1]}'], money_cols=(6,))

    # ============================================================== Inheritance_Log
    il = Sheet(wb, 'Inheritance_Log', {'A': 10, 'B': 30, 'C': 28, 'D': 12, 'E': 16, 'F': 10, 'G': 12, 'H': 16, 'I': 18, 'J': 60})
    il.row(['Inheritance log: every PS & WP register v127 FY2026/27 line'], 'title')
    il.row([f'Source {os.path.basename(pbr_stage.V127)} md5 {stage["v127_md5"]}. Match key per Method 5.0. The Register row is this workbook\'s row.'], 'sub')
    il.blank()
    il.row(['v127 row', 'LineKey', 'Outcome', 'Register row', 'Reference', 'NA', 'PK Charged', 'Amount ex GST', 'v127 Status', 'Note'], 'blue')
    vrows = [(n, r) for n, r in ((i + 1, r) for i, r in enumerate(v127['Register'][4:31364], 4)) if r[4] == 'FY2026/27']
    um_set = {n for n, _ in um}
    for n, r in vrows:
        if n in um_set:
            il.row([n, r[0], 'Absent from the 11-Sep pull', None, r[7], r[13], r[16], r[19], r[32], str(r[21])[:120]], money_cols=(8,))
        else:
            il.row([n, r[0], 'Inherited', v2new[n], r[7], r[13], r[16], r[19], r[32], None], money_cols=(8,))

    # ============================================================== Creditor_Lines
    cl = Sheet(wb, 'Creditor_Lines', {'A': 40, 'J': 50, 'AB': 44})
    cl.row(['Creditor ledger lines supporting FY2026/27 identifications'], 'title')
    cl.row([f'Rows 5-{4 + len(cl_keep)}: carried verbatim from PS & WP v127 Creditor_Lines (every line matched there to FY2026/27, plus the lines matched at branch v1 by reference and amount; column AB is the v127 row). '
            f'Rows {5 + len(cl_keep)}-{CL_LAST}: the {len(HISTS)} APLEDGER creditor histories pulled 11-Sep-2026 for branch v4 to v6, embedded in full and verbatim (rule 3, rule 14); column AB is the export row and the version the history was added at, column AC marks the lines matched to a register line (Method 12.0).'], 'sub')
    cl.blank()
    cl.row(list(CLv[3][:27]) + ['v127 Creditor_Lines row / APLEDGER export row', 'Used at branch (v1 new lines / v4 to v6 identifications)'], 'grey')
    for i, r in cl_keep:
        cl.row(list(r[:27]) + [i, 'Y' if i in new_ci else None], date_cols=(4, 5, 8, 14, 15))
    for k_, hh in enumerate(HISTS):
        for i, r in hh['data']:
            assert cl.n + 1 == clrow[(k_, i)]
            hit = (k_, i) in hm_set
            cl.row([f"{hh['code']} ({hh['label']})", 'FY2026/27' if hit else None] + list(r[:25]) + [f"APLEDGER {hh['code']} export row {i} (branch {hh.get('added', 'v4')} pull)", 'Y' if hit else None], date_cols=(4, 5, 8, 14, 15))
    assert cl.n == CL_LAST
    controls.append(('7. Creditor histories (v4 to v6)', 'Creditor_Lines', 'Creditor_Lines rows carried from the branch v4 to v6 APLEDGER pulls', 'count', f'=COUNTIF(Creditor_Lines!$AB$5:$AB${CL_LAST},"APLEDGER*")', len(clrow)))
    controls.append(('7. Creditor histories (v4 to v6)', 'Creditor_Lines', 'History lines (branch block) matched to a register line (column AC = Y)', 'count', f'=COUNTIF(Creditor_Lines!$AC${5 + len(cl_keep)}:$AC${CL_LAST},"Y")', len(hm_set)))
    controls.append(('7. Creditor histories (v4 to v6)', 'Register', 'Register lines whose evidence cites a branch APLEDGER history row', 'count', f'=COUNTIF(Register!$AB${FIRST}:$AB${LAST},"*history pulled 11-Sep-2026*")', hist_cited))
    controls.append(('7. Creditor histories (v4 to v6)', 'Register', 'Inherited lines identified at branch v4 to v6 (provenance column)', 'count', f'=COUNTIF(Reg_Prov,"*identified at branch v*")', len(ident_rows)))
    controls.append(('7. Creditor histories (v4 to v6)', 'Creditor_Lines', 'Creditor_Lines rows from the four histories added at v6', 'count', f'=COUNTIF(Creditor_Lines!$AB$5:$AB${CL_LAST},"*(branch v6 pull)")', sum(h['n'] for h in HISTS if h.get('added') == 'v6')))

    # ============================================================== SE2_Budget
    sb = Sheet(wb, 'SE2_Budget', {'A': 44})
    sb.row(['SE2 budget vs actual exports, FY2026/27 P1-3, verbatim'], 'title')
    sb.row(['Four exports on identical criteria (Branch 4090000, O110-O115, expense type 1), pulled 11-Sep-2026. Each block reproduces the export cell for cell.'], 'sub')
    for k, s in se2.items():
        sb.blank()
        sb.row([f'SE2 by {k}: {os.path.basename(s["path"])}, md5 {s["md5"]}'], 'blue')
        for r in s['rows']:
            sb.row(list(r), money_cols=tuple(range(2, 13)) if isinstance(r[1], float) else ())

    # ============================================================== Evidence_Invoices
    eih = list(EI[3][:32]) + ['Provenance (v127 row and original verification text, or the batch that captured it)']
    ei = Sheet(wb, 'Evidence_Invoices', {'A': 18, 'B': 30, 'M': 60, 'N': 50, 'AG': 70})
    ei.row(['Evidence invoices carried for the FY2026/27 sighted register lines (rule 16)'], 'title')
    ei.row(['One row per invoice. Column M is restated from the EvID maps (rule 19.10); column AG keeps the v127 text verbatim. No control block sits below the data: the rule 17 controls live on Controls.'], 'sub')
    ei.blank()
    ei.row(eih, 'green')
    for e in ev_order:
        vr, r, note = ei_rows[e]
        vals = list(r[:32])
        rr_list = reg_rows_by_ev[e]
        vals[12] = (f'Lines reconcile to the printed subtotal to the cent; reconciliation at EIL_Controls row {ei_new[e]}. '
                    f'Rule 17 checks live on Register row{"s" if len(rr_list) > 1 else ""} {", ".join(map(str, rr_list))}.')
        ei.row(vals + [note], money_cols=(10, 11, 12))
    assert ei.n == EI_LAST
    ei.blank()
    ei.row(['Totals (carried invoice headers)', '', '', '', '', '', '', '', f'=SUM(I5:I{EI_LAST})', f'=SUM(J5:J{EI_LAST})', f'=SUM(K5:K{EI_LAST})', f'=SUM(L5:L{EI_LAST})'], 'tot', money_cols=(10, 11, 12))
    EI_TOT = EI_LAST + 2

    el = Sheet(wb, 'Evidence_Invoice_Lines', {'A': 18, 'C': 80, 'J': 30, 'K': 50})
    el.row(['Evidence invoice lines carried, verbatim (rule 16)'], 'title')
    el.row(['One row per printed line: carried unchanged from PS & WP v127, or captured at branch v2, v3 and v4 from Batches mixed_1, mixed_new_26_27 and attach_1. Column J joins to the Register LineKey. ATTACHMENT rows (Glascott schedules) carry no amount in column G and are excluded from check 1 (rule 16d).'], 'sub')
    el.blank()
    el.row(list(EIL[3][:13]), 'green')
    for r in eil_lines:
        el.row(list(r[:13]), money_cols=(5, 7))
    assert el.n == EIL_LAST

    ec = Sheet(wb, 'EIL_Controls', {'A': 18, 'B': 22, 'C': 18, 'D': 26, 'E': 10})
    ec.row(['EIL_Controls: rule 17 check 1, one reconciliation per carried invoice'], 'title')
    ec.row(['Captured lines summed by invoice against the printed target on Evidence_Invoices.'], 'sub')
    ec.blank()
    ec.row(['Invoice', 'Captured lines (ex GST unless basis = Incl GST)', 'Printed target', 'Basis', 'Check 1'], 'green')
    for e in ev_order:
        rr = ec.n + 1
        basis = eilc_basis[e]
        tgt = 'EI_InclGST' if 'incl' in basis.lower() else 'EI_ExGST'
        ec.row([e, f'=ROUND(SUMIF(EIL_Invoice,$A{rr},EIL_Amount),2)', f'=INDEX({tgt},MATCH($A{rr},EI_Invoice,0))', basis, f'=IF(B{rr}=C{rr},"TRUE","FALSE")'], money_cols=(2, 3))
    ec.blank()
    ec.row(['Summary', f'=SUMPRODUCT(--(E5:E{EI_LAST}="TRUE"))', f'=COUNTA(A5:A{EI_LAST})', f'=IF(B{EI_TOT}=C{EI_TOT},"TRUE","FALSE")'], 'tot')

    vbs = Sheet(wb, 'Vendor_Boilerplate', {'A': 14, 'B': 18, 'C': 30, 'D': 20, 'F': 100})
    vbs.row(['Vendor boilerplate cited by the carried green blocks (rule 17 Amendment 2)'], 'title')
    vbs.row(['Carried verbatim from PS & WP v127 (sightings = the v127 figure) or captured at branch v2 (sightings = documents in the batch citing the key).'], 'sub')
    vbs.blank()
    vbs.row(list(VB[3][:6]), 'green')
    for r in vb_rows:
        vbs.row(list(r[:6]))
    VB_LAST = vbs.n

    rule17 = [
        ('Register lines with Nature Basis = Sighted invoice line', 'count', '=COUNTIF(Reg_Basis,"Sighted invoice line")', len(sighted)),
        ('Sighted lines carrying an Ev Invoice ID', 'count', '=COUNTIFS(Reg_Basis,"Sighted invoice line",Reg_EvID,"<>")', len(sighted)),
        ('Check 1 (captured lines = printed subtotal) TRUE on every sighted line', 'count', f'=SUMPRODUCT(--(Register!$DR${FIRST}:$DR${LAST}="TRUE"))', len(sighted)),
        ('Check 2 (register amount = printed subtotal, ratified variants) TRUE on every sighted line', 'count', f'=SUMPRODUCT(--(Register!$DS${FIRST}:$DS${LAST}="TRUE"))', len(sighted)),
        ('Check 3 (printed GST = 10%) TRUE on every sighted line', 'count', f'=SUMPRODUCT(--(Register!$DT${FIRST}:$DT${LAST}="TRUE"))', len(sighted)),
        ('EIL_Controls per-invoice reconciliations TRUE', 'count', f'=EIL_Controls!B{EI_TOT}', len(ev_order)),
        ('EIL_Controls summary verdict', 'text', f'=EIL_Controls!D{EI_TOT}', 'TRUE'),
        ('Evidence_Invoices header ex GST total equals the captured lines total', 'value', f'=Evidence_Invoices!J{EI_TOT}', float(sum(eil_sum.values()))),
        ('Captured evidence lines total (Evidence_Invoice_Lines column G)', 'value', '=ROUND(SUM(EIL_Amount),2)', float(sum(eil_sum.values()))),
        ('Check-variant lines tagged [check variant] in the anomalies column', 'count', f'=COUNTIF(Register!$DW${FIRST}:$DW${LAST},"*[check variant]*")',
         sum(1 for r in sighted if '[check variant]' in str(r['V'][127]))),
        ('Every Vendor_Boilerplate key is cited by a green block (and a build gate proves every cited key exists)', 'count',
         f'=SUMPRODUCT(--((COUNTIF(Register!$DN${FIRST}:$DN${LAST},Vendor_Boilerplate!$A$5:$A${VB_LAST})+COUNTIF(Register!$DO${FIRST}:$DO${LAST},Vendor_Boilerplate!$A$5:$A${VB_LAST}))>0))', len(vb_rows)),
        ('Carried evidence invoices', 'count', f'=COUNTA(EI_Invoice)', len(ev_order)),
    ]
    for text, kind, f, exp in rule17:
        controls.append(('4. Rule 17 evidence', 'Register / evidence', text, kind, f, exp))

    # ============================================================== Data_Acquisition
    da = Sheet(wb, 'Data_Acquisition', {'A': 180})
    da.row(['Data acquisition register, Parks Branch FY2026/27 (embedded)'], 'title')
    da.row(['Every upload logged with md5, tool identity and criteria verbatim. Rule 12 duplicate screen: each md5 below was screened against the PS & WP register v127 Data_Acquisition; none had been received before.'], 'sub')
    da.blank()
    lines = [f'F1 | 11-Sep-2026 | {os.path.basename(pbr_stage.LEDGER)} | md5 {stage["led_md5"]} | TechOne Ledger Accounts Transactions Table export (no extraction tool) | {len(L["data"]):,} lines, export total row $4,910,566.68 | {L["params"]}',
             f'F1 criteria (verbatim): {L["criteria"]}']
    for k_, (k, s) in enumerate(se2.items(), 2):
        lines.append(f'F{k_} | 11-Sep-2026 | {os.path.basename(s["path"])} | md5 {s["md5"]} | TechOne SE2 enquiry export, by {k} | {len(s["body"])} body rows, accumulated actual P1-3 $4,910,566.68 | criteria (verbatim): {s["criteria"]}')
    lines.append(f'F6 | 11-Sep-2026 | {os.path.basename(pbr_stage.V127)} | md5 {stage["v127_md5"]} | Inheritance source, read with python-calamine; not embedded (the PS & WP register remains its own record). 3,372 FY2026/27 lines screened, 3,365 inherited, 7 absent.')
    for k_, hh in enumerate(HISTS, 7):
        lines.append(f'F{k_} | 11-Sep-2026 | {os.path.basename(hh["path"])} | md5 {hh["md5"]} | TechOne Ledger Accounts Transactions Table export, APLEDGER creditor history {hh["code"]} ({hh["label"]}, ABN {hh["abn"]}), no extraction tool | {hh["n"]:,} lines {hh["first"].strftime("%d-%b-%Y")} to {hh["last"].strftime("%d-%b-%Y")}, export total row ${D(hh["total"][10]):,} | {hh["params"]} | label basis: {hh["label_basis"]}')
    for k_, m_ in enumerate(stage.get('attach_files', []), 7 + len(HISTS)):
        b_ = m_.get('batch', 'attach_1')
        lines.append(f'F{k_} | 11-Sep-2026 | {m_["file"]} | md5 {m_["md5"]} | TechOne attachment PDF (EzeScan Server21 export, {m_["pages"]} page(s)); parsed by parse_{b_}.py, pdftotext -layout, page text retained in corpus_{b_}_v6.json; gate GREEN; the PDF is not embedded (rule 15) | Batch {b_}')
    _fid = json.load(open(os.path.join(pbr_stage.ROOT, 'batches', 'code', 'corpus_code_v6.json')))['manifest']
    lines.append(f'F{7 + len(HISTS) + len(stage.get("attach_files", []))} | 11-Sep-2026 | corpus_code.json | md5 {_fid.get("supplied_corpus_md5")} | Supplied extraction corpus for code.pdf (66 pages, binder not supplied). Extraction tool as declared: {_fid.get("extraction_tool")}. '
                 f'Prepared by prep_code_corpus.py (page text rebuilt from the retained layout rows; findings restated as text; pk_refs restricted to PK000000 form, dropping the payment-block bank account) and gated GREEN in container. '
                 f'Rule 19.2 per-vendor verbatim check against an independent source: {_fid["fidelity_check"]["verdict"]}, {_fid["fidelity_check"]["template_rows"]} fixed template rows from {_fid["fidelity_check"]["source"]} present verbatim in all {_fid["fidelity_check"]["documents_tested"]} documents, terms page identical as an ordered sequence. '
                 f'Scope of that check: {_fid["fidelity_check"]["scope"]} | Batch code')
    lines.append(f'Rule 12 screen at v4 to v6: every md5 above was screened against the PS & WP v127 Data_Acquisition and this register\'s inputs; none had been received before. Re-pulls audited against the v127 embedded histories and not re-captured: HAR073 at v4 (5-Aug-2026 pull, F26 there) and LEV002 at v6 (2-Sep-2026 re-pull, F127 there): {stage.get("hist_audit")}.')
    lines.append('ABR public register lookups (v6, 11-Sep-2026, abr.business.gov.au ABN View): 52 010 996 175 Mimeway Pty. Ltd., trading name Mimeway Pty. Ltd. t/as Nuway Landscape Supplies (NUW001); 49 600 618 657 Greenway Solutions Pty Ltd (GRE083); 38 081 222 675 P.K. Consulting Pty Ltd, QLD 4133 (WAT088). Each is the ABN carried on the APLEDGER export for that creditor code; the lookup names the entity, it is not invoice evidence (rule 8: Tier 1 on the creditor history with ABR ABN; nature stays unconfirmed until an invoice is sighted under rule 17).')
    lines.append(f'Gaps and priority queue (branch): 1. APLEDGER creditor histories for the remaining unidentified supplier series (Open_Items B-001 onward; the queue with one invoice to sight per series is reports/Unidentified_Contractors_{VER}.md). 2. Sight one invoice per newly identified creditor series to confirm nature (rule 17). 3. 26SLACT P12 for the non-PS/WP sections, to pair the P1 EOY reversals. 4. 27SLACT P4 whole-branch pull when P4 closes, same criteria. 5. Document Line Tables for the recode sets that do not net in scope.')
    for t_ in lines:
        da.row([da.cell(t_, wrap=True)])

    # ============================================================== Config
    cf = Sheet(wb, 'Config', {'A': 30, 'B': 60})
    cf.row(['Config: toolkit positions (rule 19.6). One occurrence per key.'], 'title')
    cfg = [('WORKBOOK_VERSION', VER), ('WORKBOOK_NAME', OUTNAME), ('REGISTER_DATA', f'{FIRST}:{LAST}'), ('REGISTER_TOTAL_ROW', TOT),
           ('REGISTER_COLS', 148), ('GREEN_BLOCK_COLS', '88:127'), ('CONTROL_TOTAL', 4910566.68), ('LINES', N),
           ('INHERITED_LINES', stage['inherit_n']), ('NEW_LINES', N - stage['inherit_n']), ('THEME_MAP_RANGE', f'A5:B{TM_LAST}'),
           ('THEME_MAP_V3_RANGE', f'A5:C{T3_LAST}'), ('EI_DATA', f'5:{EI_LAST}'), ('EI_TOTALS_ROW', EI_TOT), ('EIL_DATA', f'5:{EIL_LAST}'),
           ('EIL_CONTROLS', f'5:{EI_LAST} summary {EI_TOT}'), ('SIGHTED_COUNT', len(sighted)), ('RECON_COUNT', len(ev_order)),
           ('BOILERPLATE_KEYS', len(vb_rows)), ('JOURNAL_SETS', f'5:{JS_LAST} total {JS_TOT}'), ('JOURNAL_PULL', f'{JP_A}:{JP_B} total {JP_TOT}'), ('SOURCE_LEDGER_MD5', stage['led_md5']),
           ('INHERITANCE_SOURCE_MD5', stage['v127_md5']), ('RULES_FILE', 'pbr_rules_v1.json'), ('HISTORIES_FILE', 'pbr_histories_v4.json'),
           ('CREDITOR_LINES', f'5:{CL_LAST} (v127 carried 5:{4 + len(cl_keep)}, APLEDGER v4 to v6 {5 + len(cl_keep)}:{CL_LAST})'), ('HISTORIES', len(HISTS)), ('BATCHES', ', '.join(pbr_stage.BATCHES))]
    for k, v_ in cfg:
        cf.row([k, v_])

    # ============================================================== Project_Instructions
    pi = Sheet(wb, 'Project_Instructions', {'A': 180})
    pi.row(['Project instructions (embedded copy)'], 'title')
    pi.row(['Branch adoption preface (v1): this register adopts PS & WP Project Instructions v11 below without relaxing any capture or verification standard. Declared differences: scope is Branch 4090000 FY2026/27 O110-O115 rather than two sections across four years; Theme maps extended (Method 7.0); P1S service governs added to the theme precedence (Method 6.0); columns 147-148 added (Method 4.0).'], 'sub')
    for t_ in open(os.path.join(pbr_stage.ROOT, 'docs', 'PSWP_Project_Instructions_v11__1_.md'), encoding='utf-8').read().splitlines():
        pi.row([t_ if t_.strip() else None])

    # ============================================================== Theme_Map_v3
    tv = Sheet(wb, 'Theme_Map_v3', {'A': 44, 'B': 44, 'C': 34})
    tv.row(['Theme map v3 (editable), branch v1 extension'], 'title')
    tv.row(['Register column EB holds the level-2 category; column EA looks up its level-1 group here. Rows 5-31 are the PS & WP map unchanged.'], 'sub')
    tv.blank()
    tv.row(['Theme category (level 2)', 'Theme group (level 1)', 'Lookup key type'], 'blue')
    for a_, b_, c_ in theme_v3:
        tv.row([a_, b_, c_])

    # ============================================================== lookups and error sweeps
    controls.append(('3. Summary ties', 'Register', 'Nature Categories not found on Theme_Map (must be 0)', 'count', f'=COUNTIF(Register!$Z${FIRST}:$Z${LAST},"Unmapped - add to Theme_Map")', 0))
    controls.append(('3. Summary ties', 'Register', 'v3 categories not found on Theme_Map_v3 (must be 0)', 'count', f'=COUNTIF(Register!$EA${FIRST}:$EA${LAST},"(not in Theme_Map_v3)")', 0))
    sweeps = [('Register', f'Register!$U${FIRST}:$Z${LAST}'), ('Register', f'Register!$DQ${FIRST}:$DT${LAST}'), ('Register', f'Register!$EA${FIRST}:$EA${LAST}'),
              ('Register', f'Register!$EI${FIRST}:$EJ${LAST}'), ('Register', f'Register!$EM${FIRST}:$EN${LAST}')]
    for shn, maxc in (('Section_Summary', 'V'), ('Summary', 'M'), ('Themes', 'M'), ('Themes_v3', 'M'), ('Axes', 'M'), ('Coverage', 'M'),
                      ('PK_Listing', 'G'), ('Vendor_Series', 'E'), ('Journal_Sets', 'E'), ('Journal_Pull', 'G'), ('Evidence_Invoices', 'L'), ('EIL_Controls', 'E')):
        sweeps.append((shn, f'{shn}!$A$1:${maxc}$2000'))
    for shn, rng in sweeps:
        controls.append(('6. Error sweeps', shn, f'Error cells in {rng} (must be 0)', 'count', f'=SUMPRODUCT(--ISERROR({rng}))', 0))

    # ============================================================== Controls
    ct = Sheet(wb, 'Controls', {'A': 22, 'B': 20, 'C': 90, 'D': 8, 'E': 18, 'F': 18, 'G': 10})
    ct.row(['CONTROLS. Every control the verify pass checks, gathered on one sheet'], 'title')
    ct.row(['Column E is a live reference or count over the workbook; F is the expected value fixed at build; G is the result. The master verdict is TRUE only when nothing reads FALSE and the TRUE count equals the registered count.'], 'sub')
    ct.blank()
    C0 = 8; C1 = C0 + len(controls) - 1
    ct.row(['MASTER VERDICT', f'=IF(AND(SUMPRODUCT(--(G{C0}:G{C1}="FALSE"))=0,SUMPRODUCT(--(G{C0}:G{C1}="TRUE"))={len(controls)}),"TRUE","FALSE")', 'Controls passing', f'=SUMPRODUCT(--(G{C0}:G{C1}="TRUE"))'], 'bold')
    ct.row(['Controls registered', len(controls), 'Controls failing', f'=SUMPRODUCT(--(G{C0}:G{C1}="FALSE"))'])
    ct.blank()
    ct.row(['Group', 'Sheet', 'What it proves', 'Kind', 'Live value', 'Expected', 'Result'], 'blue')
    for k, (g, shn, text, kind, f, exp) in enumerate(controls):
        rr = C0 + k
        res = f'=IF(E{rr}=F{rr},"TRUE","FALSE")' if kind == 'text' else f'=IF(ROUND(E{rr}-F{rr},2)=0,"TRUE","FALSE")'
        ct.row([g, shn, text, kind, f, exp, res], money_cols=(5, 6) if kind == 'value' else ())
    say(f'controls registered {len(controls)}')
    wb.save(os.path.join(SCRATCH, OUTNAME))
    meta = dict(FIRST=FIRST, LAST=LAST, TOT=TOT, N=N, EI_LAST=EI_LAST, EI_TOT=EI_TOT, ncontrols=len(controls), C0=C0, C1=C1,
                sighted_rows=[r['row'] for r in sighted], sections=SECTIONS, reclass=len(reclass), js_zero=js_zero, jrefs=len(jrefs),
                cite=dict(cite_changes), items=len(items), unid=sum(v[1] for v in unid_by_sec.values()), unid_n=sum(v[0] for v in unid_by_sec.values()),
                status_amt={k: float(v) for k, v in status_amt.items()}, hist=dict(files=len(HISTS), lines=len(clrow), matched=len(hist_matches), matched_amt=float(sum(m['amount'] for m in hist_matches)), inherited=sum(1 for m in hist_matches if m['inherited']), cited=hist_cited, conflicts=len(stage['hist_conflicts'])))
    del wb
    gc.collect()
    return meta


def pbr_stage_colnum(letters):
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n


def recalc(src, outdir):
    os.makedirs(outdir, exist_ok=True)
    prof = tempfile.mkdtemp(prefix='lo_profile_')
    os.makedirs(f'{prof}/user', exist_ok=True)
    xcu = f'{prof}/user/registrymodifications.xcu'
    open(xcu, 'w').write('<?xml version="1.0" encoding="UTF-8"?>\n<oor:items xmlns:oor="http://openoffice.org/2001/registry" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
                         '<item oor:path="/org.openoffice.Office.Calc/Formula/Load"><prop oor:name="OOXMLRecalcMode" oor:op="fuse"><value>0</value></prop></item>\n</oor:items>\n')
    assert 'OOXMLRecalcMode' in open(xcu).read()
    cmd = ['soffice', f'-env:UserInstallation=file://{prof}', '--headless', '--norestore', '--convert-to', 'xlsx', '--outdir', outdir, src]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    out = os.path.join(outdir, os.path.basename(src))
    shutil.rmtree(prof, ignore_errors=True)
    if not os.path.exists(out):
        raise RuntimeError(f'recalc produced no file: {p.stdout} {p.stderr}')
    return out


def verify(path, meta):
    wb = CalamineWorkbook.from_path(path)
    fails = []
    def get(s):
        return wb.get_sheet_by_name(s).to_python(skip_empty_area=False)
    ct = get('Controls')
    if ct[3][1] != 'TRUE':
        fails.append(f'master verdict {ct[3][1]!r}')
    for k in range(meta['C0'], meta['C1'] + 1):
        r = ct[k - 1]
        if r[6] != 'TRUE':
            fails.append(f'control {k}: {r[2]} got {r[4]!r} want {r[5]!r} -> {r[6]!r}')
    R = get('Register')
    tot = R[meta['TOT'] - 1][19]
    if D(tot) != D('4910566.68'):
        fails.append(f'register total {tot}')
    for rr in meta['sighted_rows']:
        row = R[rr - 1]
        for c in (121, 122, 123):
            if row[c] != 'TRUE':
                fails.append(f'sighted row {rr} col {c + 1} = {row[c]!r}')
    for rr in range(meta['FIRST'], meta['LAST'] + 1):
        if R[rr - 1][25] in ('', None) or str(R[rr - 1][25]).startswith('Unmapped'):
            fails.append(f'theme lookup row {rr}'); break
    ec = get('EIL_Controls')
    for rr in range(5, meta['EI_LAST'] + 1):
        if ec[rr - 1][4] != 'TRUE':
            fails.append(f'EIL_Controls row {rr}')
    pin = get('Section_Summary')
    ps = [r for r in pin if r and r[0] == '4090240'][0]
    if D(ps[3]) != D('1485304.02'):
        fails.append(f'pin: Park Services net {ps[3]!r} (a cached or stale file would not carry this)')
    errs = 0
    for s in wb.sheet_names:
        for r in get(s):
            for v in r:
                if isinstance(v, str) and (v.startswith(('#VALUE', '#REF', '#NAME', '#DIV', '#N/A', '#NUM', '#NULL')) or v.startswith('Err:')):
                    errs += 1
    if errs:
        fails.append(f'error values in workbook: {errs}')
    return fails, dict(master=ct[3][1], passing=ct[3][3], registered=ct[4][1], pin=ps[3], total=tot)


if __name__ == '__main__':
    if os.path.exists(SCRATCH):
        shutil.rmtree(SCRATCH)   # a partial run is discarded, never resumed
    os.makedirs(SCRATCH)
    stage = pbr_stage.main()
    say('stage complete')
    meta = build(stage)
    del stage; gc.collect()
    say('workbook written; recalculating (convert route)')
    out = recalc(os.path.join(SCRATCH, OUTNAME), os.path.join(SCRATCH, 'recalc'))
    say('recalc complete; verifying the recalculated file with calamine')
    fails, facts = verify(out, meta)
    json.dump(dict(meta=meta, facts=facts, fails=fails, log=LOG), open(os.path.join(SCRATCH, 'build_result.json'), 'w'), default=str, indent=1)
    if fails:
        say(f'VERIFY FAILED ({len(fails)}): ' + ' || '.join(fails[:15]))
        sys.exit(2)
    os.makedirs(OUTDIR, exist_ok=True)
    shutil.copy(out, os.path.join(OUTDIR, OUTNAME))
    say(f'VERIFY CLEAN: {facts}. Shipped {OUTNAME}')
