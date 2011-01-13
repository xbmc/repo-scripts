# -*- coding: utf-8 -*-
#
#  MythBox for XBMC - http://mythbox.googlecode.com
#  Copyright (C) 2011 analogue@yahoo.com
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
import md5
import os
import random
import imdb
import imdb.helpers
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

from decorator import decorator
from mythbox.util import synchronized, safe_str, run_async, max_threads, timed, requireDir
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
        #print 'sequence detected in chain'
        # don't chain result tuple with non-none values
        for e in result:
            if e is not None:
                #print 'but not chaining'
                return result 
        nfunc = getattr(provider.nextProvider, func.__name__)
        return nfunc(*args[1:], **kwargs)
    else:
        return result


class BaseFanartProvider(object):

    def __init__(self, nextProvider=None):
        self.nextProvider = nextProvider

    def getPosters(self, program):
        raise Exception, 'Abstract method'
    
    def getRandomPoster(self, program):
        posters = self.getPosters(program)
        if posters:
            return random.choice(posters)
        else:
            return None

    def getSeasonAndEpisode(self, program):
        if self.nextProvider:
            return self.nextProvider.getSeasonAndEpisode(program)
        else:
            return None,None
    
    def clear(self):
        if self.nextProvider:
            self.nextProvider.clear()
    
    def close(self):
        if self.nextProvider:
            self.nextProvider.close()


class NoOpFanartProvider(BaseFanartProvider):

    def getPosters(self, program):
        return []
    
    def getRandomPoster(self, program):
        return None
    
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
                f = open(self.pfilename, 'rb')
                cache = pickle.load(f)
                f.close()
        except:
            log.exception('Error loading persistent cache from %s. Starting empty' % self.pfilename)
        return cache

    def saveCache(self):
        try:
            f = open(self.pfilename, 'wb')
            pickle.dump(self.pcache, f)
            f.close()
        except:
            log.exception('Error saving persistent cache to %s' % self.pfilename)

    def clear(self):
        super(PersistentFanartProvider, self).clear()
        self.pcache.clear()
        self.saveCache()
            
    def close(self):
        super(PersistentFanartProvider, self).close()
        self.saveCache()
        

class OneStrikeAndYoureOutFanartProvider(PersistentFanartProvider):
    """
    If a fanart provider can't serve up fanart for a program the first time, 
    chances are it won't succeed on subsequent requests. For instances where
    subsequent requests can be 'expensive', this decorator will short-circuit
    the lookup process after <insert criteria here>.
    """
    
    def __init__(self, platform, delegate, nextProvider=None):
        if not delegate:
            raise Exception('delegate cannot be None')
        oneStrikeDir = requireDir(os.path.join(platform.getCacheDir(), 'onestrike'))
        PersistentFanartProvider.__init__(self, nextProvider, os.path.join(oneStrikeDir, '%s.pickle' % delegate.__class__.__name__))
        self.delegate = delegate
        self.struckOut = self.pcache

    def createKey(self, method, program):
        return '%s-%s' % (method, md5.new(safe_str(program.title())).hexdigest())
        
    @synchronized
    def hasStruckOut(self, key):
        # TODO: use timestamp to expire struckOut period so metadata doesn't become too stale
        return key in self.struckOut
    
    @synchronized
    def strikeOut(self, key, program):
        if key in self.struckOut:
            bucket = self.struckout[key]
        else:
            bucket = {'title':program.title()}
            self.struckOut[key] = bucket
        bucket['timestamp'] = datetime.datetime.now()
    
    @chain
    def getPosters(self, program):
        posters = []
        key = self.createKey('getPosters', program) 
        if not self.hasStruckOut(key):
            posters = self.delegate.getPosters(program)
            if not posters:
                self.strikeOut(key, program)
        return posters

    @chain
    def getSeasonAndEpisode(self, program):
        season, episode = None, None
        key = self.createKey('getSeasonAndEpisode', program)
        if not self.hasStruckOut(key):
            season, episode = self.delegate.getSeasonAndEpisode(program)
            if season is None or episode is None:
                self.strikeOut(key, program)
        return season, episode 

    def clear(self):
        super(OneStrikeAndYoureOutFanartProvider, self).clear()
        self.delegate.clear()

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
    
    def getPosters(self, program):
        if (program.title() in self.SPAM):
            return []
        if self.nextProvider:
            return self.nextProvider.getPosters(program)
                
    def hasPosters(self, program):
        if (program.title() in self.SPAM):
            return True
        return self.nextProvider.hasPosters(program)
        
    def getSeasonAndEpisode(self, program):
        return self.nextProvider.getSeasonAndEpisode(program)
       
        
class SuperFastFanartProvider(PersistentFanartProvider):
    
    def __init__(self, platform, nextProvider=None):
        cacheDir = requireDir(os.path.join(platform.getCacheDir(), 'superfast'))
        PersistentFanartProvider.__init__(self, nextProvider, os.path.join(cacheDir, 'superfast.pickle'))
        self.imagePathsByKey = self.pcache

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
        
    def hasPosters(self, program):
        return self.createKey('getPosters', program) in self.imagePathsByKey
        
    def createKey(self, methodName, program):
        key = '%s-%s' % (methodName, safe_str(program.title()))
        return key

    def getSeasonAndEpisode(self, program):
        return self.nextProvider.getSeasonAndEpisode(program)
        
        
class HttpCachingFanartProvider(BaseFanartProvider):
    """Caches images retrieved via http on the local filesystem"""
    
    def __init__(self, httpCache, nextProvider=None):
        BaseFanartProvider.__init__(self, nextProvider)
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
                    log.debug('Work queue size: %d' % self.workQueue.qsize())
                workUnit = self.workQueue.get(block=True, timeout=1)
                results = workUnit['results']
                httpUrl = workUnit['httpUrl']
                filePath = self.tryToCache(httpUrl)
                if filePath:
                    log.debug('Adding %s to results of size %d' % (filePath, len(results)))
                    results.append(filePath)
            except Queue.Empty:
                pass
        
    def getPosters(self, program):
        # If the chained provider returns a http:// style url, 
        # cache the contents and return the locally cached file path
        posters = []
        if self.nextProvider:
            httpPosters = self.nextProvider.getPosters(program)
            posters = self.cachePosters(httpPosters)
        return posters

    def cachePosters(self, httpUrls):
        '''Immediately retrieve the first URL and add the remaining to the 
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
            self.workQueue.put({'results' : filepaths, 'httpUrl' : nextUrl })
        
        return filepaths
    
    def tryToCache(self, poster):
        if poster and poster[:4] == 'http':
            try:
                filepath = self.httpCache.get(poster)
            except Exception, ioe:
                log.exception(ioe)
                filepath = None
        return filepath
    
    def clear(self):
        super(HttpCachingFanartProvider, self).clear()
        self.httpCache.clear()
        
    def close(self):
        self.closeRequested = True
        super(HttpCachingFanartProvider, self).close()
        self.workThread.join()
        
    def getSeasonAndEpisode(self, program):
        return self.nextProvider.getSeasonAndEpisode(program)


class ImdbFanartProvider(BaseFanartProvider):

    def __init__(self, nextProvider=None):
        BaseFanartProvider.__init__(self, nextProvider)
        self.imdb = imdb.IMDb(accessSystem=None)

    @chain
    @max_threads(1)
    @timed
    def getPosters(self, program):
        posters = []
        if program.isMovie():
            try:
                movies = self.imdb.search_movie(title=u'' + program.title(), results=1)
                for movie in movies:
                    m = self.imdb.get_movie(movie.getID())
                    #for key,value in m.items():
                    #    log.warn('movie[%d] id[%s] key[%s] -> %s' % (1, m.getID(), key, safe_str(value)))
                    posters.append(m['full-size cover url'])  
            except imdb.IMDbError, e:
                log.error('IMDB error looking up movie: %s %s' % (safe_str(program.title()), safe_str(str(e))))
            except Exception, e:
                log.error('IMDB error looking up %s: %s' % (safe_str(program.title()), safe_str(str(e))))
        return posters
    
    def getSeasonAndEpisode(self, program):
        return None,None


class TvdbFanartProvider(BaseFanartProvider):
    
    def __init__(self, platform, nextProvider=None):
        BaseFanartProvider.__init__(self, nextProvider)
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

    @chain
    @timed    
    def getPosters(self, program):
        posters = []
        if not program.isMovie():
            try:
                # Example: tvdb['scrubs']['_banners']['poster']['680x1000']['35308']['_bannerpath']
                #posterUrl = self.tvdb[program.title()]['_banners']['poster'].itervalues().next().itervalues().next()['_bannerpath']
                
                postersByDimension = self._queryTvDb(program.title()) 
                for dimension in postersByDimension.keys():
                    #log.debug('key=%s' % dimension)
                    for id in postersByDimension[dimension].keys():
                        #log.debug('idkey = %s' % id)
                        bannerPath = postersByDimension[dimension][id]['_bannerpath']
                        #log.debug('bannerPath = %s' % bannerPath)
                        posters.append(bannerPath)
                log.debug('TVDB[%s] = %s' % (len(posters), str(program.title())))
            except Exception, e:
                log.warn('TVDB errored out on "%s" with error "%s"' % (program.title(), str(e)))
        return posters

    def clear(self):
        super(TvdbFanartProvider, self).clear()        
        shutil.rmtree(self.tvdbCacheDir, ignore_errors=True)
        requireDir(self.tvdbCacheDir)

    # tvdb site rejects queries if > 2 per originating IP
    @max_threads(2)
    def _queryTvDb(self, title):
        return self.tvdb[title]['_banners']['poster']

    @chain
    def getSeasonAndEpisode(self, program):
        # TODO: try some other method if search by original air date comes up blank
        if program.isMovie(): 
            return None, None

        try:
            show = self.tvdb[program.title()]
            originalAirDate = program.originalAirDate()
            episodes = show.airedOn(originalAirDate)
            episode = episodes.pop()
            return episode['seasonnumber'], episode['episodenumber']
        except (tvdb_api.tvdb_episodenotfound, tvdb_api.tvdb_shownotfound):
            log.debug('TVDB: Show not found - %r' % safe_str(program.title()))
            return None, None
        except (tvdb_api.tvdb_error):
            log.exception(safe_str(program.title()))
            return None, None


class TheMovieDbFanartProvider(BaseFanartProvider):
    
    def __init__(self, nextProvider=None):
        BaseFanartProvider.__init__(self, nextProvider)        
        tmdb.config['apikey'] = '4956f64b34ac586d01d6820de8e93d58'
        self.mdb = tmdb.MovieDb()
    
    @chain
    @max_threads(2)
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
                    log.debug('TMDB found nothing for: %s' % program.title())
            except Exception, e:
                log.error('TMDB fanart search error: %s %s' % (program.title(), e))
        return posters


class GoogleImageSearchProvider(BaseFanartProvider):
    
    def __init__(self, nextProvider=None):
        BaseFanartProvider.__init__(self, nextProvider)        
    
    @chain
    @max_threads(2)
    def getPosters(self, program):
        posters = []
        try:
            url_values = urllib.urlencode({'v':'1.0', 'safe':'on', 'imgar':'t', 'q':program.title()})
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
            
            for i,result in enumerate(obj['responseData']['results']):
                #log.debug('%d googleresult = %s' % (i, result['unescapedUrl']))
                posters.append(result['unescapedUrl'])
        except Exception, e:
            log.error('GOOGLE fanart search:  %s %s' % (safe_str(program.title()), str(e)))
        return posters
        

class TvRageProvider(NoOpFanartProvider):

    def __init__(self, platform, nextProvider=None):
        self.cacheDir = requireDir(os.path.join(platform.getCacheDir(), 'tvrage'))
        self.nextProvider = nextProvider
        self.memcache = {}

    def clear(self):
        self.memcache.clear()
        shutil.rmtree(self.cacheDir, ignore_errors=True)
        requireDir(self.cacheDir)         

    def load(self, program):
        '''Load tvrage.api.Show from memory or disk cache'''
        if program.title() in self.memcache.keys():
            return self.memcache[program.title()]
        
        fname = os.path.join(self.cacheDir, safe_str(program.title()))
        if not os.path.exists(fname):
            return None
        f = open(fname, 'rb')
        try:
            show = pickle.load(f)
            self.memcache[program.title()] = show
        finally: 
            f.close()
        return show
    
    def save(self, program, show):
        '''Save tvrage.api.Show to memory/disk cache'''
        f = open(os.path.join(self.cacheDir, safe_str(program.title())), 'wb')
        try:
            self.memcache[program.title()] = show
            pickle.dump(show, f)
        finally:
            f.close()
        
    @chain
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
        oad = program.originalAirDate()
        d = datetime.date(int(oad[0:4]), int(oad[5:7]), int(oad[8:10]))
        try:
            if d in show.seasonsAndEpisodes:
                return show.seasonsAndEpisodes[d]
            else:
                log.debug('TVRage: No episode found matching airdate %s in %s episodes' % (oad, len(show.seasonsAndEpisodes)))
                return self.searchBySubtitle(program, show)
        except:
            # backwards compatibility for pickled shows w/o index. return None,None to force re-query
            return None, None
        
    def searchBySubtitle(self, program, show):
        subtitle = program.subtitle()
        if subtitle is None or len(subtitle) == 0:
            return None, None
        
        for sn in xrange(1, show.seasons+1):
            try:
                season = show.season(sn)
                for en, episode in season.items():
                    if episode.title.lower() == subtitle.lower():
                        return str(sn), str(episode.number)
            except KeyError:
                log.debug('Key error')
                pass # For cases where an entire season is missing, keep going...
    
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
    
    def getRandomPoster(self, program):
        """
        @type program: Program 
        @return: returns path to image suitable as a boxcover that is shaped taller 
                 than wide (portrait mode) with medium quality resolution
                 (not for thumbnails). 
        """
        return self.provider.getRandomPoster(program)
    
    def getPosters(self, program):
        return self.provider.getPosters(program)

    def hasPosters(self, program):
        return self.provider.hasPosters(program)
    
    def clear(self):
        self.provider.clear() 

    def shutdown(self):
        self.provider.close()
        
    def configure(self, settings):
        self.provider.close()
        p = None
        if settings.getBoolean('fanart_google'): p = GoogleImageSearchProvider(p)
        if settings.getBoolean('fanart_imdb')  : p = OneStrikeAndYoureOutFanartProvider(self.platform, ImdbFanartProvider(), p)
        if settings.getBoolean('fanart_tmdb')  : p = OneStrikeAndYoureOutFanartProvider(self.platform, TheMovieDbFanartProvider(), p)
        if settings.getBoolean('fanart_tvdb')  : p = OneStrikeAndYoureOutFanartProvider(self.platform, TvdbFanartProvider(self.platform), p)
        if settings.getBoolean('fanart_tvrage'): p = OneStrikeAndYoureOutFanartProvider(self.platform, TvRageProvider(self.platform), p) 
                        
        p = HttpCachingFanartProvider(self.httpCache, p)
        self.sffp = p = SuperFastFanartProvider(self.platform, p)
        p = SpamSkippingFanartProvider(p)
        self.provider = p
    
    def onEvent(self, event):
        if event['id'] == Event.SETTING_CHANGED:
            if event['tag'] in ('fanart_tvdb', 'fanart_tmdb', 'fanart_imdb', 'fanart_google', 'fanart_tvrage',):
                self.configure(self.settings)
