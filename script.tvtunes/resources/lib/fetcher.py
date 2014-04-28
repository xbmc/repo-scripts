# -*- coding: utf-8 -*-
import sys
import urllib
import os
from traceback import print_exc
import re
import unicodedata
import xbmc  
import xbmcaddon
import xbmcgui
import xbmcvfs
import traceback
import math

# Following includes required for GoEar support
import urllib2
from BeautifulSoup import BeautifulSoup
import HTMLParser


__addon__     = xbmcaddon.Addon(id='script.tvtunes')
__addonid__   = __addon__.getAddonInfo('id')
__language__  = __addon__.getLocalizedString
__icon__      = __addon__.getAddonInfo('icon')
__cwd__       = __addon__.getAddonInfo('path').decode("utf-8")
__resource__  = xbmc.translatePath( os.path.join( __cwd__, 'resources' ).encode("utf-8") ).decode("utf-8")
__lib__  = xbmc.translatePath( os.path.join( __resource__, 'lib' ).encode("utf-8") ).decode("utf-8")

sys.path.append(__resource__)
sys.path.append(__lib__)

# Import the common settings
from settings import Settings
from settings import log
from settings import os_path_join
from settings import os_path_split
from settings import list_dir
from settings import normalize_string

import soundcloud
from grooveshark import Client


#################################
# Core TvTunes Scraper class
#################################
class TvTunesFetcher:
    TELEVISION_TUNES = 'televisiontunes.com'
    SOUNDCLOUD = 'soundcloud.com'
    GROOVESHARK = 'grooveshark.com'
    GOEAR = 'goear.com'
    
    
    def __init__(self, videoList):
        # Set up the addon directories if they do not already exist
        if not xbmcvfs.exists( xbmc.translatePath( 'special://profile/addon_data/%s' % __addonid__ ).decode("utf-8") ):
            xbmcvfs.mkdir( xbmc.translatePath( 'special://profile/addon_data/%s' % __addonid__ ).decode("utf-8") )
        if not xbmcvfs.exists( xbmc.translatePath( 'special://profile/addon_data/%s/temp' % __addonid__ ).decode("utf-8") ):
            xbmcvfs.mkdir( xbmc.translatePath( 'special://profile/addon_data/%s/temp' % __addonid__ ).decode("utf-8") )
        
        self.DIALOG_PROGRESS = xbmcgui.DialogProgress()
        self.DIALOG_PROGRESS.create( __language__(32105) , __language__(32106) )

        # The video list is in the format [videoName, Path, DisplayName]
        self.Videolist = videoList

        # Get the currently selected search engine
        self.searchEngine = Settings.getSearchEngine()

        # Now we have the list of programs to search for, perform the scan
        self.scan()
        self.DIALOG_PROGRESS.close()
        

    # Search for themes
    def scan(self):
        count = 0
        total = len(self.Videolist)
        for show in self.Videolist:
            count = count + 1
            self.DIALOG_PROGRESS.update( (count*100)/total, ("%s %s" % (__language__(32107), show[0].decode("utf-8"))), ' ')
            if self.DIALOG_PROGRESS.iscanceled():
                self.DIALOG_PROGRESS.close()
                xbmcgui.Dialog().ok(__language__(32108),__language__(32109))
                break
            theme_list = self.searchThemeList( show[0] )
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

    # Download the theme
    def download(self , theme_url , path):
        log("download: %s" % theme_url )

        # Check for custom theme directory
        if Settings.isThemeDirEnabled():
            themeDir = os_path_join(path, Settings.getThemeDirectory())
            if not xbmcvfs.exists(themeDir):
                workingPath = path
                # If the path currently ends in the directory separator
                # then we need to clear an extra one
                if (workingPath[-1] == os.sep) or (workingPath[-1] == os.altsep):
                    workingPath = workingPath[:-1]
                # If not check to see if we have a DVD VOB
                if (os_path_split(workingPath)[1] == 'VIDEO_TS') or (os_path_split(workingPath)[1] == 'BDMV'):
                    log("DVD image detected")
                    # Check the parent of the DVD Dir
                    themeDir = os_path_split(workingPath)[0]
                    themeDir = os_path_join(themeDir, Settings.getThemeDirectory())
            path = themeDir

        log("target directory: %s" % path )

        theme_file = self.getNextThemeFileName(path)
        tmpdestination = xbmc.translatePath( 'special://profile/addon_data/%s/temp/%s' % ( __addonid__ , theme_file ) ).decode("utf-8")
        destination = os_path_join( path , theme_file )
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


    # Retrieve the theme that the user has selected
    def getUserChoice(self , theme_list , showname):
        theme_url = False
        searchname = showname
        while theme_url == False:
            # Get the selection list to display to the user
            displayList = []
            # start with the custom option to manual search
            displayList.insert(0, __language__(32118))
            displayList.insert(1, __language__(32120) % "")

            # Now add all the other entries
            for theme in theme_list:
                displayList.append(theme.getDisplayString())

            # Show the list to the user
            select = xbmcgui.Dialog().select(("%s %s" % (__language__(32112), searchname.decode("utf-8"))), displayList)
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
                    self.promptForSearchEngine()
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

    # Perform the actual search on the configured web site
    def searchThemeList(self, showname, manual=False):
        log("searchThemeList: Search for %s" % showname )

        theme_list = []

        # Check if the search engine being used is GoEar
        if self.searchEngine == TvTunesFetcher.GOEAR:
            # Goeear is selected
            searchListing = GoearListing()
            if manual:
                theme_list = searchListing.search(showname)
            else:
                theme_list = searchListing.themeSearch(showname)
        elif self.searchEngine == TvTunesFetcher.SOUNDCLOUD:
            # Soundcloud is selected
            searchListing = SoundcloudListing()
            theme_list = searchListing.search(showname)
        elif self.searchEngine == TvTunesFetcher.GROOVESHARK:
            # grooveshark is selected
            searchListing = GroovesharkListing()
            theme_list = searchListing.search(showname)
        else:
            # Default to Television Tunes
            searchListing = TelevisionTunesListing()
            theme_list = searchListing.search(showname)

        return theme_list


    # Calculates the next filename to use when downloading multiple themes
    def getNextThemeFileName(self, path):
        themeFileName = "theme.mp3"
        if Settings.isMultiThemesSupported() and xbmcvfs.exists(os_path_join(path,"theme.mp3")):
            idVal = 1
            while xbmcvfs.exists(os_path_join(path,"theme" + str(idVal) + ".mp3")):
                idVal = idVal + 1
            themeFileName = "theme" + str(idVal) + ".mp3"
        log("Next Theme Filename = " + themeFileName)
        return themeFileName

    # Prompt the user to select a different search option
    def promptForSearchEngine(self):
        displayList = []
        displayList.insert(0, TvTunesFetcher.TELEVISION_TUNES)
        displayList.insert(1, TvTunesFetcher.SOUNDCLOUD)
        displayList.insert(2, TvTunesFetcher.GROOVESHARK)
        displayList.insert(3, TvTunesFetcher.GOEAR + " (Broken)")

        # Show the list to the user
        select = xbmcgui.Dialog().select((__language__(32120) % ""), displayList)
        if select == -1: 
            log("promptForSearchEngine: Cancelled by user")
            return False
        else:
            if select == 0:
                self.searchEngine = TvTunesFetcher.TELEVISION_TUNES
            elif select == 1:
                self.searchEngine = TvTunesFetcher.SOUNDCLOUD
            elif select == 2:
                self.searchEngine = TvTunesFetcher.GROOVESHARK
            elif select == 3:
                self.searchEngine = TvTunesFetcher.GOEAR
            else:
                return False
        
        log("promptForSearchEngine: New search engine is %s" % self.searchEngine)
        return True

###########################################################
# Holds the details of each theme retrieved from a search
###########################################################
class ThemeItemDetails():
    def __init__(self, trackName, trackUrl, trackLength="", trackQuality=""):
        # Remove any HTML characters from the name
        h = HTMLParser.HTMLParser()
        self.trackName = h.unescape(trackName)
        self.trackUrl = trackUrl
        self.trackLength = trackLength
        self.trackQuality = trackQuality

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

    # Get the URL used to download the theme
    def getMediaURL(self):
        return self.trackUrl


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
        url = self.search_url % urllib.quote_plus(showname)
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
                downloadUrl = self._getMediaURL(themeURL)
                theme = ThemeItemDetails(themeName, downloadUrl)
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
        # fetch the html source
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
                file( os_path_join( CACHE_PATH , save ) , "w" ).write( htmlsource )
            sock.close()
            return htmlsource
        except:
            print_exc()
            log( "getHtmlSource: ERROR opening page %s" % url )
            xbmcgui.Dialog().ok(__language__(32101) , __language__(32102))
            return False

    # Gets the URL to stream and download from
    def _getMediaURL(self, themeURL):
        audio_id = themeURL
        audio_id = audio_id.replace("http://www.televisiontunes.com/", "")
        audio_id = audio_id.replace(".html" , "")

        download_url = "http://www.televisiontunes.com/download.php?f=%s" % audio_id
            
        return download_url



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
        
        self.search("%s%s" % (searchName, "-OST")) # English acronym for original soundtrack
        self.search("%s%s" % (searchName, "-theme"))
        self.search("%s%s" % (searchName, "-title"))
        self.search("%s%s" % (searchName, "-soundtrack"))
        self.search("%s%s" % (searchName, "-tv"))
        self.search("%s%s" % (searchName, "-movie"))
        self.search("%s%s" % (searchName, "-tema")) # Spanish for theme
        self.search("%s%s" % (searchName, "-BSO")) # Spanish acronym for OST (banda sonora original)
        self.search("%s%s" % (searchName, "-B.S.O.")) # variation for Spanish acronym BSO
        self.search("%s%s" % (searchName, "-banda-sonora")) # Spanish for Soundtrack
        self.search("%s%s" % (searchName, "-pelicula")) # Spanish for movie

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

        if soup != None:
            # Get all the pages for this set of search results
            urlPageList = self._getSearchPages(soup)
    
            # The first page is always /0 on the URL, so we should check this
            self._getEntries(soup)
            
            for page in urlPageList:
                # Already processed the first page, no need to retrieve it again
                if page.endswith("/0"):
                    continue
                # Get the next page and read the tracks from it
                soup = self._getPageContents(page)
                if soup != None:
                    self._getEntries(soup)
        
        return self.themeDetailsList

    # Reads a web page
    def _getPageContents(self, fullUrl):
        # Start by calling the search URL
        req = urllib2.Request(fullUrl)
        req.add_header('User-Agent', ' Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
        
        requestFailed = True
        maxAttempts = 3
        
        while requestFailed and (maxAttempts > 0):
            maxAttempts = maxAttempts - 1
            try:
                response = urllib2.urlopen(req)
                # Holds the webpage that was read via the response.read() command
                doc = response.read()
                # Closes the connection after we have read the webpage.
                response.close()
                
                requestFailed = False
            except:
                # If we get an exception we have failed to perform the http request
                # we will try again before giving up
                log("GoearListing: Request failed for %s" % fullUrl)
                log("GoearListing: %s" % traceback.format_exc())


        if requestFailed:
            # pop up a notification, and then return than none were found
            xbmc.executebuiltin('Notification(%s, %s, %d, %s)' % (__language__(32105), __language__(32994), 5, __icon__))
            return None

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
        
            downloadURL = self._getMediaURL(trackUrl)
            themeScraperEntry = ThemeItemDetails(trackName, downloadURL, trackLength, trackQuality)
            if not (themeScraperEntry in self.themeDetailsList):
                log("GoearListing: Theme Details = %s" % themeScraperEntry.getDisplayString())
                log("GoearListing: Theme URL = %s" % themeScraperEntry.getMediaURL() )
                self.themeDetailsList.append(themeScraperEntry)

    # Gets the URL to stream and download from
    def _getMediaURL(self, themeURL):
        # The URL will be of the format:
        #  http://www.goear.com/listen/1ed51e2/together-the-firm
        # We want the ID out of the middle
        start_of_id = themeURL.find("listen/") + 7
        end_of_id = themeURL.find("/", start_of_id)
        audio_id = themeURL[start_of_id:end_of_id]

        download_url = "http://www.goear.com/action/sound/get/%s" % audio_id
            
        return download_url


#################################################
# Searches www.soundcloud.com for themes
#################################################
class SoundcloudListing():
    def __init__(self):
        # Links required for televisiontunes.com
        self.search_url = ""

    # Perform the search for the theme
    def search(self, showname):
        log("SoundcloudListing: Search for %s" % showname )
 
        tracks = None
        client = soundcloud.Client(client_id='b45b1aa10f1ac2941910a7f0d10f8e28')
        try:
            # Max value for limit is 200 entries
            # TODO need to page all the results
            tracks = client.get('/tracks', q=showname, filter="streamable", limit=200)
        except:
            log("SoundcloudListing: Request failed for %s" % showname)
            log("SoundcloudListing: %s" % traceback.format_exc())

        # Loop over the tracks produced assigning it to the list
        theme_list = []
        for track in tracks:
            #another dictionary for holding all the results for a specific song
            themeName = track.title
            duration = self._convertTime(track.duration)
            # The file size makes no difference as the stream is always limited to 128kbps
            filesize = "" # self._convertSize(track.original_content_size)
            themeURL = ""
            try:
                # Only allow the theme if it is streamable
                if track.streamable:
                    id = track.id
    #                themeURL = track.download_url or track.permalink_url
                    themeURL = self._getDownloadLinkFromWaveform(track.waveform_url)
                    log("SoundcloudListing: Found %s%s (%s) %s (%s)" % (themeName, duration, themeURL, str(id), track.waveform_url))
        
                    theme = ThemeItemDetails(themeName, themeURL, duration, filesize)
                    theme_list.append(theme)
                else:
                    # As we filter for only streamable, this should never happen
                    log("SoundcloudListing: %s is not streamable" % themeName)
            except:
                pass
        return theme_list

    # Generate the stream link from the waveform_url 
    def _getDownloadLinkFromWaveform(self, waveform_url):
        regex = re.compile("\/([a-zA-Z0-9]+)_")
        r = regex.search(waveform_url)
        stream_id = r.groups()[0]
        return "http://media.soundcloud.com/stream/%s" % str(stream_id)

    # this method converts the time in milliseconds to human readable format.
    def _convertTime(self, ms):
        x = ms / 1000
        seconds = x % 60
        x /= 60
        minutes = x % 60
        x /= 60
        hours = x % 24
        x /= 24
        days = x
        return " [%02d:%02d:%02d]" % (hours, minutes, seconds)

    def _convertSize(self, size):
       size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
       i = int(math.floor(math.log(size,1024)))
       p = math.pow(1024,i)
       s = round(size/p,2)
       if (s > 0):
           return ' (%s %s)' % (s,size_name[i])
       else:
           return ""
   


#################################################
# Searches www.grooveshark.com for themes
#################################################
class GroovesharkListing():
    def __init__(self):
        # Links required for televisiontunes.com
        self.search_url = ""

    # Perform the search for the theme
    def search(self, showname):
        log("GroovesharkListing: Search for %s" % showname )
 
        tracks = None
        
        try:
            client = Client()
            client.init()
            tracks = client.search(showname)
        except:
            log("GroovesharkListing: Request failed for %s" % showname)
            log("GroovesharkListing: %s" % traceback.format_exc())

        # Loop over the tracks produced assigning it to the list
        theme_list = []
        for track in tracks:
            log("GroovesharkListing: Found %s" % track.name)
            # Construct the custom holder for the theme
            theme = GroovesharkThemeItemDetails(track)
            theme_list.append(theme)
        return theme_list

###########################################################
# Holds the details of each theme retrieved from a search
# Custom for grooveshark as we need to generate the streem
# just for the entry that is used, this is because getting
# each of the streams for everything in the list takes
# far too long up-front, so we just get the one that the
# user wants
###########################################################
class GroovesharkThemeItemDetails(ThemeItemDetails):
    def __init__(self, track):
        self.grooveshark_track = track
        ThemeItemDetails.__init__(self, track.name, "")

    # Get the URL used to download the theme
    def getMediaURL(self):
        # We need to generate the URL on the fly, this is because it takes too
        # long to generate before hand for each track
        log("GroovesharkThemeItemDetails: Getting stream for %s" % self.grooveshark_track.name)
        
        try:
            self.trackUrl = self.grooveshark_track.stream.url
            log("GroovesharkThemeItemDetails: Stream url is %s" % self.trackUrl)
        except:
            log("GroovesharkThemeItemDetails: Request failed for %s" % self.grooveshark_track.name)
            log("GroovesharkThemeItemDetails: %s" % traceback.format_exc())
        
        return self.trackUrl

