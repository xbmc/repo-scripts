__script__       = "Logo Downloader"
__author__       = "Ppic"
__url__          = "http://code.google.com/p/passion-xbmc/"
__svn_url__      = ""
__credits__      = "Team XBMC PASSION, http://passion-xbmc.org/"
__platform__     = "xbmc media center, [LINUX, OS X, WIN32, XBOX]"
__date__         = "02-10-2010"
__version__      = "2.1.1"
__svn_revision__  = "$Revision: 000 $"
__XBMC_Revision__ = "30000" #XBMC Babylon
__useragent__ = "Logo downloader %s" % __version__

##################################### HOW TO USE / INTEGRATE IN SKIN #####################################
# for automatically download the script from xbmc, include this in your addon.xml:
# 
#   <requires>
# 	<import addon="script.logo-downloader" version="2.0.0"/>
#   </requires>
#   
# for solo mode (usually used from videoinfodialog) , $INFO[ListItem.TVShowTitle] is required.
# exemple to launch:
# <onclick>XBMC.RunScript(script.logo-downloader,mode=solo,logo=True,clearart=True,showthumb=True,showname=$INFO[ListItem.TVShowTitle])</onclick>
# 
# for bulk mode, no particular info needed, just need a button to launch from where you want.
# exemple to launch:
# <onclick>XBMC.RunScript(script.logo-downloader,mode=bulk,clearart=True,logo=True,showthumb=True)</onclick>
# 
# you can replace boolean by skin settings to activate / deactivate images types.
###########################################################################################################

import urllib
import os
import re
from traceback import print_exc
import xbmc
import xbmcgui
import shutil

SOURCEPATH = os.getcwd()
RESOURCES_PATH = os.path.join( SOURCEPATH , "resources" )
DIALOG_DOWNLOAD = xbmcgui.DialogProgress()
ACTION_PREVIOUS_MENU = 10
sys.path.append( os.path.join( RESOURCES_PATH, "lib" ) )
from file_item import Thumbnails
thumbnails = Thumbnails()

if xbmc.executehttpapi( "GetLogLevel()" ).strip("<li>") == "2": DEBUG = True
else: DEBUG = False

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
        
class downloader:
    def __init__(self):
        print "### DEBUG: %s" % DEBUG
        print "### logo downloader initializing..."
        self.clearart = False
        self.logo = False
        self.show_thumb = False
        self.mode = ""
        self.reinit()
        if DEBUG:
            print sys.argv    
            try: print("arg 0: %s" % sys.argv[0])
            except:   print "no arg0"
            try: print("arg 1: %s" % sys.argv[1])
            except:   print "no arg1"
            try: print("arg 2: %s" % sys.argv[2])
            except:   print "no arg2"
            try: print("arg 3: %s" % sys.argv[3])
            except:   print "no arg3"
            try: print("arg 4: %s" % sys.argv[4])
            except:   print "no arg4"
            try: print("arg 5: %s" % sys.argv[5])
            except:   print "no arg5"    
        
        for item in sys.argv:
            match = re.search("mode=(.*)" , item)
            if match: self.mode = match.group(1)            
            match = re.search("clearart=(.*)" , item)
            if match: 
                if not match.group(1) == "False": self.clearart = match.group(1)
                else: pass
            match = re.search("logo=(.*)" , item)
            if match: 
                if not match.group(1) == "False": self.logo = match.group(1)
                else: pass
            match = re.search("showthumb=(.*)" , item)
            if match:
                if not match.group(1) == "False": self.show_thumb = match.group(1)
                else: pass
            match = re.search("showname=" , item)
            if match: self.show_name = item.replace( "showname=" , "" )
            else: pass
        
        if self.mode == "solo": 
            if DEBUG: print "### Start Solo Mode"
            self.solo_mode()
        elif self.mode == "bulk": 
            if DEBUG: print "### Start Bulk Mode"
            self.bulk_mode()
            
    def solo_mode(self):
        self.get_tvid_path()
        self.id_verif()
        self.type_list = []
        if self.logo:self.type_list.append ("logo")
        if self.clearart:self.type_list.append ("clearart")
        if self.show_thumb:self.type_list.append ("showthumb")
        
        if self.choice_type():
            self.image_list = False
            if self.logo:
                self.filename = "logo.png"
                self.get_lockstock_xml()
                self.search_logo()
            elif self.clearart: 
                self.filename = "clearart.png"
                self.get_xbmcstuff_xml()
                self.search_clearart()
            elif self.show_thumb:
                self.filename = "folder.jpg"
                self.get_xbmcstuff_xml()
                self.search_show_thumb()
            
            if self.image_list: 
                if self.choose_image(): 
                    if DEBUG: self.print_class_var()
                    if self.download_image(): xbmcgui.Dialog().ok("Success" , "Download successfull" )
                    else: xbmcgui.Dialog().ok("Error" , "Error downloading file" )
            
    def bulk_mode(self):
        if DEBUG: print "### get tvshow list"
        DIALOG_PROGRESS = xbmcgui.DialogProgress()
        DIALOG_PROGRESS.create( "SCRIPT LOGO DOWNLOADER", "checking database ...")
        self.logo_found = 0
        self.logo_download = 0
        self.thumb_found = 0
        self.thumb_download = 0
        self.clearart_found = 0
        self.clearart_download = 0
        self.TV_listing()
        
        print "###clearart#%s###" % self.clearart
        print "###logo#%s###" % self.logo
        print "###show_thumb#%s###" % self.show_thumb
        
        for currentshow in self.TVlist:
            print "####################"    
            if DIALOG_PROGRESS.iscanceled():
                DIALOG_PROGRESS.close()
                xbmcgui.Dialog().ok('CANCELED','Operation canceled by user.')
                break
            try:
                self.show_path = currentshow["path"]
                self.tvdbid = currentshow["id"]
                self.show_name = currentshow["name"]   
                print "### show_name: %s" % self.show_name 
                if DEBUG: print "### tvdbid: %s" % self.tvdbid ,"### show_path: %s" % self.show_path        
                if DEBUG: print u"### check id"
                self.id_verif()
                
                if self.logo:
                    if DEBUG: print "### Search logo for %s" % self.show_name
                    self.filename = "logo.png"
                    if not os.path.exists( os.path.join( self.show_path , self.filename ) ):
                        if DEBUG: print "### get lockstock xml"
                        self.get_lockstock_xml()
                        if self.search_logo():
                            if DEBUG: print "### found logo for %s" % self.show_name
                            if self.download_image():
                                self.logo_download = self.logo_download +1
                                if DEBUG: print "### logo downloaded for %s" % self.show_name
                    else: 
                        if DEBUG: print "### %s already exist, skipping" % self.filename
                        self.logo_found = self.logo_found + 1
                    self.image_url = False
                    self.filename = False
                    
                if self.clearart or self.show_thumb: 
                    if DEBUG: print "### get xbmcstuff xml"
                    self.get_xbmcstuff_xml()
                
                if self.clearart:
                    if DEBUG: print "### Search clearart for %s" % self.show_name
                    self.filename = "clearart.png"
                    if not os.path.exists( os.path.join( self.show_path , self.filename ) ):
                        if self.search_clearart():
                            if DEBUG: print "### found clearart for %s" % self.show_name
                            if self.download_image():
                                self.clearart_download = self.clearart_download +1
                                if DEBUG: print "### clearart downloaded for %s" % self.show_name
                    else: 
                        self.clearart_found = self.clearart_found +1
                        if DEBUG: print "### %s already exist, skipping" % self.filename
                    self.image_url = False
                    self.filename = False
                    
                if self.show_thumb:
                    if DEBUG: print "### Search showthumb for %s" % self.show_name
                    self.filename = "folder.jpg"
                    if not os.path.exists( os.path.join( self.show_path , self.filename ) ):
                        if self.search_show_thumb():
                            if DEBUG: print "### found show thumb for %s" % self.show_name
                            if self.download_image():
                                self.thumb_download = self.thumb_download +1
                                if DEBUG: print "### showthumb downloaded for %s" % self.show_name
                    else: 
                        self.thumb_found = self.thumb_found + 1
                        if DEBUG: print "### %s already exist, skipping" % self.filename
                    self.image_url = False
                    self.filename = False
                    
                self.reinit()
            except:
                print "error with: %s" % currentshow
                print_exc()
        DIALOG_PROGRESS.close()
        print "total tvshow = %s" % len(self.TVlist) 
        print "logo found = %s" % self.logo_found
        print "logo download = %s" % self.logo_download
        print "thumb found = %s" % self.thumb_found
        print "thumb download = %s" % self.thumb_download
        print "clearart found = %s" % self.clearart_found
        print "clearart download = %s" % self.clearart_download
        xbmcgui.Dialog().ok('SUMMARY %s TVSHOWS' % len(self.TVlist) , 'DOWNLOADED: logo: %s clearart: %s thumb: %s' % ( self.logo_download , self.clearart_download , self.thumb_download ) , 'FOUND: logo: %s clearart: %s thumb: %s' % ( self.logo_found , self.clearart_found , self.thumb_found ))
                
    def reinit(self):
        if DEBUG: print "### reinit"
        self.show_path = False
        self.tvdbid = False
        self.show_name = ""
        self.xbmcstuff_xml = False
        self.lockstock_xml = False
    
    def print_class_var(self):
        try: print "###show name: %s" % self.show_name
        except: print "###show name:"
        try: print "###mode: %s" % self.mode
        except: print "###mode:"
        try: print "###clearart: %s" % self.clearart
        except: print "###clearart:"
        try: print "###logo: %s" % self.logo
        except: print "###logo:"
        try: print "###thumb: %s" % self.show_thumb
        except: print "###thumb:"
        try: print "###show path: %s" % self.show_path
        except: print "###show path:"
        try: print "###id: %s" % self.tvdbid
        except: print "###id:"
        try: print "###lockstock xml: %s" % self.lockstock_xml
        except: print "###lockstock xml:"
        try: print "###image list: %s" % self.image_list
        except: print "###image list:"
        try: print "###image url: %s" % self.image_url
        except: print "###image url:"
        try: print "###filename: %s" % self.filename
        except: print "###filename:"
        try: print "###xbmcstuff_xml: %s" % self.xbmcstuff_xml
        except: print "###xbmcstuff_xml:"
               
    def TV_listing(self):
        # sql statement for tv shows
        sql_data = "select tvshow.c00 , tvshow.c12 , path.strPath from tvshow , path , tvshowlinkpath where path.idPath = tvshowlinkpath.idPath AND tvshow.idShow = tvshowlinkpath.idShow"
        xml_data = xbmc.executehttpapi( "QueryVideoDatabase(%s)" % urllib.quote_plus( sql_data ), )
        if DEBUG: print "### xml data: %s" % xml_data
        match = re.findall( "<field>(.*?)</field><field>(.*?)</field><field>(.*?)</field>", xml_data, re.DOTALL )
        
        try:
            self.TVlist = []
            for import_base in match:
                try:
                    if DEBUG: print import_base
                    TVshow = {}
                    TVshow["name"] = repr(import_base[0]).strip("'u")
                    TVshow["id"] = repr(import_base[1]).strip("'u")
                    TVshow["path"] = import_base[2]
                    self.TVlist.append(TVshow)
                except: print_exc()
        except:
            print_exc()
            print "### no tvshow found in db"
    
    def get_tvid_path( self ):
        sql_data = 'select tvshow.c12 , path.strpath from tvshow,tvshowlinkpath,path where tvshow.idShow=tvshowlinkpath.idshow and tvshowlinkpath.idpath=path.idpath and tvshow.c00=\"%s\"' % (self.show_name)
        xml_data = xbmc.executehttpapi( "QueryVideoDatabase(%s)" % urllib.quote_plus( sql_data ), )
        match = re.findall( "<field>(.*?)</field><field>(.*?)</field>", xml_data, re.DOTALL )
        try:
            self.tvdbid =  match[0][0]
            self.show_path =  match[0][1]
        except: 
            print_exc()
        if DEBUG: 
            print "sql dat: %s" % sql_data
            print "xml dat: %s" % xml_data
            
    def id_verif(self):
        if self.tvdbid[0:2] == "tt" or self.tvdbid == "" :
            print "### IMDB id found (%s) or no id found in db, checking for nfo" % self.show_path
            try: self.tvdbid = self.get_nfo_id()
            except:  
                self.tvdbid = False              
                print "### Error checking for nfo: %stvshow.nfo" % self.show_path.replace("\\\\" , "\\").encode("utf-8")
                print_exc()
                
    def get_nfo_id( self ):
        nfo= os.path.join(self.show_path , "tvshow.nfo")
        print "### nfo file: %s" % nfo
        nfo_read = file(repr(nfo).strip("u'\""), "r" ).read()
        tvdb_id = re.findall( "<tvdbid>(\d{1,10})</tvdbid>", nfo_read )
        if tvdb_id: 
            print "### tvdb id: %s" % tvdb_id[0]
            return tvdb_id[0]
        else:
            print "### no tvdb id found in: %s" % nfo
            return False
    
    def get_lockstock_xml(self):
        self.lockstock_xml = get_html_source( "http://www.lockstockmods.net/logos/getlogo.php?id=" + self.tvdbid )
    
    def get_xbmcstuff_xml(self):
        self.xbmcstuff_xml = get_html_source ("http://www.xbmcstuff.com/tv_scraper.php?&id_scraper=p7iuVTQXQWGyWXPS&size=big&thetvdb=" + self.tvdbid )

    def search_logo( self ):
        match = re.findall("""<logo url="(.*?)"/>""" , self.lockstock_xml)
        if match: 
            if self.mode == "solo" : self.image_list = match
            if self.mode == "bulk" : self.image_url = match[0]
            return True
        else: 
            print "### No logo found !"
            if self.mode == "solo": xbmcgui.Dialog().ok("Not Found" , "No logo found!" )
            self.image_list = False
            return False
            
    def search_clearart( self ):
        match = re.findall("<clearart>(.*)</clearart>" , self.xbmcstuff_xml)
        if match: 
            if self.mode == "solo" : self.image_list = match
            if self.mode == "bulk" : self.image_url = match[0]
            return True
        else: 
            print "### No clearart found !"
            if self.mode == "solo": xbmcgui.Dialog().ok("Not Found" , "No clearart found!" )
            self.image_list = False
            return False
            
    def search_show_thumb( self ):
        match = re.findall("<tvthumb>(.*)</tvthumb>" , self.xbmcstuff_xml)
        if match: 
            if self.mode == "solo" : self.image_list = match
            if self.mode == "bulk" : self.image_url = match[0]
            return True
        else: 
            print "### No show thumb found !"
            if self.mode == "solo": xbmcgui.Dialog().ok("Not Found" , "No show thumb found!" )
            self.image_list = False
            return False
        
    def choice_type(self):
        select = xbmcgui.Dialog().select("choose what to download" , self.type_list)
        if select == -1: 
            print "### Canceled by user"
            xbmcgui.Dialog().ok("Canceled" , "Download canceled by user" )
            return False
        else:
            if self.type_list[select] == "logo" : self.clearart , self.show_thumb = False , False
            elif self.type_list[select] == "showthumb" : self.clearart , self.logo = False , False
            elif self.type_list[select] == "clearart" : self.show_thumb , self.logo = False , False
            return True
            
    def choose_image(self):
        #select = xbmcgui.Dialog().select("Which one to download ?" , self.image_list)
        if DEBUG: print self.image_list
        self.image_url = MyDialog(self.image_list)
        if self.image_url: return True
        else: return False
#         if select == -1: 
#             print "### Canceled by user"
#             xbmcgui.Dialog().ok("Canceled" , "Download canceled by user" )
#             self.image_url = False
#             return False
#         else:
#             self.image_url = self.image_list[select]
#             return True
    
    def erase_current_cache(self):
        try: 
            
            if not self.filename == "folder.jpg": cached_thumb = thumbnails.get_cached_video_thumb( os.path.join( self.show_path , self.filename )).replace( "\\Video" , "").replace("tbn" , "png")
            else: cached_thumb = thumbnails.get_cached_video_thumb(self.show_path)
            print "### cache %s" % cached_thumb
            shutil.copy2( os.path.join( self.show_path , self.filename ) , cached_thumb )
            xbmc.executebuiltin( 'XBMC.ReloadSkin()' )
        except :
            print_exc()
            print "### cache erasing error"
    
    def download_image( self ):
        DIALOG_DOWNLOAD.create( "Downloading: %s " % self.show_name , "Getting info ..." )
        destination = os.path.join( self.show_path , self.filename )
        print "### download :" + self.image_url 
        if DEBUG: "### path: " + repr(destination).strip("'u")
         
        try:
            def _report_hook( count, blocksize, totalsize ):
                percent = int( float( count * blocksize * 100 ) / totalsize )
                strProgressBar = str( percent )
                if DEBUG: print percent  #DEBUG
                DIALOG_DOWNLOAD.update( percent , "Downloading: %s " % self.show_name , "Downloading: %s" % self.filename )
            if os.path.exists(self.show_path):
                fp , h = urllib.urlretrieve( self.image_url.replace(" ", "%20") , destination , _report_hook )
                if DEBUG: print h
                DIALOG_DOWNLOAD.close
                if self.mode == "solo": self.erase_current_cache()
                return True
            else : print "problem with path: %s" % self.show_path
        except :        
            print "### Image download Failed !!! (download_logo)"
            print_exc()  
            return False
                       
class MainGui( xbmcgui.WindowXMLDialog ):
    def __init__( self, *args, **kwargs ):
        xbmcgui.WindowXMLDialog.__init__( self, *args, **kwargs )
        xbmc.executebuiltin( "Skin.Reset(AnimeWindowXMLDialogClose)" )
        xbmc.executebuiltin( "Skin.SetBool(AnimeWindowXMLDialogClose)" )
        self.listing = kwargs.get( "listing" )

    def onInit(self):
        try :
            self.img_list = self.getControl(6)
            self.img_list.controlLeft(self.img_list)
            self.img_list.controlRight(self.img_list)
            
            self.getControl(3).setVisible(False)
        except :
            print_exc()
            self.img_list = self.getControl(3)
        
        self.getControl(5).setVisible(False)
        
        for image in self.listing :
            listitem = xbmcgui.ListItem( image.split("/")[-1] )
            listitem.setIconImage( image )
            listitem.setLabel2(image)
            print image
            self.img_list.addItem( listitem )
        self.setFocus(self.img_list)

    def onAction(self, action):
        #Close the script
        if action == ACTION_PREVIOUS_MENU :
            self.close() 
        
    def onClick(self, controlID):
        print controlID
        """
            Notice: onClick not onControl
            Notice: it gives the ID of the control not the control object
        """
        #action sur la liste
        if controlID == 6 or controlID == 3: 
            #Renvoie l'item selectionne
            num = self.img_list.getSelectedPosition()
            print num
            self.selected_url = self.img_list.getSelectedItem().getLabel2()
            self.close()
            
    def onFocus(self, controlID):
        pass

def MyDialog(tv_list):
    w = MainGui( "DialogSelect.xml", SOURCEPATH, listing=tv_list )
    w.doModal()
    try: return w.selected_url
    except: 
        print_exc()
        return False
    del w
    
if ( __name__ == "__main__" ): 
    footprints()
    downloader()
    print "### logo downloader exiting..."    