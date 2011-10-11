import urllib2
import re
import os
import socket
import sys
import xbmc
import xbmcaddon
import xbmcvfs
import xbmcgui


### get addon info
__addon__ = xbmcaddon.Addon('script.extrafanartdownloader')
__addonid__ = __addon__.getAddonInfo('id')
__addonname__ = __addon__.getAddonInfo('name')
__addonversion__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString


### adjust default timeout to stop script hanging
timeout = 20
socket.setdefaulttimeout(timeout)


### logging function
def log(txt, severity=xbmc.LOGDEBUG):
    message = 'script.extrafanartdownloader: %s' % txt
    xbmc.log(msg=message, level=severity)


class Main:
    def __init__(self):
        if self.initialise():
            if not self.mediatype == '':
                if not self.medianame == '':
                    self.solo_mode(self.mediatype, self.medianame)
                else:
                    if self.mediatype == 'tvshow':
                        self.Media_listing('TVShows')
                        self.download_fanart(self.Medialist, self.tv_providers)
                    elif self.mediatype == 'movie':
                        self.Media_listing('Movies')
                        self.download_fanart(self.Medialist, self.movie_providers)
                    elif self.mediatype == 'artist':
                        log('Music fanart not yet implemented', xbmc.LOGNOTICE)
            else:
                if self.tvfanart == 'true':
                    self.Media_listing('TVShows')
                    self.download_fanart(self.Medialist, self.tv_providers)
                else:
                    log('TV fanart disabled, skipping', xbmc.LOGINFO)
                if self.moviefanart == 'true':
                    self.Media_listing('Movies')
                    self.download_fanart(self.Medialist, self.movie_providers)
                else:
                    log('Movie fanart disabled, skipping', xbmc.LOGINFO)
        else:
            log('Initialisation error, script aborting', xbmc.LOGERROR)
        self.cleanup()


    ### load settings and initialise needed directories
    def initialise(self):
        self.setup_providers()
        self.fanart_count = 0
        self.current_fanart = 0
        self.moviefanart = __addon__.getSetting("moviefanart")
        self.tvfanart = __addon__.getSetting("tvfanart")
        self.dialog = xbmcgui.DialogProgress()
        self.dialog.create(__addonname__, __language__(36003))
        addondir = xbmc.translatePath('special://profile/addon_data/%s' % __addonid__)
        self.tempdir = os.path.join(addondir, 'temp')
        self.mediatype = ''
        self.medianame = ''
        for item in sys.argv:
            match = re.search("mediatype=(.*)" , item)
            if match:
                self.mediatype = match.group(1)
                if self.mediatype == 'tvshow' or self.mediatype == 'movie' or self.mediatype == 'artist':
                    pass
                else:
                    log('Error: invalid mediatype, must be one of movie, tvshow or artist', xbmc.LOGERROR)
                    return False
            else:
                pass
            match = re.search("medianame=" , item)
            if match:
                self.medianame = item.replace( "medianame=" , "" )
            else:
                pass
        try:
            if not xbmcvfs.exists(self.tempdir):
                if not xbmcvfs.exists(addondir):
                    xbmcvfs.mkdir(addondir)
                    log('Created addon directory: %s' % addondir)
                xbmcvfs.mkdir(self.tempdir)
                log('Created temporary directory: %s' % self.tempdir)
        except:
            log('Could not create temporary directory: %s' % self.tempdir, xbmc.LOGERROR)
            return False
        return True


    ### clean up and
    def cleanup(self):
        if xbmcvfs.exists(self.tempdir):
            self.dialog.update(100, __language__(36004))
            log('Cleaning up')
            for x in os.listdir(self.tempdir):
                tempfile = os.path.join(self.tempdir, x)
                xbmcvfs.delete(tempfile)
                if xbmcvfs.exists(tempfile):
                    log('Error deleting temp file: %s' % tempfile, xbmc.LOGERROR)
            xbmcvfs.rmdir(self.tempdir)
            if xbmcvfs.exists(self.tempdir):
                log('Error deleting temp directory: %s' % self.tempdir, xbmc.LOGERROR)
            else:
                log('Deleted temp directory: %s' % self.tempdir, xbmc.LOGNOTICE)
        ### log results and notify user
        log('Finished: %s extrafanart downloaded' % self.fanart_count, xbmc.LOGNOTICE)
        summary_tmp = __language__(36009) + ': %s ' % self.fanart_count
        summary = summary_tmp + __language__(36010)
        self.dialog.close()
        xbmcgui.Dialog().ok(__addonname__, summary)


    ### download a given image to a given destination
    def downloadimage(self, fanarturl, fanartpath, temppath):
        try:
            url = fanarturl.replace(" ", "%20")
            temp_file = open(temppath, "wb")
            response = urllib2.urlopen(url)
            temp_file.write(response.read())
            temp_file.close()
            response.close()
        except(socket.timeout):
            log('Download timed out, skipping: %s' % fanarturl, xbmc.LOGWARNING)
            self.failcount = self.failcount + 1
        except:
            log('Download failed, skipping: %s' % fanarturl, xbmc.LOGWARNING)
            self.failcount = self.failcount + 1
        else:
            ### copy fanart from temp path to library
            xbmcvfs.copy(temppath, fanartpath)
            if not xbmcvfs.exists(fanartpath):
                log('Error copying temp file to library: %s -> %s' % (temppath, fanartpath), xbmc.LOGERROR)
            else:
                self.failcount = 0
                log('Downloaded successfully: %s' % fanarturl, xbmc.LOGNOTICE)
                self.fanart_count = self.fanart_count + 1

    ### solo mode
    def solo_mode(self, itemtype, itemname):
        if itemtype == 'movie':
            self.Media_listing('Movies')
        elif itemtype == 'tvshow':
            self.Media_listing('TVShows')
        else:
            log("Error: type must be one of 'movie' or 'tvshow', aborting", xbmc.LOGERROR)
            return False
        log('Retrieving fanart for: %s' % itemname)
        for currentitem in self.Medialist:
            if itemname == currentitem["name"]:
                if itemtype == 'movie':
                    self.Medialist = []
                    self.Medialist.append(currentitem)
                    self.download_fanart(self.Medialist, self.movie_providers)
                if itemtype == 'tvshow':
                    self.Medialist = []
                    self.Medialist.append(currentitem)
                    self.download_fanart(self.Medialist, self.tv_providers)
                break

    ### download media fanart
    def download_fanart(self, media_list, providers):
        self.processeditems = 0
        for currentmedia in media_list:
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
                self.media_path = os.path.split(currentmedia["path"])[0].rsplit(' , ', 1)[1]
            except:
                self.media_path = os.path.split(currentmedia["path"])[0]
            self.media_id = currentmedia["id"]
            self.media_name = currentmedia["name"]
            self.dialog.update(int(float(self.processeditems) / float(len(media_list)) * 100.0), __language__(36005), self.media_name, '')
            log('Processing media: %s' % self.media_name)
            log('ID: %s' % self.media_id)
            log('Path: %s' % self.media_path)
            extrafanart_dir = os.path.join(self.media_path, 'extrafanart')
            if not xbmcvfs.exists(extrafanart_dir):
                xbmcvfs.mkdir(extrafanart_dir)
                if xbmcvfs.exists(extrafanart_dir):
                    log('Created directory: %s' % extrafanart_dir, xbmc.LOGINFO)
                else:
                    log('Error creating directory, skipping: %s' % extrafanart_dir, xbmc.LOGERROR)
                    break
            if self.media_id == '':
                log('%s: No ID found, skipping' % self.media_name, xbmc.LOGNOTICE)
            else:
                for provider in providers:
                    try:
                        backdrops = provider.get_image_list(self.media_id)
                    except:
                        log('Error getting data from %s, skipping' % provider.name, xbmc.LOGERROR)
                    else:
                        self.current_fanart = 0
                        for fanarturl in backdrops:
                            ### check if script has been cancelled by user
                            if self.dialog.iscanceled():
                                self.dialog.close()
                                break
                            fanartfile = provider.get_filename(fanarturl)
                            temppath = os.path.join(self.tempdir, fanartfile)
                            fanartpath = os.path.join(extrafanart_dir, fanartfile)
                            self.current_fanart = self.current_fanart + 1
                            if not xbmcvfs.exists(fanartpath):
                                self.downloadimage(fanarturl, fanartpath, temppath)
                                self.dialog.update(int(float(self.current_fanart) / float(len(backdrops)) * 100.0), __language__(36006), self.media_name, fanarturl)
                            else:
                                self.dialog.update(int(float(self.current_fanart) / float(len(backdrops)) * 100.0), __language__(36006), self.media_name, "")
            self.processeditems = self.processeditems + 1


    ### get list of all tvshows and movies with their imdbnumber from library
    ### copied from script.logo-downloader, thanks to it's authors
    def Media_listing(self, media_type):
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.Get%s", "params": {"properties": ["file", "imdbnumber"], "sort": { "method": "label" } }, "id": 1}' % media_type)
        json_response = re.compile( "{(.*?)}", re.DOTALL ).findall(json_query)
        self.Medialist = []
        for mediaitem in json_response:
            findmedianame = re.search( '"label":"(.*?)","', mediaitem )
            if findmedianame:
                medianame = ( findmedianame.group(1) )
                findpath = re.search( '"file":"(.*?)","', mediaitem )
                if findpath:
                    path = (findpath.group(1))
                    findimdbnumber = re.search( '"imdbnumber":"(.*?)","', mediaitem )
                    if findimdbnumber:
                        imdbnumber = (findimdbnumber.group(1))
                        Media = {}
                        Media["name"] = medianame
                        Media["id"] = imdbnumber
                        Media["path"] = path
                        self.Medialist.append(Media)

    def setup_providers(self):
        self.movie_providers = []
        self.tv_providers = []
        self.music_providers = []

        """
        Setup provider for TheMovieDB.org
        """
        tmdb = Provider()
        tmdb.name = 'TMDB'
        tmdb.api_key = '4be68d7eab1fbd1b6fd8a3b80a65a95e'
        tmdb.url = "http://api.themoviedb.org/2.1/Movie.imdbLookup/en/xml/%s/%s"
        tmdb.re_pattern = '<image type="backdrop" url="(.*?)" size="original"'
        tmdb.get_filename = lambda url: url.split('backdrops', 1)[1].replace('/', '-').lstrip('-')

        self.movie_providers.append(tmdb)

        """
        Setup provider for TheTVDB.com
        """
        tvdb = Provider()
        tvdb.name = 'TVDB'
        tvdb.api_key = '1A41A145E2DA0053'
        tvdb.url = 'http://www.thetvdb.com/api/%s/series/%s/banners.xml'
        tvdb.url_prefix = 'http://www.thetvdb.com/banners/'
        tvdb.re_pattern = '<BannerPath>(?P<url>.*?)</BannerPath>\s+<BannerType>fanart</BannerType>'

        self.tv_providers.append(tvdb)

        """
        Setup provider for fanart.tv - TV API
        """
        ftvt = Provider()
        ftvt.name = 'fanart.tv - TV API'
        ftvt.url = 'http://fanart.tv/api/fanart.php?id=%s&type=tvthumb'
        ftvt.re_pattern = ''

        #self.tv_providers.append(ftvt)

        """
        Setup provider for fanart.tv - Music API
        """
        ftvm = Provider()
        ftvm.name = 'fanart.tv - Music API'
        ftvm.url = 'http://fanart.tv/api/music.php?id=%s&type=background'
        ftvm.re_pattern = '<background>(.*?)</background>'

        #self.music_providers.append(ftvm)

"""
Provider Class

Creates general structure for all fanart providers.  This will allow us to
very easily add multiple providers for the same media type.
"""
class Provider:
    def __init__(self):
        self.name = ''
        self.api_key = ''
        self.url = ''
        self.re_pattern = ''
        self.url_prefix = ''
        self.get_filename = lambda url: url.rsplit('/', 1)[1]

    def _get_xml(self, url):
        client = urllib2.urlopen(url)
        data = client.read()
        client.close()
        return data

    def get_image_list(self, media_id):
        log(self.url % (self.api_key, media_id))
        image_list = []
        for i in re.finditer(self.re_pattern, self._get_xml(self.url % (self.api_key, media_id))):
            image_list.append(self.url_prefix + i.group(1))
        return image_list



if ( __name__ == "__main__" ):
    log('script version %s started' % __addonversion__)
    Main()
    log('script stopped')
