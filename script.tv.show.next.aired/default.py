# -*- coding: utf-8 -*-

__script__       = "TV-Show Next-Aired"
__addonID__      = "script.tv.show.next.aired"
__author__       = "Ppic, Frost"
__url__          = "http://code.google.com/p/passion-xbmc/"
__svn_url__      = "http://passion-xbmc.googlecode.com/svn/trunk/addons/script.tv.show.next.aired/"
__credits__      = "Team Passion-XBMC, http://passion-xbmc.org/"
__platform__     = "xbmc media center, [ALL]"
__date__         = "12-10-2010"
__version__      = "2.0.1"
__svn_revision__ = "$Revision: 875 $"
__useragent__ = "Mozilla/5.0 (Windows; U; Windows NT 5.1; fr; rv:1.9.0.1) Gecko/2008070208 Firefox/3.6"

import urllib
import os
import sys
from traceback import print_exc
import re
import socket
import xbmc
import xbmcgui
import time
from datetime import timedelta

DATA_PATH = xbmc.translatePath( "special://profile/addon_data/script.tv.show.next.aired/")
RESOURCES_PATH = os.path.join( os.getcwd() , "resources" )
sys.path.append( os.path.join( RESOURCES_PATH, "lib" ) )
if not os.path.exists(DATA_PATH): os.makedirs(DATA_PATH)

def footprints():
    print "### %s starting ..." % __script__
    print "### author: %s" % __author__
    print "### URL: %s" % __url__
    print "### credits: %s" % __credits__
    print "### date: %s" % __date__
    print "### version: %s" % __version__
footprints()

def get_html_source( url , save=False):
    """ fetch the html source """
    class AppURLopener(urllib.FancyURLopener):
        version = __useragent__
    urllib._urlopener = AppURLopener()
    succeed = 0
    while succeed < 5:
        try:
            urllib.urlcleanup()
            sock = urllib.urlopen( url )
            htmlsource = sock.read()
            if save: file( os.path.join( CACHE_PATH , save ) , "w" ).write( htmlsource )
            sock.close()
            succeed = 5
            return htmlsource
        except:
            succeed = succeed + 1
            print_exc()
            print "### ERROR impossible d'ouvrir la page %s ---%s---" % ( url , succeed)
    return ""

class NextAired:
    def __init__(self):
        self._parse_argv(  )
        self.nextlist = []
        testtime = os.path.join( DATA_PATH , "next_aired.db" )
        if os.path.isfile(testtime):
            if time.time() - os.path.getmtime(testtime) > 21600: # time in second for file peremption 43200=1/2day
                print "###db old more than 24h, rescanning..."
                self.scan_info()
            else : 
                print "###db less than 24, fetch local data..."
                self.current_show_data = self.get_list("next_aired.db")
                if self.current_show_data == "[]": self.scan_info()
        else: 
            print "###db doesn't exist, scanning for data..."
            self.scan_info()
        if self.current_show_data: 
            print "###data available"
            for show in self.current_show_data:
                if show.get("Next Episode" , False):
                    self.nextlist.append(show)
    #                 print "######################"
    #                 for i in show.keys():
    #                     print "###" + i + ": " + show[i]
            print "### next list: %s shows ### %s" % ( len(self.nextlist) , self.nextlist )
            self.nextlist = sorted( self.nextlist, key=lambda item: str( item.get( "RFC3339", "~" )  ).lower(), reverse=False )
            self.check_today_show()
            self.push_data()            
        else: print "### no current show data..."
        if self.PROGRESS:
            import next_aired_dialog
            next_aired_dialog.MyDialog(self.nextlist)
        if self.ALARM: self._set_alarm()
    
    def _parse_argv( self ):
        try:
            # parse sys.argv for params
            params = dict( arg.split( "=" ) for arg in sys.argv[ 1 ].split( "&" ) )
        except:
            # no params passed
            params = {}
        # set our preferences
        print params
        self.ALARM = int( params.get( "alarm", "0" ) )
        self.PROGRESS = params.get( "silent", True ) == True
    
    def _set_alarm( self ):
        # only run if user/skinner preference
        if self.ALARM == "0": return
        # set the alarms command
        command = "XBMC.RunScript(%s,silent=True&alarm=%d)" % ( os.path.join( os.getcwd(), __file__ ), self.ALARM, )
        xbmc.executebuiltin( "AlarmClock(NextAired,%s,%d,true)" % ( command, self.ALARM, ) )
        
    def check_today_show(self):
        self.todayshow = 0
        today = time.strftime('%b/%d/%Y',time.localtime()) 
        print time.strftime("%Y")
        for i in self.nextlist:
            print "################"
            print "###%s" % i.get("localname")
#             test = timedelta(i.get("RFC3339", "0")) - timedelta(time.strftime(strftime("%a, %d %b %Y %H:%M:%S +0000", gmtime())))
#             print test
            if str(i.get("Next Episode").split("^")[2]) == str(today): 
                self.todayshow = self.todayshow + 1
                print "TODAY"
                i["Today"] = "True"
            print "###%s" % i.get("Next Episode") 
            print "###%s" % i.get("RFC3339", "no rfc")
        print "today show: %s" % self.todayshow
        
    def push_data(self):
        # grab the home window
        self.WINDOW = xbmcgui.Window( 10000 )
        # reset Total property for visible condition
        self.WINDOW.setProperty( "NextAired.Total" , str(len(self.nextlist)) )
        self.WINDOW.setProperty( "NextAired.TodayTotal" , str(self.todayshow) )
        for count in range( len(self.nextlist) ):
            # we clear title for visible condition
            self.WINDOW.clearProperty( "NextAired.%d.Title" % ( count + 1, ) )
        for count, current_show in enumerate( self.nextlist ): 
            #print "###%d %s" % ( count + 1 , current_show["localname"] )
            self.WINDOW.setProperty( "NextAired.%d.Today" % ( count + 1, ), current_show.get( "Today" , "False"))
            self.WINDOW.setProperty( "NextAired.%d.ShowTitle" % ( count + 1, ), current_show.get( "localname", "" ))
            next = current_show.get( "Next Episode").split("^")
            self.WINDOW.setProperty( "NextAired.%d.NextDate" % ( count + 1, ), next[2] or "")
            self.WINDOW.setProperty( "NextAired.%d.NextTitle" % ( count + 1, ), next[1] or "")
            self.WINDOW.setProperty( "NextAired.%d.NextNumber" % ( count + 1, ), next[0] or "")
            latest = current_show.get("Latest Episode").split("^")
            self.WINDOW.setProperty( "NextAired.%d.LatestDate" % ( count + 1, ), latest[2] or "")
            self.WINDOW.setProperty( "NextAired.%d.LatestTitle" % ( count + 1, ), latest[1] or "")
            self.WINDOW.setProperty( "NextAired.%d.LatestNumber" % ( count + 1, ), latest[0] or "")            
            self.WINDOW.setProperty( "NextAired.%d.Airtime" % ( count + 1, ), current_show.get("Airtime", "" )) 
            self.WINDOW.setProperty( "NextAired.%d.Showpath" % ( count + 1, ), current_show.get("path", "" ))
            self.WINDOW.setProperty( "NextAired.%d.Status" % ( count + 1, ), current_show.get("Status", "" ))
            self.WINDOW.setProperty( "NextAired.%d.ep_img" % ( count + 1, ), current_show.get("ep_img", "" ))
            self.WINDOW.setProperty( "NextAired.%d.Network" % ( count + 1, ), current_show.get("Network", "" ))
            self.WINDOW.setProperty( "NextAired.%d.Started" % ( count + 1, ), current_show.get("Started", "" ))
            self.WINDOW.setProperty( "NextAired.%d.Classification" % ( count + 1, ), current_show.get("Classification", "" ))
            self.WINDOW.setProperty( "NextAired.%d.Genres" % ( count + 1, ), current_show.get("Genres", "" ))
            self.WINDOW.setProperty( "NextAired.%d.Premiered" % ( count + 1, ), current_show.get("Premiered", "" ))
            self.WINDOW.setProperty( "NextAired.%d.Country" % ( count + 1, ), current_show.get("Country", "" ))
            self.WINDOW.setProperty( "NextAired.%d.Runtime" % ( count + 1, ), current_show.get("Runtime", "" ))
            
    def scan_info(self):
        if self.PROGRESS: 
            DIALOG_PROGRESS = xbmcgui.DialogProgress()
            DIALOG_PROGRESS.create( "TV Show - Next Aired script in action ..." , "Getting informations ..." )
        socket.setdefaulttimeout(10)
        self.total_reaquest = 0
        self.total_next_found = 0
        self.total_error = 0 
        self.total_canceled = 0
        self.total_current = 0
        self.total_error = 0
        self.count = 0
        self.current_show_data = []
        self.canceled = self.get_list("canceled.db")
        if not self.listing(): close("erreur listing")
        self.total_show = len(self.TVlist)
        print "###canceled list: %s " % self.canceled

        for show in self.TVlist:
            current_show = {}
            self.count = self.count +1
            if self.PROGRESS:
                percent = int( float( self.count * 100 ) / self.total_show )
                DIALOG_PROGRESS.update( percent , "Getting informations ..." , "%s" % show[0] )
                if DIALOG_PROGRESS.iscanceled():
                    DIALOG_PROGRESS.close()
                    xbmcgui.Dialog().ok('CANCELED','Operation canceled by user.')
                    break
            print "###%s" % show[0]
            current_show["localname"] = show[0]
            current_show["path"] = show[1]
            if show[0] in self.canceled: print "### %s canceled/Ended" % show[0]
            else:
                self.get_show_info( current_show )
                print current_show
                if current_show.get("Status") == "Canceled/Ended": self.canceled.append(current_show["localname"])
                else: self.current_show_data.append(current_show)
             
        self.save_file( self.canceled , "canceled.db")
        self.save_file( self.current_show_data , "next_aired.db")
        if self.PROGRESS:DIALOG_PROGRESS.close
        
    def get_show_info( self , current_show ):
        print "### get info %s" % current_show["localname"]
        # get info for show with exact name
        print "### searching for %s" % current_show["localname"]
        print "###search url: http://services.tvrage.com/tools/quickinfo.php?show=%s" % urllib.quote_plus( current_show["localname"] )  #DEBUG
        result_info = get_html_source( "http://services.tvrage.com/tools/quickinfo.php?show=%s" % urllib.quote_plus( current_show["localname"]))
        print "### parse informations"
        #print "### %s" % result_info
        result = re.findall("(?m)(.*)@(.*)", result_info)
        current_show["ep_img"] = os.path.join( current_show["path"] , "folder.jpg" )
        if result:
            # get short tvshow info and next aired episode
            for item in result:
                current_show[item[0].replace("<pre>" , "")] = item[1]
                #print "### %s : %s " % ( item[0].replace("<pre>" , "") , item[1] ) #DEBUG
        
            
    def get_list(self , listname ):
        path = os.path.join( DATA_PATH , listname )
        if os.path.isfile(path):
            print "### Load list: %s" % path
            return self.load_file(path)
        else:
            print "### Load list: no file found! generating %s !" % listname
            return []
    
    def load_file( self , file_path ):
        try:
            return eval( file( file_path, "r" ).read() )
        except:
            print_exc()
            print "### ERROR impossible de charger le fichier %s" % temp
            return "[]"
            
    def save_file( self , txt , filename):
        path = os.path.join( DATA_PATH , filename )
        try:
            if txt:file( path , "w" ).write( repr( txt ) )
        except:
            print_exc()
            print "### ERROR impossible d'enregistrer le fichier %s" % DATA_PATH    
        
    def listing(self):
        # sql statement for tv shows
        sql_data = "select tvshow.c00 , path.strPath from tvshow , path , tvshowlinkpath where path.idPath = tvshowlinkpath.idPath AND tvshow.idShow = tvshowlinkpath.idShow GROUP BY tvshow.c00"
        xml_data = xbmc.executehttpapi( "QueryVideoDatabase(%s)" % urllib.quote_plus( sql_data ), )
        match = re.findall( "<field>(.*?)</field><field>(.*?)</field>", xml_data, re.DOTALL )
        try:
            self.TVlist = []
            for import_base in match:
                try: self.TVlist.append( (import_base[0] , import_base[1] ) )
                except:
                    print "### error in listing()"
                    print_exc()
            return True
        except:
            print "### nothing in get db"
            return False
            print_exc()

    def close(self , msg ):
        print msg
        exit


NextAired()

