# *  Credits:
# *
# *  divingmule for script.image.lastfm.slideshow
# *  grajen3 for script.ImageCacher
# *
# *  code of both scripts is used in script.artistslideshow
# *
# *
# *  Last.fm:  http://www.last.fm/

import urllib, urllib2, re, os, time
import xbmc, xbmcgui, xbmcaddon
from BeautifulSoup import BeautifulSoup

__settings__ = xbmcaddon.Addon( "script.artistslideshow" )

def log(txt):
    message = 'script.artistslideshow: %s' % txt
    xbmc.log(msg=message, level=xbmc.LOGNOTICE)

def checkDir(path):
    if not os.path.exists(path):
        os.mkdir(path)

def getCacheThumbName(url, CachePath):
    thumb = xbmc.getCacheThumbName(url)

    if 'jpg' in url:
        thumb = thumb.replace('.tbn', '.jpg')
    elif 'png' in url:
        thumb = thumb.replace('.tbn', '.png')
    elif 'gif' in url:
        thumb = thumb.replace('.tbn', '.gif')

    tpath = os.path.join(CachePath, thumb)
    return tpath

def download(src, dst):
    tmpname = xbmc.translatePath('special://temp/%s' % xbmc.getCacheThumbName(src))

    if os.path.exists(tmpname):
        os.remove(tmpname)

    urllib.urlretrieve(src, filename = tmpname)

    if os.path.getsize(tmpname) > 999:
        os.rename(tmpname, dst)
    else:
        os.remove(tmpname)

def startDownload(minwidth, minheight):
    global name
    global DownloadedAllImages
    if xbmc.Player().isPlayingAudio() == False:
        log('no music playing')
        xbmcgui.Window( 12006 ).clearProperty("ArtistSlideshowRunning")
        return
    else:
        name = xbmc.Player().getMusicInfoTag().getArtist()
        if len(name) == 0:
            log('no artist name provided')
            return
        song = xbmc.Player().getMusicInfoTag().getURL()
        if len(song) == 0: # url may not be available for online radio
            song = xbmc.Player().getMusicInfoTag().getTitle()
        CacheName = xbmc.getCacheThumbName(name).replace('.tbn', '')
        checkDir(xbmc.translatePath('special://profile/Thumbnails/ArtistSlideshow'))
        CacheDir = xbmc.translatePath('special://profile/Thumbnails/ArtistSlideshow/%s' % CacheName)
        checkDir(CacheDir)
        log('cachedir = %s' % CacheDir)
        files = os.listdir(CacheDir)
        CachedImagesFound = False
        DownloadedFirstImage = False
        DownloadedAllImages = False
        ImageDownloaded = False

        for file in files:
            if (file.endswith('jpg') or file.endswith('png') or file.endswith('gif') ):
                CachedImagesFound = True

        if CachedImagesFound:
            log('cached images found')
            xbmcgui.Window( 12006 ).setProperty("ArtistSlideshow", CacheDir)

        log('downloading images')
        url = 'http://ws.audioscrobbler.com/2.0/?method=artist.getimages&artist='+name.replace('&','%26').replace(' ','+')+'&autocorrect=1&api_key=fbd57a1baddb983d1848a939665310f6'
        req = urllib2.Request(url)
        response = urllib2.urlopen(req)
        link = response.read()
        response.close()
        soup = BeautifulSoup(link)
        images = soup('image')

        for image in images:
            if xbmc.Player().isPlayingAudio() == True:
                currentsong = xbmc.Player().getMusicInfoTag().getURL()
                if len(currentsong) == 0:
                    currentsong = xbmc.Player().getMusicInfoTag().getTitle()
                if song != currentsong:
                    log('new track started before download has finished')
                    return
            url = image.size.string
            size = image.size
            height = int(size.get('height').replace('height ',''))
            width = int(size.get('width').replace('width ',''))
            path = getCacheThumbName(url, CacheDir)
            if not os.path.exists(path):
                if (width >= minwidth) and (height >= minheight):
                    download(url, path)
                    log('downloaded %s to %s' % (url, path) )
                    ImageDownloaded=True
            if ImageDownloaded:
                if not DownloadedFirstImage:
                    log('downloaded first image')
                    DownloadedFirstImage = True
                if not CachedImagesFound:
                    xbmcgui.Window( 12006 ).setProperty("ArtistSlideshow", CacheDir)

        if ImageDownloaded:
            log('finished downloaded images')
            DownloadedAllImages = True
            xbmcgui.Window( 12006 ).setProperty("ArtistSlideshowRefresh", "True")
            time.sleep(0.3)
            xbmcgui.Window( 12006 ).clearProperty("ArtistSlideshow")
            time.sleep(0.05)
            xbmcgui.Window( 12006 ).setProperty("ArtistSlideshow", CacheDir)
            xbmcgui.Window( 12006 ).clearProperty("ArtistSlideshowRefresh")

        if not ImageDownloaded:
            log('no images downloaded')
            DownloadedAllImages = True
            if not CachedImagesFound:
                xbmcgui.Window( 12006 ).clearProperty("ArtistSlideshow")

def Start():
    class MyPlayer( xbmc.Player ):
        def __init__ ( self ):
            xbmc.Player.__init__( self )
            self.minwidth = int(__settings__.getSetting( "minwidth" ))
            self.minheight = int(__settings__.getSetting( "minheight" ))
            log('first song started')
            xbmc.sleep(200) # it may take some time for xbmc to read tag info after playback started
            startDownload( self.minwidth , self.minheight )
            while (True):
                if xbmc.getInfoLabel( "Window(12006).Property(ArtistSlideshowRunning)" ) == "True":
                    xbmc.sleep(1000)
                else:
                    xbmcgui.Window( 12006 ).clearProperty("ArtistSlideshow")
                    xbmcgui.Window( 12006 ).clearProperty("ArtistSlideshowRefresh")
                    break

        def onPlayBackStarted( self ):
            log('next song started')
            xbmc.sleep(200) # it may take some time for xbmc to read tag info after playback started
            if xbmc.Player().isPlayingAudio() == True:
                currentname = xbmc.Player().getMusicInfoTag().getArtist()
                if name != currentname:
                    log('new artist playing, start download')
                    startDownload( self.minwidth , self.minheight )
                elif not DownloadedAllImages:
                    log('same artist playing, continue download')
                    startDownload( self.minwidth , self.minheight )
                else:
                    log('same artist playing, no need to download')

        def onPlayBackStopped( self ):
            xbmc.sleep(1000)
            if not self.isPlayingAudio():
                log('playback stopped')
                xbmcgui.Window( 12006 ).clearProperty("ArtistSlideshowRunning")

        def onPlayBackEnded( self ):
            xbmc.sleep(1000)
            if not self.isPlayingAudio():
                log('playback ended')
                xbmcgui.Window( 12006 ).clearProperty("ArtistSlideshowRunning")

    MyPlayer()

log('script started')
if xbmc.getInfoLabel( "Window(12006).Property(ArtistSlideshowRunning)" ) == "True":
    log('script already running')
if not xbmc.getInfoLabel( "Window(12006).Property(ArtistSlideshowRunning)" ) == "True":
    xbmcgui.Window( 12006 ).setProperty("ArtistSlideshowRunning", "True")
    Start()
log('script stopped')
