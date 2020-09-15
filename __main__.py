import logging
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from tabulate import tabulate

HOWEVER = "However, our last information about it is this:"


class Release:
    def __init__(self, season: str = None, episode_num: str = None, episode_name: str = None, date: datetime = None,
                 source_site: str = None, source_date: str = None, quote: str = None, error: Exception = None):
        self.season = season
        self.episode_num = episode_num
        self.episode_name = episode_name
        self.date = date
        self.source_site = source_site
        self.source_date = source_date
        self.quote = quote
        self.error = error

    def __str__(self):
        # Todo write this more elegantly
        if not self.episode_num and not self.season:
            if self.quote:
                ref = ', '.join([i for i in [self.source_site, self.source_date] if i])
                source_str = f' ({ref})' if ref else ''
                return f'{self.quote}{source_str}'
            if self.error:
                return str(self.error)
            return ''
        if self.episode_num is None:
            e = self.episode_num
        elif ',' in self.episode_num:
            first, *x, last = [x.strip() for x in self.episode_num.split(',')]
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
        """Compare 2 Releases with each other, required for ordinality on releases"""
        if other.date is None:
            return False

        if self.date is None:
            return False

        return self.date > other.date


class Show:
    def __init__(self, show_id: str, previous: Release = Release(), next_: Release = Release(),
                 error: Exception = None):
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


def parse_episode_data(raw):
    try:
        if HOWEVER in raw:
            # they got some quote indicating the show's status
            info_str = raw.split(HOWEVER)[1].split(":", 1)
            source_strs = info_str[0].split(",", 1)
            source_site = source_strs[0].strip()
            source_date = source_strs[1].strip()
            quote = info_str[1].strip()
            return Release(quote=quote, source_site=source_site, source_date=source_date)

        parsed = dict(line.strip().split(':', 1) for line in raw.split('\n') if ':' in line)
        date = parsed.get('Date', parsed.get('Local Date', ''))

        if not date:
            return Release()

        return Release(
            parsed['Season'],
            parsed['Episode'],
            parsed['Name'],
            date=datetime.strptime(date, '%a %b %d, %Y')
        )
    except Exception as e:
        # the response is of some unaccounted-for format.
        # this is bound to happen periodically since the parsing is tailored
        # for content that we don't have control over
        return Release(error=e)


def get_show_data(show_name):
    url = 'https://next-episode.net/%s' % show_name
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

    return Show(
        show_name,
        parse_episode_data(soup.select_one('#previous_episode').get_text()),
        parse_episode_data(soup.select_one('#next_episode').get_text())
    )


def show_sort(a: Show, b: Show):
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
    sorted_shows = sorted(show_data.values(), key=lambda s: (s.next_, s.previous))

    # finally, print the list of shows
    headers = ['Show ID', 'Previous release', 'Next release']
    data = [[s.show_id, str(s.previous), str(s.next_)] for s in sorted_shows]
    print(tabulate(data, headers, tablefmt=arguments.format))


if __name__ == "__main__":
    import argparse

    logging.basicConfig(format='[%(asctime)s] \033[1;34m%(message)s\033[0m',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.INFO)
    PARSER = argparse.ArgumentParser()
    PARSER.add_argument('-c', '--config', help='a file pointing to a list of series, newline separated')
    PARSER.add_argument('-f', '--format',
                        choices="plain simple github grid fancy_grid pipe orgtbl jira presto psql rst mediawiki "
                                "moinmoin youtrack html latex latex_raw latex_booktabs textile".split(),
                        default="plain",
                        help="table of output format")
    PARSER.add_argument('shows', nargs='*', default=[], help='series names')
    main(PARSER.parse_args())
