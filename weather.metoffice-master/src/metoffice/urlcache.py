#A basic way of caching files associated with URLs

from datetime import datetime
import os
import urllib2
import tempfile
import json
import socket

import utilities
import shutil

class URLCache(object):
    TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

    def __init__(self, folder):
        self._folder = os.path.join(folder, 'cache')
        self._file = os.path.join(folder, 'cache.json')

    def __enter__(self):
        if not os.path.exists(self._folder):
            os.makedirs(self._folder)
        try:
            fyle = open(self._file, 'r')
        except IOError:
            #create the file and try again.
            open(self._file, 'a').close()
            fyle = open(self._file, 'r')
        try:
            self._cache = json.load(fyle)
        except ValueError:
            self._cache = dict()
        fyle.close()
        return self

    def __exit__(self, typ, value, traceback):
        self.flush()
        with open(self._file, 'w+') as fyle:
            json.dump(self._cache, fyle, indent=2)

    def remove(self, url):
        if url in self._cache:
            entry = self._cache[url]
            if os.path.isfile(entry['resource']):
                os.remove(entry['resource'])
            del self._cache[url]

    def flush(self):
        flushlist = list()
        for url, entry in self._cache.iteritems():
            if not os.path.isfile(entry['resource']) or utilities.strptime(entry['expiry'], self.TIME_FORMAT) < datetime.utcnow():
                    flushlist.append(url)
        for url in flushlist:
            self.remove(url)

    def erase(self):
        os.remove(self._file)
        shutil.rmtree(self._folder)

    def get(self, url, expiry_callback, resource_callback=None):
        """
        Checks to see if an item is in cache
        """
        try:
            entry = self._cache[url]
            if not os.path.isfile(entry['resource']) or utilities.strptime(entry['expiry'], self.TIME_FORMAT) < datetime.utcnow():
                raise InvalidCacheError
            else:
                return entry['resource']
        except (KeyError, InvalidCacheError):
            #(src, headers) = urllib.urlretrieve(url)
            try:
                response = urllib2.urlopen(url)
            except (socket.timeout, urllib2.URLError) as e:
                e.args = (str(e), url)
                raise
            page = response.read()
            response.close()
            tmp = tempfile.NamedTemporaryFile(dir=self._folder, delete=False)
            tmp.write(page)
            tmp.close()
            expiry = expiry_callback(tmp.name)
            if resource_callback:
                resource_callback(tmp.name)
            self._cache[url] = {'resource': tmp.name, 'expiry': expiry.strftime(self.TIME_FORMAT)}
            return tmp.name

class InvalidCacheError(Exception):
    pass