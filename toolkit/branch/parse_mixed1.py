"""parse_mixed1.py - Mixed 1.pdf, raw-text route (pdftotext -layout, page text retained), seven vendor templates.

Emits corpus JSON in the pswp corpus schema. Every priced row is captured verbatim from the page text
(rule 16a); Glascott schedule rows are captured as ATTACHMENT lines (rule 16d) and do not enter check 1,
which ties the invoice face. Gate: pswp_json_repair.repair_and_gate.
"""
import datetime as dt, hashlib, json, re, subprocess, sys
from decimal import Decimal, ROUND_HALF_UP

import os
PDF = os.environ.get('PDF', 'Mixed_1.pdf')
D = lambda x: Decimal(str(x).replace(',', '').replace('$', '')).quantize(Decimal('0.01'), ROUND_HALF_UP)
MON = {m: i for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'], 1)}


def text(page, layout=True):
    a = ['pdftotext'] + (['-layout'] if layout else []) + ['-f', str(page), '-l', str(page), PDF, '-']
    return subprocess.run(a, capture_output=True, text=True).stdout


def iso(s):
    s = s.strip()
    m = re.match(r'(\d{1,2})/(\d{2})/(\d{2,4})$', s)
    if m:
        y = int(m.group(3)); y = y + 2000 if y < 100 else y
        return dt.date(y, int(m.group(2)), int(m.group(1))).isoformat()
    m = re.match(r'(\d{1,2})-(\d{2})-(\d{4})$', s)
    if m:
        return dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
    m = re.match(r'(\d{1,2}) ([A-Za-z]{3})[a-z]* (\d{4})$', s)
    if m:
        return dt.date(int(m.group(3)), MON[m.group(2).lower()], int(m.group(1))).isoformat()
    m = re.match(r'(\d{1,2})-([A-Za-z]{3})[a-z]*-(\d{4})$', s)   # Play Force and PPG attachment layouts (branch v6)
    if m:
        return dt.date(int(m.group(3)), MON[m.group(2).lower()], int(m.group(1))).isoformat()
    raise ValueError(s)


class Doc:
    def __init__(self, vendor, first):
        self.vendor = vendor; self.pages = [first]; self.lines = []; self.attach = []; self.h = {}
        self.findings = []

    def add(self, page, no, txt, kind, **f):
        self.lines.append(dict(source='TEXT', page=page, line_no=no, line_text=txt.rstrip(), line_type=kind,
                               ocr_only=False, ocr_status='not_required', ocr_reason='text layer present',
                               qty=f.get('qty'), unit=None, unit_price_ex_gst=f.get('unit'), line_ex_gst=f.get('amt'),
                               gst=(float(D(f['gst'])) if f.get('gst') and re.fullmatch(r'[\d,]+\.\d{2}', str(f['gst'])) else None), gst_rate_printed=(f.get('gst') if f.get('gst') and not re.fullmatch(r'[\d,]+\.\d{2}', str(f['gst'])) else None), stated_amt=None, band_hits=f.get('bands', []), work_order=f.get('wo'),
                               note=f.get('note')))


def vendor_of(p):
    if 'T & H LEVAI' in p: return 'LEVAI'
    if 'Total Environmental' in p and 'Invoice Number' in p: return 'TEC'
    if 'Australasia Pty Ltd' in p and 'Tax Invoice' in p: return 'TREESCAPE'
    if re.search(r'INVOICE\s*NO\.?', p) and 'Fletcher' in p: return 'BUSHCARE'
    if 'A.B.N: 89 122 731 775' in p: return 'AUSTSPRAY'
    if 'PAYMENT ADVICE' in p: return None
    if 'Management Unit' in p and 'Invoice Date' in p: return 'EMU'
    if 'Lilgeco' in p and 'Invoice Date' in p: return 'ACTIVECO'
    if 'Guru Dirt Works' in p and ('Invoice Date' in p or 'Issue date' in p): return 'GURU'
    if 'ABN: 53 093 389 407' in p and 'Site Contact:' in p: return 'AUSTCARE'
    if 'Technigr' in p and 'Invoice No' in p: return 'GLASCOTT'
    return None


NUMROW = re.compile(r'^(?P<d>.*?\S)\s{2,}(?P<q>-?\d+(?:\.\d+)?)\s+(?P<u>-?[\d,]+\.\d{2})\s+(?:(?P<g>\d+%)\s+)?(?P<a>-?[\d,]+\.\d{2})\s*$')
NUMONLY = re.compile(r'^\s+(?P<q>\d+(?:\.\d+)?)\s+(?P<u>[\d,]+\.\d{2})\s+(?P<g>\d+%)\s+(?P<a>[\d,]+\.\d{2})\s*$')
BUSH = re.compile(r'^\s*(?P<d>Park:.*?\S|Woody weed and Vine treatment)\s{2,}(?P<q>\d+)\s+(?P<u>[\d,]+\.\d{2,3})\s+(?P<a>[\d,]+\.\d{2})\s+GST\s*$')
AUSTC = re.compile(r'(\d{5})\s+(.+?)\s+(\d{6})\s+(PK\d{6})\s+\$([\d,]+\.\d{2})', re.S)
GLAS = re.compile(r'^\s*(?P<park>.+?\S)\s{2,}(?P<wt>(?:Communities |Tracks )?AMP|Rubbish Removal)\s+(?P<site>\S+)\s+(?P<pk>PK\d{6})\s+(?P<rot>\d+ of \d+)\s+\$(?P<ex>[\d,]+\.\d{2})\s+\$(?P<gst>[\d,]+\.\d{2})\s+\$(?P<inc>[\d,]+\.\d{2})\s+(?P<date>.+?)\s*$')
MONEY_TAIL = re.compile(r'^(?P<d>.*?\S)\s{2,}\$?(?P<a>-?[\d,]+\.\d{2})\s*$')


def labelled(page_text, label, first=True):
    hits = re.findall(r'(?im)^.*?' + label + r'\s*:?\s*\$?\s*(-?[\d,]+\.\d{2})\s*$', page_text)
    return D(hits[0] if first else hits[-1]) if hits else None



def austcare_rows(page):
    """Word-level bbox: job rows keyed by the Job No. word; site-name lines (x in the Site Name band) assigned to the
    nearest job row by vertical midpoint boundaries. Every cell is vertically centred in its row, so this is exact."""
    from lxml import etree
    xml = subprocess.run(['pdftotext', '-bbox', '-f', str(page), '-l', str(page), PDF, '-'], capture_output=True, text=True).stdout
    x = etree.fromstring(xml.encode()); ns = {'h': 'http://www.w3.org/1999/xhtml'}
    words = [(float(w.get('xMin')), float(w.get('yMin')), float(w.get('yMax')), w.text) for w in x.iterfind('.//h:word', ns)]
    jobs = sorted((y0 + y1) / 2 for x0, y0, y1, t in words if re.fullmatch(r'\d{5}', t) and x0 < 60)
    if not jobs:
        return []
    def row_of(yc):
        return min(range(len(jobs)), key=lambda i: abs(jobs[i] - yc))
    rows = [dict(job=None, site=[], order=None, pk=None, amt=None) for _ in jobs]
    lines = {}
    for x0, y0, y1, t in words:
        lines.setdefault(round(y0), []).append((x0, y0, y1, t))
    for y in sorted(lines):
        ws = sorted(lines[y]); yc = (ws[0][1] + ws[0][2]) / 2
        if yc < min(jobs) - 12 or yc > max(jobs) + 12:
            continue
        r = rows[row_of(yc)]
        for x0, y0, y1, t in ws:
            if x0 < 60 and re.fullmatch(r'\d{5}', t): r['job'] = t
            elif 130 <= x0 < 240: r['site'].append(t)
            elif 240 <= x0 < 350: r['order'] = t
            elif 350 <= x0 < 470: r['pk'] = t
            elif x0 >= 470 and t.startswith('$'): r['amt'] = t
    return rows


def parse():
    n = 61
    pages = [text(p) for p in range(1, n + 1)]
    raws = [text(p, False) for p in range(1, n + 1)]
    docs = []
    cur = None
    for pno, p in enumerate(pages, 1):
        v = vendor_of(p)
        if v:
            cur = Doc(v, pno); docs.append(cur)
        else:
            assert cur, pno
            cur.pages.append(pno)
    assert len(docs) == 30, len(docs)

    for d in docs:
        P = [(pn, pages[pn - 1]) for pn in d.pages]
        full = '\n'.join(p for _, p in P)
        d.page_text = {pn: pages[pn - 1] for pn in d.pages}
        h = d.h
        h['pk'] = sorted(set(re.findall(r'PK\s?\d{6}', full)))
        h['po'] = sorted(set(re.findall(r'\b(?:7\d{5}|8\d{5})\b', full)))
        h['contract'] = sorted(set(re.findall(r'PAR/?\d{3}[A-Z]?/?\d{4}|PAR\d{3}[A-Z]\d{4}|LCC-\d{2}-\d{4}', full)))
        vend = d.vendor
        lno = 0
        if vend == 'LEVAI':
            h.update(supplier='T & H LEVAI PTY LTD', abn='65 100 395 480', inv=re.search(r'TAX INVOICE\s+(INV-\d+)', full).group(1),
                     date=iso(re.search(r'DATE\s+(\d+ \w+ \d{4})', full).group(1)), due=iso(re.search(r'DUE DATE\s+(\d+ \w+ \d{4})', full).group(1)),
                     sub=labelled(full, 'Subtotal'), gst=labelled(full, r'GST \(10%\)'), tot=labelled(full, 'Total'), ref=re.search(r'YOUR REF\s+(\d+)', full).group(1))
            for pn, p in P:
                for ln in p.splitlines():
                    lno += 1
                    m = re.match(r'^\s*(Quote No\. \d+:)\s+([\d,]+\.\d{2})\s*$', ln)
                    if m:
                        d.add(pn, lno, ln, 'PRICED', qty=1.0, unit=float(D(m.group(2))), amt=float(D(m.group(2))), bands=['amount'])
                    elif ln.strip():
                        d.add(pn, lno, ln, 'NARRATIVE')
        elif vend in ('TEC', 'EMU', 'ACTIVECO', 'GURU'):
            hp = P[0][1]
            name = {'TEC': ('Total Environmental Concepts Pty Ltd', '11 600 627 343'), 'EMU': ('Environmental Management Unit Pty Ltd', '57 679 181 447'),
                    'ACTIVECO': ('Lilgeco Pty Ltd ATF M Hanns Family Trust Trading As Activeco', '36 540 248 138'), 'GURU': ('Guru Dirt Works', '39 950 797 737')}[vend]
            if 'Bill to' in hp:  # Guru new Xero layout
                m = re.search(r'\$([\d,]+\.\d{2})\s+(\d+ \w+ \d{4})\s+(\d+ \w+ \d{4})\s+(INV-\d+)\s+(PO\d+)', hp)
                h.update(supplier=name[0], abn='39950797737 (printed ungrouped)', inv=m.group(4), date=iso(m.group(3)), due=iso(m.group(2)), ref=m.group(5),
                         sub=labelled(full, 'Subtotal'), gst=labelled(full, 'Total GST 10%'), tot=D(re.search(r'^\s*Total\s+([\d,]+\.\d{2})\s*$', full, re.M).group(1)))
            else:
                mi = re.search(r'Invoice Number[^\n]*\n[^\n]*?\b(INV-\d+|\d{4})\b', hp)
                md = re.search(r'Invoice Date[^\n]*\n[^\n]*?\b(\d{1,2} \w{3} \d{4})', hp)
                h.update(supplier=name[0], abn=name[1], inv=mi.group(1), date=iso(md.group(1)), sub=labelled(full, 'Subtotal'),
                         gst=labelled(full, r'TOTAL\s+GST\s+10%'), tot=labelled(full, 'TOTAL AUD'))
                mr = re.search(r'Reference[^\n]*\n(?:[^\n]*\n)?[^\n]*?\b(PO#?:? ?\d+|\d{6}|PK\d{6})\b', hp); h['ref'] = mr.group(1) if mr else None
                mdd = re.search(r'Due Date:\s+(\d+ \w{3} \d{4})', full); h['due'] = iso(mdd.group(1)) if mdd else None
            pend = None
            for pn, p in P:
                for ln in p.splitlines():
                    lno += 1
                    if not ln.strip():
                        continue
                    if re.search(r'^\s*(Subtotal|TOTAL\s+GST|TOTAL AUD|Total GST|Total\s+[\d,]+\.\d{2}|Amount due)', ln):
                        d.add(pn, lno, ln, 'TOTALS'); continue
                    m = NUMROW.match(ln)
                    if vend == 'ACTIVECO':
                        m2 = re.match(r'^(?P<d>PK\d{6}\s+.*?\S)\s{2,}(?P<q>\d+\.\d\d)\s+(?P<u>[\d,]+\.\d{2})\s+(?P<a>[\d,]+\.\d{2})\s*$', ln)
                        if m2:
                            d.add(pn, lno, ln, 'PRICED', qty=float(m2.group('q')), unit=float(D(m2.group('u'))), amt=float(D(m2.group('a'))), bands=['qty', 'unit_price', 'amount'], wo='PK000378')
                            continue
                    if m and not re.search(r'Amount Due|Amount due', ln):
                        d.add(pn, lno, ln, 'PRICED', qty=float(m.group('q')), unit=float(D(m.group('u'))), amt=float(D(m.group('a'))), gst=m.group('g'),
                              bands=['qty', 'unit_price', 'amount'])
                        continue
                    m = NUMONLY.match(ln)
                    if m and pend is not None:
                        d.lines[pend].update(line_type='PRICED', qty=float(m.group('q')), unit_price_ex_gst=float(D(m.group('u'))), line_ex_gst=float(D(m.group('a'))),
                                             gst=None, gst_rate_printed=m.group('g'), band_hits=['qty', 'unit_price', 'amount'], note='amounts print on the following layout row: ' + ln.strip())
                        d.add(pn, lno, ln, 'NARRATIVE', note='numeric row of the preceding description'); pend = None; continue
                    d.add(pn, lno, ln, 'NARRATIVE')
                    pend = len(d.lines) - 1 if vend == 'GURU' and re.match(r'^\s?\S', ln) and 'Day Rate' in ln or 'Variation' in ln else pend
        elif vend == 'TREESCAPE':
            p = P[0][1]
            h.update(supplier='Treescape Australasia Pty Ltd', abn='20-117-830-118 (printed hyphenated)', inv=re.search(r'Tax Invoice\s*\n.*?(\d{5})', p).group(1),
                     date=iso(re.search(r'Date : (\S+)', p).group(1)), due=iso(re.search(r'Due Date : (\S+)', p).group(1)), ref=re.search(r'Order No : (\d+)', p).group(1),
                     sub=labelled(p, 'Subtotal'), gst=labelled(p, r'\bGST\b'), tot=labelled(p, r'\bTotal\b'))
            for ln in p.splitlines():
                lno += 1
                if not ln.strip(): continue
                m = re.match(r'^(Mowing contract - Logan - Q1GSL21074)\s{2,}\$([\d,]+\.\d{2})\s*$', ln)
                if m: d.add(d.pages[0], lno, ln, 'PRICED', qty=1.0, unit=float(D(m.group(2))), amt=float(D(m.group(2))), bands=['amount'], wo='PK000373')
                elif re.match(r'^\s*(Subtotal|GST|Total)\s', ln): d.add(d.pages[0], lno, ln, 'TOTALS')
                else: d.add(d.pages[0], lno, ln, 'NARRATIVE')
        elif vend == 'BUSHCARE':
            hp = P[0][1]
            h.update(supplier='Bushcare Services', abn='14 532 577 037', inv=re.search(r'INVOICE\s*NO\.?\s+(\d{5})', hp).group(1),
                     date=iso(re.search(r'(?<![EU] )\bDATE\s+(\d{2}/\d{2}/\d{4})', hp).group(1)), due=iso(re.search(r'D\s?U\s?E DATE\s+(\d{2}/\d{2}/\d{4})', hp).group(1)),
                     ref=re.search(r'(?:P\s*O\s*NUMBER|O NUMBER)\s*\n?\s*(\d{6})', hp).group(1), sub=labelled(full, 'SUBTOTAL'), gst=labelled(full, r'GST\s*TOTAL'), tot=labelled(full, r'^\s*TOTAL(?!\s*GST)'))
            if h['tot'] is None:
                h['tot'] = labelled(full, r'BALANCE D\s*U\s*E\s+A')
            for pn, p in P:
                for ln in p.splitlines():
                    lno += 1
                    if not ln.strip(): continue
                    m = BUSH.match(ln)
                    if m:
                        d.add(pn, lno, ln, 'PRICED', qty=float(m.group('q')), unit=float(m.group('u').replace(',', '')), amt=float(D(m.group('a'))), gst='GST', bands=['qty', 'rate', 'amount'])
                    elif re.search(r'SUBTOTAL|GST TOTAL|^\s*TOTAL|BALANCE', ln): d.add(pn, lno, ln, 'TOTALS')
                    else: d.add(pn, lno, ln, 'NARRATIVE')
        elif vend == 'AUSTSPRAY':
            p = P[0][1]
            m = re.search(r'Invoice Number: (\d+)\s+Order Number: (\d+) (PK ?\d{6})\s+Date: (\S+)', p)
            h.update(supplier='Austspray Environmental Weed Control Pty Ltd', abn='89 122 731 775', inv=m.group(1), ref=m.group(2), date=iso(m.group(4)),
                     sub=labelled(p, 'Sub Total'), gst=labelled(p, r'G\.S\.T\.'), tot=labelled(p, r'^\s*Total'), due=None, pk_printed=m.group(3))
            lines = p.splitlines()
            i = 0; item_buf = []; in_item = False
            for ln in lines:
                lno += 1
                if not ln.strip(): continue
                if re.match(r'^\s*Item\s+Total\s*$', ln): in_item = True; d.add(d.pages[0], lno, ln, 'HEADER'); continue
                if in_item and re.match(r'^\s*\$([\d,]+\.\d{2})\s*$', ln):
                    amt = D(ln.strip())
                    item_buf.append((lno, ln)); continue
                if in_item and ln.strip().startswith('Variations'):
                    in_item = False
                    txt = ' | '.join(t.strip() for _, t in item_buf)
                    d.add(d.pages[0], item_buf[0][0], txt, 'PRICED', qty=1.0, unit=float(amt), amt=float(amt), bands=['amount'], note='item block spans several layout rows; amount printed on its own row')
                    d.add(d.pages[0], lno, ln, 'NARRATIVE'); continue
                if in_item and re.match(r'^\s*Sub Total', ln):
                    in_item = False
                    txt = ' | '.join(t.strip() for _, t in item_buf)
                    d.add(d.pages[0], item_buf[0][0], txt, 'PRICED', qty=1.0, unit=float(amt), amt=float(amt), bands=['amount'], note='item block spans several layout rows; amount printed on its own row')
                    d.add(d.pages[0], lno, ln, 'TOTALS'); continue
                if in_item:
                    item_buf.append((lno, ln)); continue
                mv = re.match(r'^\s*(LZ\d-\d+.*?\S)\s{2,}\$(-?[\d,]+\.\d{2})\s*$', ln)
                if mv:
                    d.add(d.pages[0], lno, ln, 'PRICED', qty=1.0, unit=float(D(mv.group(2))), amt=float(D(mv.group(2))), bands=['amount']); continue
                if re.match(r'^\s*(Sub Total|G\.S\.T\.|Total)\s', ln): d.add(d.pages[0], lno, ln, 'TOTALS')
                else: d.add(d.pages[0], lno, ln, 'NARRATIVE')
        elif vend == 'AUSTCARE':
            hp = P[0][1]
            h.update(supplier='Aust Care Environmental Services Pty Ltd', abn='53 093 389 407', inv=re.search(r'TAX INVOICE NO\. (\d+)', hp).group(1),
                     date=iso(re.search(r'Date:\s+(\d{2}/\d{2}/\d{4})', hp).group(1)), due=iso(re.search(r'PLEASE PAY BY.*?\n\s*(\d{2}/\d{2}/\d{4})', hp, re.S).group(1)),
                     sub=labelled(full, 'Sub-Total ex GST'), gst=labelled(full, r'^\s*GST'), tot=labelled(full, 'Total inc GST'))
            for pn in d.pages:
                for r in austcare_rows(pn):
                    lno += 1
                    assert r['job'] and r['amt'] and r['pk'], (pn, r)
                    txt = f"{r['job']} {' '.join(r['site'])} {r['order']} {r['pk']} {r['amt']}"
                    d.add(pn, lno, txt, 'PRICED', qty=1.0, unit=float(D(r['amt'])), amt=float(D(r['amt'])), bands=['amount'], wo=r['pk'],
                          note='row rebuilt from word positions (pdftotext -bbox); site name printed across wrapped cells')
                for ln in pages[pn - 1].splitlines():
                    if ln.strip() and not re.match(r'^\s*\d{5}\b', ln) and not re.search(r'\b8\d{5}\b|\b7\d{5}\b', ln) and not re.match(r'^\s{15,}\S', ln):
                        lno += 1
                        d.add(pn, lno, ln, 'TOTALS' if re.search(r'Sub-Total|^\s*GST|Total inc|Amount Applied|Balance Due', ln) else 'NARRATIVE')
            h['ref'] = ', '.join(sorted(set(re.findall(r'\b(?:70\d{4}|80\d{4})\b', full))))
        elif vend == 'GLASCOTT':
            hp = P[0][1]
            h.update(supplier='Glascott Landscape and Civil Pty Limited (letterhead prints "Technigro ABN 97 001 281 572")', abn='97 001 281 572', inv=re.search(r'Invoice No\s+(\d+)', hp).group(1),
                     date=iso(re.search(r'Invoice\s+Date\s+:\s+(\S+)', hp).group(1)), due=iso(re.search(r'Due Date\s+:\s+(\S+)', hp).group(1)), ref=re.search(r'Order Ref\s+:\s+(\d+)', hp.replace(' Ref ',' Ref ')).group(1) if re.search(r'Order Ref\s+:\s+(\d+)', hp) else re.search(r'Ref\s+:\s+(\d{6})', hp).group(1),
                     sub=labelled(hp, 'Invoice Amount'), gst=labelled(hp, 'Plus GST'), tot=labelled(hp, r'Total\s+Incl\.\s+GST'))
            for ln in hp.splitlines():
                lno += 1
                if not ln.strip(): continue
                m = re.match(r'^\s*(Please refer to attached sheet for details\.)\s{2,}([\d,]+\.\d{2})\s*$', ln)
                if m: d.add(d.pages[0], lno, ln, 'PRICED', qty=1.0, unit=float(D(m.group(2))), amt=float(D(m.group(2))), bands=['amount'], wo='PK000378')
                elif re.search(r'Invoice Amount|Plus GST|Total\s+Incl', ln): d.add(d.pages[0], lno, ln, 'TOTALS')
                else: d.add(d.pages[0], lno, ln, 'NARRATIVE')
            sched = Decimal(0)
            for ln in P[1][1].splitlines():
                lno += 1
                if not ln.strip(): continue
                m = GLAS.match(ln)
                if m:
                    sched += D(m.group('ex'))
                    d.add(d.pages[1], lno, ln, 'ATTACHMENT', qty=1.0, unit=float(D(m.group('ex'))), amt=None, gst=m.group('gst'), wo=m.group('pk'),
                          note=f'attached schedule row (rule 16d), ex GST ${m.group("ex")}; not a face line, excluded from check 1')
                else:
                    d.add(d.pages[1], lno, ln, 'NARRATIVE' if 'Total' not in ln else 'TOTALS')
            h['sched'] = sched
            d.findings.append(f'Attached schedule totals ${sched:,} ex GST against the invoice face ${h["sub"]:,}; difference ${sched - h["sub"]:,}. The face is what was billed and what the ledger carries.')
    # duplicates
    seen = {}
    out = []
    for d in docs:
        h = d.h
        key = (h['supplier'], h['inv'])
        dup = seen.get(key)
        seen.setdefault(key, f'{h["inv"]}/pages{d.pages[0]}-{d.pages[-1]}')
        pr = [d.pages[0], d.pages[-1]]
        cap = sum(D(l['line_ex_gst']) for l in d.lines if l['line_type'] == 'PRICED')
        gst_calc = (h['sub'] * Decimal('0.1')).quantize(Decimal('0.01'), ROUND_HALF_UP)
        if h['gst'] != gst_calc:
            d.findings.append(f'Printed GST ${h["gst"]} differs from 10% of the subtotal ${gst_calc} by {abs(h["gst"] - gst_calc)} (rounding; check 3 rounding-tolerance variant).')
        purpose = {'LEVAI': 'track works', 'TEC': 'creek crossing' if h['inv'] == '3597' else 'weed rehab', 'TREESCAPE': 'mowing R4', 'BUSHCARE': 'bush maint',
                   'AUSTSPRAY': 'landscape', 'EMU': 'bush maint', 'ACTIVECO': 'bush maint', 'GURU': 'MTB trail', 'AUSTCARE': 'bush maint', 'GLASCOTT': 'bush maint'}[d.vendor]
        sname = {'LEVAI': 'Levai', 'TEC': 'TEC', 'TREESCAPE': 'Treescap', 'BUSHCARE': 'Bushcare', 'AUSTSPRAY': 'Austspray', 'EMU': 'EMU', 'ACTIVECO': 'Activeco',
                 'GURU': 'Guru Dirt', 'AUSTCARE': 'AustCare', 'GLASCOTT': 'Glascott'}[d.vendor]
        stem = f'{sname}, {purpose}, {dt.date.fromisoformat(h["date"]).strftime("%b-%Y")}, {h["tot"]:.2f}'
        assert len(stem) <= 40, stem
        doc = dict(doc_ref=f'{h["inv"]}/pages{pr[0]}-{pr[1]}', doc_kind='TAX_INVOICE', source_file='Mixed_1.pdf', page_range=pr,
                   supplier=h['supplier'], supplier_abn=h['abn'], abn_source='letterhead', invoice_no=h['inv'], invoice_date=h['date'], due_date=h.get('due'),
                   printed_subtotal_ex_gst=float(h['sub']), subtotal_basis='printed', printed_gst=float(h['gst']), printed_total_incl_gst=float(h['tot']),
                   captured_ex_gst=float(cap), line_amount_basis='ex_gst', tie_basis='ex_gst', self_tie='TIE' if cap == h['sub'] else 'OUT',
                   retry_log=[], table_headers=[], work_orders=h['pk'], contract_refs=h['contract'], po_refs=[h.get('ref')] if h.get('ref') else [], pk_refs=h['pk'],
                   printed_account_codes=h['pk'], evidence_stem=stem, duplicate_of=dup, findings=d.findings,
                   notes=f'{d.vendor} template, raw-text route (pdftotext -layout), page text retained.', lines=d.lines,
                   page_text=d.page_text, vendor_template=d.vendor)
        out.append(doc)
    return out


if __name__ == '__main__':
    docs = parse()
    md5 = hashlib.md5(open(PDF, 'rb').read()).hexdigest()
    corpus = dict(manifest=dict(batch_id='mixed_1', source_files=[dict(file='Mixed_1.pdf', md5=md5, pages=61)], runtime='A',
                                extraction_tool='parse_mixed1.py raw-text route (pdftotext -layout, 7 vendor templates)', extracted_utc=dt.datetime.utcnow().isoformat() + 'Z',
                                prompt_version='v5 (raw-text fallback)', ocr_pages_run=0, ocr_pages_not_required=61, ocr_pages_not_available=0, ocr_pages_outstanding=0,
                                resume_point=None), documents=docs)
    json.dump(corpus, open(os.environ.get('OUT', 'corpus_mixed_1_v6.json'), 'w'), indent=1)
    for d in docs:
        pl = [l for l in d['lines'] if l['line_type'] == 'PRICED']
        print(f"{d['invoice_no']:10} {d['vendor_template']:9} p{d['page_range']} sub {d['printed_subtotal_ex_gst']:>10,.2f} cap {d['captured_ex_gst']:>10,.2f} {d['self_tie']} priced {len(pl)} lines {len(d['lines'])} dup={d['duplicate_of']} {d['findings'][:1]}")
