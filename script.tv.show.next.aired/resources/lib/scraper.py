
__useragent__ = "Mozilla/5.0 (Windows; U; Windows NT 5.1; fr; rv:1.9.0.1) Gecko/2008070208 Firefox/3.6"

import urllib
import os 
import re
import sys
from traceback import print_exc
import xbmc
import xbmcgui
import time
import socket

SOURCEPATH = os.getcwd()
DATA_PATH = xbmc.translatePath( "special://profile/addon_data/script.tv.show.next.aired/")

RESOURCES_PATH = os.path.join( SOURCEPATH , "resources" )
CACHE_PATH = os.path.join( DATA_PATH , "cache" )
IMAGES_PATH = os.path.join( DATA_PATH , "images" )
dialog = xbmcgui.Dialog()
canceled_path = os.path.join (DATA_PATH , "canceled.db")
next_aired_path = os.path.join (DATA_PATH , "next_aired.db")
search_name = ""
if not os.path.exists(CACHE_PATH): os.makedirs(CACHE_PATH)
if not os.path.exists(IMAGES_PATH): os.makedirs(IMAGES_PATH)

from convert import translate_string
from file_item import Thumbnails
thumbnails = Thumbnails()

socket.setdefaulttimeout(10)


fr = ["janvier" , "février" , "mars" , "avril" , "mai" , "juin" , "juillet" , "août" , "septembre" , "octobre" , "novembre" , "décembre" , "Lundi" , "Mardi" , "Mercredi" , "Jeudi" , "Vendredi" , "Samedi" , "Dimanche"]
us = ["January" , "February" , "March" , "April" , "May" , "June" , "July" , "August" , "September" , "October" , "November" , "December" , "Monday" , "Tuesday" , "Wednesday" , "Thursday" , "Friday" , "Saturday" , "Sunday"]



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
            #time.sleep(1)
            #dialog.ok("ERROR" , "TVrage.com might be down")
            
    return ""

def save_file( txt , temp):
    try:
        if txt:file( temp , "w" ).write( repr( txt ) )
    except:
        print_exc()
        print "### ERROR impossible d'enregistrer le fichier %s" % temp

def load_file( file_path ):
    try:
        temp_data = eval( file( file_path, "r" ).read() )
    except:
        print_exc()
        print "### ERROR impossible de charger le fichier %s" % temp
        temp_data = False
    return temp_data

def convert_date(date):
    for i in range(len(us)):
        date = date.replace( fr[i] , us[i] )
    return date

def listing():
    # sql statement for tv shows
    sql_data = "select tvshow.c00 , path.strPath from tvshow , path , tvshowlinkpath where path.idPath = tvshowlinkpath.idPath AND tvshow.idShow = tvshowlinkpath.idShow"
    xml_data = xbmc.executehttpapi( "QueryVideoDatabase(%s)" % urllib.quote_plus( sql_data ), )
    match = re.findall( "<field>(.*?)</field><field>(.*?)</field>", xml_data, re.DOTALL )

    try:
        TVlist = []
        for import_base in match:
            try: 
                TVlist.append( (translate_string(import_base[0]).encode("utf-8") , import_base[1] ) )
                print "### %s" % import_base[1]
            except:
                print "### error in listing()"
                try: print "### %s" % import_base[1]
                except: pass
                print_exc()
        return TVlist
    except:
        print "nothing in get db"
        return False
        print_exc()

def quick_search( search_name ):
    # get info for show with exact name
    print "### searching for %s" % search_name
    print "###search url: http://services.tvrage.com/tools/quickinfo.php?show=%s" % urllib.quote_plus( search_name )  #DEBUG
    result_info = get_html_source( "http://services.tvrage.com/tools/quickinfo.php?show=%s" % urllib.quote_plus( search_name))
    print "### parse informations"
    #print dict( re.findall( "(?m)(.*)@(.*)", result_info.strip( "<pre>\n" ) ) )
    #print "-"*100
    result = re.findall("(?m)(.*)@(.*)", result_info)
    if result:
        episode = {}
        # get short tvshow info and next aired episode
        for item in result:
            episode[item[0].replace("<pre>" , "")] = item[1]
            #print "### %s : %s " % ( item[0].replace("<pre>" , "") , item[1] ) #DEBUG
        return episode
    elif re.search("No Show Results" , result_info ):
        print "### no tvshow found !"
        return False

def get_list(path):
    if os.path.isfile(path):
        print "### Load list: %s" % path
        result = load_file(path)
    else:
        print "### Load list: no file found! generating one !"
        result = []
    return result

def existing_data(showname,next_aired_list):
    for show in next_aired_list:

        if show["dbname"] == showname:
            print show["dbname"]
            print showname
            #current = next_aired_list.pop(next_aired_list.index(show))
            return show
    return False

def getDetails( user_request="" ):
    # recherche manuel, user_request pas implanter
    DIALOG_PROGRESS = xbmcgui.DialogProgress()
    cancel_add = 0
    request_num = 0
    next_num = 0
    total_not_found = 0
    count = 0
    errornum = 0
    DIALOG_PROGRESS.create( "TV Show - Next Aired script in action ..." , "Getting informations ..." )
    list_tv = listing()
    print "### %s" % listing()
    total_show = len(list_tv)
    canceled = get_list(canceled_path)
    next_aired_list = []

    for show in list_tv:
        count = count +1
        percent = int( float( count * 100 ) / total_show )
        DIALOG_PROGRESS.update( percent , "Getting informations ..." , "%s" % translate_string(show[0]) )
        if show[0] in canceled :
            infos = False
            print "### Skipping %s, on canceled list ..." % translate_string(show[0])
        elif existing_data(show[0],next_aired_list):
            "### %s existing infos, already in listing" % translate_string(show[0])
            infos = existing_data(show[0],next_aired_list)
            print infos
        else: 
            request_num = request_num + 1
            infos = quick_search( show[0] )
            if infos == "error": 
                total_url_error = total_url_error + 1
                infos = False

        if infos:
            if infos['Status'] == "Canceled/Ended":
                print "##### CANCELED / ENDED #####"
                canceled.append(show[0])
                cancel_add = cancel_add + 1
            if infos.has_key('Next Episode'):
                next_num = next_num + 1
                infos["dbname"] = show[0]
                infos["ep_img"] = thumbnails.get_cached_video_thumb( show[1] )
                infos['Show path'] = show[1]
                try:
                    print "##### NEXT AIRED INFOS##### Show Path: %s" % infos['Show path']
                    print "##### NEXT AIRED INFOS##### Show Name: %s" % infos['Show Name']
                    print "##### NEXT AIRED INFOS##### Status: %s" % infos['Status']
                    print "##### NEXT AIRED INFOS##### Started: %s" % infos['Started']
                    print "##### NEXT AIRED INFOS##### Next Episode: %s" % infos['Next Episode']
                    print "##### NEXT AIRED INFOS##### Latest Episode: %s" % infos['Latest Episode']
                    print "##### NEXT AIRED INFOS##### Network: %s" % infos['Network']
                    print "##### NEXT AIRED INFOS##### Airtime: %s" % infos['Airtime']
                    print "##### NEXT AIRED INFOS##### Country: %s" % infos['Country']
                    print "##### NEXT AIRED INFOS##### ep_img: %s" % infos["ep_img"]
                    print "##### NEXT AIRED INFOS##### Genres: %s" % infos["Genres"]
                    print "##### NEXT AIRED INFOS##### Runtime: %s" % infos["Runtime"]
                except:
                    print_exc()
                next_aired_list.append(infos)
                #display.display( infos )
            else: print "### %s: %s" % ( infos['Show Name'] , infos['Status'] )
        else: total_not_found = total_not_found + 1

    print "### Saving lists..."
    save_file( canceled , canceled_path)
    save_file( next_aired_list , next_aired_path)

    total_canceled = len(canceled)
    total_not_found = int(total_not_found) - int(total_canceled) + int(cancel_add)
    print "### Total TVshow: %s " % total_show
    print "### Total Next aired info: %s " % next_num
    print "### Total Canceled: %s " % total_canceled
    print "### Total request: %s " % request_num
    print "### Total Canceled added: %s " % cancel_add
    print "### Total not found: %s " % total_not_found
    #print "### Total url error: %s " % total_url_error
    DIALOG_PROGRESS.close()
    return next_aired_list
