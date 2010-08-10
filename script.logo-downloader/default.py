__script__       = "Logo Downloader"
__author__       = "Ppic"
__url__          = "http://code.google.com/p/passion-xbmc/"
__svn_url__      = ""
__credits__      = "Team XBMC PASSION, http://passion-xbmc.org/"
__platform__     = "xbmc media center, [LINUX, OS X, WIN32, XBOX]"
__date__         = "10-08-2010"
__version__      = "1.4.0"
__svn_revision__  = "$Revision: 000 $"
__XBMC_Revision__ = "30000" #XBMC Babylon
__useragent__ = "Logo downloader %s" % __version__


import urllib
import os
import re
from traceback import print_exc
import xbmc
import xbmcgui



SOURCEPATH = os.getcwd()
RESOURCES_PATH = os.path.join( SOURCEPATH , "resources" )

#BASE_URL = "http://www.themurrayworld.com/xbmc/logos/"
BASE_URL = "http://www.lockstockmods.net/logos/getlogo.php?id="
LOGO_TEST_PATH = os.path.join( RESOURCES_PATH , "test" )
DIALOG_PROGRESS = xbmcgui.DialogProgress()


sys.path.append( os.path.join( RESOURCES_PATH, "lib" ) )

from convert import translate_string
from convert import set_entity_or_charref
from file_item import Thumbnails
thumbnails = Thumbnails()

def footprints():
    print "### %s starting ..." % __script__
    print "### author: %s" % __author__
    print "### URL: %s" % __url__
    print "### credits: %s" % __credits__
    print "### date: %s" % __date__
    print "### version: %s" % __version__
    
def get_html_source( url , save=False):
    """ fetch the html source """
    class AppURLopener(urllib.FancyURLopener):
        version = __useragent__
    urllib._urlopener = AppURLopener()

    try:
        if os.path.isfile( url ): sock = open( url, "r" )
        else:
            urllib.urlcleanup()
            sock = urllib.urlopen( url )

        htmlsource = sock.read()
        if save: file( os.path.join( CACHE_PATH , save ) , "w" ).write( htmlsource )
        sock.close()
        return htmlsource
    except:
        print_exc()
        print "### ERROR impossible d'ouvrir la page %s" % url
        xbmcgui.Dialog().ok("ERROR" , "site unreacheable")
        return False

def get_nfo_id( path ):
    nfo= os.path.join(path , "tvshow.nfo")
    print "### nfo file: %s" % nfo
    nfo_read = file(repr(nfo).strip("u'\""), "r" ).read()
    tvdb_id = re.findall( "<tvdbid>(\d{1,10})</tvdbid>", nfo_read )
    if tvdb_id: 
        print "### tvdb id: %s" % tvdb_id[0]
        return tvdb_id[0]
    else:
        print "### no tvdb id found in: %s" % nfo
        return False

def listing():
    # sql statement for tv shows
    sql_data = "select tvshow.c00 , tvshow.c12 , path.strPath from tvshow , path , tvshowlinkpath where path.idPath = tvshowlinkpath.idPath AND tvshow.idShow = tvshowlinkpath.idShow"
    xml_data = xbmc.executehttpapi( "QueryVideoDatabase(%s)" % urllib.quote_plus( sql_data ), )
    print xml_data
    match = re.findall( "<field>(.*?)</field><field>(.*?)</field><field>(.*?)</field>", xml_data, re.DOTALL )
    print match[0]
    try:
        TVlist = []
        for import_base in match:
            #print import_base
            TVshow = {}
            TVshow["name"] = repr(import_base[0]).strip("'u")
            TVshow["id"] = repr(import_base[1]).strip("'u")
            TVshow["path"] = import_base[2]
            TVlist.append(TVshow)
        
        return TVlist
    except:
        print_exc()
        print "no tvdbid found in db"
        return False
        

def get_tvid_path( tvpath ):
    sql_data = 'select tvshow.c12 , path.strpath from tvshow,tvshowlinkpath,path where tvshow.idShow=tvshowlinkpath.idshow and tvshowlinkpath.idpath=path.idpath and path.strpath=\"%s\"' % (tvpath)
    xml_data = xbmc.executehttpapi( "QueryVideoDatabase(%s)" % urllib.quote_plus( sql_data ), )
    match = re.findall( "<field>(.*?)</field><field>(.*?)</field>", xml_data, re.DOTALL )
    try:
        return match[0][0] , match[0][1]
    except: 
        print_exc()
        return  "False" , "False" 
    
    
def get_first_logo( tvid ):
    #match = re.search("""<li><a href="(.*%s.*\.png)">.*?</a></li>""" % tvid , base_info)
    base_info = get_html_source( BASE_URL + tvid )
    match = re.search("""<logo url="(.*?)"/>""" , base_info)
    if match:
        logo_url = match.group(1)
        #getting first logo:
        multi_logo = re.search("(-\d)\.png" , logo_url )
        if multi_logo:
            print "### Detect multi logo, getting the first"
            logo_url = logo_url.replace ( multi_logo.group(1) , "")
        print "### logo: %s" % logo_url
        return logo_url
    else: 
        print "### No match"
        return False

def get_logo_list( tvid ):
    #match = re.findall("""<li><a href="(.*%s.*\.png)">.*?</a></li>""" % tvid , base_info)
    base_info = get_html_source( BASE_URL + tvid )
    match = re.findall("""<logo url="(.*?)"/>""" , base_info)
    if match: return match
    else: 
        print "### No logo found !"
        return False
    
def download_logo( url_logo , path , tvcount , name ):
    destination = os.path.join( path , "logo.png").replace("\\\\" , "\\").encode("utf-8")
    print "### download :" + url_logo , "### path: " + repr(destination).strip("'u")
     
    try:
        def _report_hook( count, blocksize, totalsize ):
            percent = int( float( count * blocksize * 100 ) / totalsize )
            strProgressBar = str( percent )
            #print percent  #DEBUG
            DIALOG_PROGRESS.update( tvcount , "Searching: %s " %  translate_string( name ) , "Downloading: %s" % percent )
        if os.path.exists(path.encode("utf-8")):
            fp , h = urllib.urlretrieve( url_logo , destination , _report_hook )
            #print h
            return True
    except :        
        print "### Logo download Failed !!! (download_logo)"
        print_exc()  
        return False
        
        
if ( __name__ == "__main__" ): 
     
    solo_mode = False
    footprints()
    try: 
        if sys.argv[ 1 ] : 
            DIALOG_PROGRESS.create( "Logo Downloader in action ..." , "Searching Logo ..." )
            solo_mode = True
    except: print "### No Args found"
    
    #base_info = get_html_source( BASE_URL )
    base_info = True
    
    if solo_mode:        
        print "### Starting solo Mode"
        logo_path = sys.argv[ 1 ]
        print "### path:%s###" % logo_path
        print "### Getting id"
        try: baseid , logo_path = get_tvid_path( sys.argv[ 1 ] )
        except: 
            baseid = False
            print_exc()
        print "### id Found: %s" % baseid
        if baseid:
            if baseid[0:2] == "tt" or baseid == "" : 
                print "### IMDB id found (%s) or no id found in db, checking for nfo" % logo_path
                try: tvid = get_nfo_id( logo_path )
                except:  
                    tvid = False              
                    print "### Error checking for nfo: %stvshow.nfo" % logo_path.replace("\\\\" , "\\").encode("utf-8")
                    print_exc()
            else: 
                tvid = baseid
            
            
            if tvid: 
                print "### tvdb id Found: %s" % tvid
                print "### get logo list for id:%s ###" % tvid
                logo_list = get_logo_list( tvid )
            else:
                print "### no tvdb id Found"
                logo_list = False
            if logo_list: 
                print "### %s" % logo_list
                DIALOG_PROGRESS.close
                select = xbmcgui.Dialog().select("choose logo to download" , logo_list)
                if select == -1: 
                    print "### Canceled by user"
                    xbmcgui.Dialog().ok("Canceled" , "Download canceled by user" )
                else:
                    DIALOG_PROGRESS.create( "Logo Downloader in action ..." , "Downloading ..." )
                    
                    url_logo = logo_list[select]
                    
                    if logo_path: 
                        full_logo_path = os.path.join( logo_path , "logo.png").replace("\\\\" , "\\").encode("utf-8")
                        print "### download logo: %s" % url_logo
                        print "### destination logo: %s" % full_logo_path
                        try:
                            def _report_hook( count, blocksize, totalsize ):
                                percent = int( float( count * blocksize * 100 ) / totalsize )
                                strProgressBar = str( percent )
                                #print percent  #DEBUG
                                DIALOG_PROGRESS.update( percent , "downloading: %s " %  logo_list[select] , "path: %s" % full_logo_path )
                            if os.path.exists(logo_path.encode("utf-8")):
                                fp , h = urllib.urlretrieve( url_logo , full_logo_path , _report_hook )
                                try: 
                                    import shutil
                                    cached_thumb = thumbnails.get_cached_video_thumb( full_logo_path).replace( "\\Video" , "").replace("tbn" , "png")
                                    print "cache %s" % cached_thumb
                                    shutil.copy2( full_logo_path , cached_thumb )
                                    xbmc.executebuiltin( 'XBMC.ReloadSkin()' )
                                except :
                                    print_exc()
                                    print "### cache erasing error"
                                #print h
                                DIALOG_PROGRESS.close
                                print "### Logo downloaded Successfully !!!"
                                xbmcgui.Dialog().ok("Success" , "Logo downloaded successfully !" )
                            else: 
                                print "### Logo download Failed !!!"
                                print_exc()
                                xbmcgui.Dialog().ok("Little Error" , "Error detecting path !" )
                                
                        except :
                            print_exc()
                            DIALOG_PROGRESS.close   
                            print "### Logo download error !!!"
                            xbmcgui.Dialog().ok("Error" , "Error downloading logo !" )
                    else: print "### Path not found"
            else: xbmcgui.Dialog().ok("Not Found" , "No logo found!" )
        else: xbmcgui.Dialog().ok("Error" , "Can't get logo from this view" )
        
    else:
        print "### Starting Bulk Mode"
        DIALOG_PROGRESS.create( "Logo Downloader in action ..." , "Getting info ..." )   
        TVshow_list = listing()
   
        if TVshow_list and base_info:
            total_tvshow = len(TVshow_list)
            tvcount = 0
            total_logo = 0
            downloaded = 0
            for TVshow in TVshow_list:
                tvcount = tvcount + 1
                ratio =  int (float( tvcount  * 100 ) / total_tvshow )
                print "### Checking %s TVshow: %s  id: %s" % ( ratio , translate_string( TVshow["name"] ) , TVshow["id"] )
                if TVshow["id"][0:2] == "tt" or TVshow["id"] == "": 
                    print "### IMDB id found in database(%s), checking for nfo" % TVshow["id"]
                    try: tvid = get_nfo_id( TVshow["path"] )
                    except:                
                        print "### Error checking for nfo: %stvshow.nfo" % TVshow["path"]
                        tvid = TVshow["id"]
                        print_exc()
                else : tvid = TVshow["id"]        
                DIALOG_PROGRESS.update( ratio , "Searching: %s " %  translate_string( TVshow["name"] ) , tvid )
                if ( DIALOG_PROGRESS.iscanceled() ): break
                if tvid == "" : 
                    print "### no id, skipping ..."
                    logo_url = False
                if os.path.isfile(os.path.join( TVshow["path"] , "logo.png").replace("\\\\" , "\\").encode("utf-8")):
                    print "### Logo.png already exist, skiping ..."
                    total_logo = total_logo + 1
                    logo_url = False
                else: 
                    print "### Search for a Logo..."
                    logo_url = get_first_logo( tvid )
                if logo_url: 
                    succes = download_logo( logo_url , TVshow["path"] , ratio , TVshow["name"] )
                    if succes: 
                        downloaded = downloaded + 1
                        total_logo = total_logo + 1
                        print "### Logo downloaded Successfully !!!"
                    else: print "### Logo download Failed !!!"
            DIALOG_PROGRESS.close
            reussite = int( float( total_logo  * 100 ) / total_tvshow ) 
            xbmcgui.Dialog().ok("Logo Downloader Finished ..." , " %s Logo Downloaded ! TVshow: %s" % ( downloaded , total_tvshow ) , "%s percent completed (%s logo found)" %  ( reussite , total_logo ) )
            print "### %s Logo Downloaded ! TVshow: %s" % (downloaded , total_tvshow)
        else: xbmcgui.Dialog().ok("Error" , "No tvshow find or error getting web page" )
print "### Exiting ..."    
    