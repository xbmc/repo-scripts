# *  Credits:
# *
# *  original Artist Slideshow Helper code by pkscuot
# *

import xbmc, xbmcaddon, xbmcvfs
import os, sys
if sys.version_info >= (2, 7):
    import json
    from collections import OrderedDict
else:
    import simplejson as json
    from resources.common.ordereddict import OrderedDict

from resources.common.fix_utf8 import smartUTF8
from resources.common.xlogger import Logger
from resources.common.fileops import checkDir, writeFile
from resources.common.transforms import itemHash

__addon__        = xbmcaddon.Addon()
__addonname__    = __addon__.getAddonInfo('id')
__addonversion__ = __addon__.getAddonInfo('version')
__addonpath__    = __addon__.getAddonInfo('path').decode('utf-8')
__addonicon__    = xbmc.translatePath('%s/icon.png' % __addonpath__ )
__language__     = __addon__.getLocalizedString

#this initiates the logger object, which helps log arbitrary data to the log file
lw = Logger('[Artist Slideshow Helper]')


class Main:
    def __init__( self ):
        command = 'XBMC.Notification(%s, %s, %s, %s)' % (smartUTF8(__language__(30300)), smartUTF8(__language__(30301)), 5000, smartUTF8(__addonicon__))
        xbmc.executebuiltin(command)
        self._init_vars()
        self._get_settings()
        self._make_dirs()
        if self.HASHLIST == 'false' and self.MIGRATE == 'false':
            command = 'XBMC.Notification(%s, %s, %s, %s)' % (smartUTF8(__language__(30350)), smartUTF8(__language__(30351)), 5000, smartUTF8(__addonicon__))
            xbmc.executebuiltin(command)
            return        
        if self.HASHLIST == 'true' and self.HASHLISTFOLDER:
            self._generate_hashlist()
        elif self.HASHLIST == 'true' and not self.HASHLISTFOLDER:
            command = 'XBMC.Notification(%s, %s, %s, %s)' % (smartUTF8(__language__(30340)), smartUTF8(__language__(30341)), 5000, smartUTF8(__addonicon__))
            xbmc.executebuiltin(command)
        if self.MIGRATE == 'true' and self.MIGRATEFOLDER:
            self._migrate()
        elif self.MIGRATE == 'true' and not self.MIGRATEFOLDER:
            command = 'XBMC.Notification(%s, %s, %s, %s)' % (smartUTF8(__language__(30320)), smartUTF8(__language__(30321)), 5000, smartUTF8(__addonicon__))
            xbmc.executebuiltin(command)


    def _generate_hashlist( self ):
        hashmap = self._get_artists_hashmap()
        hashmap_str = ''
        for key, value in hashmap.iteritems():
           hashmap_str = hashmap_str + value + '\t' + key + '\n'
        success, log_line = writeFile( hashmap_str, self.HASHLISTFILE )
        if success:
            message = __language__(30311)
            lw.log( log_line, xbmc.LOGDEBUG )
        else:
            message = __language__(30312)
            lw.log( 'unable to write has list file out to disk', xbmc.LOGDEBUG )
        command = 'XBMC.Notification(%s, %s, %s, %s)' % (smartUTF8(__language__(30310)), smartUTF8(message), 5000, smartUTF8(__addonicon__))
        xbmc.executebuiltin(command)


    def _get_artists_hashmap( self ):
        #gets a list of all the artists from XBMC
        hashmap = OrderedDict()
        response = xbmc.executeJSONRPC ( '{"jsonrpc":"2.0", "method":"AudioLibrary.GetArtists", "params":{"albumartistsonly":false, "sort":{"order":"ascending", "ignorearticle":true, "method":"artist"}},"id": 1}}' )
        try:
            artists_info = json.loads(response)['result']['artists']
        except (IndexError, KeyError, ValueError):
            artists_info = []
        except Exception, e:
            lw.log( 'unexpected error getting JSON back from XBMC', xbmc.LOGDEBUG )
            lw.log( e, xbmc.LOGDEBUG )
            artists_info = []
        if artists_info:
            for artist_info in artists_info:
            	artist_hash = itemHash( artist_info['artist'] )
                hashmap[artist_hash] = artist_info['artist']
            hashmap[itemHash( "Various Artists" )] = "Various Artists" 
        return hashmap


    def _get_settings( self ):
        self.HASHLIST = __addon__.getSetting( "hashlist" )
        if self.HASHLIST == 'true':
            self.HASHLISTFOLDER = __addon__.getSetting( "hashlist_path" ).decode('utf-8')
            lw.log( 'set hash list path to %s' % self.HASHLISTFOLDER, xbmc.LOGDEBUG )
            self.HASHLISTFILE = os.path.join( self.HASHLISTFOLDER, 'as_hashlist.txt' )
        self.MIGRATE = __addon__.getSetting( "migrate" )
        if self.MIGRATE == 'true':
            mtype = __addon__.getSetting( "migrate_type" )
            if mtype == '2':
                self.MIGRATETYPE = 'copy'
            elif mtype == '1':
                self.MIGRATETYPE = 'move'
            elif mtype == '0':
                self.MIGRATETYPE = 'test'
            lw.log( 'raw migrate type is %s, so migrate type is %s' % (mtype, self.MIGRATETYPE), xbmc.LOGDEBUG )
            if __addon__.getSetting( "migrate_path" ):
                self.MIGRATEFOLDER = __addon__.getSetting( "migrate_path" ).decode('utf-8')
                lw.log( 'set migrate folder to %s' % self.MIGRATEFOLDER, xbmc.LOGDEBUG )
            else:
                self.MIGRATEFOLDER = ''
                lw.log( 'no migration folder set', xbmc.LOGDEBUG )
            

    def _init_vars( self ):
        self.HASHLIST = ''
        self.HASHLISTFOLDER = ''
        self.HASHLISTFILE = ''
        self.MIGRATE = ''
        self.MIGRATETYPE = ''
        self.MIGRATEFOLDER = ''
        self.ASCACHEFOLDER = xbmc.translatePath( 'special://profile/addon_data/script.artistslideshow/ArtistSlideshow' ).decode('utf-8')


    def _make_dirs( self ):
        checkDir( xbmc.translatePath('special://profile/addon_data/%s' % __addonname__ ).decode('utf-8') )
        if self.HASHLISTFOLDER:
            checkDir( self.HASHLISTFOLDER )
        if self.MIGRATEFOLDER:
            checkDir( self.MIGRATEFOLDER )


    def _migrate( self ):
        lw.log( 'attempting to %s images from Artist Slideshow cache directory' % self.MIGRATETYPE, xbmc.LOGDEBUG )
        test_str = ''
        checkDir(self.MIGRATEFOLDER)
        hashmap = self._get_artists_hashmap()
        try:
            os.chdir( self.ASCACHEFOLDER )
            folders = os.listdir( self.ASCACHEFOLDER )
        except OSError:
            lw.log( 'no directory found: ' + self.ASCACHEFOLDER, xbmc.LOGDEBUG )
            return
        except Exception, e:
            lw.log( 'unexpected error while getting directory list', xbmc.LOGDEBUG )
            lw.log( e, xbmc.LOGDEBUG )
            return
        for folder in folders:
            try:
                artist_name = hashmap[folder]
            except KeyError:
                lw.log( 'no matching artist folder for: ' + folder, xbmc.LOGDEBUG )
                artist_name = ''
            except Exception, e:
                lw.log( 'unexpected error while finding matching artist for ' + folder, xbmc.LOGDEBUG )
                lw.log( e, xbmc.LOGDEBUG )
                artist_name = ''
            if artist_name and not (artist_name.find('/') != -1):
                old_folder = os.path.join( self.ASCACHEFOLDER, folder )
                new_folder = os.path.join( self.MIGRATEFOLDER, artist_name, 'extrafanart' )
                if self.MIGRATETYPE == 'copy' or self.MIGRATETYPE == 'move':
                    checkDir(new_folder)
                try:
                    os.chdir( old_folder )
                    files = os.listdir( old_folder )
                except OSError:
                    lw.log( 'no directory found: ' + old_folder, xbmc.LOGDEBUG )
                    return
                except Exception, e:
                    lw.log( 'unexpected error while getting file list', xbmc.LOGDEBUG )
                    lw.log( e, xbmc.LOGDEBUG )
                    return
                lw.log( '%s %s to %s' % (self.MIGRATETYPE, folder, new_folder), xbmc.LOGDEBUG )
                for file in files:
                    old_file = os.path.join(old_folder, file)
                    new_file = os.path.join(new_folder, file)
                    if self.MIGRATETYPE == 'move':
                        xbmcvfs.rename( old_file, new_file  )
                    elif self.MIGRATETYPE == 'copy':                
                        xbmcvfs.copy( old_file, new_file )
                    else:
                        test_str = test_str + old_file + ' to ' + new_file + '\n'
                if self.MIGRATETYPE == 'move':
                    xbmcvfs.rmdir ( old_folder )
        if self.MIGRATETYPE == 'test':
            success, logline = writeFile( test_str, os.path.join( self.MIGRATEFOLDER, '_migrationtest.txt' ) )
            lw.log( logline, xbmc.LOGDEBUG )
        command = 'XBMC.Notification(%s, %s, %s, %s)' % (smartUTF8(__language__(30330)), smartUTF8(__language__(30331)), 5000, smartUTF8(__addonicon__))
        xbmc.executebuiltin(command)


if ( __name__ == "__main__" ):
    lw.log('script version %s started' % __addonversion__)
    slideshow = Main()

lw.log('script stopped')