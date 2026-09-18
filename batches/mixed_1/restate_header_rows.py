"""restate_header_rows.py - type the eight mis-typed item-table headers TABLE_HEADER (rule 19.2, R-M1-1).

corpus_mixed_1_v6.json carries eight rows typed HEADER, which is in no version of the closed list and is P13.
Every one of them is the same row on eight Austspray documents, the item table's own header reading "Item", and
the closed list has carried TABLE_HEADER for it since v6. It is a mis-typing and nothing more: no amount moves,
no tie changes, and the printed text is untouched.

Usage: python3 restate_header_rows.py
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'corpus_mixed_1_v6.json')


def main():
    corpus = json.load(open(SRC))
    n = 0
    for doc in corpus['documents']:
        for l in doc['lines']:
            if l.get('line_type') == 'HEADER':
                assert l.get('line_ex_gst') is None and l.get('stated_amt') is None, (doc['doc_ref'], l['line_no'])
                l['line_type'] = 'TABLE_HEADER'
                l['note'] = 'R-M1-1: typed HEADER, which is outside the closed list (P13); it is the item table header.'
                n += 1
    corpus['manifest'].setdefault('restatements', []).append(
        dict(rule='R-M1-1', rows=n, detail='HEADER retyped TABLE_HEADER; no amount, tie or printed text changed'))
    json.dump(corpus, open(SRC, 'w'), indent=1)
    print(f'{n} rows retyped HEADER -> TABLE_HEADER')


if __name__ == '__main__':
    main()
