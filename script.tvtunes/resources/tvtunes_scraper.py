# -*- coding: utf-8 -*-
__useragent__    ="Mozilla/5.0 (Windows; U; Windows NT 5.1; fr; rv:1.9.0.1) Gecko/2008070208 Firefox/3.6"
import urllib
import os
from traceback import print_exc
import re
import xbmc  
import xbmcaddon
import xbmcgui

try:
    # parse sys.argv for params
    print sys.argv[ 1 ]
    try:params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
    except:
        print_exc()
        params =  dict( sys.argv[ 1 ].split( "=" ))
except:
    # no params passed
    print_exc()
    params = {} 

__settings__ = xbmcaddon.Addon( "script.tvtunes" )
__cwd__  = __settings__.getAddonInfo('path')
RESOURCES_PATH = os.path.join( __cwd__ , "resources" )
SOURCEPATH = __cwd__

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

class TvTunes:
    def __init__(self):
        self.search_url = "http://www.televisiontunes.com/search.php?searWords=%s&Send=Search"
        self.download_url = "http://www.televisiontunes.com/download.php?f=%s"
        self.theme_file = "theme.mp3"
        self.TVlist = self.listing()
        self.DIALOG_PROGRESS = xbmcgui.DialogProgress()
        self.ERASE = xbmcgui.Dialog().yesno("TvTune downloader","Replace existing theme?")
        self.DIALOG_PROGRESS.create( "TelevisionTunes script in action ..." , "Getting informations ..." )
        if params.get("mode", "false" ) == "solo" : self.scan(params.get("name", "" ),params.get("path", "false" ))    
        else: self.scan()
        
    def scan(self , cur_name=False , cur_path=False):
        count = 0
        if cur_name and cur_path: 
            print "solo mode"
            self.TVlist = [[cur_name,cur_path.encode('utf-8')]]
        total = len(self.TVlist)        
        for show in self.TVlist:
            count = count + 1
            if not self.ERASE and os.path.exists(os.path.join(show[1],"theme.mp3")):
                print "### %s already exists, ERASE is set to %s" % (os.path.join(show[1],"theme.mp3"), [False,True][self.ERASE] )
            else:
                self.DIALOG_PROGRESS.update( (count*100)/total , "Searching for %s" % show[0] , "")
                if self.DIALOG_PROGRESS.iscanceled():
                    self.DIALOG_PROGRESS.close()
                    xbmcgui.Dialog().ok('CANCELED','Operation canceled by user.')
                    break
                theme_list = self.search_theme_list( show[0])
                #print theme_list
                if len(theme_list) == 1: theme_url = self.download_url % theme_list[0]["url"].replace("http://www.televisiontunes.com/", "").replace(".html" , "")
                else: theme_url = self.get_user_choice( theme_list , show[0] )
                if theme_url: self.download(theme_url , show[1])
            
    def download(self , theme_url , path):
        print "### download :" + theme_url
        destination = os.path.join( path , self.theme_file)
        try:
            def _report_hook( count, blocksize, totalsize ):
                percent = int( float( count * blocksize * 100 ) / totalsize )
                strProgressBar = str( percent )
                self.DIALOG_PROGRESS.update( percent , "Downloading: %s " % theme_url , "to: %s" % destination )
            if os.path.exists(path):
                fp , h = urllib.urlretrieve( theme_url , destination , _report_hook )
                print h
                self.DIALOG_PROGRESS.close
                return True
            else : print "problem with path: %s" % destination
        except :        
            print "### Theme download Failed !!!"
            print_exc()  
            return False 
               
    def get_user_choice(self , theme_list , showname):
        #### on cree la liste de choix de theme
        theme_url = False
        searchname = showname
        searchdic = { "name" : "Manual Search..."}
        theme_list.insert(0 , searchdic)
        while theme_url == False:
            
            select = xbmcgui.Dialog().select("Choose for %s" % searchname, [ theme["name"] for theme in theme_list ])
            if select == -1: 
                print "### Canceled by user"
                #xbmcgui.Dialog().ok("Canceled" , "Download canceled by user" )
                return False
            else:
                if theme_list[select]["name"] == "Manual Search...":
                    kb = xbmc.Keyboard(showname, 'ENTER MANUAL SEARCH', False)
                    kb.doModal()
                    result = kb.getText()
                    theme_list = self.search_theme_list(result)
                    searchname = result
                    theme_list.insert(0 , searchdic)
                else:
                    theme_url = self.download_url % theme_list[select]["url"].replace("http://www.televisiontunes.com/", "").replace(".html" , "")
                    print "### %s" % theme_url
                    listitem = xbmcgui.ListItem(theme_list[select]["name"])
                    listitem.setInfo('music', {'Title': theme_list[select]["name"]})
                    xbmc.Player().play(theme_url, listitem)
                    ok = xbmcgui.Dialog().yesno("TvTune downloader","Download this one?")
                    if not ok: theme_url = False
                    xbmc.executebuiltin('PlayerControl(Stop)')
                
        return theme_url
        
    def search_theme_list(self , showname):
        print "### Search for %s" % showname
        ### on nettoie le nom des caract pas cool (type ": , ; , ...")
        showname = showname.replace(":","")
        theme_list = []
        next = True
        url = self.search_url % urllib.quote_plus(showname)
        urlpage = ""
        while next == True:
            ### on recup le result de la recherche
            data = get_html_source( url + urlpage )
            print "### Search url: %s" % ( url + urlpage )
            ###on parse la recherche pour renvoyer une liste de dico
            match = re.search(r"1\.&nbsp;(.*)<br>", data)
            if match: data2 = re.findall('<a href="(.*?)">(.*?)</a>', match.group(1))
            else: 
                print "not theme found for %s" % showname
                data2 = ""
            for i in data2:
                theme = {}
                theme["url"] = i[0] or ""
                theme["name"] = i[1] or ""
                theme_list.append(theme)
            match = re.search(r'&search=Search(&page=\d)"><b>Next</b>', data)
            if match:
            	urlpage = match.group(1)
            else:
            	next = False
            print "### next page: %s" % next
        return theme_list

    def listing(self):
        # on recup la liste des series en biblio
        # sql statement for tv shows
        sql_data = "select tvshow.c00 , path.strPath from tvshow , path , tvshowlinkpath where path.idPath = tvshowlinkpath.idPath AND tvshow.idShow = tvshowlinkpath.idShow GROUP BY tvshow.c00"
        xml_data = xbmc.executehttpapi( "QueryVideoDatabase(%s)" % urllib.quote_plus( sql_data ), )
        match = re.findall( "<field>(.*?)</field><field>(.*?)</field>", xml_data, re.DOTALL )
        try:
            TVlist = []
            for import_base in match:
                try: TVlist.append( (import_base[0] , import_base[1] ) )
                except:
                    print "### error in listing()"
                    print_exc()
            return TVlist
        except:
            print "### nothing in get db"
            return False
            print_exc()    
              
if ( __name__ == "__main__" ):
    TvTunes()
    xbmcgui.Dialog().ok('TvTunes','You can help to get more theme on:' , "http://www.televisiontunes.com/")
# fp , h = urllib.urlretrieve("http://www.televisiontunes.com/download.php?f=Alias 1".replace(" " , "_" ) , os.path.join(SOURCEPATH , "theme.mp3"))
# print fp,h


