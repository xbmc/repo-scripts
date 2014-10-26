import xbmc
import xbmcgui
import xbmcaddon
import urllib
import urllib2
import httplib
import hashlib
import StringIO
import gzip
import sys
import json as json
from random import randrange
from uuid import uuid4 as uuid4


class DownloadUtils():

    logLevel = 0
    addonSettings = None
    getString = None

    def __init__(self, *args):
        self.addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        self.getString = self.addonSettings.getLocalizedString     
        self.logLevel = 0


    def logMsg(self, msg, level = 1):
        if(self.logLevel >= level):
            xbmc.log("[Titanskin] -> " + msg)


    def getArtwork(self, data, type, index = "0", userParentInfo = False):

        id = data.get("Id")
        getSeriesData = False

        if type == "tvshow.poster": # Change the Id to the series to get the overall series poster
            if data.get("Type") == "Season" or data.get("Type")== "Episode":
                id = data.get("SeriesId")
                getSeriesData = True
        elif type == "poster" and data.get("Type") == "Episode" and self.addonSettings.getSetting('useSeasonPoster')=='true': # Change the Id to the Season to get the season poster
            id = data.get("SeasonId")
        if type == "poster" or type == "tvshow.poster": # Now that the Ids are right, change type to MB3 name
            type="Primary"
        if data.get("Type") == "Season":  # For seasons: primary (poster), thumb and banner get season art, rest series art
            if type != "Primary" and type != "Primary2" and type != "Primary3" and type != "Thumb" and type != "Banner":
                id = data.get("SeriesId")
                getSeriesData = True
        if data.get("Type") == "Episode":  # For episodes: primary (episode thumb) gets episode art, rest series art. 
            if type != "Primary" and type != "Primary2" and type != "Primary3":
                id = data.get("SeriesId")
                getSeriesData = True
            if type =="Primary2" or type=="Primary3":
                id = data.get("SeasonId")
                getSeriesData = True
        if id == None:
            id=data.get("Id")
        # if requested get parent info
        if getSeriesData == True and userParentInfo == True:
            self.logMsg("Using Parent Info for image link", level=1)
            mb3Host = self.addonSettings.getSetting('ipaddress')
            mb3Port = self.addonSettings.getSetting('port')
            userid = WINDOW.getProperty("userid")
            seriesJsonData = self.downloadUrl("http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items/" + id + "?format=json", suppress=False, popup=1 )
            seriesResult = json.loads(seriesJsonData)
            data = seriesResult

        imageTag = "e3ab56fe27d389446754d0fb04910a34" # a place holder tag, needs to be in this format
        originalType = type
        if type == "Primary2" or type == "Primary3" or type=="SeriesPrimary":
            type = "Primary"
        if type == "Backdrop2" or type=="Backdrop3" or type=="BackdropNoIndicators":
            type = "Backdrop"
        if type == "Thumb2" or type=="Thumb3":
            type = "Thumb"
        if(data.get("ImageTags") != None and data.get("ImageTags").get(type) != None):
            imageTag = data.get("ImageTags").get(type)   

        if (data.get("Type") == "Episode" or data.get("Type") == "Season") and type=="Logo":
            imageTag = data.get("ParentLogoImageTag")
        if (data.get("Type") == "Episode" or data.get("Type") == "Season") and type=="Art":
            imageTag = data.get("ParentArtImageTag")

        query = ""
        height = "10000"
        width = "10000"
        played = "0"
        totalbackdrops = 0


        # use the local image proxy server that is made available by this addons service

        port = self.addonSettings.getSetting('port')
        host = self.addonSettings.getSetting('ipaddress')
        server = host + ":" + port

        if imageTag == None:
            imageTag = "e3ab56fe27d389446754d0fb04910a34"
        artwork = "http://" + server + "/mediabrowser/Items/" + str(id) + "/Images/" + type + "/" + index + "/" + imageTag + "/original/" + height + "/" + width + "/" + played + "?" + query
        artwork = artwork + "&EnableImageEnhancers=false"

        #self.logMsg("getArtwork : " + artwork, level=2)

        # do not return non-existing images
        if (    (type!="Backdrop" and imageTag=="e3ab56fe27d389446754d0fb04910a34") |  #Remember, this is the placeholder tag, meaning we didn't find a valid tag
                (type=="Backdrop" and data.get("BackdropImageTags") != None and len(data.get("BackdropImageTags")) == 0) | 
                (type=="Backdrop" and data.get("BackdropImageTag") != None and len(data.get("BackdropImageTag")) == 0)                
                ):
            if type != "Backdrop" or (type=="Backdrop" and getSeriesData==True and data.get("ParentBackdropImageTags") == None) or (type=="Backdrop" and getSeriesData!=True):
                artwork=''        

        return artwork

    def getUserArtwork(self, data, type, index = "0"):

        id = data.get("Id")
        query = "&type=" + type + "&user=user"
        # use the local image proxy server that is made available by this addons service
        port = self.addonSettings.getSetting('port')
        host = self.addonSettings.getSetting('ipaddress')
        server = host + ":" + port

        # use the local image proxy server that is made available by this addons service
        artwork = "http://localhost:15001/?id=" + str(id) + query

        return artwork                  

    def imageUrl(self, id, type, index, width, height):

        port = self.addonSettings.getSetting('port')
        host = self.addonSettings.getSetting('ipaddress')
        server = host + ":" + port

        return "http://" + server + "/mediabrowser/Items/" + str(id) + "/Images/" + type + "/" + str(index) + "/e3ab56fe27d389446754d0fb04910a34/original/" + str(height) + "/" + str(width) + "/0"

    def downloadUrl(self, url, suppress=False, type="GET", popup=0 ):
        self.logMsg("[Titanskin] == ENTER: getURL ==")
        try:
            if url[0:4] == "http":
                serversplit=2
                urlsplit=3
            else:
                serversplit=0
                urlsplit=1

            server=url.split('/')[serversplit]
            urlPath="/"+"/".join(url.split('/')[urlsplit:])

            conn = httplib.HTTPConnection(server, timeout=20)
            head = {"Accept-Encoding" : "gzip", "Accept-Charset" : "UTF-8,*", "X-MediaBrowser-Token" : self.addonSettings.getSetting('AccessToken')} 
            #head = getAuthHeader()
            conn.request(method=type, url=urlPath, headers=head)
            #conn.request(method=type, url=urlPath)
            data = conn.getresponse()
            self.logMsg("GET URL HEADERS : " + str(data.getheaders()), level=2)
            link = ""
            contentType = "none"
            if int(data.status) == 200:
                retData = data.read()
                contentType = data.getheader('content-encoding')
                self.logMsg("Data Len Before : " + str(len(retData)))
                if(contentType == "gzip"):
                    retData = StringIO.StringIO(retData)
                    gzipper = gzip.GzipFile(fileobj=retData)
                    link = gzipper.read()
                else:
                    link = retData

            elif ( int(data.status) == 301 ) or ( int(data.status) == 302 ):
                try: conn.close()
                except: pass
                return data.getheader('Location')

            elif int(data.status) >= 400:
                try: conn.close()
                except: pass
                return ""
            else:
                link = ""
        except Exception, msg:
            error = "[Titanskin] Unable to connect to " + str(server) + " : " + str(msg)
            raise
        else:
            try: conn.close()
            except: pass

        return link