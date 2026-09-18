"""record_sighting_20260918.py - record the binders sighted on 18-Sep-2026 (rule 12).

WHAT ARRIVED. Two PDFs, against the two source files this corpus names:

  97 001 281 572.pdf      16 pages   md5 007e24fb685834aa109a08eebcc9f1cd
  play force and vinton   42 pages   md5 db27c53bee4e62455a041d6dfa7e767a

The Glascott binder is COMPLETE: 16 pages against 16 declared, and the md5 matches the one the
masked-row screen recorded when it was tuned, so it is the same file.

THE PLAY FORCE BINDER IS A 42-PAGE SLICE OF A 124-PAGE BINDER, and this is the finding, not a
footnote. The corpus declares 124 pages for it. Mapping every invoice number in the slice against
the corpus's page ranges gives one constant offset of +81, so the slice is binder pages 82 to 123.

  fully sighted    20 documents, 19675 19830 19873 19884 19896 19902 19917 19922 19927 19938
                                 19939 19943 19944 19952 19961 19971 19979 19980 19985 19988
  partly sighted    2 documents, INV-8009 [80,82] (page 82 only) and 19996 [123,124] (page 123 only)
  not sighted      28 documents, binder pages 1 to 81 and page 124

WHAT THE SIGHTING BUYS.

  M1, masked rows.  pbr_mask_screen.py over the 42-page slice: 0 pages mask rows. So the 20 fully
  sighted documents carry a clean M1 verdict, which they did not before: the screen record says of
  this binder "NOT SUPPLIED to this session, so its 124 pages are unscreened". The 28 unsighted
  documents still carry no M1 verdict either way.

  10, the description layer.  pswp_shingle_check.py against page text parsed from both PDFs:
  840 shingles tested, 0 failing, 28 unverifiable. The 28 are exactly the unsighted documents.
  So 33 of 61 documents are verbatim VERIFIED against an independent parse of the page, and the
  corpus-level verdict stays UNVERIFIABLE because the other 28 retain nothing to test.

  That check had to be fixed before it could be run. It keyed page text on the bare page number,
  and this corpus has two source files each numbered from 1, so five Play Force documents at binder
  pages 1 to 16 were tested against the Glascott binder's pages 1 to 16 and reported FAIL. A
  qualified key "<source_file>|<page>" is now read first and a bare-keyed file is refused on a
  multi-source corpus. Logged as B8.

WHAT IT DOES NOT BUY. The batch stays RED and stays held. It is RED on P11, P12 and P17, which are
bands, residue lists and header-source rows: a re-extraction produces those and a sighting does not.
A re-extraction of the 33 sighted documents is possible now; the other 28 need binder pages 1 to 81
and page 124, and a partial re-extraction cannot clear a batch gate.

Usage: python3 record_sighting_20260918.py
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, 'corpus_playforce_vinton_glascott_20260916_v7.json')
SCREEN = os.path.join(HERE, 'mask_screen_playforce_vinton_glascott_20260916.json')

SIGHTED = """19675 19830 19873 19884 19896 19902 19917 19922 19927 19938 19939 19943 19944
             19952 19961 19971 19979 19980 19985 19988""".split()
PARTIAL = {'INV-8009': 'page 82 of [80, 82]', '19996': 'page 123 of [123, 124]'}
PF_MD5 = 'db27c53bee4e62455a041d6dfa7e767a'
GL_MD5 = '007e24fb685834aa109a08eebcc9f1cd'


def main():
    screen = json.load(open(SCREEN))
    for b in screen['binders']:
        if b['name'] == 'play force and vinton.pdf':
            assert b.get('md5') is None, 'already screened; this script is a first sighting'
            b['md5'] = PF_MD5
            b['pages_supplied'] = 42
            b['pages_declared'] = 124
            b['slice'] = [82, 123]
            b['pages_masking_rows'] = []
            b['note'] = ('PARTIAL. 42 pages supplied against 124 declared, mapped to binder pages 82 to 123 '
                         'by a constant +81 offset over every invoice number in the slice. 0 pages mask rows, '
                         'so the 20 documents wholly inside the slice carry a clean M1 verdict. Binder pages '
                         '1 to 81 and page 124, and the 28 documents in them, remain unscreened.')
    json.dump(screen, open(SCREEN, 'w'), indent=1)

    corpus = json.load(open(CORPUS))
    man = corpus['manifest']
    for sf in man['source_files']:
        if sf['name'] == '97 001 281 572.pdf':
            sf['md5'] = GL_MD5
            sf['sighted_utc'] = '2026-09-18'
            sf['pages_supplied'] = 16
        elif sf['name'] == 'play force and vinton.pdf':
            sf['md5'] = PF_MD5
            sf['sighted_utc'] = '2026-09-18'
            sf['pages_supplied'] = 42
            sf['pages_supplied_range'] = [82, 123]
            sf['sighting'] = 'PARTIAL: 42 of 124 pages'
    man['shingle_checks_run'] = 840
    man['shingle_failures'] = 0
    man['shingle_unverifiable_documents'] = 28
    man['page_text_basis'] = ('pdftotext -layout over the supplied binders, 18-Sep-2026: all 16 Glascott '
                              'pages and Play Force binder pages 82 to 123. 33 of 61 documents verified, '
                              '840 shingles, 0 failing. The other 28 retain no page text.')
    man.setdefault('sightings', []).append(dict(
        utc='2026-09-18', rule='rule 12, a re-sighting is audited not re-captured',
        fully_sighted=SIGHTED, partly_sighted=PARTIAL, unsighted=28,
        mask_screen='0 pages mask rows over the 42-page slice; the Glascott binder was already clean',
        shingles='840 tested, 0 failing, 28 unverifiable',
        gate_effect='NONE. The batch stays RED on P11, P12 and P17, which need a re-extraction, not a sighting.'))
    json.dump(corpus, open(CORPUS, 'w'), indent=1)
    print(f'sighting recorded: {len(SIGHTED)} fully, {len(PARTIAL)} partly, 28 unsighted; '
          f'840 shingles, 0 failing')


if __name__ == '__main__':
    main()
