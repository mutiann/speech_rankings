import os
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import tqdm
from functools import partial
import time
import datetime
import html
import traceback as tb
import re

import unidecode
import pandas as pd

from fetch import *

current_year = datetime.date.today().year
start_year = current_year - 10

def read_series(issue_start, issue_end, pattern, name, issue_to_year=None):
    base_url = r"https://dblp.org/search/publ/api"
    results = defaultdict(list)
    for issue in tqdm.trange(issue_start, issue_end, desc=name):
        if isinstance(pattern, str):
            key = pattern % issue
        else:
            key = pattern(issue)
        result = get_dblp_page(base_url, key)
        if not result:
            continue
        for i in range(len(result)):
            item = result[i]['info']
            if 'title' in item:
                item['title'] = html.unescape(item['title'])
            else:
                print("Missing title:", item['url'])
        result = [r for r in result if 'title' in r['info']]
        if issue_to_year is not None:
            issue = issue_to_year(issue)
        results[issue].extend(result)
    return results


patterns = {

    "SpeechComm": r"toc:db/journals/speech/speech%d.bht:",
    "TASLP": r"toc:db/journals/taslp/taslp%d.bht:",

    "ICASSP": r"toc:db/conf/icassp/icassp%d.bht:",
    "Interspeech": r"toc:db/conf/interspeech/interspeech%d.bht:",

    "ICML": r"toc:db/conf/icml/icml%d.bht:",
    "NeurIPS": lambda
        year: r"toc:db/conf/nips/neurips%d.bht:" % year if year >= 2020 else r"toc:db/conf/nips/nips%d.bht:" % year,
    "ICLR": r"toc:db/conf/iclr/iclr%d.bht:",
    "AAAI": r"toc:db/conf/aaai/aaai%d.bht:",
    "IJCAI": r"toc:db/conf/ijcai/ijcai%d.bht:",
    "KDD": r"toc:db/conf/kdd/kdd%d.bht:",

    "ACL": lambda
        year: r"toc:db/conf/acl/acl%d-1.bht:" % year if year >= 2012 and year != 2020 else r"toc:db/conf/acl/acl%d.bht:" % year,
    "EMNLP": lambda
        year: r"toc:db/conf/emnlp/emnlp%d-1.bht:" % year if 2019 <= year <= 2021 else r"toc:db/conf/emnlp/emnlp%d.bht:" % year,
    "NAACL": lambda year: r"toc:db/conf/naacl/naacl%d-1.bht:" % year if year in (
    2018, 2019) else r"toc:db/conf/naacl/naacl%d.bht:" % year,

    "ACL-Findings": r"toc:db/conf/acl/acl%df.bht:",
    "EMNLP-Findings": r"toc:db/conf/emnlp/emnlp%df.bht:",
    "NAACL-Findings": r"toc:db/conf/naacl/naacl%df.bht:",

    "SSW": r"toc:db/conf/ssw/ssw%d.bht:",
    "ASRU": r"toc:db/conf/asru/asru%d.bht:",
    "IWSLT": r"toc:db/conf/iwslt/iwslt%d.bht:",
    "SLT": r"toc:db/conf/slt/slt%d.bht:",

}


# Consider past 20 years by default
def collect_publ_data():
    cache_dir = os.path.join(cache_path, 'publ_all')
    os.makedirs(cache_dir, exist_ok=True)
    for key in patterns:
        if key == "SpeechComm":
            l, r = 55, 164  # 2014~2024

            def issue_to_year(issue):
                if 18 <= issue <= 47:
                    year = 2005 - (47 - issue) // 3
                elif 48 <= issue <= 55:
                    year = 2013 - (55 - issue)
                elif issue > 55:
                    year = (issue - 55) // 10 + 2014
                else:
                    raise ValueError("Unsupported issue %d" % issue)
                return year
        elif key == "TASLP":
            l, r = 22, current_year - 1992 + 1

            def issue_to_year(issue):
                return 2021 - (29 - issue)
        else:
            l, r = start_year, current_year + 1
            issue_to_year = None

        results = read_series(l, r, patterns[key], key, issue_to_year)

        print("Missing in %s:" % key, [k for k in range(start_year, current_year + 1) if k not in results or len(results[k]) == 0])
        json.dump(results, open(os.path.join(cache_dir, '%s.json' % key), 'w', encoding='utf-8'), ensure_ascii=False,
                  indent=1)


def filter_non_speech_venue():
    speech_venues = ['TASLP', 'SpeechComm', 'Interspeech', 'ICASSP', 'SSW', 'ASRU', 'IWSLT', 'SLT']
    cache_dir = os.path.join(cache_path, 'publ_filtered')
    os.makedirs(cache_dir, exist_ok=True)
    for k in patterns:
        if os.path.exists(os.path.join(cache_path, 'publ_ex', '%s.json' % k)):
            publ = json.load(open(os.path.join(cache_path, 'publ_ex', '%s.json' % k), 'r', encoding='utf-8'))
        else:
            publ = json.load(open(os.path.join(cache_path, 'publ_all', '%s.json' % k), 'r', encoding='utf-8'))
        if k not in speech_venues:
            years = list(publ.keys())
            for year in years:
                print(k, year)
                results = []
                for item in publ[year]:
                    title = item['info'].get('title', '').lower()
                    title = ''.join([(t if t.isalnum() else ' ') for t in title ]).strip()
                    title = re.sub(r'\s+', ' ', title)
                    if ('speech' in title or ' asr ' in title or ' tts ' in title or 'speaker' in title or 'prosody' in title or 'audio' in title or 'voice' in title or 'waveform' in title or 'acoustic' in title or 'spoken' in title) \
                            and not ('hate' in title or 'part of speech' in title or 'wavelet' in title or 'imaging' in title or 'parts of speech' in title or 'part of speech' in title or 'invited speakers' in title or 'keynote speaker' in title or 'speaker commitment' in title or 'native speaker' in title or 'waveform inversion' in title or 'blood' in title):
                        print(item['info']['title'])
                        results.append(item)
                publ[year] = results
        json.dump(publ, open(os.path.join(cache_dir, '%s.json' % k), 'w', encoding='utf-8'), ensure_ascii=False,
                  indent=1)

def collect_ieee_keywords():
    ieee_venues = ['ICASSP', 'TASLP', 'ASRU', 'SLT']
    cache_dir = os.path.join(cache_path, 'publ_ex')
    os.makedirs(cache_dir, exist_ok=True)
    executor = ThreadPoolExecutor(max_workers=4)

    for k in ieee_venues:
        publ = json.load(open(os.path.join(cache_path, 'publ_all', '%s.json' % k), 'r', encoding='utf-8'))
        years = list(publ.keys())
        for year in tqdm.tqdm(years, desc=k):
            if int(year) < start_year:
                continue

            futures = []
            for item in publ[year]:
                url = item['info']['ee']
                title = item['info']['title'].lower().replace('-', '')
                if item['info']['type'] == 'Editorship':
                    continue
                if k in ['ICASSP', 'TASLP']:
                    keys = [' sensor ', ' point cloud', ' reid', 'beamform', ' mimo ', 'radar', 'signal recovery',
                            'wireless', 'image compression', 'video compression', 'phase retrieval',
                            'compressed sensing', '3d', 'super resolution', 'microphone',
                            'superresolution', 'facial', ' face ', 'coding', 'ctscan', 'ct scan', 'medical',
                            'broadband', ' dsp ', 'remote sensing', ' array', ' doa ', ' time series ',
                            'anomaly detection', 'narrowband', 'sparse decomposition', 'matrix decomposition',
                            'matrix completion']
                    if any([t in title for t in keys]):
                        # print("Skip by title:", item['info']['title'])
                        continue
                futures.append((item, executor.submit(partial(get_ieee_meta, url))))
            print("%d/%d papers skipped" % (len(publ[year]) - len(futures), len(publ[year])))
            for item, f in futures:
                try:
                    meta = f.result()
                except:
                    tb.print_exc()
                    print(item['info']['ee'], item['info']['title'])
                    time.sleep(0.5)
                    continue
                keywords = []
                for kwds in meta['keywords']:
                    # if 'type' not in kwds or kwds['type'].strip() in ('IEEE Keywords', 'Author Keywords'):
                    keywords.extend([t.lower().strip(' ').strip('.').replace('-', ' ') for t in kwds['kwd']])
                keywords = set(keywords)
                item['info']['keywords'] = list(keywords)
                item['info']['ieee_meta'] = meta
            # print("Appeared keywords:", kw_count.keys())
        json.dump(publ, open(os.path.join(cache_dir, '%s.json' % k), 'w', encoding='utf-8'), ensure_ascii=False,
                  indent=1)


def collect_interspeech_track():
    cache_dir = os.path.join(cache_path, 'publ_ex')
    os.makedirs(cache_dir, exist_ok=True)
    publ = json.load(open(os.path.join(cache_path, 'publ_all', 'Interspeech.json'), 'r', encoding='utf-8'))
    years = list(publ.keys())
    base_url = r"https://www.isca-archive.org/interspeech_%s/index.html"
    escapes = {'&quot;': r'"', '²': r"'", '&amp;': '&', '&apos;': r"'", ', 000': ',000', ', ..': ',..'}
    for year in tqdm.tqdm(years):
        if year == '2002':
            url = r'https://www.isca-archive.org/icslp_2002/index.html'
        elif year == '2003':
            url = r'https://www.isca-archive.org/eurospeech_2003/index.html'
        else:
            url = base_url % year
        tracks = get_interspeech_tracks(url)
        paper_to_track = {}
        for tr in tracks:
            for pl in tracks[tr]:
                pl = pl.lower().replace(' : ', ' - ').replace(': ', ' - ').replace(' :', ' - ').replace(':', ' - ')\
                    .replace('“', '"').replace('”', '"').\
                    replace('‘', "'").replace("’", "'").replace('—', '-').replace('²', "'").replace('', "'").\
                    replace('^', '').replace("`", "'").strip(".").replace('  ', ' ')
                pl = unidecode.unidecode(pl)
                pl = ''.join([p for p in pl if p.islower()])
                if pl in paper_to_track:
                    print("Duplicate:", pl, '|', paper_to_track[pl], '|', tr)
                paper_to_track[pl] = tr.lower()
        n_missing = 0
        for paper in publ[year]:
            title = paper['info']['title'].lower().strip('.')
            title = title.replace("Auotmatic", "Automatic") # Some mysterious typo in IS2022
            for k in escapes:
                title = title.replace(k, escapes[k])
            if ' - ' in title and title[0] == '"':
                pos = title.find('-') - 2
                if title[pos] == '"':
                    title = title[1:pos] + title[pos + 1:]
            title = unidecode.unidecode(title)
            title = ''.join([p for p in title if p.islower()])
            if title not in paper_to_track:
                print("Missing:", paper['info']['title'])
                n_missing += 1
                continue
            paper['info']['isca_track'] = paper_to_track[title]
        print("Year %s: %d/%d missing" % (year, n_missing, len(publ[year])))
        print(tracks.keys())
    json.dump(publ, open(os.path.join(cache_dir, 'Interspeech.json'), 'w', encoding='utf-8'), ensure_ascii=False,
              indent=1)

def filter_non_speech_paper():
    mixed_venues = ['TASLP', 'ICASSP']
    cache_dir = os.path.join(cache_path, 'publ_filtered')
    os.makedirs(cache_dir, exist_ok=True)
    accept_keywords = set(['speech', 'speaker', 'spoken', 'voice', 'asr', 'tts', 'vocoder'])
    for venue in patterns:
        if venue in mixed_venues:
            publ = json.load(open(os.path.join(cache_path, 'publ_ex', '%s.json' % venue), 'r', encoding='utf-8'))
            years = list(publ.keys())
            for year in years:
                results = []
                kw_count = defaultdict(int)
                kw_publ = defaultdict(list)
                publ_kw_count = defaultdict(list)

                for item in publ[year]:
                    keywords = item['info'].get('keywords', [])
                    if keywords and any(['natural language' in kw or accept_keywords.intersection(kw.split(' ')) for kw in keywords]):
                        results.append(item)
                        continue
                    if keywords is None:
                        keywords = ['']
                    publ_kw_count[len(keywords)].append(item)
                    for kw in keywords:
                        kw_count[kw] += 1
                        kw_publ[kw].append(item['info']['title'])
                print(venue, year, len(results), len(publ[year]))
                publ[year] = results
                if len(results) == 0:
                    continue
                kw_publ = list(kw_publ.items())
                kw_publ.sort(key=lambda x: -len(x[1]))
            json.dump(publ, open(os.path.join(cache_dir, '%s.json' % venue), 'w', encoding='utf-8'), ensure_ascii=False,
                      indent=1)

exclude_keywords = ["speech processing", "learning (artificial intelligence)", "feature extraction",
                    "conferences", "signal processing", "neural nets", "acoustics", "statistical analysis",
                    "acoustic signal processing", "vectors", "training", "deep learning", "neural networks"]
def aggregate():
    results = []
    for venue in patterns:
        publ = json.load(open(os.path.join(cache_path, 'publ_filtered', '%s.json' % venue), 'r', encoding='utf-8'))
        for year in publ:
            for item in publ[year]:
                item = item['info']
                if 'authors' not in item or item['type'] == 'Editorship':
                    continue
                authors = item['authors']['author']
                if isinstance(authors, dict):
                    authors = [authors]
                meta = {'title': item['title'], 'key': item['key'], 'url': item['ee'] if 'ee' in item else item['url'],
                        'authors': authors}
                tags = {'year': int(year), 'venue': venue}
                if 'ieee_meta' in item:
                    keywords = item['ieee_meta']['keywords']
                    keywords = dict([(t.get('type', '').strip(), t['kwd']) for t in keywords])
                    kwd = []
                    if 'INSPEC: Controlled Indexing' in keywords:
                        kwd.extend(keywords['INSPEC: Controlled Indexing'])
                    elif 'IEEE Keywords' in keywords:
                        kwd.extend(keywords['IEEE Keywords'])
                    if 'Author Keywords' in keywords:
                        kwd.extend(keywords['Author Keywords'])
                    kwd = set([k.lower().replace('-', ' ') for k in kwd]).difference(exclude_keywords)
                    for k in kwd:
                        tags['keyword:' + k] = ''
                if 'isca_track' in item:
                    tags['track'] = item['isca_track']
                meta['tags'] = tags
                results.append(meta)

    json.dump(results, open('publications.json', 'w', encoding='utf-8'), ensure_ascii=False,
              indent=1)

def collect_author_info():
    publs = json.load(open('publications.json', 'r', encoding='utf-8'))
    results = {}
    # df = pd.read_csv('csrankings.csv') # Not used, since almost all authors are not in CSRankings
    n_csr = 0
    paper_cnt = defaultdict(int)

    for publ in tqdm.tqdm(publs):
        for author in publ['authors']:
            pid = author['@pid']
            paper_cnt[pid] += 1

    target_pids = [k for k in paper_cnt if paper_cnt[k] >= 10]
    executor = ThreadPoolExecutor(max_workers=2)
    futures = [(pid, executor.submit(partial(get_author_info, pid))) for pid in target_pids]

    for pid, f in tqdm.tqdm(futures):
        info = f.result()
        for url in info['url']:
            if 'scholar.google.com' in url:
                info['google'] = url
        # row = df.loc[df['name'] == author['text']]
        # if len(row) > 0:
        #     row = row.iloc[0]
        #     info['csr_aff'] = row['affiliation']
        #     info['homepage'] = row['homepage']
        #     info['google'] = "https://scholar.google.com/citations?user=" + row['scholarid']
        #     n_csr += 1

        results[pid] = info

    print("Total %d authors, %d in CSRankings" % (len(target_pids), n_csr))
    json.dump(results, open('authors.json', 'w', encoding='utf-8'), ensure_ascii=False,
              indent=1)

if __name__ == '__main__':
    collect_publ_data()
    collect_ieee_keywords()
    collect_interspeech_track()

    filter_non_speech_venue()
    filter_non_speech_paper()

    aggregate()

    collect_author_info()