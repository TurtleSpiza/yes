"""pbr_capture.py - rule 16/17 capture of a gated corpus into branch-register rows (brief-driven, rule 20).

Inputs held as data: the GREEN corpus JSON (page text retained) and the match table JSON. Output: mutated register
rows (analysis block, green block cols 88-127) plus evidence structures the build writes to Evidence_Invoices,
Evidence_Invoice_Lines, EIL_Controls and Vendor_Boilerplate. Formulas for DQ:DT are generated after the sort.
"""
import collections, datetime as dt, json, re
from decimal import Decimal, ROUND_HALF_UP

D = lambda x: Decimal(str(x)).quantize(Decimal('0.01'), ROUND_HALF_UP)
NP = '(not printed)'; BL = '(blank as printed)'
STAMP = '11-Sep-2026, branch v2, Batch mixed_1 (raw-text route, corpus_mixed_1_v6.json)'
STAMPS = {'mixed_1': STAMP, 'mixed_new_26_27': '11-Sep-2026, branch v3, Batch mixed_new_26_27 (raw-text route, corpus_mixed_new_26_27_v6.json)',
          'attach_1': '11-Sep-2026, branch v4, Batch attach_1 (TechOne attachments, raw-text route, corpus_attach_1_v6.json)',
          'attach_2': '11-Sep-2026, branch v5, Batch attach_2 (TechOne attachments, raw-text route, corpus_attach_2_v6.json)',
          'code': '11-Sep-2026, branch v5, Batch code (code.pdf, supplied corpus prepared and fidelity-checked, corpus_code_v6.json)',
          'mix22': '11-Sep-2026, branch v6, Batch mix22 (mix 22.pdf, supplied corpus restated and fidelity-checked, corpus_mix22_v6.json)',
          'attach_3': '11-Sep-2026, branch v6, Batch attach_3 (TechOne attachments, raw-text route, corpus_attach_3_v6.json)',
          'mix222': '11-Sep-2026, branch v7, Batch mix222 (mix_222.pdf, raw-text route to extraction prompt v6, corpus_mix222_v6.json)',
          'binder11111': '11-Sep-2026, branch v7, Batch binder11111 (Binder11111.pdf, raw-text route to extraction prompt v6, corpus_binder11111_v6.json)',
          'pla073_1': '14-Sep-2026, branch v10, Batch pla073_1 (pla073 1.pdf, supplied corpus to extraction prompt v6, runtime A, corpus_pla073_1_v6.json)'}
BATCH_VER = {'mixed_1': 'v2', 'mixed_new_26_27': 'v3', 'attach_1': 'v4', 'attach_2': 'v5', 'code': 'v5', 'mix22': 'v6', 'attach_3': 'v6', 'mix222': 'v7', 'binder11111': 'v7', 'pla073_1': 'v10'}
SRCS = {'mixed_1': 'Mixed_1.pdf (md5 b9ddf7fd6c56188a22181921b7b2c8ab), Batch mixed_1, corpus_mixed_1_v6.json', 'mixed_new_26_27': 'Mixed_new_26-27.pdf (md5 813f23077d1d5e77fb1e7150ad08b3cc), Batch mixed_new_26_27, corpus_mixed_new_26_27_v6.json',
        'code': 'code.pdf, 66 pages (binder not supplied; supplied corpus corpus_code.json md5 e256555fc9d22d46a9cce80f8e7bbe3b, M365 Copilot layout extraction), Batch code, corpus_code_v6.json',
        'mix22': 'mix 22.pdf, 81 pages (binder not supplied; supplied corpus corpus_mix22.json md5 e6782e55b5379dc3adcb6a1b5c7cebd4, M365 Copilot layout extraction, gate RED as supplied), Batch mix22, corpus_mix22_v6.json',
        'pla073_1': 'pla073 1.pdf, 144 pages (binder not supplied; supplied corpus corpus_pla073_1_v6.json md5 8b9d6481fa8926c86d849d8e290106e3, M365 Copilot runtime A to extraction prompt v6, gate GREEN as supplied), Batch pla073_1, corpus_pla073_1_v6.json'}

CAT = {  # vendor template -> (Nature Category v2, v3 category, theme rule)
    'LEVAI': ('Natural areas & bushland works', 'Bushland, weeds & fire', 'P2 sighted job, dominant scope'),
    'TEC': ('Natural areas & bushland works', 'Bushland, weeds & fire', 'P2 sighted job, dominant scope'),
    'TREESCAPE': ('Contract mowing', 'Grounds, turf & vegetation', 'P2 sighted job, dominant scope'),
    'BUSHCARE': ('Natural areas & bushland works', 'Bushland, weeds & fire', 'P2 sighted job, dominant scope'),
    'AUSTSPRAY': ('Contract landscape maintenance', 'Grounds, turf & vegetation', 'P2 sighted job, dominant scope'),
    'EMU': ('Natural areas & bushland works', 'Bushland, weeds & fire', 'P2 sighted job, dominant scope'),
    'ACTIVECO': ('Natural areas & bushland works', 'Bushland, weeds & fire', 'P2 sighted job, dominant scope'),
    'GURU': ('Parks maintenance (contract/reactive)', 'Paths, courts, skate & hard surfaces', 'P2 sighted job, dominant scope'),
    'AUSTCARE': ('Natural areas & bushland works', 'Bushland, weeds & fire', 'P2 sighted job, dominant scope'),
    'GLASCOTT': ('Natural areas & bushland works', 'Bushland, weeds & fire', 'P2 sighted job, dominant scope'),
    'ORIGIN': ('Electricity supply', 'Utilities supply', 'P1 account governs'),
    'SEACRETE': ('Water park contract works', 'Water play & aquatic plant', 'P2 sighted job, dominant scope'),
    'POOLSHOP': ('Water park contract works', 'Water play & aquatic plant', 'P2 sighted job, dominant scope'),
    'QPOWER': ('Electrical & data services', 'Electrical, lighting & data', 'P2 sighted job, dominant scope'),
    'PLAYFORCE': ('Playground inspection & repair', 'Playground equipment & softfall', 'P2 sighted job, dominant scope'),
    'FLAVELL': ('Parks maintenance (contract/reactive)', 'Fencing, bollards, rails & gates', 'P2 sighted job, dominant scope'),
    'WEIS': ('Playground surfacing', 'Playground equipment & softfall', 'P2 sighted job, dominant scope'),
    'ELEMENTAL': ('Parks maintenance (contract/reactive)', 'Shade sails & shelters', 'P2 sighted job, dominant scope'),
    'HIGGINS': ('Parks maintenance (contract/reactive)', 'Painting & protective coatings', 'P2 sighted job, dominant scope'),
    'HARPLEY': ('Plumbing & water assets', 'Amenities buildings & plumbing', 'P2 sighted job, dominant scope'),
    'C2C': ('Contract mowing', 'Grounds, turf & vegetation', 'P2 sighted job, dominant scope'),
    'KACHEL': ('Cleaning & sanitary', 'Cleaning & pressure washing', 'P2 sighted job, dominant scope'),
    'ETSOL': ('Contract mowing', 'Grounds, turf & vegetation', 'P2 sighted job, dominant scope'),
    'GLASCOTT_LM': ('Contract landscape maintenance', 'Grounds, turf & vegetation', 'P2 sighted job, dominant scope'),
    'PROVAC': ('Cemetery operations', 'Cemetery operations', 'P2 sighted job, dominant scope'),
    'SAVCO': ('Tree operations', 'Trees & arboriculture', 'P2 sighted job, dominant scope'),
    'HERITAGE': ('Tree operations', 'Trees & arboriculture', 'P2 sighted job, dominant scope'),
    'BURLY': ('Contract landscape maintenance', 'Grounds, turf & vegetation', 'P2 sighted job, dominant scope'),
    'CERTIFIED': ('Contract mowing', 'Grounds, turf & vegetation', 'P2 sighted job, dominant scope'),
    'C2C_INCL': ('Contract mowing', 'Grounds, turf & vegetation', 'P2 sighted job, dominant scope'),
    'FLAVELL_ATT': ('Parks maintenance (contract/reactive)', 'Amenities buildings & plumbing', 'P2 sighted job, dominant scope'),
    'MPDT': ('Tree operations', 'Trees & arboriculture', 'P2 sighted job, dominant scope'),
    'HERITAGE_CN': ('Tree operations', 'Trees & arboriculture', 'P2 sighted job, dominant scope'),
    'PLAYFORCE_ATT': ('Playground inspection & repair', 'Playground equipment & softfall', 'P2 sighted job, dominant scope'),
    'PPG': ('Horticultural & landscape supplies', 'Materials & minor equipment', 'P1 account governs'),
    'VINTON': ('Tree operations', 'Trees & arboriculture', 'P2 sighted job, dominant scope'),
}
BPK = {'ORIGIN': 'ORG', 'SEACRETE': 'SC', 'POOLSHOP': 'PSH', 'QPOWER': 'QP', 'PLAYFORCE': 'PF', 'FLAVELL': 'FD', 'WEIS': 'WC', 'ELEMENTAL': 'ELM', 'HIGGINS': 'HIG', 'HARPLEY': 'INV', 'C2C': 'C2C', 'KACHEL': 'KC', 'LEVAI': 'LEV', 'TEC': 'TEC', 'TREESCAPE': 'TRS', 'BUSHCARE': 'BSH', 'AUSTSPRAY': 'ASP', 'EMU': 'EMU', 'ACTIVECO': 'ACT', 'GURU': 'GDW', 'AUSTCARE': 'ACE', 'GLASCOTT': 'GLA', 'GLASCOTT_LM': 'GLA', 'ETSOL': 'ETS', 'PROVAC': 'PRV', 'SAVCO': 'SAV', 'HERITAGE': 'HTS', 'BURLY': 'BUR', 'CERTIFIED': 'CER', 'C2C_INCL': 'C2C', 'FLAVELL_ATT': 'FD', 'MPDT': 'MPD', 'HERITAGE_CN': 'HTS', 'PLAYFORCE_ATT': 'PF', 'PPG': 'PPG', 'VINTON': 'VTS'}
PAY_RX = re.compile(r'BSB|\bAcc\b|Acc No|Account|Bank:|Bank\s|Name:|Please make all payments|Please remit|Payment can be made|Direct Deposit|Please include invoice|Please Mail Payment|Detach this section|Acc\. No|Acc\. Name', re.I)
TERM_RX = re.compile(r'Terms of Payment|Payment Terms|Payment Due On Receipt|fee of|Security of Payment|Credits cards|processing fee|View and pay online|Please pay the total|questions concerning|THANK YOU|Net30|Net 30|View online', re.I)


def first(rx, text, default=NP, flags=re.M):
    m = re.search(rx, text, flags)
    return m.group(1).strip() if m else default


def date_out(iso):
    return dt.date.fromisoformat(iso).strftime('%d-%b-%Y') if iso else NP


def header_fields(d):
    """Printed header fields per template, from the retained page text. Blank-as-printed where the label is there and empty."""
    t = '\n'.join(d['page_text'][k] for k in sorted(d['page_text'], key=int))
    v = d['vendor_template']; f = {}
    if v == 'LEVAI':
        f.update(addr='41 Industrial Ave, LOGAN VILLAGE QLD 4207, AUSTRALIA', phone='Office: (07) 3803 0032; Email: admin@thlevai.com', po=first(r'YOUR REF\s+(\d+)', t),
                 bill='Logan City Council, 150 Wembley Rd, PO Box 3226, LOGAN CENTRAL QLD 4114, AUSTRALIA', officer='Jamie Fisher (Fire Management)', site='Spring Mountain Reserve (Ref: 35715)',
                 work='Bush Track Repair & Drainage Works; Completed - 29.06.2026', contract=NP, paid=first(r'Paid to Date\s+([\d,]+\.\d{2})', t), bal=first(r'Balance Due\s+([\d,]+\.\d{2})', t))
    elif v == 'TEC':
        f.update(addr='PO Box 14, JIMBOOMBA QLD 4280, AUSTRALIA', phone='E: admin@totalenviro.net.au; Peter Sands 0402 644380, peters@totalenviro.net.au', po=first(r'Reference\s*\n[^\n]*?\b(PO#?:? ?\d{6})', t),
                 bill='Logan City Council, PO Box 3226, LOGAN CITY DC QLD 4114, AUSTRALIA', officer=NP, site='Lyndale Reserve' if d['invoice_no'] == '3597' else 'Norman Drive',
                 work='Fire Access Line creek crossing & track upgrades, Separable Portion 13 PAR/334/2023 SP13, QU-1193' if d['invoice_no'] == '3597' else 'Norman Drive Weed Management and Rehabilitation',
                 contract='PAR/334/2023 SP13; QU-1193' if d['invoice_no'] == '3597' else NP, paid=NP, bal=NP)
    elif v == 'TREESCAPE':
        f.update(addr='PO Box 275 ELLEN GROVE QLD 4078 AUSTRALIA', phone='Tel: +64-7-34574300; Fax: +64-7-32713410; Email: accounts@treescape.net.au; Aaron.Fritz@treescape.net.au', po=first(r'Order No : (\d+)', t),
                 bill='Logan City Council, PO Box 3226, Logan City DC 4114; Atten: JAMIE FISHER; Account No. LOGCIT', officer='Aaron Fritz (Your Contact Is)', site='Mowing contract - Logan - Q1GSL21074, PAR/334/2023, PK000373',
                 work='Mowing contract - Logan - Q1GSL21074; PAR/334/2023; Year 3; Round 4 - Apr/May; Please see spreadsheet for cost breakdown. Our Job No 210740101; Project Code 21074', contract='PAR/334/2023', paid=NP, bal=first(r'Total Payable\s*\n?.*?\$([\d,]+\.\d{2})', t, flags=re.S))
    elif v == 'BUSHCARE':
        f.update(addr='7-9 Fletcher Rd, BETHANIA QLD 4205', phone='07 3133 4243; admin@bushcare.com.au; www.bushcare.com.au', po=first(r'(?:P\s*O\s*NUMBER|O NUMBER)\s*\n?\s*(\d{6})', t),
                 bill='Logan City Council, PO Box 3226, LOGAN CITY DC QLD 4114', officer=NP,
                 site=first(r'^\s*(Logan Reserve Riverside Parkland)\s*$', t) if d['invoice_no'] == '18709' else 'Multiple parks, one printed per line (see line items)',
                 work=' | '.join(x.strip() for x in re.findall(r'^\s*((?:Contract|Cost (?:Account|Code)|CRN|SP\d|Annual Maintenance|Woody weed|9th|July 2026|August ?2026|Annual)[^\n]*)$', t, re.M)[:8]),
                 contract=first(r'Contract:\s*(PAR\S+)', t), paid=NP, bal=first(r'BALANCE D\s?U\s?E\s+A\$([\d,]+\.\d{2})', t))
        if d['invoice_no'] == '18709': f['work'] = 'Contract: PAR/334/2023; Cost Account: PK000375; CRN: (blank as printed); SP9; Logan Reserve Riverside Parkland; Woody weed & vine treatment; 9th, 22nd, 30th June 2026'
    elif v == 'AUSTSPRAY':
        f.update(addr='PO Box 794, Helensvale QLD 4212', phone='07 5580 4851; admin@austspray.com', po=first(r'Order Number: (\d+)', t),
                 bill='Logan City Council - Sara Pryor, PO Box 3226, Logan City Queensland 4114', officer='Sara Pryor (customer contact)', site=first(r'^\s*(Logan Zone \d)\s*$', t),
                 work=' '.join(x.strip() for x in re.findall(r'^\s*(Landscape Maintenance[^\n]*|PAR/338A/2025[^\n]*|PK\d{6} Parks/Roads[^\n]*)$', t, re.M)), contract='PAR/338A/2025', paid=NP, bal=NP)
    elif v == 'EMU':
        f.update(addr='17 Creswick Pl, BIRKDALE QLD 4159, AUSTRALIA', phone='admin@teamemu.com.au', po=first(r'CON Order Number: CON# (\d+)', t),
                 bill='Logan City Council, 138-158 Wembley Rd, LOGAN CENTRAL QLD 4114, AUSTRALIA, ABN: 21 627 796 435', officer=first(r'Requesting Officer: ([^\n]+)', t),
                 site='Multiple parks, one printed per line (see line items)', work=first(r'Work description: ([^\n]+(?:\n[^\n]*DRS)?)', t).replace('\n', ' '), contract=first(r'Contract Number: (\S+)', t), paid=NP, bal=NP)
    elif v == 'ACTIVECO':
        f.update(addr='2/47 Cook Ct, NORTH LAKES 4509, AUSTRALIA', phone=NP, po=first(r'Purchase Order No:\s*\n?\s*(\d{6})', t),
                 bill='Logan City Council, PO BOX 3226, LOGAN CITY DC QLD 4114, AUSTRALIA., ABN: 21 627 796 435', officer=NP, site='Multiple parks, one printed per line (see line items)',
                 work='Schedule Maintenance Treatments (AMP5); CREDITOR ID: ACT028; Contract Ref: PAR334S2023; Separable Portion 5', contract='PAR334S2023 Separable Portion 5', paid=NP, bal=NP)
    elif v == 'GURU':
        f.update(addr=NP, phone='m: 0451 959 421; e: gurudirtworks@outlook.com' + ('; +61 430441616' if 'Bill to' in t else ''), po='PO717368',
                 bill='Logan City Council, 177 Chambers Flat Rd, MARSDEN QLD 4132' + (', einvoicing@logan.qld.gov.au, 07 34123412' if 'Bill to' in t else ', AUSTRALIA'),
                 officer='Peter Salisnew - Parks Communities Officer', site='Underwood Park, Priestdale', work='XCO#3 Mountain Bike Trail Maintenance; PO717368 Cost Account PK000381', contract=NP, paid=NP, bal=first(r'Amount due\s+\$([\d,]+\.\d{2})', t))
    elif v == 'AUSTCARE':
        f.update(addr='HEAD OFFICE 234 Newnham Road, Upper Mt Gravatt, Queensland 4122', phone='T 1300 138 096; F (07) 3420 3093; E admin@austcare.net.au; W www.austcare.net.au',
                 po=', '.join(sorted(set(re.findall(r'\b(?:70\d{4}|80\d{4})\b', t)))), bill='Logan City Council, 177 Chambers Flat Road, Marsden Qld 4132', officer=first(r'Site Contact:\s+([^\n]+?)\s{2,}|Site Contact:\s+([^\n]+)$', t),
                 site='Multiple parks, one printed per line (see line items)', work=first(r'Description\s*\n\s*(Portion \d[^\n]*\n[^\n]*)', t).replace('\n', '; '), contract=NP, paid=first(r'Amount Applied\s+\$([\d,]+\.\d{2})', t), bal=first(r'Balance Due\s+\$([\d,]+\.\d{2})', t))
        f['officer'] = 'Site Contact: Lisa Hodgson; Salesperson: ' + first(r'Salesperson:\s+([^\n]+)', t)
    elif v == 'GLASCOTT':
        f.update(addr='29 Computer Road, Yatala QLD 4207 (letterhead: Technigro)', phone='Phone: 02 9429 8500; Email: ar@glascott.com.au', po=first(r'Order Ref\s+:\s+(\d+)', t),
                 bill='Logan City Council, 150 Wembley Road, Logan Central QLD 4114', officer='Attention: Lisa Hodgson', site='Multiple parks, one printed per attached schedule row',
                 work=first(r'(Natural\s?Areas Maintenance of Portion \d, Rotation \d)', t) + '; ' + first(r'(Treatment date: [^\n]+)', t) + '; Please refer to attached sheet for details.', contract=NP, paid=NP, bal=NP)
    elif v == 'ORIGIN':
        f.update(addr='Origin Energy Electricity Limited, GPO Box 3125, Sydney NSW 2001 (payment address)', phone='13 23 34; originenergy.com.au', po=NP,
                 bill='LOGAN CITY COUNCIL, PO BOX 3226, LOGAN CITY DC QLD 4114; Customer ABN 21 627 796 435; Account No. ' + first(r'Account No\.\s*\n\s*(\d+)', t) + '; Agreement No. ' + first(r'Agreement No\.\s*\n\s*(\d+)', t),
                 officer=NP, site='Consolidated invoice, ' + first(r'(\d+)\s+\d+\s+\d+\s*\n\s*Metering', t) + ' sites (one printed per line); Parks carries Logan Garden Park, Civic Parade, Logan Central QLD 4114 (NMI QB10790446 8, account 50002940795)',
                 work='Your Business Electricity Tax Invoice; consolidated invoice summary: Energy, Network, Regulated, Environmental, Metering, Retail Service charges; Additional Charges, Credits & Adjustments', contract=NP, paid=NP, bal=first(r'TOTAL OUTSTANDING[^$]*\$([\d,]+\.\d{2})', t, flags=re.S))
    elif v == 'SEACRETE':
        f.update(addr='PO BOX 1034, Coolangatta, 4225, QLD.', phone='0407374125; gregbeer02@gmail.com; http://seacrete.com.au', po=NP, bill='Logan city council', officer=NP,
                 site=first(r'^\s*(Logan garden water park|.*?water park)', t, NP), work=first(r'Code\s+Description[^\n]*\n\s*(.+?)\s{2,}\d+\s+\$', t), contract=NP, paid=first(r'Paid\s+\$([\d,]+\.\d{2})', t), bal=first(r'Balance Due\s+\$([\d,]+\.\d{2})', t))
    elif v == 'POOLSHOP':
        f.update(addr='233 Ernest Street, Lota QLD 4179', phone='Jon 0407 766 860; operations@poolshopqld.com.au', po=first(r'Reference\s*\n\s*(\d{6})', t) if 'Bill to' not in t else first(r'(\d{6})\s*$', t.split('Reference')[1].split('View')[0]),
                 bill='Logan City Council, 138-158 Wembley Rd, LOGAN CENTRAL QLD 4114, ABN: 21 627 796 435', officer=NP, site='Multiple water play sites, one printed per line (see line items)', work='Monthly water play maintenance and chemicals', contract=NP, paid=NP, bal=first(r'Amount due\s+\$([\d,]+\.\d{2})', t))
    elif v == 'QPOWER':
        f.update(addr='8/27 Allgas Street, Slacks Creek QLD 4127', phone='Tel. 07 3155 4225; qpower.com.au; Licence # 69807', po=first(r'Order No\.:\s+(\d+)', t), bill='Logan City Council, PO Box 3226, Logan City DC QLD 4114', officer=first(r'^\s*(.+?)\s*\n\s*Service Estimator', t),
                 site=first(r'Site:\s+(.+?)\s*\n\s*(?:.*?)\s*Site Address:\s+(?:.+)', t) + '; ' + first(r'Site Address:\s+(.+)', t), work=first(r'Description\s*\n\s*(\d{4}-\d+ - .+)', t), contract=NP, paid=first(r'Amount Applied\s+\$([\d,]+\.\d{2})', t), bal=first(r'Balance Due\s+\$([\d,]+\.\d{2})', t))
    elif v == 'PLAYFORCE':
        # the description block prints Contact, Account (the PK), Contract, Date Completed and a work-order site row
        # that wraps its "(Ref: nnnnn)" onto the next layout row. Both layout variants are read here.
        blk = [' '.join(x.split()) for x in re.findall(r'^\s{20,}(\S.*?)\s*$', t, re.M)]
        joined = []
        for x in blk:
            if joined and joined[-1].endswith('(Ref:'):
                joined[-1] += ' ' + x
            else:
                joined.append(x)
        site_rows = [x for x in joined if re.match(r'^\d{6,7} - [A-Z]{2,5} - ', x)]
        f.update(addr='41 Industrial Ave, Logan Village QLD 4207', phone='Office: (07) 3803 1788; Email: team@playforce.com.au; Web: playforce.com.au', po=first(r'Reference\s+(\d+)', t), bill='Logan City Council, 150 Wembley Rd, Logan Central QLD 4114, Australia',
                 officer=first(r'Contact:\s+(.+)', t),
                 site='; '.join(re.sub(r'^\d{6,7} - [A-Z]{2,5} - ', '', x) for x in site_rows) or NP,
                 work=' | '.join(x for x in joined if re.match(r'^(Contact|Account|Contract|Date Completed|\d{6,7} - [A-Z]{2,5} - |\(Ref)', x)),
                 contract=first(r'Contract:\s+(\S+)', t), paid=NP, bal=NP)
        acc = [x.replace('Account: ', '') for x in joined if x.startswith('Account: ') and x != 'Account: 10367833']
        f['printed_account'] = acc[0] if acc else NP
        f['crwo'] = '; '.join(x.split(' - ')[0] for x in site_rows) or NP
    elif v == 'FLAVELL':
        f.update(addr='PO Box 5202, DAISY HILL QLD 4127', phone=first(r'(accounts@f82landscaping\.com\.au)', t) + ('; +61 0478186497' if '0478186497' in t else ''), po=first(r'PO#\s?(\d+)', t), bill='Logan City Council', officer=NP,
                 site=first(r'Reference\s*\n\s*(.+?)\s*\n\s*(?:Park|ABN)', t) if 'Bill to' not in t and 'einvoicing' not in t else first(r'CR# \d+ (.+?)\s*$', t), work=first(r'Reference\s*\n\s*(.+?)\s*\n', t) if 'einvoicing' not in t else first(r'(CR# \d+ .+?)\s*$', t), contract=NP, paid=NP, bal=first(r'Amount [Dd]ue\s+\$?([\d,]+\.\d{2})', t))
    elif v == 'WEIS':
        f.update(addr='22 Crestview St, LOGANLEA QLD 4131, AUSTRALIA', phone='christine@weiscontractors.com.au' + ('; +61 433 824 633' if '433 824 633' in t else ''), po=first(r'P/O # (\d+)', t), bill='Logan City Council, PO Box 3226, LOGAN CITY DC QLD 4114, AUSTRALIA', officer=('nakitabishop@logan.qld.gov.au' if 'nakitabishop' in t else NP),
                 site=first(r'(CR - Division \d+)', t), work=first(r'(Supply labour and equipment to machine clean sand soft[\s\S]*?cleaning)', t).replace('\n', ' '), contract=first(r'Contract # (\S+)', t), paid=NP, bal=first(r'Amount [Dd]ue\s+\$?([\d,]+\.\d{2})', t))
        f['work'] = ' '.join(f['work'].split())
    elif v == 'ELEMENTAL':
        f.update(addr='Unit 9 /1 Belvedere Drive Park Ridge brisbane 4215', phone='Phone: 32002914; info@elementalshades.com; QBSA #1159300', po=first(r'PURCHASE ORDER (\d+)', t), bill='Logan City Council, 34125595, 150 Wembly Rd Logan Central, Brisbane QLD 4114', officer=first(r'Requesting Officers - (.+?)\s{2,}', t),
                 site='Multiple sites (shade structures on sites with multiple / single shade structures)', work='2026- Shade sail inspections; Contract Reference LB304', contract='LB304', paid=first(r'Payments Received\s+\$([\d,]+\.\d{2})', t), bal=first(r'Invoice Balance\s+\$([\d,]+\.\d{2})', t))
    elif v == 'HIGGINS':
        f.update(addr='PO Box 272, Port Melbourne, VIC 3207, Australia', phone='Phone: 03 9646 9999; Fax: 03 9646 5333', po=first(r'Order Ref\s+:\s+(\S+)', t), bill='LOGAN CITY COUNCIL, melinaturpin@logan.qld.gov.au, 150 WEMBLEY ROAD, LOGAN CENTRAL, QLD 4114, Email: einvoicing@logan.qld.gov.au; Debtor Code QR6891',
                 officer='melinaturpin@logan.qld.gov.au (bill-to contact)', site=first(r'Works 100% completed\s*\n\s*(.+?)\s{2,}', t), work=first(r'Job: (.+?)\s*$', t) + '; ' + first(r'Works 100% completed\s*\n\s*.+?\s{2,}(.+?)\s{2,}[\d,]+\.\d{2}', t), contract=NP, paid=NP, bal=NP)
    elif v == 'HARPLEY':
        f.update(addr='PO Box 126, Kingston QLD 4114', phone='0421 213 216; A.C.N. 162 601 694', po=first(r'Purchase Order:\s+(\d+)', t), bill='Logan City Council, Po Box 3226, Logan City DC QLD 4114; Ship To: Logan City Council, Parks Depot, 177 Chambers Flat Road, Marsden QLD 4132',
                 officer=first(r'Requesting Officer:\s+(.+?)\s*$', t), site=first(r'Site Details:\s+(.+?)\s*$', t), work=first(r'Work Description:\s+(.+?)\s*$', t) + ' ' + first(r'Work Description:[^\n]*\n\s{15,}(\S.+?)\s*$', t, ''), contract=first(r'Contract #:\s+(\S+)', t), paid=first(r'Payments Made:\s+\$([\d,]+\.\d{2})', t), bal=first(r'Balance Due:\s+\$([\d,]+\.\d{2})', t))
        f['request_date'] = first(r'^\s+Date:\s+(\S+)', t); f['via'] = first(r'Via:\s+(\S+)', t); f['crwo'] = first(r'CR/WO#:\s*(\S*)\s*$', t, BL) or BL; f['site_contact'] = first(r'Site Contact:\s+(.+?)\s*$', t); f['technician'] = first(r'Technician:\s*(\S.*?)\s*$', t, BL) or BL
    elif v == 'C2C':
        f.update(addr='35 Leahy Road, CABOOLTURE QLD 4510, AUSTRALIA', phone='0437 777 141; admin@c2cgg.com; +61 437777141', po=first(r'Purchase Order:\s+(\d+)', t), bill='Logan City Council (LCC) Parks Depot, 177 Chambers Flat Road, Marsden Qld 4132, einvoicing@logan.qld.gov.au', officer=NP,
                 site=first(r'(MZ\d+ STANDARD GROWTH - CUT \d)', t), work=first(r'(MZ\d+ STANDARD GROWTH - CUT \d)', t) + '; Vendor No: COA030; ' + first(r'(Reference: PAR/\S+)', t), contract=first(r'Reference: (PAR/\S+)', t), paid=NP, bal=first(r'Amount due\s+\$([\d,]+\.\d{2})', t))
    elif v == 'KACHEL':
        f.update(addr=NP, phone='Mobile: 0408 846964; Email:kachelcleaning@live.com.au', po=first(r'Purchase Order No:\s+(\d+)', t), bill='To CEO, Logan City Council, Wembley Road, WOODRIDGE QLD 4114', officer=NP, site='Zone 1 and Zone 2 toilets and BBQs; sanitary bins',
                 work=first(r'(Cleaning of the Public Facilities and Sanitary Bins for Contract No\s*\n?\s*PAR/377/2025 for the month of \w+ 2026\.)', t).replace('\n', ' '), contract='PAR/377/2025', paid=NP, bal=NP)
        f['work'] = ' '.join(f['work'].split())
    elif v == 'BURLY':
        f.update(addr='PO BOX 206, Biggera Waters, QLD 4216', phone='0420 371 884; accounts@burlyholdings.com.au', po=first(r'Order#\s*(\d+)', t),
                 bill='Accounts Payable, Logan City Council, 150 Wembley Road, Logan Central, QLD 4114', officer=first(r'(Attention [^\n]+?)\s*$', t),
                 site=' '.join(first(r'JOB ADDRESS:\s*\n(.+?\n.+?)\s*$', t, NP, re.M | re.S).split()),
                 work='; '.join(' '.join(x.split()) for x in re.findall(r'^\s*((?:Landscape Maintenance as per Fixed Fee[^\n]*|Attention [^\n]+|PK\d{6}|Order# \d+))\s*$', t, re.M)),
                 contract=first(r'(Fixed Fee #[\d.]+)', t), paid=first(r'PAID:\s+\$([\d,]+\.\d{2})', t), bal=first(r'BALANCE DUE:\s+\$([\d,]+\.\d{2})', t))
    elif v == 'CERTIFIED':
        f.update(addr='22-42 Seaview Rd, Mount Cotton QLD 4165', phone=NP, po=first(r'PO # (\d+)', t),
                 bill='Logan City Council - Mowing Services, Po Box 3226, 4114 QLD, AUSTRALIA, ABN: 21 627 796 435', officer=NP,
                 site='; '.join(' '.join(x.split()) for x in re.findall(r'^\s*(MZ\d+ Grass Cutting[^\n]*)\s*$', t, re.M)) or NP,
                 work='; '.join(' '.join(x.split()) for x in re.findall(r'^\s*((?:MZ\d+ Grass Cutting[^\n]*|Standard Growth[^\n]*|High Growth[^\n]*|Main roads PK\d{5,6}[^\n]*|Parks/[Rr]oads PK\d{5,6}[^\n]*|NOTE: this invoice includes[^\n]*|Partial deletion[^\n]*))\s*$', t, re.M)),
                 contract=NP, paid=NP, bal=NP)
    elif v == 'C2C_INCL':
        f.update(addr='35 Leahy Road, CABOOLTURE QLD 4510, AUSTRALIA', phone='0437 777 141', po=first(r'Purchase Order:\s+(\d+)', t),
                 bill='Logan City Council (LCC) Parks Depot, 177 Chambers Flat Road, MARSDEN QLD 4132', officer=NP,
                 site=first(r'^\s*(MZ\d+ (?:HIGH|STANDARD) GROWTH - CUT \d)\b', t),
                 work='; '.join(' '.join(x.split()) for x in re.findall(r'^\s*((?:Purchase Order: \d+|Vendor No: \S+|Reference: PAR\S+|Contract Reference: \S+|MZ\d+ (?:HIGH|STANDARD) GROWTH - CUT \d|\$[\d,]+\.\d{2} plus GST|FUEL LEVY SURCHARGE|INV-\d+ MZ\d+ [A-Z]{2} \d:[^\n]*|= \$[\d,]+\.\d{2}))\s*$', t, re.M)),
                 contract=first(r'Reference: (PAR/\S+)', t), paid=NP, bal=first(r'Amount Due\s+([\d,]+\.\d{2})', t))
    elif v == 'FLAVELL_ATT':
        f.update(addr='PO Box 5202, DAISY HILL QLD 4127', phone=NP, po=first(r'PO#\s?(\d+)', t), bill='Logan City Council', officer=NP,
                 site=' '.join(first(r'Reference\s*\n(.+?)\n\s*ABN', t, NP, re.S).split()),
                 work='; '.join(' '.join(x.split()) for x in re.findall(r'^((?:Remove roof sheets[^\n]*|Replace rotten[^\n]*|Reinstall shelter[^\n]*|PO# \d+|PK\d{6}))', t, re.M)),
                 contract=NP, paid=NP, bal=first(r'Amount Due\s+([\d,]+\.\d{2})', t))
    elif v == 'ETSOL':
        f.update(addr='PO Box 7960, Gold Coast Mail Centre, Queensland 9726', phone=NP, po=first(r'Purchase Order Number:\s*(\d+)', t), bill='Logan City Council, PO Box 3226, Logan City DC, QLD 4114',
                 officer=first(r'(Attn: [^\n]+?)\s*$', t), site='Multiple parks, one printed per line (MZ1 site codes, Mowing Zone 1)',
                 work='; '.join(x.strip() for x in re.findall(r'^\s*((?:PAR/336/2024 Zonal Mowing Services[^\n]*|Growth Parks|Round \d|Started [\d.]+|Completed [\d.]+|PK\d{6} \(Parks/Roads\)[^\n]*))\s*$', t, re.M)),
                 contract='PAR/336/2024', paid=NP, bal=NP)
    elif v == 'GLASCOTT_LM':
        f.update(addr='29 Computer Road, Yatala QLD 4207 (letterhead: Technigro)', phone='Phone: 02 9429 8500; Email: ar@glascott.com.au', po=first(r'Order Ref\s+:\s+(\d+)', t),
                 bill='Logan City Council, 150 Wembley Road, Logan Central QLD 4114', officer=NP, site='Zone 3 (landscape maintenance zone; no park named)',
                 work='; '.join(x.strip() for x in re.findall(r'^\s*((?:Contract PAR\d{3}[A-Z]\d{4}|Zone \d Landscape Maintenance[^\n]*|of \w+ 20\d\d, as per claim\.))', t, re.M)),
                 contract=first(r'Contract (PAR\d{3}[A-Z]\d{4})', t), paid=NP, bal=NP)
    elif v == 'PROVAC':
        f.update(addr='Po Box 3662, Helensvale 4212', phone='Ph: 1300 734 772; accounts@provac.net.au; Leanne@provac.net.au', po=first(r'Reference[\s\S]*?\n\s*(\d{6})\s*$', t),
                 bill=first(r'(Logan City Council #\d+)', t), officer=first(r'(ATTENTION [^\n]+?)\s*$', t), site=first(r'^\s*(Beenleigh Cemetery)\s*$', t),
                 work='; '.join(x.strip() for x in re.findall(r'^\s+((?:\d{2}/\d{2}/\d{4}|Hire Docket [^\n]+|Beenleigh Cemetery|Plot: \S+|PK\d{6}|KEPU))\s*$', t, re.M)), contract=NP, paid=NP, bal=first(r'Amount Due\s+([\d,]+\.\d{2})', t))
        f['work'] = 'Grave Dig; ' + f['work']
    elif v == 'SAVCO':
        f.update(addr='134 BRIGGS RD, RACEVIEW QLD 4305', phone='+61732888800; accounts@savco.com.au; www.savco.com.au', po=first(r'^\s*(PO\d{6})\s*$', t),
                 bill='Accounts, LOGAN CITY COUNCIL, PO BOX 3226, LOGAN CITY DC QLD 4114, ABN 21627796435; Ship to: Accounts, LOGAN CITY COUNCIL, 150 WEMBLEY RD, LOGAN CENTRAL QLD 4114', officer=NP,
                 site=first(r'WORK WAS CARRIED OUT IN ([^\n]+?)\s*$', t), work='; '.join(x.strip() for x in re.findall(r'^\s*((?:CUSTOMER REQUEST NUMBER[^\n]*|PK\d{6} - CONTRACT NUMBER[^\n]*|VEGETATION|WORK WAS CARRIED OUT[^\n]*|AS PER QUOTE|AND STUMP GRINDER[^\n]*))\s*$', t, re.M)) + '; TERMS NET 14',
                 contract=first(r'CONTRACT NUMBER - (PAR/\d{3}/\d{4})', t), paid=NP, bal=first(r'BALANCE DUE\s*\n\s*(A\$[\d,]+\.\d{2})', t))
        f['crwo'] = first(r'(CR#\d+)', t)
    elif v == 'VINTON':
        f.update(addr=NP, phone='admin@vintontreeservices.com.au (remittance address); no letterhead address prints',
                 po=first(r'PO:\s+(\d+)', t), bill='Logan City Council, A/C Payable Department, PO Box 3226, Logan City DC QLD 4114',
                 officer=first(r'Attention:\s*\n\s*(\S.+?)\s*$', t),
                 site=first(r'^\s{10,}(\d+[\w \-/,]+(?:Street|St|Road|Rd|Drive|Dr|Court|Ct|Avenue|Ave|Parade|Crescent|Way|Place|Pl|Highway|Hwy)[^\n]*)$', t),
                 work='; '.join(' '.join(x.split()) for x in re.findall(r'^\s*((?:CR ?#\s?\d+[^\n]*|Completed \d{2}/\d{2}/\d{4}|Provide [^\n]+|Remove [^\n]+|Stump grind[^\n]*|Supply [^\n]+|Prune [^\n]+))\s*$', t, re.M)),
                 contract=first(r'(PAR/\d{3}[A-Z]?/\d{4})', t), paid=NP, bal=first(r'Balance Due:\s+\$([\d,]+\.\d{2})', t))
        f['crwo'] = first(r'(CR ?#\s?\d+)', t)
    elif v == 'PLAYFORCE_ATT':
        blk = [' '.join(x.split()) for x in re.findall(r'^\s{20,}(\S.*?)\s*$', t, re.M)]
        joined = []
        for x in blk:
            if joined and joined[-1].endswith('(Ref:'):
                joined[-1] += ' ' + x
            else:
                joined.append(x)
        site_rows = [x for x in joined if re.match(r'^\d{6,7} - [A-Z]{2,5} - ', x)]
        f.update(addr='41 Industrial Ave, Logan Village QLD 4207', phone='Office: (07) 3803 1788; Email: team@playforce.com.au; Web: playforce.com.au',
                 po=first(r'Reference\s+(\d+)', t), bill='Logan City Council, 150 Wembley Rd, Logan Central QLD 4114, Australia',
                 officer=first(r'Contact:\s+(.+)', t),
                 site='; '.join(re.sub(r'^\d{6,7} - [A-Z]{2,5} - ', '', x) for x in site_rows) or NP,
                 work=' | '.join(x for x in joined if re.match(r'^(Contact|Account|Contract|Date Completed|\d{6,7} - [A-Z]{2,5} - |\(Ref)', x)),
                 contract=first(r'Contract:\s+(\S+)', t), paid=NP, bal=first(r'Total \(Inc\. GST\)\s+\$\s?([\d,]+\.\d{2})', t))
        acc = [x.replace('Account: ', '') for x in joined if x.startswith('Account: ') and x != 'Account: 10367833']
        f['printed_account'] = acc[0] if acc else NP
        f['crwo'] = '; '.join(x.split(' - ')[0] for x in site_rows) or NP
    elif v == 'PPG':
        f.update(addr='McNaughton Road, Clayton VIC 3168, AUSTRALIA', phone='TEL: (03)92636000; FAX: (03)92636993',
                 po=first(r'Customer Reference\s*\n\s*(\d{6})', t),
                 bill='LOGAN CITY COUNCIL, WEMBLEY ROAD, LOGAN CENTRAL Queensland 4114, AUSTRALIA; Customer Number ' + first(r'Customer Number\s*\n\s*(\d+)', t),
                 officer='Salesperson: ' + first(r'Salesperson:\s+(.+?)\s*$', t),
                 site='LOGAN CITY COUNCIL, WEMBLEY ROAD, LOGAN CENTRAL Queensland 4114 (ship to)',
                 work='; '.join(' '.join(x.split()) for x in re.findall(r'^\s*((?:Delivery Docket:[^\n]*|POS Order No:[^\n]*|PPG Order No[^\n]*|Ship Date:[^\n]*|\s*\d+\s+\d{8}\s+ReasonCode:[^\n]*|\s*MIXED MERCHANDSE))\s*$', t, re.M)),
                 contract=NP, paid=NP, bal=first(r'INVOICE TOTAL\s+([\d,]+\.\d{2})', t))
    elif v == 'MPDT':
        f.update(addr='PO Box 158, MOSSMAN QLD 4873', phone='07 4098 8264; accounts@mpdt.com.au', po=first(r'Reference\s*\n[^\n]*?\b(7\d{5})\b', t),
                 bill='Logan City Council, Attention: Aisha Wilson, 150 Wembley Road, LOGAN CENTRAL QLD 4114', officer=first(r'(Attention: [^\n]+?)\s*$', t),
                 site=first(r'Reference\s*\n[^\n]*?7\d{5} - ([^\n]+?)\s*$', t) + first(r'^\s*Reference\s*\n(?:[^\n]*\n){2}\s*([A-Z][^\n]+?)\s*$', t, ''),
                 work='; '.join(' '.join(x.split()) for x in re.findall(r'^((?:Tree Removal[^\n]*|TREE REMOVAL[^\n]*|CR#\d+|PK#\d+|Full removal[^\n]*|Remove [^\n]*|\d+\. [^\n]*))', t, re.M)),
                 contract=NP, paid=NP, bal=first(r'TOTAL AUD\s+([\d,]+\.\d{2})', t))
        f['crwo'] = first(r'(CR#\d+)', t)
    elif v == 'HERITAGE_CN':
        f.update(addr='21-25 Spine Street, Sumner Park QLD 4074, AUSTRALIA', phone=NP, po=first(r'(Blanket Order #: \d+)', t),
                 bill='Logan City Council, PO Box 3226, LOGAN CITY QLD 4114, AUSTRALIA', officer=NP, site=first(r'Site address: ([^\n]+?)\s*$', t),
                 work='; '.join(' '.join(x.split()) for x in re.findall(r'^((?:To be applied to [^\n]+|To applied to [^\n]+|Contract # \S+|Blanket Order #: \d+|Proposal Number: \d+|Site address: [^\n]+|CR# \d+|PK\d{6}|SP\d|Work Specification[^\n]*|Cut back vegetation[^\n]*|poison all stumps[^\n]*))\s*$', t, re.M)),
                 contract=first(r'Contract # (PAR\d{3}[A-Z]\d{4})', t), paid=NP, bal=first(r'REMAINING CREDIT\s+([\d,]+\.\d{2})', t))
        f['crwo'] = first(r'(CR# \d+)', t)
    elif v == 'HERITAGE':
        f.update(addr='21-25 Spine Street, Sumner Park QLD 4074, AUSTRALIA', phone=NP, po=first(r'Reference[\s\S]*?\n\s*(\d{9})\s*$', t) + '; ' + first(r'(Blanket Order #: \d+)', t),
                 bill='Logan City Council, PO Box 3226, LOGAN CITY QLD 4114, AUSTRALIA', officer=NP, site=first(r'Site address: ([^\n]+?)\s*$', t),
                 work='; '.join(' '.join(x.split()) for x in re.findall(r'^((?:Contract # \S+|Blanket Order #: \d+|Proposal Number: \d+|Site address: [^\n]+|CR# \d+|PK\d{6}|SP\d|Logan City Council Request for Quote|RFQ: [^\n]+|Address: [^\n]+|Work Instructions: [^\n]+|formative pruning\.|\u2022 [^\n]+|access|curb|Heritage Tree Care - Scope of Works|Undertake all works[^\n]+|Provide all Traffic Management[^\n]+))\s*$', t, re.M)),
                 contract=first(r'Contract # (PAR\d{3}[A-Z]\d{4})', t), paid=NP, bal=first(r'Amount Due\s+([\d,]+\.\d{2})', t))
        f['crwo'] = first(r'(CR# \d+)', t)
    return f


BOILER = {  # verbatim per vendor template, first sighting; stored once and cited by key (rule 17 Amendment 2)
    'LEVAI': ('Bank Details | Commonwealth Bank Australia | BSB: 064 194 | Account: 101 540 21 | Name: T AND H LEVAI PTY LTD', None),
    'TEC': ('Please remit payment to: | Account Name: Total Environmental Concepts Pty Ltd | Bank: NAB | BSB: 082-738 | Account: 743930428 | View and pay online now',
            'Payment Due On Receipt | Please pay the total amount on or before the due date for payment. If you are unable to pay the total amount, please respond with a payment schedule within 15 business days after the date you received this invoice as required under the Building Industry Fairness (Security of Payment) Act 2017. | Please note a fee of 1.75% will apply if paying via Credit or Debit Card. If you wish to pay by this method follow the link below. Payment can not be received over the phone. | If you have any questions concerning this invoice, please contact Peter Sands on 0402 644380 or email peters@totalenviro.net.au | THANK YOU FOR YOUR BUSINESS!'),
    'TREESCAPE': ('BSB: 0 1 4 3 1 4 Acc No: 4 9 5 3 0 2 7 9 8 | Please Mail Payment to : Treescape Australia Pty Ltd PO Box 275 ELLEN GROVE 4078 | Payment Slip No Statement Issued | CREDIT CARD DETAILS',
                  'Payment Terms: 30 Days from Invoice Date | Credits cards will be charged at 2 % processing fee'),
    'BUSHCARE': ('PAYMENT DETAILS | Account Name: Bushcare Services | BSB: 064-474 Acc: 10607842', 'TERMS Net 30'),
    'AUSTSPRAY': ('Austspray Environmental Weed Control Pty Ltd - Payment Options | INTERNET BANKING: BSB: 014 596, Account: 4922 06581 (Please include invoice number as your reference and email remittance advice to admin@austspray.com) | POSTAL: Austspray Environmental Weed Control Pty Ltd PO Box 794, Helensvale QLD, 4212',
                  'Terms of Payment - Strictly 30 Days'),
    'EMU': ('Bank: NAB | Name: Environmental Management Unit | BSB: 084034 | AC #: 927141968 | Please include Invoice Number for reference', None),
    'ACTIVECO': ('Account Name: Lilgeco Pty Ltd ATF M Hanns Family Trust Trading As Activeco | Bank: ANZ | BSB #014636 | Account #296531168', None),
    'GURU': ('Please make all payments to | Guru Dirt Works | BSB 085 779 | Acc 747 711 863', None),
    'AUSTCARE': ('How To Pay | Mail: Detach this section and mail cheque to: Aust Care Environmental Services Pty Ltd 234 Newnham Road UPPER MT GRAVATT QLD 4122 | Direct Deposit: Bank Commonwealth Bank; Acc. Name Aust Care Environmental Services Pty Ltd; BSB 064-172; Acc. No. 10309026', None),
    'GLASCOTT': ('Payment can be made directly to our bank account | Bank : CBA | BSB : 062-037 | Account No : 28054554 | Account Name : Glascott Landscape and Civil Pty Limited | Branch : Chatswood', None),
    'ORIGIN': ('HOW TO PAY | DIRECT DEBIT Call 13 23 34 to arrange automatic payment of future invoices or for further information. | BPAY Make this payment via internet or phone banking Biller Code: 747428 Ref: 2500 1690 9112 | Visa, Mastercard or American Express Call 1300 593 687 or visit www.origin.com.au/CI-pay | MAIL Send the payment slip with your cheque made payable to: Origin Energy, GPO Box 3125, Sydney NSW 2001',
               '^Payments received after the due date may incur late payment interest charges, which will be reflected in your next invoice. | *Payment processing fees (incl GST) of total payment amount. Visa Debit 0.27% Visa Credit 0.87% Mastercard Debit 0.23% Mastercard Credit 0.94% American Express 0.95%'),
    'SEACRETE': ('Payment Details | Jeol Pty Ltd | Bank: Bendigo Bank | BSB: 633 000 | Account: 131562043 | Pay Now', 'Terms: NET 30'),
    'POOLSHOP': ('EFT Payment Details | BSB 032-108 | Account 163043 | Please email remittance to xero@office21.com.au', None),
    'QPOWER': ('How To Pay | Credit Card (MasterCard or Visa) Pay Online qpow.simprosuite.com/payment/ Please call 07 3155 4225 to pay over the phone. | Direct Deposit Bank Suncorp Acc. Name Q Power BSB 484-799 Acc. No. 611134396',
               'Major credit cards are accepted however a 2.2% surcharge will apply. To avoid surcharge please pay via Direct Deposit. | Payment terms are net: 14 days from date of invoice'),
    'PLAYFORCE': ('Electronic Funds Transfer | Account Name: Play Force Australia Pty Ltd | BSB: 064 400 | Account: 10367833 | Remittance To: accounts@playforce.com.au', 'Terms & Conditions (two printed pages, 1. General onward)'),
    'FLAVELL': ('Payment Details: | BOQ Flavell-Dau Family Trust | F82 Landscaping | BSB: 124 026 | Account: 2354 3389', 'Thank you for your business, we appreciate your support.'),
    'WEIS': ('BSB: Westpac 034 264 | Account: 425286', None),
    'ELEMENTAL': ('Bank Details-- Commonwealth Bank | A/C Name--Elemental Shade Structures | BSB--064 000 | A/C-- 16714326', 'Order on Start, Balance on Completion. Quote valid 30 days - Terms 7 days from invoice.'),
    'HIGGINS': ('Payment can be made directly to our bank account. Please include the Debtor Code/Invoice# with your payment. | Bank : NAB | BSB : 083 004 | Account No : 635 426 283 | AR Email: accounts@higgins.com.au',
                'Please call 1300 HIGGINS if you have any queries regarding this transaction. | This is a claim made under the Buding Industry Fairness (Security of Payment) Act 2017 (Qld).'),
    'HARPLEY': ('Direct Payment Details: | Harpley Services Pty Ltd | Commonwealth Bank | BSB: 064170 | Account: 10298115',
                'Invoives not paid in full by due date will incur further fees and charges. | All Materials remain property of Harpley Services Pty Ltd until Invoice paid in full. | Harpley Services Pty Ltd reserves the right to remove materials to recover costs of unpaid Invoices. | This is a Payment Claim made under the provisions of the Building and Construction Industry Payments Act QLD 2004.'),
    'C2C': ('Please pay invoice within 14 days and use the INVOICE NUMBER as the reference: | BSB: 084855 | ACC: 335780029 | NAME: Coast2Coast Grounds and Gardens', None),
    'KACHEL': (None, None),
    'ETSOL': (None, None),
    'GLASCOTT_LM': ('Payment can be made directly to our bank account | Bank : CBA | BSB : 062 037 | Account No : 28054554 | Account Name : Glascott Landscape and Civil Pty Limited | Branch : Chatswood', None),
    'PROVAC': ('Please make payment via Electronic Funds Transfer (EFT) | Name: Provac Australia Pty Ltd | BSB 064 474 | Acc 10279519 | Invoice enquiries to accounts@provac.net.au | Please use your Inv Number as your Reference for payment | Remittance advice to Leanne@provac.net.au', 'View and pay online now'),
    'SAVCO': ('BANK DETAILS | NAME: SAVCO VEGETATION SERVICES PL | BSB: 064420 | ACCOUNT NUMBER: 10891562', '**Please note a surcharge fee of 1.5% will be charged if paid by credit card'),
    'HERITAGE': ('Bank Transfer - Account Details | BSB: 014 279 | Account Number: 9056 99311 | View and pay online now', 'Credit Card Payments - Available using the link in your invoice email, noting credit card fees are 1.7% + 30c per transaction.'),
    'BURLY': ('How to Pay | Bank Details Name: Burly Holdings | BSB: 084-034 | Account Number: 254 857 098', None),
    'CERTIFIED': ('Payment by direct deposit to : | Certified Mowing Pty Ltd | BSB: 064 401 | ACCOUNT: 1072 9344', None),
    'C2C_INCL': ('Please pay invoice within 14 days and use the INVOICE NUMBER as the reference: | BSB: 084855 | ACC: 335780029 | NAME: Coast2Coast Grounds and Gardens', None),
    'FLAVELL_ATT': ('Payment Details: | BOQ Flavell-Dau Family Trust | F82 Landscaping | BSB: 124 026 | Account: 2354 3389', 'Thank you for your business, we appreciate your support.'),
    'MPDT': ('Please remit payments to MPDT (Tree Acq Pty Ltd) | BSB 082 167 | Account 329 781 201 | Email remittances to accounts@mpdt.com.au',
             'Please use the link below or call the office if you wish to pay this invoice via Visa or Mastercard. Please note that card payments will incur an additional 1.70% surcharge. If you wish to avoid this fee, or make a partial payment on invoice, please pay via direct debit. We do not accept American Express.'),
    'HERITAGE_CN': ('Bank Transfer - Account Details | BSB: 014 279 | Account Number: 9056 99311 | View and pay online now',
                    'CREDIT ADVICE | Please do not pay on this advice. Deduct the amount of this Credit Note from your next payment to us.'),
    'PLAYFORCE_ATT': ('Electronic Funds Transfer | Account Name: Play Force Australia Pty Ltd | BSB: 064 400 | Account: 10367833 | Remittance To: accounts@playforce.com.au', None),
    'VINTON': ('BANK DETAIL FOR EFT PAYMENT | RST Systems Pty Ltd | ANZ Underwood | BSB - 014279 | ACC No - 260818618 | Please email remittance Advice to admin@vintontreeservices.com.au', None),
    'PPG': ('Remit To: Bank Deposit: Citibank Limited Sydney NSW 2000 | AUD A/C: 242000-300098029 | USD A/C: 021000089-36198872 | Australia',
            'Terms of Sale - PPG Industries Australia Pty Limited (ACN 055 500 939), printed in full on page 2 (1 Definition onward), with the export compliance notice.'),
}


def canon_abn(s):
    dg = re.sub(r'\D', '', str(s or ''))
    return f'{dg[:2]} {dg[2:5]} {dg[5:8]} {dg[8:]}' if len(dg) == 11 else s


def boilerplate(d):
    p, t = BOILER[d['vendor_template']]
    return p or NP, t or NP


def capture(rows, corpus_path, match_path, say, existing_keys=frozenset(), existing_text=None, ev=None, variants=None):
    existing_text = existing_text or {}
    normt = lambda x: re.sub(r'[^a-z0-9]', '', str(x).lower())
    ex_by_text = {normt(t): k for k, t in existing_text.items()}
    corpus = json.load(open(corpus_path)); match = json.load(open(match_path))
    docs = {d['invoice_no']: d for d in corpus['documents'] if not d['duplicate_of']}
    batch = corpus['manifest']['batch_id']; stamp = STAMPS[batch]; ver = BATCH_VER[batch]
    by_key = {r['V'][1]: r for r in rows}
    import re as _re
    canon = {}
    for r in rows:
        # Canonical contractor label per printed ABN: from the inherited PS/WP analysis and from the APLEDGER history
        # identifications, whose labels come from the history manifest. Without the second source a supplier that
        # appears only outside Park Services takes the label as the invoice prints it, which on Savco is upper case
        # and collides with the history label under COUNTIF (case-insensitive trap).
        if r['meta']['inherited'] and r['V'][13] and r['V'][12]:
            canon.setdefault(_re.sub(r'\D', '', str(r['V'][13])), r['V'][12])
    for r in rows:
        if r['V'][13] and r['V'][12] and not r['V'][88]:
            canon.setdefault(_re.sub(r'\D', '', str(r['V'][13])), r['V'][12])
    def label(d):
        return canon.get(_re.sub(r'\D', '', str(d['supplier_abn'])), d['supplier'].split(' (')[0])
    ev = ev if ev is not None else dict(order=[], ei={}, eil=[], basis={}, vb=[], vb_keys={})
    variants = variants if variants is not None else {}
    ids = collections.Counter()
    for row in ev['vb']:
        mm = re.match(r'BP:(\w+)-([PT])(\d+)$', row[0]); ids[(row[0], )] += 0
    existing_keys = frozenset(existing_keys) | {row[0] for row in ev['vb']}
    ex_by_text.update({normt(row[5]): row[0] for row in ev['vb']})
    for m in match:
        d = docs[m['invoice']]; v = d['vendor_template']; evid = m['evid']
        pdfname = d['source_file']
        src = f"{pdfname} (md5 {d['source_md5']}), Batch {batch}, corpus_{batch}_v6.json" if d.get('source_md5') else SRCS[batch]
        assert evid not in ev['ei'], evid
        hf = header_fields(d)
        pay, term = boilerplate(d)
        bpk = {}
        for kind, txt in (('P', pay), ('T', term)):
            if txt == NP: bpk[kind] = NP; continue
            key = ev['vb_keys'].get((v, kind, txt)) or ex_by_text.get(normt(txt))
            if key and key in existing_keys:
                bpk[kind] = key; continue
            if not key:
                ids[(v, kind)] += 1
                key = f'BP:{BPK[v]}-{kind}{ids[(v, kind)]}'
                while key in existing_keys:
                    ids[(v, kind)] += 1; key = f'BP:{BPK[v]}-{kind}{ids[(v, kind)]}'
                ev['vb_keys'][(v, kind, txt)] = key
                ev['vb'].append([key, 'Payment details' if kind == 'P' else 'Terms & notices', d['supplier'], evid, 0, txt])
            bpk[kind] = key
            for row in ev['vb']:
                if row[0] == key: row[4] += 1
        priced = [l for l in d['lines'] if l['line_type'] == 'PRICED']
        attach = [l for l in d['lines'] if l['line_type'] == 'ATTACHMENT']
        targets = m['target'] if isinstance(m['target'], list) else [m['target']]
        assert all(t in by_key for t in targets), m['invoice']
        # line -> LineKey join: SUM-TIE Levai maps each quote line to its own AP row; all else to the single target
        def lk_for(i, l):
            if m.get('line_map'):
                for lk, rx in m['line_map']:
                    if re.search(rx, l['line_text']):
                        return lk
                return '(outside Parks scope, not a register line)'
            if len(targets) == 2:
                return targets[0] if '657861' in l['line_text'] else targets[1]
            return targets[0]
        sites = []
        pk_by_target = collections.defaultdict(list)   # printed PK on the lines mapped to each register line (split posting)
        for i, l in enumerate(priced, 1):
            if l.get('work_order') and re.fullmatch(r'PK\s?\d{5,6}', str(l['work_order'])):
                pk_by_target[lk_for(i, l)].append(str(l['work_order']))
        for i, l in enumerate(priced, 1):
            txt = ' '.join(l['line_text'].split())
            site = first(r'^Park: (.+?)\s+\d+\s+71\.526', txt, '') if v == 'BUSHCARE' else (first(r'^\d{5} (.+?) \d{6} PK', txt, '') if v == 'AUSTCARE' else (first(r'^(.+?) - [A-Z]{2,5}\d', txt, '') if v == 'EMU' else (first(r'^PK\d{6} AMP5 (.+?) \d\.\d\d', txt, '') if v == 'ACTIVECO' else '')))
            if site: sites.append(site)
            pk = l.get('work_order') or (d['pk_refs'][0] if len(d['pk_refs']) == 1 else '')
            ev['eil'].append([evid, i, txt, l.get('qty'), l.get('unit_price_ex_gst'), l.get('gst_rate_printed') or (float(l['gst']) if l.get('gst') not in (None, '') else NP), l['line_ex_gst'],
                              pk or NP, pk.replace(' ', '') if pk else NP, lk_for(i, l), l.get('note') or None, site or 'No park named on the printed line', 'Sighted invoice site (printed)' if site else 'No park named on the printed line'])
        for j, l in enumerate(attach, len(priced) + 1):
            txt = ' '.join(l['line_text'].split())
            ev['eil'].append([evid, j, txt, 1.0, l.get('unit_price_ex_gst'), l.get('gst'), None, l.get('work_order') or NP, l.get('work_order') or NP, targets[0],
                              f"ATTACHMENT (rule 16d): schedule row ex GST {l.get('unit_price_ex_gst')}; excluded from check 1", first(r'^(.+?)\s{2,}', l['line_text'], '') or NP, 'Sighted attachment schedule (printed)'])
        sub, gst, tot = D(d['printed_subtotal_ex_gst']), D(d['printed_gst']), D(d['printed_total_incl_gst'])
        ev['order'].append(evid)
        ev['basis'][evid] = 'Ex GST (printed subtotal)'
        ei = [evid, d['supplier'], d['supplier_abn'], date_out(d['invoice_date']), date_out(d.get('due_date')) if d.get('due_date') else NP, m['invoice'], hf['contract'] if hf['contract'] != NP else (hf['po']),
              '; '.join(dict.fromkeys(sites)) if sites else hf['site'], len(priced), float(sub), float(gst), float(tot), '',
              f'Complete on the register line (green block, columns CJ to DW), LineKey {", ".join(targets)}; staging not required.'] + [''] * 17 + [f'{pdfname} pages {d["page_range"][0]}-{d["page_range"][1]}; {stamp}']
        ev['ei'][evid] = (None, ei, f'New at branch {ver} (Batch {batch})')
        # anomalies
        var = m['variant']; anom = []
        if 'PARTIAL-SCOPE' in var: anom.append('[check variant] Check 2 PARTIAL-SCOPE (v32): Council-wide consolidated invoice; this register line ties its own site row by LineKey; checks 1 and 3 tie the whole printed invoice; the association is fixed by the site NMI and account printed on the row and in the ledger narration.')
        if 'split-posting' in var: anom.append('[check variant] Check 2 split-posting: each register line ties its own printed line(s) by LineKey.')
        if 'SUM-TIE' in var: anom.append('[check variant] Check 2 SUM-TIE: one printed invoice posts as two AP rows, each tied to its own printed quote line by LineKey; check 2 sums the sibling register amounts against the printed subtotal.')
        if 'derivation' in var: anom.append(f'[check variant] Check 2 derivation equality: register amount = ROUND(printed total incl GST {tot} / 1.1, 2); the printed GST {gst} is a per-line basket, not 10% of the subtotal.')
        if 'one-cent' in var: anom.append('[check variant] Check 2 one-cent tolerance: TechOne incl/1.1 derivation differs from the printed subtotal by 1c.')
        if 'companion' in var: anom.append('Cents companion AP line(s) on the same document (TechOne incl/1.1 rounding leg), not green-blocked: ' + var.split('cents companion AP line(s) ')[1].split(' (TechOne')[0] + '.')
        basket = sum(D(D(l['line_ex_gst']) * Decimal('0.1')) for l in priced)
        std = D(sub * Decimal('0.1'))
        chk3 = 'std'
        if v == 'ORIGIN':
            chk3 = 'sitegst'; anom.append(f'[check variant] Check 3 per-site GST: the consolidated GST {gst} is the sum of the GST printed on each site row (captured in Evidence_Invoice_Lines column F), not ROUND(subtotal x 0.1) = {std}.')
            anom.append('[check variant] Check 2 derivation on the site row: register amount = ROUND(site total incl GST / 1.1, 2) (TechOne posts the site incl/1.1; 1026231 prints $2,822.57 new charges, $3,104.81 total, register $2,822.55).')
        elif gst != std:
            if basket == gst: chk3 = 'basket'; anom.append(f'[check variant] Check 3 per-line rounding basket: printed GST {gst} equals the sum of each line rounded to the cent, not ROUND(subtotal x 0.1) = {std}.')
            else: chk3 = 'tol1c'; anom.append(f'[check variant] Check 3 rounding tolerance 1c: printed GST {gst} against ROUND(subtotal x 0.1) = {std}.')
        for fnd in d['findings']:
            if 'Printed GST' not in fnd: anom.append(fnd)
        if v == 'GLASCOTT': anom.append('Letterhead prints Technigro ABN 97 001 281 572; payment account name is Glascott Landscape and Civil Pty Limited. Printed ABN decides identity (rule 8); confirm the creditor entity against the APLEDGER record.')
        if v == 'GLASCOTT_LM': anom.append('Letterhead prints Technigro ABN 97 001 281 572; payment account name is Glascott Landscape and Civil Pty Limited. APLEDGER GLA009 (branch v4) carries ABN 97001281572, so the creditor entity is the Glascott record (rule 8, printed ABN decides).')
        if v == 'VINTON': anom.append('No ABN is printed anywhere on this invoice and no entity name prints on the face; the only supplier identification is "RST Systems Pty Ltd" in the bank block and the remittance address admin@vintontreeservices.com.au. The register label and ABN come from the APLEDGER history VIN003 (Vinton Tree Services, ABN 84 008 552 538), not from this document (rule 8).')
        if v == 'SAVCO': anom.append('ABN printed ungrouped (78161366749); register column M carries the grouped form.')
        if m['invoice'] == 'INV-9360': anom.append('Invoice date 31-Mar-2026 and due 30-Apr-2026 print against July 2026 treatment dates and a 24-Jul-2026 posting; supplier-side date error, service period Jul-2026.')
        if m.get('evid_note'): anom.append(m['evid_note'])
        if v == 'BUSHCARE' and d['invoice_no'] in ('18751', '18750', '18788'): anom.append('Scanned copy with an OCR text layer; letter-spacing artefacts in the text layer (e.g. "J D R 6") are captured as the layer prints; the image reads unspaced.')
        items = ' '.join(f'{i}. {" ".join(l["line_text"].split())}' for i, l in enumerate(priced, 1))
        if len(items) > 30000: items = items[:30000] + ' [trimmed at the cell cap; full lines on Evidence_Invoice_Lines]'
        cat, v3, trule = CAT[v]
        desc_top = '; '.join(' '.join(l['line_text'].split())[:80] for l in priced[:3])
        for t in targets:
            r = by_key[t]; V = r['V']
            assert not V[88], t
            if r['meta']['inherited']:
                V[148] = f'Inherited from PS_WP register v127; sighted at branch {ver} (port the capture to PS_WP v128)'
                r['meta']['ported'] = True; r['meta']['ported_ver'] = ver
            V[11] = V[11]
            if d.get('supplier_abn'):
                V[12] = label(d); V[13] = canon_abn(d['supplier_abn']) if batch == 'attach_1' else d['supplier_abn']
            else:
                # Rule 8: the printed ABN decides identity, and this face prints none. The creditor history that
                # identified the line (Tier 1, with an ABN) keeps the label and the ABN; the printed supplier name
                # goes to the green block and the coding note, never over the top of evidence that carries an ABN.
                V[12] = V[12] or label(d); V[13] = V[13] or None
            V[24] = cat; V[132] = v3; V[133] = trule; V[131] = None
            V[25] = f'{cat}; sighted {len(priced)} line(s), {d["supplier"].split(" (")[0]}: {hf["work"][:160]}. Items: {desc_top}'
            V[27] = 'Sighted invoice line'; V[29] = 1; V[33] = 'Confirmed'
            V[28] = f'Sighted tax invoice {m["invoice"]}, {d["supplier"].split(" (")[0]}, ABN {d["supplier_abn"]}; captured in full at line-item granularity at branch {ver} ({pdfname} pages {d["page_range"][0]}-{d["page_range"][1]})'
            V[31] = 'Review' if (v == 'GLASCOTT' or m['invoice'] == 'INV-9360') else 'Correct'
            notes = []
            if v == 'GLASCOTT': notes.append(f'Attached schedule totals differ from the invoice face ({d["findings"][0][:120]}); schedule carries rows on PKs outside PK000378.')
            if m['invoice'] == 'INV-9360': notes.append('Supplier printed invoice date 31-Mar-2026 for July 2026 works.')
            if 'companion' in var: notes.append('Cents companion line(s) on this document: ' + var.split('cents companion AP line(s) ')[1].split(' (TechOne')[0] + '; TechOne incl/1.1 rounding legs.')
            if m.get('coding_note'): notes.append(m['coding_note'])
            if m.get('coding_verdict'): V[31] = m['coding_verdict']
            V[32] = ' '.join(notes) or None
            V[34] = ('Confirm the Technigro/Glascott creditor entity and the schedule-to-face difference with Natural Areas.' if v == 'GLASCOTT' else
                     'Ask Activeco to reissue with the correct invoice date; no financial effect.' if m['invoice'] == 'INV-9360' else None)
            if m.get('follow_up'): V[34] = m['follow_up']
            V[130] = 'Sighted invoice site (printed)' if sites or hf['site'] not in (NP, '') else 'No site determinable'
            V[129] = sites[0] if len(set(sites)) == 1 else ('Multiple sites named (not allocated)' if sites else (hf['site'] if hf['site'] != NP else None))
            V[146] = 'R1 Contract, schedule of rates' if hf['contract'] != NP else ('R3 Quoted works' if v in ('LEVAI',) else 'R4 Ad hoc purchase order')
            own = pk_by_target.get(t) or []
            pkp = own[0] if own else (d['pk_refs'][0] if d['pk_refs'] else hf.get('printed_account', NP))
            if pkp == 'undefined':
                pkp = 'undefined (as printed)'
            if batch in ('attach_1', 'attach_2', 'code', 'mix22', 'attach_3') and pkp not in (NP, 'undefined (as printed)') and pkp.replace(' ', '').replace('#', '') != str(V[17]):
                anom.append(f'Printed PK {pkp} differs from the PK charged {V[17]}; see the coding note. PK Charged stays the ledger Work Order (rule 1).')
            G = {88: evid, 89: d['supplier'], 90: d['supplier_abn'], 91: NP, 92: hf['addr'], 93: hf['phone'], 94: date_out(d['invoice_date']), 95: date_out(d.get('due_date')) if d.get('due_date') else NP,
                 96: hf['po'], 97: hf['contract'], 98: hf['bill'], 99: NP, 100: hf['officer'], 101: NP, 102: NP, 103: NP, 104: pkp, 105: pkp.replace(' ', '').replace('#', '') if pkp != NP else NP,
                 106: hf['site'], 107: hf['officer'] if 'Site Contact' in hf['officer'] else NP, 108: hf['work'], 109: NP, 103: hf.get('crwo', NP), 110: len(priced), 111: items, 112: NP,
                 113: float(sub), 114: float(gst), 115: float(tot), 116: hf['paid'], 117: hf['bal'], 118: bpk['P'], 119: bpk['T'],
                 120: f'{d["page_range"][1] - d["page_range"][0] + 1} page(s) ({pdfname} pp {d["page_range"][0]}-{d["page_range"][1]})', 125: src, 126: stamp,
                 127: ' '.join(anom) or None}
            for c, val in G.items(): V[c] = val
            variants[t] = dict(kind=('bykey_deriv' if v == 'ORIGIN' else 'sumtie' if 'SUM-TIE' in var else 'bykey' if ('PARTIAL-SCOPE' in var or 'split-posting' in var) else 'deriv' if 'derivation' in var else 'tol1c' if 'one-cent' in var else 'std'), siblings=targets, chk3=chk3)
            if v == 'HARPLEY':
                V[101] = hf['request_date']; V[102] = hf['via']; V[103] = hf['crwo']; V[107] = hf['site_contact']; V[109] = hf['technician']
        # companion rows: coding note cross-reference only
        for l in m['register_lines']:
            if l['linekey'] not in targets:
                r = by_key[l['linekey']]; V = r['V']
                V[32] = ((V[32] + ' ') if V[32] else '') + f'Cents companion of {m["invoice"]} (sighted on {", ".join(targets)}, {evid}); TechOne incl/1.1 rounding leg, zero-amount companion rule: no green block.'
                V[12] = label(d); V[13] = d['supplier_abn']; V[29] = 1
    say(f'capture: {len(ev["order"])} invoices, {len(ev["eil"])} evidence lines, {len(variants)} green blocks, {len(ev["vb"])} boilerplate keys')
    return ev, variants


def formulas(row, var, tm_last=None):
    r = row; k = var['kind']
    f = {'DQ': f'=ROUND(SUMIF(EIL_Invoice,CJ{r},EIL_Amount),2)', 'DR': f'=IF(DQ{r}=DI{r},"TRUE","FALSE")'}
    if k == 'std': f['DS'] = f'=IF(ROUND(T{r},2)=DI{r},"TRUE","FALSE")'
    elif k == 'tol1c': f['DS'] = f'=IF(ROUND(ABS(T{r}-DI{r}),2)<=0.01,"TRUE","FALSE")'
    elif k == 'deriv': f['DS'] = f'=IF(ROUND(T{r},2)=ROUND(DK{r}/1.1,2),"TRUE","FALSE")'
    elif k == 'sumtie': f['DS'] = f'=IF(ROUND({"+".join("T%d" % s for s in var["sibling_rows"])},2)=DI{r},"TRUE","FALSE")'
    elif k == 'bykey_deriv': f['DS'] = f'=IF(ROUND(T{r},2)=ROUND((SUMIFS(EIL_Amount,EIL_Invoice,CJ{r},EIL_LineKey,A{r})+SUMIFS(EIL_GST,EIL_Invoice,CJ{r},EIL_LineKey,A{r}))/1.1,2),"TRUE","FALSE")'
    elif k == 'bykey': f['DS'] = f'=IF(ROUND(T{r},2)=ROUND(SUMIFS(EIL_Amount,EIL_Invoice,CJ{r},EIL_LineKey,A{r}),2),"TRUE","FALSE")'
    if var['chk3'] == 'std': f['DT'] = f'=IF(DJ{r}=ROUND(DI{r}*0.1,2),"TRUE","FALSE")'
    elif var['chk3'] == 'sitegst': f['DT'] = f'=IF(ROUND(DJ{r},2)=ROUND(SUMIF(EIL_Invoice,CJ{r},EIL_GST),2),"TRUE","FALSE")'
    elif var['chk3'] == 'basket': f['DT'] = f'=IF(ROUND(DJ{r},2)=ROUND(SUMPRODUCT((EIL_Invoice=CJ{r})*ROUND(EIL_Amount*0.1,2)),2),"TRUE","FALSE")'
    else: f['DT'] = f'=IF(ROUND(ABS(DJ{r}-ROUND(DI{r}*0.1,2)),2)<=0.01,"TRUE","FALSE")'
    return f
