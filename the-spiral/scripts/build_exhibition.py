#!/usr/bin/env python3
"""
Curiosity Loop - "life, death, transformation, return" exhibition builder.

Reads the hand-curated  exhibition/curation.json  (order = spiral order, centre first)
and writes:
    exhibition/images/001.jpg ...            1600px long side, aspect kept, never cropped
    exhibition/metadata/artworks.json/.csv   one record per place in the spiral
    exhibition/metadata/README.md            sources, licences, description provenance

Sources (official APIs only):
    met      The Met Open Access API         (isPublicDomain = true)
    cma      Cleveland Museum of Art API     (share_license_status = CC0)
    commons  Wikimedia Commons API           (licence must be Public domain)

Titles, dates and makers come from the museum record. For Commons files, whose
metadata is uneven, they come from curation.json, checked by hand against the file
description. Descriptions come from curation.json, each tagged with its source.

    python3 scripts/build_exhibition.py
"""

import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from download_artworks import met_record, cma_record, download  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
EX = os.path.join(ROOT, 'exhibition')
IMAGES = os.path.join(EX, 'images')
META = os.path.join(EX, 'metadata')
UA = 'CuriosityLoop/1.0 (IXD415 class project)'
COMMONS = 'https://commons.wikimedia.org/w/api.php'


def commons_info(filename):
    url = COMMONS + '?' + urllib.parse.urlencode({
        'action': 'query', 'format': 'json', 'titles': 'File:' + filename,
        'prop': 'imageinfo', 'iiprop': 'url|size|extmetadata', 'iiurlwidth': 1600})
    r = subprocess.run(['curl', '-s', '-m', '40', '-A', UA, url], capture_output=True)
    pages = json.loads(r.stdout)['query']['pages']
    page = next(iter(pages.values()))
    ii = (page.get('imageinfo') or [None])[0]
    if not ii:
        return None
    em = ii.get('extmetadata', {})
    lic = re.sub('<[^>]+>', '', (em.get('LicenseShortName') or {}).get('value', '')).strip()
    return {'license': lic, 'page': ii.get('descriptionurl'), 'original': ii.get('url'),
            'download': ii.get('thumburl') or ii.get('url')}


def build():
    with open(os.path.join(EX, 'curation.json'), encoding='utf-8') as f:
        cur = json.load(f)
    os.makedirs(IMAGES, exist_ok=True)
    os.makedirs(META, exist_ok=True)
    for old in os.listdir(IMAGES):
        if old.endswith('.jpg'):
            os.remove(os.path.join(IMAGES, old))

    records = []
    for n, w in enumerate(cur['works'], 1):
        fn = '%03d.jpg' % n
        if w.get('repeatOf'):
            # the same work returning: same image, same record, new place in the spiral
            src = records[w['repeatOf'] - 1]
            shutil.copyfile(os.path.join(IMAGES, src['filename']), os.path.join(IMAGES, fn))
            rec = dict(src, id=n, filename=fn, stage=w['stage'], repeatOf=src['filename'],
                       description=w['description'], descriptionSource=w['descriptionSource'])
            records.append(rec)
            print('%s  (return of %s) %s' % (fn, src['filename'], rec['title']))
            continue

        if w['source'] in ('met', 'cma'):
            raw = met_record(w['id']) if w['source'] == 'met' else cma_record(w['id'])
            if raw is None:
                sys.exit('!! %s %s is not open access / has no image' % (w['source'], w['id']))
            rec = {
                'title': raw['title'], 'artist': raw['maker'] or raw['culture'], 'date': raw['date'],
                'medium': raw['medium'], 'culture': raw['culture'], 'museum': raw['museum'],
                'objectNumber': raw['objectNumber'], 'objectURL': raw['objectURL'],
                'imageURL': raw['imageURL'], 'license': raw['license'], 'creditLine': raw['creditLine'],
            }
            url = raw['downloadURL']
        else:
            info = commons_info(w['file'])
            if info is None or info['license'].lower() != 'public domain':
                sys.exit('!! Commons file is missing or not public domain: %s (%s)'
                         % (w['file'], info and info['license']))
            rec = {
                'title': w['title'], 'artist': w['artist'], 'date': w['date'], 'medium': w.get('medium'),
                'culture': None, 'museum': w['museum'], 'objectNumber': w.get('objectNumber'),
                'objectURL': info['page'], 'imageURL': info['original'],
                'license': 'Public domain (Wikimedia Commons; artist died 1944)', 'creditLine': None,
            }
            url = info['download']

        tmp = os.path.join(IMAGES, '_download')
        if not download(url, tmp):
            sys.exit('!! image download failed: %s' % url)
        subprocess.run(['sips', '-Z', '1600', '-s', 'format', 'jpeg', '-s', 'formatOptions', '85',
                        tmp, '--out', os.path.join(IMAGES, fn)], capture_output=True, check=True)
        os.remove(tmp)
        rec = dict({'id': n, 'filename': fn, 'stage': w['stage'], 'source': w['source']}, **rec)
        rec['description'] = w['description']
        rec['descriptionSource'] = w['descriptionSource']
        records.append(rec)
        print('%s  %-7s %-7s %s' % (fn, w['stage'], w['source'], (rec['title'] or '')[:64]))
        time.sleep(0.2)

    with open(os.path.join(META, 'artworks.json'), 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    fields = ['id', 'filename', 'stage', 'title', 'artist', 'date', 'medium', 'culture', 'museum',
              'objectNumber', 'objectURL', 'imageURL', 'license', 'creditLine', 'description',
              'descriptionSource', 'repeatOf']
    with open(os.path.join(META, 'artworks.csv'), 'w', newline='', encoding='utf-8') as f:
        wr = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        wr.writeheader()
        for r in records:
            wr.writerow({k: ('' if r.get(k) is None else r.get(k)) for k in fields})
    write_readme(cur, records)
    verify(records)


def write_readme(cur, records):
    L = ['# ' + cur['title'], '', cur['concept'], '',
         '## The spiral, from the centre outward', '']
    stage = None
    for r in records:
        if r['stage'] != stage:
            stage = r['stage']
            L += ['', '### ' + stage.capitalize(), '']
        L.append('- `%s` **%s**, %s, %s. %s. [source](%s). %s.%s' % (
            r['filename'], r['title'], r['artist'] or 'unknown maker', r['date'] or 'n.d.',
            r['museum'], r['objectURL'], r['license'],
            ' (returns: same work as `%s`)' % r['repeatOf'] if r.get('repeatOf') else ''))
    L += ['', '## Sources and licences', '',
          '- **Cleveland Museum of Art**: Open Access API, CC0 works only.',
          '- **The Metropolitan Museum of Art**: Open Access API, public-domain works only (CC0).',
          '- **Wikimedia Commons**: public-domain scans and photographs of works by Hilma af Klint',
          '  (1862–1944), held by the Hilma af Klint Foundation, Stockholm. Only files that Commons marks',
          '  public domain were used; each record links to its file page.',
          '- Robert Smithson and Ana Mendieta are conceptual references only. Their work is still in',
          '  copyright, so it is not reproduced here.', '',
          '## Descriptions', '',
          'Each record has a `descriptionSource`:', '']
    for k, v in cur['descriptionSources'].items():
        L.append('- `%s`: %s' % (k, v))
    L += ['', 'Titles, dates and makers come from the museum record (for Commons files, from the file',
          'description, checked by hand). Nothing is invented; missing fields are `null`.', '']
    with open(os.path.join(META, 'README.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(L))


def verify(records):
    imgs = sorted(fn for fn in os.listdir(IMAGES) if fn.endswith('.jpg'))
    problems = []
    if len(records) != len(imgs):
        problems.append('%d records but %d images' % (len(records), len(imgs)))
    for r in records:
        for key in ('title', 'date', 'artist', 'description', 'descriptionSource', 'museum', 'objectURL', 'license'):
            if not r.get(key):
                problems.append('%s: no %s' % (r['filename'], key))
        if r['filename'] not in imgs:
            problems.append('%s: image missing' % r['filename'])
    if records and records[0]['objectURL'] != records[-1]['objectURL']:
        problems.append('the spiral does not end on the work it began with')
    print('verify: %d records, %d images, %s' % (len(records), len(imgs), 'OK' if not problems else 'PROBLEMS'))
    for p in problems:
        print('   -', p)


if __name__ == '__main__':
    build()
