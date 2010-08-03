__scriptname__    = "cdART Single Shot script"
__scriptID__      = "script.cdart"
__author__        = "Giftie"
__version__       = "1.0.0"
__credits__       = "Ppic, Reaven, Imaginos"
__XBMC_Revision__ = "32000"
__date__          = "01-08-10"

import urllib
import sys
import os
import unicodedata
import re
from traceback import print_exc
import xbmcgui
import xbmcaddon
import xbmc
import socket
import shutil
from pysqlite2 import dbapi2 as sqlite3
from string import maketrans
#time socket out at 30 seconds
socket.setdefaulttimeout(30)

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( os.getcwd(), 'resources' ) )
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ))

from convert import set_entity_or_charref
from convert import translate_string

__language__ = xbmcaddon.Addon(__scriptID__).getLocalizedString

intab = ""
outtab = ""
transtab = maketrans(intab, outtab)
artist_url = "http://www.xbmcstuff.com/music_scraper.php?&id_scraper=65DFdfsdfgvfd6v8&t=artists"
album_url = "http://www.xbmcstuff.com/music_scraper.php?&id_scraper=65DFdfsdfgvfd6v8&t=cdarts"
cross_url = "http://www.xbmcstuff.com/music_scraper.php?&id_scraper=65DFdfsdfgvfd6v8&t=cross"
addon_work_folder = os.path.join(xbmc.translatePath( "special://profile/addon_data/" ), "script.cdartmanager")
addon_db = os.path.join(addon_work_folder, "l_cdart.db")
pDialog = xbmcgui.DialogProgress()
__useragent__  = "Mozilla/5.0 (Windows; U; Windows NT 5.1; fr; rv:1.9.0.1) Gecko/2008070208 Firefox/3.0.1"


CHAR_REPLACEMENT = {
    # latin-1 characters that don't have a unicode decomposition
    0xc6: u"AE", # LATIN CAPITAL LETTER AE
    0xd0: u"D",  # LATIN CAPITAL LETTER ETH
    0xd8: u"OE", # LATIN CAPITAL LETTER O WITH STROKE
    0xde: u"Th", # LATIN CAPITAL LETTER THORN
    0xdf: u"ss", # LATIN SMALL LETTER SHARP S
    0xe6: u"ae", # LATIN SMALL LETTER AE
    0xf0: u"d",  # LATIN SMALL LETTER ETH
    0xf8: u"oe", # LATIN SMALL LETTER O WITH STROKE
    0xfe: u"th", # LATIN SMALL LETTER THORN
    }

##
# Translation dictionary.  Translation entries are added to this
# dictionary as needed.

class unaccented_map(dict):
    ##
    # Maps a unicode character code (the key) to a replacement code
    # (either a character code or a unicode string).
    def mapchar(self, key):
        ch = self.get(key)
        if ch is not None:
            return ch
        de = unicodedata.decomposition(unichr(key))
        if de:
            try:
                ch = int(de.split(None, 1)[0], 16)
            except (IndexError, ValueError):
                ch = key
        else:
            ch = CHAR_REPLACEMENT.get(key, key)
        self[key] = ch
        return ch

class Main:

    def __init__( self ):
        #RunScript(script.cdart,$INFO[ListItem.Artist],$INFO[ListItem.Album],$INFO[ListItem.Path])
        #   argv[1] = Artist Name
        #   argv[2] = Album Title
        #   argv[3] = Album Path
        artist = sys.argv[ 1 ]
        album = sys.argv[ 2 ]
        path = sys.argv[ 3 ]
        self.start_script( artist, album, path ) 
    
    def get_html_source( self , url ):
        """ fetch the html source """
        error = 0
        class AppURLopener(urllib.FancyURLopener):
            version = __useragent__
        urllib._urlopener = AppURLopener()
        for i in range(0, 4):
            try:
                urllib.urlcleanup()
                sock = urllib.urlopen( url )
                htmlsource = sock.read()
                sock.close()
                break
            except:
                print_exc()
                print "# !!Unable to open page %s" % url
                error = 1
                print "# get_html_source error: %s" % error
        if not error == 0:
            return ""
        else:
            return htmlsource


    def remove_special( self, temp ):
        return temp.translate(transtab, "!@#$^*()?[]{}<>',./")
    

    #search xbmcstuff.com for similar artists if an artist match is not made
    #between local artist and distant artist
    def search( self , name ):
        print "#  Search Artist based on name: %s" % name
        error = 0
        select = None
        artist_album_list = []
        search_list = []
        search_dialog = []
        name = str.lower(name)
        search_name = self.remove_special( name )
        search_name = search_name.replace("-", " ") # break up name if hyphens are present
        for part in search_name.split(" "):
            search_xml = str.lower(self.get_html_source( cross_url + "&artist=%s" % urllib.quote_plus(part)) )
            if search_xml =="":
                error = 1
                break
            else:
                #print cross_url + cross_url + "&artist=%s" % part 
                #print search_xml
                match = re.search('<message>(.*?)</message>', search_xml )    
                if match:
                    print "#          Artist(part name): %s  not found on xbmcstuff.com" % part
                elif len(part) == 1 or part in ["the","le","de"]:
                    pass
                else: 
                    raw = re.compile( "<cdart>(.*?)</cdart>", re.DOTALL ).findall(search_xml)
                    for i in raw:
                        album = {}
                        album["local_name"] = name
                        match = re.search( "<artist>(.*?)</artist>", i )
                        if match:
                            album["artist"] = set_entity_or_charref((match.group(1).replace("&amp;", "&")).replace("'",""))
                            #print "#               Artist Matched: %s" % album["artist"]
                        else:
                            album["artist"] = ""
                        if not album["artist"] in search_dialog:
                            search_dialog.append(album["artist"])                    
                        match = re.search( "<album>(.*?)</album>", i )
                        if match:
                            album["title"] = (match.group(1).replace("&amp;", "&")).replace("'","")
                        else:
                            album["title"] = ""
                        #print "#                         Album Title: %s" % album["title"]
                        match = re.search( "<thumb>(.*?)</thumb>", i )
                        if match:
                            album["thumb"] = (match.group(1))
                        else:
                            album["thumb"] = ""
                        #print "#                         Album Thumb: %s" % album["thumb"]                        
                        match = re.search( "<picture>(.*?)</picture>", i )
                        if match:
                            album["picture"] = (match.group(1))
                        else:
                            album["picture"] = ""                    
                        #print "#                         Album cdART: %s" % album["picture"]
                        search_list.append(album)            
            if search_dialog: 
                select = xbmcgui.Dialog().select( __language__(32032), search_dialog)
                #Onscreen Select Menu
                print select
            if not select == -1:
                for item in search_list : 
                    if item["artist"] == search_list[select]["artist"]:
                        artist_album_list.append(item)
                return artist_album_list    
            else:
                if error == 1:
                    xbmcgui.Dialog().ok( __language__(32066) )
                    #Onscreen Dialog - Error connecting to XBMCSTUFF.COM, Socket Timed out
                else:
                    xbmcgui.Dialog().ok( __language__(32033), "%s %s" % ( __language__(32034), name) )
                    #Onscreen Dialog - Not Found on XBMCSTUFF.COM, No cdART found for 

    
    def find_match( self , distant_artist , artist ):
        print "#  Finding Artist Match from XBMCSTUFF.COM"
        name = ""
        name = str.lower( artist )
        match = re.search('<artist id="(.*?)">%s</artist>' % str.lower( re.escape(name) ), distant_artist )
        if match: 
            distant_id = match.group(1)
        else:
            s_name = name
            if (s_name.split(" ")[0]) == "the":
                s_name = s_name.replace("the ", "") # Try removing 'the ' from the name
            match = re.search('<artist id="(.*?)">%s</artist>' % re.escape( s_name ), distant_artist )
            if match: 
                distant_id = match.group(1)
            else:
                s_name = s_name.replace("&","&amp;") #Change any '&' to '&amp;' - matches xbmcstuff.com's format
                match = re.search('<artist id="(.*?)">%s</artist>' % re.escape( s_name ), distant_artist )
                if match: 
                    distant_id = match.group(1)
                else:
                    s_name = self.remove_special( s_name ) #remove punctuation and other special characters
                    match = re.search('<artist id="(.*?)">%s</artist>' % re.escape(s_name), distant_artist )
                    if match: 
                        distant_id = match.group(1)
                    else:    
                        distant_id =  ""
        if distant_id == "":
            print "#  No Matches found.  Compare Artist and Album names with xbmcstuff.com"
        return distant_id

    def get_matched_albumlist( self, distant_id, artist ):
        match = ""
        album_list = []
        artist_xml = self.get_html_source( album_url + "&id_artist=%s" % distant_id )
        raw = re.compile( "<cdart (.*?)</cdart>", re.DOTALL ).findall(artist_xml)
        for i in raw:
            album = {}
            album["artistd_id"] = distant_id
            album["local_name"] = album["artist"] = artist
            match = re.search('album="(.*?)">', i )
            #search for album title match, if found, store in album["title"], if not found store empty space
            if match:
                album["title"] = (match.group(1).replace("&amp;", "&"))              
                #print "#               Distant Album: %s" % album["title"]
            else:
                album["title"] = ""
            match = re.search( "<picture>(.*?)</picture>", i )
            #search for album cdart match, if found, store in album["picture"], if not found store empty space
            if match:
                album["picture"] = (match.group(1))                
            else:
                album["picture"] = ""
            #print "#                    cdART picture: %s" % album["picture"]
            album_list.append(album)
        return album_list

    def download_cdart( self, url_cdart , path, title ):
        print "#  Url: %s" % url_cdart
        print "#  path: %s" % path
        print "#  Album: %s" % title
        destination = os.path.join( path.replace("\\\\" , "\\") , "cdart.png") 
        download_success = 0
        pDialog.create(__language__(32047) )
        #Onscreen Dialog - "Downloading...."
        try:
            #this give the ability to use the progress bar by retrieving the downloading information
            #and calculating the percentage
            def _report_hook( count, blocksize, totalsize ):
                percent = int( float( count * blocksize * 100 ) / totalsize )
                strProgressBar = str( percent )
                pDialog.update( percent,__language__(32035) )
                #Onscreen Dialog - *DOWNLOADING CDART*
                if ( pDialog.iscanceled() ):
                    pass  
            if os.path.exists( path ):
                fp, h = urllib.urlretrieve(url_cdart, destination, _report_hook)
                message = [__language__(32023), __language__(32024), "File: %s" % path , "Url: %s" % url_cdart]
                #message = ["Download Sucessful!"]
                download_success = 1
            else:
                message = [ __language__(32026),  __language__(32025) , "File: %s" % path , "Url: %s" % url_cdart]
                #message = Download Problem, Check file paths - cdART Not Downloaded]           
            if ( pDialog.iscanceled() ):
                pDialog.close()            
        except:
            message = [ __language__(32026), __language__(32025), "File: %s" % path , "Url: %s" % url_cdart]
            #message = [Download Problem, Check file paths - cdART Not Downloaded]           
            print_exc()
        if download_success == 1 and os.path.isfile(addon_db):  #If cdART Manager's db is located add the info to db
            conn = sqlite3.connect(addon_db)
            c = conn.cursor()
            c.execute('''UPDATE alblist SET cdart="TRUE" WHERE title="%s"''' % title )
            conn.commit()
            c.close()
        pDialog.close()
        return message, download_success  # returns one of the messages built based on success or lack of

    def start_script(self, artist, original_album, path):
        albums = {}
        album_search=[]
        album_selection=[]
        select = None
        pDialog.create(__language__(32027) )
        message = [ "No Matches Found", "Why not try your hand at creating one", "And submit it to XBMCSTUFF.COM", ""]
        print "#  Artist: %s" % artist
        print "#  Album: %s" % original_album
        print "#  Path: %s" % path
        path_match = re.search( ".*(CD \d|CD\d|Disc\d|Disc \d)." , path, re.I)
        title_match = re.search( ".*(CD \d|CD\d|Disc\d|Disc \d)" , original_album, re.I)
        if title_match:
            print "#     Title has CD count"
            album = original_album
        else:
            if path_match:
                print "#     Path has CD count"
                print "#        %s" % path_match.group(1)
                album = "%s - %s" % (original_album, path_match.group(1))
                print "#     New Album Title: %s" % album
            else:
                album = original_album
        distant_artist = str.lower(self.get_html_source( artist_url ))
        if not distant_artist == "":
            distant_id = self.find_match( distant_artist , artist )
        if distant_id == "":#If no direct match found open search dialog
            album_list = self.search( artist )
        else: #Match found, get album list
            album_list = self.get_matched_albumlist( distant_id, artist )
        print album_list
        if not album_list:
            #no cdart found
            xbmcgui.Dialog().ok( __language__(32033), __language__(32030), __language__(32031) )
            #Onscreen Dialog - Not Found on XBMCSTUFF.COM, Please contribute! Upload your cdARTs, On www.xbmcstuff.com
        else: #if album list is not empty
            for part in album_list:
                remote_title = str.lower( part["title"] )
                if remote_title == str.lower( album ):
                    message, download_success = self.download_cdart( part["picture"], path, original_album )
                    break
                else:
                    download_success = 0
            if download_success == 1:
                xbmcgui.Dialog().ok(message[0] ,message[1] ,message[2] ,message[3])
                pDialog.close()
                
            else:
                for elem in album_list:
                    albums["search_name"] = elem["title"]
                    albums["search_url"] = elem["picture"]
                    album_search.append(albums["search_name"])
                    album_selection.append(albums["search_url"])
                select = xbmcgui.Dialog().select( __language__(32022), album_search)
                #print select
                if not select == -1:
                    picture = album_selection[select]
                    message, download_success = self.download_cdart( picture, path, original_album )
                    xbmcgui.Dialog().ok(message[0] ,message[1] ,message[2] ,message[3])
                    pDialog.close()
                else:
                    xbmcgui.Dialog().ok( __language__(32033), __language__(32030), __language__(32031) )
                    #Onscreen Dialog - Not Found on XBMCSTUFF.COM, Please contribute! Upload your cdARTs, On www.xbmcstuff.com
                    pDialog.close()
    

if ( __name__ == "__main__" ):
    print "############################################################"
    print "#    %-50s    #" % __scriptname__
    print "#    %-50s    #" % __scriptID__
    print "#    %-50s    #" % __author__
    print "#    %-50s    #" % __version__
    print "############################################################"
    Main()
    
            
            
    
