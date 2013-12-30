# -*- coding: utf-8 -*-
import xbmcplugin
__useragent__    ="Mozilla/5.0 (Windows; U; Windows NT 5.1; fr; rv:1.9.0.1) Gecko/2008070208 Firefox/3.6"
import urllib
import os
from traceback import print_exc
import re
import unicodedata
import xbmc  
import xbmcaddon
import xbmcgui
import xbmcvfs
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

__addon__     = xbmcaddon.Addon(id='script.tvtunes')
__addonid__   = __addon__.getAddonInfo('id')
__language__  = __addon__.getLocalizedString

def log(txt):
    if isinstance (txt,str):
        txt = txt.decode("utf-8")
    message = u'%s: [Scraper] %s' % (__addonid__, txt)
    xbmc.log(msg=message.encode("utf-8"), level=xbmc.LOGDEBUG)

try:
    # parse sys.argv for params
    params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
except:
    # no params passed
    params = {} 

def _unicode( text, encoding='utf-8' ):
    try: text = unicode( text, encoding )
    except: pass
    return text

def normalize_string( text ):
    try:
        text = text.replace(":","")
        text = text.replace("/","-")
        text = text.replace("\\","-")
        text = unicodedata.normalize( 'NFKD', unicode( text, 'utf-8' ) ).encode( 'ascii', 'ignore' )
    except:
        pass
    return text

def get_html_source( url , save=False):
    """ fetch the html source """
    class AppURLopener(urllib.FancyURLopener):
        version = __useragent__
    urllib._urlopener = AppURLopener()

    try:
        if os.path.isfile( url ): sock = open( url, "r" )
        else:
            urllib.urlcleanup()
            sock = urllib.urlopen( url )

        htmlsource = sock.read()
        if save: file( os.path.join( CACHE_PATH , save ) , "w" ).write( htmlsource )
        sock.close()
        return htmlsource
    except:
        print_exc()
        log( "### ERROR opening page %s" % url )
        xbmcgui.Dialog().ok(__language__(32101) , __language__(32102))
        return False

###############################################################
# Class to make it easier to see which screen is being checked
###############################################################
class WindowShowing():
    xbmcMajorVersion = 0

    @staticmethod
    def getXbmcMajorVersion():
        if WindowShowing.xbmcMajorVersion == 0:
            xbmcVer = xbmc.getInfoLabel('system.buildversion')
            log("WindowShowing: XBMC Version = " + xbmcVer)
            WindowShowing.xbmcMajorVersion = 12
            try:
                # Get just the major version number
                WindowShowing.xbmcMajorVersion = int(xbmcVer.split(".", 1)[0])
            except:
                # Default to frodo as the default version if we fail to find it
                log("WindowShowing: Failed to get XBMC version")
            log("WindowShowing: XBMC Version %d (%s)" % (WindowShowing.xbmcMajorVersion, xbmcVer))
        return WindowShowing.xbmcMajorVersion

    @staticmethod
    def isTv():
        if xbmc.getCondVisibility("Container.Content(tvshows)"):
            return True
        if xbmc.getCondVisibility("Container.Content(Seasons)"):
            return True
        if xbmc.getCondVisibility("Container.Content(Episodes)"):
            return True

        folderPathId = "videodb://2/2/"
        # The ID for the TV Show Title changed in Gotham
        if WindowShowing.getXbmcMajorVersion() > 12:
            folderPathId = "videodb://tvshows/titles/"
        if xbmc.getInfoLabel( "container.folderpath" ) == folderPathId:
            return True # TvShowTitles
        
        return False


class TvTunes:
    def __init__(self):
        if not xbmcvfs.exists( xbmc.translatePath( 'special://profile/addon_data/%s' % __addonid__ ).decode("utf-8") ):
            xbmcvfs.mkdir( xbmc.translatePath( 'special://profile/addon_data/%s' % __addonid__ ).decode("utf-8") )
        if not xbmcvfs.exists( xbmc.translatePath( 'special://profile/addon_data/%s/temp' % __addonid__ ).decode("utf-8") ):
            xbmcvfs.mkdir( xbmc.translatePath( 'special://profile/addon_data/%s/temp' % __addonid__ ).decode("utf-8") )
        self.search_url = "http://www.televisiontunes.com/search.php?searWords=%s&Send=Search"
        self.download_url = "http://www.televisiontunes.com/download.php?f=%s"
        self.enable_custom_path = __addon__.getSetting("custom_path_enable")
        self.exact_match = __addon__.getSetting('exact_match')
        self.support_multi_themes = __addon__.getSetting('multiThemeDownload')
        self.searchMovieDownload =  __addon__.getSetting('searchMovieDownload')
        if self.enable_custom_path == "true":
            self.custom_path = __addon__.getSetting("custom_path").decode("utf-8")
            self.isThemeDirEnabled = "false"
        else:
            # Load the information about storing themes in sub-directories
            # Only use the Theme dir if custom path is not used
            self.isThemeDirEnabled = __addon__.getSetting("searchSubDir")
            if self.isThemeDirEnabled == "true":
                self.themeDir = __addon__.getSetting("subDirName")

        self.TVlist = self.listing()
        self.DIALOG_PROGRESS = xbmcgui.DialogProgress()
        # Only display the erase dialog if we would overwrite
        if self.support_multi_themes == 'false':
            self.ERASE = xbmcgui.Dialog().yesno(__language__(32103),__language__(32104))
        else:
            self.ERASE = True
        self.DIALOG_PROGRESS.create( __language__(32105) , __language__(32106) )
        if params.get("mode", "false" ) == "solo":
            self.runSolo()
        else:
            self.scan()
        self.DIALOG_PROGRESS.close()
        
    # Handles the case where there is just a single theme to look for
    # and it has been invoked from the given video location
    def runSolo(self):
        # Used to pass the name and path via the command line
        # This caused problems with non ascii characters, so now
        # we just look at the screen details
        # The solo option is only available from the info screen
        # Looking at the TV Show information page
        if WindowShowing.isTv():
            videoPath = xbmc.getInfoLabel( "ListItem.Path" )
            videoName = xbmc.getInfoLabel( "ListItem.TVShowTitle" )
            if videoPath == None or videoPath == "":
                videoPath = xbmc.getInfoLabel( "ListItem.FilenameAndPath" )
            log("runSolo: TV Show detected %s" % videoPath)
        else:
            videoPath = xbmc.getInfoLabel( "ListItem.FilenameAndPath" )
            videoName = xbmc.getInfoLabel( "ListItem.Title" )
            if videoPath == None or videoPath == "":
                videoPath = xbmc.getInfoLabel( "ListItem.Path" )
            log("runSolo: Movie detected %s" % videoPath)
        
        if self.enable_custom_path == "true":
            tvshow = videoName.replace(":","")
            tvshow = normalize_string( tvshow )
            self.scan(normalize_string( videoName ),os.path.join(self.custom_path, tvshow).decode("utf-8"))
        else:
            log("runSolo: Solo dir = %s" % videoPath)
            # Need to clean the path if we are going to store the file there
            # Handle stacked files that have a custom file name format
            if videoPath.startswith("stack://"):
                videoPath = videoPath.replace("stack://", "").split(" , ", 1)[0]
            # Need to remove the filename from the end  as we just want the directory
            # if not os.path.isdir(videoPath):
            fileExt = os.path.splitext( videoPath )[1]
            # If this is a file, then get it's parent directory
            if fileExt != None and fileExt != "":
                videoPath = os.path.dirname( videoPath )

            self.scan(normalize_string( videoName ),videoPath.decode("utf-8"))

    # Checks if a theme exists in a directory
    def _doesThemeExist(self, directory):
        log("## Checking directory: %s" % directory)
        # Check for custom theme directory
        if self.isThemeDirEnabled == "true":
            directory = os.path.join(directory, self.themeDir)

        # check if the directory exists before searching
        if xbmcvfs.exists(directory):
            # Generate the regex
            fileTypes = "mp3" # mp3 is the default that is always supported
            if(__addon__.getSetting("wma") == 'true'):
                fileTypes = fileTypes + "|wma"
            if(__addon__.getSetting("flac") == 'true'):
                fileTypes = fileTypes + "|flac"
            if(__addon__.getSetting("m4a") == 'true'):
                fileTypes = fileTypes + "|m4a"
            if(__addon__.getSetting("wav") == 'true'):
                fileTypes = fileTypes + "|wav"
            themeFileRegEx = '(theme[ _A-Za-z0-9.-]*.(' + fileTypes + ')$)'

            dirs, files = xbmcvfs.listdir( directory )
            for aFile in files:
                m = re.search(themeFileRegEx, aFile, re.IGNORECASE)
                if m:
                    log("### Found match: " + aFile)
                    return True
        return False


    def scan(self , cur_name=False , cur_path=False):
        count = 0
        if cur_name and cur_path: 
            log( "### solo mode" )
            log("####################### %s" % cur_name )
            log("####################### %s" % cur_path )
            self.TVlist = [[cur_name,cur_path,cur_name]]
        total = len(self.TVlist)
        for show in self.TVlist:
            count = count + 1
            if (not self.ERASE and self._doesThemeExist(show[1])) and (self.support_multi_themes == 'false'):
                log( "### %s already exists, ERASE is set to %s" % ( os.path.join(show[1],"theme.*"), [False,True][self.ERASE] ) )
            else:
                self.DIALOG_PROGRESS.update( (count*100)/total , __language__(32107) + ' ' + show[0] , ' ')
                if self.DIALOG_PROGRESS.iscanceled():
                    self.DIALOG_PROGRESS.close()
                    xbmcgui.Dialog().ok(__language__(32108),__language__(32109))
                    break
                theme_list = self.search_theme_list( show[0])
                #log( theme_list )
                if (len(theme_list) == 1) and (self.exact_match == 'true'): 
                    theme_url = self.download_url % theme_list[0]["url"].replace("http://www.televisiontunes.com/", "").replace(".html" , "")
                else:
                    theme_url = self.get_user_choice( theme_list , show[2] )
                if theme_url:
                    self.download(theme_url , show[1])
                else:
                    # Give the user an option to stop searching the remaining themes
                    # as they did not select one for this show, but only prompt
                    # if there are more to be processed
                    if count < total:
                        if not xbmcgui.Dialog().yesno(__language__(32105), __language__(32119)):
                            break

    def download(self , theme_url , path):
        log( "### download :" + theme_url )

        # Check for custom theme directory
        if self.isThemeDirEnabled == "true":
            path = os.path.join(path, self.themeDir)

        theme_file = self.getNextThemeFileName(path)
        tmpdestination = xbmc.translatePath( 'special://profile/addon_data/%s/temp/%s' % ( __addonid__ , theme_file ) ).decode("utf-8")
        destination = os.path.join( path , theme_file )
        try:
            def _report_hook( count, blocksize, totalsize ):
                percent = int( float( count * blocksize * 100 ) / totalsize )
                strProgressBar = str( percent )
                self.DIALOG_PROGRESS.update( percent , __language__(32110) + ' ' + theme_url , __language__(32111) + ' ' + destination )
            if not xbmcvfs.exists(path):
                try:
                    xbmcvfs.mkdir(path)
                except:
                    log( "problem with path: %s" % destination )
            fp , h = urllib.urlretrieve( theme_url , tmpdestination , _report_hook )
            log( h )
            copy = xbmcvfs.copy(tmpdestination, destination)
            if copy:
                log( "### copy successful" )
            else:
                log( "### copy failed" )
            xbmcvfs.delete(tmpdestination)
            return True
        except :
            log( "### Theme download Failed !!!" )
            print_exc()
            return False 

    def get_user_choice(self , theme_list , showname):
        theme_url = False
        searchname = showname
        searchdic = { "name" : __language__(32118)}
        theme_list.insert(0 , searchdic)
        while theme_url == False:
            select = xbmcgui.Dialog().select(__language__(32112) + ' ' + searchname, [ theme["name"] for theme in theme_list ])
            if select == -1: 
                log( "### Canceled by user" )
                #xbmcgui.Dialog().ok("Canceled" , "Download canceled by user" )
                return False
            else:
                if theme_list[select]["name"] == __language__(32118):
                    kb = xbmc.Keyboard(showname, __language__(32113), False)
                    kb.doModal()
                    result = kb.getText()
                    theme_list = self.search_theme_list(result)
                    searchname = result
                    theme_list.insert(0 , searchdic)
                else:
                    theme_url = self.download_url % theme_list[select]["url"].replace("http://www.televisiontunes.com/", "").replace(".html" , "")
                    log( "### %s" % theme_url )
                    listitem = xbmcgui.ListItem(theme_list[select]["name"])
                    listitem.setInfo('music', {'Title': theme_list[select]["name"]})
                    # Check if a tune is already playing
                    if xbmc.Player().isPlayingAudio():
                        xbmc.Player().stop()
                    while xbmc.Player().isPlayingAudio():
                        xbmc.sleep(5)
                    
                    xbmcgui.Window( 10025 ).setProperty( "TvTunesIsAlive", "true" )
                    xbmc.Player().play(theme_url, listitem)
                    ok = xbmcgui.Dialog().yesno(__language__(32103),__language__(32114))
                    if not ok: theme_url = False
                    xbmc.executebuiltin('PlayerControl(Stop)')
                    xbmcgui.Window( 10025 ).clearProperty('TvTunesIsAlive')

        return theme_url

    def search_theme_list(self , showname):
        log( "### Search for %s" % showname )
        theme_list = []
        next = True
        # Prevent the erro if there are invalid characters by encoding as utf-8
        url = self.search_url % urllib.quote_plus(showname.encode("utf-8"))
        urlpage = ""
        while next == True:
            ### on recup le result de la recherche
            data = get_html_source( url + urlpage )
            log( "### Search url: %s" % ( url + urlpage ) )
            ###on parse la recherche pour renvoyer une liste de dico
            match = re.search(r"1\.&nbsp;(.*)<br>", data)
            if match: data2 = re.findall('<a href="(.*?)">(.*?)</a>', match.group(1))
            else: 
                log( "no theme found for %s" % showname )
                data2 = ""
            for i in data2:
                theme = {}
                theme["url"] = i[0] or ""
                theme["name"] = i[1] or ""
                # in case of an exact match (when enabled) only return this theme
                if self.exact_match == 'true' and theme["name"] == showname:
                    theme_list = []
                    theme_list.append(theme)
                    return theme_list
                else:
                    theme_list.append(theme)
            match = re.search(r'&search=Search(&page=\d)"><b>Next</b>', data)
            if match:
            	urlpage = match.group(1)
            else:
            	next = False
            log( "### next page: %s" % next )
        return theme_list

    def listing(self):
        # on recup la liste des series en biblio
        # json statement for tv shows
        json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"properties": ["title", "file"], "sort": { "method": "title" } }, "id": 1}')
        json_query = unicode(json_query, 'utf-8', errors='ignore')
        json_response = simplejson.loads(json_query)
        log( json_response )
        TVlist = []
        if json_response['result'].has_key('tvshows'):
            for item in json_response['result']['tvshows']:
                orgname = item['title']
                tvshow = item['title'].replace(":","")
                tvshow = normalize_string( tvshow )
                if self.enable_custom_path == "true":
                    path = os.path.join(self.custom_path, tvshow).decode("utf-8")
                else:
                    # The file is actually the path for a TV Show
                    path = item['file']
                TVlist.append( ( tvshow , path, orgname ) )
                
        if self.searchMovieDownload == 'true':
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["title", "file"], "sort": { "method": "title" } }, "id": 1}')
            json_query = unicode(json_query, 'utf-8', errors='ignore')
            json_response = simplejson.loads(json_query)
            log( json_response )
            if (self.searchMovieDownload == 'true') and json_response['result'].has_key('movies'):
                for item in json_response['result']['movies']:
                    orgname = item['title']
                    movie = item['title'].replace(":","")
                    movie = normalize_string( movie )
                    if self.enable_custom_path == "true":
                        path = os.path.join(self.custom_path, movie).decode("utf-8")
                    else:
                        path = item['file']
                        # Handle stacked files that have a custom file name format
                        if path.startswith("stack://"):
                            path = path.replace("stack://", "").split(" , ", 1)[0]
                        # Need to remove the filename from the end  as we just want the directory
                        path = os.path.dirname( path )
                    TVlist.append( ( movie , path, orgname ) )
        
        return TVlist   

    # Calculates the next filename to use when downloading multiple themes
    def getNextThemeFileName(self, path):
        themeFileName = "theme.mp3"
        if (self.support_multi_themes == 'true') and xbmcvfs.exists(os.path.join(path,"theme.mp3")):
            idVal = 1
            while xbmcvfs.exists(os.path.join(path,"theme" + str(idVal) + ".mp3")):
                idVal = idVal + 1
            themeFileName = "theme" + str(idVal) + ".mp3"
        log("Next Theme Filename = " + themeFileName)
        return themeFileName


if ( __name__ == "__main__" ):
    TvTunes()
    xbmcgui.Dialog().ok(__language__(32105),__language__(32116) , __language__(32117))
