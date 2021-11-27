import requests
import os
import json
import urllib

import xmltodict
from bs4 import BeautifulSoup
from collections import defaultdict
from requests import Session
import random

r = Session()

cache_path = r"cache"
os.makedirs(cache_path, exist_ok=True)

def get_headers():
    user_agents = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36",
                   "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:84.0) Gecko/20100101 Firefox/84.0",
                   "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36 Edg/87.0.664.66"] + \
                  ['Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)',
                   'Mozilla/5.0 (compatible; adidxbot/2.0; +http://www.bing.com/bingbot.htm)',
                   'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/534+ (KHTML, like Gecko) BingPreview/1.0b']
    headers = {'User-Agent': random.choice(user_agents)}
    return headers

def get_page(url, params, cache_dir, do_render=False):
    os.makedirs(cache_dir, exist_ok=True)
    key = urllib.parse.quote(url + urllib.parse.urlencode(params), safe="")
    if os.path.exists(os.path.join(cache_dir, key)):
        page_text = open(os.path.join(cache_dir, key), encoding="utf-8").read()
    else:
        page = r.get(url, params=params, headers=get_headers())
        if do_render:
            page.html.render()
        if page.status_code != 200:
            raise ValueError(page.status_code)
        page_text = page.content.decode('utf-8')
        if 'IEEE Xplore Temporarily Unavailable' in page_text:
            raise ValueError(page.status_code)
        open(os.path.join(cache_dir, key), 'w', encoding="utf-8").write(page_text)
    return page_text

def get_dblp_page(url, key):
    params = {'q': key, 'format': 'json', 'h': 1000, 'f': 0}
    result = []
    while True:
        response = get_page(url, params, os.path.join(cache_path, 'responses'))
        response = json.loads(response)['result']
        if 'hit' in response['hits']:
            result.extend(response['hits']['hit'])
        if int(response['hits']['@sent']) + int(response['hits']['@first']) >= int(response['hits']['@total']):
            break
        params['f'] += 1000
    return result

def get_ieee_meta(url):
    page = get_page(url, {}, os.path.join(cache_path, 'ieee'))
    ml = None
    for l in page.splitlines():
        l = l.strip('\t')
        if l.startswith('xplGlobal.document.metadata='):
            ml = l[len('xplGlobal.document.metadata='):]
            break
    if ml is None:
        raise ValueError(url)
    meta = json.loads(ml.strip(';'))
    topics = [t['name'] for t in meta['pubTopics']]
    meta = {'authors': meta['authors'], 'keywords': meta.get('keywords', []), 'topics': topics, 'id': meta['htmlAbstractLink']}
    return meta

def get_interspeech_tracks(url):
    page = get_page(url, {}, os.path.join(cache_path, 'isca'))
    page = BeautifulSoup(page)

    tracks = defaultdict(list)
    for sec in page.find_all('div', attrs={'class': 'w3-card'}):
        heading = sec.text.strip('\n').splitlines()[0].strip().replace("—", ':')
        if ':' in heading:
            heading = heading.split(':')[0].strip()
        ends = ["1, 2", "I, II", "I-III", "I-IV", "I", "II", "III", "1", "2", "3", "4", "5", "oral", "poster",
                "Oral", "Poster", "-"]
        for e in ends:
            if heading.endswith(' ' + e) or heading.endswith('-' + e):
                heading = heading[:-len(e) - 1]

        for paper in sec.find_all('a'):
            name = paper.text.strip('\n').splitlines()[0].strip()
            tracks[heading].append(name)
    return tracks

def get_author_info(pid):
    url = r"https://dblp.uni-trier.de/pid/" + pid + ".xml"
    page = get_page(url, {}, os.path.join(cache_path, 'responses'))
    info = xmltodict.parse(page, force_list=('note', 'url', 'author', 'r'))['dblpperson']
    papers = info['r']
    info = info['person']
    result = {'affiliation': [], 'url': [], 'pid': pid, 'name': info['author'][0]['#text']}
    exclude_url = ['orcid.org', 'wikidata.org', 'scopus.com', 'researchgate.net', 'semanticscholar.org',
                   'wikipedia.org', 'isni.org', 'viaf.org', 'id.loc.gov']
    if 'note' in info:
        for n in info['note']:
            if n['@type'] == 'affiliation':
                afn = n['#text']
                if '@label' in n:
                    afn += ' (' + n['@label'] + ')'
                result['affiliation'].append(afn)
            else:
                print(n)
    if 'url' in info:
        for url in info['url']:
            if any([t in url for t in exclude_url]):
                continue
            result['url'].append(url)

    year_cnt = defaultdict(int)
    for paper in papers:
        k = list(paper.keys())[0]
        assert len(paper.keys()) == 1
        year = int(paper[k]['year'])
        year_cnt[year] += 1
    result['years'] = year_cnt
    return result
