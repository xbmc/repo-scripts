# Random trailer player
#
# Author - kzeleny
# Version - 1.1.15
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
import xml.dom.minidom
from xml.dom.minidom import Node

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

def getTitleFont():
    title_font='font13'
    base_size=20
    multiplier=1
    skin_dir = xbmc.translatePath("special://skin/")
    list_dir = os.listdir( skin_dir )
    fonts=[]
    fontxml_path =''
    font_xml=''
    for item in list_dir:
        item = os.path.join( skin_dir, item )
        if os.path.isdir( item ):
            font_xml = os.path.join( item, "Font.xml" )
        if os.path.exists( font_xml ):
            fontxml_path=font_xml
            break
    dom =  xml.dom.minidom.parse(fontxml_path)
    fontlist=dom.getElementsByTagName('font')
    for font in fontlist:
        name = font.getElementsByTagName('name')[0].childNodes[0].nodeValue
        size = font.getElementsByTagName('size')[0].childNodes[0].nodeValue
        fonts.append({'name':name,'size':float(size)})
    fonts =sorted(fonts, key=lambda k: k['size'])
    for f in fonts:
        if f['name']=='font13':
            multiplier=f['size'] / 20
            break
    for f in fonts:
        if f['size'] >= 38 * multiplier:
            title_font=f['name']
            break
    return title_font

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
        rating_limit=('G',nr,nyr)
    if rating_limit=='2':
        rating_limit=('G','PG',nr,nyr)
    if rating_limit=='3':
        rating_limit=('G','PG','PG-13',nr,nyr)
    if rating_limit=='4':
        rating_limit=('G','PG','PG-13','R',nr,nyr)
    if rating_limit=='5':
        rating_limit=('G','PG','PG-13','R','NC-17','NC17',nr,nyr)
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
            mpaa=get_mpaa(trailer)
            if checkRating(mpaa):
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
    if addon.getSetting("tmdb_source") == '4':source='dvd'
    if addon.getSetting("tmdb_source") == '5':source='all'
    rating_limit=addon.getSetting('rating_limit')
    if rating_limit=='0':rating_limit='NC-17'
    if rating_limit=='1':rating_limit='G'
    if rating_limit=='2':rating_limit='PG'
    if rating_limit=='3':rating_limit='PG-13'
    if rating_limit=='4':rating_limit='R'
    if rating_limit=='5':rating_limit='NC-17'
    if source=='all':
        data = {}
        data['api_key'] = '99e8b7beac187a857152f57d67495cf4'
        data['sort_by'] ='popularity.desc'
        data['certification_country']='us'
        data['certification.lte']=rating_limit
        url_values = urllib.urlencode(data)
        url = 'http://api.themoviedb.org/3/discover/movie'
        full_url = url + '?' + url_values
        req = urllib2.Request(full_url)
        infostring = urllib2.urlopen(req).read()
        infostring = json.loads(infostring)
        total_pages=infostring['total_pages']
        if total_pages > 1000: total_pages=1000
        for i in range(1,11):
            data = {}
            data['api_key'] = '99e8b7beac187a857152f57d67495cf4'
            data['sort_by'] ='popularity.desc'
            data['certification_country']='us'
            data['certification.lte']=rating_limit
            data['page']=random.randrange(1,total_pages+1)
            url_values = urllib.urlencode(data)
            url = 'http://api.themoviedb.org/3/discover/movie'
            full_url = url + '?' + url_values
            req = urllib2.Request(full_url)
            infostring = urllib2.urlopen(req).read()
            infostring = json.loads(infostring)
            for movie in infostring['results']:
                id=movie['id']
                dict={'trailer':'tmdb','id': id,'source':'tmdb','title':movie['title']}
                tmdbTrailers.append(dict)

    elif source=='dvd':
        data={}
        data['apikey']='99dgtphe3c29y85m2g8dmdmt'
        data['country'] = 'us'
        url_values = urllib.urlencode(data)
        url = 'http://api.rottentomatoes.com/api/public/v1.0/lists/dvds/new_releases.json'
        full_url = url + '?' + url_values
        req = urllib2.Request(full_url)
        response = urllib2.urlopen(req).read()
        infostring = json.loads(response)
        for movie in infostring['movies']:
            data={}
            data['api_key']='99e8b7beac187a857152f57d67495cf4'
            data['query']=movie['title']
            data['year']=movie['year']
            url_values = urllib.urlencode(data)
            url = 'https://api.themoviedb.org/3/search/movie'
            full_url = url + '?' + url_values
            req = urllib2.Request(full_url)
            infostring = urllib2.urlopen(req).read()
            infostring = json.loads(infostring)
            for m in infostring['results']:
                id=m['id']
                dict={'trailer':'tmdb','id': id,'source':'tmdb','title':movie['title']}
                tmdbTrailers.append(dict)
                break
    else:
        page=0
        for i in range(0,11):
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
                dict={'trailer':'tmdb','id': id,'source':'tmdb','title':movie['title']}
                tmdbTrailers.append(dict)
            if infostring['total_pages']==page:
                break
    return tmdbTrailers

def search_tmdb(title,year):
    id=''
    data = {}
    data['api_key'] = '99e8b7beac187a857152f57d67495cf4'
    data['page']='1'
    data['query']=query
    data['language']='en'
    url_values = urllib.urlencode(data)
    url = 'https://api.themoviedb.org/3/search/movie'
    full_url = url + '?' + url_values
    req = urllib2.Request(full_url)
    infostring = urllib2.urlopen(req).read()
    infostring = json.loads(infostring)
    results=infostring['results']
    for movie in results:
        if movie['year']==year:
            id=movie['id']
            break
    return id    

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
        if mpaa=='':mpaa='NR'
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
        if movieString['adult']=='true':addMovie = False
        addMovie=checkRating(mpaa)
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
        windowstring = xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"GUI.GetProperties","params":{"properties":["currentwindow"]},"id":1}')
        windowstring=json.loads(windowstring)
        xbmc.log('Trailer_Window_id = ' + str(windowstring['result']['currentwindow']['id']))
        global played
        global SelectedGene
        global trailer
        global info
        global do_timeout
        global NUMBER_TRAILERS
        global trailercountF
        global source
        random.shuffle(trailers)
        trailercount=0
        trailer=random.choice(trailers)
        while trailer['title'] in played:
            trailer=random.choice(trailers)
            trailercount=trailercount+1
            if trailercount == len(trailers):
                played=[]
        if trailer['trailer']=='tmdb':
            trailer=getTmdbTrailer(trailer['id'])
        played.append(trailer['title'])
        source=trailer['source']
        if source=='library':
            if trailer['trailer']=='': #no trailer search tmdb for one
                id=search_tmdb(trailer['title'],trailer['year'])
                if id!='':
                    trailer['trailer']=getTmdbTrailer(id)
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
            try:
                content = opener.open(trailer['trailer']).read()
                match = re.compile('<a class="movieLink" href="(.+?)"', re.DOTALL).findall(content)
                urlTemp = match[0]
                url = urlTemp[:urlTemp.find("?")].replace("480p", "h"+quality)+"|User-Agent=iTunes/9.1.1"
            except:
                url=''
        else:
            url = trailer['trailer'].encode('ascii', 'ignore')
        xbmc.log(str(trailer))
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
                self.getControl(30011).setLabel('[B]'+trailer["title"] + ' - ' + trailer['source']+ ' ' + trailer['type']+'[/B]')
            else:
                self.getControl(30011).setLabel('[B]'+trailer["title"] + ' - ' + trailer['source'] + ' ' + trailer['type'] + ' - ' + str(trailer["year"])+'[/B]')
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
        xbmc.log(str(action.getId()))
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
                xbmc.Player().pause()
                w.doModal()
                xbmc.Player().pause()
            if hide_title == 'false':
                self.getControl(30011).setVisible(True)
            else:
                self.getControl(30011).setVisible(False)
                              
class infoWindow(xbmcgui.WindowXMLDialog):
    def onInit(self):
        source = trailer['source']
        info=getInfo(trailer['title'],trailer['year'])
        self.getControl(30001).setImage(trailer["thumbnail"])
        self.getControl(30003).setImage(trailer["fanart"])
        title_font=getTitleFont()
        title_string =trailer["title"] + ' - ' + trailer['source'] + ' ' + trailer['type'] + ' - ' + str(trailer["year"])
        title=xbmcgui.ControlLabel(10,40,800,40,title_string,title_font)
        title=self.addControl(title)
        title=self.getControl(3001)
        title.setAnimations([('windowclose', 'effect=fade end=0 time=1000')])          
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
        self.getControl(30006).setLabel(movieActor)
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
    GROUP_TRAILERS = False
    if addon.getSetting('group_trailers')=='true':GROUP_TRAILERS = True
    GROUP_NUMBER = int(addon.getSetting('group_number'))
    GROUP_COUNT=GROUP_NUMBER
    GROUP_DELAY = (int(addon.getSetting('group_delay')) * 60) * 1000
    trailercount = 0
    while not exit_requested:
        if NUMBER_TRAILERS == 0:
            while not exit_requested and not xbmc.abortRequested:
                if GROUP_TRAILERS:
                    GROUP_COUNT=GROUP_COUNT - 1
                mytrailerWindow = trailerWindow('script-trailerwindow.xml', addon_path,'default',)
                mytrailerWindow.doModal()
                del mytrailerWindow
                if GROUP_TRAILERS and GROUP_COUNT==0:
                    GROUP_COUNT=GROUP_NUMBER
                    i = GROUP_DELAY
                    while i > 0 and not exit_requested and not xbmc.abortRequested:
                        xbmc.sleep(500)
                        i=i-500                      
        else:
            while NUMBER_TRAILERS > 0:
                if GROUP_TRAILERS:
                    GROUP_COUNT=GROUP_COUNT - 1
                mytrailerWindow = trailerWindow('script-trailerwindow.xml', addon_path,'default',)
                mytrailerWindow.doModal()
                del mytrailerWindow
                if GROUP_TRAILERS and GROUP_COUNT==0:
                    GROUP_COUNT=GROUP_NUMBER
                    i = GROUP_DELAY
                    while i > 0 and not exit_requested and not xbmc.abortRequested:
                        xbmc.sleep(500)
                        i=i-500  
                if exit_requested:
                    break
        if not exit_requested:
            if DO_CURTIANS == 'true':
                xbmc.Player().play(close_curtain_path)
                while xbmc.Player().isPlaying():
                    xbmc.sleep(250)
        exit_requested=True

def check_for_xsqueeze():
    KEYMAPDESTFILE = os.path.join(xbmc.translatePath('special://userdata/keymaps'), "xsqueeze.xml")
    if os.path.isfile(KEYMAPDESTFILE):
        return True
    else:
        return False

def get_mpaa(trailer):
    Rating='NR'
    if trailer["mpaa"].startswith('G'): Rating='G'
    if trailer["mpaa"] == ('G'): Rating='G'
    if trailer["mpaa"].startswith('Rated G'): Rating='G'
    if trailer["mpaa"].startswith('PG '): Rating='PG'
    if trailer["mpaa"] == ('PG'): Rating='PG'
    if trailer["mpaa"].startswith('Rated PG'): Rating='PG'
    if trailer["mpaa"].startswith('PG-13 '): Rating='PG-13'
    if trailer["mpaa"] == ('PG-13'): Rating='PG-13'
    if trailer["mpaa"].startswith('Rated PG-13'): Rating='PG-13'
    if trailer["mpaa"].startswith('R '): Rating='R'
    if trailer["mpaa"] == ('R'): Rating='R'
    if trailer["mpaa"].startswith('Rated R'): Rating='R'
    if trailer["mpaa"].startswith('NC17'): Rating='NC17'
    if trailer["mpaa"].startswith('Rated NC17'): 'NC17'
    return Rating

if not xbmc.Player().isPlaying() and not check_for_xsqueeze():
    DO_CURTIANS = addon.getSetting('do_animation')
    bs = blankWindow('script-BlankWindow.xml', addon_path,'default',)
    bs.show()
    if do_volume == 'true':
        muted = xbmc.getCondVisibility("Player.Muted")
        if not muted and volume == 0:
            xbmc.executebuiltin('xbmc.Mute()')
        else:
            xbmc.executebuiltin('XBMC.SetVolume('+str(volume)+')')
    if DO_CURTIANS == 'true':
        xbmc.Player().play(open_curtain_path)
        while xbmc.Player().isPlaying():
            xbmc.sleep(250)
    trailers = []
    filtergenre = False
    trailerNumber = 0
    library_trailers=[]
    iTunes_trailers=[]
    folder_trailers=[]
    tmdb_trailers=''
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
    dp=xbmcgui.DialogProgress()
    dp.create('Random Trailers','','','Loading Trailers')
    if do_library == 'true':
        for trailer in library_trailers:
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
            trailers.append(trailer)     
    if do_tmdb =='true':
        tmdbTrailers=getTmdbTrailers()
        for trailer in tmdbTrailers:
            trailers.append(trailer)    
    exit_requested=False
    if dp.iscanceled():exit_requested=True 
    dp.close()
    if len(trailers) > 0 and not exit_requested:
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
