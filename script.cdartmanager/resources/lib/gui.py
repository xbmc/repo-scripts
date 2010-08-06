#to do:
# -  
# -  *add comments showing what local strings are being displayed   _(32002) = Search Artist
# -  add log printing
# -  insure mouse use works properly - at the moment it seems to break everything!
# -  add save local cdART list, showing which album have or don't have cdARTs
# -  add user input(ie keyboard) to get more advanced searches
# -  add database update for any downloads
#        many need to read local database(l_cdart - lalist) to find local id #'s
#        then write to l_cdart - alblist with the important information
#

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
from PIL import Image
from string import maketrans
#time socket out at 30 seconds
socket.setdefaulttimeout(30)



KEY_BUTTON_BACK = 275
KEY_KEYBOARD_ESC = 61467

# pull information from default.py
_              = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__scriptID__   = sys.modules[ "__main__" ].__scriptID__
__version__    = sys.modules[ "__main__" ].__version__
__settings__   = sys.modules[ "__main__" ].__settings__
__useragent__  = "Mozilla/5.0 (Windows; U; Windows NT 5.1; fr; rv:1.9.0.1) Gecko/2008070208 Firefox/3.0.1"

BASE_RESOURCE_PATH = xbmc.translatePath( os.path.join( os.getcwd(), 'resources' ) )

sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
from convert import set_entity_or_charref
from convert import translate_string

#variables
intab = ""
outtab = ""
transtab = maketrans(intab, outtab)
musicdb_path = os.path.join(xbmc.translatePath( "special://profile/Database/" ), "MyMusic7.db")
artist_url = "http://www.xbmcstuff.com/music_scraper.php?&id_scraper=65DFdfsdfgvfd6v8&t=artists"
album_url = "http://www.xbmcstuff.com/music_scraper.php?&id_scraper=65DFdfsdfgvfd6v8&t=cdarts"
cross_url = "http://www.xbmcstuff.com/music_scraper.php?&id_scraper=65DFdfsdfgvfd6v8&t=cross"
addon_work_folder = os.path.join(xbmc.translatePath( "special://profile/addon_data/" ), __scriptID__)
addon_db = os.path.join(addon_work_folder, "l_cdart.db")
addon_image_path = os.path.join( BASE_RESOURCE_PATH, "skins", "Default", "media")
addon_img = os.path.join( addon_image_path , "cdart-icon.png" )
pDialog = xbmcgui.DialogProgress()

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

    #if sys.version >= "2.5":
    #    # use __missing__ where available
    #    __missing__ = mapchar
    #else:
        # otherwise, use standard __getitem__ hook (this is slower,
        # since it's called for each character)
    __getitem__ = mapchar



class GUI( xbmcgui.WindowXMLDialog ):
    def __init__( self, *args, **kwargs ):    	
        pass


    def onInit( self ):
        self.setup_colors()       
	self.setup_all()

    def setup_colors( self ):
        if __settings__.getSetting("enablecustom")=="true":
            self.recognized_color = str.lower(__settings__.getSetting("recognized"))
            self.unrecognized_color = str.lower(__settings__.getSetting("unrecognized"))
            self.remote_color = str.lower(__settings__.getSetting("remote"))
            self.local_color = str.lower(__settings__.getSetting("local"))
            self.remotelocal_color = str.lower(__settings__.getSetting("remotelocal"))
            self.unmatched_color = str.lower(__settings__.getSetting("unmatched"))
            self.localcdart_color = str.lower(__settings__.getSetting("localcdart"))
        else:
            self.recognized_color = "green"
            self.unrecognized_color = "white"
            self.remote_color = "green"
            self.local_color = "orange"
            self.remotelocal_color = "yellow"
            self.unmatched_color = "white"
            self.localcdart_color = "orange"
        print self.recognized_color
        print self.unrecognized_color
        print self.remote_color
        print self.local_color
        print self.remotelocal_color
        print self.unmatched_color
        print self.localcdart_color
            

    def remove_special( self, temp ):
        return temp.translate(transtab, "!@#$^*()?[]{}<>',./")
    
    # sets the colours for the lists
    def coloring( self , text , color , colorword ):
        if color == "white":
            color="FFFFFFFF"
        if color == "blue":
            color="FF0000FF"
        if color == "cyan":
            color="FF00FFFF"
        if color == "violet":
            color="FFEE82EE"
        if color == "pink":
            color="FFFF1493"
        if color == "red":
            color="FFFF0000"
        if color == "green":
            color="FF00FF00"
        if color == "yellow":
            color="FFFFFF00"
        if color == "orange":
            color="FFFF4500"
        colored_text = text.replace( colorword , "[COLOR=%s]%s[/COLOR]" % ( color , colorword ) )
        return colored_text

    def remove_color( self, text ):
        clean_text = (((text.replace("[/COLOR]","")).replace("[COLOR=FFFFFFFF]","")).replace("[COLOR=FF0000FF]","")).replace("[COLOR=FF00FFFF]","")
        clean_text = ((clean_text.replace("[COLOR=FFEE82EE]","")).replace("[COLOR=FFFF1493]","")).replace("[COLOR=FFFF0000]","")
        clean_text = ((clean_text.replace("[COLOR=FF00FF00]","")).replace("[COLOR=FFFFFF00]","")).replace("[COLOR=FFFF4500]","")
        return clean_text


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

    #retrieve local artist list from xbmc's music db
    def get_local_artist( self ):
        print "#  Retrieving Local Artist from XBMC's Music DB"
        conn_b = sqlite3.connect(musicdb_path)
        d = conn_b.cursor()
        d.execute('SELECT DISTINCT strArtist , idArtist FROM albumview WHERE strAlbum!=""')
        count = 1
        artist_list = []
        for item in d:
            #print item[0]
            artist = {}
            name = item[0].translate(unaccented_map())
            artist["name"]= ((repr(name).lstrip("'u")).rstrip("'")).strip('"')
            artist["local_id"]= item[1]
            artist_list.append(artist)
            count = count + 1
        d.close
        count = count - 1
        print "# Total Local Artists: %s" % count
        return artist_list, count

    def get_albums(self, local_id):
        #print "get_albums"
        path =""
        search_title = ""
        album_songview = []
        conn_b = sqlite3.connect(musicdb_path)
        d = conn_b.cursor()
        d.execute("""SELECT DISTINCT strAlbum, strPath FROM songview WHERE idArtist="%s" AND strAlbum !=''""" % local_id )
        #print d
        for l in d:
            album = {}
            album["title"]=(translate_string( repr(l[0]).lstrip("'u").strip('"').rstrip("'") )).replace('"','')
            #print "album %s" % album["title"]
            album["path"]=(repr(l[1]).lstrip("'u").rstrip("'")).replace('"','')
            #print album["path"]
            album_songview.append(album)
        if len(album_songview)==0:
            album = {}
            album["title"]=""
            album["path"]=""
            album_songview.append(album)
        d.close
        return album_songview
        
    
    #retrieve local albums based on artist's name from xbmc's db
    def get_local_album( self , artist, local_id):
        print "#  Retrieving Local Albums from XBMC's Music DB, based on artist id: %s" % local_id
        local_album_list = []
        album_albumview = []
        temp_albums = []
        album_songview = []
        conn_b = sqlite3.connect(musicdb_path)
        d = conn_b.cursor()
        d.execute("""SELECT DISTINCT strAlbum, idAlbum FROM albumview WHERE idArtist="%s" AND strAlbum !=''""" % local_id)
        #print d
        for item in d:
            albums = {}
            albums["title"] = (translate_string( repr(item[0]).lstrip("'u").strip('"').rstrip("'") )).replace('"','')
            album_albumview.append(albums)
        d.close
        album_songview = self.get_albums( local_id )
        if album_songview[0]["title"]=="":
            album = {}
            album["artist"] = ""
            album["artist_id"] = ""
            album["path"] = ""
            album["title"] = ""
            album["cdart"] = ""
            local_album_list.append(album)            
            return local_album_list
        else:    
            for item in album_albumview:
                title = item["title"]
                #print title
                for songview in album_songview:
                    if songview["title"] == title:
                        album = {}
                        album["artist"] = artist
                        album["artist_id"] = local_id
                        album["path"] = songview["path"]
                        #print album["artist"]
                        #print album["path"]
                        path_match = re.search( ".*(CD \d|CD\d|Disc\d|Disc \d)." , album["path"], re.I)
                        title_match = re.search( ".*(CD \d|CD\d|Disc\d|Disc \d)" , title, re.I)
                        if title_match:
                            print "#     Title has CD count"
                            album["title"] = title
                        else:
                            if path_match:
                                print "#     Path has CD count"
                                print "#        %s" % path_match.group(1)
                                album["title"] = "%s - %s" % (title, path_match.group(1))
                                print "#     New Album Title: %s" % album["title"]
                            else:
                                album["title"] = title
                
                        if os.path.isfile(os.path.join( album["path"] , "cdart.png").replace("\\\\" , "\\").encode("utf-8")):
                            album["cdart"] = "TRUE"
                        else :
                            album["cdart"] = "FALSE"
                        local_album_list.append(album)
            return local_album_list

            
    #match artists on xbmcstuff.com with local database    
    def get_recognized( self , distant_artist , l_artist ):
        print "#  Retrieving Recognized Artists from XBMCSTUFF.COM"
        true = 0
        count = 0
        name = ""
        artist_list = []
        recognized = []
        pDialog.create( _(32048) )
        #Onscreen dialog - Retrieving Recognized Artist List....
        for artist in l_artist:
            name = str.lower(artist["name"])
            match = re.search('<artist id="(.*?)">%s</artist>' % str.lower( re.escape(name) ), distant_artist )
            percent = int((float(count)/len(l_artist))*100)
            if match: 
                true = true + 1
                artist["distant_id"] = match.group(1)
                recognized.append(artist)
                artist_list.append(artist)
            else:
                s_name = name
                if (s_name.split(" ")[0]) == "the":
                    s_name = s_name.replace("the ", "") # Try removing 'the ' from the name
                match = re.search('<artist id="(.*?)">%s</artist>' % re.escape( s_name ), distant_artist )
                if match: 
                    true = true + 1
                    artist["distant_id"] = match.group(1)
                    recognized.append(artist)
                    artist_list.append(artist)
                else:
                    s_name = s_name.replace("&","&amp;") #Change any '&' to '&amp;' - matches xbmcstuff.com's format
                    match = re.search('<artist id="(.*?)">%s</artist>' % re.escape( s_name ), distant_artist )
                    if match: 
                        true = true + 1
                        artist["distant_id"] = match.group(1)
                        recognized.append(artist)
                        artist_list.append(artist)
                    else:
                        s_name = self.remove_special( s_name ) #remove punctuation and other special characters
                        match = re.search('<artist id="(.*?)">%s</artist>' % re.escape(s_name), distant_artist )
                        if match: 
                            true = true + 1
                            artist["distant_id"] = match.group(1)
                            recognized.append(artist)
                            artist_list.append(artist)
                        else:    
                            artist["distant_id"] = ""
                            artist_list.append(artist)
            pDialog.update(percent, (_(32049) % true))
            #Onscreen Dialog - Artists Matched: %
            count=count+1
            if ( pDialog.iscanceled() ):
                break
        print "#  Total Artists Matched: %s" % true
        if true == 0:
            print "#  No Matches found.  Compare Artist and Album names with xbmcstuff.com"
        pDialog.close()
        return recognized, artist_list
    
    #search xbmcstuff.com for similar artists if an artist match is not made
    #between local artist and distant artist
    def search( self , name, local_id):
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
                        album["artistl_id"] = local_id
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
                select = xbmcgui.Dialog().select( _(32032), search_dialog)
                #Onscreen Select Menu
                print select
            if not select == -1:
                for item in search_list : 
                    if item["artist"] == search_list[select]["artist"]:
                        artist_album_list.append(item)
                return artist_album_list    
            else:
                if error == 1:
                    xbmcgui.Dialog().ok( _(32066) )
                    #Onscreen Dialog - Error connecting to XBMCSTUFF.COM, Socket Timed out
                else:
                    xbmcgui.Dialog().ok( _(32033), "%s %s" % ( _(32034), name) )
                    #Onscreen Dialog - Not Found on XBMCSTUFF.COM, No cdART found for 
        return


    def cdart_search( self, cdart_url, title ):
        print "#  Searching for matching remote albums & cdARTs"
        s_title = ""
        rms_title = ""
        s_title = self.remove_special( title )
        cdart_find = {}
        for album in cdart_url:
            r_title1 = str.lower( album["title"] )
            r_title2 = str.lower( album["title"].split(" (")[0] )
            r_title3 = str.lower(self.remove_special( album["title"] ))
            r_title4 = str.lower(self.remove_special( album["title"].split(" (")[0] ))
            if title == r_title1 or title == r_title2 or title == r_title3 or title == r_title4 or s_title == r_title1 or s_title == r_title2 or s_title == r_title3 or s_title == r_title4:
                cdart_find = album
                break
            else:
                cdart_find["picture"]=""
                cdart_find["thumb"]=""
                cdart_find["title"]=""
                cdart_find["artistd_id"]=""
                cdart_find["artistl_id"]=""
                cdart_find["local_name"]=""
                cdart_find["artist_name"]=""
        return cdart_find        
    
    # finds the cdart for the album list    
    def find_cdart( self , aname , atitle, remote_cdart_url ):
        match = ""
        name = str.lower( aname )
        title = str.lower( atitle )
        for item in remote_cdart_url:
            if str.lower(item["title"])==title:
                return item["picture"]
        return match


    # finds the cdart for the album list    
    def find_cdart2( self , aname , atitle ):
        match = None
        name = str.lower( aname )
        title = str.lower( atitle )
        xml = self.get_html_source( cross_url + "&album=%s&artist=%s" % (urllib.quote_plus(title.replace("&", "&amp;")) , urllib.quote_plus(name.replace("&", "&amp;"))))
        match = re.search("<no_result", xml)
        if match:
            s_name = self.remove_special( name )
            s_title = self.remove_special( title )
            xml = self.get_html_source( cross_url + "&album=%s&artist=%s" % (urllib.quote_plus(s_title.replace("&", "&amp;")) , urllib.quote_plus(s_name.replace("&", "&amp;"))))
            if not xml == "":
                match = re.findall( "<picture>(.*?)</picture>", xml )
            else:
                print "# Error, xml= %s" % xml
                match = []
        elif not xml == "":
            match = re.findall( "<picture>(.*?)</picture>", xml )
        else:
            print "# Error, xml= %s" % xml
            match = []
        return match
    
        
    # downloads the cdart.  used from album list selections
    def download_cdart( self, url_cdart , album ):
        destination = os.path.join( album["path"].replace("\\\\" , "\\") , "cdart.png") 
        download_success = 0
        pDialog.create( _(32047) )
        #Onscreen Dialog - "Downloading...."
        conn = sqlite3.connect(addon_db)
        c = conn.cursor()
        try:
            #this give the ability to use the progress bar by retrieving the downloading information
            #and calculating the percentage
            def _report_hook( count, blocksize, totalsize ):
                percent = int( float( count * blocksize * 100 ) / totalsize )
                strProgressBar = str( percent )
                pDialog.update( percent, _(32035) )
                #Onscreen Dialog - *DOWNLOADING CDART*
                if ( pDialog.iscanceled() ):
                    pass  
            if os.path.exists(album["path"]):
                fp, h = urllib.urlretrieve(url_cdart, destination, _report_hook)
                message = [_(32023), _(32024), "File: %s" % album["path"] , "Url: %s" % url_cdart]
                #message = ["Download Sucessful!"]
                c.execute('''UPDATE alblist SET cdart="TRUE" WHERE title="%s"''' % album["title"])
                download_success = 1
            else:
                message = [ _(32026),  _(32025) , "File: %s" % album["path"] , "Url: %s" % url_cdart]
                #message = Download Problem, Check file paths - cdART Not Downloaded]           
            if ( pDialog.iscanceled() ):
                pDialog.close()            
        except:
            message = [ _(32026), _(32025), "File: %s" % album["path"] , "Url: %s" % url_cdart]
            #message = [Download Problem, Check file paths - cdART Not Downloaded]           
            print_exc()
        conn.commit()
        c.close()
        return message, download_success  # returns one of the messages built based on success or lack of

        

    #Automatic download of non existing cdarts and refreshes addon's db
    def auto_download( self ):
        print "#  Autodownload"
        print "# "
        pDialog.create( _(32046) )
        #Onscreen Dialog - Automatic Downloading of cdART
        artist_count = 0
        download_count = 0
        cdart_existing = 0
        album_count = 0
        d_error=0
        distant_artist = str.lower(self.get_html_source( artist_url ))
        if not distant_artist == "":
            recognized_artists, local_artists = self.get_recognized( distant_artist , local_artist )
        pDialog.create( _(32046) )
        count_artist_local = len(recognized_artists)
        for artist in recognized_artists:
            artist_count = artist_count + 1
            percent = int((artist_count / float(count_artist_local)) * 100)
            print "#    Artist: %-40s Local ID: %-10s   Distant ID: %s" % (artist["name"], artist["local_id"], artist["distant_id"])
            local_album_list = self.get_local_album( artist["name"], artist["local_id"] )
            remote_cdart_url = self.remote_cdart_list( artist, 2 )
            for album in local_album_list:
                if remote_cdart_url == []:
                    print "#    No cdARTs found"
                    break
                album_count = album_count + 1
                pDialog.update( percent , "%s%s" % (_(32038) , artist["name"] )  , "%s%s" % (_(32039) , album["title"] ) )
                name = artist["name"]
                title = album["title"]
                print "#     Album: %s" % album["title"]
                if album["cdart"] == "FALSE":
                    test_album = self.find_cdart( name, title, remote_cdart_url )
                    if not test_album == "" : 
                        print "#            ALBUM MATCH FOUND"
                        #print "test_album[0]: %s" % test_album[0]
                        message, d_success = self.download_cdart( test_album , album )
                        if d_success == 1:
                            download_count = download_count + 1
                            album["cdart"] = "TRUE"
                        else:
                            print "#  Download Error...  Check Path."
                            print "#      Path: %s" % album["path"]
                            d_error = 1
                    else :
                        print "#            ALBUM MATCH NOT FOUND"
                else:
                    cdart_existing = cdart_existing + 1
                    print "#            cdART file already exists, skipped..."    
                if ( pDialog.iscanceled() ):
                    break
            if ( pDialog.iscanceled() ):
                    break    
        pDialog.close()
        if d_error == 1:
            xbmcgui.Dialog().ok( _(32026), "%s: %s" % ( _(32041), download_count ) )
        else:
            xbmcgui.Dialog().ok( _(32040), "%s: %s" % ( _(32041), download_count ) )
        return

    #Local vs. XBMCSTUFF.COM cdART list maker
    def local_vs_distant( self ):
        print "#  Local vs. XBMCSTUFF.COM cdART"
        print "# "
        pDialog.create( _(32065) )
        #Onscreen Dialog - Comparing Local and Online cdARTs...
        count_artist_local = len(local_artist)
        local_count = 0
        distant_count = 0
        cdart_difference = 0
        album_count = 0
        artist_count = 0
        temp_album = {}
        cdart_lvd = []
        for artist in local_artist:
            artist_count = artist_count + 1
            percent = int((artist_count / float(count_artist_local)) * 100)
            print "#    Artist: %-40s Local ID: %s" % (artist["name"], artist["local_id"])
            local_album_list = self.get_local_album( artist["name"], artist["local_id"] )
            for album in local_album_list:
                temp_album = {}
                album_count = album_count + 1
                temp_album["artist"] = artist["name"]
                temp_album["title"] = album["title"]
                temp_album["path"] = album["path"]
                name = artist["name"]
                title = album["title"]
                pDialog.update( percent , "%s%s" % (_(32038) , artist["name"] )  , "%s%s" % (_(32039) , album["title"] ) )
                test_album = self.find_cdart2(name , title)
                print "#        Album: %s" % album["title"]
                if not test_album == [] : 
                    print "#            ALBUM MATCH FOUND"
                    temp_album["distant"] = "TRUE"
                    distant_count = distant_count + 1
                    if album["cdart"] == "TRUE" :
                        temp_album["local"] = "TRUE"
                        local_count = local_count + 1
                        print "#                Local & Distant cdART image exists..."
                    else:
                        temp_album["local"] = "FALSE"
                        print "#                No local cdART image exists"
                else :
                    print "#            ALBUM MATCH NOT FOUND"
                    temp_album["distant"] = "FALSE"
                    if album["cdart"] == "TRUE" :
                        local_count = local_count + 1
                        temp_album["local"] = "TRUE"
                        print "#                Local cdART image exists..."
                    else:
                        temp_album["local"] = "FALSE"
                        print "#                No local cdART image exists"
                cdart_lvd.append(temp_album)
                #print temp_album
                #print cdart_lvd                
                if ( pDialog.iscanceled() ):
                    break
            if ( pDialog.iscanceled() ):
                    break    
        pDialog.close()
        if (local_count - distant_count) > 0:
            xbmcgui.Dialog().ok( "There are %s cdARTs that only exist locally" % (local_count - distant_count), "Local cdARTs: %s" % local_count, "Distant cdARTs: %s" % distant_count )
            difference = 1
        else:
            xbmcgui.Dialog().ok( "There are %s new cdARTs on XBMCSTUFF.COM" % (distant_count - local_count), "Local cdARTs: %s" % local_count, "Distant cdARTs: %s" % distant_count )
            differnece = 0
        return cdart_lvd, difference

    def remote_cdart_list( self, artist_menu, mode ):
        print "#  Finding Remote cdARTs"
        print "# "
        if mode == 1:
            print "#        Mode - Populate Album List"
        elif mode == 2:
            print "#        Mode - Find cdART"
        else:
            print "#        Mode - unknown"        
        cdart_url = []
        #If there is something in artist_menu["distant_id"] build cdart_url
        print "# distant id: %s" % artist_menu["distant_id"]
        if artist_menu["distant_id"] :
            #print "#    Local artist matched on XBMCSTUFF.COM"
            #print "#        Artist: %s     Local ID: %s     Distant ID: %s" % (artist_menu["name"] , artist_menu["local_id"] , artist_menu["distant_id"])
            artist_xml = self.get_html_source( album_url + "&id_artist=%s" % artist_menu["distant_id"] )
            raw = re.compile( "<cdart (.*?)</cdart>", re.DOTALL ).findall(artist_xml)
            for i in raw:
                album = {}
                album["artistl_id"] = artist_menu["local_id"]
                album["artistd_id"] = artist_menu["distant_id"]
                album["local_name"] = album["artist"] = artist_menu["name"]
                match = re.search('album="(.*?)">', i )
                #search for album title match, if found, store in album["title"], if not found store empty space
                if match:
                    album["title"] = (match.group(1).replace("&amp;", "&"))              
                    #print "#               Distant Album: %s" % album["title"]
                else:
                    album["title"] = ""
                #search for album thumb match, if found, store in album["thumb"], if not found store empty space
                match = re.search( "<thumb>(.*?)</thumb>", i )
                if match:
                    album["thumb"] = (match.group(1))                
                else:
                    album["thumb"] = ""
                #print "#                    cdART Thumb: %s" % album["thumb"]
                match = re.search( "<picture>(.*?)</picture>", i )
                #search for album cdart match, if found, store in album["picture"], if not found store empty space
                if match:
                    album["picture"] = (match.group(1))                
                else:
                    album["picture"] = ""
                #print "#                    cdART picture: %s" % album["picture"]
                cdart_url.append(album)
                #print "cdart_url: %s " % cdart_url
        #If artist_menu["distant_id"] is empty, search for name match
        else:
            if mode == 1:
                cdart_url = self.search( artist_menu["name"], artist_menu["local_id"])
            else:
                pass
            #print cdart_url
        return cdart_url
            
    #creates the album list on the skin
    def populate_album_list(self, artist_menu, cdart_url):
        print "#  Populating Album List"
        print "#"
        self.getControl( 122 ).reset()
        if not cdart_url:
            #no cdart found
            xbmcgui.Dialog().ok( _(32033), _(32030), _(32031) )
            #Onscreen Dialog - Not Found on XBMCSTUFF.COM, Please contribute! Upload your cdARTs, On www.xbmcstuff.com
            xbmc.executebuiltin( "Dialog.Close(busydialog)" )
            #return
        else:
            #print "#  Building album list based on:"
            #print "#        artist: %s     local_id: %s" % (cdart_url[0]["local_name"], cdart_url[0]["artistl_id"] )
            local_album_list = self.get_local_album(cdart_url[0]["local_name"], cdart_url[0]["artistl_id"])
            cdart_img = ""
            label1 = ""
            label2 = ""
            album_list= {}
            #print local_album_list
            for album in local_album_list:
                name = cdart_url[0]["artist"]
                title = str.lower(album["title"])
                cdart = self.cdart_search( cdart_url, title )
                #print album
                #check to see if there is a thumb
                if not cdart["title"]=="": 
                    label1 = "%s - %s" % (album["artist"] , album["title"])
                    url = cdart["picture"]
                    #check to see if cdart already exists
                    # set the matched colour local and distant colour
                    #colour the label to the matched colour if not
                    if album["cdart"] == "TRUE":
                        label2 = "%s&&%s&&&&%s" % (url, album["path"], (os.path.join(album["path"], "cdart.png")))
                        cdart_img = os.path.join(album["path"], "cdart.png")
                        label1 = "%s - %s     ***Local & xbmcstuff.com cdART Exists***" % (album["artist"] , album["title"])
                        listitem = xbmcgui.ListItem( label=label1, label2=label2, thumbnailImage=(os.path.join(album["path"], "cdart.png")) )
                        self.getControl( 122 ).addItem( listitem )
                        listitem.setLabel( self.coloring( label1 , self.remotelocal_color , label1 ) )
                        listitem.setLabel2( label2 )                        
                    else :
                        label2 = "%s&&%s&&&&%s" % ( url, album["path"], "")
                        cdart_img=url
                        listitem = xbmcgui.ListItem( label=label1, label2=label2, thumbnailImage=cdart_img )
                        self.getControl( 122 ).addItem( listitem )
                        listitem.setLabel( self.coloring( label1 , self.remote_color , label1 ) )
                        listitem.setLabel2( label2 )
                    listitem.setThumbnailImage( cdart_img )                                   
                else :
                    url = ""
                    if album["cdart"] == "TRUE":
                        cdart_img = os.path.join(album["path"], "cdart.png")
                        label2 = "%s&&%s&&&&%s" % (url, album["path"], cdart_img)
                        label1 = "%s - %s     ***Local only cdART Exists***" % (album["artist"] , album["title"])
                        listitem = xbmcgui.ListItem( label=label1, label2=label2, thumbnailImage=cdart_img )
                        self.getControl( 122 ).addItem( listitem )
                        listitem.setLabel( self.coloring( label1 , self.local_color , label1 ) )
                        listitem.setLabel2( label2 )
                        listitem.setThumbnailImage( cdart_img )
                    else:
                        label1 = "choose for %s - %s" % (album["artist"] , album["title"] )
                        cdart_img = ""
                        label2 = "%s&&%s&&&&%s" % (url, album["path"], cdart_img)
                        print "#  labe2: %s" % label2
                        listitem = xbmcgui.ListItem( label=label1, label2=label2, thumbnailImage=cdart_img )
                        self.getControl( 122 ).addItem( listitem )
                        listitem.setLabel( self.coloring( label1 , self.unmatched_color , label1 ) )
                        listitem.setLabel2( label2 )
                        listitem.setThumbnailImage( cdart_img )            
                self.cdart_url=cdart_url
            xbmc.executebuiltin( "Dialog.Close(busydialog)" )
            self.setFocus( self.getControl( 122 ) )
            self.getControl( 122 ).selectItem( 0 )
        return
       
    #creates the artist list on the skin        
    def populate_artist_list( self, local_artist_list):
        print "#  Populating Artist List"
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        for artist in local_artist_list:
                if not artist["distant_id"] == "":
                    listitem = xbmcgui.ListItem( label=self.coloring( artist["name"] , "green" , artist["name"] ) )
                    self.getControl( 120 ).addItem( listitem )
                    listitem.setLabel( self.coloring( artist["name"] , self.recognized_color , artist["name"] ) )
                else :
                    listitem = xbmcgui.ListItem( label=artist["name"] )
                    self.getControl( 120 ).addItem( listitem )
                    listitem.setLabel( self.coloring( artist["name"] , self.unrecognized_color , artist["name"] ) )
        xbmc.executebuiltin( "Dialog.Close(busydialog)" )
        self.setFocus( self.getControl( 120 ) )
        self.getControl( 120 ).selectItem( 0 )
        return
    
    #create the addon's database
    def database_setup( self ):
        global local_artist
        artist_count = 0
        download_count = 0
        cdart_existing = 0
        album_count = 0
        percent=0
        print "#  Setting Up Database"
        print "#    addon_work_path: %s" % addon_work_folder
        if not os.path.exists(addon_work_folder):
            xbmcgui.Dialog().ok( _(32071), _(32072), _(32073) )
            print "#  Settings not set, aborting database creation"
            return album_count, artist_count, cdart_existing
        local_artist, count_artist_local = self.get_local_artist()
        pDialog.create( _(32021), _(32016) )
        #Onscreen Dialog - Creating Addon Database
        #                      Please Wait....
        #print addon_db
        conn = sqlite3.connect(addon_db)
        c = conn.cursor()
        c.execute('''create table lalist(local_id, name)''')
        c.execute('''create table alblist(cdart, path, artist_id, title, artist)''')
        for artist in local_artist:
            c.execute("insert into lalist(local_id, name) values (?, ?)", (artist["local_id"], artist["name"]))
            artist_count = artist_count + 1
            percent = int((artist_count / float(count_artist_local)) * 100) 
            local_album_list = self.get_local_album( artist["name"], artist["local_id"] )
            for album in local_album_list:
                pDialog.update( percent, _(32016), "" , "%s - %s" % ( artist["name"] , album["title"] ) )
                album_count = album_count + 1               
                if album["cdart"] == "TRUE" :
                   cdart_existing = cdart_existing + 1
                c.execute("insert into alblist(cdart, path, artist_id, title, artist) values (?, ?, ?, ?, ?)", (album["cdart"], album["path"], album["artist_id"], album["title"], album["artist"]))
                if (pDialog.iscanceled()):
                    break
            if (pDialog.iscanceled()):
                break
        if (pDialog.iscanceled()):
            pDialog.close()
            ok=xbmcgui.Dialog().ok(_(32050), _(32051), _(32052), _(32053))
            print ok
        pDialog.close()
        conn.commit()
        c.close()
        return album_count, artist_count, cdart_existing
    
    #retrieve the addon's database - saves time by no needing to search system for infomation on every addon access
    def get_local_db( self ):
        print "#  Retrieving Local Database"
        print "#"
        local_album_list = []    
        conn_l = sqlite3.connect(addon_db)
        c = conn_l.cursor()
        c.execute("""SELECT DISTINCT cdart, path, artist_id, title, artist FROM alblist""")
        db=c.fetchall()
        for item in db:
            album = {}
            album["cdart"] = translate_string( item[0].encode("utf-8")).strip("'u")
            album["path"] = (repr(item[1]).replace('"','')).encode("utf-8").strip("'u")
            album["artist_id"] = repr(item[2]).strip("'u")
            album["title"] = translate_string( item[3].encode("utf-8")).strip("'u")
            album["artist"] = translate_string( item[4].encode("utf-8")).strip("'u")
            local_album_list.append(album)
            c.close
        return local_album_list
    
    #retrieves counts for local album, artist and cdarts
    def new_local_count( self ):
        print "#  Counting Local Artists, Albums and cdARTs"
        print "#"
        pDialog.create( _(32020), _(32016) )
        #Onscreen Dialog - Retrieving Local Music Database, Please Wait....
        global local_artist
        local_artist, count_artist_local = self.get_local_artist()
        artist_count = 0
        download_count = 0
        cdart_existing = 0
        album_count = 0
        percent=0
        local_album_list = self.get_local_db( )
        for album in local_album_list:
            pDialog.update( percent, _(32016), "" , "%s - %s" % ( album["artist"] , album["title"] ) )
            album_count = album_count + 1               
            if album["cdart"] == "TRUE" :
               cdart_existing = cdart_existing + 1
        pDialog.close()
        return album_count, count_artist_local, cdart_existing
    
    #user call from Advanced menu to refresh the addon's database
    def refresh_db( self ):
        print "#  Refreshing Local Database"
        print "#"
        if os.path.isfile((addon_db).replace("\\\\" , "\\").encode("utf-8")):
            #File exists needs to be deleted
            db_delete = xbmcgui.Dialog().yesno( _(32042) , _(32015) )
            if db_delete :
                os.remove(addon_db)
                local_album_count, local_artist_count, local_cdart_count = self.database_setup()                
            else:
                pass            
        else :
            #If file does not exist and some how the program got here, create new database
            local_album_count, local_artist_count, local_cdart_count = self.database_setup()
        #update counts
        self.refresh_counts( local_album_count, local_artist_count, local_cdart_count )
        return

    def single_unique_copy(self, artist, album, source):
        print "### Copying to Unique Folder: %s - %s" % (artist,album) 
        destination = ""
        fn_format = int(__settings__.getSetting("folder"))
        unique_folder = __settings__.getSetting("unique_path")
        resize = __settings__.getSetting("enableresize")
        if unique_folder =="":
            __settings__.openSettings()
            unique_folder = __settings__.getSetting("unique_path")
        print "#    source: %s" % source
        if os.path.isfile(source):
            print "#    source: %s" % source
            if fn_format == 0:
                destination=os.path.join(unique_folder, (artist.replace("/","")).replace("'","")) #to fix AC/DC
                fn = os.path.join(destination, ( ((album.replace("/","")).replace("'","")) + ".png"))
            else:
                destination=unique_folder
                fn = os.path.join(destination, ((((artist.replace("/", "")).replace("'","")) + " - " + ((album.replace("/","")).replace("'","")) + ".png").lower()))
            print "#    destination: %s" % destination
            if not os.path.exists(destination):
                #pass
                os.makedirs(destination)
            else:
                pass
            print "filename: %s" % fn
            try:
                if resize:
                    try:
                        cdart = Image.open(source)
                        print "##   Opening image: %s" % source
                        if cdart.size[0] != cdart.size[1]:
                            print "###      Original cdART not square, not my fault if resize is wrong ###"
                        if cdart.size[0] > 450 or cdart.size[1] > 450:
                            print "##       Resizing cdART"
                            cdart_resized = cdart.resize((450,450), Image.ANTIALIAS)
                            print "##   Saving image: %s" % fn
                            cdart_resized.save(fn)
                        else:
                            print "##       Not Resizing...."
                            print "#    Saving: %s" % fn
                            shutil.copy(source, fn)
                    except:
                        print "#### Resizing error"
                else:
                    print "#    Saving: %s" % fn
                    shutil.copy(source, fn)
            except:
                print "#  Copying error, check path and file permissions"
        else:
            print "#   Error: cdART file does not exist..  Please check..."
        return


    def single_backup_copy(self, artist, album, source):
        print "### Copying To Backup Folder: %s - %s" % (artist,album) 
        destination = ""
        fn_format = int(__settings__.getSetting("folder"))
        backup_folder = __settings__.getSetting("backup_path")
        if backup_folder =="":
            __settings__.openSettings()
            backup_folder = __settings__.getSetting("backup_path")
        print "#    source: %s" % source
        if os.path.isfile(source):
            print "#    source: %s" % source
            if fn_format == 0:
                destination=os.path.join(backup_folder, (artist.replace("/","")).replace("'","")) #to fix AC/DC
                fn = os.path.join(destination, ( ((album.replace("/","")).replace("'","")) + ".png"))
            else:
                destination=backup_folder
                fn = os.path.join(destination, ((((artist.replace("/", "")).replace("'","")) + " - " + ((album.replace("/","")).replace("'","")) + ".png").lower()))
            print "#    destination: %s" % destination
            if not os.path.exists(destination):
                #pass
                os.makedirs(destination)
            else:
                pass
            print "filename: %s" % fn
            try:
                shutil.copy(source, fn)
            except:
                print "#  Copying error, check path and file permissions"
        else:
            print "#   Error: cdART file does not exist..  Please check..."
        return


    def single_cdart_delete(self, source, album):
        print "### Deleting: %s" % source
        conn = sqlite3.connect(addon_db)
        c = conn.cursor()
        c.execute("""UPDATE alblist SET cdart="FALSE" WHERE title='%s'""" % album)
        conn.commit()
        c.close()
        if os.path.isfile(source):
            try:
                os.remove(source)
            except:
                print "#  Deleteing error, check path and file permissions"
        else:
            print "#   Error: cdART file does not exist..  Please check..."
        return
    
    # Copy's all the local unique cdARTs to a folder specified bye the user
    def unique_cdart_copy( self, unique ):
        print "### Copying Unique cdARTs..."
        percent = 0
        count = 0
        duplicates = 0
        destination = ""
        album = {}
        fn_format = int(__settings__.getSetting("folder"))
        unique_folder = __settings__.getSetting("unique_path")
        resize = __settings__.getSetting("enableresize")
        if unique_folder =="":
            __settings__.openSettings()
            unique_folder = __settings__.getSetting("unique_path")
        #print "#    fn_format: %s" % fn_format
        #print "#    unique_folder: %s" % unique_folder
        pDialog.create( _(32060) )
        for album in unique:
            #print album
            percent = int((count/len(unique))*100)
            if (pDialog.iscanceled()):
                break
            if album["local"] == "TRUE" and album["distant"] == "FALSE":
                source=os.path.join(album["path"].replace("\\\\" , "\\"), "cdart.png")
                print "#    Artist: %-30s    ##    Album:%s" % (album["artist"], album["title"])
                print "#        source: %s" % source
                if os.path.isfile(source):
                    if fn_format == 0:
                        destination=os.path.join(unique_folder, (album["artist"].replace("/","")).replace("'","")) #to fix AC/DC
                        fn = os.path.join(destination, ( ((album["title"].replace("/","")).replace("'","")) + ".png"))
                    else:
                        destination=unique_folder
                        fn = os.path.join(destination, ((((album["artist"].replace("/", "")).replace("'","")) + " - " + ((album["title"].replace("/","")).replace("'","")) + ".png").lower()))
                    if not os.path.exists(destination):
                        #pass
                        os.makedirs(destination)
                    else:
                        pass
                    print "#        destination: %s" % fn
                    if os.path.isfile(fn):
                        print "################## cdART Not being copied, File exists: %s" % fn
                        duplicates = duplicates + 1
                    else:
                        try:
                            if resize:
                                try:
                                    cdart = Image.open(source)
                                    print "##   Opening image: %s" % source
                                    if cdart.size[0] != cdart.size[1]:
                                        print "###      Original cdART not square, not my fault if resize is wrong ###"
                                    if cdart.size[0] > 450 or cdart.size[1] > 450:
                                        print "##       Resizing cdART"
                                        cdart_resized = cdart.resize((450,450), Image.ANTIALIAS)
                                        print "##   Saving image: %s" % fn
                                        cdart_resized.save(fn)
                                    else:
                                        print "##       Not Resizing...."
                                        print "#    Saving: %s" % fn
                                        shutil.copy(source, fn)
                                except:
                                    print "#### Resizing error"
                            
                            else:
                                print "#    Saving: %s" % fn                                    
                                shutil.copy(source, fn)
                            count=count + 1
                        except:
                            print "#  Copying error, check path and file permissions"
                            count=count + 1
                        pDialog.update( percent, _(32064) % unique_folder , "Filename: %s" % fn, "%s: %s" % ( _(32056) , count ) )
                else:
                    print "#   Error: cdART file does not exist..  Please check..."
            else:
                pass
        pDialog.close()
        xbmcgui.Dialog().ok( _(32057), "%s: %s" % ( _(32058), unique_folder), "%s %s" % ( count , _(32059)))
        return

    def restore_from_backup( self ):
        print "### Restoring cdARTs from backup folder"
        pDialog.create( _(32069) )
        #Onscreen Dialog - Restoring cdARTs from backup...
        conn = sqlite3.connect(addon_db)
        c = conn.cursor()
        destination = ""
        source = ""
        fn = ""
        part = {}
        local_db = []
        percent = 0
        count = 0
        total_albums = 0 
        total_count = 0
        fn_format = int(__settings__.getSetting("folder"))
        bkup_folder = __settings__.getSetting("backup_path")
        if bkup_folder =="":
            __settings__.openSettings()
            bkup_folder = __settings__.getSetting("backup_path")
        else:
            pass
        print "#    fn_format: %s" % fn_format
        print "#    bkup_folder: %s" % bkup_folder
        local_db = self.get_local_db()
        total_albums=len(local_db)
        print "#    total albums: %s" % total_albums
        #print "#    albums: %s" % albums
        for part in local_db:
            if (pDialog.iscanceled()):
                break
            print "#     Artist: %-30s  ##  Album: %s" % (part["artist"], part["title"])
            print "#        Album Path: %s" % part["path"]
            percent = int(total_count/float(total_albums))*100
            if fn_format == 0:
                source=os.path.join( bkup_folder, (part["artist"].replace("/","").replace("'","") ) )#to fix AC/DC and other artists with a / in the name
                fn = os.path.join(source, ( ( part["title"].replace("/","").replace("'","") ) + ".png") )
                if not os.path.isfile(fn):
                    source=os.path.join( bkup_folder ) #to fix AC/DC
                    fn = os.path.join(source, ( ( ( part["artist"].replace("/", "").replace("'","") ) + " - " + ( part["title"].replace("/","").replace("'","") ) + ".png").lower() ) )
            else:
                source=os.path.join( bkup_folder ) #to fix AC/DC
                fn = os.path.join(source, ( ( ( part["artist"].replace("/", "").replace("'","") ) + " - " + ( part["title"].replace("/","").replace("'","") ) + ".png").lower() ) )
                if not os.path.isfile(fn):
                    source=os.path.join( bkup_folder, (part["artist"].replace("/","").replace("'","") ) )#to fix AC/DC and other artists with a / in the name
                    fn = os.path.join(source, ( ( part["title"].replace("/","").replace("'","") ) + ".png") )
            print "#        Source folder: %s" % source
            print "#        Source filename: %s" % fn
            if os.path.isfile(fn):
                destination = os.path.join(part["path"], "cdart.png")
                print "#        Destination: %s" % destination
                try:
                    shutil.copy(fn, destination)
                    count = count + 1
                except:
                    print "######  Copying error, check path and file permissions"
                try:
                    c.execute("""UPDATE alblist SET cdart="TRUE" WHERE title='%s'""" % part["title"])
                except:
                    print "######  Problem modifying Database!!  Artist: %s   Album: %s" % (part["artist"], part["title"])
            else:
                pass
            pDialog.update( percent , "backup folder: %s" % bkup_folder, "Filename: %s" % fn, "%s: %s" % ( _(32056) , count ) )
            total_count = total_count + 1
        pDialog.close()
        conn.commit()
        c.close()
        xbmcgui.Dialog().ok( _(32057),  "%s %s" % ( count , _(32070) ) ) 
        return        
        
    # copy cdarts from music folder to temporary location
    # first step to copy to skin folder
    def cdart_copy( self ):
        print "### Copying cdARTs to Backup folder"
        destination = ""
        duplicates = 0
        percent = 0
        count = 0
        total = 0
        album = {}
        albums = []
        fn_format = int(__settings__.getSetting("folder"))
        bkup_folder = __settings__.getSetting("backup_path")
        cdart_list_folder = __settings__.getSetting("cdart_path")
        if bkup_folder =="":
            __settings__.openSettings()
            bkup_folder = __settings__.getSetting("backup_path")
            cdart_list_folder = __settings__.getSetting("cdart_path")
        #print "#    fn_format: %s" % fn_format
        #print "#    bkup_folder: %s" % bkup_folder
        #print "#    cdart_list_folder: %s" % cdart_list_folder
        albums = self.get_local_db()
        #print albums
        #print len(albums)
        pDialog.create( _(32060) )
        for album in albums:
            if (pDialog.iscanceled()):
                break
            #print album
            if album["cdart"] == "TRUE":
                source=os.path.join(album["path"].replace("\\\\" , "\\"), "cdart.png")
                print "#     cdART #: %s" % count
                print "#     Artist: %-30s  Album: %s" % (album["artist"], album["title"])
                print "#        Album Path: %s" % source
                if os.path.isfile(source):
                    if fn_format == 0:
                        destination=os.path.join( bkup_folder, ( album["artist"].replace("/","").replace("'","") ) ) #to fix AC/DC
                        fn = os.path.join( destination, ( ( album["title"].replace("/","").replace("'","") ) + ".png") )
                    elif fn_format == 1:
                        destination=os.path.join( bkup_folder ) #to fix AC/DC
                        fn = os.path.join( destination, (  ( album["artist"].replace("/", "").replace("'","") ) + " - " + ( album["title"].replace("/","").replace("'","") ) + ".png").lower())
                    print "#        Destination Path: %s" % destination
                    if not os.path.exists(destination):
                        #pass
                        os.makedirs(destination)
                    print "#        Filename: %s" % fn
                    if os.path.isfile(fn):
                        print "################## cdART Not being copied, File exists: %s" % fn
                        duplicates = duplicates + 1
                    else:
                        try:
                            shutil.copy(source, fn)
                            count = count + 1
                            pDialog.update( percent , "backup folder: %s" % bkup_folder, "Filename: %s" % fn, "%s: %s" % ( _(32056) , count ) )
                        except:
                            print "######  Copying error, check path and file permissions"
                else:
                    print "######  Copying error, cdart.png does not exist"
            else:
                pass
            percent = int(total/float(len(albums))*100)
            total = total + 1        
        pDialog.close()
        print "#     Duplicate cdARTs: %s" % duplicates
        xbmcgui.Dialog().ok( _(32057), "%s: %s" % ( _(32058), bkup_folder), "%s %s" % ( count , _(32059)), "%s Duplicates Found" % duplicates)
        return
    
         
    def setup_artist_list( self, artist):
        self.artist_menu = {}
        self.artist_menu["local_id"] = str(artist[self.getControl( 120 ).getSelectedPosition()]["local_id"])
        self.artist_menu["name"] = str(artist[self.getControl( 120 ).getSelectedPosition()]["name"])
        self.artist_menu["distant_id"] = str(artist[self.getControl( 120 ).getSelectedPosition()]["distant_id"])
        self.populate_album_list( self.artist_menu )
                    
    def refresh_counts( self, local_album_count, local_artist_count, local_cdart_count ):
        self.getControl( 109 ).setLabel( _(32007) % local_artist_count)
        self.getControl( 110 ).setLabel( _(32010) % local_album_count)
        self.getControl( 112 ).setLabel( _(32008) % local_cdart_count)

    def populate_local_cdarts( self ):
        label2= ""
        cdart_img=""
        url = ""
        work_temp = []
        l_artist = self.get_local_db()
        xbmc.executebuiltin( "ActivateWindow(busydialog)" )
        self.getControl( 140 ).reset()
        for album in l_artist:
            if album["cdart"] == "TRUE":
                cdart_img = os.path.join(album["path"], "cdart.png")
                label2 = "%s&&%s&&&&%s" % (url, album["path"], cdart_img)
                label1 = "%s - %s" % (album["artist"] , album["title"])
                listitem = xbmcgui.ListItem( label=label1, label2=label2, thumbnailImage=cdart_img )
                self.getControl( 140 ).addItem( listitem )
                listitem.setLabel( self.coloring( label1 , "orange" , label1 ) )
                listitem.setLabel2( label2 )
                work_temp.append(album)
                #print label2
            else:
                pass
        xbmc.executebuiltin( "Dialog.Close(busydialog)" )
        self.setFocus( self.getControl( 140 ) )
        self.getControl( 140 ).selectItem( 0 )
        return work_temp
  
    # This selects which cdART image shows up in the display box (image id 210) 
    def cdart_icon( self ):
        try:   # If there is information in label 2 of list id 122(album list)
            local_cdart = ""
            url = ""
            cdart_path ={}
            local_cdart = (self.getControl(122).getSelectedItem().getLabel2()).split("&&&&")[1]
            url = ((self.getControl( 122 ).getSelectedItem().getLabel2()).split("&&&&")[0]).split("&&")[1]
            cdart_path["path"] = ((self.getControl( 122 ).getSelectedItem().getLabel2()).split("&&&&")[0]).split("&&")[0]
            #print "#   cdart_path: %s" % cdart_path["path"]
            #print "#   url: %s" % url
            #print "#   local_cdart: %s" % local_cdart
            if not local_cdart == "": #Test to see if there is a path in local_cdart
                image = local_cdart
                self.getControl( 210 ).setImage( image )
            else:
                if not cdart_path["path"] =="": #Test to see if there is an url in cdart_path["path"]
                    image = cdart_path["path"]
                    self.getControl( 210 ).setImage( image )
                else:
                    image =""
                    #image = addon_img
        
        except:  
            try: # If there is information in label 2 of list id 140(local album list)
                local_cdart = (self.getControl(140).getSelectedItem().getLabel2()).split("&&&&")[1]
                url = ((self.getControl( 140 ).getSelectedItem().getLabel2()).split("&&&&")[0]).split("&&")[1]
                cdart_path["path"] = ((self.getControl( 140 ).getSelectedItem().getLabel2()).split("&&&&")[0]).split("&&")[0]
                #print "#   cdart_path: %s" % cdart_path["path"]
                #print "#   url: %s" % url
                #print "#   local_cdart: %s" % local_cdart
                if not local_cdart == "": #Test to see if there is a path in local_cdart
                    image = local_cdart
                    self.getControl( 210 ).setImage( image )
                else:
                    if not cdart_path["path"] =="": #Test to see if there is an url in cdart_path["path"]
                        image = cdart_path["path"]
                        self.getControl( 210 ).setImage( image )
                    else:
                        image =""
                        #image = addon_img
            
            except: # If there is not any information in any of those locations, no image.
                image =""
                #image=addon_img
        self.getControl( 210 ).setImage( image )
            
    # setup self. strings and initial local counts
    def setup_all( self ):
        self.menu_mode = 0
        self.artist_menu = {}
        self.remote_cdart_url =[]
        self.recognized_artists = []
        self.all_artists = []
        self.cdart_url = []
        self.local_artists = []
        self.label_1 = ""
        self.label_2 = addon_img
        self.cdartimg = ""
        listitem = xbmcgui.ListItem( label=self.label_1, label2=self.label_2, thumbnailImage=self.cdartimg )
        self.getControl( 122 ).addItem( listitem )
        listitem.setLabel2(self.label_2)
        #checking to see if addon_db exists, if not, run database_setup()
        if not os.path.isfile((addon_db).replace("\\\\" , "\\").encode("utf-8")):
            local_album_count, local_artist_count, local_cdart_count = self.database_setup()
        else:
            local_album_count, local_artist_count, local_cdart_count = self.new_local_count()
        self.refresh_counts( local_album_count, local_artist_count, local_cdart_count )
        self.setFocusId( 100 ) # set menu selection to the first option(Search Artists)


    def onClick( self, controlId ):
        #print "Control ID: %s " % controlId
        if controlId == 102 : #Automatic Download
            self.menu_mode = 3
            download_count = self.auto_download()
            local_album_count, local_artist_count, local_cdart_count = self.new_local_count()
            self.refresh_counts( local_album_count, local_artist_count, local_cdart_count )
        if controlId in [105, 106]: #Get Artists List
            xbmc.executebuiltin( "ActivateWindow(busydialog)" )
            self.getControl( 120 ).reset()
            distant_artist = str.lower(self.get_html_source( artist_url ))
            if not distant_artist == "":
                self.recognized_artists, self.local_artists = self.get_recognized( distant_artist , local_artist )
        if controlId == 105 : #Recognized Artists
            self.menu_mode = 1
            self.populate_artist_list( self.recognized_artists )
        if controlId == 106 : #All Artists
            self.menu_mode = 2
            self.populate_artist_list( self.local_artists )   
        if controlId == 120 : #Retrieving information from Artists List
            xbmc.executebuiltin( "ActivateWindow(busydialog)" )
            if self.menu_mode == 1: #information pulled from recognized list
                self.artist_menu = {}
                self.artist_menu["local_id"] = str(self.recognized_artists[self.getControl( 120 ).getSelectedPosition()]["local_id"])
                self.artist_menu["name"] = str(self.recognized_artists[self.getControl( 120 ).getSelectedPosition()]["name"])
                self.artist_menu["distant_id"] = str(self.recognized_artists[self.getControl( 120 ).getSelectedPosition()]["distant_id"])
            elif self.menu_mode == 2: #information pulled from All Artist List
                self.artist_menu = {}
                self.artist_menu["local_id"] = str(self.local_artists[self.getControl( 120 ).getSelectedPosition()]["local_id"])
                self.artist_menu["name"] = str(self.local_artists[self.getControl( 120 ).getSelectedPosition()]["name"])
                self.artist_menu["distant_id"] = str(self.local_artists[self.getControl( 120 ).getSelectedPosition()]["distant_id"])
            self.remote_cdart_url = self.remote_cdart_list( self.artist_menu, 1 )
            #print "# %s" % self.artist_menu
            #print artist_menu
            self.populate_album_list( self.artist_menu, self.remote_cdart_url )
        if controlId == 122 : #Retrieving information from Album List
            #print "#  Setting up Album List"
            self.getControl( 140 ).reset()
            select = None
            local = ""
            url = ""
            album = {}
            album_search=[]
            album_selection=[]
            cdart_path = {}
            local_cdart = ""
            count = 0
            select=0
            local_cdart = (self.getControl(122).getSelectedItem().getLabel2()).split("&&&&")[1]
            url = ((self.getControl( 122 ).getSelectedItem().getLabel2()).split("&&&&")[0]).split("&&")[0]
            cdart_path["path"] = ((self.getControl( 122 ).getSelectedItem().getLabel2()).split("&&&&")[0]).split("&&")[1]
            local = (self.getControl( 122 ).getSelectedItem().getLabel()).replace("choose for ", "")
            cdart_path["artist"]=local.split(" - ")[0]
            cdart_path["title"]=(((local.split(" - ")[1]).replace("     ***Local & xbmcstuff.com cdART Exists***","")).replace("     ***Local only cdART Exists***",""))
            cdart_path["title"]= self.remove_color(cdart_path["title"])
            #print "#   artist: %s" % cdart_path["artist"]
            #print "#   album title: %s" % cdart_path["title"]
            #print "#   cdart_path: %s" % cdart_path["path"]
            #print "#   url: %s" % url
            #print "#   local_cdart: %s" % local_cdart
            if not url =="" : # If it is a recognized Album...
                message, d_success = self.download_cdart( url, cdart_path )
                xbmcgui.Dialog().ok(message[0] ,message[1] ,message[2] ,message[3])
                pDialog.close()
            else : # If it is not a recognized Album...
                for elem in self.cdart_url:
                    album["search_name"] = elem["title"]
                    album["search_url"] = elem["picture"]
                    album_search.append(album["search_name"])
                    album_selection.append(album["search_url"])
                select = xbmcgui.Dialog().select( _(32022), album_search)
                #print select
                if not select == -1:
                    cdart_url = album_selection[select]
                    message, d_success = self.download_cdart( cdart_url, cdart_path )
                    xbmcgui.Dialog().ok(message[0] ,message[1] ,message[2] ,message[3])
                    pDialog.close()
            local_album_count, local_artist_count, local_cdart_count = self.new_local_count()
            self.refresh_counts( local_album_count, local_artist_count, local_cdart_count )
            self.populate_album_list( self.artist_menu, self.remote_cdart_url )
        if controlId == 132 : #Clean Music database selected from Advanced Menu
            xbmc.executebuiltin( "CleanLibrary(music)") 
        if controlId == 133 : #Update Music database selected from Advanced Menu
            xbmc.executebuiltin( "UpdateLibrary(music)")
        if controlId == 135 : #Back up cdART selected from Advanced Menu
            self.cdart_copy()
        if controlId == 134 : #Copy Unique Local cdART selected from Advanced Menu
            unique, difference = self.local_vs_distant()
            if difference == 1:
                self.unique_cdart_copy( unique )
            else:
                xbmcgui.Dialog().ok( "There are no unique local cdARTs")
        if controlId == 131 : #Refresh Local database selected from Advanced Menu
            self.refresh_db()
        if controlId == 136 : #Restore from Backup
            self.restore_from_backup()
            local_album_count, local_artist_count, local_cdart_count = self.new_local_count()
            self.refresh_counts( local_album_count, local_artist_count, local_cdart_count )
        if controlId == 137 : #Local cdART List
            self.getControl( 122 ).reset()
            self.populate_local_cdarts()
        if controlId == 104 : #Settings
            self.menu_mode = 5
            __settings__.openSettings()
            self.setup_colors()
        if controlId == 111 : #Exit
            self.menu_mode = 0
            self.close()
        if controlId == 107 :
            self.setFocusId( 200 )
        if controlId == 108 :
            self.setFocusId( 200 ) 
        if controlId == 130 : #cdART Backup Menu
            self.setFocusId( 135 )
        if controlId == 140 : #Local cdART selection
            self.cdart_icon
            self.setFocusId( 142 )
            artist_album = self.getControl(140).getSelectedItem().getLabel()
            artist_album = self.remove_color(artist_album)
            artist = artist_album.split(" - ")[0]
            album_title = artist_album.split(" - ")[1]
            #print "# Album: %s" % album_title
            #print "# Artist: %s" % artist
            self.getControl( 300 ).setLabel( self.getControl(140).getSelectedItem().getLabel() )
        if controlId == 143 : #Delete cdART
            path = ((self.getControl( 140 ).getSelectedItem().getLabel2()).split("&&&&")[1])
            artist_album = self.getControl(140).getSelectedItem().getLabel()
            artist_album = self.remove_color(artist_album)
            artist = artist_album.split(" - ")[0]
            album_title = artist_album.split(" - ")[1]
            #print "# Path: %s" % path
            #print "# Album: %s" % album_title
            self.single_cdart_delete( path, album_title )
            local_album_count, local_artist_count, local_cdart_count = self.new_local_count()
            self.refresh_counts( local_album_count, local_artist_count, local_cdart_count )
            self.setFocusId( 140 )
            self.populate_local_cdarts()
        if controlId == 142 : #Backup to backup folder
            artist_album = self.getControl(140).getSelectedItem().getLabel()
            artist_album = self.remove_color(artist_album)
            artist = artist_album.split(" - ")[0]
            album_title = artist_album.split(" - ")[1]
            path = ((self.getControl( 140 ).getSelectedItem().getLabel2()).split("&&&&")[1])
            #print "# Album: %s" % album_title
            #print "# Artist: %s" % artist
            self.single_backup_copy( artist, album_title, path )
        if controlId == 144 : #Copy to Unique folder
            artist_album = self.getControl(140).getSelectedItem().getLabel()
            artist_album = self.remove_color(artist_album)
            artist = artist_album.split(" - ")[0]
            album_title = artist_album.split(" - ")[1]
            path = ((self.getControl( 140 ).getSelectedItem().getLabel2()).split("&&&&")[1])
            #print "# Album: %s" % album_title
            #print "# Artist: %s" % artist
            self.single_unique_copy( artist, album_title, path )
        if controlId == 100 : #Search Artist
            self.setFocusId( 105 )
        if controlId == 103 : #Advanced
            self.setFocusId( 130 )
            	

    def onFocus( self, controlId ):
        if controlId == 122 or controlId == 140:
            self.cdart_icon()
            
        	
    def onAction( self, action ):
        self.cdart_icon()
        buttonCode =  action.getButtonCode()
        actionID   =  action.getId()
        #print "onAction(): actionID=%i buttonCode=%i" % (actionID,buttonCode)
        if (buttonCode == KEY_BUTTON_BACK or buttonCode == KEY_KEYBOARD_ESC):
            self.close()
        if actionID == 10:
            print "Closing"
            pDialog.close()
            self.close()
   
def onAction( self, action ):
    #print action
    if (buttonCode == KEY_BUTTON_BACK or buttonCode == KEY_KEYBOARD_ESC):
            self.close()
    if ( action.getButtonCode() in CANCEL_DIALOG ):
	print "# Closing"
	self.close()
