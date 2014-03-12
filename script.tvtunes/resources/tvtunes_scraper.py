# -*- coding: utf-8 -*-
import urllib
import os
from traceback import print_exc
import re
import unicodedata
import xbmc  
import xbmcaddon
import xbmcgui
import xbmcvfs

# Following includes required for GoEar support
import urllib2
from BeautifulSoup import BeautifulSoup
import HTMLParser

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


def normalize_string( text ):
    try:
        text = text.replace(":","")
        text = text.replace("/","-")
        text = text.replace("\\","-")
        text = unicodedata.normalize( 'NFKD', unicode( text, 'utf-8' ) ).encode( 'ascii', 'ignore' )
    except:
        pass
    return text

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
    def isMovieInformation():
        return xbmc.getCondVisibility("Window.IsVisible(movieinformation)")

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

########################################
# Class to read all the settings from
########################################
class Settings():
    @staticmethod
    def isCustomPathEnabled():
        return __addon__.getSetting("custom_path_enable") == 'true'

    @staticmethod
    def getCustomPath():
        return __addon__.getSetting("custom_path").decode("utf-8")

    @staticmethod
    def isThemeDirEnabled():
        # Theme sub directory only supported when not using a custom path
        if Settings.isCustomPathEnabled():
            return False
        return __addon__.getSetting("searchSubDir") == 'true'

    @staticmethod
    def getThemeDirectory():
        # Load the information about storing themes in sub-directories
        # Only use the Theme dir if custom path is not used
        return __addon__.getSetting("subDirName")

    @staticmethod
    def isExactMatchEnabled():
        return __addon__.getSetting("exact_match") == 'true'
    
    @staticmethod
    def isMultiThemesSupported():
        return __addon__.getSetting("multiThemeDownload") == 'true'

    @staticmethod
    def isMovieDownloadEnabled():
        return __addon__.getSetting("searchMovieDownload") == 'true'

    @staticmethod
    def isGoEarSearch():
        return __addon__.getSetting("themeSearchSource") == 'goear.com'


#################################
# Core TvTunes Scraper class
#################################
class TvTunesScraper:
    def __init__(self):
        # Set up the addon directories if they do not already exist
        if not xbmcvfs.exists( xbmc.translatePath( 'special://profile/addon_data/%s' % __addonid__ ).decode("utf-8") ):
            xbmcvfs.mkdir( xbmc.translatePath( 'special://profile/addon_data/%s' % __addonid__ ).decode("utf-8") )
        if not xbmcvfs.exists( xbmc.translatePath( 'special://profile/addon_data/%s/temp' % __addonid__ ).decode("utf-8") ):
            xbmcvfs.mkdir( xbmc.translatePath( 'special://profile/addon_data/%s/temp' % __addonid__ ).decode("utf-8") )
        
        self.DIALOG_PROGRESS = xbmcgui.DialogProgress()
        # Only display the erase dialog if we would overwrite
        if not Settings.isMultiThemesSupported():
            self.ERASE = xbmcgui.Dialog().yesno(__language__(32103),__language__(32104))
        else:
            self.ERASE = True
        self.DIALOG_PROGRESS.create( __language__(32105) , __language__(32106) )

        # If running solo need to work out which Video is currently selected
        if params.get("mode", "false" ) == "solo":
            self.Videolist = self.getSoloVideo()
        else:
            # If not running in solo mode, look for everything
            self.Videolist = self.getAllVideos()

        self.isGoEarSearch = Settings.isGoEarSearch()

        # Now we have the list of programs to search for, perform the scan
        self.scan()
        self.DIALOG_PROGRESS.close()
        
    # Handles the case where there is just a single theme to look for
    # and it has been invoked from the given video location
    def getSoloVideo(self):
        log("getSoloVideo: solo mode")
        
        # Used to pass the name and path via the command line
        # This caused problems with non ascii characters, so now
        # we just look at the screen details
        # The solo option is only available from the info screen
        # Looking at the TV Show information page
        if WindowShowing.isTv():
            videoName = xbmc.getInfoLabel( "ListItem.TVShowTitle" )
            log("getSoloVideo: TV Show detected %s" % videoName)
        else:
            videoName = xbmc.getInfoLabel( "ListItem.Title" )
            log("getSoloVideo: Movie detected %s" % videoName)

        # Now get the video path
        videoPath = None
        if WindowShowing.isMovieInformation() and WindowShowing.isTv():
            videoPath = xbmc.getInfoLabel( "ListItem.FilenameAndPath" )
        if videoPath == None or videoPath == "":
            videoPath = xbmc.getInfoLabel( "ListItem.Path" )
        log("getSoloVideo: Video Path %s" % videoPath)


        normVideoName = normalize_string( videoName )
        log("getSoloVideo: videoName = %s" % normVideoName )

        if Settings.isCustomPathEnabled():
            videoPath = os.path.join(Settings.getCustomPath(), normVideoName)
        else:
            log("getSoloVideo: Solo dir = %s" % videoPath)
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

        log("getSoloVideo: videoPath = %s" % videoPath )
        return [[normVideoName,videoPath.decode("utf-8"),normVideoName]]

    # Gets the list of shows that the search is being conducted for
    def getAllVideos(self):
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
                if Settings.isCustomPathEnabled():
                    path = os.path.join(Settings.getCustomPath(), tvshow).decode("utf-8")
                else:
                    # The file is actually the path for a TV Show
                    path = item['file']
                TVlist.append( ( tvshow , path, orgname ) )
        
        # Check is Movies should be added to the list of shows to search
        if Settings.isMovieDownloadEnabled():
            json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.GetMovies", "params": {"properties": ["title", "file"], "sort": { "method": "title" } }, "id": 1}')
            json_query = unicode(json_query, 'utf-8', errors='ignore')
            json_response = simplejson.loads(json_query)
            log( json_response )
            if json_response['result'].has_key('movies'):
                for item in json_response['result']['movies']:
                    orgname = item['title']
                    movie = item['title'].replace(":","")
                    movie = normalize_string( movie )
                    if Settings.isCustomPathEnabled():
                        path = os.path.join(Settings.getCustomPath(), movie).decode("utf-8")
                    else:
                        path = item['file']
                        # Handle stacked files that have a custom file name format
                        if path.startswith("stack://"):
                            path = path.replace("stack://", "").split(" , ", 1)[0]
                        # Need to remove the filename from the end  as we just want the directory
                        path = os.path.dirname( path )
                    TVlist.append( ( movie , path, orgname ) )
        
        return TVlist   

    # Checks if a theme exists in a directory
    def _doesThemeExist(self, directory):
        log("doesThemeExist: Checking directory: %s" % directory)
        # Check for custom theme directory
        if Settings.isThemeDirEnabled():
            directory = os.path.join(directory, Settings.getThemeDirectory())

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
                    log("doesThemeExist: Found match: " + aFile)
                    return True
        return False


    def scan(self):
        count = 0
        total = len(self.Videolist)
        for show in self.Videolist:
            count = count + 1
            if (not self.ERASE and self._doesThemeExist(show[1])) and (not Settings.isMultiThemesSupported()):
                log("scan: %s already exists, ERASE is set to %s" % ( os.path.join(show[1],"theme.*"), [False,True][self.ERASE] ) )
            else:
                self.DIALOG_PROGRESS.update( (count*100)/total , __language__(32107) + ' ' + show[0] , ' ')
                if self.DIALOG_PROGRESS.iscanceled():
                    self.DIALOG_PROGRESS.close()
                    xbmcgui.Dialog().ok(__language__(32108),__language__(32109))
                    break
                theme_list = self.searchThemeList( show[0] )
                #log( theme_list )
                if (len(theme_list) == 1) and Settings.isExactMatchEnabled(): 
                    theme_url = theme_list[0].getMediaURL()
                else:
                    theme_url = self.getUserChoice( theme_list , show[2] )
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
        log("download: %s" % theme_url )

        # Check for custom theme directory
        if Settings.isThemeDirEnabled():
            path = os.path.join(path, Settings.getThemeDirectory())

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
                    log("download: problem with path: %s" % destination )
            fp , h = urllib.urlretrieve( theme_url , tmpdestination , _report_hook )
            log( h )
            copy = xbmcvfs.copy(tmpdestination, destination)
            if copy:
                log("download: copy successful")
            else:
                log("download: copy failed")
            xbmcvfs.delete(tmpdestination)
            return True
        except :
            log("download: Theme download Failed!!!")
            print_exc()
            return False 

    def getUserChoice(self , theme_list , showname):
        theme_url = False
        searchname = showname
        while theme_url == False:
            # Get the selection list to display to the user
            displayList = []
            # start with the custom option to manual search
            displayList.insert(0, __language__(32118))
            if self.isGoEarSearch:
                displayList.insert(1, __language__(32120) % "televisiontunes.com")
            else:
                displayList.insert(1, __language__(32120) % "goear.com")

            # Now add all the other entries
            for theme in theme_list:
                displayList.append(theme.getDisplayString())

            # Show the list to the user
            select = xbmcgui.Dialog().select(__language__(32112) + ' ' + searchname, displayList)
            if select == -1: 
                log("getUserChoice: Cancelled by user")
                return False
            else:
                if select == 0:
                    # Manual search selected
                    kb = xbmc.Keyboard(showname, __language__(32113), False)
                    kb.doModal()
                    result = kb.getText()
                    if (result == None) or (result == ""):
                        log("getUserChoice: No text entered by user")
                        return False
                    theme_list = self.searchThemeList(result, True)
                    searchname = result
                elif select == 1:
                    # Search using the alternative engine 
                    self.isGoEarSearch = not self.isGoEarSearch
                    theme_list = self.searchThemeList(searchname)
                else:
                    # Not the first entry selected, so change the select option
                    # so the index value matches the theme list
                    select = select - 2
                    theme_url = theme_list[select].getMediaURL()
                    log( "getUserChoice: Theme URL = %s" % theme_url )
                    
                    # Play the theme for the user
                    listitem = xbmcgui.ListItem(theme_list[select].getName())
                    listitem.setInfo('music', {'Title': theme_list[select].getName()})
                    # Check if a tune is already playing
                    if xbmc.Player().isPlayingAudio():
                        xbmc.Player().stop()
                    while xbmc.Player().isPlayingAudio():
                        xbmc.sleep(5)
                    
                    xbmcgui.Window( 10025 ).setProperty( "TvTunesIsAlive", "true" )
                    xbmc.Player().play(theme_url, listitem)
                    # Prompt the user to see if this is the theme to download
                    ok = xbmcgui.Dialog().yesno(__language__(32103),__language__(32114))
                    if not ok:
                        theme_url = False
                    xbmc.executebuiltin('PlayerControl(Stop)')
                    xbmcgui.Window( 10025 ).clearProperty('TvTunesIsAlive')

        return theme_url

    def searchThemeList(self , showname, manual=False):
        log("searchThemeList: Search for %s" % showname )

        theme_list = []

        # Check if the search engine being used is GoEar
        if self.isGoEarSearch:
            searchListing = GoearListing()
            if manual:
                theme_list = searchListing.search(showname)
            else:
                theme_list = searchListing.themeSearch(showname)
        else:
            # Default to Television Tunes
            searchListing = TelevisionTunesListing()
            theme_list = searchListing.search(showname)

        return theme_list


    # Calculates the next filename to use when downloading multiple themes
    def getNextThemeFileName(self, path):
        themeFileName = "theme.mp3"
        if Settings.isMultiThemesSupported() and xbmcvfs.exists(os.path.join(path,"theme.mp3")):
            idVal = 1
            while xbmcvfs.exists(os.path.join(path,"theme" + str(idVal) + ".mp3")):
                idVal = idVal + 1
            themeFileName = "theme" + str(idVal) + ".mp3"
        log("Next Theme Filename = " + themeFileName)
        return themeFileName


###########################################################
# Holds the details of each theme retrieved from a search
###########################################################
class ThemeItemDetails():
    def __init__(self, trackName, trackUrlTag, trackLength="", trackQuality="", isGoEarSearch=False):
        # Remove any HTML characters from the name
        h = HTMLParser.HTMLParser()
        self.trackName = h.unescape(trackName)
        self.trackUrlTag = trackUrlTag
        self.trackLength = trackLength
        self.trackQuality = trackQuality
        self.isGoEarSearch = isGoEarSearch

        # Television Tunes download URL (default)
        self.download_url = "http://www.televisiontunes.com/download.php?f=%s"

        if self.isGoEarSearch:
            # GoEar download URL
            self.download_url = "http://www.goear.com/action/sound/get/%s"

    # Checks if the theme this points to is the same
    def __eq__(self, other):
        if other == None:
            return False
        # Check if the URL is the same as that will make it unique
        return self.trackUrlTag == other.trackUrlTag

    # lt defined for sorting order only
    def __lt__(self, other):
        # Order just on the name of the file
        return self.trackName < other.trackName


    # Get the raw track name
    def getName(self):
        return self.trackName

    # Get the display name that could include extra information
    def getDisplayString(self):
        return "%s%s%s" % (self.trackName, self.trackLength, self.trackQuality)

    # Gets the ID to uniquely identifier a given tune
    def _getId(self):
        audio_id = ""

        # Check if the search engine being used is GoEar
        if self.isGoEarSearch:
            # The URL will be of the format:
            #  http://www.goear.com/listen/1ed51e2/together-the-firm
            # We want the ID out of the middle
            start_of_id = self.trackUrlTag.find("listen/") + 7
            end_of_id = self.trackUrlTag.find("/", start_of_id)
            audio_id = self.trackUrlTag[start_of_id:end_of_id]
        else:
            # Default to Television Tunes
            audio_id = self.trackUrlTag
            audio_id = audio_id.replace("http://www.televisiontunes.com/", "")
            audio_id = audio_id.replace(".html" , "")
            
        return audio_id

    # Get the URL used to download the theme
    def getMediaURL(self):
        theme_url = self.download_url % self._getId()
        return theme_url

#################################################
# Searches www.televisiontunes.com for themes
#################################################
class TelevisionTunesListing():
    def __init__(self):
        # Links required for televisiontunes.com
        self.search_url = "http://www.televisiontunes.com/search.php?searWords=%s&Send=Search"
    
    # Perform the search for the theme
    def search(self, showname):
        log("TelevisionTunesListing: Search for %s" % showname )
        theme_list = []
        next = True
        # Prevent the error if there are invalid characters by encoding as utf-8
        url = self.search_url % urllib.quote_plus(showname.encode("utf-8"))
        urlpage = ""
        while next == True:
            # Get the HTMl at the given URL
            data = self._getHtmlSource( url + urlpage )
            log("TelevisionTunesListing: Search url = %s" % ( url + urlpage ) )
            # Search the HTML for the links to the themes
            match = re.search(r"1\.&nbsp;(.*)<br>", data)
            if match: data2 = re.findall('<a href="(.*?)">(.*?)</a>', match.group(1))
            else: 
                log("TelevisionTunesListing: no theme found for %s" % showname )
                data2 = ""
            for i in data2:
                themeURL = i[0] or ""
                themeName = i[1] or ""
                theme = ThemeItemDetails(themeName, themeURL)
                # in case of an exact match (when enabled) only return this theme
                if Settings.isExactMatchEnabled() and themeName == showname:
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
            log("TelevisionTunesListing: next page = %s" % next )
        return theme_list

    def _getHtmlSource(self, url, save=False):
        """ fetch the html source """
        class AppURLopener(urllib.FancyURLopener):
            version = "Mozilla/5.0 (Windows; U; Windows NT 5.1; fr; rv:1.9.0.1) Gecko/2008070208 Firefox/3.6"
        urllib._urlopener = AppURLopener()
    
        try:
            if os.path.isfile( url ):
                sock = open( url, "r" )
            else:
                urllib.urlcleanup()
                sock = urllib.urlopen( url )
    
            htmlsource = sock.read()
            if save:
                file( os.path.join( CACHE_PATH , save ) , "w" ).write( htmlsource )
            sock.close()
            return htmlsource
        except:
            print_exc()
            log( "getHtmlSource: ERROR opening page %s" % url )
            xbmcgui.Dialog().ok(__language__(32101) , __language__(32102))
            return False

#################################################
# Searches www.goear.com for themes
#################################################
class GoearListing():
    def __init__(self):
        self.baseUrl = "http://www.goear.com/search/"
        self.themeDetailsList = []

    # Searches for a given subset of themes, trying to reduce the list
    def themeSearch(self, name):
        # If performing the automated search, remove anything in brackets
        # Remove anything in square brackets
        searchName = re.sub(r'\[[^)]*\]', '', name)
        # Remove anything in rounded brackets
        searchName = re.sub(r'\([^)]*\)', '', searchName)
        # Remove double space
        searchName = searchName.replace("  ", " ")
        
        self.search(searchName + "-OST") # English acronym for original soundtrack
        self.search(searchName + "-theme")
        self.search(searchName + "-title")
        self.search(searchName + "-soundtrack")
        self.search(searchName + "-tv")
        self.search(searchName + "-movie")
        self.search(searchName + "-tema") # Spanish for theme
        self.search(searchName + "-BSO") # Spanish acronym for OST (banda sonora original)
        self.search(searchName + "-B.S.O.") # variation for Spanish acronym BSO
        self.search(searchName + "-banda-sonora") # Spanish for Soundtrack
        self.search(searchName + "-pelicula") # Spanish for movie

        # If no entries found doing the custom search then just search for the name only
        if len(self.themeDetailsList) < 1:
            self.search(searchName)
        else:
            # We only sort the returned data if it is a result of us doing multiple searches
            # The case where we just did a single "default" search we leave the list as
            # it was returned to us, this is because it will be returned in "relevance" order
            # already, so we want the best matches at the top
            self.themeDetailsList.sort()
        
        return self.themeDetailsList

    # Perform the search for the theme
    def search(self, name):
        # User - instead of spaces
        searchName = name.replace(" ", "-")
        # Remove double space
        searchName = searchName.replace("--", "-")

        fullUrl = self.baseUrl + searchName

        # Load the output of the search request into Soup
        soup = self._getPageContents(fullUrl)

        # Get all the pages for this set of search results
        urlPageList = self._getSearchPages(soup)

        # The first page is always /0 on the URL, so we should check this
        self._getEntries(soup)
        
        for page in urlPageList:
            # Already processed the first page, no need to retrieve it again
            if page == (fullUrl + "/0"):
                continue
            # Get the next page and read the tracks from it
            soup = self._getPageContents(page)
            self._getEntries(soup)
        
        return self.themeDetailsList

    def _getPageContents(self, fullUrl):
        # Start by calling the search URL
        req = urllib2.Request(fullUrl)
        req.add_header('User-Agent', ' Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
        response = urllib2.urlopen(req)
        # Holds the webpage that was read via the response.read() command
        doc = response.read()
        # Closes the connection after we have read the webpage.
        response.close()

        # Load the output of the search request into Soup
        return BeautifulSoup(''.join(doc))


    # Results could be over multiple pages
    def _getSearchPages(self, soup):
        # Now check to see if there were any other pages
        searchPages = soup.find('ol', { "id" : "new_pagination"})

        urlList = []
        for page in searchPages.contents:
            # Skip the blank lines, just want the <li> elements
            if page == '\n':
                continue
        
            # Get the URL for the track
            pageUrlTag = page.find('a')
            if pageUrlTag == None:
                continue
            pageUrl = pageUrlTag['href']
            # Add to the list of URLs
            urlList.append(pageUrl)

        return urlList

    # Reads the track entries from the page
    def _getEntries(self, soup):
        # Get all the items in the search results
        searchResults = soup.find('ol', { "id" : "search_results"})
        
        # Check out each item in the search results list
        for item in searchResults.contents:
            # Skip the blank lines, just want the <li> elements
            if item == '\n':
                continue
        
            # Get the name of the track
            trackNameTag = item.find('span', { "class" : "song" })
            if trackNameTag == None:
                continue
            trackName = trackNameTag.string
            
            # Get the URL for the track
            trackUrlTag = item.find('a')
            if trackUrlTag == None:
                continue
            trackUrl = trackUrlTag['href']
        
            # Get the length of the track
            # e.g. <li class="length radius_3">3:36</li>
            trackLength = ""
            trackLengthTag = item.find('li', { "class" : "length radius_3" })
            if trackUrlTag != None:
                trackLength = " [" + trackLengthTag.string + "]"
        
            # Get the quality of the track
            # e.g. <li class="kbps radius_3">128<abbr title="Kilobit por segundo">kbps</abbr></li>
            trackQuality = ""
            trackQualityTag = item.find('li', { "class" : "kbps radius_3" })
            if trackQualityTag != None:
                trackQuality = " (" + trackQualityTag.contents[0] + "kbps)"
        
            themeScraperEntry = ThemeItemDetails(trackName, trackUrl, trackLength, trackQuality, True)
            if not (themeScraperEntry in self.themeDetailsList):
                log("GoearListing: Theme Details = %s" % themeScraperEntry.getDisplayString())
                log("GoearListing: Theme URL = %s" % themeScraperEntry.getMediaURL() )
                self.themeDetailsList.append(themeScraperEntry)


if ( __name__ == "__main__" ):
    TvTunesScraper()
