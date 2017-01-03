# *  Credits:
# *
# *  original Artist Slideshow Helper code by pkscuot
# *

from __future__ import division
import xbmc, xbmcaddon, xbmcvfs
from xbmcgui import DialogProgressBG
import os, platform, sys
if sys.version_info >= (2, 7):
    import json as _json
    from collections import OrderedDict as _ordereddict
else:
    import simplejson as _json
    from resources.common.ordereddict import OrderedDict as _ordereddict

from resources.common.fix_utf8 import smartUTF8
from resources.common.xlogger import Logger
from resources.common.fileops import checkPath, writeFile
from resources.common.transforms import itemHash

addon        = xbmcaddon.Addon()
addonname    = addon.getAddonInfo('id')
addonversion = addon.getAddonInfo('version')
addonpath    = addon.getAddonInfo('path').decode('utf-8')
addonicon    = xbmc.translatePath('%s/icon.png' % addonpath )
language     = addon.getLocalizedString
preamble     = '[Artist Slideshow Helper]'
logdebug     = addon.getSetting( "logging" ) 

lw = Logger( preamble=preamble, logdebug=logdebug )


class Main:
    def __init__( self ):
        self._init_vars()
        self._get_settings()
        self._make_dirs()
        if self.HASHLIST == 'false' and self.MIGRATE == 'false':
            command = 'XBMC.Notification(%s, %s, %s, %s)' % (smartUTF8(language(30350)), smartUTF8(language(30351)), 5000, smartUTF8(addonicon))
            xbmc.executebuiltin(command)
            return        
        if self.HASHLIST == 'true' and self.HASHLISTFOLDER:
            self._generate_hashlist()
        elif self.HASHLIST == 'true' and not self.HASHLISTFOLDER:
            command = 'XBMC.Notification(%s, %s, %s, %s)' % (smartUTF8(language(30340)), smartUTF8(language(30341)), 5000, smartUTF8(addonicon))
            xbmc.executebuiltin(command)
        if self.MIGRATE == 'true' and self.MIGRATEFOLDER:
            self._migrate()
        elif self.MIGRATE == 'true' and not self.MIGRATEFOLDER:
            command = 'XBMC.Notification(%s, %s, %s, %s)' % (smartUTF8(language(30320)), smartUTF8(language(30321)), 5000, smartUTF8(addonicon))
            xbmc.executebuiltin(command)


    def _generate_hashlist( self ):
        hashmap = self._get_artists_hashmap()
        hashmap_str = ''
        for key, value in hashmap.iteritems():
           hashmap_str = hashmap_str + value + '\t' + key + '\n'
        success, log_line = writeFile( hashmap_str, self.HASHLISTFILE )
        if success:
            lw.log( log_line )
            message = smartUTF8( language(30311) )
        else:
            lw.log( ['unable to write has list file out to disk'] )
            message = smartUTF8( language(30312) )


    def _get_artists_hashmap( self ):
        #gets a list of all the artists from XBMC
        pDialog = DialogProgressBG()
        pDialog.create( smartUTF8(language(32001)), smartUTF8(language(30301)) )
        hashmap = _ordereddict()
        response = xbmc.executeJSONRPC ( '{"jsonrpc":"2.0", "method":"AudioLibrary.GetArtists", "params":{"albumartistsonly":false, "sort":{"order":"ascending", "ignorearticle":true, "method":"artist"}},"id": 1}}' )
        try:
            artists_info = _json.loads(response)['result']['artists']
        except (IndexError, KeyError, ValueError):
            artists_info = []
        except Exception, e:
            lw.log( ['unexpected error getting JSON back from XBMC', e] )
            artists_info = []
        if artists_info:
            total = len( artists_info )
            count = 1
            for artist_info in artists_info:
                lw.log( ["getting hash for artist %s" % artist_info['artist']] )
            	artist_hash = itemHash( artist_info['artist'] )
                hashmap[artist_hash] = artist_info['artist']
                pDialog.update(int(100*(count/total)), smartUTF8( language(32001) ), smartUTF8( artist_info['artist'] ) )
                count += 1
            hashmap[itemHash( "Various Artists" )] = "Various Artists" 
        pDialog.close()
        return hashmap


    def _get_settings( self ):
        self.HASHLIST = addon.getSetting( "hashlist" )
        if self.HASHLIST == 'true':
            self.HASHLISTFOLDER = addon.getSetting( "hashlist_path" ).decode('utf-8')
            lw.log( ['set hash list path to %s' % self.HASHLISTFOLDER] )
            self.HASHLISTFILE = os.path.join( self.HASHLISTFOLDER, 'as_hashlist.txt' )
        self.MIGRATE = addon.getSetting( "migrate" )
        if self.MIGRATE == 'true':
            mtype = addon.getSetting( "migrate_type" )
            if mtype == '2':
                self.MIGRATETYPE = 'copy'
            elif mtype == '1':
                self.MIGRATETYPE = 'move'
            elif mtype == '0':
                self.MIGRATETYPE = 'test'
            lw.log( ['raw migrate type is %s, so migrate type is %s' % (mtype, self.MIGRATETYPE)] )
            if addon.getSetting( "migrate_path" ):
                self.MIGRATEFOLDER = addon.getSetting( "migrate_path" ).decode('utf-8')
                lw.log( ['set migrate folder to %s' % self.MIGRATEFOLDER] )
            else:
                self.MIGRATEFOLDER = ''
                lw.log( ['no migration folder set'] )
        self.ENABLEFUZZYSEARCH = addon.getSetting( "enable_fuzzysearch" )
        lw.log( ['fuzzy search is ' + self.ENABLEFUZZYSEARCH] )
        if self.ENABLEFUZZYSEARCH == 'true':
            pl = addon.getSetting( "storage_target" )
            lw.log( ['the target is ' + pl] )
            if pl == "0":
                self.ENDREPLACE = addon.getSetting( "end_replace" )
                self.ILLEGALCHARS = list( '<>:"/\|?*' )
            elif pl == "2":
                self.ENDREPLACE = '.'
                self.ILLEGALCHARS = [':']
            else:
                self.ENDREPLACE = '.'
                self.ILLEGALCHARS = [os.path.sep]
            self.ILLEGALREPLACE = addon.getSetting( "illegal_replace" )
        

    def _init_vars( self ):
        self.HASHLIST = ''
        self.HASHLISTFOLDER = ''
        self.HASHLISTFILE = ''
        self.MIGRATE = ''
        self.MIGRATETYPE = ''
        self.MIGRATEFOLDER = ''
        self.ASCACHEFOLDER = xbmc.translatePath( 'special://profile/addon_data/script.artistslideshow/ArtistSlideshow' ).decode('utf-8')


    def _make_dirs( self ):
        exists, loglines = checkPath( os.path.join( xbmc.translatePath('special://profile/addon_data/%s' % addonname ).decode('utf-8'), '' ) )
        lw.log( loglines )
        if self.HASHLISTFOLDER:
            exists, loglines = checkPath( self.HASHLISTFOLDER )
            lw.log( loglines )
        if self.MIGRATEFOLDER:
            exists, loglines = checkPath( self.MIGRATEFOLDER )
            lw.log( loglines )


    def _migrate( self ):
        lw.log( ['attempting to %s images from Artist Slideshow cache directory' % self.MIGRATETYPE] )
        test_str = ''
        hashmap = self._get_artists_hashmap()
        try:
            folders, throwaway = xbmcvfs.listdir( self.ASCACHEFOLDER )
        except OSError:
            lw.log( ['no directory found: ' + self.ASCACHEFOLDER] )
            return
        except Exception, e:
            lw.log( ['unexpected error while getting directory list', e] )
            return
        pDialog = DialogProgressBG()
        pDialog.create( smartUTF8(language(32003)), smartUTF8(language(30301)) )
        total = len( folders )
        count = 1
        for folder in folders:
            try:
                artist_start = hashmap[folder]
            except KeyError:
                lw.log( ['no matching artist folder for: ' + folder] )
                artist_start = ''
            except Exception, e:
                lw.log( ['unexpected error while finding matching artist for ' + folder, e] )
                artist_start = ''
            if artist_start:
                pDialog.update(int(100*(count/total)), smartUTF8( language(32003) ), smartUTF8( artist_start ) )
                if self.ENABLEFUZZYSEARCH == 'true':
                    artist_name = ''
                    lw.log( ['the illegal characters are ', self.ILLEGALCHARS, 'the replacement is ' + self.ILLEGALREPLACE] )
                    for c in list( self._remove_trailing_dot( artist_start ) ):
                        if c in self.ILLEGALCHARS:
                            artist_name = artist_name + self.ILLEGALREPLACE
                        else:
                            artist_name = artist_name + c  
                else:
                    artist_name = artist_start
                old_folder = os.path.join( self.ASCACHEFOLDER, folder )
                new_folder = os.path.join( self.MIGRATEFOLDER, artist_name, 'extrafanart' )
                if self.MIGRATETYPE == 'copy' or self.MIGRATETYPE == 'move':
                    exists, loglines = checkPath( new_folder )
                    
                    lw.log( loglines )
                try:
                    throwaway, files = xbmcvfs.listdir( old_folder )
                except OSError:
                    lw.log( ['no directory found: ' + old_folder] )
                    return
                except Exception, e:
                    lw.log( ['unexpected error while getting file list', e] )
                    return
                lw.log( ['%s %s to %s' % (self.MIGRATETYPE, folder, new_folder)] )
                for file in files:
                    old_file = os.path.join(old_folder, file)
                    new_file = os.path.join(new_folder, file)
                    if self.MIGRATETYPE == 'move':
                        xbmcvfs.copy( old_file, new_file  )
                        xbmcvfs.delete( old_file )
                    elif self.MIGRATETYPE == 'copy':                
                        xbmcvfs.copy( old_file, new_file )
                    else:
                        test_str = test_str + old_file + ' to ' + new_file + '\n'
                if self.MIGRATETYPE == 'move':
                    xbmcvfs.rmdir ( old_folder )
                count += 1
        if self.MIGRATETYPE == 'test':
            success, loglines = writeFile( test_str, os.path.join( self.MIGRATEFOLDER, '_migrationtest.txt' ) )
            lw.log( loglines )
        pDialog.close()


    def _remove_trailing_dot( self, thename ):
        if thename[-1] == '.' and len( thename ) > 1 and self.ENDREPLACE <> '.':
            return self._remove_trailing_dot( thename[:-1] + self.ENDREPLACE )
        else:
            return thename


if ( __name__ == "__main__" ):
    lw.log( ['script version %s started' % addonversion], xbmc.LOGNOTICE )
    lw.log( ['debug logging set to %s' % logdebug], xbmc.LOGNOTICE )
    Main()
    command = 'XBMC.Notification(%s, %s, %s, %s)' % (smartUTF8(language(30330)), smartUTF8(language(30331)), 3000, smartUTF8(addonicon))
    xbmc.executebuiltin( command )
lw.log( ['script stopped'], xbmc.LOGNOTICE )
