"""parse_mixed_new.py - Mixed_new_26-27.pdf, raw-text route (pdftotext -layout, page text retained), 13 vendor templates."""
import datetime as dt, hashlib, json, os, re, subprocess, sys
from decimal import Decimal, ROUND_HALF_UP
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_mixed1 import D, iso, Doc, labelled, NUMROW, NUMONLY, text as _text  # noqa

PDF = os.environ.get('PDF', 'Mixed_new_26-27.pdf')
def text(page): return subprocess.run(['pdftotext', '-layout', '-f', str(page), '-l', str(page), PDF, '-'], capture_output=True, text=True).stdout
NP = '(not printed)'
M = r'-?\$?[\d,]+\.\d{2}'


def vendor_of(p):
    if 'Your Business Electricity Tax Invoice' in p: return 'ORIGIN'
    if p.lstrip().startswith('Sea-Crete') and 'Invoice No:' in p: return 'SEACRETE'
    if 'Pool Shop QLD' in p and ('Invoice Number' in p or 'Invoice number' in p) and 'PAYMENT ADVICE' not in p: return 'POOLSHOP'
    if 'qpower.com.au' in p and 'Page 1/4' in p: return 'QPOWER'
    if 'Play Force Australia Pty Ltd | 89 677 476 541' in p: return 'PLAYFORCE'
    if 'Flavell-Dau' in p and ('Invoice Number' in p or 'Invoice number' in p): return 'FLAVELL'
    if 'T & H LEVAI PTY LTD | ABN' in p: return 'LEVAI'
    if 'WEIS CONTRACTORS' in p and ('Invoice Number' in p or 'Invoice number' in p): return 'WEIS'
    if 'Elemental Shade Structures' in p and 'Invoice No.' in p: return 'ELEMENTAL'
    if 'A.B.N: 89 122 731 775' in p: return 'AUSTSPRAY'
    if 'Higgins Coatings Pty Ltd' in p and 'Invoice' in p: return 'HIGGINS'
    if 'Harpley Services Pty Ltd' in p and 'Invoice No.:' in p and 'Page 1 of' in p: return 'HARPLEY'
    if 'Coast2Coast' in p and 'Invoice number' in p: return 'C2C'
    if 'kachelcleaning' in p: return 'KACHEL'
    return None


def parse():
    pages = [text(p) for p in range(1, 76)]
    docs = []; cur = None
    for pno, p in enumerate(pages, 1):
        v = vendor_of(p)
        if v:
            cur = Doc(v, pno); docs.append(cur)
        else:
            assert cur, pno; cur.pages.append(pno)
    assert len(docs) == 36, len(docs)
    for d in docs:
        P = [(pn, pages[pn - 1]) for pn in d.pages]
        full = '\n'.join(p for _, p in P); d.page_text = {pn: pages[pn - 1] for pn in d.pages}
        h = d.h; v = d.vendor; lno = 0
        h['pk'] = sorted(set(re.findall(r'PK\s?\d{5,6}', full)))
        h['contract'] = sorted(set(re.findall(r'PAR/?\d{3}[A-Z]?/?\d{4}|PAR\d{3}[A-Z]\d{4}|LCC-\d{2}-\d{4}|LB304', full)))
        def add_all(kind_fn):
            nonlocal lno
            for pn, p in P:
                for ln in p.splitlines():
                    lno += 1
                    if ln.strip(): kind_fn(pn, lno, ln)
        if v == 'ORIGIN':
            hp = P[0][1]
            h.update(supplier='Origin Energy Electricity Limited', abn='33 071 052 287', inv=re.search(r'Tax Invoice No\.\s*\n\s*(\d+)', hp).group(1),
                     date=iso(re.search(r'Issue Date[^\n]*\n[^\n]*?(\d{2} \w{3} \d{2})\b', hp).group(1).replace(' 26', ' 2026')), due=iso(re.search(r'DUE DATE: (\d+ \w{3} \d{2})', hp).group(1).replace(' 26', ' 2026')),
                     sub=D(re.search(r'Sub-Total\s*\n\s*GST\s*\n\s*\$([\d,]+\.\d{2})', hp).group(1)), gst=D(re.search(r'Sub-Total\s*\n\s*GST\s*\n\s*\$[\d,]+\.\d{2}\s*\n\s*\$([\d,]+\.\d{2})', hp).group(1)),
                     tot=D(re.search(r'^\s*Total\s+\$([\d,]+\.\d{2})', hp, re.M).group(1)), ref=re.search(r'Account No\.\s*\n\s*(\d+)', hp).group(1))
            pend = None; site_gst = None
            for pn, p in P:
                for ln in p.splitlines():
                    lno += 1
                    if not ln.strip(): continue
                    s = ln.strip()
                    if s.startswith('NMI:'): pend = [lno, s]; d.add(pn, lno, ln, 'NARRATIVE'); continue
                    if s.startswith('Site Address:') and pend: pend[1] += ' | ' + s; d.add(pn, lno, ln, 'NARRATIVE'); continue
                    mg = re.match(r'^\s*GST: \$([\d,]+\.\d{2})\s*$', ln)
                    if mg and pend: site_gst = D(mg.group(1)); d.add(pn, lno, ln, 'NARRATIVE'); continue
                    mm = re.match(r'^\s*\$([\d,]+\.\d{2})\s+\$([\d,]+\.\d{2})(?:\s+\$([\d,]+\.\d{2})( CR)?)?\s+Total: \$([\d,]+\.\d{2})\s+\$([\d,]+\.\d{2})\s*$', ln)
                    if mm and pend:
                        d.add(pn, lno, pend[1] + ' | New charges: $' + mm.group(2), 'PRICED', qty=1.0, unit=float(D(mm.group(2))), amt=float(D(mm.group(2))), bands=['amount'], gst=f'{site_gst:.2f}',
                              note=f'site row; carried forward ${mm.group(1)}, site total ${mm.group(5)}, balance ${mm.group(6)}; amounts print on the row: {s}')
                        if mm.group(3):
                            adj = D(mm.group(3)) * (-1 if mm.group(4) else 1)
                            d.add(pn, lno, pend[1] + ' | Additional charges, credits and adjustments: $' + mm.group(3) + (mm.group(4) or ''), 'PRICED', qty=1.0, unit=float(adj), amt=float(adj), bands=['amount'], note='additional charges column on the same site row' + ('; CR = credit, captured negative' if mm.group(4) else ''))
                        pend = None; continue
                    d.add(pn, lno, ln, 'TOTALS' if re.match(r'^\s*(Sub-Total|GST|Total|Energy Charges|Network|Regulated|Environmental|Metering|Retail Service|Additional Charges)', ln) else 'NARRATIVE')
        elif v == 'SEACRETE':
            hp = P[0][1]
            h.update(supplier='Sea-Crete (Jeol Pty Ltd)', abn='84127054291 (printed ungrouped)', inv=re.search(r'Invoice No:\s+(\d+)', hp).group(1), date=iso(re.search(r'Date:\s+(\S+)', hp).group(1)),
                     due=iso(re.search(r'Due Date:\s+(\S+)', hp).group(1)), sub=labelled(hp, 'Subtotal'), gst=labelled(hp, 'GST 10%'), tot=D(re.search(r'\bTotal\s+\$([\d,]+\.\d{2})', hp).group(1)), ref=NP)
            def f(pn, no, ln):
                mm = re.match(r'^\s*(?P<d>.*?\S)\s{2,}(?P<q>\d+)\s+\$(?P<u>[\d,]+\.\d{2})\s+\$(?P<a>[\d,]+\.\d{2})\s*$', ln)
                if mm: d.add(pn, no, ln, 'PRICED', qty=float(mm.group('q')), unit=float(D(mm.group('u'))), amt=float(D(mm.group('a'))), bands=['qty', 'rate', 'amount'])
                elif re.search(r'Subtotal|GST 10%|^\s*Total|Balance Due|Paid', ln): d.add(pn, no, ln, 'TOTALS')
                else: d.add(pn, no, ln, 'NARRATIVE')
            add_all(f)
        elif v in ('POOLSHOP', 'WEIS', 'FLAVELL', 'C2C'):
            hp = P[0][1]
            name = {'POOLSHOP': ('Pool Shop QLD Pty Ltd', '54 618 873 251'), 'WEIS': ('WEIS CONTRACTORS', '71 812 055 648'), 'FLAVELL': ('The Trustee for Flavell-Dau Family Trust', '47 220 358 629'), 'C2C': ('Coast2Coast Grounds and Gardens', '24488420203 (printed ungrouped)')}[v]
            newx = 'Bill to' in hp or 'Amount due' in hp.split('Description')[0]
            if newx:
                mm = re.search(r'Invoice number\s+Reference\s*\n\s*(?:\$[\d,]+\.\d{2}\s+)?(?:\d+ \w+ \d{4}\s+)?(?:\d+ \w+ \d{4}\s+)?(INV-\d+)\s+(.*?)\s*$', hp, re.M)
                inv = re.search(r'(INV-\d+)', hp.split('Invoice number')[1]).group(1)
                dates = re.findall(r'(\d{1,2} \w+ \d{4})', hp.split('Amount due')[1].split('Description')[0])
                h.update(supplier=name[0], abn=name[1].replace(' ', '') + ' (printed ungrouped)' if v != 'C2C' else name[1], inv=inv, due=iso(dates[0]), date=iso(dates[1]),
                         sub=labelled(full, 'Subtotal'), gst=labelled(full, 'Total GST 10%'), tot=D(re.search(r'(?:View (?:and pay )?online\s+)?Total\s+([\d,]+\.\d{2})\s*$', full, re.M).group(1)),
                         ref=re.search(r'Reference\s*\n[^\n]*?(INV-\d+)\s+(.+?)\s*$', hp, re.M).group(2))
            else:
                h.update(supplier=name[0], abn=name[1], inv=re.search(r'Invoice Number[^\n]*\n[^\n]*?(INV-\d+)', hp).group(1), date=iso(re.search(r'Invoice Date[^\n]*\n[^\n]*?(\d{1,2} \w{3} \d{4})', hp).group(1)),
                         sub=labelled(full, 'Subtotal'), gst=labelled(full, r'TOTAL GST 10%'), tot=labelled(full, 'TOTAL AUD'), ref=re.search(r'Reference[^\n]*\n(?:[^\n]*\n)?\s*([^\n]+?)\s{2,}|Reference\s*\n\s*(\S.*?)\s*$', hp, re.M).group(1) or '')
                mdd = re.search(r'Due Date:\s+(\d+ \w{3} \d{4})', full); h['due'] = iso(mdd.group(1)) if mdd else None
            pend = None
            for pn, p in P:
                for ln in p.splitlines():
                    lno += 1
                    if not ln.strip(): continue
                    if re.search(r'^\s*(Subtotal|TOTAL\s+GST|TOTAL AUD|Total GST|Total\s+[\d,]+\.\d{2}|Amount due)', ln): d.add(pn, lno, ln, 'TOTALS'); continue
                    mm = NUMROW.match(ln)
                    if mm and 'Amount' not in ln:
                        d.add(pn, lno, ln, 'PRICED', qty=float(mm.group('q')), unit=float(D(mm.group('u'))), amt=float(D(mm.group('a'))), gst=mm.group('g'), bands=['qty', 'unit_price', 'amount']); pend = None; continue
                    mm = re.match(r'^\s+(?P<q>\d+(?:\.\d+)?)\s+(?P<u>[\d,]+\.\d{2})\s+(?:(?P<g>\d+%)\s+)?(?P<a>[\d,]+\.\d{2})\s*$', ln)
                    if mm and pend is not None:
                        d.lines[pend].update(line_type='PRICED', qty=float(mm.group('q')), unit_price_ex_gst=float(D(mm.group('u'))), line_ex_gst=float(D(mm.group('a'))), gst_rate_printed=mm.group('g'), band_hits=['qty', 'unit_price', 'amount'], note='amounts print on the following layout row: ' + ln.strip())
                        d.add(pn, lno, ln, 'NARRATIVE', note='numeric row of the preceding description'); pend = None; continue
                    mm = re.match(r'^(?P<d>.*?\S)\s{2,}10%\s+(?P<a>[\d,]+\.\d{2})\s*$', ln)  # Flavell description + tax + amount
                    if mm:
                        d.add(pn, lno, ln, 'PRICED', qty=1.0, unit=float(D(mm.group('a'))), amt=float(D(mm.group('a'))), gst_rate_printed='10%', bands=['amount']); pend = None; continue
                    mm = re.match(r'^\s*(?P<d>\S.*?\S)\s{2,}(?P<a>0\.00)\s*$', ln)  # Flavell new: PO# line with 0.00
                    if mm:
                        d.add(pn, lno, ln, 'PRICED', qty=None, unit=None, amt=0.0, bands=['amount']); pend = None; continue
                    d.add(pn, lno, ln, 'NARRATIVE')
                    if re.match(r'^\s?\S', ln) and not re.match(r'^\s*PK\d', ln) and not re.match(r'^\s*(Description|View|Please|BSB|Account|NAME|ACC|Thank|Payment|EFT|To:|BOQ|F82|PAYMENT|Customer|Invoice|Due|Amount|Enter|\d{3} |Jon|operations|accounts|christine|einvoicing|\+61|\d{2,4} |\$|Purchase Order|Vendor No|Reference|Contract|Logan City|PO Box|Lota|LOGAN|AUSTRALIA|ABN|Bill to|22 Crestview|LOGANLEA|nakita|07 |Marsden|177|35 Leahy|CABOOLTURE|admin@|0437)', ln):
                        pend = len(d.lines) - 1
        elif v == 'QPOWER':
            hp = P[0][1]
            h.update(supplier='Q Power (Qld) Pty Ltd', abn='82 067 507 591', inv=re.search(r'TAX INVOICE NO\. (\d+)', hp).group(1), date=iso(re.search(r'INVOICE DATE\s*\n[^\n]*?(\d{2}/\d{2}/\d{4})\s*$', hp, re.M).group(1)),
                     due=iso(re.search(r'PLEASE PAY BY[^\n]*\n[^\n]*?(\d{2}/\d{2}/\d{4})', hp).group(1)), ref=re.search(r'Order No\.:\s+(\d+)', hp).group(1),
                     sub=D(re.search(r'Sub-Total ex GST\s+\$([\d,]+\.\d{2})', full).group(1)), gst=D(re.search(r'^\s*GST\s+\$([\d,]+\.\d{2})', full, re.M).group(1)), tot=D(re.search(r'Total inc GST\s+\$([\d,]+\.\d{2})', full).group(1)))
            prev = None
            for pn, p in P:
                for ln in p.splitlines():
                    lno += 1
                    if not ln.strip(): continue
                    mm = re.match(r'^\s*(?P<d>.*?)\s*(?P<q>\d+\.\d{2})\s+\$(?P<u>[\d,]+\.\d{2})\s+10%\s+\$(?P<a>[\d,]+\.\d{2})\s*$', ln)
                    if mm:
                        prev = prev or '(preceding row not captured)'
                        d.add(pn, lno, (ln if mm.group('d').strip() else f'{prev} {ln.strip()}'), 'PRICED', qty=float(mm.group('q')), unit=float(D(mm.group('u'))), amt=float(D(mm.group('a'))), gst_rate_printed='10%', bands=['qty', 'unit_price', 'amount'],
                              note=None if mm.group('d').strip() else 'item name wraps from the preceding layout row: ' + prev)
                        continue
                    d.add(pn, lno, ln, 'TOTALS' if re.search(r'Sub-Total|^\s*GST|Total inc|Amount Applied|Balance Due|^\s*Total', ln) else 'NARRATIVE')
                    if 'Page 3/4' in p and re.match(r'^\s{170,185}\S', ln) and not re.search(r'Sub-Total|GST|Total|Allgas|Slacks|Tel\.|qpower|ABN|Licence|PLEASE|TAX INVOICE|\d{2}/\d{2}/\d{4}|Part #|Service - Quoted|For electrical|Powered|Page|Amount Applied|Balance', ln):
                        prev = ln.strip()
        elif v == 'PLAYFORCE':
            hp = P[0][1]
            h.update(supplier='Play Force Australia Pty Ltd', abn='89 677 476 541', inv=re.search(r'Invoice Number\s+(INV-\d+)', hp).group(1), date=iso(re.search(r'\bDate\s+(\d{2}-\w{3}-\d{4})', hp).group(1).replace('-', ' ')),
                     due=iso(re.search(r'Due Date\s+(\d{2}-\w{3}-\d{4})', hp).group(1).replace('-', ' ')), ref=re.search(r'Reference\s+(\d+)', hp).group(1),
                     sub=D(re.search(r'Total \(Ex\. GST\)\s+\$ ?([\d,]+\.\d{2})', hp).group(1)), gst=D(re.search(r'GST \(10%\)\s+\$ ?([\d,]+\.\d{2})', hp).group(1)), tot=D(re.search(r'Total \(Inc\. GST\)\s+\$ ?([\d,]+\.\d{2})', hp).group(1)))
            def f(pn, no, ln):
                mm = re.match(r'^\s*(?P<q>\d+\.\d{2})\s+(?P<i>\S+)\s+(?P<d>.*?\S)\s{2,}(?P<u>[\d,]+\.\d{2})\s+(?P<a>[\d,]+\.\d{2})\s*$', ln)
                if mm: d.add(pn, no, ln, 'PRICED', qty=float(mm.group('q')), unit=float(D(mm.group('u'))), amt=float(D(mm.group('a'))), bands=['qty', 'unit_price', 'amount'])
                elif re.search(r'Total \(|GST \(10', ln): d.add(pn, no, ln, 'TOTALS')
                else: d.add(pn, no, ln, 'NARRATIVE')
            add_all(f)
        elif v == 'LEVAI':
            hp = P[0][1]
            h.update(supplier='T & H LEVAI PTY LTD', abn='65 100 395 480', inv=re.search(r'TAX INVOICE\s+(INV-\d+)', hp).group(1), date=iso(re.search(r'DATE\s+(\d+ \w+ \d{4})', hp).group(1)),
                     due=iso(re.search(r'DUE DATE\s+(\d+ \w+ \d{4})', hp).group(1)), ref=re.search(r'YOUR REF\s+(\d+)', hp).group(1),
                     sub=labelled(full, 'Subtotal'), gst=labelled(full, r'GST \(10%\)'), tot=labelled(full, r'^\s*(?:Account:.*?)?Total'))
            region = False
            for pn, p in P:
                for ln in p.splitlines():
                    lno += 1
                    if not ln.strip(): continue
                    if re.match(r'^\s*DESCRIPTION\s+AMOUNT', ln): region = True; d.add(pn, lno, ln, 'TABLE_HEADER'); continue
                    if re.search(r'Bank Details|Subtotal', ln): region = False
                    mm = re.match(r'^\s*(?P<d>.*?\S)\s{2,}(?P<a>[\d,]+\.\d{2})\s*$', ln) if region else None
                    if mm: d.add(pn, lno, ln, 'PRICED', qty=1.0, unit=float(D(mm.group('a'))), amt=float(D(mm.group('a'))), bands=['amount'])
                    elif re.search(r'Subtotal|GST \(10%\)|Total|Paid to Date|Balance Due', ln): d.add(pn, lno, ln, 'TOTALS')
                    else: d.add(pn, lno, ln, 'NARRATIVE')
        elif v == 'ELEMENTAL':
            hp = P[0][1]
            h.update(supplier='Elemental Shade Structures (Dice Canvas Pty Ltd ATF The Dice Trust & SSAR Australia Pty Ltd ATF The Mark West Trust)', abn='99 292 107 173', inv=re.search(r'Invoice No\.:\s+(\d+)', hp).group(1),
                     date=iso(re.search(r'Tax Invoice Date:\s+(\S+)', hp).group(1)), due=None, ref=re.search(r'PURCHASE ORDER (\d+)', hp).group(1),
                     sub=D(re.search(r'Total Excluding GST\s+\$([\d,]+\.\d{2})', hp).group(1)), gst=D(re.search(r'^\s*GST\s+\$([\d,]+\.\d{2})', hp, re.M).group(1)), tot=D(re.search(r'Total Including GST\s+\$([\d,]+\.\d{2})', hp).group(1)))
            def f(pn, no, ln):
                mm = re.match(r'^\s*(?P<d>.*?\S)\s{2,}(?P<u>[\d.]+)\s+(?P<q>\d+)\s+(?P<g>[\d.]+)\s+(?P<a>[\d.]+)\s*$', ln)
                if mm: d.add(pn, no, ln, 'PRICED', qty=float(mm.group('q')), unit=float(D(mm.group('u'))), amt=float(D(mm.group('a')) - D(mm.group('g'))), gst=float(D(mm.group('g'))), bands=['unit_price', 'qty', 'gst', 'amount'], note=f"printed Total column is GST inclusive ({mm.group('a')}); ex GST = Total less GST = unit price x quantity")
                elif re.search(r'Total Excluding|^\s*GST|Total Including|Payments Received|Invoice Balance', ln): d.add(pn, no, ln, 'TOTALS')
                else: d.add(pn, no, ln, 'NARRATIVE')
            add_all(f)
        elif v == 'AUSTSPRAY':
            p = P[0][1]; mm = re.search(r'Invoice Number: (\d+)\s+Order Number: (\d+) (PK ?\d{6})\s+Date: (\S+)', p)
            h.update(supplier='Austspray Environmental Weed Control Pty Ltd', abn='89 122 731 775', inv=mm.group(1), ref=mm.group(2), date=iso(mm.group(4)), due=None,
                     sub=labelled(p, 'Sub Total'), gst=labelled(p, r'G\.S\.T\.'), tot=labelled(p, r'^\s*Total'))
            buf = []; in_item = False; amt = None
            for ln in p.splitlines():
                lno += 1
                if not ln.strip(): continue
                if re.match(r'^\s*Item\s+Total\s*$', ln): in_item = True; d.add(d.pages[0], lno, ln, 'TABLE_HEADER'); continue
                if in_item and re.match(r'^\s*\$([\d,]+\.\d{2})\s*$', ln): amt = D(ln.strip()); buf.append(ln.strip()); continue
                if in_item and (ln.strip().startswith('Variations') or re.match(r'^\s*Sub Total', ln)):
                    in_item = False; d.add(d.pages[0], lno - len(buf), ' | '.join(buf), 'PRICED', qty=1.0, unit=float(amt), amt=float(amt), bands=['amount'], note='item block spans several layout rows; amount printed on its own row')
                    d.add(d.pages[0], lno, ln, 'NARRATIVE' if 'Variations' in ln else 'TOTALS'); continue
                if in_item: buf.append(ln.strip()); continue
                mv = re.match(r'^\s*(LZ\d-\d+.*?\S)\s{2,}\$(-?[\d,]+\.\d{2})\s*$', ln)
                if mv: d.add(d.pages[0], lno, ln, 'PRICED', qty=1.0, unit=float(D(mv.group(2))), amt=float(D(mv.group(2))), bands=['amount']); continue
                d.add(d.pages[0], lno, ln, 'TOTALS' if re.match(r'^\s*(Sub Total|G\.S\.T\.|Total)\s', ln) else 'NARRATIVE')
        elif v == 'HIGGINS':
            hp = P[0][1]
            h.update(supplier='Higgins Coatings Pty Ltd', abn='50 005 632 708', inv=re.search(r'Invoice\s+No\s+\+?\s*(\d+)', hp).group(1), date=iso(re.search(r'Invoice\s+Date\s+:\s+(\S+)', hp).group(1)),
                     due=iso(re.search(r'Due\s+Date\s+:\s+(\S+)', hp).group(1)), ref=re.search(r'Order Ref\s+:\s+(\S+)', hp).group(1),
                     sub=D(re.search(r'Invoice\s+Amount\s+:\s+([\d,]+\.\d{2})', hp).group(1)), gst=D(re.search(r'Plus\s+GST\s+:\s+([\d,]+\.\d{2})', hp).group(1)), tot=D(re.search(r'Total\s+including\s+GST\s+:\s+([\d,]+\.\d{2})', hp).group(1)))
            region = False
            for pn, p in P:
                for ln in p.splitlines():
                    lno += 1
                    if not ln.strip(): continue
                    if 'DESCRIPTION OF SUPPLY' in ln: region = True; d.add(pn, lno, ln, 'TABLE_HEADER'); continue
                    if 'Invoice' in ln and 'Amount' in ln: region = False
                    mm = re.match(r'^\s*(?P<d>.*?\S)\s{2,}(?P<a>[\d,]+\.\d{2})\s*$', ln) if region else None
                    if mm: d.add(pn, lno, ln, 'PRICED', qty=1.0, unit=float(D(mm.group('a'))), amt=float(D(mm.group('a'))), bands=['amount'])
                    elif re.search(r'Invoice\s+Amount|Plus\s+GST|Total\s+including', ln): d.add(pn, lno, ln, 'TOTALS')
                    else: d.add(pn, lno, ln, 'NARRATIVE')
        elif v == 'HARPLEY':
            hp = P[0][1]
            h.update(supplier='Harpley Services Pty Ltd', abn='22 162 601 694', inv=re.search(r'Invoice No\.:\s+(\d+)', hp).group(1), date=iso(re.search(r'Date:\s+(\d{2}/\d{2}/\d{4})', hp).group(1)),
                     due=iso(re.search(r'Due Date:\s+(\d{2}/\d{2}/\d{4})', hp).group(1)), ref=re.search(r'Purchase Order:\s+(\d+)', hp).group(1),
                     sub=D(re.search(r'Sub Total:\s+\$([\d,]+\.\d{2})', full).group(1)), tot=D(re.search(r'Total Inc GST:\s*\n?\s*\$?([\d,]+\.\d{2})', full).group(1)) if re.search(r'Total Inc GST:\s+\$([\d,]+\.\d{2})', full) else None)
            g = re.findall(r'^\s*\$([\d,]+\.\d{2})\s*$', full, re.M)
            h['gst'] = D(g[0]) if g else None
            if h['tot'] is None:
                h['tot'] = D(re.search(r'Balance due: \$([\d,]+\.\d{2})', full).group(1))
            def f(pn, no, ln):
                mm = re.match(r'^\s*(?P<q>\d+)\s+(?P<d>.*?\S)\s{2,}\$(?P<u>[\d,]+\.\d{2})\s+\$(?P<a>[\d,]+\.\d{2})\s*$', ln)
                if mm: d.add(pn, no, ln, 'PRICED', qty=float(mm.group('q')), unit=float(D(mm.group('u'))), amt=float(D(mm.group('a'))), bands=['qty', 'unit_price', 'amount'])
                elif re.search(r'Sub Total:|Total Inc GST|Payments Made|Balance Due|^\s*\$[\d,]+\.\d{2}\s*$', ln): d.add(pn, no, ln, 'TOTALS')
                else: d.add(pn, no, ln, 'NARRATIVE')
            add_all(f)
        elif v == 'KACHEL':
            hp = P[0][1]
            h.update(supplier='Kachel Cleaning', abn='77 083 786 592', inv=re.search(r'No\.(\d+)', hp).group(1), date=iso(re.search(r'Date: (\S+)', hp).group(1)), due=None, ref=re.search(r'Purchase Order No:\s+(\d+)', hp).group(1),
                     sub=D(re.search(r'SubTotal\s+([\d,]+\.\d{2})', hp).group(1)), gst=D(re.search(r'Plus 10% GST\s+([\d,]+\.\d{2})', hp).group(1)), tot=D(re.search(r'Total price including GST\. \$([\d,]+\.\d{2})', hp).group(1)))
            pkpend = None
            for ln in hp.splitlines():
                lno += 1
                if not ln.strip(): continue
                mm = re.match(r'^\s*(?P<d>Zone \d.*?:)\s+(?P<pk>PK\d{6})\s+(?P<a>[\d,]+\.\d{2})\s*$', ln)
                if mm: d.add(d.pages[0], lno, ln, 'PRICED', qty=None, unit=None, amt=float(D(mm.group('a'))), bands=['amount'], wo=mm.group('pk')); continue
                if re.match(r'^\s*PK\d{6}\s*$', ln): pkpend = ln.strip(); d.add(d.pages[0], lno, ln, 'NARRATIVE'); continue
                mm = re.match(r'^\s*(?P<d>Cleaning of sanitary bins.*?\S)\s{2,}(?P<a>[\d,]+\.\d{2})\s*$', ln)
                if mm: d.add(d.pages[0], lno, ln, 'PRICED', qty=None, unit=None, amt=float(D(mm.group('a'))), bands=['amount'], wo=pkpend, note='PK printed on the preceding row (Sanitary Bins block)'); continue
                d.add(d.pages[0], lno, ln, 'TOTALS' if re.search(r'SubTotal|Plus 10% GST|Total price', ln) else 'NARRATIVE')
    seen = {}; out = []
    for d in docs:
        h = d.h; key = (d.vendor, h['inv']); dup = seen.get(key); seen.setdefault(key, f'{h["inv"]}/pages{d.pages[0]}-{d.pages[-1]}')
        pr = [d.pages[0], d.pages[-1]]
        cap = sum(D(l['line_ex_gst']) for l in d.lines if l['line_type'] == 'PRICED')
        sname = {'ORIGIN': 'Origin', 'SEACRETE': 'Sea-Crete', 'POOLSHOP': 'Pool Shop', 'QPOWER': 'Q Power', 'PLAYFORCE': 'Play Force', 'FLAVELL': 'FlavellDau', 'LEVAI': 'Levai', 'WEIS': 'Weis', 'ELEMENTAL': 'Elemental', 'AUSTSPRAY': 'Austspray', 'HIGGINS': 'Higgins', 'HARPLEY': 'Harpley', 'C2C': 'C2C', 'KACHEL': 'Kachel'}[d.vendor]
        purpose = {'ORIGIN': 'electric', 'SEACRETE': 'waterpark', 'POOLSHOP': 'waterplay', 'QPOWER': 'electric', 'PLAYFORCE': 'playgrnd', 'FLAVELL': 'fencing', 'LEVAI': 'landscape', 'WEIS': 'softfall', 'ELEMENTAL': 'shade', 'AUSTSPRAY': 'landscap', 'HIGGINS': 'coatings', 'HARPLEY': 'plumbing', 'C2C': 'mowing', 'KACHEL': 'cleaning'}[d.vendor]
        assert h['tot'] is not None and h['sub'] is not None, (d.vendor, h)
        stem = f'{sname}, {purpose}, {dt.date.fromisoformat(h["date"]).strftime("%b-%Y")}, {h["tot"]:.2f}'
        assert len(stem) <= 40, stem
        gst_calc = D(h['sub'] * Decimal('0.1'))
        if h['gst'] is not None and h['gst'] != gst_calc: d.findings.append(f'Printed GST ${h["gst"]} differs from 10% of the subtotal ${gst_calc} by {abs(h["gst"] - gst_calc)}.')
        out.append(dict(doc_ref=f'{h["inv"]}/pages{pr[0]}-{pr[1]}', doc_kind='TAX_INVOICE', source_file='Mixed_new_26-27.pdf', page_range=pr, supplier=h['supplier'], supplier_abn=h['abn'], abn_source='letterhead',
                        invoice_no=h['inv'], invoice_date=h['date'], due_date=h.get('due'), printed_subtotal_ex_gst=float(h['sub']), subtotal_basis='printed', printed_gst=float(h['gst']) if h['gst'] is not None else None,
                        printed_total_incl_gst=float(h['tot']), captured_ex_gst=float(cap), line_amount_basis='ex_gst', tie_basis='ex_gst', self_tie='TIE' if cap == h['sub'] else 'OUT', retry_log=[], table_headers=[],
                        work_orders=h['pk'], contract_refs=h['contract'], po_refs=[h['ref']] if h.get('ref') and h['ref'] != NP else [], pk_refs=h['pk'], printed_account_codes=h['pk'], evidence_stem=stem, duplicate_of=dup,
                        findings=d.findings, notes=f'{d.vendor} template, raw-text route (pdftotext -layout), page text retained.', lines=d.lines, page_text=d.page_text, vendor_template=d.vendor))
    return out


if __name__ == '__main__':
    docs = parse()
    md5 = hashlib.md5(open(PDF, 'rb').read()).hexdigest()
    corpus = dict(manifest=dict(batch_id='mixed_new_26_27', source_files=[dict(file='Mixed_new_26-27.pdf', md5=md5, pages=75)], runtime='A', extraction_tool='parse_mixed_new.py raw-text route (pdftotext -layout, 13 vendor templates)',
                                extracted_utc=dt.datetime.now(dt.timezone.utc).isoformat(), prompt_version='v5 (raw-text fallback)', ocr_pages_run=0, ocr_pages_not_required=75, ocr_pages_not_available=0, ocr_pages_outstanding=0, resume_point=None), documents=docs)
    json.dump(corpus, open(os.environ.get('OUT', 'corpus_mixed_new_26_27_v6.json'), 'w'), indent=1)
    for d in docs:
        pl = [l for l in d['lines'] if l['line_type'] == 'PRICED']
        print(f"{d['invoice_no']:10} {d['vendor_template']:9} p{d['page_range']} sub {d['printed_subtotal_ex_gst']:>12,.2f} cap {d['captured_ex_gst']:>12,.2f} {d['self_tie']} priced {len(pl)} gst {d['printed_gst']} dup={d['duplicate_of']}")
