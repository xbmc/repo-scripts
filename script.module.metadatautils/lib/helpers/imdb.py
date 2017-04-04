#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.module.metadatautils
    imdb.py
    Get metadata from imdb
'''

from utils import requests, try_parse_int
import BeautifulSoup
from simplecache import use_cache


class Imdb(object):
    '''Info from IMDB (currently only top250)'''

    def __init__(self, simplecache=None):
        '''Initialize - optionaly provide simplecache object'''
        if not simplecache:
            from simplecache import SimpleCache
            self.cache = SimpleCache()
        else:
            self.cache = simplecache

    def get_top250_rating(self, imdb_id):
        '''get the top250 rating for the given imdbid'''
        return {"IMDB.Top250": self.get_top250_db().get(imdb_id, 0)}

    @use_cache(7)
    def get_top250_db(self):
        '''
            get the top250 listing for both movies and tvshows as dict with imdbid as key
            uses 7 day cache to prevent overloading the server
        '''
        results = {}
        for listing in [("top", "chttp_tt_"), ("toptv", "chttvtp_tt_")]:
            html = requests.get(
                "http://www.imdb.com/chart/%s" %
                listing[0], headers={
                    'User-agent': 'Mozilla/5.0'}, timeout=20)
            soup = BeautifulSoup.BeautifulSoup(html.text)
            for table in soup.findAll('table'):
                if table.get("class") == "chart full-width":
                    for td_def in table.findAll('td'):
                        if td_def.get("class") == "titleColumn":
                            a_link = td_def.find("a")
                            if a_link:
                                url = a_link["href"]
                                imdb_id = url.split("/")[2]
                                imdb_rank = url.split(listing[1])[1]
                                results[imdb_id] = try_parse_int(imdb_rank)
        return results
