import sys
import os
import xbmc
import xbmcaddon
import re
import string
import urllib
import urllib2
from urllib2 import URLError

# disgracefully stolen from xbmc subtitles
try:
  # Python 2.6 +
  from hashlib import sha as sha
except ImportError:
  # Python 2.5 and earlier
  import sha

__settings__ = xbmcaddon.Addon(id='script.trakt')
__language__ = __settings__.getLocalizedString
__version__ = "0.0.9"
__cwd__ = __settings__.getAddonInfo('path')

#Path handling
LANGUAGE_RESOURCE_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'language' ) )
CONFIG_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'settings.cfg' ) )
AUTOEXEC_PATH = xbmc.translatePath( 'special://home/userdata/autoexec.py' )
AUTOEXEC_FOLDER_PATH = xbmc.translatePath( 'special://home/userdata/' )
VERSION_PATH = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'version.cfg' ) )

#Consts
AUTOEXEC_SCRIPT = '\nimport time;time.sleep(5);xbmc.executebuiltin("XBMC.RunScript(special://home/addons/script.trakt/default.py,-startup)")\n'

def SendUpdate(info, progress, sType, status):
    Debug("Creating data to send", False)
    
    bUsername = __settings__.getSetting( "Username" )
    bPassword = sha.new(__settings__.getSetting( "Password" )).hexdigest()
    bNotify = __settings__.getSetting( "NotifyOnSubmit" )
    
    
    if (bUsername == '' or bPassword == ''):
        Debug("Username or password not set", False)
        notification("Trakt", __language__(45051).encode( "utf-8", "ignore" ), 5000, __settings__.getAddonInfo("icon"))
        return False
    
    Debug(info, False)
    
    if (sType == "TVShow"):
        ID = getID(sType, unicode(xbmc.getInfoLabel("VideoPlayer.TvShowTitle"), 'utf-8'))
    elif (sType == "Movie"):
        ID = getID(sType, unicode(xbmc.getInfoLabel("VideoPlayer.Title")))
    
    # split on type and create data packet for each type
    if (sType == "Movie"):
        Debug("Parsing Movie", False)
        
        # format: title, year
        title, year, ID = info.split(",")
        
        # set alert text
        submitAlert = __language__(45052).encode( "utf-8", "ignore" )
        submitAlert = submitAlert.replace('%MOVIENAME%', title)
        submitAlert = submitAlert.replace('%YEAR%', year)
        
        toSend = urllib.urlencode({ "type": sType,
                                    "status": status,
                                    "title": title, 
                                    "year": year,
                                    "imdbid": ID,
                                    "progress": progress,
                                    "plugin_version": __version__,
                                    "media_center": 'xbmc',
                                    "media_center_version": xbmc.getInfoLabel( "system.buildversion" ),
                                    "media_center_date": xbmc.getInfoLabel( "system.builddate" ),
                                    "username": bUsername, 
                                    "password": bPassword})
    elif (sType == "TVShow"):
        Debug("Parsing TVShow", False)
        
        # format: title, year, season, episode
        title, year, season, episode, ID = info.split(",")
        
        # set alert text
        submitAlert = __language__(45053).encode( "utf-8", "ignore" )
        submitAlert = submitAlert.replace('%TVSHOW%', title)
        submitAlert = submitAlert.replace('%SEASON%', season)
        submitAlert = submitAlert.replace('%EPISODE%', episode)
        
        toSend = urllib.urlencode({ "type": sType,
                                    "status": status,
                                    "title": title, 
                                    "year": year, 
                                    "season": season, 
                                    "episode": episode,
                                    "tvdbid": ID,
                                    "progress": progress,
                                    "plugin_version": __version__,
                                    "media_center": 'xbmc',
                                    "media_center_version": xbmc.getInfoLabel( "system.buildversion" ),
                                    "media_center_date": xbmc.getInfoLabel( "system.builddate" ),
                                    "username": bUsername, 
                                    "password": bPassword})
        
    Debug("Data: "+toSend, False)
    
    # send
    transmit(toSend)
    # and notify if wanted
    if (bNotify == "true" and status == "watched"):
        notification("Trakt", submitAlert, 3000, __settings__.getAddonInfo("icon"))
    
def transmit(status):
    bNotify = __settings__.getSetting( "NotifyOnSubmit" )

    req = urllib2.Request("http://api.trakt.tv/post",
            status,
            headers = { "Accept": "*/*",   
                        "User-Agent": "Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)", 
                      })

    try:
        f = urllib2.urlopen(req)
        response = f.read()
        Debug("Return packet: "+response)
        
    except URLError, e:
        if e.code == 401:
            Debug("Bad username or password", False)
            if (bNotify == "true"):
                notification("Trakt: Bad Authentication!", "Check your login information", 5000, __settings__.getAddonInfo("icon"))
                
    except:
        # do nothing 'cept spit out error (catch all)
        if (bNotify == "true"):
            notification("Trakt", "Error sending status.  API may not be reachable", 10000, __settings__.getAddonInfo("icon"))


def Debug(message, Verbose=True):
    message = "TRAKT: " + message
    bVerbose = __settings__.getSetting( "debug" )
    if (bVerbose == 'true'):
        bVerbose = True
    else:
        bVerbose = False
    
    if (bVerbose and Verbose):
        # repr() is used, got wierd issues with unicode otherwise, since we send mixed string types (eg: unicode and ascii) 
        print repr(message)
    elif (not Verbose):
        # repr() is used, got wierd issues with unicode otherwise, since we send mixed string types (eg: unicode and ascii) 
        print repr(message)

def CalcPercentageRemaining(currenttime, duration):
    try:
         iCurrentMinutes = (int(currenttime.split(':')[0]) * 60) + int(currenttime.split(':')[1])
    except:
        iCurrentMinutes = int(0)
        
    try:
        iDurationMinutes = (int(duration.split(':')[0]) * 60) + int(duration.split(':')[1])
    except:
        iDurationMinutes = int(0)

    try:
        Debug( 'Percentage of progress: ' + str(float(iCurrentMinutes) / float(iDurationMinutes)), True)
        return float(iCurrentMinutes) / float(iDurationMinutes) 
    except:
        Debug( 'Percentage of progress: null', True)
        return float(0.0)

def SetAutoStart(bState = True):
    Debug( '::AutoStart::' + str(bState), True)
    if (os.path.exists(AUTOEXEC_PATH)):
        Debug( 'Found Autoexec.py file, checking we''re there', True)
        bFound = False
        autoexecfile = file(AUTOEXEC_PATH, 'r')
        filecontents = autoexecfile.readlines()
        autoexecfile.close()
        for line in filecontents:
            if line.find('trakt') > 0:
                Debug( 'Found our script, no need to do anything', True)
                bFound = True
        if (not bFound):
            Debug( 'Appending our script to the autoexec.py script', True)
            autoexecfile = file(AUTOEXEC_PATH, 'w')
            filecontents.append(AUTOEXEC_SCRIPT)
            autoexecfile.writelines(filecontents)            
            autoexecfile.close()
        if (bFound and not bState):
            #remove line
            Debug( 'Removing our script from the autoexec.py script', True)
            autoexecfile = file(AUTOEXEC_PATH, 'w')
            for line in filecontents:
                if not line.find('trakt') > 0:
                    autoexecfile.write(line)
            autoexecfile.close()            
    else:
        if (os.path.exists(AUTOEXEC_FOLDER_PATH)):
            Debug( 'File Autoexec.py is missing, creating file with autostart script', True)
            autoexecfile = file(AUTOEXEC_PATH, 'w')
            autoexecfile.write (AUTOEXEC_SCRIPT.strip())
            autoexecfile.close()
        else:
            Debug( 'Scripts folder is missing, creating folder and autoexec.py file with autostart script', True)
            os.makedirs(AUTOEXEC_FOLDER_PATH)
            autoexecfile = file(AUTOEXEC_PATH, 'w')
            autoexecfile.write (AUTOEXEC_SCRIPT.strip())
            autoexecfile.close()
    Debug( '::AutoStart::'  , True)

def notification( header="", message="", sleep=5000, icon=__settings__.getAddonInfo( "icon" ) ):
    """ Will display a notification dialog with the specified header and message,
        in addition you can set the length of time it displays in milliseconds and a icon image. 
    """
    xbmc.executebuiltin( "XBMC.Notification(%s,%s,%i,%s)" % ( header, message, sleep, icon ) )
    
def getID(sType, title):
    video_id = ""
    if (sType == "TVShow"):
        # get tvdb id
        try:
            query = "select c12 from tvshow where c00 = '" + title + "'"
            res = xbmc.executehttpapi("queryvideodatabase(" + query + ")")
            tvid = re.findall('[\d.]*\d+',res) # find it

            if len(tvid[0].strip()) >= 1:
                video_id = tvid[0].strip();
        except:        
            video_id = ""
    else:
        try:
            query = "select case when not movie.c09 is null then movie.c09 else 'NOTFOUND' end as [MovieID] from movie where movie.c00 = '" + title + "' limit 1"
            res = xbmc.executehttpapi("queryvideodatabase(" + query + ")")
            movieid = re.findall('>(.*?)<',res) # find it
            if len(movieid[1].strip()) >= 1:
                video_id = str(movieid[1].strip())
        except:
            video_id = ""
    
    return video_id