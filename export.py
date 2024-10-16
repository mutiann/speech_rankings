import argparse
from jinja2 import Template
from markupsafe import escape
import json
from collections import defaultdict
import datetime

def main(args):
    publs = json.load(open('publications.json', 'r', encoding='utf-8'))
    authors = json.load(open('authors.json', 'r', encoding='utf-8'))
    exclude_venue = args.exclude_venue.split(',')
    publs.sort(key=lambda x: -x['tags']['year'])

    venue_appearances = defaultdict(set)
    for publ in publs:
        if not args.year_start <= publ['tags']['year'] <= args.year_end:
            continue
        venue_appearances[publ['tags']['venue']].add(publ['tags']['year'])
    shift_venues = []
    for venue, years in venue_appearances.items():
        if len(years) == 0 or max(years) < args.year_end:
            shift_venues.append(venue)

    for publ in publs:
        shift = 1 if publ['tags']['venue'] in shift_venues else 0
        if not args.year_start - shift <= publ['tags']['year'] <= args.year_end:
            continue
        if publ['tags']['venue'] in exclude_venue:
            continue
        for a in publ['authors']:
            pid, name = a['@pid'], a['text']
            a['pid'] = pid
            del a['@pid']
            if pid in authors:
                if 'tags' not in authors[pid]:
                    authors[pid]['tags'] = {'Year': defaultdict(int), 'Venue': defaultdict(int),
                                            'Interspeech': defaultdict(int), 'IEEE': defaultdict(int)}
                    authors[pid]['pubs'] = []
                for k, v in publ['tags'].items():
                    if k == 'year':
                        bin = 'Year'
                    elif k == 'venue':
                        bin = 'Venue'
                    elif k == 'track':
                        bin = 'Interspeech'
                    elif k.startswith('keyword:'):
                        bin = 'IEEE'
                        v = k[len('keyword:'):]
                    authors[pid]['tags'][bin][v] += 1
                authors[pid]['pubs'].append(publ)

    command = ' '.join(['--%s %s' % (k, v) for k, v in vars(args).items()])
    authors = [a for a in authors.values() if 'pubs' in a]
    if args.author_start_year is not None:
        authors = [a for a in authors if min([int(t) for t in a['years'].keys()]) >= args.author_start_year]
    authors.sort(key=lambda x: -len(x['pubs']))
    for i, a in enumerate(authors):
        if 'google' not in a:
            a['google'] = "https://www.google.com/search?q=" + a['name'] + " site:scholar.google.com"
        a['dblp'] = "https://dblp.uni-trier.de/pid/" + a['pid']
        for tag in a['tags']:
            a['tags'][tag] = list(a['tags'][tag].items())
            a['tags'][tag].sort(key=lambda x: -x[1])
        a['tags']['Year'].sort(key=lambda x: -x[0])
        a['pubs'] = a['pubs'][:args.n_pubs]
        a['rank'] = i + 1

        years = list(a['years_dedup'].items())
        years.sort(key=lambda x: -x[-1])
        a['years'] = years[:5]
    authors = authors[args.rank_start: args.rank_end]
    print(json.dumps([a['name'] for a in authors]))

    tm = Template(open('template.html').read())
    report = tm.render(authors=authors, command=command,
                       timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    open(args.output, 'w', encoding='utf-8').write(report)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    current_year = datetime.datetime.now().year
    parser.add_argument('--year-start', type=int, default=current_year - 5, help="Min year")
    parser.add_argument('--year-end', type=int, default=current_year, help="Max year")
    parser.add_argument('--year-shift', type=int, default=1,
                        help="Also consider the N years earlier than year-start if no paper is found at year-end;"
                             "suitable for cases when the conference of the current year is not yet held")
    parser.add_argument('--author-start-year', type=int, default=1900,
                        help="Only consider authors with their first paper after this year")
    parser.add_argument('--exclude-venue', type=str, default="SSW,ASRU,IWSLT,SLT",
                        help="Venues excluded, workshops by default")
    parser.add_argument('--n-pubs', type=int, default=20,
                        help="Number of listed publications per person")
    parser.add_argument('--rank-start', type=int, default=0,
                        help="Include authors ranked from")
    parser.add_argument('--rank-end', type=int, default=200,
                        help="Include authors ranked to")
    parser.add_argument('--output', type=str, default="speech_rankings.html", help="Output file")

    args, unparsed = parser.parse_known_args()
    print('unparsed:', unparsed)
    main(args)