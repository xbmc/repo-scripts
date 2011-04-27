"""
MyMediaDB XBMC Addon
Licensed under GPL3
"""

# Import statements
import sys
import os
import xbmc
import urllib2
from mymediadb.mmdb import MMDB
from mymediadb.xbmcapp import XBMCApp
from mymediadb.commonutils import debug,sleeper,addon
    
def remoteMovieExists(imdbId):
    for remoteMedia in mmdb_library:
        if(remoteMedia['imdbId'] == imdbId):
            return True
    return False

def movieUpdatedNotifications():
    global updatedMovies
    if(addon.getSetting('shownotifications') == 'true'):
        moviesUpdatedCounter= updatedMovies.__len__()
        del updatedMovies[:]
        if(moviesUpdatedCounter > 0):
            xbmc.executebuiltin('Notification(%s,%s,%s,%s)' % (addon.getAddonInfo('name'),"%d movies updated on MMDB" % (moviesUpdatedCounter),7000,addon.getAddonInfo("icon")))

#def periodicallyGetRemoteLibrary():
#    while (not xbmc.abortRequested):
#        sleeper(3600000) #1 hour
#        debug('perodically import of remote library initiated')
#        mmdb_library = getRemoteMovieLibrary()                 

def _setRemoteMovieTag(imdbId, postdata):
    global recentlyFailedMovies
    global updatedMovies
    
    try:
        if(imdbId not in recentlyFailedMovies):
            mmdb.setRemoteMovieTag(imdbId,postdata) 
            updatedMovies += [imdbId] ## adding to updated list
            return True
        else:
            debug('Movie was on failed list, and did not update')           
    except urllib2.URLError, e:
        if(e.code == 404):
            recentlyFailedMovies += [imdbId] #Adding movie to failed movies list,  these will not be updated next sync
            debug('Adding movie to failed list.')
            return False
    
def syncWithMMDB():
    #define global access
    global mmdb_library
    #sync remote media with local db
    if(mmdb_library == None):
        debug("mmdb_library = None, is api down/changed?")
        return
    anyRemoteChanges = False
    anyLocalChanges = False
    for remoteMedia in mmdb_library:
        if(remoteMedia['imdbId']) != None:
            localMedia = xbmcApp.getLocalMovie(remoteMedia['imdbId'])
            if (localMedia != None): 
                debug('Media exists both locally and remotely - ('+remoteMedia['name']+')')
                if not remoteMedia['acquired']:
                    debug('Setting remote media status to acquired')
                    _setRemoteMovieTag(remoteMedia['imdbId'],{'acquired':True})
                    anyRemoteChanges = True
                if(remoteMedia['experienced'] != localMedia['watched']):
                    debug('watched status is not synchronized')
                    if(addon.getSetting('dontsyncwatched') == 'false'):
                        if(remoteMedia['experienced']):
                            debug('setting local media to watched')
                            xbmcApp.setLocalMovieAsWatched(localMedia['idFile'])
                            anyLocalChanges = True
                        else:
                            debug ('setting remote media to watched')
                            _setRemoteMovieTag(localMedia['imdbId'],{'experienced':localMedia['watched'] == 1})
                            anyRemoteChanges = True
                    else:
                        debug('Cancelled synchronize of watched status due to settings!')
            else:
                debug('Media ('+remoteMedia['name']+') exists only remotely')
                if(remoteMedia['acquired'] == True):
                    if(addon.getSetting('dontdeleteacquired') == 'false'):
                        debug('Acquired flag was removed from mmdb')
                        _setRemoteMovieTag(remoteMedia['imdbId'],{'acquired':False})
                        anyRemoteChanges = True
                    else:
                        debug('Acquired flag was not removed from mmdb due to settings!')
        else:
            #MISSING IMDBID in REMOTE MOVIE
            debug('('+remoteMedia['name']+') was missing imdbID, please add it at TMDB.org')
      
    #sync local media with remote db
    for localMedia in xbmcApp.getLocalMovieLibrary():
        if(remoteMovieExists(localMedia['imdbId'])):
            continue
        debug('Media exists only locally - ('+localMedia['name']+')')
        if(_setRemoteMovieTag(localMedia['imdbId'],{'acquired': True, 'experienced':localMedia['watched'] == 1})):
            anyRemoteChanges = True  #if it _setRemoteMovieTag fails doesnt set: anyRemoteChanges
    
    
    movieUpdatedNotifications()     
    if(anyRemoteChanges):
        debug('--- MADE REMOTE UPDATE(S) ---')
        mmdb_library = mmdb.getRemoteMovieLibrary() #sync local copy with changes on remote
    elif(anyLocalChanges):
        debug('--- MADE LOCAL CHANGE(S)  ---')
    else:
        debug('--- NO CHANGES DETECTED ---')
    

# Constants
mmdb = MMDB(addon.getSetting('username'),addon.getSetting('password'))
xbmcApp = XBMCApp(xbmc.translatePath('special://database/%s' % addon.getSetting('database')))

# Globals
mmdb_library = []
recentlyFailedMovies = []
updatedMovies = []
# autoexecute addon on startup for older xbmc versions, remove this when xbmc.service goes live
# Auto exec info
AUTOEXEC_PATH = xbmc.translatePath( 'special://home/userdata/autoexec.py' )
AUTOEXEC_FOLDER_PATH = xbmc.translatePath( 'special://home/userdata/' )
AUTOEXEC_SCRIPT = '\nimport time;time.sleep(5);xbmc.executebuiltin("XBMC.RunScript(special://home/addons/%s/default.py)")\n' % addon.getAddonInfo('id')
# See if the autoexec.py file exists
if (os.path.exists(AUTOEXEC_PATH)):
    debug('Found autoexec')
    
    # Var to check if we're in autoexec.py
    found = False
    autostart = addon.getSetting('autostart') == 'true'
    autoexecfile = file(AUTOEXEC_PATH, 'r')
    filecontents = autoexecfile.readlines()
    autoexecfile.close()
    
    # Check if we're in it
    for line in filecontents:
        if line.find(addon.getAddonInfo('id')) > 0:
            debug('Found ourselves in autoexec')
            found = True
    
    # If the autoexec.py file is found and we're not in it,
    if (not found and autostart):
        debug('Adding ourselves to autoexec.py')
        autoexecfile = file(AUTOEXEC_PATH, 'w')
        filecontents.append(AUTOEXEC_SCRIPT)
        autoexecfile.writelines(filecontents)            
        autoexecfile.close()
    
    # Found that we're in it and it's time to remove ourselves
    if (found and not autostart):
        debug('Removing ourselves from autoexec.py')
        autoexecfile = file(AUTOEXEC_PATH, 'w')
        for line in filecontents:
            if not line.find(addon.getAddonInfo('id')) > 0:
                autoexecfile.write(line)
        autoexecfile.close()

else:
    debug('autoexec.py doesnt exist')
    if (os.path.exists(AUTOEXEC_FOLDER_PATH)):
        debug('Creating autoexec.py with our autostart script')
        autoexecfile = file(AUTOEXEC_PATH, 'w')
        autoexecfile.write (AUTOEXEC_SCRIPT.strip())
        autoexecfile.close()
    else:
        debug('Scripts folder missing, creating autoexec.py in that new folder with our script')
        os.makedirs(AUTOEXEC_FOLDER_PATH)
        autoexecfile = file(AUTOEXEC_PATH, 'w')
        autoexecfile.write (AUTOEXEC_SCRIPT.strip())
        autoexecfile.close()


try:
    # Print addon information
    print "[ADDON] '%s: version %s' initialized!" % (addon.getAddonInfo('name'), addon.getAddonInfo('version'))
    if(addon.getSetting('shownotifications') == 'true'):
        xbmc.executebuiltin('Notification(%s,%s,%s,%s)' % (addon.getAddonInfo('name'),'is running!',3000,addon.getAddonInfo("icon")))
    
    # Main logic
    debug('initial import of mmdb library')
    mmdb_library = mmdb.getRemoteMovieLibrary() #initial fetch    
            
    #thread.start_new_thread(periodicallyGetRemoteLibrary,())    Removed because python error
    syncWithMmdbRunsCounter= 0
    
    while (not xbmc.abortRequested):
        syncWithMMDB()       
        sleeper(300000) #5minutes
        syncWithMmdbRunsCounter += 1
        if(syncWithMmdbRunsCounter == 12): #60minutes
            del recentlyFailedMovies[:]   # Will clear the failedmovies list, since we now got a newer remote medialibrary
            mmdb_library = mmdb.getRemoteMovieLibrary()
            debug('Scheduled import of mmdb library')
            GRLCounter = 0
            
except urllib2.URLError, e:
    if(e.code == 401):
        xbmc.executebuiltin('Notification(%s,%s,%s,%s)' % (addon.getAddonInfo('name'),e,3000,addon.getAddonInfo("icon")))
except Exception, e:
        xbmc.executebuiltin('Notification(%s,%s,%s,%s)' % (addon.getAddonInfo('name'),'Error: %s' %e,5000,addon.getAddonInfo("icon")))
        #xbmc.executebuiltin('Notification(%s,%s,%s,%s)' % (addon.getAddonInfo('name'),"An error occured.. check the logs! exiting!",3000,addon.getAddonInfo("icon")))
        debug(e)
        sleeper(5000)
        sys.exit(1)