# -*- coding: UTF-8 -*-
# Copyright, 2010, Guilherme Jardim.
# This program is distributed under the terms of the GNU General Public License, version 3.
# http://www.gnu.org/licenses/gpl.txt
# Rev. 2.1.2

import os
import sys
import xbmc
import re
import urllib
import urllib2
import xbmcvfs
import xbmcaddon
import xbmcgui,xbmcplugin

__addon__ = xbmcaddon.Addon()
__author__     = __addon__.getAddonInfo('author')
__scriptid__   = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__    = __addon__.getAddonInfo('version')
__language__   = __addon__.getLocalizedString

__cwd__        = xbmc.translatePath( __addon__.getAddonInfo('path') ).decode("utf-8")
__profile__    = xbmc.translatePath( __addon__.getAddonInfo('profile') ).decode("utf-8")
__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) ).decode("utf-8")
__temp__       = xbmc.translatePath( os.path.join( __profile__, 'temp') ).decode("utf-8")

sys.path.append (__resource__)
__search__ = __addon__.getSetting( 'SEARCH' )

from LTVutilities import log, xbmcOriginalTitle, cleanDirectory, isStacked
from LegendasTV import *

def Search(item):  # standard input

    try:
        LTV = LegendasTV()
        LTV.Log = log
        subtitles = ""
        languages = []
        subtitles = LTV.Search(title=item['title'], 
                               tvshow=item['tvshow'], 
                               year=item['year'], 
                               season=item['season'], 
                               episode=item['episode'], 
                               lang=item['languages'])
    except:
        import traceback
        log("\n%s" % traceback.format_exc())
        return 1 

    if subtitles:
        for it in subtitles:
            listitem = xbmcgui.ListItem(label=it["language_name"],
                                        label2=it["filename"],
                                        iconImage=it["rating"],
                                        thumbnailImage=it["language_flag"]
                                        )
            if it["sync"]: listitem.setProperty( "sync", "true" )
            else: listitem.setProperty( "sync", "false" )
            if it.get("hearing_imp", False): listitem.setProperty( "hearing_imp", "true" )
            else: listitem.setProperty( "hearing_imp", "false" )
            url = "plugin://%s/?action=download&download_url=%s&filename=%s" % (__scriptid__, it["url"],os.path.basename(item["file_original_path"]))
            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=listitem,isFolder=False)
    
def Download(url, filename, stack=False): #standard input
    #Create some variables
    subtitles = []
    extractPath = os.path.join(__temp__, "Extracted")
    cleanDirectory(__temp__)
    if not xbmcvfs.exists(extractPath): os.makedirs(extractPath)
    
    # Download the subtitle using its ID.
    Response = urllib2.urlopen(url).read()

    downloadID = re.findall(regex_3, Response)[0] if re.search(regex_3, Response) else 0

    if not downloadID: return ""
    Response = urllib2.urlopen(urllib2.Request("http://minister.legendas.tv%s" % downloadID))
    ltv_sub = Response.read()
    
    # Set the path of file concatenating the temp dir, the subtitle ID and a zip or rar extension.
    # Write the subtitle in binary mode.
    fname = os.path.join(__temp__,"subtitle")
#     fname += '.rar' if re.search("\x52\x61\x72\x21\x1a\x07\x00", ltv_sub) else '.zip'
    fname += '.rar' if Response.url.__contains__('.rar') else '.zip'
    with open(fname,'wb') as f: f.write(ltv_sub)

    # brunoga fixed solution for non unicode caracters
    # Ps. Windows allready parses Unicode filenames.
    fs_encoding = sys.getfilesystemencoding() if sys.getfilesystemencoding() else "utf-8"
    extractPath = extractPath.encode(fs_encoding)

    # Use XBMC.Extract to extract the downloaded file, extract it to the temp dir, 
    # then removes all files from the temp dir that aren't subtitles.
    def extract_and_copy(extraction=0):
        for root, dirs, files in os.walk(extractPath, topdown=False):
            for file in files:
                dirfile = os.path.join(root, file)
                
                # Sanitize filenames - converting them to ASCII - and remove them from folders
                f = xbmcvfs.File(dirfile)
                temp = f.read()
                f.close()
                xbmcvfs.delete(dirfile)
                dirfile_with_path_name = normalizeString(os.path.relpath(dirfile, extractPath))
                dirname, basename = os.path.split(dirfile_with_path_name)
                dirname = re.sub(r"[/\\]{1,10}","-", dirname)
                dirfile_with_path_name = "(%s)%s" % (dirname, basename) if len(dirname) else basename
                new_dirfile = os.path.join(extractPath, dirfile_with_path_name)
                with open(new_dirfile, "w") as f: f.write(temp)
                
                # Get the file extension
                ext = os.path.splitext(new_dirfile)[1][1:].lower()
                if ext in sub_ext and xbmcvfs.exists(new_dirfile):
                    if not new_dirfile in subtitles:
                        #Append the matching file
                        subtitles.append(new_dirfile)
                elif ext in "rar zip" and not extraction:
                    # Extract compressed files, extracted priorly
                    xbmc.executebuiltin("XBMC.Extract(%s, %s)" % (new_dirfile, extractPath))
                    xbmc.sleep(1000)
                    extract_and_copy(1)
                elif ext not in "idx": xbmcvfs.delete(new_dirfile)
            for dir in dirs:
                dirfolder = os.path.join(root, dir)
                xbmcvfs.rmdir(dirfolder)

    xbmc.executebuiltin("XBMC.Extract(%s, %s)" % (fname, extractPath))
    xbmc.sleep(1000)
    extract_and_copy()
    
    temp = []
    for sub in subtitles:
        ltv = LegendasTV()
        video_file = ltv.CleanLTVTitle(filename)
        sub_striped =  ltv.CleanLTVTitle(os.path.basename(sub))
        Ratio = ltv.CalculateRatio(sub_striped, video_file)
        temp.append([Ratio, sub])
    subtitles = sorted(temp, reverse=True)
    outputSub = []
    if len(subtitles) > 1:
        dialog = xbmcgui.Dialog()
        sel = dialog.select("%s\n%s" % (__language__( 32001 ).encode("utf-8"), filename ) ,
                             [os.path.basename(y) for x, y in subtitles])
        if sel >= 0:
            subSelected = subtitles[sel][1]
            outputSub.append(subSelected)
            for x, sub in subtitles:
                if isStacked(subSelected, sub):
                    outputSub.append(sub)
    elif len(subtitles) == 1: outputSub.append(subtitles[0][1])
    return outputSub

def get_params(string=""):
    param=[]
    if string == "": paramstring=sys.argv[2]
    else:
        paramstring=string 
    if len(paramstring)>=2:
        params=paramstring
        cleanedparams=params.replace('?','')
        if (params[len(params)-1]=='/'): params=params[0:len(params)-2]
        pairsofparams=cleanedparams.split('&')
        param={}
        for i in range(len(pairsofparams)):
            splitparams={}
            splitparams=pairsofparams[i].split('=')
            if (len(splitparams))==2: param[splitparams[0]]=splitparams[1]
    return param

params = get_params()
log( "Version: %s" % __version__)
log( "Action '%s' called" % params['action'])

if params['action'] == 'search' or params['action'] == 'manualsearch':
    item = {}
    item['temp']                = False
    item['rar']                 = False
    item['year']                = xbmc.getInfoLabel("VideoPlayer.Year")                                                 # Year
    item['season']              = str(xbmc.getInfoLabel("VideoPlayer.Season"))                                    # Season
    item['episode']             = str(xbmc.getInfoLabel("VideoPlayer.Episode"))                                 # Episode
    item['tvshow']              = normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))    # Show
    item['title']               = normalizeString(xbmc.getInfoLabel("VideoPlayer.OriginalTitle"))# try to get original title
    item['file_original_path']  = urllib.unquote(xbmc.Player().getPlayingFile().decode('utf-8'))# Full path of a playing file
    item['languages']           = [] #['scc','eng']
    item["languages"].extend(urllib.unquote(params['languages']).decode('utf-8').split(","))
    
    if not item['title']:
        # no original title, get just Title
        log( "VideoPlayer.OriginalTitle not found")        
        item['title']  = normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))

    if 'searchstring' in params:
        if item['title']: item['title'] = urllib.unquote(params['searchstring'])
        elif item['tvshow']: item['tvshow'] = urllib.unquote(params['searchstring'])

    langtemp = []
    for lang in item["languages"]:
        if __search__ == '0':
            if lang == u"Portuguese (Brazil)": langtemp.append((0, lang))
            elif lang == u"Portuguese": langtemp.append((1, lang))
            elif lang == u"English": langtemp.append((2, lang))
            else: langtemp.append((3, lang))
        elif __search__ == '1':
            if lang == u"Portuguese (Brazil)": langtemp.append((1, lang))
            elif lang == u"Portuguese": langtemp.append((0, lang))
            elif lang == u"English": langtemp.append((2, lang))
            else: langtemp.append((3, lang))
        elif __search__ == '2':            
            if lang == u"Portuguese (Brazil)": langtemp.append((1, lang))
            elif lang == u"Portuguese": langtemp.append((2, lang))
            elif lang == u"English": langtemp.append((0, lang))
            else: langtemp.append((3, lang))
        elif __search__ == '3':        
            if lang == u"Portuguese (Brazil)": langtemp.append((1, lang))
            elif lang == u"Portuguese": langtemp.append((2, lang))
            elif lang == u"English": langtemp.append((3, lang))
            else: langtemp.append((0, lang))
    langtemp = sorted(langtemp)
    item["languages"] = []
    for a, b in langtemp: item["languages"].append(b)

    if item['episode'].lower().find("s") > -1:                                                # Check if season is "Special"
        item['season'] = "0"                                    
        item['episode'] = item['episode'][-1:]
    
    if ( item['file_original_path'].find("http") > -1 ):
        item['temp'] = True

    elif ( item['file_original_path'].find("rar://") > -1 ):
        item['rar']    = True
        item['file_original_path'] = os.path.dirname(item['file_original_path'][6:])

    elif ( item['file_original_path'].find("stack://") > -1 ):
        stackPath = item['file_original_path'].split(" , ")
        item['file_original_path'] = stackPath[0][8:]
    
    Search(item)    

elif params['action'] == 'download':
    try: subs = Download(params["download_url"],params["filename"])
    except: subs = Download(params["download_url"],'filename')
    for sub in subs:
        listitem = xbmcgui.ListItem(label2=os.path.basename(sub))
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=sub,listitem=listitem,isFolder=False)

xbmcplugin.endOfDirectory(int(sys.argv[1]))
    
