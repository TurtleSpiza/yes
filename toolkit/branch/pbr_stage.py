"""pbr_stage.py - Parks Branch Transaction Register FY2026/27, stage 1 (load, inherit, classify, gate).

Produces stage.pkl consumed by pbr_build.py. Every pre-write gate raises; nothing is written to a
workbook here. Reads via python-calamine (rule 19.8). Rules held as data in pbr_rules_v1.json (rule 18).
"""
import collections, datetime as dt, hashlib, json, os, pickle, re, sys
from decimal import Decimal, ROUND_HALF_UP
from python_calamine import CalamineWorkbook

import os as _os
ROOT = _os.environ.get('PBR_ROOT', _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', '..')))
UP = _os.environ.get('PBR_INPUTS', _os.path.join(ROOT, 'data', 'inputs_2026-09-11'))
LEDGER = f'{UP}/Ledger_Accounts_Transactions_Table_-_2026-09-11T101136_185.xlsx'
SE2 = {'Section': f'{UP}/SE2_-_2026-09-11T101056_724.xlsx', 'Natural Account': f'{UP}/SE2_-_2026-09-11T101046_254.xlsx',
       'WO Task': f'{UP}/SE2_-_2026-09-11T101103_345.xlsx', 'Service No': f'{UP}/SE2_-_2026-09-11T101109_717.xlsx'}
V127 = _os.environ.get('PBR_V127', _os.path.join(ROOT, 'registers', 'PS_WP_Transaction_Register_3FY_v127_CANDIDATE.xlsx'))
CACHE = _os.path.join(ROOT, 'cache')
HERE = os.path.dirname(os.path.abspath(__file__))
RULES = json.load(open(os.path.join(HERE, 'pbr_rules_v1.json')))
HIST = json.load(open(os.path.join(HERE, 'pbr_histories_v4.json')))  # APLEDGER creditor histories, branch v4 to v10 (content as data; 'added' names the version each was pulled for)
HIST_COLS = ['Reference', 'GST Date', 'Discount Date', 'On Hold', 'Has Note', 'Date', 'Description (Document Type)', 'Details', 'Outstanding', 'Applied',
             'Transaction Amount', 'Due Date', 'Ageing Date', 'Period', 'Ageing', 'Source', 'Units', 'Discount', 'Has Attachment', 'Payment Details', 'ABN',
             'Billing System', 'Work Order', 'Work Order Transaction Number', 'Work System']
BATCHES = ('mixed_1', 'mixed_new_26_27', 'attach_1', 'attach_2', 'code', 'mix22', 'attach_3', 'mix222', 'binder11111', 'pla073_1')
JOURNAL_BATCH = 'journal_1'  # TechOne Document Line Table pulls (rule 21, pipeline "per journal batch")
RECON_BATCH = 'recon_1'      # TechOne Document Reconstruction pulls (rule 21, the counterparty route)
NCOL = 148  # 146 PS/WP columns + 147 Src Note + 148 Register provenance

def D(x):
    return Decimal(str(x)).quantize(Decimal('0.01'), ROUND_HALF_UP)

def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

def sheet(path, name=None):
    wb = CalamineWorkbook.from_path(path)
    return wb.get_sheet_by_name(name or wb.sheet_names[0]).to_python(skip_empty_area=False)

def fy_of(d):
    if not isinstance(d, (dt.date, dt.datetime)):
        return ''
    y = d.year if d.month >= 7 else d.year - 1
    return f'FY{y}/{str(y + 1)[-2:]}'

def clean_num_text(v):
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return '' if v is None else str(v)

MONTHS = {m: i for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'], 1)}

def service_period(narr, docdate):
    """Returns (Service Period, FY (Service), typo_flag)."""
    n = narr or ''
    m = re.search(r'End of Year (\d{2})/(\d{2})', n, re.I)
    if m and int(m.group(2)) == int(m.group(1)) + 1:
        return f'FY20{m.group(1)}/{m.group(2)}', f'FY20{m.group(1)}/{m.group(2)}', False
    m = re.search(r'Charges (\d{2})/(\d{2})/(\d{2}) to (\d{2})/(\d{2})/(\d{2})', n)
    if m:
        if m.group(6) == '00':
            return 'Not stated on line (01/01/00 placeholder)', 'Unstated', False
        e = dt.date(2000 + int(m.group(6)), int(m.group(5)), int(m.group(4)))
        return e.strftime('%b-%Y'), fy_of(e), False
    m = re.search(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[ \-](20\d{2}|\d{2})\b', n, re.I)
    if m:
        yr = int(m.group(2)); yr = yr + 2000 if yr < 100 else yr
        sd = dt.date(yr, MONTHS[m.group(1).lower()], 1)
        if isinstance(docdate, dt.date) and (sd - docdate).days > 92:
            fixed = dt.date(docdate.year if sd.month >= docdate.month - 3 else docdate.year + 1, sd.month, 1)
            return f'{sd.strftime("%b-%Y")} as printed (read as {fixed.strftime("%b-%Y")})', fy_of(fixed), True
        return sd.strftime('%b-%Y'), fy_of(sd), False
    m = re.search(r'(?<![\d/])(?:20)?(\d{2})/(?:20)?(\d{2})(?![\d/])', n)
    if m and int(m.group(2)) == int(m.group(1)) + 1 and 20 <= int(m.group(1)) <= 30:
        return f'FY20{m.group(1)}/{m.group(2)}', f'FY20{m.group(1)}/{m.group(2)}', False
    return 'Per doc date', fy_of(docdate), False

def parse_refs(narr):
    n = narr or ''
    out = {}
    m = re.search(r'PAR/[\w]+/\d{4}|LCC-\d{2}-\d{4}|\bCN-?\d{4,6}\b', n); out[35] = m.group(0) if m else ''
    m = re.search(r'\bDM ?#?\s?(\d{6,9})', n); out[36] = f'DM {m.group(1)}' if m else ''
    m = re.search(r'\b(Quote|QU-|Q\.)\s*[#:]?\s*([A-Z]{0,3}[\-.]?\d{3,})', n); out[37] = m.group(0).strip() if m else ''
    m = re.search(r'\bCR ?#?\d{5,}', n); out[38] = m.group(0) if m else ''
    m = re.search(r'REGO:\s*([A-Z0-9]+)', n); out[39] = m.group(1) if m else ''
    m = re.search(r'TAG:\s*(\d+)', n); out[40] = m.group(1) if m else ''
    m = re.search(r'Electricity Charges [\d/]+ to [\d/]+-(\w+)-(.*)$', n, re.S)
    if m:
        out[41] = m.group(1)
        out[42] = re.sub(r'\s*\n\s*', ' | ', m.group(2)).strip()[:40]
    else:
        out[41] = ''; out[42] = ''
    person = ''
    for pat in [r'Immunisation Services - [^-]+-(.+?) \d', r'Approved to pay -\s*([A-Z][a-z]+ [A-Z][a-z]+)',
                r'\bper ([A-Z] [A-Z][a-z]+)', r'^([A-Z][a-z]+ [A-Z][a-z]+) (?:Adelaide|Travel)', r'Blood Test-(.+?) \d']:
        m = re.search(pat, n)
        if m:
            person = m.group(1).strip(); break
    out[43] = person
    out[44] = 'Y' if re.search(r'standing order', n, re.I) else ''
    return out


def load_ledger():
    rows = sheet(LEDGER)
    crit = rows[2][0]
    hdr_code, hdr = rows[4], rows[5]
    data, total = [], None
    for r in rows[6:]:
        if all(c in ('', None) for c in r):
            continue
        if r[0] == '' and r[2] == '' and isinstance(r[7], float):
            total = D(r[7]); continue
        data.append(r)
    return dict(params=rows[1][0], criteria=crit, hdr_code=hdr_code, hdr=hdr, data=data, total=total)


def as_date(v):
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    if isinstance(v, str) and re.match(r'\d{4}-\d{2}-\d{2}', v):
        return dt.date.fromisoformat(v[:10])
    return None


def load_histories():
    """APLEDGER creditor histories (branch v4 to v10): one TechOne export per creditor account, verbatim rows keyed by export row."""
    out = []
    for h in HIST['histories']:
        p = os.path.join(ROOT, HIST['dir'], h['file'])
        rows = sheet(p)
        hdr = [str(c) for c in rows[4]]
        assert hdr[:25] == HIST_COLS, (h['file'], hdr)
        code = re.search(r'Account = (\w+)', str(rows[1][0])).group(1)
        assert code == h['code'], (h['file'], code, h['code'])
        data, total = [], None
        for i, r in enumerate(rows[5:], 6):
            if all(c in ('', None) for c in r):
                continue
            if r[5] in ('', None) and isinstance(r[10], float):
                total = r; continue
            data.append((i, r))
        assert total is not None and sum(D(r[10]) for _, r in data) == D(total[10]), (h['code'], 'export total row does not tie')
        # dominant ABN over the rows that carry one: a blank is the absence of an ABN, not a competing value.
        # Payment, funds-transfer and generated-transaction rows carry no ABN by design and can outnumber the
        # invoice rows on a small creditor account (INT036: 2 invoice rows, 5 blanks).
        abns = collections.Counter(a for a in (str(r[20]).strip() for _, r in data) if a)
        assert abns and abns.most_common(1)[0][0] == h['abn'], (h['code'], abns.most_common(3))
        dates = [as_date(r[5]) for _, r in data]
        out.append(dict(h, path=p, md5=md5(p), params=str(rows[1][0]), hdr=hdr, data=data, total=total, n=len(data), first=min(dates), last=max(dates),
                        n_fy27=sum(1 for d_ in dates if d_ >= dt.date(2026, 7, 1)), abn_other=[a for a, _ in abns.most_common() if a != h['abn']]))
    return out


def load_se2():
    out = {}
    for k, p in SE2.items():
        rows = sheet(p)
        body, total = [], None
        for r in rows[6:]:
            if all(c in ('', None) for c in r):
                continue
            if r[0] == '' and total is None and r is rows[-1]:
                total = r; continue
            body.append(r)
        out[k] = dict(path=p, md5=md5(p), rows=rows, body=body, total=total, criteria=rows[2][0])
    return out


def ensure_v127_cache():
    """Rebuild the v127 caches when absent: calamine pickle of every sheet, and the formula text of the
    FY2026/27 register rows (U, Z, DQ:DT, EI, EJ) read from the sheet XML, since calamine returns values only."""
    import zipfile
    from lxml import etree
    if not os.path.exists(_os.path.join(CACHE, 'v127.pkl')):
        wb = CalamineWorkbook.from_path(V127)
        pickle.dump({s: wb.get_sheet_by_name(s).to_python(skip_empty_area=False) for s in wb.sheet_names}, open(_os.path.join(CACHE, 'v127.pkl'), 'wb'))
    if not os.path.exists(_os.path.join(CACHE, 'v127_fy2627_forms.json')):
        v = pickle.load(open(_os.path.join(CACHE, 'v127.pkl'), 'rb'))
        fyset = {i + 1 for i, r in enumerate(v['Register']) if i >= 4 and r[4] == 'FY2026/27'}
        z = zipfile.ZipFile(V127)
        wbx = z.read('xl/workbook.xml').decode(); rels = z.read('xl/_rels/workbook.xml.rels').decode()
        rid = dict(re.findall(r'<sheet [^>]*name="([^"]+)"[^>]*r:id="([^"]+)"', wbx))['Register']
        tgt = re.search(r'Target="([^"]+)"', re.search(r'<Relationship [^>]*Id="%s"[^>]*/>' % rid, rels).group(0)).group(1)
        ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
        forms = {}
        with z.open('xl/' + tgt.replace('/xl/', '')) as f:
            for _, el in etree.iterparse(f, tag=ns + 'row'):
                rn = int(el.get('r'))
                if rn in fyset:
                    for c in el.findall(ns + 'c'):
                        fe = c.find(ns + 'f'); col = re.match(r'[A-Z]+', c.get('r')).group()
                        if fe is not None and col in ('DQ', 'DR', 'DS', 'DT', 'EI', 'EJ', 'U', 'Z'):
                            forms[f'{rn}|{col}'] = fe.text
                el.clear()
        json.dump(forms, open(_os.path.join(CACHE, 'v127_fy2627_forms.json'), 'w'))


def main(dry=False):
    log = []
    say = lambda s: (log.append(s), print(s))
    ensure_v127_cache()
    L = load_ledger()
    se2 = load_se2()
    led_md5 = md5(LEDGER)
    H = load_histories()
    say(f'creditor histories loaded: {len(H)} files, {sum(h["n"] for h in H):,} lines')
    say(f'ledger rows {len(L["data"])} total {L["total"]}')
    # ------------------------------------------------------------------ gate 1: extract ties
    tot = sum(D(r[7]) for r in L['data'])
    assert tot == L['total'] == D(4910566.68), (tot, L['total'])
    for k, s in se2.items():
        st = D(s['total'][6])
        assert st == tot, (k, st, tot)
        assert sum(D(r[6]) for r in s['body']) == tot, k
    say('gate1 extract ties: ledger = 4 SE2 reports = $4,910,566.68')

    # ------------------------------------------------------------------ v127 FY2026/27 population
    v = pickle.load(open(_os.path.join(CACHE, 'v127.pkl'), 'rb'))
    VR = v['Register']
    # ------------------------------------------------------------------ rule 12 duplicate screen (md5 against v127 Data_Acquisition and this register's inputs)
    da127 = ' '.join(str(c) for r in v['Data_Acquisition'] for c in r if c)
    known = {led_md5} | {s_['md5'] for s_ in se2.values()}
    for h in H:
        assert h['md5'] not in da127 and h['md5'] not in known, ('rule 12: history already received', h['code'], h['md5'])
        known.add(h['md5'])
    for batch in BATCHES:
        cj = json.load(open(os.path.join(ROOT, 'batches', batch, f'corpus_{batch}_v6.json')))
        assert cj['manifest'].get('gate') == 'GREEN', (batch, cj['manifest'].get('gate'))
        for sf in cj['manifest']['source_files']:
            # a supplied corpus may name a binder that was not itself supplied; then the corpus md5 is what is screened
            h_ = sf.get('md5') or cj['manifest'].get('supplied_corpus_md5')
            assert h_, ('rule 12: no md5 to screen', batch, sf)
            assert h_ not in da127, ('rule 12: source file already received', batch, sf)
    say('gate rule 12: no history or source-file md5 previously received')
    # re-pull audit against the v127 embedded histories, HAR073 at v4 and LEV002 at v6 (rule 12: a re-sighting is audited, not re-captured)
    hist_audit = {}
    for k_, h in enumerate(H):
        old = {(str(r[2]).strip(), str(as_date(r[7])), D(r[12])) for r in v['Creditor_Lines'][4:] if str(r[0]).startswith(h['code'])}
        if old:
            new = {(str(r[0]).strip(), str(as_date(r[5])), D(r[10])) for _, r in h['data']}
            hist_audit[h['code']] = dict(v127_rows=len(old), new_rows=len(new), in_both=len(old & new), v127_only=len(old - new), new_only=len(new - old))
    say(f'history re-pull audit against v127 Creditor_Lines: {hist_audit}')
    v_hdr = VR[3]
    forms = json.load(open(_os.path.join(CACHE, 'v127_fy2627_forms.json')))
    vfy = [(i + 1, r) for i, r in enumerate(VR) if i >= 4 and i < 31364 and r[4] == 'FY2026/27']
    say(f'v127 FY2026/27 rows {len(vfy)}')
    nl = lambda s: re.sub(r'\s*\n\s*', ' | ', str(s)).strip()
    vkey = lambda r: (r[67], r[54], r[75], r[65], D(r[60]), nl(r[59]))
    lkey = lambda x: (x[14], x[1], x[22], x[12], D(x[7]), nl(x[6]))
    pool = collections.defaultdict(list)
    for n, r in vfy:
        pool[vkey(r)].append((n, r))
    inherit = {}  # ledger index -> (v127 row, r)
    for i, x in enumerate(L['data']):
        k = lkey(x)
        if pool.get(k):
            inherit[i] = pool[k].pop(0)
    unmatched_v = [nr for lst in pool.values() for nr in lst]
    say(f'inherited {len(inherit)}; v127 rows absent from the 11-Sep pull {len(unmatched_v)}')
    assert len(inherit) + len(unmatched_v) == len(vfy) and len(unmatched_v) < 20

    # ------------------------------------------------------------------ names
    sec_names = RULES['section_names']
    svc_names = {}
    for r in se2['Service No']['body']:
        if r[0]:
            c, nm = r[0].split(' - ', 1); svc_names[c] = nm
    na_names = {}
    for r in se2['Natural Account']['body']:
        if r[0]:
            c, nm = r[0].split(' - ', 1); na_names[c] = nm
    for x in L['data']:
        assert x[23] in svc_names, x[23]
        assert x[27] in sec_names, x[27]

    # ------------------------------------------------------------------ creditor lines (v127 embedded histories)
    CL = v['Creditor_Lines']
    cl_by_ref = collections.defaultdict(list)
    for i, r in enumerate(CL[4:], 5):
        if str(r[2]).strip():
            cl_by_ref[str(r[2]).strip()].append((i, r))
    # branch v4 to v10 APLEDGER histories: reference -> (history index, export row, row)
    hist_by_ref = collections.defaultdict(list)
    for k_, h in enumerate(H):
        for i, r in h['data']:
            hist_by_ref[clean_num_text(r[0]).strip()].append((k_, i, r))
    # One label per creditor code (rule: a COUNTIF-keyed label must be canonical). Where a branch APLEDGER
    # history is held, its researched label (with a label_basis on the entry) is authoritative for that code
    # and supersedes the legacy "CODE (label)" rendering carried on the v127 Creditor_Lines.
    hist_label = {h['code']: h['label'] for h in H}
    du_sum = collections.defaultdict(Decimal)
    for y in L['data']:
        du_sum[y[14]] += D(y[7])
    hist_matches, hist_conflicts, hist_ambiguous = [], [], []

    def hist_match(ref, du, ddate):
        cands = hist_by_ref.get(ref, [])
        if not cands:
            return None
        want = (du_sum[du] * Decimal('1.1')).quantize(Decimal('0.01'), ROUND_HALF_UP)
        ok = []
        for k_, i, r in cands:
            hd = as_date(r[5])
            if abs(D(r[10]) - want) <= Decimal('0.02') and hd and isinstance(ddate, dt.date) and abs((hd - ddate).days) <= 120:
                ok.append((k_, i, r))
        codes = {H[k_]['code'] for k_, _, _ in ok}
        if len(codes) > 1:
            hist_ambiguous.append((ref, sorted(codes)))
        return ok[0] if len(codes) == 1 else None

    def apply_hist(V, hm, ref, dsum):
        k_, i, c = hm; hh = H[k_]
        V[11] = hh['code']; V[12] = hh['label']
        abn_raw = clean_num_text(c[20]).strip()
        abn = f'{abn_raw[:2]} {abn_raw[2:5]} {abn_raw[5:8]} {abn_raw[8:]}' if len(abn_raw) == 11 else None
        V[13] = abn
        V[45] = c[10]; V[46] = c[1] or None; V[47] = c[11] or None; V[48] = c[8]; V[49] = c[9]
        V[50] = c[14] or None; V[51] = c[3] or None; V[52] = (str(c[19]) if c[19] not in (None, '') else '').strip() or None; V[53] = (str(c[21]) if c[21] not in (None, '') else '').strip() or None
        V[23] = c[7] or None
        hd = as_date(c[5])
        ev = (f'Creditor history line (APLEDGER {hh["code"]} history pulled {hh.get("pulled", "11-Sep-2026")}, Creditor_Lines row {{CL:{k_}:{i}}}): {hh["code"]} ({hh["label"]}), reference {ref}, '
              f'${D(c[10]):,} incl GST dated {hd.strftime("%d-%b-%Y") if hd else "(no date)"} against document net ${dsum:,} ex GST (x1.1 within 2c)'
              + (f', ABN {abn}' if abn else ', no ABN on the history line'))
        return abn, ev

    # ------------------------------------------------------------------ build rows
    theme_v2 = [(r[0], r[1]) for r in v['Theme_Map'][4:31] if r[0]] + [tuple(x) for x in RULES['theme_map_v2_extension']]
    theme_v3 = [(r[0], r[1], r[2]) for r in v['Theme_Map_v3'][4:31] if r[0]] + [tuple(x) for x in RULES['theme_map_v3_extension']]
    cat2 = {a for a, _ in theme_v2}; cat3 = {a for a, _, _ in theme_v3}
    assert len(cat2) == len(theme_v2) and len({a.casefold() for a in cat2}) == len(cat2)
    t9cats = {a for a, b in theme_v2 if b.startswith('T9')}

    rows = []  # list of dict: v (list NCOL+1, 1-indexed), meta
    jdocs = set(RULES['journal_doc_types'])
    contract_nas = set(RULES['contract_nas'])
    ncls = [(c, re.compile(p, re.I)) for c, p in RULES['narration_classes']]
    stop = set(RULES['generic_stopwords'])
    acc_re = re.compile(RULES['accrual_regex'], re.I)
    rec_re = re.compile(RULES['recode_regex'], re.I)

    def svc_class(svc, sec):
        nm = svc_names.get(svc, '')
        if re.search('mowing', nm, re.I): return 'Contract mowing'
        if re.search('landscap|horticult', nm, re.I): return 'Contract landscape maintenance'
        if re.search('rubbish', nm, re.I): return 'Illegal dumping & rubbish removal'
        if re.search(r'\btree', nm, re.I) or sec == '4090250': return 'Tree operations'
        if sec == '4090220': return 'Natural areas & bushland works'
        if sec == '4090270' or re.search('cemeter', nm, re.I): return 'Cemetery operations'
        if re.search('playground', nm, re.I): return 'Playground inspection & repair'
        if re.search('cleaning', nm, re.I): return 'Cleaning & sanitary'
        if re.search('water parks', nm, re.I): return 'Water park contract works'
        return 'Parks maintenance (contract/reactive)'

    def narr_class(n):
        for c, rx in ncls:
            if rx.search(n or ''):
                return c
        return None

    def content_words(n):
        w = re.findall(r'[A-Za-z]{3,}', n or '')
        return [x for x in w if x.lower() not in stop]

    # journal nets by reference over the whole branch population (Decimal)
    jnet = collections.defaultdict(Decimal); jcount = collections.Counter()
    for i, x in enumerate(L['data']):
        if x[9] in ('GL', 'GJ', 'BI') or x[5] in jdocs:
            jnet[x[3]] += D(x[7]); jcount[x[3]] += 1

    used_keys = set(r[0] for _, r in inherit.values())
    assert len(used_keys) == len(inherit), 'inherited LineKeys not unique'
    seq_next = collections.Counter()
    for k in used_keys:
        b, s = k.rsplit('-', 1)
        seq_next[b] = max(seq_next[b], int(s))

    flags = collections.Counter(); oi_data = collections.defaultdict(list)
    typo_rows = []
    cred_new_matches = []
    for i, x in enumerate(L['data']):
        V = [None] * (NCOL + 1)
        narr = x[6]; na = x[22]; svc = x[23]; sec = x[27]; src = x[9]; dtype = x[5]
        ddate = x[4]; amt = D(x[7]); wo = x[12].strip(); task = x[30].strip()
        # grey block, verbatim, mapped by position of the 35-column 27SLACT layout
        for j in range(33):
            V[54 + j] = x[j]
        V[87] = '27SLACT'
        V[128] = x[34]  # __md5Row (blank in this export)
        V[147] = x[33]  # Note (LNTNoteNumber)
        if i in inherit:
            vrow, r = inherit[i]
            for c in list(range(1, 54)) + list(range(88, 128)) + list(range(129, 147)):
                V[c] = r[c - 1] if r[c - 1] != '' else None
            V[148] = 'Inherited from PS_WP register v127'
            for tc in (29,):
                tv = V[tc]
                if isinstance(tv, str) and re.fullmatch(r'(Tier )?[123]', tv.strip()):
                    V[tc] = int(tv.strip()[-1]); flags['tier_type_canonicalised'] += 1
                elif isinstance(tv, float):
                    V[tc] = int(tv)
            meta = dict(inherited=True, vrow=vrow)
            # source-derived analysis columns must agree with the new export
            chk = {4: ddate, 8: clean_num_text(x[3]), 14: na, 17: (wo or task), 19: svc, 20: float(x[7])}
            for c, want in chk.items():
                got = r[c - 1]
                if c == 20:
                    assert D(got) == D(want), (vrow, c)
                elif c == 4:
                    pass
                elif str(got).strip() != str(want).strip():
                    flags[f'inherited_field_diff_col{c}'] += 1
            V[30] = x[8]
            rows.append(dict(V=V, meta=meta, lidx=i)); continue

        meta = dict(inherited=False)
        pk = wo or task
        base = f'{x[14][:8]}-{na}-{pk}'
        seq_next[base] += 1
        V[1] = f'{base}-{seq_next[base]:02d}'
        V[2] = sec; V[3] = sec_names[sec]; V[4] = ddate; V[5] = 'FY2026/27'
        sp, fys, typo = service_period(narr, ddate)
        V[6] = sp; V[7] = fys
        if typo:
            typo_rows.append(V[1])
        V[8] = clean_num_text(x[3]); V[9] = dtype; V[10] = src
        V[14] = na; V[15] = x[0]
        V[16] = task if task else '(no WO Task)'
        V[17] = pk if pk else '(no Work Order)'
        V[18] = ('Unallocated (no Work Order)' if not wo else
                 'Header charged direct' if wo == task else
                 'Work Order charged, no WO Task header' if not task else 'Sub-PK charged')
        V[19] = svc; V[20] = float(amt); V[22] = narr
        V[30] = x[8]
        V.__setitem__(slice(35, 45), [None] * 10)
        for c, val in parse_refs(narr).items():
            V[c] = val or None
        is_journal = src in ('GL', 'GJ', 'BI') or dtype in jdocs
        V[137] = clean_num_text(x[3]) if is_journal else None
        V[138] = int(x[2]) if isinstance(x[2], float) else x[2]
        V[142] = f'SET-{clean_num_text(x[3])}' if is_journal else None
        V[148] = 'New at branch v1 (not in the PS_WP register)'

        internal_na = na.startswith('7B') or na.startswith('7C')
        charge = ('Statutory levy / insurance' if na in RULES['statutory_nas'] else
                  'Internal Council charge' if (internal_na or src in ('IN', 'BS', 'BI', 'P1')) else 'External supplier')
        nc = narr_class(narr)
        is_contract = na in contract_nas
        acct_cat = RULES['na_category'].get(na)
        assert is_contract or acct_cat, f'NA {na} has no category rule'
        review, note, follow = [], [], []
        net_zero = jnet.get(x[3], Decimal(1)) == 0 if is_journal else False
        docfile = clean_num_text(x[15])

        # ---- nature category and theme rule
        if is_contract:
            scls = svc_class(svc, sec)
            if nc:
                cat, trule = nc, 'P4 narration, single class'
                if nc in RULES['hard_conflict_classes'] and scls in RULES['hard_conflict_classes'] and nc != scls \
                        and not (nc == 'Contract mowing' and scls == 'Contract landscape maintenance') \
                        and not (nc == 'Contract landscape maintenance' and scls == 'Contract mowing'):
                    review.append('narration class conflicts with service')
                    note.append(f'Narration reads as {nc} but service {svc} ({svc_names[svc]}) is {scls}; confirm the service and PK charged.')
            else:
                cat = scls
                trule = 'P1S service governs (branch v1)' if scls in RULES['single_class_services'] else 'P6 declared evidence state'
        else:
            cat, trule = acct_cat, 'P1 account governs'
        v3 = RULES['na_v3_override'].get(na) if not is_contract else None
        v3 = v3 or RULES['v2_to_v3'].get(cat)
        if cat == 'Parks maintenance (contract/reactive)' and trule != 'P6 declared evidence state' and not is_contract:
            v3 = 'No invoice sighted'; trule = 'P6 declared evidence state'
        line_kind, lk_rule = 'Operational', ('K3 journal, operational narration' if is_journal else 'K4 AP or other source document')
        if na == '73412':
            line_kind = 'Recovery / claim'
        site_basis = None

        # ---- source-type engine
        cont = abn = cred = None; tier = None; basis = None; status = None; verdict = None; evidence = None
        route = None
        if is_journal and (acc_re.search(narr or '') or str(x[3]).startswith('RJ') or dtype == 'Reversing Journal'):
            cat = 'EOFY accrual reversal'; line_kind = 'Accrual reversal'; lk_rule = 'K1 tagged Nature Category'
            cont = 'Journal (no supplier)'; tier = 2; basis = 'Journal narration / pairing'
            evidence = f'Journal narration and pairing by reference {V[8]} across the branch O110-O115 population'
            if net_zero:
                verdict, status = 'Journal (net-zero)', 'Confirmed'
                note.append(f'Reference {V[8]} nets to $0.00 across {jcount[x[3]]} branch lines (accrual and reversal both loaded).')
            else:
                verdict, status = 'Journal (reversal)', 'Partial'
                if re.search(r'End of Year', narr or '', re.I):
                    follow.append('Cross-FY: pair against the FY2025/26 EOY AP accrual (26SLACT P12) before reading net (rule 5).')
                    oi_data['eoy_reversal'].append((sec, amt))
                else:
                    follow.append('Reversing leg not in the loaded periods P1-P3; re-read at the next period load (rule 6).')
                    oi_data['open_accrual'].append((sec, amt))
            v3 = (RULES['na_v3_override'].get(na) or RULES['v2_to_v3'].get(acct_cat)) if (acct_cat and not is_contract) else 'Untagged accrual or reversal'
            trule = 'P1 account governs' if (acct_cat and not is_contract) else 'P6 declared evidence state'
            route = 'R8 Journal' if charge == 'External supplier' else 'R6 Internal Council charge'
            site_basis = 'Accounting event (no site by construction)'
        elif is_journal and rec_re.search(narr or ''):
            cat = 'Recode journal'; line_kind = 'Recode / transfer journal'; lk_rule = 'K1 tagged Nature Category'
            cont = 'Journal (no supplier)'; tier = 2; basis = 'Journal narration / pairing'
            evidence = f'Journal narration and pairing by reference {V[8]} across the branch O110-O115 population'
            if net_zero:
                verdict, status = 'Journal (net-zero)', 'Confirmed'
                note.append(f'Reference {V[8]} nets to $0.00 across {jcount[x[3]]} branch lines.')
            else:
                verdict, status = 'Review', 'Partial'
                follow.append(f'Journal set {V[8]} does not net to zero inside branch O110-O115; the balancing leg sits outside this scope. Pull the Document Line Table for Document File {docfile} (rule 21).')
                oi_data['recode_open'].append((sec, amt, V[8]))
            v3 = (RULES['na_v3_override'].get(na) or RULES['v2_to_v3'].get(acct_cat)) if (acct_cat and not is_contract) else 'Untagged transfer or recode journal'
            trule = 'P1 account governs' if (acct_cat and not is_contract) else 'P6 declared evidence state'
            route = 'R8 Journal' if charge == 'External supplier' else 'R6 Internal Council charge'
            site_basis = 'Accounting event (no site by construction)'
            if re.search('incorrect na', narr or '', re.I):
                note.append('Narration states the natural account was incorrect; this is the correcting leg.')
        elif is_journal:
            cont = 'Journal (no supplier)'; tier = 2
            if len(content_words(narr)) == 0:
                basis, status, verdict = 'Journal narration / pairing', 'Partial', 'Confirm'
                follow.append(f'Blank or non-descriptive journal narration; pull the Document Line Table for Document File {docfile}.')
            else:
                basis, status, verdict = 'Line narration', 'Confirmed', 'Correct'
            evidence = 'Journal narration'
            route = 'R6 Internal Council charge' if charge != 'External supplier' else 'R8 Journal'
            site_basis = 'Internal charge (not site-specific)' if charge != 'External supplier' else 'No site determinable'
            if src == 'BI' and 'SLA Hire' in (narr or ''):
                cat = 'Internal plant & fleet'
        elif src == 'IN':
            cont = 'LCC Stores (inventory issue)'; tier = 1; basis = 'System record'; status = 'Confirmed'; verdict = 'Correct'
            cat_keep = cat; cat = 'Internal stores issue'; trule = 'P5 stores narration'
            v3 = 'Materials & minor equipment'; evidence = 'Inventory issue system record (despatch stock requisition)'
            route = 'R7 Stores issue'; site_basis = 'Internal charge (not site-specific)'
        elif src == 'BS':
            cont = 'LCC internal billing (Plant & Fleet / Workshop)'; tier = 1; basis = 'System record'
            status, verdict = 'Confirmed', 'Correct'
            cat = 'Internal workshop billing' if re.search('workshop', narr or '', re.I) else 'Internal plant & fleet'
            v3 = 'Plant, fleet & internal services'; evidence = 'Plant & Fleet internal invoice system record'
            route = 'R6 Internal Council charge'; site_basis = 'Internal charge (not site-specific)'
        elif src == 'P1':
            cont = 'LCC Payroll (internal)'; tier = 1; basis = 'System record'; status, verdict = 'Confirmed', 'Correct'
            evidence = 'Payroll posting system record'; route = 'R6 Internal Council charge'; site_basis = 'Internal charge (not site-specific)'
        elif src == 'TE':
            merchant = (narr or '').split('-')[0].strip() or 'Unnamed merchant'
            cont = f'{merchant} (purchase card)'; tier = 2; basis = 'Line narration'; status, verdict = 'Confirmed', 'Correct'
            evidence = 'Purchase card reconciliation narration'; route = 'R5 Purchase card'; site_basis = 'No site determinable'
        elif src == 'AP' and dtype == 'DIR Cred Invoice' and na == '73312' and (narr or '').startswith('Electricity Charges'):
            cont = 'Origin Energy (collective/direct, confirm)'; tier = 2; basis = 'Line narration'
            status, verdict = 'Confirmed', 'Correct'; evidence = 'Direct-debit electricity narration (utility rests on the system record)'
            route = 'R4 Ad hoc purchase order'; site_basis = 'Supply-point address only (address route pending)'
        elif src == 'AP' and dtype == 'DIR Cred Invoice' and na == '73535' and 'TAG:' in (narr or ''):
            cont = 'Toll operator (Linkt/Transurban, confirm)'; tier = 2; basis = 'Line narration'
            status, verdict = 'Confirmed', 'Correct'; evidence = 'Toll tag narration (system record)'
            route = 'R4 Ad hoc purchase order'; site_basis = 'No site determinable'
        else:  # AP supplier documents
            ref = clean_num_text(x[3]).strip()
            docsum = None
            cands = cl_by_ref.get(ref, [])
            if cands:
                docsum = sum(D(y[7]) for y in L['data'] if y[14] == x[14])
                ok = [(ci, c) for ci, c in cands if abs(D(c[12]) - (docsum * Decimal('1.1')).quantize(Decimal('0.01'), ROUND_HALF_UP)) <= Decimal('0.02')]
                if len({c[0] for _, c in ok}) == 1:
                    cred = ok[0]
            m_named = re.search(r"([A-Z][\w&'\.]*(?: [A-Z&][\w&'\.]*){0,4} (?:Pty Ltd|Pty Limited|Limited|Ltd))", narr or '')
            hm = None if cred else hist_match(ref, x[14], ddate)
            if cred:
                ci, c = cred
                code, label = (c[0].split(' (', 1) + [''])[:2]
                cont = hist_label.get(code) or label.rstrip(')') or code
                V[11] = code
                abn_raw = clean_num_text(c[22]).strip()
                abn = f'{abn_raw[:2]} {abn_raw[2:5]} {abn_raw[5:8]} {abn_raw[8:]}' if len(abn_raw) == 11 else None
                tier = 1 if abn else 2; basis = 'Matched creditor history'
                V[45] = c[12]; V[46] = c[3] or None; V[47] = c[13] or None; V[48] = c[10]; V[49] = c[11]
                V[50] = c[16] or None; V[51] = c[5] or None; V[52] = (c[21] or '').strip() or None; V[53] = (c[23] or '').strip() or None
                V[23] = c[9] or None
                evidence = (f'Creditor history line (PS_WP v127 Creditor_Lines row {ci}, carried as Creditor_Lines here): {c[0]}, reference {ref}, '
                            f'${D(c[12]):,} incl GST against document net ${docsum:,} ex GST (x1.1 within 2c)' + (f', ABN {abn}' if abn else ', no ABN on the history line'))
                cred_new_matches.append((V[1], ci))
            elif hm:
                docsum = du_sum[x[14]]
                abn, evidence = apply_hist(V, hm, ref, docsum)
                cont = V[12]; tier = 1 if abn else 2; basis = 'Matched creditor history'
                hist_matches.append(dict(lk=V[1], k=hm[0], i=hm[1], code=H[hm[0]]['code'], inherited=False, prior=None, amount=amt, sec=sec))
            elif dtype == 'Creditors invoices' and re.match(r"^[A-Z][A-Za-z'\. &]+-", narr or ''):
                cont = f'{(narr or "").split("-")[0].strip()} (narration-named payee)'; tier = 2; basis = 'Line narration'
                evidence = 'Payee named in the AP narration; invoice not sighted'
            elif m_named:
                cont = f'{m_named.group(1)} (narration-named)'; tier = 2; basis = 'Line narration'
                evidence = 'Supplier named in the AP narration; invoice not sighted'
            else:
                cont = RULES['unidentified_label']; tier = 3
                evidence = 'No invoice sighted and no creditor history held'
            if basis is None:
                basis = 'Line narration' if (nc or (not is_contract and len(content_words(narr)) >= 2)) else 'Vendor inference (unconfirmed)'
            elif basis == 'Line narration' and is_contract and not nc:
                basis = 'Vendor inference (unconfirmed)'
            status = 'Pending evidence' if tier == 3 else 'Partial'
            verdict = 'Confirm'
            evidence += f'. TechOne attachment: {x[8].strip() or "(blank)"}; Document File {docfile}.'
            if tier == 3:
                follow.append((f'Identify supplier and nature: sight the TechOne attachment on Document File {docfile}' if x[8].strip() == 'Y'
                               else f'No TechOne attachment; request the invoice for reference {ref} from AP') + ', or request the APLEDGER creditor history (rule 12).')
                oi_data['unidentified'].append((sec, amt))
            else:
                follow.append(f'Sight the invoice (Document File {docfile}) to confirm nature under rule 17.')
            if re.search(r'standing order', narr or '', re.I): route = 'R2 Standing order'
            elif re.search(r'PAR/|CON ORDER|contract', narr or '', re.I): route = 'R1 Contract, schedule of rates'
            elif re.search(r'\bquote|\bQU-|proposal', narr or '', re.I): route = 'R3 Quoted works'
            else: route = 'R4 Ad hoc purchase order'
            site_basis = 'No invoice sighted (awaiting capture)'
            if internal_na:
                review.append('external supplier document on an internal account')
                note.append(f'AP supplier document posted to internal account {na}; internal accounts carry Council charges only.')
        if site_basis is None:
            site_basis = 'No site determinable'
        # generic flags
        if src == 'AP' and na != '73312' and re.search(r'^Electricity Charges', narr or ''):
            review.append('electricity narration off 73312'); note.append('Electricity narration posted off 73312 Electricity.')
        if src == 'AP' and na != '73535' and 'TAG:' in (narr or ''):
            review.append('toll narration off 73535'); note.append('Toll tag narration posted off 73535 Tollway Charges.')
        if not wo:
            follow.append('No Work Order on the line: PK Charged falls back to the WO Task header and the line is Unallocated (rule 1).')
        if sec == 'NA':
            follow.append(f'Service {svc} carries no section in TechOne (Section = NA) and no WO Task; confirm the service-to-section mapping.')
            oi_data['na_section'].append((svc, amt, pk))
        if review and verdict not in ('Journal (net-zero)',):
            verdict = 'Review'
            oi_data['review'].append((sec, amt, '; '.join(review)))
        if typo:
            note.append(f'Narration prints {sp.split(" as printed")[0]}, more than three months after the posting date; read as a printed-year error for FY (Service).')
        assert cat in cat2, cat
        assert v3 in cat3, (v3, cat)
        V[11] = V[11] or None; V[12] = cont; V[13] = abn; V[24] = cat
        svc_bit = f'service {svc} {svc_names[svc]}'
        nd = (narr or '').strip().replace('\n', ' | ') or '(blank narration)'
        if basis == 'Vendor inference (unconfirmed)':
            V[25] = f'{cat} (per {svc_bit}; narration generic): {nd}'
        else:
            V[25] = f'{cat}, {svc_bit}: {nd}'
        V[27] = basis; V[28] = evidence; V[29] = tier; V[31] = verdict
        V[32] = ' '.join(note) or None; V[33] = status; V[34] = ' '.join(follow) or None
        V[129] = None; V[130] = site_basis; V[132] = v3; V[133] = trule; V[134] = line_kind; V[135] = lk_rule
        V[136] = charge; V[146] = route
        meta['charge'] = charge
        rows.append(dict(V=V, meta=meta, lidx=i))

    # ------------------------------------------------------------------ inherited AP lines identified from the branch v4 to v10 histories (rule 8 Tier 1; port to PS_WP)
    weak = re.compile(r'Unidentified|series-inferred|confirm\)|\(named in', re.I)
    for r in rows:
        if not r['meta']['inherited']:
            continue
        V = r['V']; x = L['data'][r['lidx']]
        if V[10] != 'AP' or V[88] or V[27] == 'Sighted invoice line':
            continue
        prior = str(V[12] or ''); prior_abn = V[13]
        if not (V[29] == 3 or weak.search(prior) or V[27] == 'Vendor inference (unconfirmed)'):
            continue
        ref = clean_num_text(x[3]).strip()
        hm = hist_match(ref, x[14], x[4])
        if not hm:
            continue
        old_ev = str(V[28] or '')
        abn, ev = apply_hist(V, hm, ref, du_sum[x[14]])
        docfile = clean_num_text(x[15])
        V[27] = 'Matched creditor history'; V[29] = 1 if abn else 2
        V[28] = (ev + f'. TechOne attachment: {str(x[8]).strip() or "(blank)"}; Document File {docfile}. Identified at branch {H[hm[0]].get("added", "v4")} (port to PS_WP v128); '
                 f'the PS_WP v127 evidence read: {old_ev[:240]}')
        if V[33] == 'Pending evidence':
            V[33] = 'Partial'
        V[34] = f'Sight the invoice (Document File {docfile}) to confirm nature under rule 17. Port this identification to PS_WP v128.'
        r['meta']['ident_v4'] = H[hm[0]]['code']; r['meta']['ident_ver'] = H[hm[0]].get('added', 'v4')
        # a conflict is a DIFFERENT vendor, not the same one under a fuller or shorter name: test the ABN first,
        # then containment of the canonical name (v127 carries trading-name suffixes the APLEDGER label does not).
        nm = lambda x: re.sub(r'[^a-z0-9]', '', str(x).lower())
        same_abn = bool(abn) and re.sub(r'\D', '', str(prior_abn or '')) == re.sub(r'\D', '', str(abn))
        same_name = nm(H[hm[0]]['label']) in nm(prior) or nm(prior.split(' (')[0]) in nm(H[hm[0]]['label'])
        if not re.search(r'Unidentified|series-inferred|confirm\)', prior, re.I) and not (same_abn or same_name):
            hist_conflicts.append((V[1], prior, H[hm[0]]['code'], D(V[20])))
        hist_matches.append(dict(lk=V[1], k=hm[0], i=hm[1], code=H[hm[0]]['code'], inherited=True, prior=prior, amount=D(V[20]), sec=str(V[2])))
    say(f'APLEDGER history identifications: {len(hist_matches)} lines ({sum(1 for m in hist_matches if m["inherited"])} inherited), '
        f'{sum(m["amount"] for m in hist_matches):,} ex GST; label conflicts {len(hist_conflicts)}; ambiguous references {len(hist_ambiguous)}')

    # ------------------------------------------------------------------ supplier named in a Council journal (Tier 2, corroborated)
    digits = lambda ref: re.sub(r'\D', '', str(ref)).lstrip('0')
    ap_by_inv = collections.defaultdict(list)
    for r in rows:
        if r['V'][10] == 'AP' and not r['meta']['inherited']:
            dg = digits(r['V'][8])
            if len(dg) >= 3:
                ap_by_inv[dg].append(r)
    rev = collections.defaultdict(lambda: [Decimal(0), set()])
    fuel = collections.defaultdict(set)
    for r in rows:
        if not r['V'][137]:
            continue
        n = str(r['V'][22] or '')
        m = re.match(r"^([A-Z][A-Za-z&']+) INV-?\s?(\d{3,})\b.*?reversal", n)
        if m:
            rev[(m.group(1), m.group(2).lstrip('0'))][0] += D(r['V'][20]); rev[(m.group(1), m.group(2).lstrip('0'))][1].add(str(r['V'][8]))
        m = re.search(r"Fuel levy (PK\d+) to PK\d+-([A-Z][A-Za-z&' ]+?) INV-?(\d{3,})\s*$", n)
        if m:
            fuel[(m.group(2).strip(), m.group(3).lstrip('0'), m.group(1))].add(str(r['V'][8]))
    jnamed = collections.Counter()
    def name_it(r, name, how, refs):
        V = r['V']
        if V[12] != RULES['unidentified_label']:
            return
        V[12] = f'{name} (named in recode journal, confirm)'; V[29] = 2; V[33] = 'Partial'
        df = clean_num_text(V[69])
        V[28] = (f'Supplier named in Council journal {", ".join(sorted(refs))}: {how}. Invoice not sighted. '
                 f'TechOne attachment: {str(V[62]).strip() or "(blank)"}; Document File {df}.')
        V[34] = f'Sight the invoice (Document File {df}) to confirm supplier and nature under rule 17.'
        jnamed[name] += 1
    for (name, inv), (tot, refs) in rev.items():
        aps = ap_by_inv.get(inv, [])
        if aps and abs(tot + sum(D(a['V'][20]) for a in aps)) <= Decimal('0.02'):
            for a in aps:
                name_it(a, name, f'reversal legs naming invoice {inv} total {tot} against the AP document total (equal and opposite within 2c)', refs)
    for (name, inv, pk_from), refs in fuel.items():
        for a in ap_by_inv.get(inv, []):
            if a['V'][17] == pk_from:
                name_it(a, name, f'fuel levy recode names invoice {inv} and moves it from {pk_from}, the PK this AP line charges', refs)
    say(f'suppliers named in journals (new AP lines identified at Tier 2): {dict(jnamed)}')
    stage_jnamed = dict(jnamed)

    # ------------------------------------------------------------------ batch capture (rules 16/17, brief-driven)
    import pbr_capture
    _keys = frozenset(str(r[0]) for r in v['Vendor_Boilerplate'][4:] if str(r[0]).startswith('BP:'))
    _text = {str(r[0]): r[5] for r in v['Vendor_Boilerplate'][4:] if str(r[0]).startswith('BP:')}
    ev_new, cap_variants = None, None
    for batch in BATCHES:
        ev_new, cap_variants = pbr_capture.capture(rows, os.path.join(ROOT, 'batches', batch, f'corpus_{batch}_v6.json'), os.path.join(ROOT, 'batches', batch, f'match_{batch}_v6.json'), say, _keys, _text, ev_new, cap_variants)

    # ------------------------------------------------------------------ journal source documents (rule 21, batch journal_1)
    # The batch driver has already proved each document nets to zero, that every in-scope leg ties its own register
    # line, and that a re-pull of a document already embedded in PS_WP v127 is identical leg by leg (rule 12). Those
    # facts are re-asserted here, because the stage is where a gate belongs, and then the authored restatement is
    # applied to the register lines the document evidences.
    jb = json.load(open(os.path.join(ROOT, 'batches', JOURNAL_BATCH, f'{JOURNAL_BATCH}_v6.json')))
    jm = jb['manifest']
    assert jm['gate'] == 'GREEN', jm['gate']
    assert jm['all_documents_net_zero'] and jm['all_ties_true'], jm
    jkey = {r['V'][1]: r for r in rows}
    jsrc_docs, jupd, jcited = [], 0, set()
    for d in jb['documents']:
        assert d['nets_to_zero'] and d['all_ties_true'], d['document_file']
        if d['capture'] != 'embed verbatim':
            assert d['v127_audit'] and d['v127_audit']['identical'], d['document_file']
            continue
        upd = d.get('register_updates') or {}
        cols = {int(k): val for k, val in (upd.get('cols') or {}).items()}
        per = {lk: {int(c): val for c, val in m.items()} for lk, m in (upd.get('per_linekey') or {}).items()}
        for leg in d['legs']:
            if leg['in_branch_scope'] != 'Yes':
                continue
            r = jkey[leg['register_linekey']]
            for c, val in {**cols, **per.get(leg['register_linekey'], {})}.items():
                r['V'][c] = val
            r['meta']['journal_src'] = d['document_file']
            jcited.add(leg['register_linekey'])
            jupd += 1
        jsrc_docs.append(d)
    say(f'journal sources: {len(jsrc_docs)} document(s) embedded verbatim, '
        f'{jm["documents_audited_only"]} audited only (rule 12), {jupd} register line(s) restated from a pulled document')

    # ------------------------------------------------------------------ reconstruction batch (rule 21, Document Reconstruction route)
    # Same standard as the journal batch: the gate, the net-zero proof and the per-reference tie are re-asserted here,
    # because the stage is where a gate belongs. A reconstruction reaches the Council-side counterparty legs a Document
    # Line Table taken inside the branch never shows, and maps to a register line on the register's own Src Account.
    rb = json.load(open(os.path.join(ROOT, 'batches', RECON_BATCH, f'{RECON_BATCH}_v9.json')))
    rm = rb['manifest']
    assert rm['gate'] == 'GREEN', rm['gate']
    assert rm['all_documents_net_zero'] and rm['all_ties_true'], rm
    rsrc_docs, rcited = [], set()
    for d in rb['documents']:
        assert d['nets_to_zero'] and d['all_ties_true'], d['cross_reference']
        if d['capture'] != 'embed verbatim':
            assert d.get('journal_audit') and d['journal_audit']['identical'], d['cross_reference']
            continue
        for leg in d['legs']:
            if leg['in_branch_scope'] != 'Yes':
                continue
            assert leg['register_linekey'] in jkey, (d['cross_reference'], leg['register_linekey'])
            rcited.add(leg['register_linekey'])
        rsrc_docs.append(d)
    say(f'reconstruction sources: {len(rsrc_docs)} document(s) embedded verbatim, '
        f'{rm["documents_audited_only"]} audited only (rule 12), {len(rcited)} register line(s) evidenced by a reconstruction leg')

    # a sighted invoice (rule 17) supersedes a history identification on the same line: the green block carries the evidence
    for r in rows:
        if r['meta'].get('ident_v4') and r['V'][88]:
            r['meta']['ident_v4_superseded'] = r['meta'].pop('ident_v4')
    say(f'history identifications superseded by a sighted invoice: {sum(1 for r in rows if r["meta"].get("ident_v4_superseded"))}')

    # ------------------------------------------------------------------ LineKey uniqueness (rule 9)
    keys = [r['V'][1] for r in rows]
    assert len(keys) == len(set(keys)), 'LineKey collision'
    say(f'gate LineKey unique across {len(keys)} lines')

    # ------------------------------------------------------------------ sort
    def sk(r):
        V = r['V']
        return (str(V[2]), str(V[19]), str(V[16]), str(V[14]), V[4] if isinstance(V[4], dt.date) else dt.date(1900, 1, 1), str(V[8]), V[1])
    rows.sort(key=sk)
    FIRST = 5
    for n, r in enumerate(rows):
        r['row'] = FIRST + n
    v2new = {r['meta']['vrow']: r['row'] for r in rows if r['meta']['inherited']}

    # ------------------------------------------------------------------ inherited label canonicalisation audit (COUNTIF case trap)
    for c in (12, 24, 27, 31, 33, 132, 134, 136, 146):
        vals = collections.defaultdict(set)
        for r in rows:
            val = r['V'][c]
            if isinstance(val, str):
                vals[val.casefold()].add(val)
        coll = {k: s for k, s in vals.items() if len(s) > 1}
        if coll:
            say(f'case-variant labels in col {c}: {sorted(map(sorted, coll.values()))}')

    # ------------------------------------------------------------------ one contractor label per creditor code (COUNTIF canonical-label trap)
    # Col 12 is COUNTIF/SUMIFS-keyed, so a code carrying two spellings splits every per-contractor rollup.
    # Where a branch APLEDGER history is held its label is canonical for the code on every line, whatever the
    # path that identified the line: a sighted capture keeps the name as printed in its evidence text (col 28),
    # but col 12 carries the one researched label. This is the intent recorded on the THE289 label_basis at v5.
    relabelled = collections.Counter()
    for r in rows:
        cc = r['V'][11]
        canon = hist_label.get(cc.strip()) if isinstance(cc, str) else None
        if canon and isinstance(r['V'][12], str) and r['V'][12].strip() != canon:
            relabelled[(cc.strip(), r['V'][12].strip())] += 1
            r['V'][12] = canon
    if relabelled:
        say(f'col 12 labels canonicalised to the branch history label: {dict(relabelled)}')

    code_labels = collections.defaultdict(set)
    for r in rows:
        cc, lb = r['V'][11], r['V'][12]
        if isinstance(cc, str) and cc.strip() and isinstance(lb, str) and lb.strip():
            code_labels[cc.strip()].add(lb.strip())
    split = {k: sorted(s) for k, s in code_labels.items() if len(s) > 1}
    assert not split, ('creditor code carries more than one contractor label in col 12', split)
    say(f'gate one contractor label per creditor code across {len(code_labels)} codes')

    attach_files = []
    for b in ('attach_1', 'attach_2', 'attach_3'):
        for sf in json.load(open(os.path.join(ROOT, 'batches', b, f'corpus_{b}_v6.json')))['manifest']['source_files']:
            attach_files.append(dict(sf, batch=b))
    stage = dict(rows=rows, L=L, se2=se2, led_md5=led_md5, v127_md5=md5(V127), inherit_n=len(inherit), hist=H, attach_files=attach_files, hist_matches=hist_matches,
                 hist_conflicts=hist_conflicts, hist_ambiguous=hist_ambiguous, hist_audit=hist_audit,
                 unmatched_v=[(n, r) for n, r in unmatched_v], v2new=v2new, theme_v2=theme_v2, theme_v3=theme_v3,
                 svc_names=svc_names, na_names=na_names, sec_names=sec_names, flags=flags, oi_data=oi_data,
                 typo_rows=typo_rows, cred_new_matches=cred_new_matches, jnamed=stage_jnamed, log=log, jnet=jnet, jcount=jcount,
                 journal_batch=jb, journal_docs=jsrc_docs, journal_lines=sorted(jcited),
                 recon_batch=rb, recon_docs=rsrc_docs, recon_lines=sorted(rcited))
    # carry evidence
    sighted = [r for r in rows if r['V'][88]]
    evids = collections.OrderedDict()
    for r in sighted:
        evids.setdefault(r['V'][88], []).append(r)
    stage['sighted'] = sighted; stage['evids'] = evids
    # formula remap for sighted rows
    rx = re.compile(r'(?<![A-Za-z_])(\$?)([A-Z]{1,3})(\$?)(\d+)(?!\d)')
    gforms = {}
    for r in sighted:
        if not r['meta']['inherited'] or r['meta'].get('ported'):
            continue
        vr = r['meta']['vrow']
        for col in ('DQ', 'DR', 'DS', 'DT'):
            f = forms[f'{vr}|{col}']
            def rep(m):
                old = int(m.group(4))
                if m.group(2) in ('EIL',):
                    return m.group(0)
                assert old in v2new, (vr, col, f)
                return f'{m.group(1)}{m.group(2)}{m.group(3)}{v2new[old]}'
            nf = rx.sub(rep, f.replace('EIL_Invoice', '\x00I').replace('EIL_Amount', '\x00A').replace('EIL_LineKey', '\x00K'))
            nf = nf.replace('\x00I', 'EIL_Invoice').replace('\x00A', 'EIL_Amount').replace('\x00K', 'EIL_LineKey')
            gforms[(r['row'], col)] = '=' + nf
    keyrow = {r['V'][1]: r['row'] for r in rows}
    for lk, var in cap_variants.items():
        var['sibling_rows'] = [keyrow[x] for x in var['siblings']]
        for col, f in pbr_capture.formulas(keyrow[lk], var).items():
            gforms[(keyrow[lk], col)] = f
    stage['gforms'] = gforms
    stage['ev_new'] = ev_new; stage['cap_variants'] = cap_variants
    say(f'sighted rows {len(sighted)} across {len(evids)} invoices; green-block formulas remapped {len(gforms)}')
    os.makedirs(CACHE, exist_ok=True); pickle.dump(stage, open(_os.path.join(CACHE, 'stage.pkl'), 'wb'))
    say('stage written')
    return stage


if __name__ == '__main__':
    main(dry='--dry-run' in sys.argv)
