# Random trailer player
#
# Author - kzeleny
# Version - 1.1.10
# Compatibility - Frodo/Gothum
#

import xbmc
import xbmcvfs
import xbmcgui
from urllib import quote_plus, unquote_plus
import datetime
import urllib
import urllib2
import re
import sys
import os
import random
import json
import time
import xbmcaddon

addon = xbmcaddon.Addon()
number_trailers =  addon.getSetting('number_trailers')
do_curtains = 'false'
do_genre = addon.getSetting('do_genre')
do_volume = addon.getSetting('do_volume')
volume = int(addon.getSetting("volume"))
path = addon.getSetting('path')
do_library=addon.getSetting('do_library')
do_folder=addon.getSetting('do_folder')
do_itunes=addon.getSetting('do_itunes')
do_tmdb=addon.getSetting('do_tmdb')
quality = addon.getSetting("quality")
quality = ["480p", "720p", "1080p"][int(quality)]
if volume > 100:
    do_volume='false'
currentVolume = xbmc.getInfoLabel("Player.Volume")
currentVolume = int((float(currentVolume.split(" ")[0])+60.0)/60.0*100.0)
trailer_type = int(addon.getSetting('trailer_type'))
g_action = addon.getSetting('g_action') == 'true'
g_comedy = addon.getSetting('g_comedy') == 'true'
g_docu = addon.getSetting('g_docu') == 'true'
g_drama = addon.getSetting('g_drama') == 'true'
g_family = addon.getSetting('g_family') == 'true'
g_fantasy = addon.getSetting('g_fantasy') == 'true'
g_foreign = addon.getSetting('g_foreign') == 'true'
g_horror = addon.getSetting('g_horror') == 'true'
g_musical = addon.getSetting('g_musical') == 'true'
g_romance = addon.getSetting('g_romance') == 'true'
g_scifi = addon.getSetting('g_scifi') == 'true'
g_thriller = addon.getSetting('g_thriller') == 'true'
hide_info = addon.getSetting('hide_info')
hide_title = addon.getSetting('hide_title')
trailers_path = addon.getSetting('path')
addon_path = addon.getAddonInfo('path')
hide_watched = addon.getSetting('hide_watched')
watched_days = addon.getSetting('watched_days')
resources_path = xbmc.translatePath( os.path.join( addon_path, 'resources' ) ).decode('utf-8')
media_path = xbmc.translatePath( os.path.join( resources_path, 'media' ) ).decode('utf-8')
open_curtain_path = xbmc.translatePath( os.path.join( media_path, 'OpenSequence.mp4' ) ).decode('utf-8')
close_curtain_path = xbmc.translatePath( os.path.join( media_path, 'ClosingSequence.mp4' ) ).decode('utf-8')
selectedGenre =''
exit_requested = False
movie_file = ''
opener = urllib2.build_opener()
opener.addheaders = [('User-Agent', 'iTunes')]
urlMain = "http://trailers.apple.com"

if len(sys.argv) == 2:
    do_genre ='false'

trailer=''
info=''
do_timeout = False
played = []

def askGenres():
    addon = xbmcaddon.Addon()
    # default is to select from all movies
    selectGenre = False
    # ask user whether they want to select a genre
    a = xbmcgui.Dialog().yesno(addon.getLocalizedString(32100), addon.getLocalizedString(32101))
    # deal with the output
    if a == 1: 
    # set filter
        selectGenre = True
    return selectGenre  
  
def selectGenre():
  success = False
  selectedGenre = ""
  myGenres = []
  trailerstring = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": { "properties": ["genre", "playcount", "file", "trailer"]}, "id": 1}')
  trailerstring = unicode(trailerstring, 'utf-8', errors='ignore')
  trailers = json.loads(trailerstring)
  if 'movies' in trailers:
      for movie in trailers["result"]["movies"]:
        # Let's get the movie genres
        genres = movie["genre"]
        for genre in genres:
            # check if the genre is a duplicate
            if not genre in myGenres:
              # if not, add it to our list
              myGenres.append(genre)
      # sort the list alphabeticallt        
      mySortedGenres = sorted(myGenres)
      # prompt user to select genre
      selectGenre = xbmcgui.Dialog().select(addon.getLocalizedString(32100), mySortedGenres)
      # check whether user cancelled selection
      if not selectGenre == -1:
        # get the user's chosen genre
        selectedGenre = mySortedGenres[selectGenre]
        success = True
      else:
        success = False
  # return the genre and whether the choice was successfult
  return success, selectedGenre

def checkRating(rating):
    passed = False
    rating_limit = addon.getSetting('rating_limit')
    do_notyetrated = addon.getSetting('do_notyetrated')
    do_nr = addon.getSetting('do_nr')
    nyr=''
    nr=''
    if do_notyetrated=='true':nyr='Not yet rated'
    if do_nr == 'true':nr='NR'
    if rating_limit=='0':passed=True
    if rating_limit=='1':
        rating_limit=['G',nr,nyr]
    if rating_limit=='2':
        rating_limit=['G','PG',nr,nyr]
    if rating_limit=='3':
        rating_limit=['G','PG','PG-13',nr,nyr]
    if rating_limit=='4':
        rating_limit=['G','PG','PG-13','R',nr,nyr]
    if rating_limit=='5':
        rating_limit=['G','PG','PG-13','R','NC-17',nr,nyr]
    if rating in rating_limit:passed=True
    return passed
    
def genreCheck(genres):
    passed = True
    if not g_action:
        if "Action and Adventure" in genres:
            passed = False
    if not g_comedy:
        if "Comedy" in genres:
            passed = False
    if not g_docu:
        if "Documentary" in genres:
            passed = False
    if not g_drama:
        if "Drama" in genres:
            passed = False
    if not g_family:
        if "Family" in genres:
            passed = False
    if not g_fantasy:
        if "Fantasy" in genres:
            passed = False
    if not g_foreign:
        if "Foreign" in genres:
            passed = False
    if not g_horror:
        if "Horror" in genres:
            passed = False
    if not g_musical:
        if "Musical" in genres:
            passed = False
    if not g_romance:
        if "Romance" in genres:
            passed = False
    if not g_scifi:
        if "Science Fiction" in genres:
            passed = False
    if not g_thriller:
        if "Thriller" in genres:
            passed = False
    return passed

def getInfo(title,year):
    data = {}
    data['query'] = title
    data['year'] = str(year)
    data['api_key'] = '99e8b7beac187a857152f57d67495cf4'
    data['language'] ='en'
    url_values = urllib.urlencode(data)
    url = 'https://api.themoviedb.org/3/search/movie'
    full_url = url + '?' + url_values
    req = urllib2.Request(full_url)
    infostring = urllib2.urlopen(req).read()
    infostring = json.loads(infostring)
    if len(infostring['results']) > 0:
        results=infostring['results'][0]
        movieId=str(results['id'])
        if not movieId == '':
            data = {}
            data['api_key'] = '99e8b7beac187a857152f57d67495cf4'
            data['append_to_response'] ='credits'
            url_values = urllib.urlencode(data)
            url = 'https://api.themoviedb.org/3/movie/' + movieId
            full_url = url + '?' + url_values
            req = urllib2.Request(full_url)
            infostring = urllib2.urlopen(req).read()
            infostring = json.loads(infostring)
            director=[]
            writer=[]
            cast=[]
            plot=''
            runtime=''
            genre=[]
            plot=infostring['overview']
            runtime=infostring['runtime']
            genres=infostring['genres']
            for g in genres:
                genre.append(g['name'])
            castMembers = infostring['credits']['cast']
            for castMember in castMembers:
                cast.append(castMember['name'])     
            crewMembers = infostring['credits']['crew']
            for crewMember in crewMembers:
                if crewMember['job'] =='Director':
                    director.append(crewMember['name'])
                if crewMember['department']=='Writing':
                    writer.append(crewMember['name'])
    else:
        director=['Unavailable']
        writer=['Unavailable']
        cast=['Unavailable']
        plot='Unavailable'
        runtime=0
        genre=['Unavailable']
    dictInfo = {'director':director,'writer':writer,'plot':plot,'cast':cast,'runtime':runtime,'genre':genre}
    return dictInfo
    
def getItunesTrailers():
    trailers=[]
    do_clips=addon.getSetting('do_clips')
    do_featurettes=addon.getSetting('do_featurettes')
    if trailer_type == 0:content = opener.open(urlMain+"/trailers/home/feeds/studios.json").read()
    if trailer_type == 1:content = opener.open(urlMain+"/trailers/home/feeds/just_added.json").read()
    if trailer_type == 2:content = opener.open(urlMain+"/trailers/home/feeds/most_pop.json").read()
    if trailer_type == 3:content = opener.open(urlMain+"/trailers/home/feeds/exclusive.json").read()
    if trailer_type == 4:content = opener.open(urlMain+"/trailers/home/feeds/studios.json").read()
    content = content.decode('unicode_escape').encode('ascii','ignore')
    spl = content.split('"title"')
    for i in range(1, len(spl), 1):
        entry = spl[i]
        match = re.compile('"poster":"(.+?)"', re.DOTALL).findall(entry)
        thumb = urlMain+match[0].replace('poster.jpg', 'poster-xlarge.jpg')
        fanart = urlMain+match[0].replace('poster.jpg', 'background.jpg')
        match = re.compile('"rating":"(.+?)"', re.DOTALL).findall(entry)
        rating = match[0]
        match = re.compile('"releasedate":"(.+?)"', re.DOTALL).findall(entry)
        if len(match)>0:
            month = match[0][8:-20]
            day = int(match[0][5:-24])
            year = int(match[0][12:-15])
            if month=='Jan':month=1
            if month=='Feb':month=2
            if month=='Mar':month=3
            if month=='Apr':month=4
            if month=='May':month=5
            if month=='Jun':month=6
            if month=='Jul':month=7
            if month=='Aug':month=8
            if month=='Sep':month=9
            if month=='Oct':month=10
            if month=='Nov':month=11
            if month=='Dec':month=12
            releasedate = datetime.date(year,month,day)
        else:
            releasedate = datetime.date.today()
        match = re.compile('"(.+?)"', re.DOTALL).findall(entry)
        title = match[0]
        match = re.compile('"genre":(.+?),', re.DOTALL).findall(entry)
        genre = match[0]
        match = re.compile('"directors":(.+?),', re.DOTALL).findall(entry)
        director = match[0]
        match = re.compile('"studio":"(.+?)",', re.DOTALL).findall(entry)
        studio = match[0]
        match = re.compile('"type":"(.+?)",', re.DOTALL).findall(entry)
        type = match[0]
        match = re.compile('"url":"(.+?)","type":"(.+?)"', re.DOTALL).findall(entry)
        for url, type in match:
            filter = ["- JP Sub","Interview","- UK","- BR Sub","- FR","- IT","- AU","- MX","- MX Sub","- BR","- RU","- DE","- ES","- FR Sub","- KR Sub","- Russian","- French","- Spanish","- German","- Latin American Spanish","- Italian"]
            filtered = False
            for f in filter:
                if f in type:
                    filtered = True
            if do_clips=='false':
                if 'Clip' in type:
                    filtered = True
            if do_featurettes =='false':
                if 'Featurette' in type:
                    filtered = True
            if trailer_type==0:
                if releasedate < datetime.date.today() :filtered = True
            if genreCheck(genre) and checkRating(rating) and not filtered:
                url = urlMain+url+"includes/"+type.replace('-', '').replace(' ', '').lower()+"/large.html"
                trailer = {'title': title, 'trailer': url, 'type':type, 'mpaa':rating,'year':year,'thumbnail':thumb,'fanart':fanart,'genre':genre,'director':director,'studio':studio,'source':'iTunes'}
                trailers.append(trailer)
    return trailers
    
def getLibraryTrailers(genre):
    # get the raw JSON output
    lib_trailers=[]
    tmp_trailers=''
    trailerstring = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["title", "lastplayed", "studio", "cast", "plot", "writer", "director", "fanart", "runtime", "mpaa", "thumbnail", "file", "year", "genre", "trailer"], "filter": {"field": "genre", "operator": "contains", "value": "%s"}}, "id": 1}' % genre)
    trailerstring = unicode(trailerstring, 'utf-8', errors='ignore') 
    trailerstring = json.loads(trailerstring)
    if trailerstring['result']['limits']['total'] > 0:
        tmp_trailers = trailerstring["result"]["movies"]  
        for trailer in tmp_trailers:
            trailer['source'] = 'library'
            trailer['type'] = 'Trailer'
            lib_trailers.append(trailer)
    return lib_trailers

def getFolderTrailers(path):
    trailers = []
    folders = []
    # multipath support
    if path.startswith('multipath://'):
        # get all paths from the multipath
        paths = path[12:-1].split('/')
        for item in paths:
            folders.append(urllib.unquote_plus(item))
    else:
        folders.append(path)
    for folder in folders:
        if xbmcvfs.exists(xbmc.translatePath(folder)):
            # get all files and subfolders
            dirs,files = xbmcvfs.listdir(folder)
            for item in files:
                if not os.path.join(folder,item) in played:
                    trailers.append(os.path.join(folder,item))
            for item in dirs:
                # recursively scan all subfolders
                trailers += getFolderTrailers(os.path.join(folder,item))
    return trailers

def getTmdbTrailers():
    tmdbTrailers=[]
    if addon.getSetting("tmdb_source") == '0':source='popular'
    if addon.getSetting("tmdb_source") == '1':source='top_rated'
    if addon.getSetting("tmdb_source") == '2':source='upcoming'
    if addon.getSetting("tmdb_source") == '3':source='now_playing'
    if addon.getSetting("tmdb_source") == '4':
        data = {}
        data['api_key'] = '99e8b7beac187a857152f57d67495cf4'
        url_values = urllib.urlencode(data)
        url = 'https://api.themoviedb.org/3/movie/latest'
        full_url = url + '?' + url_values
        req = urllib2.Request(full_url)
        infostring = urllib2.urlopen(req).read()
        infostring = json.loads(infostring)
        maxID=infostring['id']
        id=0
        for i in range(1,maxID):
            id=id+1
            dict={'trailer':'tmdb','id': id}
            tmdbTrailers.append(dict)
    else:
        page=0
        for i in range(0,5):
            page=page+1
            data = {}
            data['api_key'] = '99e8b7beac187a857152f57d67495cf4'
            data['page'] = page
            data['language']='en'
            url_values = urllib.urlencode(data)
            url = 'https://api.themoviedb.org/3/movie/' + source
            full_url = url + '?' + url_values
            req = urllib2.Request(full_url)
            infostring = urllib2.urlopen(req).read()
            infostring = json.loads(infostring)
            for result in infostring['results']:
                id=result['id']
                dict={'trailer':'tmdb','id':id}
                tmdbTrailers.append(dict)
    return tmdbTrailers

def getTmdbTrailer(movieId):
    trailer_url=''
    type=''
    you_tube_base_url='plugin://plugin.video.youtube/?action=play_video&videoid='
    image_base_url='http://image.tmdb.org/t/p/'
    data = {}
    data['append_to_response']='credits,trailers,releases'
    data['api_key'] = '99e8b7beac187a857152f57d67495cf4'
    url_values = urllib.urlencode(data)
    url = 'http://api.themoviedb.org/3/movie/' + str(movieId)
    full_url = url + '?' + url_values
    req = urllib2.Request(full_url)
    try:
        movieString = urllib2.urlopen(req).read()        
        movieString = unicode(movieString, 'utf-8', errors='ignore')
        movieString = json.loads(movieString)
    except:
        dictInfo = {'title':'','trailer': '','year':0,'studio':[],'mpaa':'','file':'','thumbnail':'','fanart':'','director':[],'writer':[],'plot':'','cast':'','runtime':0,'genre':[],'source': 'tmdb','type':''} 
    else:
        for trailer in movieString['trailers']['youtube']:
            if 'source' in trailer:
                trailer_url=you_tube_base_url + trailer['source']
                type=trailer['type']
                break
        countries = movieString['releases']['countries']
        mpaa=''
        for c in countries:
            if c['iso_3166_1'] =='US':
                mpaa=c['certification']
        year=movieString['release_date'][:-6]
        fanart=image_base_url + 'w300'+str(movieString['backdrop_path'])
        thumbnail=image_base_url + 'w342'+str(movieString['poster_path'])
        title=movieString['title']
        plot=movieString['overview']
        runtime=movieString['runtime']
        studios=movieString['production_companies']
        studio=[]
        for s in studios:
            studio.append(s['name'])
        genres=movieString['genres']
        genre=[]
        for g in genres:
            genre.append(g['name'])
        castMembers = movieString['credits']['cast']
        cast=[]
        for castMember in castMembers:
            cast.append(castMember['name'])     
        crewMembers = movieString['credits']['crew']
        director=[]
        writer=[]
        for crewMember in crewMembers:
            if crewMember['job'] =='Director':
                director.append(crewMember['name'])
            if crewMember['department']=='Writing':
                writer.append(crewMember['name'])
        addMovie=False
        for s in movieString['spoken_languages']:
            if s['name']=='English':
                addMovie=True
        if movieString['adult']=='true':AddMovie = False
        if not addMovie:
            dictInfo = {'title':'','trailer': '','year':0,'studio':[],'mpaa':'','file':'','thumbnail':'','fanart':'','director':[],'writer':[],'plot':'','cast':'','runtime':0,'genre':[],'source': 'tmdb','type':''} 
        else:
            dictInfo = {'title':title,'trailer': trailer_url,'year':year,'studio':studio,'mpaa':mpaa,'file':'','thumbnail':thumbnail,'fanart':fanart,'director':director,'writer':writer,'plot':plot,'cast':cast,'runtime':runtime,'genre':genre,'source': 'tmdb','type':type} 
    return dictInfo
        
class blankWindow(xbmcgui.WindowXML):
    def onInit(self):
        pass
        
class trailerWindow(xbmcgui.WindowXMLDialog):

    def onInit(self):
        global played
        global SelectedGenre
        global trailer
        global info
        global do_timeout
        global NUMBER_TRAILERS
        global trailercount
        global source
        random.shuffle(trailers)
        trailercount=0
        trailer=random.choice(trailers)
        while trailer["number"] in played:
            trailer=random.choice(trailers)
            trailercount=trailercount+1
            if trailercount == len(trailers):
                played=[]
        played.append(trailer["number"])
        if trailer['trailer']=='tmdb':
            if addon.getSetting('tmdb_source') == '4':
                dp=xbmcgui.DialogProgress()
                dp.create('Random Trailers','Please wait while we get a random trailer from themoviedb...')
                gotTrailer=False
                searchCount=0
                while not gotTrailer:
                    searchCount=searchCount+1
                    trailer=getTmdbTrailer(trailer['id'])
                    if trailer['trailer'] != '':
                        gotTrailer=True
                    else:
                        trailer=random.choice(trailers)
                        while trailer["number"] in played:
                            trailer=random.choice(trailers)
                            trailercount=trailercount+1
                            if trailercount == len(trailers):
                                played=[]
                            played.append(trailer["number"])
                    dp.update(0,'Please wait while we get a random trailer from themoviedb...','Searched '+ str(searchCount) + ' movies with trailers...')
                    if dp.iscanceled():
                        break
                dp.close()
                del dp
            else:
                trailer=getTmdbTrailer(trailer['id'])
        source=trailer['source']
        lastPlay = True
        if 'lastplayed' in trailer:
            if not trailer["lastplayed"] =='' and hide_watched == 'true':
                pd=time.strptime(trailer["lastplayed"],'%Y-%m-%d %H:%M:%S')
                pd = time.mktime(pd)
                pd = datetime.datetime.fromtimestamp(pd)
                lastPlay = datetime.datetime.now() - pd
                lastPlay = lastPlay.days
                if lastPlay > int(watched_days) or watched_days == '0':
                    lastPlay = True
                else:
                    lastPlay = False
        if source == 'iTunes':
            content = opener.open(trailer['trailer']).read()
            match = re.compile('<a class="movieLink" href="(.+?)"', re.DOTALL).findall(content)
            urlTemp = match[0]
            url = urlTemp[:urlTemp.find("?")].replace("480p", "h"+quality)+"|User-Agent=iTunes/9.1.1"
        else:
            url = trailer['trailer'].encode('ascii', 'ignore')
        if  trailer["trailer"] != '' and lastPlay:
            NUMBER_TRAILERS = NUMBER_TRAILERS -1
            if hide_info == 'false' and source !='folder':
                if source == 'iTunes':
                    info = getInfo(trailer['title'],trailer['year'])
                w=infoWindow('script-DialogVideoInfo.xml',addon_path,'default')
                do_timeout=True
                w.doModal()
                if not exit_requested:
                    xbmc.Player().play(url)
                do_timeout=False
                del w
                if exit_requested:
                    xbmc.Player().play(trailer['file'])
            else:
                xbmc.Player().play(url)
                NUMBER_TRAILERS = NUMBER_TRAILERS -1
            if source == 'folder':
                self.getControl(30011).setLabel(trailer["title"] + ' - ' + trailer['source']+ ' ' + trailer['type'])
            else:
                self.getControl(30011).setLabel(trailer["title"] + ' - ' + trailer['source'] + ' ' + trailer['type'] + ' - ' + str(trailer["year"]))
            if hide_title == 'false':
                self.getControl(30011).setVisible(True)
            else:
                self.getControl(30011).setVisible(False)
            while xbmc.Player().isPlaying():                
                xbmc.sleep(250)
        self.close()
        
    def onAction(self, action):
        ACTION_PREVIOUS_MENU = 10
        ACTION_BACK = 92
        ACTION_ENTER = 7
        ACTION_I = 11
        ACTION_LEFT = 1
        ACTION_RIGHT = 2
        ACTION_UP = 3
        ACTION_DOWN = 4
        ACTION_TAB = 18
        ACTION_M = 122
        ACTION_Q=34
        
        global exit_requested
        global movie_file
        global source
        global trailer
        movie_file=''

        if action == ACTION_Q:
            strCouchPotato='plugin://plugin.video.couchpotato_manager/movies/add?title='+trailer['title']
            xbmc.executebuiltin('XBMC.RunPlugin('+strCouchPotato+')')
        
        if action == ACTION_PREVIOUS_MENU or action == ACTION_LEFT or action == ACTION_BACK:
            xbmc.Player().stop()
            exit_requested = True
            self.close()

        if action == ACTION_RIGHT or action == ACTION_TAB:
            xbmc.Player().stop()
            
        if action == ACTION_ENTER:
            exit_requested = True
            xbmc.Player().stop()
            movie_file = trailer["file"]
            self.getControl(30011).setVisible(False)
            self.close()
            
        if action == ACTION_M:
            self.getControl(30011).setVisible(True)
            xbmc.sleep(2000)
            self.getControl(30011).setVisible(False)
        
        if action == ACTION_I or action == ACTION_UP:
            if source !='folder':
                self.getControl(30011).setVisible(False)
                w=infoWindow('script-DialogVideoInfo.xml',addon_path,'default')
                w.doModal()
            if hide_title == 'false':
                self.getControl(30011).setVisible(True)
            else:
                self.getControl(30011).setVisible(False)
                              
class infoWindow(xbmcgui.WindowXMLDialog):
    def onInit(self):
        source = trailer['source']
        if source == 'iTunes':
            info=getInfo(trailer['title'],trailer['year'])
        self.getControl(30001).setImage(trailer["thumbnail"])
        self.getControl(30003).setImage(trailer["fanart"])
        self.getControl(30002).setLabel(trailer["title"] + ' - ' + trailer['source'] + ' ' + trailer['type'] + ' - ' + str(trailer["year"]))
        movieDirector=''
        movieWriter=''
        if source=='iTunes':
            writers = info['writer']
            directors = info['director']
            actors = info['cast']
            plot = info['plot']
            movieActor=''
            actorcount=0        
            for actor in actors:
                actorcount=actorcount+1
                movieActor = movieActor + actor + ", "
                if actorcount == 8: break
            if not movieActor == '':
                movieActor = movieActor[:-2]    
        else:
            plot=trailer["plot"]
            writers = trailer["writer"]
            directors = trailer["director"]
            actors = trailer["cast"]
            movieActor=''
            actorcount=0
            if source=='library':
                for actor in actors:
                    actorcount=actorcount+1
                    movieActor = movieActor + actor['name'] + ", "
                    if actorcount == 8: break
                if not movieActor == '':
                    movieActor = movieActor[:-2] 
            else:
                movieActor=''
                actorcount=0        
                for actor in actors:
                    actorcount=actorcount+1
                    movieActor = movieActor + actor + ", "
                    if actorcount == 8: break
                if not movieActor == '':
                    movieActor = movieActor[:-2]    
        for director in directors:
            movieDirector = movieDirector + director + ", "
        if not movieDirector =='':
            movieDirector = movieDirector[:-2]
        for writer in writers:
            movieWriter = movieWriter + writer + ", "
        if not movieWriter =='':
            movieWriter = movieWriter[:-2]                
        self.getControl(30005).setLabel(movieDirector)
        self.getControl(30006).setText(movieActor)
        self.getControl(30005).setLabel(movieDirector)
        self.getControl(30007).setLabel(movieWriter)
        self.getControl(30009).setText(plot)
        movieStudio=''
        if source == 'iTunes':
            studios=trailer["studio"]        
            movieStudio=studios
        if source =='library' or source == 'tmdb':
            studios=trailer["studio"]
            for studio in studios:
                movieStudio = movieStudio + studio + ", "
                if not movieStudio =='':
                    movieStudio = movieStudio[:-2]
        self.getControl(30010).setLabel(movieStudio)
        movieGenre=''
        if source =='iTunes':
            genres = info['genre']
        if source =='library' or source == 'tmdb':
            genres = trailer["genre"]
        for genre in genres:
            movieGenre = movieGenre + genre + " / "
        if not movieGenre =='':
            movieGenre = movieGenre[:-3]
        runtime=''
        if source == 'iTunes':runtime=''
        if source == 'library':runtime=str(trailer["runtime"] / 60)
        if runtime != '':runtime=runtime + ' Minutes - '
        self.getControl(30011).setLabel(runtime + movieGenre)
        imgRating='ratings/notrated.png'
        if trailer["mpaa"].startswith('G'): imgRating='ratings/g.png'
        if trailer["mpaa"] == ('G'): imgRating='ratings/g.png'
        if trailer["mpaa"].startswith('Rated G'): imgRating='ratings/g.png'
        if trailer["mpaa"].startswith('PG '): imgRating='ratings/pg.png'
        if trailer["mpaa"] == ('PG'): imgRating='ratings/pg.png'
        if trailer["mpaa"].startswith('Rated PG'): imgRating='ratings/pg.png'
        if trailer["mpaa"].startswith('PG-13 '): imgRating='ratings/pg13.png'
        if trailer["mpaa"] == ('PG-13'): imgRating='ratings/pg13.png'
        if trailer["mpaa"].startswith('Rated PG-13'): imgRating='ratings/pg13.png'
        if trailer["mpaa"].startswith('R '): imgRating='ratings/r.png'
        if trailer["mpaa"] == ('R'): imgRating='ratings/r.png'
        if trailer["mpaa"].startswith('Rated R'): imgRating='ratings/r.png'
        if trailer["mpaa"].startswith('NC17'): imgRating='ratings/nc17.png'
        if trailer["mpaa"].startswith('Rated NC17'): imgRating='ratings/nc1.png'
        self.getControl(30013).setImage(imgRating)
        if do_timeout:
            xbmc.sleep(6000)
            self.close()
        
    def onAction(self, action):
        ACTION_PREVIOUS_MENU = 10
        ACTION_BACK = 92
        ACTION_ENTER = 7
        ACTION_I = 11
        ACTION_LEFT = 1
        ACTION_RIGHT = 2
        ACTION_UP = 3
        ACTION_DOWN = 4
        ACTION_TAB = 18
        ACTION_Q = 34
        
        global do_timeout
        global exit_requested
        global trailer
        global movie_file
        movie_file=''
        
        if action == ACTION_PREVIOUS_MENU or action == ACTION_LEFT or action == ACTION_BACK:
            do_timeout=False
            xbmc.Player().stop()
            exit_requested=True
            self.close()
        
        if action == ACTION_Q:
            strCouchPotato='plugin://plugin.video.couchpotato_manager/movies/add?title='+trailer['title']
            xbmc.executebuiltin('XBMC.RunPlugin('+strCouchPotato+')') 
            
        if action == ACTION_I or action == ACTION_DOWN:
            self.close()
            
        if action == ACTION_RIGHT or action == ACTION_TAB:
            xbmc.Player().stop()
            self.close()

        if action == ACTION_ENTER:
            movie_file = trailer["file"]
            xbmc.Player().stop()
            exit_requested=True
            self.close()
                    
def playTrailers():
    global exit_requested
    global movie_file
    global NUMBER_TRAILERS
    global trailercount
    movie_file = ''
    exit_requested = False
    DO_CURTIANS = addon.getSetting('do_animation')
    DO_EXIT = addon.getSetting('do_exit')
    NUMBER_TRAILERS =  int(addon.getSetting('number_trailers'))
    if DO_CURTIANS == 'true':
        xbmc.Player().play(open_curtain_path)
        while xbmc.Player().isPlaying():
            xbmc.sleep(250)
    trailercount = 0
    while not exit_requested:
        if NUMBER_TRAILERS == 0:
            while not exit_requested and not xbmc.abortRequested:
                mytrailerWindow = trailerWindow('script-trailerwindow.xml', addon_path,'default',)
                mytrailerWindow.doModal()
                del mytrailerWindow
        else:
            while NUMBER_TRAILERS > 0:
                mytrailerWindow = trailerWindow('script-trailerwindow.xml', addon_path,'default',)
                mytrailerWindow.doModal()
                del mytrailerWindow
                if exit_requested:
                    break
        if not exit_requested:
            if DO_CURTIANS == 'true':
                xbmc.Player().play(close_curtain_path)
                while xbmc.Player().isPlaying():
                    xbmc.sleep(250)
        exit_requested=True

if not xbmc.Player().isPlaying():
    bs = blankWindow('script-BlankWindow.xml', addon_path,'default',)
    bs.show()
    trailers = []
    filtergenre = False
    trailerNumber = 0
    if do_library == 'true':
        if do_genre == 'true':
            filtergenre = askGenres()
        success = False
        if filtergenre:
            success, selectedGenre = selectGenre()
        if success:
            library_trailers = getLibraryTrailers(selectedGenre)
        else:
            library_trailers = getLibraryTrailers("")
        library_trailers = getLibraryTrailers("")
        for trailer in library_trailers:
            trailerNumber= trailerNumber+1
            trailer['number']=trailerNumber
            trailers.append(trailer) 
    if do_folder == 'true' and path !='':
        folder_trailers = getFolderTrailers(path)
        for trailer in folder_trailers:
            trailerNumber=trailerNumber +1
            title = xbmc.translatePath(trailer)
            title =os.path.basename(title)
            title =os.path.splitext(title)[0]   
            dictTrailer={'title':title,'trailer':trailer,'type':'trailer','source':'folder','number':trailerNumber}
            trailers.append(dictTrailer)
    if do_itunes == 'true':
        iTunes_trailers = getItunesTrailers()
        for trailer in iTunes_trailers:
            trailerNumber=trailerNumber+1
            trailer['number']=trailerNumber
            trailers.append(trailer)
    if do_tmdb =='true':
        tmdbTrailers=getTmdbTrailers()
        for trailer in tmdbTrailers:
            trailerNumber=trailerNumber+1
            trailer['number']=trailerNumber 
            trailers.append(trailer)
    if do_volume == 'true':
        muted = xbmc.getCondVisibility("Player.Muted")
        if not muted and volume == 0:
            xbmc.executebuiltin('xbmc.Mute()')
        else:
            xbmc.executebuiltin('XBMC.SetVolume('+str(volume)+')')
    if len(trailers) > 0:
       playTrailers()
    del bs
    if do_volume == 'true':
        muted = xbmc.getCondVisibility("Player.Muted")
        if muted and volume == 0:
            xbmc.executebuiltin('xbmc.Mute()')
        else:
            xbmc.executebuiltin('XBMC.SetVolume('+str(currentVolume)+')')        
else:
    xbmc.log('Random Trailers: ' + 'Exiting Random Trailers Screen Saver Something is playing!!!!!!')
