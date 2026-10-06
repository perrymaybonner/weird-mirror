#!/usr/bin/env python3
"""
Spiral artworks for Curiosity Loop - downloader.

Only official open-access APIs, only public-domain / CC0 works:
  - The Metropolitan Museum of Art  https://metmuseum.github.io/            (isPublicDomain = true)
  - Cleveland Museum of Art         https://openaccess-api.clevelandart.org (share_license_status = CC0)

Two steps:

  python3 scripts/download_artworks.py candidates
      searches both museums for spiral / vortex / coil / whorl ... works and writes
      artworks/candidates.json (metadata only, no images) to choose from.

  python3 scripts/download_artworks.py build
      reads artworks/selection.json (an ordered list of {"source": "met"|"cma", "id": ...}),
      re-fetches each record from the museum, downloads its image, and writes
        artworks/images/001.jpg ...           (1600px long side, aspect kept, never cropped)
        artworks/metadata/artworks.json / artworks.csv / README.md
      then verifies that records and images line up.

Nothing is invented: any field a museum does not provide is null.
Uses curl (always present on macOS) so there are no Python SSL/cert surprises.
"""

import csv
import json
import os
import subprocess
import sys
import time
import urllib.parse

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
ART = os.path.join(ROOT, 'artworks')
IMAGES = os.path.join(ART, 'images')
META = os.path.join(ART, 'metadata')

MET_API = 'https://collectionapi.metmuseum.org/public/collection/v1'
CMA_API = 'https://openaccess-api.clevelandart.org/api/artworks/'

MET_TERMS = ['spiral', 'spiral ornament', 'spiral staircase', 'spiral column', 'vortex', 'whirlpool',
             'coil', 'whorl', 'swirl', 'ammonite', 'nautilus', 'snail shell', 'rosette', 'volute',
             'labyrinth', 'whirl', 'waves', 'scroll ornament', 'circular', 'rotation', 'wheel']
CMA_TERMS = ['spiral', 'coil', 'whorl', 'swirl', 'vortex', 'volute', 'rosette', 'shell',
             'nautilus', 'whirlpool', 'wave', 'scroll', 'wheel', 'circle']
PER_TERM_MET = 30
PER_TERM_CMA = 40


def fetch_json(url, tries=3):
    for k in range(tries):
        r = subprocess.run(['curl', '-s', '-m', '30', '-L', url], capture_output=True)
        if r.returncode == 0 and r.stdout:
            try:
                return json.loads(r.stdout)
            except ValueError:
                pass
        time.sleep(1.0 + k)
    return None


def download(url, path):
    r = subprocess.run(['curl', '-s', '-f', '-m', '120', '-L', '-o', path, url])
    return r.returncode == 0 and os.path.getsize(path) > 1000


def none_if_blank(v):
    if v is None:
        return None
    if isinstance(v, str):
        v = v.strip()
        return v or None
    if isinstance(v, (list, dict)) and not v:
        return None
    return v


# ------------------------------------------------------------------ records
def met_record(oid):
    o = fetch_json('%s/objects/%s' % (MET_API, oid))
    if not o or not o.get('isPublicDomain') or not o.get('primaryImage'):
        return None
    artist = none_if_blank(o.get('artistDisplayName'))
    return {
        'source': 'met', 'sourceId': o['objectID'],
        'title': none_if_blank(o.get('title')),
        'maker': artist,
        'artist': artist,
        'date': none_if_blank(o.get('objectDate')),
        'culture': none_if_blank(o.get('culture')),
        'period': none_if_blank(o.get('period')),
        'medium': none_if_blank(o.get('medium')),
        'materials': None,
        'dimensions': none_if_blank(o.get('dimensions')),
        'classification': none_if_blank(o.get('classification')),
        'department': none_if_blank(o.get('department')),
        'provenance': None,                         # not provided by the Met API
        'creditLine': none_if_blank(o.get('creditLine')),
        'museum': 'The Metropolitan Museum of Art',
        'objectNumber': none_if_blank(o.get('accessionNumber')),
        'objectURL': none_if_blank(o.get('objectURL')),
        'imageURL': o.get('primaryImage'),
        'downloadURL': o.get('primaryImageSmall') or o.get('primaryImage'),   # web size is plenty for 1280x720
        'additionalImages': o.get('additionalImages') or [],
        'license': 'Public Domain (The Met Open Access, CC0)',
        'copyright': None,
        'description': None,                        # not provided by the Met API
        'tags': [t['term'] for t in (o.get('tags') or []) if t.get('term')],
    }


def cma_to_record(a):
    if (a.get('share_license_status') or '').upper() != 'CC0':
        return None
    imgs = a.get('images') or {}
    main = (imgs.get('print') or imgs.get('web') or {}).get('url')
    web = (imgs.get('web') or imgs.get('print') or {}).get('url')
    if not main:
        return None
    creators = [c.get('description') for c in (a.get('creators') or []) if c.get('description')]
    prov = [p.get('description') for p in (a.get('provenance') or []) if p.get('description')]
    culture = a.get('culture') or []
    return {
        'source': 'cma', 'sourceId': a['id'],
        'title': none_if_blank(a.get('title')),
        'maker': '; '.join(creators) or None,
        'artist': '; '.join(creators) or None,
        'date': none_if_blank(a.get('creation_date')),
        'culture': '; '.join(culture) if isinstance(culture, list) else none_if_blank(culture),
        'period': None,
        'medium': none_if_blank(a.get('technique')),
        'materials': None,
        'dimensions': none_if_blank(a.get('measurements')),
        'classification': none_if_blank(a.get('type')),
        'department': none_if_blank(a.get('department')),
        'provenance': ' | '.join(prov) or None,
        'creditLine': none_if_blank(a.get('creditline')),
        'museum': 'Cleveland Museum of Art',
        'objectNumber': none_if_blank(a.get('accession_number')),
        'objectURL': none_if_blank(a.get('url')),
        'imageURL': main,
        'downloadURL': web,
        'additionalImages': [((x.get('print') or x.get('web') or {}).get('url'))
                             for x in (a.get('alternate_images') or [])
                             if (x.get('print') or x.get('web'))],
        'license': 'CC0 (Cleveland Museum of Art Open Access)',
        'copyright': none_if_blank(a.get('copyright')),
        'description': none_if_blank(a.get('description')),
        'tags': [],
    }


def cma_record(aid):
    d = fetch_json('%s%s' % (CMA_API, aid))
    return cma_to_record(d['data']) if d and d.get('data') else None


# ------------------------------------------------------------------ steps
def candidates():
    found, seen = [], set()
    for term in MET_TERMS:
        q = fetch_json('%s/search?hasImages=true&q=%s' % (MET_API, urllib.parse.quote(term)))
        ids = (q or {}).get('objectIDs') or []
        kept = 0
        for oid in ids[:PER_TERM_MET * 3]:
            if ('met', oid) in seen:
                continue
            seen.add(('met', oid))
            rec = met_record(oid)
            time.sleep(0.03)
            if rec:
                rec['matchedTerm'] = term
                found.append(rec)
                kept += 1
                if kept >= PER_TERM_MET:
                    break
        print('met  %-18s %3d kept (of %d hits)' % (term, kept, len(ids)))
    for term in CMA_TERMS:
        q = fetch_json('%s?q=%s&cc0=1&has_image=1&limit=%d' % (CMA_API, urllib.parse.quote(term), PER_TERM_CMA))
        kept = 0
        for a in (q or {}).get('data') or []:
            if ('cma', a['id']) in seen:
                continue
            seen.add(('cma', a['id']))
            rec = cma_to_record(a)
            if rec:
                rec['matchedTerm'] = term
                found.append(rec)
                kept += 1
        print('cma  %-18s %3d kept' % (term, kept))
    os.makedirs(ART, exist_ok=True)
    with open(os.path.join(ART, 'candidates.json'), 'w') as f:
        json.dump(found, f, indent=1, ensure_ascii=False)
    print('%d candidates -> artworks/candidates.json' % len(found))


CSV_FIELDS = ['id', 'filename', 'title', 'maker', 'artist', 'date', 'culture', 'period', 'medium',
              'materials', 'dimensions', 'classification', 'department', 'provenance', 'creditLine',
              'museum', 'objectNumber', 'objectURL', 'imageURL', 'license', 'copyright', 'description', 'tags']


def build():
    with open(os.path.join(ART, 'selection.json')) as f:
        selection = json.load(f)
    os.makedirs(IMAGES, exist_ok=True)
    os.makedirs(META, exist_ok=True)
    for old in os.listdir(IMAGES):
        if old.endswith('.jpg'):
            os.remove(os.path.join(IMAGES, old))
    records = []
    for n, pick in enumerate(selection, 1):
        rec = met_record(pick['id']) if pick['source'] == 'met' else cma_record(pick['id'])
        if rec is None:
            sys.exit('!! %s %s is no longer open access / has no image - replace it in selection.json'
                     % (pick['source'], pick['id']))
        fn = '%03d.jpg' % n
        raw = os.path.join(IMAGES, '_download')
        if not download(rec['downloadURL'], raw):
            sys.exit('!! image download failed for %s %s: %s' % (pick['source'], pick['id'], rec['downloadURL']))
        # 1600px long side, aspect kept, never cropped
        subprocess.run(['sips', '-Z', '1600', '-s', 'format', 'jpeg', '-s', 'formatOptions', '85',
                        raw, '--out', os.path.join(IMAGES, fn)], capture_output=True, check=True)
        os.remove(raw)
        rec = dict({'id': n, 'filename': fn}, **{k: v for k, v in rec.items() if k not in ('source', 'sourceId', 'matchedTerm', 'downloadURL')})
        records.append(rec)
        print('%s  %-8s %s' % (fn, pick['source'], (rec['title'] or '')[:70]))
        time.sleep(0.1)

    with open(os.path.join(META, 'artworks.json'), 'w') as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    with open(os.path.join(META, 'artworks.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction='ignore')
        w.writeheader()
        for r in records:
            row = dict(r)
            row['tags'] = '; '.join(r.get('tags') or [])
            w.writerow({k: ('' if row.get(k) is None else row.get(k)) for k in CSV_FIELDS})
    write_readme(records)
    verify()


def write_readme(records):
    by_museum = {}
    for r in records:
        by_museum.setdefault(r['museum'], []).append(r)
    lines = [
        '# Spiral artworks - sources and licenses', '',
        'The %d images in `artworks/images/` are the collection shown in Curiosity Loop.' % len(records),
        'Every image and record came from an official museum open-access API through',
        '`scripts/download_artworks.py`; nothing was typed in by hand. Fields a museum does not',
        'provide are `null` in `artworks.json` (for example, the Met API has no provenance or description).', '',
        '## Sources and licenses', '',
        '- **The Metropolitan Museum of Art**: Open Access API (https://metmuseum.github.io/). Only',
        '  objects with `isPublicDomain: true` were used. The Met releases these images under',
        '  Creative Commons Zero (CC0): free to use, share and adapt for any purpose, no permission needed.',
        '- **Cleveland Museum of Art**: Open Access API (https://openaccess-api.clevelandart.org/).',
        '  Only objects with `share_license_status: CC0` were used, also free for any use.', '',
        'No attribution is legally required under CC0, but this project credits each museum and keeps',
        'the object number, credit line and official object URL for every work.', '',
        '## How it was generated', '',
        '1. `python3 scripts/download_artworks.py candidates` searched both APIs for spiral, vortex,',
        '   coil, whorl, swirl, volute, rosette, shell and related terms, keeping only public-domain/CC0 works.',
        '2. 40 works were chosen for visual variety and listed in order in `artworks/selection.json`.',
        '3. `python3 scripts/download_artworks.py build` re-fetched each record, downloaded the museum',
        '   image, resized it to 1600px on the long side (aspect ratio kept, never cropped) and wrote',
        '   `artworks.json`, `artworks.csv` and this file.', '',
        '## The works', '',
    ]
    for museum, rs in by_museum.items():
        lines.append('### %s (%d)' % (museum, len(rs)))
        lines.append('')
        for r in rs:
            who = r['maker'] or r['culture'] or 'Unknown maker'
            lines.append('- `%s` **%s**. %s, %s. %s. [%s](%s). %s' % (
                r['filename'], r['title'], who, r['date'] or 'n.d.', r['objectNumber'],
                'object page', r['objectURL'], r['license']))
        lines.append('')
    with open(os.path.join(META, 'README.md'), 'w') as f:
        f.write('\n'.join(lines))


def verify():
    with open(os.path.join(META, 'artworks.json')) as f:
        records = json.load(f)
    imgs = sorted(fn for fn in os.listdir(IMAGES) if fn.endswith('.jpg'))
    problems = []
    if len(records) != len(imgs):
        problems.append('%d records but %d images' % (len(records), len(imgs)))
    for r in records:
        if r['filename'] not in imgs:
            problems.append('%s: image missing' % r['filename'])
        for key in ('title', 'museum', 'objectURL', 'imageURL', 'license', 'objectNumber'):
            if not r.get(key):
                problems.append('%s: no %s' % (r['filename'], key))
    ids = [r['objectNumber'] for r in records]
    if len(set(ids)) != len(ids):
        problems.append('duplicate object numbers')
    print('verify: %d records, %d images, %s' % (len(records), len(imgs), 'OK' if not problems else 'PROBLEMS'))
    for p in problems:
        print('   -', p)
    return not problems


if __name__ == '__main__':
    step = sys.argv[1] if len(sys.argv) > 1 else ''
    {'candidates': candidates, 'build': build, 'verify': verify}.get(step, lambda: sys.exit(__doc__))()
