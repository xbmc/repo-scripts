# -*- coding: utf-8 -*-
#
#  MythBox for XBMC - http://mythbox.googlecode.com
#  Copyright (C) 2012 analogue@yahoo.com
# 
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
import datetime
import logging
import os
import random
import imdb         #@UnusedImport
import imdb.helpers #@UnusedImport
import pickle
import shutil
import simplejson as json
import threading
import tmdb
import tvdb_api
import tvrage.api
import urllib2
import urllib
import Queue

from hashlib import md5
from decorator import decorator
from mythbox.util import sync_instance, synchronized, safe_str, run_async, max_threads, timed, requireDir, formatSize
from mythbox.bus import Event

log = logging.getLogger('mythbox.fanart')


@decorator
def chain(func, *args, **kwargs):
    provider = args[0]
    result = func(*args, **kwargs)
    if not result and provider.nextProvider:
        nfunc = getattr(provider.nextProvider, func.__name__)
        return nfunc(*args[1:], **kwargs)
    elif isinstance(result, tuple) and provider.nextProvider:
        # don't chain result tuple with non-none values
        for e in result:
            if e is not None:
                return result
        nfunc = getattr(provider.nextProvider, func.__name__)
        return nfunc(*args[1:], **kwargs)
    else:
        return result


class BaseFanartProvider(object):

    def __init__(self, nextProvider=None):
        self.nextProvider = nextProvider

    def trace(self, msg):
        if hasattr(self, 'tag'):
            t = self.tag
        else:
            t = '???'
        log.debug('[%s %s] %s' % (self.__class__.__name__, t, msg))

    def getPosters(self, program):
        raise Exception, 'Abstract method'
    
    def getBanners(self, program):
        raise Exception, 'Abstract method'

    def getBackgrounds(self, program):
        raise Exception, 'Abstract method'

    def getSeasonAndEpisode(self, program):
        if self.nextProvider:
            return self.nextProvider.getSeasonAndEpisode(program)
        else:
            return None,None
    
    def clear(self, program=None):
        if self.nextProvider:
            self.nextProvider.clear(program)
    
    def close(self):
        if self.nextProvider:
            self.nextProvider.close()


class NoOpFanartProvider(BaseFanartProvider):

    def __init__(self):
        BaseFanartProvider.__init__(self, nextProvider=None)

    def hasPosters(self, program):
        return False
    
    def hasBanners(self, program):
        return False
    
    def hasBackgrounds(self, program):
        return False
    
    def getPosters(self, program):
        return []

    def getBanners(self, program):
        return []

    def getBackgrounds(self, program):
        return []
    
    def getSeasonAndEpisode(self, program):
        return None, None


class PersistentFanartProvider(BaseFanartProvider):
    """Abstract base class which persists a dict (pcache) to disk across sessions"""
    
    def __init__(self, nextProvider, pfilename):
        BaseFanartProvider.__init__(self, nextProvider)
        self.pfilename = pfilename
        self.pcache = self.loadCache()

    def loadCache(self):
        cache = {}
        try:
            if os.path.exists(self.pfilename):
                with open(self.pfilename, 'rb') as f:
                    cache = pickle.load(f)
        except EOFError:
            log.error('EOF error loading persistent cache from %s. Starting fresh' % self.pfilename)
        except:
            log.exception('Loading from %s' % self.pfilename)
        return cache

    def saveCache(self):
        try:
            with open(self.pfilename, 'wb') as f:
                pickle.dump(self.pcache, f)
        except:
            log.exception('Error saving persistent cache to %s' % self.pfilename)

    def clear(self, program=None):
        super(PersistentFanartProvider, self).clear(program)
        if program is None:
            self.pcache.clear()
            self.saveCache()
            
    def close(self):
        super(PersistentFanartProvider, self).close()
        self.saveCache()
        if log.isEnabledFor(logging.DEBUG):
            try: 
                self.trace('Cache size %s %s' % (os.path.split(self.pfilename)[1], formatSize(os.path.getsize(self.pfilename)/1000))) 
            except: 
                pass
        

class OneStrikeAndYoureOutFanartProvider(PersistentFanartProvider):
    """
    If a fanart provider can't serve up fanart for a program the first time, 
    chances are it won't succeed on subsequent requests. For instances where
    subsequent requests can be 'expensive', this decorator will short-circuit
    the lookup process after <insert criteria here>.
    """
    
    def __init__(self, platform, delegate, nextProvider=None, filename=None, tag=None):
        if not delegate:
            raise Exception('delegate cannot be None')
        oneStrikeDir = requireDir(os.path.join(platform.getCacheDir(), 'onestrike'))
        if filename is None:
            filename = '%s' % delegate.__class__.__name__
        PersistentFanartProvider.__init__(self, nextProvider, os.path.join(oneStrikeDir, '%s.pickle' % filename))
        self.delegate = delegate
        self.struckOut = self.pcache
        self.tag = tag
        
    def createKey(self, method, program):
        if method != 'getSeasonAndEpisode':
            return '%s-%s' % (method, md5(safe_str(program.title())).hexdigest())
        else:
            return ('getSeasonAndEpisode', program.title(), program.subtitle(), program.originalAirDate())
        
    @synchronized
    def hasStruckOut(self, key):
        if not key in self.struckOut:
            return False
        
        bucket = self.struckOut[key]
        if 'timestamp' in bucket:
            # remove program from penalty box if the last lookup failure was over 30 days ago
            ts = bucket['timestamp']
            now = datetime.datetime.now()
            diff = now - ts
            if diff < datetime.timedelta(days=14):
                return True
            
            self.trace('Strikeout expired for %s:%s' % (key, safe_str(bucket['title'])))
            del self.struckOut[key]
            return False
        else:
            # Support older versions before timestamp was introduced
            bucket['timestamp'] = datetime.datetime.now()
            return True
    
    @synchronized
    def strikeOut(self, key, program):
        if key in self.struckOut:
            bucket = self.struckOut[key]
        else:
            bucket = {'title':program.title()}
            self.struckOut[key] = bucket
        bucket['timestamp'] = datetime.datetime.now()

    def hasPosters(self, program):
        return self._hasStrikeOutable('getPosters', 'hasPosters', program)
    
    def hasBanners(self, program):
        return self._hasStrikeOutable('getBanners', 'hasBanners', program)

    def hasBackgrounds(self, program):
        return self._hasStrikeOutable('getBackgrounds', 'hasBackgrounds', program)

    def _hasStrikeOutable(self, getterMethodName, hasMethodName, program):
        key = self.createKey(getterMethodName, program)
        if self.hasStruckOut(key):
            if self.nextProvider:
                hasMethod = getattr(self.nextProvider, hasMethodName)
                return hasMethod(program)
            else:
                return False
        else:
            hasMethod = getattr(self.delegate, hasMethodName)
            return hasMethod(program)

    @chain
    def getPosters(self, program):
        return self._getStrikeOutable(program, 'getPosters', self.delegate.getPosters)

    @chain
    def getBanners(self, program):
        return self._getStrikeOutable(program, 'getBanners', self.delegate.getBanners)

    @chain
    def getBackgrounds(self, program):
        return self._getStrikeOutable(program, 'getBackgrounds', self.delegate.getBackgrounds)

    def _getStrikeOutable(self, program, methodName, delegateFunc):
        results = []
        key = self.createKey(methodName, program) 
        if not self.hasStruckOut(key):
            results = delegateFunc(program)
            if not results:
                self.strikeOut(key, program)
        return results

    def getSeasonAndEpisode(self, program):
        season, episode = None, None
        key = self.createKey('getSeasonAndEpisode', program)
        if not self.hasStruckOut(key):
            season, episode = self.delegate.getSeasonAndEpisode(program)
            if season is None or episode is None:
                self.strikeOut(key, program)
                
        if self.hasStruckOut(key):
            return super(OneStrikeAndYoureOutFanartProvider, self).getSeasonAndEpisode(program) 
        else:
            return season, episode
        
    def clear(self, program=None):
        if program:
            for key in [self.createKey(m, program) for m in ['getPosters', 'getBanners', 'getBackgrounds', 'getSeasonAndEpisode']]:
                if self.hasStruckOut(key):
                    del self.struckOut[key]
        else:
            self.struckOut.clear()
        
        self.delegate.clear(program)
        super(OneStrikeAndYoureOutFanartProvider, self).clear(program)

    def close(self):
        super(OneStrikeAndYoureOutFanartProvider, self).close()
        self.delegate.close()


class SpamSkippingFanartProvider(BaseFanartProvider):
    """
    Lets not waste cycles looking up fanart for programs which probably don't
    have fanart.
    """
    
    SPAM = ['Paid Programming', 'No Data', 'SIGN OFF'] 
    
    def __init__(self, nextProvider=None):
        BaseFanartProvider.__init__(self, nextProvider)
        self.tag = 'spam'
    
    def getPosters(self, program):
        if program.title() in self.SPAM:
            return []
        if self.nextProvider:
            return self.nextProvider.getPosters(program)

    def getBanners(self, program):
        if program.title() in self.SPAM:
            return []
        if self.nextProvider:
            return self.nextProvider.getBanners(program)
                        
    def getBackgrounds(self, program):
        if program.title() in self.SPAM:
            return []
        if self.nextProvider:
            return self.nextProvider.getBackgrounds(program)
                                
    def hasPosters(self, program):
        if program.title() in self.SPAM:
            return True
        return self.nextProvider.hasPosters(program)

    def hasBanners(self, program):
        if program.title() in self.SPAM:
            return True
        return self.nextProvider.hasBanners(program)

    def hasBackgrounds(self, program):
        if program.title() in self.SPAM:
            return True
        return self.nextProvider.hasBackgrounds(program)
        
    def getSeasonAndEpisode(self, program):
        if program.title() in self.SPAM:
            return None,None 
        return self.nextProvider.getSeasonAndEpisode(program)
       
        
class SuperFastFanartProvider(PersistentFanartProvider):
    
    def __init__(self, platform, nextProvider=None, filename=None, tag=None):
        cacheDir = requireDir(os.path.join(platform.getCacheDir(), 'superfast'))
        if filename is None:
            filename = 'superfast'
        PersistentFanartProvider.__init__(self, nextProvider, os.path.join(cacheDir, '%s.pickle' % filename))
        self.imagePathsByKey = self.pcache
        self.tag = tag

    def getPosters(self, program):
        posters = []
        key = self.createKey('getPosters', program)
        if key in self.imagePathsByKey:
            posters = self.imagePathsByKey[key]
        
        if not posters and self.nextProvider:
            posters = self.nextProvider.getPosters(program)
            if posters:  # cache returned poster 
                self.imagePathsByKey[key] = posters
        return posters

    def getBanners(self, program):
        # Different from posters in that it is ok for the
        # list to be empty
        banners = []
        key = self.createKey('getBanners', program)
        if key in self.imagePathsByKey:
            banners = self.imagePathsByKey[key]
        elif self.nextProvider:
            banners = self.nextProvider.getBanners(program)
            if banners:
                self.imagePathsByKey[key] = banners
        return banners

    def getBackgrounds(self, program):
        # Different from posters in that it is ok for the
        # list to be empty
        backgrounds = []
        key = self.createKey('getBackgrounds', program)
        if key in self.imagePathsByKey:
            backgrounds = self.imagePathsByKey[key]
        elif self.nextProvider:
            backgrounds = self.nextProvider.getBackgrounds(program)
            if backgrounds:
                self.imagePathsByKey[key] = backgrounds
        return backgrounds

    def hasPosters(self, program):
        return self.createKey('getPosters', program) in self.imagePathsByKey
        
    def hasBanners(self, program):
        return self.createKey('getBanners', program) in self.imagePathsByKey
    
    def hasBackgrounds(self, program):
        return self.createKey('getBackgrounds', program) in self.imagePathsByKey
        
    def createKey(self, methodName, program):
        key = '%s-%s' % (methodName, safe_str(program.title()))
        return key

    def createEpisodeKey(self, methodName, program):
        return '-'.join(str(k) for k in [
            methodName, 
            safe_str(program.title()), 
            safe_str(program.subtitle()), 
            program.originalAirDate()])

    def getSeasonAndEpisode(self, program):
        season, episode = None, None
        key = self.createEpisodeKey('getSeasonAndEpisode', program)
        
        # looks like we're caching more than just paths now
        if key in self.imagePathsByKey:
            season, episode = self.imagePathsByKey[key]
        elif self.nextProvider:
            season, episode = self.nextProvider.getSeasonAndEpisode(program)
            if season and episode:
                self.imagePathsByKey[key] = (season, episode)
        return season, episode
        
    def clear(self, program=None):
        super(SuperFastFanartProvider, self).clear(program)
  
        if program:
            for key in [self.createKey(m, program) for m in ['getPosters', 'getBanners', 'getBackgrounds']]:
                if key in self.imagePathsByKey:
                    del self.imagePathsByKey[key]
            
            episodeKey = self.createEpisodeKey('getSeasonAndEpisode', program)
            if episodeKey and episodeKey in self.imagePathsByKey:
                del self.imagePathsByKey[episodeKey]
        else:
            self.imagePathsByKey.clear()
        
            
class HttpCachingFanartProvider(BaseFanartProvider):
    """Caches images retrieved via http on the local filesystem"""
    
    def __init__(self, httpCache, nextProvider=None, tag=None):
        BaseFanartProvider.__init__(self, nextProvider)
        self.tag = tag
        self.parent = None
        self.httpCache = httpCache
        self.workQueue = Queue.Queue()   
        self.closeRequested = False
        self.startLock = threading.Event()
        self.startLock.clear()
        self.workThread = self.workerBee()
        self.startLock.wait()
        
    @run_async
    def workerBee(self):
        self.startLock.set()
        while not self.closeRequested:
            try:
                if not self.workQueue.empty():
                    self.trace('httpcache work queue size: %d' % self.workQueue.qsize())
                workUnit = self.workQueue.get(block=True, timeout=1)
                results = workUnit['results']
                httpUrl = workUnit['httpUrl']
                filePath = self.tryToCache(httpUrl)
                if filePath:
                    self.trace("Adding image %s as %s[%d]" % (filePath.split(os.sep)[-1], safe_str(workUnit['program'].title()), len(results)))
                    results.append(filePath)
            except Queue.Empty:
                pass
        
    def getPosters(self, program):
        # If the chained provider returns a http:// style url, 
        # cache the contents and return the locally cached file path
        posters = []
        if self.nextProvider:
            httpPosters = self.nextProvider.getPosters(program)
            posters = self.cacheImages(httpPosters, program)
        return posters

    def getBanners(self, program):
        banners = []
        if self.nextProvider:
            httpBanners = self.nextProvider.getBanners(program)
            banners = self.cacheImages(httpBanners, program)
        return banners
    
    def getBackgrounds(self, program):
        backgrounds = []
        if self.nextProvider:
            httpBackgrounds = self.nextProvider.getBackgrounds(program)
            backgrounds = self.cacheImages(httpBackgrounds, program)
        return backgrounds
        
    def cacheImages(self, httpUrls, program):
        '''
        Immediately retrieve the first URL and add the remaining to the 
        work queue so we can return *something* very quickly.
        '''
        filepaths = []
        remainingUrls = []
        
        for i in xrange(len(httpUrls)):
            first = self.tryToCache(httpUrls[i])
            if first:
                filepaths.append(first)
                remainingUrls = httpUrls[i:]
                break                  
        
        for nextUrl in remainingUrls:
            httpUrls.remove(nextUrl)
            self.workQueue.put({'results' : filepaths, 'httpUrl' : nextUrl, 'program' : program })
        
        return filepaths
    
    def tryToCache(self, imageUrl):
        if imageUrl and imageUrl[:4] == 'http':
            try:
                filepath = self.httpCache.get(imageUrl)
            except Exception, ioe:
                log.exception(ioe)
                filepath = None
        return filepath
    
    def clear(self, program=None):
        super(HttpCachingFanartProvider, self).clear(program)
        if program is None:
            self.httpCache.clear()
        else:
            pass # TODO: remove program specific images from HTTP cache
        
    def close(self):
        self.closeRequested = True
        super(HttpCachingFanartProvider, self).close()
        self.workThread.join()
        
    def getSeasonAndEpisode(self, program):
        # pass through
        return self.nextProvider.getSeasonAndEpisode(program)


class ImdbFanartProvider(NoOpFanartProvider):

    def __init__(self):
        NoOpFanartProvider.__init__(self)
        self.imdb = imdb.IMDb(accessSystem=None) # loggingConfig='~/git/mythbox/mythbox_log.ini')

    @max_threads(1)
    @timed
    def getPosters(self, program):
        if not program.isMovie():
            return []
        
        posters = []
        try:
            movies = self.imdb.search_movie(title=u'' + program.title(), results=1)
            for movie in movies:
                m = self.imdb.get_movie(movie.getID())
                #for key,value in m.items():
                #    log.warn('movie[%d] id[%s] key[%s] -> %s' % (1, m.getID(), key, safe_str(value)))
                posters.append(m['full-size cover url'])  
        except imdb.IMDbError, e:
            log.error('IMDB: Error looking up movie: %s %s' % (safe_str(program.title()), safe_str(str(e))))
        except Exception, e:
            log.error('IMDB: Error looking up %s: %s' % (safe_str(program.title()), safe_str(str(e))))
        return posters
    

class TvdbFanartProvider(NoOpFanartProvider):
    """tvdb site rejects queries if > 2 per originating IP.
    Furthermore, the API is not thread safe hence the use
    of self.lock
    """

    overrides = {
        u'Conan'                 : u'Conan (2010)',
        u'Dobie Gillis'          : u'The Many Loves of Dobie Gillis', 
        u'Skins'                 : u'Skins (US)',
        u'The Challenge: Rivals' : u'The Challenge',
        u'The Office'            : u'The Office (US)'  # TODO: How to differentiate between the US and UK version?
    }
    
    def __init__(self, platform):
        NoOpFanartProvider.__init__(self)
        self.tvdbCacheDir = requireDir(os.path.join(platform.getCacheDir(), 'tvdb'))
        self.tvdb = tvdb_api.Tvdb(interactive=False, 
            select_first=True, 
            debug=False, 
            cache=self.tvdbCacheDir, 
            banners=True, 
            actors=False, 
            custom_ui=None, 
            language=None, 
            search_all_languages=False, 
            apikey='E2032A158BE34568')

        self.lock = threading.RLock()
        
    @timed    
    def getPosters(self, program):
        
        if program.isMovie(): 
            return []
        
        t = self.overrides.get(program.title(), program.title())
        posters = []
        try:
            # Example: tvdb['scrubs']['_banners']['poster']['680x1000']['35308']['_bannerpath']
            #posterUrl = self.tvdb[program.title()]['_banners']['poster'].itervalues().next().itervalues().next()['_bannerpath']
            
            with self.lock:
                postersByDimension = self._queryTvDb(t, qtype='poster') 
                for dimension in postersByDimension.keys():
                    #log.debug('key=%s' % dimension)
                    for id in postersByDimension[dimension].keys():
                        #log.debug('idkey = %s' % id)
                        bannerPath = postersByDimension[dimension][id]['_bannerpath']
                        #log.debug('bannerPath = %s' % bannerPath)
                        posters.append(bannerPath)
                log.debug('TVDB[%s] = %s' % (len(posters), safe_str(t)))
        except Exception, e:
            log.warn('TVDB: "%s" error "%s"' % (safe_str(t), safe_str(e)))
        return posters
    
    def getBanners(self, program):
        if program.isMovie(): 
            return []
        
        banners = []
        t = self.overrides.get(program.title(), program.title())
        try:
            with self.lock:
                bannersByType = self._queryTvDb(t, qtype='series')
                for subType in ['graphical', 'text', 'blank']:
                    if subType in bannersByType:
                        bannersById = bannersByType[subType]
                        for id in bannersById.keys():
                            banners.append(bannersById[id]['_bannerpath'])
        except Exception, e:
            log.warn('TVDB: No banners for %s - %s' % (safe_str(t), safe_str(e)))
        return banners

    def getBackgrounds(self, program):
        if program.isMovie():
            return []
        
        t = self.overrides.get(program.title(), program.title())
        backgrounds = []
        try:
            with self.lock:
                backgroundsByDimension = self._queryTvDb(t, qtype='fanart')
                for knownDim in ['1280x720', '1920x1080']:
                    if knownDim in backgroundsByDimension:
                        backgroundsById = backgroundsByDimension[knownDim]
                        for id in backgroundsById.keys():
                            backgrounds.append(backgroundsById[id]['_bannerpath'])
        except Exception, e:
            log.debug('TVDB: No backgrounds for %s - %s' % (safe_str(t), safe_str(e)))
        return backgrounds

    def clear(self, program=None):
        if program is None:
            with self.lock:        
                shutil.rmtree(self.tvdbCacheDir, ignore_errors=True)
                requireDir(self.tvdbCacheDir)
        else:
            log.warn('TVDB: cannot invalidate individual program')

    def _queryTvDb(self, title, qtype=None):
        with self.lock:
            if qtype: 
                return self.tvdb[title]['_banners'][qtype]
            else:
                return self.tvdb[title]

    def getSeasonAndEpisode(self, program):
        if program.isMovie(): 
            return None, None
        
        title = self.overrides.get(program.title(), program.title())
        tvdb_show = None
        
        try:
            try:
                with self.lock:
                    tvdb_show = self._queryTvDb(title)
            except tvdb_api.tvdb_shownotfound:
                log.debug('TVDB: Show not found - %s' % safe_str(title))
                return None, None
 
            episode = self._findEpisode(program, tvdb_show)
            return (episode['seasonnumber'], episode['episodenumber']) if episode else (None, None) 
            
        except tvdb_api.tvdb_error:
            log.exception(safe_str(title))
            return None, None

    def _findEpisode(self, program, tvdb_show):
        finders = [
            ('original air date', program.hasOriginalAirDate, program.originalAirDate, None, 'firstaired'),
            ('subtitle', program.subtitle, program.subtitle, None, 'episodename'),
            ('recording date', program.starttimeAsTime, lambda p: p.starttimeAsTime().strftime('%Y-%m-%d'), program, 'firstaired'),
            ('recording date - 1', program.starttimeAsTime, lambda p: (p.starttimeAsTime() - datetime.timedelta(days=1)).strftime('%Y-%m-%d'), program, 'firstaired')
        ]
    
        for searchStrategy, shouldSearch, searchFor, searchForArg, searchKey in finders:
            if shouldSearch():
                term = searchFor(searchForArg) if searchForArg else searchFor()
                with self.lock:
                    episodes = tvdb_show.search(term=term, key=searchKey)
                if episodes:
                    return episodes[0]
                else:
                    log.debug("TVDB: '%s' episode not found by '%s' as '%s'" % (safe_str(program.title()), searchStrategy, term))
        return None


class TheMovieDbFanartProvider(NoOpFanartProvider):
    
    def __init__(self):
        NoOpFanartProvider.__init__(self)        
        tmdb.config['apikey'] = '4956f64b34ac586d01d6820de8e93d58'
        self.mdb = tmdb.MovieDb()
    
    @max_threads(1)
    @timed
    def getPosters(self, program):
        posters = []
        if program.isMovie():
            try:
                results = self.mdb.search(program.title())
                if results and len(results) > 0:
                    filmId = results[0]['id']
                    film = self.mdb.getMovieInfo(filmId)
                    
                    for id in film['images']['poster']:
                        if 'mid' in film['images']['poster'][id]:
                        #for size in film['images']['poster'][id]:
                            size = 'mid'
                            url = film['images']['poster'][id][size]
                            #log.debug('TMDB: %s size = %s  url = %s' % (id, size, url))
                            posters.append(url)

                    #for i, result in enumerate(results):    
                        # Poster keys: 
                        #    'cover'      -- little small - 185px by 247px 
                        #    'mid'        -- just right   - 500px by 760px
                        #    'original'   -- can be huge  - 2690px by 3587px
                        #    'thumb'      -- tiny         - 92px by 136px
                        
                        #for key, value in result['poster'].items():
                        #    log.debug('TMDB: %d key = %s  value = %s' % (i, key, value))

                        #if  'mid' in result['poster']:
                        #    posters.append(result['poster']['mid'])
                else:
                    log.debug('TMDB: Found nothing for: %s' % safe_str(program.title()))
            except Exception, e:
                log.exception('TMDB: Fanart search error: %s %s' % (safe_str(program.title()), safe_str(e)))
        return posters
    
    
class GoogleImageSearchProvider(NoOpFanartProvider):
    '''http://code.google.com/apis/imagesearch/v1/jsondevguide.html'''
    
    API_KEY = 'ABQIAAAAtSwHhE1Qf9mbLYNOFLH-DhT20V1GhzX5gQnCPfmaLAI2Lns2JRTbUFdk3MQzyqjPwjJDcQay_EVizw'
    
    def __init__(self):
        NoOpFanartProvider.__init__(self)        
    
    @max_threads(1)
    def getPosters(self, program):
        posters = []
        try:
            url_values = urllib.urlencode({'v':'1.0', 'safe':'moderate', 'rsz':'4', 'imgsz':'medium', 'key':self.API_KEY, 'q':program.title()}, doseq=True)
            searchUrl = 'http://ajax.googleapis.com/ajax/services/search/images?' + url_values
            req = urllib2.Request(searchUrl, headers={'Referer':'http://mythbox.googlecode.com'})
            resp = urllib2.urlopen(req)
            s = resp.readlines()
            obj = json.loads(s[0])
            
            #if log.isEnabledFor('debug'):
            #    log.debug(json.dumps(obj, sort_keys=True, indent=4))
            #    log.debug('url = %s' % searchUrl)
            #    for result in obj['responseData']['results']: 
            #        log.debug(result['unescapedUrl'])            
        
            posters = [result['unescapedUrl'] for result in obj['responseData']['results'] if float(result['height'])/float(result['width']) > 1.0]
            if len(posters) == 0:
                log.debug('GOOGLE: No images meet aspect ratio constaints for %s' % safe_str(program.title()))
                posters.append(obj['responseData']['results'][0]['unescapedUrl'])
        
        except Exception, e:
            log.exception('GOOGLE: Fanart search:  %s %s' % (safe_str(program.title()), safe_str(e)))
        return posters


class TvRageProvider(NoOpFanartProvider):

    def __init__(self, platform):
        NoOpFanartProvider.__init__(self)
        self.cacheDir = requireDir(os.path.join(platform.getCacheDir(), 'tvrage'))
        self.memcache = {}

    @sync_instance
    def clear(self, program=None):
        if program is None:
            self.memcache.clear()
            shutil.rmtree(self.cacheDir, ignore_errors=True)
            requireDir(self.cacheDir)         
        else:
            # purge from memory
            if program.title() in self.memcache:
                del self.memcache[program.title()]
            
            # purge from disk
            fname = os.path.join(self.cacheDir, safe_str(program.title().replace('/','_')))
            if os.path.exists(fname):
                os.remove(fname)
            
    def load(self, program):
        '''Load tvrage.api.Show from memory or disk cache'''
        if program.title() in self.memcache.keys():
            return self.memcache[program.title()]
        
        fname = os.path.join(self.cacheDir, safe_str(program.title().replace('/','_')))
        if not os.path.exists(fname):
            return None

        with open(fname, 'rb') as f:
            try:
                show = pickle.load(f)
                self.memcache[program.title()] = show
                return show
            except EOFError: 
                return None  # file corrupt
    
    def save(self, program, show):
        '''Save tvrage.api.Show to memory/disk cache'''
        with open(os.path.join(self.cacheDir, safe_str(program.title().replace('/','_'))), 'wb') as f:
            self.memcache[program.title()] = show
            pickle.dump(show, f)
        
    @sync_instance
    def getSeasonAndEpisode(self, program):
        if program.isMovie(): 
            return None, None
        
        show = self.load(program)

        if show is None:
            return self.queryTvRage(program)        
        else:
            season, episode = self.searchForEpisode(program, show)
            if season is None or episode is None:
                # not found in cached show, get fresh data if show has not been cancelled
                if show.status == 'Canceled/Ended':
                    return None, None
                else:
                    return self.queryTvRage(program)
            else:
                return season, episode
                
    def queryTvRage(self, program):
        try:
            show = self.indexEpisodes(tvrage.api.Show(program.title()))
            self.save(program, show)
            return self.searchForEpisode(program, show)
        except tvrage.api.ShowNotFound:
            log.debug('TVRage: Show not found - %s' % safe_str(program.title()))
            return None, None
        except TypeError, te:
            #  File "tvrage/api.py", line 145, in __init__
            #    for season in eplist:
            #TypeError: iteration over non-sequence
            log.exception('TVRage: TypeError %s - %s' % (safe_str(te), safe_str(program.title())))
            return None, None
        
    def indexEpisodes(self, show):
        '''Throw all episodes into a map for fast lookup and attach to show object so the index is persisted'''
        show.seasonsAndEpisodes = {}  # key = original air date, value = (season, episode)
        for sn in xrange(1, show.seasons+1):
            try:
                season = show.season(sn)
                for en, episode in season.items():
                    show.seasonsAndEpisodes[episode.airdate] = (str(sn), str(en))
            except KeyError:
                pass # For cases where an entire season is missing, keep going...
        return show
    
    def searchForEpisode(self, program, show):
        """Search for a match in this order until we get a hit
        - original air date
        - subtitle
        - original air date - 1 day
        - original air date + 1 day
        """        
        if not program.hasOriginalAirDate():
            # set unrealistic date to force lookup failure 
            oad = datetime.date(2099, 1, 1)             
        else:
            oad = program.originalAirDate()
            
        # TODO: change original air date in RecordedProgram to type datetime.date
        if type(oad) == datetime.date: 
            d = oad
        else:
            d = datetime.date(int(oad[0:4]), int(oad[5:7]), int(oad[8:10]))

        if d in show.seasonsAndEpisodes:
            return show.seasonsAndEpisodes[d]
        else:
            log.debug('TVRage: No episode found matching airdate %s in %s episodes of %s' % 
                (oad, len(show.seasonsAndEpisodes), safe_str(program.title())))
            
            season, episode = self.searchBySubtitle(program, show)
            if season and episode:
                return season, episode
            
            dayBefore = d - datetime.timedelta(days=1)
            if dayBefore in show.seasonsAndEpisodes:
                return show.seasonsAndEpisodes[dayBefore]

            dayAfter  = d + datetime.timedelta(days=1)
            if dayAfter in show.seasonsAndEpisodes:
                return show.seasonsAndEpisodes[dayAfter]
            
            return None, None
    
    def searchBySubtitle(self, program, show):
        subtitle = program.subtitle()
        if subtitle is None or len(subtitle) == 0:
            return None, None
        
        for sn in xrange(1, show.seasons+1):
            try:
                season = show.season(sn)
                for en, episode in season.items():
                    if episode.title and episode.title.lower() == subtitle.lower():
                        return str(sn), str(episode.number)
            except KeyError:
                # For cases where an entire season is missing, keep going...
                log.debug('TVRage: Season %d of %s is missing' % (sn, safe_str(program.title())))
    
        log.debug('TVRage: No episode of %s found matching subtitle %s' % (safe_str(program.title()), safe_str(subtitle)))        
        return None, None


class FanArt(object):
    '''One stop shop for fanart and program metadata not originating from mythtv'''
    
    def __init__(self, platform, httpCache, settings, bus):
        self.platform = platform
        self.httpCache = httpCache
        self.settings = settings
        self.provider = NoOpFanartProvider()
        self.configure(self.settings)
        bus.register(self)
    
    def getSeasonAndEpisode(self, program):
        '''Return pair of strings'''
        return self.provider.getSeasonAndEpisode(program)
    
    def pickPoster(self, program):
        posters = self.provider.getPosters(program)
        if posters:
            return random.choice(posters)
    
    def pickBanner(self, program):
        banners = self.provider.getBanners(program)
        if banners:
            return random.choice(banners)
        
    def pickBackground(self, program):
        backgrounds = self.provider.getBackgrounds(program)
        if backgrounds:
            return random.choice(backgrounds)
    
    def getPosters(self, program):
        return self.provider.getPosters(program)

    def getBanners(self, program):
        return self.provider.getBanners(program)
    
    def getBackgrounds(self, program):
        return self.provider.getBackgrounds(program)

    def hasBanners(self, program):
        return self.provider.hasBanners(program)
    
    def hasPosters(self, program):
        return self.provider.hasPosters(program)

    def hasBackgrounds(self, program):
        return self.provider.hasBackgrounds(program)
    
    def clear(self, program=None):
        self.provider.clear(program) 
        
    @timed    
    def shutdown(self):
        self.provider.close()

    def configure(self, settings):
        self.provider.close()
        
        p = NoOpFanartProvider()
        
        if settings.getBoolean('fanart_google'): 
            p = SuperFastFanartProvider(
                    self.platform, 
                    HttpCachingFanartProvider(
                        self.httpCache, 
                        GoogleImageSearchProvider(),
                        tag='goog'), 
                    filename='google',
                    tag='goog')
        
        if settings.getBoolean('fanart_imdb')  : 
            p = OneStrikeAndYoureOutFanartProvider(
                    platform=self.platform, 
                    delegate=SuperFastFanartProvider(
                        self.platform, 
                        HttpCachingFanartProvider(
                            self.httpCache, 
                            ImdbFanartProvider(),
                            tag='imdb'), 
                        filename='imdb',
                        tag='imdb'), 
                    nextProvider=p, 
                    filename='imdb',
                    tag='imdb')
            
        if settings.getBoolean('fanart_tmdb')  : 
            p = OneStrikeAndYoureOutFanartProvider(
                    platform=self.platform, 
                    delegate=SuperFastFanartProvider(
                        self.platform, 
                        HttpCachingFanartProvider(
                            self.httpCache, 
                            TheMovieDbFanartProvider(),
                            tag='tmdb'), 
                        filename='tmdb',
                        tag='tmdb'), 
                    nextProvider=p, 
                    filename='tmdb',
                    tag='tmdb')
            
        if settings.getBoolean('fanart_tvdb')  : 
            p = OneStrikeAndYoureOutFanartProvider(
                    platform=self.platform, 
                    delegate=SuperFastFanartProvider(
                        self.platform, 
                        HttpCachingFanartProvider(
                            self.httpCache, 
                            TvdbFanartProvider(self.platform), 
                            tag='tvdb'), 
                        filename='tvdb',
                        tag='tvdb'),  
                    nextProvider=p, 
                    filename='tvdb',
                    tag='tvdb')

        if settings.getBoolean('fanart_tvrage'): 
            p = OneStrikeAndYoureOutFanartProvider(
                    platform=self.platform, 
                    delegate=SuperFastFanartProvider(
                        self.platform, 
                        HttpCachingFanartProvider(
                            self.httpCache, 
                            TvRageProvider(self.platform),
                            tag='tvrage'), 
                        filename='tvrage',
                        tag='tvrage'), 
                    nextProvider=p, 
                    filename='tvrage',
                    tag='tvrage') 
                        
        #p = HttpCachingFanartProvider(self.httpCache, p)
        #self.sffp = p = SuperFastFanartProvider(self.platform, p)
        p = SpamSkippingFanartProvider(p)
        self.provider = p
    
    def onEvent(self, event):
        if event['id'] == Event.SETTING_CHANGED:
            if event['tag'] in ('fanart_tvdb', 'fanart_tmdb', 'fanart_imdb', 'fanart_google', 'fanart_tvrage',):
                self.configure(self.settings)
