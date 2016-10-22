# -*- coding: UTF-8 -*-
# Copyright, 2010, Guilherme Jardim.
# This program is distributed under the terms of the GNU General Public License, version 3.
# http://www.gnu.org/licenses/gpl.txt
# Rev. 2.3.2

import os
import sys
import xbmc
import re
import urllib
import urllib2
import xbmcvfs
import xbmcaddon
import xbmcgui,xbmcplugin

__addon__      = xbmcaddon.Addon()
__author__     = __addon__.getAddonInfo('author')
__scriptid__   = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__version__    = __addon__.getAddonInfo('version')
__language__   = __addon__.getLocalizedString

__cwd__        = xbmc.translatePath( __addon__.getAddonInfo('path') ).decode("utf-8")
__profile__    = xbmc.translatePath( __addon__.getAddonInfo('profile') ).decode("utf-8")
__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) ).decode("utf-8")
__temp__       = xbmc.translatePath( os.path.join( __profile__, 'temp', '') ).decode("utf-8")

sys.path.append (__resource__)
__search__   = __addon__.getSetting( 'SEARCH' )
__username__ = __addon__.getSetting( 'USERNAME' )
__password__ = __addon__.getSetting( 'PASSWORD' )

from LTVutilities import log, cleanDirectory, isStacked, getMovieIMDB, getShowIMDB, getShowId, getTVShowOrginalTitle, getMovieOriginalTitle, safeFilename
from LegendasTV import *

LTV = LegendasTV()
LTV.Log = log

def Search(item):  # standard input

    try:
        languages = []
        subtitles = LTV.Search(title=item['title'], 
                               tvshow=item['tvshow'], 
                               year=item['year'], 
                               season=item['season'], 
                               episode=item['episode'], 
                               lang=item['languages'],
                               imdb=item['imdb'])
    except:
        import traceback
        log("\n%s" % traceback.format_exc(), "ERROR")
        return 1 

    if subtitles:
        for it in subtitles:
            if it['type'] == "destaque":
                label = "[COLOR FFDE7B18]%s[/COLOR]" % it["filename"]
            else:
                label = it["filename"]

            listitem = xbmcgui.ListItem(label=it["language_name"],
                                        label2=label,
                                        iconImage=it["rating"],
                                        thumbnailImage=it["language_flag"]
                                        )
            if it["sync"]: listitem.setProperty( "sync", "true" )
            else: listitem.setProperty( "sync", "false" )
            if it.get("hearing_imp", False): listitem.setProperty( "hearing_imp", "true" )
            else: listitem.setProperty( "hearing_imp", "false" )
            pack = "true" if it['type'] == "pack" else "false"
            url = "plugin://%s/?action=download&download_url=%s&filename=%s&pack=%s&lang=%s" % (__scriptid__, 
                                                                                                it["url"],
                                                                                                os.path.basename(item["file_original_path"]), 
                                                                                                pack,
                                                                                                it["language_name"] )

            xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=listitem,isFolder=False)
    
    if item['original_title'] != "true":
        listitem = xbmcgui.ListItem(label="", label2=__language__( 32011 ).encode("utf-8"), iconImage="", thumbnailImage="")
        searchstring = "&searchstring=%s" % item['searchstring'] if item.has_key("searchstring") else ""
        url = "plugin://%s/?action=search&original_title=true&languages=%s%s" % ( __scriptid__, 
                                                                                  urllib.quote(",".join(item["languages"])), 
                                                                                  urllib.quote(searchstring)
                                                                                )
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=url,listitem=listitem,isFolder=False)

# def xbmc_walk(path, out = [] ):
#     dirs, files =  xbmcvfs.listdir(path)
#     for f in files:
#         f =  u"%s/%s" % (path,f.decode("utf-8"))
#         out.append(f)
#     for d in dirs:
#         d = "%s/%s/" % (path, d)
#         if xbmcvfs.exists(d): out.extend(xbmc_walk(d, out) )
#     return out

def xbmc_walk(DIR):
    LIST = []
    dirs, files = xbmcvfs.listdir(DIR)
    for file in files:
        LIST.append(os.path.join( DIR, file ))
    for dir in dirs:
        LIST.extend(list(xbmc_walk(os.path.join( DIR, dir ))))
    return LIST




def Download(url, filename, pack, language): #standard input
    #Create some variables
    subtitles = []
    extractPath = os.path.join(__temp__, "Extracted")
    cleanDirectory(extractPath)

    FileContent, FileExt = LTV.Download(url)

    fname = "%s.%s" % ( os.path.join(__temp__,"subtitle"), FileExt )

    with open(fname,'wb') as f: f.write(FileContent)

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
                log("Opening file: "+dirfile, "DEBUG")

                with open(dirfile,'rb') as f: 
                    FileContent = f.read()
                xbmcvfs.delete(dirfile)

                dirfile_with_path_name = normalizeString(os.path.relpath(dirfile, extractPath))
                dirname, basename = os.path.split(dirfile_with_path_name)
                dirname = re.sub(r"[/\\]{1,10}","-", dirname)
                dirfile_with_path_name = "(%s) %s" % (dirname, basename) if len(dirname) else basename
                new_dirfile = os.path.join(extractPath, safeFilename(dirfile_with_path_name))
                with open(new_dirfile, "w") as f: 
                    log("Writing file: "+new_dirfile, "DEBUG")
                    f.write(FileContent)
                
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
        if pack:
            subtitles.append(["pack",__language__( 32010 )])
        dialog = xbmcgui.Dialog()
        sel = dialog.select("%s\n%s" % (__language__( 32001 ).encode("utf-8"), filename ) ,
                             [os.path.basename(y) for x, y in subtitles])
        if sel >= 0:
            subSelected = subtitles[sel][1]

            # Handling package import
            if subtitles[sel][0] == "pack":
                dir = os.path.dirname(urllib.unquote(xbmc.Player().getPlayingFile().decode('utf-8')))
                for f in xbmc_walk(dir):
                    if os.path.splitext(f)[1] in [".mkv", ".avi", ".vob", ".mov", ".mp4"]:
                        for x, s in subtitles:
                            se, fe = 0, 1
                            if re.search("s\d{2}e\d{2}", s.lower()): se = re.findall("s\d{2}e\d{2}", s.lower())[0]
                            if re.search("s\d{2}e\d{2}", f.lower()): fe = re.findall("s\d{2}e\d{2}", f.lower())[0]
                            if se == fe:
                                if os.path.basename(f) == os.path.basename(filename):
                                    outputSub.append(s)
                                name = os.path.splitext(f)[0]
                                ext = os.path.splitext(s)[1]
                                lang = "pt" if re.search("Portuguese", language) else "en"
                                out = "%s.%s%s" % (name, lang, ext)
                                xbmcvfs.copy(s, out)


            outputSub.append(subSelected)
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
    item['year']                = xbmc.getInfoLabel("VideoPlayer.Year")                              # Year
    item['season']              = str(xbmc.getInfoLabel("VideoPlayer.Season"))                       # Season
    item['episode']             = str(xbmc.getInfoLabel("VideoPlayer.Episode"))                      # Episode
    item['tvshow']              = normalizeString(xbmc.getInfoLabel("VideoPlayer.TVshowtitle"))      # Show
    item['title']               = normalizeString(xbmc.getInfoLabel("VideoPlayer.OriginalTitle"))    # try to get original title
    item['file_original_path']  = urllib.unquote(xbmc.Player().getPlayingFile().decode('utf-8'))     # Full path of a playing file
    item['languages']           = [] #['scc','eng']
    item["languages"].extend(urllib.unquote(params['languages']).decode('utf-8').split(","))
    item["original_title"]      = "true" if params.has_key("original_title") else "false"

    if not item['title']:
        log( "VideoPlayer.OriginalTitle not found")        
        item['title']  = normalizeString(xbmc.getInfoLabel("VideoPlayer.Title"))

    if item['tvshow']:
        item["imdb"] = getShowIMDB()
    else:
        item["imdb"] = getMovieIMDB()


    if item["original_title"] == "true":
        if item['tvshow']: 
            item['tvshow'] = getTVShowOrginalTitle(item["tvshow"], getShowId())
        else:
            item['title'] = getMovieOriginalTitle(item["title"], item["imdb"])

    if 'searchstring' in params:
        item["searchstring"] = urllib.unquote(params['searchstring'])
        if item['tvshow']: 
            item['tvshow']   = item["searchstring"]
        elif item['title']: 
            item['title']    = item["searchstring"]

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
    pack = True if params['pack'] == "true" else False
    Cookie = LTV.login(__username__, __password__)
    try:
        subs = Download(params["download_url"],params["filename"], pack, params['lang'])
    except: 
        subs = Download(params["download_url"],'filename', pack, params['lang'])
    for sub in subs:
        listitem = xbmcgui.ListItem(label2=os.path.basename(sub))
        xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=sub,listitem=listitem,isFolder=False)
xbmcplugin.endOfDirectory(int(sys.argv[1]))
    
