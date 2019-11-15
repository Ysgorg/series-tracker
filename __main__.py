import logging
from typing import Union, List
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from tabulate import tabulate

class Release:
    def __init__(self, season: str = None, episode_num: str = None, episode_name: str = None, date: datetime = None):
        self.season = season
        self.episode_num = episode_num
        self.episode_name = episode_name
        self.date = date

    def __str__(self):
        # Todo write this more elegantly
        if not self.episode_num and not self.season:
            return ''
        if self.episode_num is None:
            e = self.episode_num
        elif ',' in self.episode_num:
            first, *, last = [x.strip() for x in self.episode_num.split(',')]
            e = f'E{first}-{last}'
        elif not self.episode_num.isnumeric():
            e = f'"{self.episode_num}"'
        else:
            e = f'E{self.episode_num}'

        if self.date is not None:
            d = self.date.strftime('%Y-%m-%d')
        else:
            d = self.date
        
        return f'{d} S{self.season} {e}'

    def __gt__(self, other):
        '''Compare 2 Releases with each other, required for ordinality on releases'''
        if other.date is None:
            return False
        
        if self.date is None:
            return False

        return self.date > other.date


class Show:
    def __init__(self, show_id: str, previous: Release = Release(), next_: Release = Release(), error: Exception = None):
        self.show_id = show_id
        self.previous = previous
        self.next_ = next_
        self.error = error

def get_series_identifiers(filename):
    try:
        with open(filename) as config_file:
            for line in map(str.strip, config_file):
                if not line:
                    continue

                yield line.replace(' ', '-').lower()

    except OSError as oe:
        logging.critical(
            'Received error while reading from %r: %s' % (filename, oe))

    return
    yield

def parse_episode_data(raw):
    parsed = dict(l.strip().split(':') for l in raw.split('\n') if ':' in l)
    date = parsed.get('Date', parsed.get('Local Date', ''))
    if not date:
        return Release()

    return Release(
        parsed['Season'],
        parsed['Episode'],
        parsed['Name'],
        date=datetime.strptime(date, '%a %b %d, %Y')
    )

def get_show_data(show_name):
    url = 'https://next-episode.net/%s' % (show_name)
    try:
        html = requests.get(url).text
    except Exception as e:
        logging.info("Failed to reach url %r" % url)
        return Show(show_name, error=e)

    try:
        soup = BeautifulSoup(html, 'html.parser')
    except Exception as e:
        return Show(show_name, error=Exception("Failed to parse page: %s" % e))

    if soup.select_one('#previous_episode') is None:
        return Show(show_name, Release(), Release())

    return Show(show_name,
       parse_episode_data(soup.select_one('#previous_episode').get_text()),
       parse_episode_data(soup.select_one('#next_episode').get_text())
    )

def main(arguments):
    # Get the positional argument series
    shows = [name.replace(' ', '-').lower() for name in arguments.shows]

    # Get list of shows from config file and add if it was given as command line argument
    if arguments.config:
        shows.extend(get_series_identifiers(arguments.config))

    # If list of shows is empty print warning and quit
    if not shows:
        logging.info("No shows found")
        return

    # parse Show instances from next-episode.net html pages
    show_data = {name: get_show_data(name) for name in shows}

    # sort the shows to the order in which they should be printed
    sorted_shows = sorted(show_data.values(), key=lambda s:(s.next_, s.previous))

    # finally, print the list of shows
    headers = ['Show ID', 'Previous release', 'Next release']
    data = [[s.show_id, str(s.previous), str(s.next_)] for s in sorted_shows]
    print(tabulate(data, headers, tablefmt=arguments.format))

if __name__ == "__main__":
    import argparse

    logging.basicConfig(format='[%(asctime)s] \033[1;34m%(message)s\033[0m',
                        datefmt='%Y-%m-%d %H:%M:%S', level=logging.INFO)
    PARSER = argparse.ArgumentParser()
    PARSER.add_argument(
        '-c', '--config', help='a file pointing to a list of series, newline separated')
    PARSER.add_argument('-f', '--format', choices="plain simple github grid fancy_grid pipe orgtbl jira presto psql rst mediawiki moinmoin youtrack html latex latex_raw latex_booktabs textile".split(), default="plain", help="table of output format")
    PARSER.add_argument('shows', nargs='*', default=[], help='series names')
    main(PARSER.parse_args())
