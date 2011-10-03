import urllib, re, os, socket
import xbmc, xbmcaddon, xbmcvfs, xbmcgui
from elementtree import ElementTree


### get addon info
__addon__ = xbmcaddon.Addon()
__addonid__ = __addon__.getAddonInfo('id')
__addonname__ = __addon__.getAddonInfo('name')
__addonversion__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString


### adjust default timeout to stop script hanging
timeout = 20
socket.setdefaulttimeout(timeout)


### logging function
def log(txt):
    message = 'script.extrafanartdownloader: %s' % txt
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)


class getBackdrops(object):

    def __init__(self):
        self.tvdbbaseurl = 'http://www.thetvdb.com/banners/'
        self.tvdbkey = '1A41A145E2DA0053'
        self.tmdbkey = '4be68d7eab1fbd1b6fd8a3b80a65a95e'

    def tvdb(self, showid):
        bannerlist = []
        url = 'http://www.thetvdb.com/api/%s/series/%s/banners.xml' % (self.tvdbkey, showid)
        log('Fetching: %s' % url)
        tree = self.socket(url)
        for banner in tree.findall('Banner'):
            if banner.find('BannerType').text == 'fanart':
                fanarturl = self.tvdbbaseurl + banner.find('BannerPath').text
                bannerlist.append(fanarturl)
        log('Fanart list: %s' % str(bannerlist))
        return bannerlist

    def tmdb(self, tmdbid):
        bannerlist = []
        url = 'http://api.themoviedb.org/2.1/Movie.getImages/en/xml/%s/%s' % (self.tmdbkey, tmdbid)
        log('Fetching: %s' % url)
        tree = self.socket(url)
        for backdrop in tree.getiterator('backdrop'):
            for image in backdrop.getiterator('image'):
                if image.attrib['size'] == 'original':
                    fanarturl = image.attrib['url']
                    bannerlist.append(fanarturl)
        log('Fanart list: %s' % str(bannerlist))
        return bannerlist

    def socket(self, url):
        client = urllib.urlopen(url)
        data = client.read()
        client.close()
        return ElementTree.fromstring(data)


class Main:


    def __init__(self):
        self.initialise()
        if self.tvfanart == 'true':
            self.download_tvfanart()
        else:
            log('TV fanart disabled, skipping')
        if self.moviefanart == 'true':
            self.download_moviefanart()
        else:
            log('Movie fanart disabled, skipping')
        self.cleanup()


    ### load settings and initialise needed directories
    def initialise(self):
        self.getbackdrops = getBackdrops()
        self.fanart_count = 0
        self.moviefanart = __addon__.getSetting("moviefanart")
        self.tvfanart = __addon__.getSetting("tvfanart")
        self.dialog = xbmcgui.DialogProgress()
        self.dialog.create(__addonname__, __language__(36003))
        addondir = xbmc.translatePath('special://profile/addon_data/%s' % __addonid__)
        self.tempdir = os.path.join(addondir, 'temp')
        try:
            if not xbmcvfs.exists(self.tempdir):
                if not xbmcvfs.exists(addondir):
                    xbmcvfs.mkdir(addondir)
                    log('Created addon directory: %s' % addondir)
                xbmcvfs.mkdir(self.tempdir)
                log('Created temporary directory: %s' % self.tempdir)
        except:
            log('Could not create temporary directory: %s' % self.tempdir)


    ### clean up and 
    def cleanup(self):
        if xbmcvfs.exists(self.tempdir):
            self.dialog.update(100, __language__(36004))
            log('Cleaning up')
            for x in os.listdir(self.tempdir):
                tempfile = os.path.join(self.tempdir, x)
                xbmcvfs.delete(tempfile)
                if xbmcvfs.exists(tempfile):
                    log('Error deleting temp file: %s' % tempfile)
            xbmcvfs.rmdir(self.tempdir)
            if xbmcvfs.exists(self.tempdir):
                log('Error deleting temp directory: %s' % self.tempdir)
            else:
                log('Deleted temp directory: %s' % self.tempdir)
        ### log results and notify user
        log('Finished: %s extrafanart downloaded' % self.fanart_count)
        summary_tmp = __language__(36009) + ': %s ' % self.fanart_count
        summary = summary_tmp + __language__(36010)
        self.dialog.close()
        xbmcgui.Dialog().ok(__addonname__, summary)


    ### download a given image to a given destination
    def downloadimage(self, fanarturl, fanartpath, temppath):
        try:
            urllib.urlretrieve(fanarturl, temppath)
        except(socket.timeout):
            log('Download timed out, skipping: %s' % fanarturl)
            self.failcount = self.failcount + 1
        except:
            log('Download failed, skipping: %s' % fanarturl)
            self.failcount = self.failcount + 1
        else:
            ### copy fanart from temp path to library
            xbmcvfs.copy(temppath, fanartpath)
            if not xbmcvfs.exists(fanartpath):
                log('Error copying temp file to library: %s -> %s' % (temppath, fanartpath))
            else:
                self.failcount = 0
                log('Downloaded successfully: %s' % fanarturl)
                self.fanart_count = self.fanart_count + 1


    ### download all tv show fanart
    def download_tvfanart(self):
        self.processeditems = 0
        self.TV_listing()
        for currentshow in self.TVlist:
            ### check if XBMC is shutting down
            if xbmc.abortRequested == True:
                log('XBMC shutting down, aborting')
                break
            ### check if script has been cancelled by user
            if self.dialog.iscanceled():
                self.dialog.close()
                break
            self.failcount = 0
            self.show_path = currentshow["path"]
            self.tvdbid = currentshow["id"]
            self.show_name = currentshow["name"]
            self.dialog.update(int(float(self.processeditems) / float(len(self.TVlist)) * 100), __language__(36005), self.show_name, '')
            log('Processing show: %s' % self.show_name)
            log('ID: %s' % self.tvdbid)
            log('Path: %s' % self.show_path)
            extrafanart_dir = os.path.join(self.show_path, 'extrafanart')
            if not xbmcvfs.exists(extrafanart_dir):
                xbmcvfs.mkdir(extrafanart_dir)
                log('Created directory: %s' % extrafanart_dir)
            try:
                backdrops = self.getbackdrops.tvdb(self.tvdbid)
            except:
                log('Error getting data from TVDB, skipping')
            else:
                for fanarturl in backdrops:
                    fanartfile = fanarturl.rsplit('/', 1)[1]
                    temppath = os.path.join(self.tempdir, fanartfile)
                    fanartpath = os.path.join(extrafanart_dir, fanartfile)
                    if not xbmcvfs.exists(fanartpath):
                        self.dialog.update(int(float(self.processeditems) / float(len(backdrops)) * 100), __language__(36006), self.show_name, fanarturl)
                        self.downloadimage(fanarturl, fanartpath, temppath)
            self.processeditems = self.processeditems + 1


    ### get list of all tvshows and their imdbnumber from library
    ### copied from script.logo-downloader, thanks to it's authors
    def TV_listing(self):
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["file", "imdbnumber"], "sort": { "method": "label" } }, "id": 1}')
        json_response = re.compile( "{(.*?)}", re.DOTALL ).findall(json_query)
        self.TVlist = []
        for tvshowitem in json_response:
            findtvshowname = re.search( '"label":"(.*?)","', tvshowitem )
            if findtvshowname:
                tvshowname = ( findtvshowname.group(1) )
                findpath = re.search( '"file":"(.*?)","', tvshowitem )
                if findpath:
                    path = (findpath.group(1))
                    findimdbnumber = re.search( '"imdbnumber":"(.*?)","', tvshowitem )
                    if findimdbnumber:
                        imdbnumber = (findimdbnumber.group(1))
                        TVshow = {}
                        TVshow["name"] = tvshowname
                        TVshow["id"] = imdbnumber
                        TVshow["path"] = path
                        self.TVlist.append(TVshow)


    def download_moviefanart(self):
        self.processeditems = 0
        self.Movie_listing()
        for currentmovie in self.Movielist:
            ### check if XBMC is shutting down
            if xbmc.abortRequested == True:
                log('XBMC shutting down, aborting')
                break
            ### check if script has been cancelled by user
            if self.dialog.iscanceled():
                self.dialog.close()
                break
            self.failcount = 0
            try:
                self.movie_path = os.path.split(currentmovie["path"])[0].rsplit(' , ', 1)[1]
            except:
                self.movie_path = os.path.split(currentmovie["path"])[0]
            self.tmdbid = currentmovie["id"]
            self.movie_name = currentmovie["name"]
            self.dialog.update(int(float(self.processeditems) / float(len(self.Movielist)) * 100), __language__(36007), self.movie_name, '')
            log('Processing movie: %s' % self.movie_name)
            log('ID: %s' % self.tmdbid)
            log('Path: %s' % self.movie_path)
            extrafanart_dir = os.path.join(self.movie_path, 'extrafanart')
            if not xbmcvfs.exists(extrafanart_dir):
                xbmcvfs.mkdir(extrafanart_dir)
                log('Created directory: %s' % extrafanart_dir)
            if self.tmdbid == '':
                log('No TMDB ID found, skipping')
            else:
                try:
                    backdrops = self.getbackdrops.tmdb(self.tmdbid)
                except:
                    log('Error getting data from TMDB, skipping')
                else:
                    for fanarturl in backdrops:
                        fanartfilename = fanarturl.split('backdrops', 1)[1].replace('/', '-').lstrip('-')
                        temppath = os.path.join(self.tempdir, fanartfilename)
                        fanartpath = os.path.join(extrafanart_dir, fanartfilename)
                        if not xbmcvfs.exists(fanartpath):
                            self.dialog.update(int(float(self.processeditems) / float(len(backdrops)) * 100), __language__(36008), self.movie_name, fanarturl)
                            self.downloadimage(fanarturl, fanartpath, temppath)
            self.processeditems = self.processeditems + 1


    ### get list of all movies and their imdbnumber from library
    def Movie_listing(self):
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["file", "imdbnumber"], "sort": { "method": "label" } }, "id": 1}')
        json_response = re.compile( "{(.*?)}", re.DOTALL ).findall(json_query)
        self.Movielist = []
        for movieitem in json_response:
            findmoviename = re.search( '"label":"(.*?)","', movieitem )
            if findmoviename:
                moviename = ( findmoviename.group(1) )
                findpath = re.search( '"file":"(.*?)","', movieitem )
                if findpath:
                    path = (findpath.group(1))
                    findimdbnumber = re.search( '"imdbnumber":"(.*?)","', movieitem )
                    if findimdbnumber:
                        imdbnumber = (findimdbnumber.group(1))
                        Movie = {}
                        Movie["name"] = moviename
                        Movie["id"] = imdbnumber
                        Movie["path"] = path
                        self.Movielist.append(Movie)



if ( __name__ == "__main__" ):
    log('script version %s started' % __addonversion__)
    Main()
    log('script stopped')
