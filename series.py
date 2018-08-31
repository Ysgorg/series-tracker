from urllib import request, parse
from bs4 import BeautifulSoup
from dateutil import parser
from datetime import datetime
import os

CONFIG_FILENAME = '%s/series.txt'%os.path.dirname(os.path.realpath(__file__))
TBA = 'Sorry, no info about the next episode'
ENDED = 'Canceled/Ended'
NEXT_EPISODE_URL = 'https://next-episode.net/'
FETCHING = 'Fetching info from %s ...%s'
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
'August', 'September', 'October', 'November', 'December']

class Episode:

    def __init__(self, id, max_id_length):
        self.time = None
        self.tba = False
        self.ended = False
        self.error = None
        self.id = id
        self.max_id_length = max_id_length
        html = self.request_page()
        if html:
            self.parse_page(html)

    def get_time_string(self, time):
        for k in MONTHS:
            if k[:3] in time:
                return datetime.strptime(time.replace(k[:3], k), '%B %d, %Y')

    def request_page(self):
        url = '%s%s' % (NEXT_EPISODE_URL, self.id)
        print(FETCHING % (url, ' ' * self.max_id_length), end='\r')
        try:
            return request.urlopen(url).read().decode('utf-8')
        except Exception as e:
            self.error = e

    def parse_page(self, html):

        if ENDED in html:
            self.ended = True
            return
        elif TBA in html:
            self.tba = True
            return
        info = BeautifulSoup(html, 'html.parser').find(id="next_episode")
        if info:
            lines = [l.strip() for l in info.get_text().split('\n') if l][1:-1]
            self.name = lines[0].split(':')[1]
            self.season = int(lines[3].split(':')[1])
            self.episode = int(lines[4].split(':')[1])
            self.time = self.get_time_string(' '.join(lines[2].split(' ')[1:]))
        else:
            self.error = Exception('No episode info found')

    def pretty(self):
        pre = '%s%s' % (self.id, ' ' * (self.max_id_length - len(self.id)))
        if self.tba:
            print('%s To be announced' % pre)
        elif self.ended:
            print('%s Ended or cancelled' % pre)
        elif self.error:
            print('%s Error: %s' % (pre, str(self.error)))
        else:
            episode_code = 'S%02dE%02d' % (self.season, self.episode)
            formated_time = str(self.time).split(' ')[0]
            print('%s %s %s' % (pre, episode_code, formated_time))

def getEpisodes(series_identifiers):
    max_id_length = max([len(i) for i in series_identifiers])
    spacing = (' ' * (max_id_length + 12))
    print('Downloading episode infos...')
    eps = [Episode(id, max_id_length) for id in series_identifiers]
    print('Downloaded info for all episodes%s' % spacing)
    return eps

def printEpisodes(episodes):
    print('- ' * 30)
    for e in sorted([e for e in episodes if e.time], key=lambda e: e.time):
        e.pretty()
    for e in sorted([e for e in episodes if e.tba], key=lambda e: e.id):
        e.pretty()
    for e in sorted([e for e in episodes if e.ended], key=lambda e: e.id):
        e.pretty()
    for e in sorted([e for e in episodes if e.error], key=lambda e: e.id):
        e.pretty()

def get_series_identifiers():
    with open(CONFIG_FILENAME) as f:
        return [l.strip() for l in f.read().split('\n')
                if l and len(l.strip()) > 0]

if __name__ == "__main__":
    printEpisodes(getEpisodes(get_series_identifiers()))
