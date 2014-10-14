import xbmc
import xbmcgui
import xbmcaddon
import urllib
import urllib2
import httplib
import requests
import hashlib
import StringIO
import gzip
import sys
import json as json
from random import randrange
from uuid import getnode as get_mac

class DownloadUtils():

    logLevel = 0
    addonSettings = None
    getString = None

    def __init__(self, *args):  
        self.logLevel = 0
        self.addonSettings = xbmcaddon.Addon(id='plugin.video.xbmb3c')
        self.getString = self.addonSettings.getLocalizedString
        level = self.addonSettings.getSetting('logLevel')                

    def logMsg(self, msg, level = 1):
        if(self.logLevel >= level):
            xbmc.log("[Titanskin DownloadUtils] -> " + msg)      

    def getArtwork(self, data, type, index = "0"):

        id = data.get("Id")
        getseriesdata = False
        if type == "tvshow.poster": # Change the Id to the series to get the overall series poster
            if data.get("Type") == "Season" or data.get("Type")== "Episode":
                id = data.get("SeriesId")
                getseriesdata = True
        elif type == "poster" and data.get("Type") == "Episode" and self.addonSettings.getSetting('useSeasonPoster')=='true': # Change the Id to the Season to get the season poster
            id = data.get("SeasonId")
        if type == "poster" or type == "tvshow.poster": # Now that the Ids are right, change type to MB3 name
            type="Primary"
        if data.get("Type") == "Season":  # For seasons: primary (poster), thumb and banner get season art, rest series art
            if type != "Primary" and type != "Thumb" and type != "Banner":
                id = data.get("SeriesId")
                getseriesdata = True
        if data.get("Type") == "Episode":  # For episodes: primary (episode thumb) gets episode art, rest series art. 
            if type != "Primary":
                id = data.get("SeriesId")
                getseriesdata = True
        
        if getseriesdata == True:   
            mb3Host = self.addonSettings.getSetting('ipaddress')
            mb3Port = self.addonSettings.getSetting('port')    
            userid = self.getUserId()
            seriesJsonData = self.downloadUrl("http://" + mb3Host + ":" + mb3Port + "/mediabrowser/Users/" + userid + "/Items/" + id + "?format=json", suppress=False, popup=1 )     
            seriesResult = json.loads(seriesJsonData)
            data = seriesResult
        
        imageTag = ""
        originalType = type
        if type == "Primary2" or type == "Primary3" or type=="SeriesPrimary":
            type = "Primary"
        if type == "Backdrop2" or type=="Backdrop3":
            type = "Backdrop"
        if type == "Thumb2" or type=="Thumb3":
            type = "Thumb"
        if(data.get("ImageTags") != None and data.get("ImageTags").get(type) != None):
            imageTag = data.get("ImageTags").get(type)   

        #query = "&type=" + type + "&tag=" + imageTag
        query = ""
        height = "10000"
        width = "10000"
        played = "0"

        if self.addonSettings.getSetting('showIndicators')=='true': # add watched, unplayedcount and percentage played indicators to posters

            if (originalType =="Primary" or  originalType =="Backdrop") and data.get("Type") != "Episode":
                userData = data.get("UserData")
                if originalType =="Backdrop" and index == "0":
                  totalbackdrops = len(data.get("BackdropImageTags"))
                  if totalbackdrops != 0:
                    index = str(randrange(0,totalbackdrops))
                if userData != None:

                    UnWatched = 0 if userData.get("UnplayedItemCount")==None else userData.get("UnplayedItemCount")        

                    if UnWatched <> 0 and self.addonSettings.getSetting('showUnplayedIndicators')=='true':
                        query = query + "&UnplayedCount=" + str(UnWatched)


                    if(userData != None and userData.get("Played") == True and self.addonSettings.getSetting('showWatchedIndicators')=='true'):
                        query = query + "&AddPlayedIndicator=true"

                    PlayedPercentage = 0 if userData.get("PlayedPercentage")==None else userData.get("PlayedPercentage")
                    if PlayedPercentage == 0 and userData!=None and userData.get("PlayedPercentage")!=None :
                        PlayedPercentage = userData.get("PlayedPercentage")
                    if (PlayedPercentage != 100 or PlayedPercentage) != 0 and self.addonSettings.getSetting('showPlayedPrecentageIndicators')=='true':
                        #query = query + "&PercentPlayed=" + str(PlayedPercentage)
                        played = str(PlayedPercentage)

            elif originalType =="Primary2" and data.get("Type") != "Episode":
                userData = data.get("UserData") 
                if userData != None:

                    UnWatched = 0 if userData.get("UnplayedItemCount")==None else userData.get("UnplayedItemCount")        

                    if UnWatched <> 0 and self.addonSettings.getSetting('showUnplayedIndicators')=='true':
                        query = query + "&UnplayedCount=" + str(UnWatched)


                    if(userData != None and userData.get("Played") == True and self.addonSettings.getSetting('showWatchedIndicators')=='true'):
                        query = query + "&AddPlayedIndicator=true"

                    PlayedPercentage = 0 if userData.get("PlayedPercentage")==None else userData.get("PlayedPercentage")
                    if PlayedPercentage == 0 and userData!=None and userData.get("PlayedPercentage")!=None :
                        PlayedPercentage = userData.get("PlayedPercentage")
                    if (PlayedPercentage != 100 or PlayedPercentage) != 0 and self.addonSettings.getSetting('showPlayedPrecentageIndicators')=='true':
                        #query = query + "&PercentPlayed=" + str(PlayedPercentage)  
                        played = str(PlayedPercentage)
                        
                    #query = query + "&height=340&width=226"
                    height = "340"
                    width = "226"
            elif (originalType =="Primary3" and data.get("Type") != "Episode") or originalType == "SeriesPrimary":
                userData = data.get("UserData") 
                if userData != None:

                    UnWatched = 0 if userData.get("UnplayedItemCount")==None else userData.get("UnplayedItemCount")        

                    if UnWatched <> 0 and self.addonSettings.getSetting('showUnplayedIndicators')=='true':
                        query = query + "&UnplayedCount=" + str(UnWatched)


                    if(userData != None and userData.get("Played") == True and self.addonSettings.getSetting('showWatchedIndicators')=='true'):
                        query = query + "&AddPlayedIndicator=true"

                    PlayedPercentage = 0 if userData.get("PlayedPercentage")==None else userData.get("PlayedPercentage")
                    if PlayedPercentage == 0 and userData!=None and userData.get("PlayedPercentage")!=None :
                        PlayedPercentage = userData.get("PlayedPercentage")
                    if (PlayedPercentage != 100 or PlayedPercentage) != 0 and self.addonSettings.getSetting('showPlayedPrecentageIndicators')=='true':
                        #query = query + "&PercentPlayed=" + str(PlayedPercentage)  
                        played = str(PlayedPercentage)
                        
                    #query = query + "&height=600&width=400"
                    height = "800"
                    width = "550"                    
            elif type =="Primary" and data.get("Type") == "Episode":
                userData = data.get("UserData")
                if userData != None:

                    UnWatched = 0 if userData.get("UnplayedItemCount")==None else userData.get("UnplayedItemCount")        

                    if UnWatched <> 0 and self.addonSettings.getSetting('showUnplayedIndicators')=='true':
                        query = query + "&UnplayedCount=" + str(UnWatched)


                    if(userData != None and userData.get("Played") == True and self.addonSettings.getSetting('showWatchedIndicators')=='true'):
                        query = query + "&AddPlayedIndicator=true"

                    PlayedPercentage = 0 if userData.get("PlayedPercentage")==None else userData.get("PlayedPercentage")
                    if PlayedPercentage == 0 and userData!=None and userData.get("PlayedPercentage")!=None :
                        PlayedPercentage = userData.get("PlayedPercentage")
                    if (PlayedPercentage != 100 or PlayedPercentage) != 0 and self.addonSettings.getSetting('showPlayedPrecentageIndicators')=='true':
                        #query = query + "&PercentPlayed=" + str(PlayedPercentage)
                        played = str(PlayedPercentage)
                        
                    #query = query + "&height=225&width=400"
                    height = "410"
                    width = "770"                       
            elif originalType =="Backdrop2" or originalType =="Thumb2" and data.get("Type") != "Episode":
                userData = data.get("UserData")
                if originalType =="Backdrop2":
                  totalbackdrops = len(data.get("BackdropImageTags"))
                  if totalbackdrops != 0:
                    index = str(randrange(0,totalbackdrops))
                if userData != None:

                    UnWatched = 0 if userData.get("UnplayedItemCount")==None else userData.get("UnplayedItemCount")        

                    if UnWatched <> 0 and self.addonSettings.getSetting('showUnplayedIndicators')=='true':
                        query = query + "&UnplayedCount=" + str(UnWatched)


                    if(userData != None and userData.get("Played") == True and self.addonSettings.getSetting('showWatchedIndicators')=='true'):
                        query = query + "&AddPlayedIndicator=true"

                    PlayedPercentage = 0 if userData.get("PlayedPercentage")==None else userData.get("PlayedPercentage")
                    if PlayedPercentage == 0 and userData!=None and userData.get("PlayedPercentage")!=None :
                        PlayedPercentage = userData.get("PlayedPercentage")
                    if (PlayedPercentage != 100 or PlayedPercentage) != 0 and self.addonSettings.getSetting('showPlayedPrecentageIndicators')=='true':
                        #query = query + "&PercentPlayed=" + str(PlayedPercentage)  
                        played = str(PlayedPercentage)
                        
                    #query = query + "&height=270&width=480"
                    height = "270"
                    width = "480"      
            elif originalType =="Backdrop3" or originalType =="Thumb3" and data.get("Type") != "Episode":
                userData = data.get("UserData")
                if originalType =="Backdrop3":
                  totalbackdrops = len(data.get("BackdropImageTags"))
                  if totalbackdrops != 0:
                    index = str(randrange(0,totalbackdrops))
                if userData != None:

                    UnWatched = 0 if userData.get("UnplayedItemCount")==None else userData.get("UnplayedItemCount")        

                    if UnWatched <> 0 and self.addonSettings.getSetting('showUnplayedIndicators')=='true':
                        query = query + "&UnplayedCount=" + str(UnWatched)


                    if(userData != None and userData.get("Played") == True and self.addonSettings.getSetting('showWatchedIndicators')=='true'):
                        query = query + "&AddPlayedIndicator=true"

                    PlayedPercentage = 0 if userData.get("PlayedPercentage")==None else userData.get("PlayedPercentage")
                    if PlayedPercentage == 0 and userData!=None and userData.get("PlayedPercentage")!=None :
                        PlayedPercentage = userData.get("PlayedPercentage")
                    if (PlayedPercentage != 100 or PlayedPercentage) != 0 and self.addonSettings.getSetting('showPlayedPrecentageIndicators')=='true':
                        #query = query + "&PercentPlayed=" + str(PlayedPercentage)  
                        played = str(PlayedPercentage)
                        
                    #query = query + "&height=660&width=1180"
                    height = "900"
                    width = "1480"                        

        # use the local image proxy server that is made available by this addons service
        
        port = self.addonSettings.getSetting('port')
        host = self.addonSettings.getSetting('ipaddress')
        server = host + ":" + port
        
        artwork = "http://" + server + "/mediabrowser/Items/" + str(id) + "/Images/" + type + "/" + index + "/e3ab56fe27d389446754d0fb04910a34/original/" + height + "/" + width + "/" + played + "?" + query
        
        self.logMsg("getArtwork : " + artwork, level=2)
        
        # do not return non-existing images
        if ((type!="Backdrop" and imageTag=="") | (type=="Backdrop" and data.get("BackdropImageTags")!=None and len(data.get("BackdropImageTags")) == 0) | (type=="Backdrop" and data.get("BackdropImageTag")!=None and len(data.get("BackdropImageTag")) == 0)) :
            artwork=''        
        
        return artwork            

    def imageUrl(self, id, type, index, width, height):
    
        port = self.addonSettings.getSetting('port')
        host = self.addonSettings.getSetting('ipaddress')
        server = host + ":" + port
        
        return "http://" + server + "/mediabrowser/Items/" + str(id) + "/Images/" + type + "/" + str(index) + "/e3ab56fe27d389446754d0fb04910a34/original/" + str(height) + "/" + str(width) + "/0"
        
    def downloadUrl(self, url, suppress=False, type="GET", popup=0 ):
        self.logMsg("== ENTER: getURL ==")
        try:
            if url[0:4] == "http":
                serversplit=2
                urlsplit=3
            else:
                serversplit=0
                urlsplit=1

            server=url.split('/')[serversplit]
            urlPath="/"+"/".join(url.split('/')[urlsplit:])

            self.logMsg("url = " + url)
            self.logMsg("server = "+str(server), level=2)
            self.logMsg("urlPath = "+str(urlPath), level=2)
            conn = httplib.HTTPConnection(server, timeout=20)
            #head = {"Accept-Encoding" : "gzip,deflate", "Accept-Charset" : "UTF-8,*"} 
            if self.addonSettings.getSetting('AccessToken')==None:
                self.addonSettings.setSetting('AccessToken','')
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

                self.logMsg("Data Len After : " + str(len(link)))
                self.logMsg("====== 200 returned =======")
                self.logMsg("Content-Type : " + str(contentType))
                self.logMsg(link)
                self.logMsg("====== 200 finished ======")

            elif ( int(data.status) == 301 ) or ( int(data.status) == 302 ):
                try: conn.close()
                except: pass
                return data.getheader('Location')

            elif int(data.status) >= 400:
                error = "HTTP response error: " + str(data.status) + " " + str(data.reason)
                xbmc.log (error)
                if suppress is False:
                    if popup == 0:
                        xbmc.executebuiltin("XBMC.Notification(URL error: "+ str(data.reason) +",)")
                    else:
                        xbmcgui.Dialog().ok(self.getString(30135),server)
                xbmc.log (error)
                try: conn.close()
                except: pass
                return ""
            else:
                link = ""
        except Exception, msg:
            error = "Unable to connect to " + str(server) + " : " + str(msg)
            xbmc.log (error)
            xbmc.executebuiltin("XBMC.Notification(\"XBMB3C\": URL error: Unable to connect to server,)")
            xbmcgui.Dialog().ok("",self.getString(30204))
            raise
        else:
            try: conn.close()
            except: pass

        return link