# Credits: Daledude, WestCoast13
# Awesome efficient lightweight code.
# last modified 19 March 2011
# added support for TVDB search for show, seasons, episodes
# also searches imdb (using http://www.omdbapi.com/) for missing info in movies or tvshows

import sys
import simplejson as simplejson 

import urllib, re
from datetime import datetime
import time
from addon.common.net import Net  
from addon.common.addon import Addon       
from threading import Thread
try:
    import Queue as queue
except ImportError:
    import queue
net = Net()
addon = Addon('script.module.metahandler')

class TMDB(object):
    '''
    This class performs TMDB and IMDB lookups.
    
    First call is made to TMDB by either IMDB ID or Name/Year depending on what is supplied. If movie is not found
    or if there is data missing on TMDB, another call is made to IMDB to fill in the missing information.       
    '''  
    
    def __init__(self, api_key='', view='json', lang='en'):
        #view = yaml json xml
        self.view = view
        self.lang = lang
        self.api_key = api_key
        self.url_prefix = 'http://api.themoviedb.org/3'
        self.imdb_api = 'http://www.omdbapi.com/?i=%s'
        self.imdb_name_api = 'http://www.omdbapi.com/?t=%s'
        self.imdb_nameyear_api = 'http://www.omdbapi.com/?t=%s&y=%s' 
      
    def __clean_name(self, mystring):
        newstring = ''
        for word in mystring.split(' '):
            if word.isalnum()==False:
                w = ""          
                for i in range(len(word)):
                    if(word[i].isalnum()):              
                        w+=word[i]
                word = w
            newstring += ' ' + word
        return newstring.strip()


    def _do_request(self, method, values):
        '''
        Request JSON data from TMDB
        
        Args:
            method (str): Type of TMDB request to make
            values (str): Value to use in TMDB lookup request
                        
        Returns:
            DICT of meta data found on TMDB
            Returns None when not found or error requesting page
        '''      
        url = "%s/%s?language=%s&api_key=%s&%s" % (self.url_prefix, method, self.lang, self.api_key, values)
        addon.log('Requesting TMDB : %s' % url, 0)
        try:
            meta = simplejson.loads(net.http_GET(url,{"Accept":"application/json"}).content)
        except Exception, e:
            addon.log("Error connecting to TMDB: %s " % e, 4)
            return None

        if meta == 'Nothing found.':
            return None
        else:
            addon.log('TMDB Meta: %s' % meta, 0)
            return meta


    def _do_request_all(self, method, values):
        '''
        Request JSON data from TMDB, returns all matches found
        
        Args:
            method (str): Type of TMDB request to make
            values (str): Value to use in TMDB lookup request
                        
        Returns:
            DICT of meta data found on TMDB
            Returns None when not found or error requesting page
        '''      
        url = "%s/%s?language=%s&api_key=%s&%s" % (self.url_prefix, method, self.lang, self.api_key, values)
        addon.log('Requesting TMDB : %s' % url, 0)
        try:
            meta = simplejson.loads(net.http_GET(url,{"Accept":"application/json"}).content)
        except Exception, e:
            addon.log("Error connecting to TMDB: %s " % e, 4)
            return None

        if meta == 'Nothing found.':
            return None
        else:
            addon.log('TMDB Meta: %s' % meta, 0)
            return meta


    def _convert_date(self, string, in_format, out_format):
        ''' Helper method to convert a string date to a given format '''
        strptime = lambda date_string, format: datetime(*(time.strptime(date_string, format)[0:6]))
        try:
            a = strptime(string, in_format).strftime(out_format)
        except Exception, e:
            addon.log('************* Error Date conversion failed: %s' % e, 4)
            return None
        return a
        
        
    def _upd_key(self, meta, key):
        ''' Helper method to check if a key exists and if it has valid data, returns True if key needs to be udpated with valid data '''    
        if meta.has_key(key) == False :
            return True 
        else:
            try:
                bad_list = ['', '0.0', '0', 0, 'None', '[]', 'No overview found.', 'TBD', 'N/A', None]
                if meta[key] in bad_list:
                    return True
                else:
                    return False
            except:
                return True

                
    def call_config(self):
        '''
        Query TMDB config api for current values
        '''
        r = self._do_request('configuration', '')
        return r        

        
    def search_imdb(self, name, imdb_id='', year=''):
        '''
        Search IMDB by either IMDB ID or Name/Year      
        
        Args:
            name (str): full name of movie you are searching            
        Kwargs:
            imdb_id (str): IMDB ID
            year (str): 4 digit year of video, recommended to include the year whenever possible
                        to maximize correct search results.
                        
        Returns:
            DICT of meta data or None if cannot be found.
        '''        
        #Set IMDB API URL based on the type of search we need to do
        if imdb_id:
            url = self.imdb_api % imdb_id
        else:
            name = urllib.quote(name)
            if year:
                url = self.imdb_nameyear_api % (name, year)
            else:
                url = self.imdb_name_api % name

        try:
            addon.log('Requesting IMDB : %s' % url, 0)
            meta = simplejson.loads(net.http_GET(url).content)
            addon.log('IMDB Meta: %s' % meta, 0)
        except Exception, e:
            addon.log("Error connecting to IMDB: %s " % e, 4)
            return {}

        if meta['Response'] == 'True':
            return meta
        else:
            return {}
        

    def update_imdb_meta(self, meta, imdb_meta):
        '''
        Update dict TMDB meta with data found on IMDB where appropriate
        
        Args:
            meta (dict): typically a container of meta data found on TMDB
            imdb_meta (dict): container of meta data found on IMDB
                       
        Returns:
            DICT of updated meta data container
        '''        
        addon.log('Updating current meta with IMDB', 0)
        
        if self._upd_key(meta, 'overview') and self._upd_key(meta, 'plot'):
            addon.log('-- IMDB - Updating Overview', 0)
            if imdb_meta.has_key('Plot'):
                meta['overview']=imdb_meta['Plot']           
        
        if self._upd_key(meta, 'released') and self._upd_key(meta, 'premiered'):
            addon.log('-- IMDB - Updating Premiered', 0)
            
            temp=self._convert_date(imdb_meta['Released'], '%d %b %Y', '%Y-%m-%d')
            #May have failed, lets try a different format
            if not temp:
                temp=self._convert_date(imdb_meta['Released'], '%b %Y', '%Y-%m-%d')
            
            if temp:
                meta['released'] = temp
            else:
                if imdb_meta['Year'] != 'N/A':
                    meta['released'] = imdb_meta['Year'] + '-01-01'
        
        if self._upd_key(meta, 'cover_url'):
            addon.log('-- IMDB - Updating Posters', 0)
            temp=imdb_meta['Poster']
            if temp != 'N/A':
                meta['cover_url']=temp
        
        if self._upd_key(meta, 'rating'):
            addon.log('-- IMDB - Updating Rating', 0)
            imdb_rating = imdb_meta['imdbRating']
            if imdb_rating not in ('N/A', '', None):
                meta['rating'] = imdb_rating
            else:
                if meta.has_key('tmdb_rating'):
                    meta['rating'] = meta['tmdb_rating']

        if self._upd_key(meta, 'certification'):
            if imdb_meta['Rated']:
                addon.log('-- IMDB - Updating MPAA', 0)
                meta['certification'] = imdb_meta['Rated']

        if self._upd_key(meta, 'director'):
            if imdb_meta['Director']:
                addon.log('-- IMDB - Updating Director', 0)
                meta['director'] = imdb_meta['Director']

        if self._upd_key(meta, 'writer'):
            if imdb_meta['Writer']:
                addon.log('-- IMDB - Updating Writer', 0)
                meta['writer'] = imdb_meta['Writer']

        if not self._upd_key(imdb_meta, 'imdbVotes'):
            meta['votes'] = imdb_meta['imdbVotes']
        else:
            meta['votes'] = ''
                
        if self._upd_key(meta, 'genre'):
            addon.log('-- IMDB - Updating Genre', 0)
            temp=imdb_meta['Genre']
            if temp != 'N/A':
                meta['genre']=temp
                
        if self._upd_key(meta, 'runtime') and self._upd_key(meta, 'duration'):
            addon.log('-- IMDB - Updating Runtime', 0)
            temp=imdb_meta['Runtime']
            if temp != 'N/A':
                dur=0
                scrape=re.compile('([0-9]+) h ([0-9]+) min').findall(temp)
                if len(scrape) > 0:
                    dur = (int(scrape[0][0]) * 60) + int(scrape[0][1])
                scrape=re.compile('([0-9]+) hr').findall(temp)
                if len(scrape) > 0:
                    dur = int(scrape[0]) * 60
                scrape=re.compile(' ([0-9]+) ([0-9]+) min').findall(temp)
                if len(scrape) > 0:
                    dur = dur + int(scrape[0][1])
                else: # No hrs in duration
                    scrape=re.compile('([0-9]+) min').findall(temp)
                    if len(scrape) > 0:
                        dur = dur + int(scrape[0])
                meta['runtime']=str(dur)
        
        meta['imdb_id'] = imdb_meta['imdbID']       
        return meta


    def _get_info(self, tmdb_id, values='', q = False):
        ''' Helper method to start a TMDB getInfo request '''            
        r = self._do_request('movie/'+str(tmdb_id), values)
        if q: q.put(r)
        return r


    def _get_cast(self, tmdb_id, q = False):
        ''' Helper method to start a TMDB getCast request '''            
        r = self._do_request('movie/'+str(tmdb_id)+'/casts', '')
        if q: q.put(r)
        return r


    def _get_trailer(self, tmdb_id, q = False):
        ''' Helper method to start a TMDB trailer request '''            
        r = self._do_request('movie/'+str(tmdb_id)+'/trailers', '')
        if q: q.put(r)
        return r


    def _get_similar_movies(self, tmdb_id, page):
        ''' Helper method to start a TMDB get similar movies request '''            
        r = self._do_request('movie/'+str(tmdb_id)+'/similar_movies', 'page=%s' % page)
        return r


    def _search_movie(self, name, year=''):
        ''' Helper method to start a TMDB Movie.search request - search by Name/Year '''
        name = urllib.quote(self.__clean_name(name))
        if year:
            name = name + '&year=' + year
        return self._do_request('search/movie','query='+name)


    def tmdb_similar_movies(self, tmdb_id, page=1):
        '''
        Query for a list of movies that are similar to the given id
        
        MUST use a TMDB ID - NOT a IMDB ID
        
        Returns a tuple of matches containing movie name and imdb id
        
        Args:
            tmdb_id (str): MUST be a valid TMDB ID
            page (int): Page # of results to return - check # of pages first before calling subsequent pages
                        
        Returns:
            DICT of matches
        '''
        return self._get_similar_movies(tmdb_id, page)


    def tmdb_search(self, name):
        '''
        Used primarily to update a single movie meta data by providing a list of possible matches
        
        Returns a tuple of matches containing movie name and imdb id
        
        Args:
            name (str): full name of movie you are searching            
                        
        Returns:
            DICT of matches
        '''
        return self._do_request_all('search/movie','query='+urllib.quote(name))
        
        
    def tmdb_lookup(self, name, imdb_id='', tmdb_id='', year=''):
        '''
        Main callable method which initiates the TMDB/IMDB meta data lookup
        
        Returns a final dict of meta data    
        
        Args:
            name (str): full name of movie you are searching            
        Kwargs:
            imdb_id (str): IMDB ID
            tmdb_id (str): TMDB ID
            year (str): 4 digit year of video, recommended to include the year whenever possible
                        to maximize correct search results.
                        
        Returns:
            DICT of meta data
        ''' 
        meta = {}
        
        #If we don't have an IMDB ID or TMDB ID let's try searching TMDB first by movie name
        if not imdb_id and not tmdb_id:
            meta = self._search_movie(name,year)              
            ##Retry without the year
            if meta and meta['total_results'] == 0 and year:
                meta = self._search_movie(name,'')
            if meta and meta['total_results'] != 0 and meta['results']:
                tmdb_id = meta['results'][0]['id']
                if meta['results'][0].has_key('imdb_id'):
                    imdb_id = meta['results'][0]['imdb_id']
            
            #Didn't get a match by name at TMDB, let's try IMDB by name
            else:
                meta = self.search_imdb(name, year=year)
                if meta:
                    imdb_id = meta['imdbID']                         

        #If we don't have a tmdb_id yet but do have imdb_id lets see if we can find it
        elif imdb_id and not tmdb_id:
            #tmdb api v3 supports imdb_id
            tmdb_id = imdb_id

        if tmdb_id:

            #Attempt to grab all info in one request
            meta = self._get_info(tmdb_id, 'append_to_response=casts,trailers')
            if meta is None: # fall through to IMDB lookup
                meta = {}
            else:
                #Parse out extra info from request
                cast = meta['casts']
                trailers = meta['trailers']
                
                if meta.has_key('poster_path') and meta['poster_path']:
                    meta['cover_url'] = meta['poster_path']
                if meta.has_key('backdrop_path') and meta['backdrop_path']:
                    meta['backdrop_url'] = meta['backdrop_path']
                meta['released'] = meta['release_date']
                #Set rating to 0 so that we can force it to be grabbed from IMDB
                meta['tmdb_rating'] = meta['vote_average']
                meta['rating'] = 0
                if cast:
                    meta['cast'] = cast['cast']
                    meta['crew'] = cast['crew']

                if trailers:
                    #We only want youtube trailers
                    trailers = trailers['youtube']

                    #Only want trailers - no Featurettes etc.
                    found_trailer = next((item for item in trailers if 'Trailer' in item["name"] and item['type'] == 'Trailer'), None)
                    if found_trailer:
                        meta['trailers'] = found_trailer['source']
                    else:
                        meta['trailers'] = ''
                else:
                    meta['trailers'] = ''

                #Update any missing information from IDMB
                if meta.has_key('imdb_id'):
                    imdb_id = meta['imdb_id']
            if imdb_id: 
                addon.log('Requesting IMDB for extra information: %s' % imdb_id, 0)
                imdb_meta = self.search_imdb(name, imdb_id)
                if imdb_meta:
                    meta = self.update_imdb_meta(meta, imdb_meta)
        
        #If all else fails, and we don't have a TMDB id
        else:
            imdb_meta = self.search_imdb(name, imdb_id, year)
            if imdb_meta:
                meta = self.update_imdb_meta({}, imdb_meta)
       
        return meta

