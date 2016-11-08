import xbmc
from os.path import basename
from collections import deque
from random import choice
from time import time

import quickjson
from pykodi import log, datetime_now

WATCHMODE_UNWATCHED = 'unwatched'
WATCHMODE_WATCHED = 'watched'

def get_generator(content, info, singleresult):
    if content == 'tvshows':
        return RandomFilterableJSONGenerator(lambda filters, limit:
            quickjson.get_random_episodes(info.get('tvshowid'), info.get('season'), filters, limit),
            info.get('filters'), singleresult)
    elif content == 'movies':
        return RandomFilterableJSONGenerator(quickjson.get_random_movies, info.get('filters'), singleresult)
    elif content == 'musicvideos':
        return RandomFilterableJSONGenerator(quickjson.get_random_musicvideos, info.get('filters'), singleresult)
    elif content == 'other':
        return RandomJSONDirectoryGenerator(info['path'], info['watchmode'], singleresult)
    else:
        log("I don't know what to do with this:", xbmc.LOGWARNING)
        log({'content': content, 'info': info}, xbmc.LOGWARNING)

class RandomFilterableJSONGenerator(object):
    def __init__(self, source_function, filters=None, singleresult=False):
        """
        Args:
            source_function: takes two parameters, a list of `filters` and `limit` count
                returns an iterable
            filters: a list of additional filters to be passed to the source_function
        """
        self.source_function = source_function

        self.filters = [{'field': 'lastplayed', 'operator': 'lessthan', 'value': datetime_now().isoformat(' ')}]
        if filters:
            self.filters.extend(filters)
        self.singleresult = singleresult
        self.singledone = False

        self.readylist = deque()
        self.lastresults = deque(maxlen=20)

    def __iter__(self):
        return self

    def next(self):
        if self.singleresult:
            if self.singledone:
                raise StopIteration()
            else:
                self.singledone = True
        if not self.readylist:
            filters = list(self.filters)
            if len(self.lastresults):
                filters.append({'field': 'filename', 'operator': 'isnot', 'value': [ep for ep in self.lastresults]})
            self.readylist.extend(self.source_function(filters, 1 if self.singleresult else 20))
            if not self.readylist:
                raise StopIteration()
        result = self.readylist.popleft()
        self.lastresults.append(basename(result['file']))
        return result

class RandomJSONDirectoryGenerator(object):
    FIRST_CHUNK_SIZE = 20
    FIRST_TIMEOUT = 15

    def __init__(self, path, watchmode, singleresult=False):
        self.watchmode = watchmode
        self.singleresult = singleresult

        self.tick = 0
        self.firstbatch = set()
        self.unuseddirs = set((path,))
        self.unuseditems = []
        self.firstlist = True

    def __iter__(self):
        return self

    def next(self):
        if self.singleresult and self.tick:
            raise StopIteration()

        result = None
        if self.tick == 1:
            result = self._pop_randomitem()
        if not result:
            result = self._get_item_from_nextpath()
        if not result: # still
            raise StopIteration()

        self.tick = 1 if self.tick != 1 else 2
        return result

    def _pop_randomdir(self, secondaryset=None):
        useset = self.unuseddirs or secondaryset
        result = None
        if useset:
            result = choice(tuple(useset))
            useset.remove(result)
        return result

    def _pop_randomitem(self, secondarylist=None):
        uselist = self.unuseditems or secondarylist
        result = None
        if uselist:
            result = choice(uselist)
            uselist.remove(result)
        return result

    def _get_item_from_nextpath(self):
        dirs, files = self._get_next_files()
        self.unuseddirs |= dirs
        if not files:
            return self._pop_randomitem()

        result = choice(tuple(files))
        files.remove(result)
        self.unuseditems.extend(files)
        return result

    def _get_next_files(self):
        path_to_use = self._pop_randomdir()
        result_files = ()
        result_dirs = set()
        if not path_to_use:
            return result_dirs, result_files
        if not self.tick:
            timeout = time() + self.FIRST_TIMEOUT
        while not result_files and path_to_use:
            log("Listing '{0}'".format(path_to_use), xbmc.LOGINFO)
            newdirs, result_files = self._get_random_from_path(path_to_use)
            result_dirs |= newdirs
            if not self.tick and time() > timeout:
                log("Timeout reached", xbmc.LOGINFO)
                break
            if not result_files:
                path_to_use = self._pop_randomdir(result_dirs)
        return result_dirs, result_files

    def _get_random_from_path(self, fullpath):
        files = quickjson.get_directory(fullpath, self.FIRST_CHUNK_SIZE if self.firstlist else None)
        result_dirs = set()
        result_files = []
        check_mimetype = fullpath.endswith(('.m3u', '.pls', '.cue'))
        for file_ in files:
            if file_['file'] in self.firstbatch:
                self.firstbatch.remove(file_['file'])
                continue
            if file_['filetype'] == 'directory':
                result_dirs.add(file_['file'])
            else:
                if check_mimetype and not file_['mimetype'].startswith('video') or \
                        self.watchmode == WATCHMODE_UNWATCHED and file_['playcount'] > 0 or \
                        self.watchmode == WATCHMODE_WATCHED and file_['playcount'] == 0:
                    continue
                result_files.append(file_)
                if self.singleresult:
                    break
        if self.firstlist and len(files) == self.FIRST_CHUNK_SIZE:
            self.firstbatch = set(file_['file'] for file_ in files)
            self.unuseddirs.add(fullpath)
        self.firstlist = False
        return result_dirs, result_files
