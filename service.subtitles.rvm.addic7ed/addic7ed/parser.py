# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:        addic7ed
# Purpose:     Parsing and downloading subs from addic7ed.com
# Author:      Roman Miroshnychenko
# Created on:  05.03.2013
# Copyright:   (c) Roman Miroshnychenko, 2013
# Licence:     GPL v.3 http://www.gnu.org/licenses/gpl.html
#-------------------------------------------------------------------------------

from __future__ import absolute_import, unicode_literals
import re
from contextlib import closing
from collections import namedtuple
from bs4 import BeautifulSoup
from kodi_six.xbmcvfs import File
from .exceptions import SubsSearchError, DailyLimitError
from .utils import LanguageData
from .webclient import Session

__all__ = ['search_episode', 'get_episode', 'download_subs']

session = Session()
SubsSearchResult = namedtuple('SubsSearchResult', ['subtitles', 'episode_url'])
EpisodeItem = namedtuple('EpisodeItem', ['title', 'link'])
SubsItem = namedtuple('SubsItem', ['language', 'version', 'link', 'hi', 'unfinished'])
serie_re = re.compile(r'^serie')
version_re = re.compile(r'Version (.*?),')
original_download_re = re.compile(r'^/original')
updated_download_re = re.compile(r'^/updated')
jointranslation_re = re.compile('^/jointranslation')


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
        if not results:
            raise SubsSearchError
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
        else:
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
    if sub_cells:
        return SubsSearchResult(
            parse_episode(sub_cells, languages), session.last_url
        )
    else:
        raise SubsSearchError


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
            version += u', ' + works_with
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


def download_subs(link, referer, filename='subtitles.srt'):
    """
    Download subtitles from addic7ed.com

    :param link: relative lint to .srt file
    :param referer: episode page for referer header
    :param filename: file name for subtitles
    :raises ConnectionError: if addic7ed.com cannot be opened
    :raises DailyLimitError: if a user exceeded their daily download quota
        (10 subtitles).
    """
    subtitles = session.download_subs(link, referer=referer)
    if subtitles[:9].lower() != b'<!doctype':
        with closing(File(filename, 'w')) as fo:
            fo.write(bytearray(subtitles))
    else:
        raise DailyLimitError
