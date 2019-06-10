import functools
from typing import Union, List
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from tabulate import tabulate
import os

# path to the list of files
CONFIG_FILENAME = '%s/series.txt' % os.path.dirname(os.path.realpath(__file__))

# strings found in next-episode.net pages
TBA = 'Sorry, no info about the next episode'
ENDED = 'Canceled/Ended'

# base url for downloading html
NEXT_EPISODE_URL = 'https://next-episode.net/'

# used for date parsing
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
          'August', 'September', 'October', 'November', 'December']


class Release:
    def __init__(self, season: str = None, episode_num: str = None, episode_name: str = None, date: datetime = None):
        self.season = season
        self.episode_num = episode_num
        self.episode_name = episode_name
        self.date = date

    def __str__(self):

        if not self.episode_num and not self.season:
            return ''
        if self.episode_num is None:
            e = self.episode_num
        elif ',' in self.episode_num:
            comma_separated = self.episode_num.split(',')
            e = f'E{comma_separated[0].strip()}-{comma_separated[-1].strip()}'
        elif not self.episode_num.isnumeric():
            e = f'"{self.episode_num}"'
        else:
            e = f'E{self.episode_num}'
        if self.date is not None:
            d = self.date.strftime('%Y-%m-%d')
        else:
            d = self.date
        return f'{d} S{self.season} {e}'


class Show:
    def __init__(self, show_id: str, previous: Release = None, next_: Release = None, error: Exception = None):
        self.show_id = show_id
        self.previous = previous
        self.next_ = next_
        self.error = error


def request_page(show_id: str):
    url = '%s%s' % (NEXT_EPISODE_URL, show_id)
    try:
        return requests.get(url).text
    except Exception as e:
        return e


def process_release(html, element_id: str):
    info = html.find(id=element_id)
    if not info:
        return Release()

    html_text = info.get_text()

    if element_id == 'next_episode':
        if TBA in html_text or ENDED in html_text:
            return Release()

    # extract lines from the html obj of interest
    element_lines = html_text.split('\n')

    # we're only interested in non-empty strings with a ':' char
    # (the : indicates a key-value pair)
    keyval_lines = [l for l in element_lines if l and ":" in l]

    # split each line by first ':' and trim the results
    keyval_pairs = [
        [v.strip() for v in keyval_line.split(':', 1)]
        for keyval_line in keyval_lines
    ]

    # transform the key-value lists into a python dict
    info_dict = {key: value for key, value in keyval_pairs}

    def parse_time(time_str: str):
        time = ' '.join(time_str.split(' ')[1:])
        for k in MONTHS:
            if k[:3] in time:
                time = datetime.strptime(time.replace(k[:3], k), '%B %d, %Y')
                break
        return time

    return Release(
        info_dict['Season'],
        info_dict['Episode'],
        info_dict['Name'],
        parse_time(info_dict['Date']) if 'Date' in info_dict else parse_time(info_dict['Local Date'])
    )


def process_page(show_id: str, page: Union[str, Exception]):
    if type(page) == Exception:
        return Show(show_id, error=page)
    try:
        html = BeautifulSoup(page, 'html.parser')
    except Exception as e:
        print(e)
        return Show(show_id, error=Exception("Failed to parse page: " + str(e)))
    try:
        prev = process_release(html, 'previous_episode')
    except:
        prev = None
    try:
        next_ = process_release(html, 'next_episode')
    except:
        next_ = None
    return Show(show_id, prev, next_)


def sort_shows(show_map):
    def customsort(a: Show, b: Show):
        a_next = a.next_.date if a.next_ else None
        b_next = b.next_.date if b.next_ else None
        a_prev = a.previous.date if a.previous else None
        b_prev = b.previous.date if b.previous else None
        if a_next:
            return a_next.timestamp() - b_next.timestamp() if b_next else -1
        elif b_next:
            return 1
        elif a_prev:
            return b_prev.timestamp() - a_prev.timestamp() if b_prev else -1
        return 1 if b_prev else 0

    return sorted([show_map[i] for i in show_map], key=functools.cmp_to_key(customsort))


def print_result(show_list: List[Show]):
    print(tabulate([[s.show_id, str(s.previous), str(s.next_)] for s in show_list],
                   ['Show ID', 'Previous release', 'Next release']))


def get_series_identifiers():
    with open(CONFIG_FILENAME) as f:
        return [l.strip() for l in f.read().split('\n')
                if l and len(l.strip()) > 0]


if __name__ == "__main__":
    # get list of shows from config file
    ids = get_series_identifiers()
    # parse Show instances from next-episode.net html pages
    shows = {show_id: process_page(show_id, request_page(show_id)) for show_id in ids}
    # sort the shows to the order in which they should be printed
    sorted_shows = sort_shows(shows)
    # finally, print the list of shows
    print_result(sorted_shows)
