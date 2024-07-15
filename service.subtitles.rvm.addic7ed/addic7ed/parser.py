## Copyright (C) 2013, Roman Miroshnychenko aka Roman V.M.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import re
from collections import namedtuple

from bs4 import BeautifulSoup

from addic7ed.exceptions import SubsSearchError, ParseError
from addic7ed.webclient import Session

__all__ = [
    'search_episode',
    'get_episode',
    'parse_filename',
    'normalize_showname',
    'get_languages',
]

session = Session()

SubsSearchResult = namedtuple('SubsSearchResult', ['subtitles', 'episode_url'])
EpisodeItem = namedtuple('EpisodeItem', ['title', 'link'])
SubsItem = namedtuple('SubsItem', ['language', 'version', 'link', 'hi', 'unfinished'])
LanguageData = namedtuple('LanguageData', ['kodi_lang', 'add7_lang'])

serie_re = re.compile(r'^serie')
version_re = re.compile(r'Version (.*?),')
original_download_re = re.compile(r'^/original')
updated_download_re = re.compile(r'^/updated')
jointranslation_re = re.compile('^/jointranslation')
spanish_re = re.compile(r'Spanish \(.*?\)')

episode_patterns = (
    re.compile(r'^(.*?)[ \.](?:\d*?[ \.])?s(\d+)[ \.]?e(\d+)\.', re.I | re.U),
    re.compile(r'^(.*?)[ \.](?:\d*?[ \.])?(\d+)x(\d+)\.', re.I | re.U),
    re.compile(r'^(.*?)[ \.](?:\d*?[ \.])?(\d{1,2}?)[ \.]?(\d{2})\.', re.I | re.U),
)
# Convert show names from TheTVDB format to Addic7ed.com format
# Keys must be all lowercase
NAME_CONVERSIONS = {
    'castle (2009)': 'castle',
    'law & order: special victims unit': 'Law and order SVU',
    'bodyguard (2018)': 'bodyguard',
}


def search_episode(query, languages=None):
    """
    Search episode function. Accepts a TV show name, a season #, an episode #
    and language. Note that season and episode #s must be strings, not integers!
    For better search results relevance, season and episode #s
    should be 2-digit, e.g. 04. languages param must be a list of tuples
    ('Kodi language name', 'addic7ed language name')
    If search returns only 1 match, addic7ed.com redirects to the found episode
    page. In this case the function returns the list of available subs
    and an episode page URL.

    :param query: subs search query
    :param languages: the list of languages to search
    :return: search results as the list of potential episodes for multiple matches
        or the list of subtitles and episode page URL for a single match
    :raises: ConnectionError if addic7ed.com cannot be opened
    :raises: SubsSearchError if search returns no results
    """
    if languages is None:
        languages = [LanguageData('English', 'English')]
    webpage = session.load_page('/search.php',
                                params={'search': query, 'Submit': 'Search'})
    soup = BeautifulSoup(webpage, 'html5lib')
    table = soup.find('table',
                      {'class': 'tabel', 'align': 'center', 'width': '80%',
                       'border': '0'}
                      )
    if table is not None:
        results = list(parse_search_results(table))
        if results:
            return results
    else:
        sub_cells = soup.find_all(
            'table',
            {'width': '100%', 'border': '0',
             'align': 'center', 'class': 'tabel95'}
        )
        if sub_cells:
            return SubsSearchResult(
                parse_episode(sub_cells, languages), session.last_url
            )
    raise SubsSearchError


def parse_search_results(table):
    a_tags = table.find_all('a', href=serie_re)
    for tag in a_tags:
        yield EpisodeItem(tag.text, tag['href'])


def get_episode(link, languages=None):
    if languages is None:
        languages = [LanguageData('English', 'English')]
    webpage = session.load_page('/' + link)
    soup = BeautifulSoup(webpage, 'html5lib')
    sub_cells = soup.find_all(
        'table',
        {'width': '100%', 'border': '0', 'align': 'center', 'class': 'tabel95'}
    )
    if not sub_cells:
        raise SubsSearchError
    return SubsSearchResult(
        parse_episode(sub_cells, languages), session.last_url
    )


def parse_episode(sub_cells, languages):
    """
    Parse episode page. Accepts an episode page and a language.
    languages param must be a list of tuples
    ('Kodi language name', 'addic7ed language name')
    Returns the generator of available subs where each item is a named tuple
    with the following fields:

    - ``language``: subtitles language (Kodi)
    - ``version``: subtitles version (description on addic7ed.com)
    - ``link``: subtitles link
    - ``hi``: ``True`` for subs for hearing impaired, else ``False``

    :param sub_cell: BS nodes with episode subtitles
    :param languages: the list of languages to search
    :return: generator function that yields :class:`SubsItem` items.
    """
    for sub_cell in sub_cells:
        version = version_re.search(
                            sub_cell.find('td',
                                          {'colspan': '3',
                                           'align': 'center',
                                           'class': 'NewsTitle'}).text
                            ).group(1)
        works_with = sub_cell.find(
            'td', {'class': 'newsDate', 'colspan': '3'}
        ).get_text(strip=True)
        if works_with:
            version += ', ' + works_with
        lang_cells = sub_cell.find_all('td', {'class': 'language'})
        for lang_cell in lang_cells:
            for language in languages:
                if language.add7_lang in lang_cell.text:
                    download_cell = lang_cell.find_next('td', {'colspan': '3'})
                    download_button = download_cell.find(
                        'a',
                        class_='buttonDownload',
                        href=updated_download_re
                    )
                    if download_button is None:
                        download_button = download_cell.find(
                            'a',
                            class_='buttonDownload',
                            href=original_download_re
                        )
                    download_row = download_button.parent.parent
                    info_row = download_row.find_next('tr')
                    hi = info_row.find('img', title='Hearing Impaired') is not None
                    unfinished = info_row.find('a', href=jointranslation_re) is not None
                    yield SubsItem(
                        language=language.kodi_lang,
                        version=version,
                        link=download_button['href'],
                        hi=hi,
                        unfinished=unfinished
                    )
                    break


def parse_filename(filename):
    """
    Filename parser for extracting show name, season # and episode # from
    a filename.

    :param filename: episode filename
    :return: parsed showname, season and episode
    :raises ParseError: if the filename does not match any episode patterns
    """
    filename = filename.replace(' ', '.')
    for regexp in episode_patterns:
        episode_data = regexp.search(filename)
        if episode_data is not None:
            showname = episode_data.group(1).replace('.', ' ')
            season = episode_data.group(2).zfill(2)
            episode = episode_data.group(3).zfill(2)
            return showname, season, episode
    raise ParseError


def normalize_showname(showname):
    """
    Normalize showname if there are differences
    between TheTVDB and Addic7ed

    :param showname: TV show name
    :return: normalized show name
    """
    showname = showname.strip().lower()
    showname = NAME_CONVERSIONS.get(showname, showname)
    return showname.replace(':', '')


def get_languages(languages_raw):
    """
    Create the list of pairs of language names.
    The 1st item in a pair is used by Kodi.
    The 2nd item in a pair is used by
    the addic7ed web site parser.

    :param languages_raw: the list of subtitle languages from Kodi
    :return: the list of language pairs
    """
    languages = []
    for language in languages_raw:
        kodi_lang = language
        if 'English' in kodi_lang:
            add7_lang = 'English'
        elif kodi_lang == 'Portuguese (Brazil)':
            add7_lang = 'Portuguese (Brazilian)'
        elif spanish_re.search(kodi_lang) is not None:
            add7_lang = 'Spanish (Latin America)'
        else:
            add7_lang = language
        languages.append(LanguageData(kodi_lang, add7_lang))
    return languages
