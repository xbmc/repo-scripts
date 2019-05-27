#!/usr/bin/python
# encoding: utf-8

import sys
import os
import xbmc
import xbmcaddon
import urlparse


from resources.lib.utils import log

reload(sys)
sys.setdefaultencoding("utf-8")

addon         = xbmcaddon.Addon()
addonID       = addon.getAddonInfo('id')  #script.reddit.reader
addon_path    = addon.getAddonInfo('path')      #where the addon resides
profile_path  = addon.getAddonInfo('profile')   #where user settings are stored

reddit_userAgent = "XBMC:"+addonID+":v"+addon.getAddonInfo('version')+" (by /u/gsonide)"
reddit_clientID      ="ZEbDJ5DUrguDMA"
reddit_redirect_uri  ='http://localhost:8090/'   #specified when registering for a clientID

urlMain = "https://www.reddit.com"

hide_nsfw            = addon.getSetting("hide_nsfw") == "true"
domain_filter        = addon.getSetting("domain_filter")
subreddit_filter     = addon.getSetting("subreddit_filter")
comments_link_filter = addon.getSetting("comments_link_filter")

sitemsPerPage        = addon.getSetting("itemsPerPage")
try: itemsPerPage    = ["10", "25", "50", "75", "100"][ int(sitemsPerPage) ]
except ValueError: itemsPerPage = 50

CommentTreshold          = addon.getSetting("CommentTreshold")
try: int_CommentTreshold = int(CommentTreshold)
except ValueError: int_CommentTreshold = -1000    #if CommentTreshold can't be converted to int, show all comments

try:istreamable_quality=int(addon.getSetting("streamable_quality"))  #values 0 or 1
except ValueError:istreamable_quality=0
streamable_quality  =["full", "mobile"][istreamable_quality]       #https://streamable.com/documentation

REQUEST_TIMEOUT=(5,10) #requests.get timeout in seconds (connect timeout, read timeout) tuple.

addonUserDataFolder = xbmc.translatePath(profile_path)
subredditsFile      = xbmc.translatePath(os.path.join(addonUserDataFolder, 'subreddits'))
subredditsPickle    = xbmc.translatePath(os.path.join(addonUserDataFolder, 'subreddits.pickle'))
CACHE_FILE          = xbmc.translatePath(os.path.join(addonUserDataFolder, 'requests_cache'))

ytdl_core_path=xbmc.translatePath(os.path.join(addon_path,'resources','lib','youtube_dl' ))


if not os.path.isdir(addonUserDataFolder):
    os.mkdir(addonUserDataFolder)

def parameters_string_to_dict(parameters):

    return dict( urlparse.parse_qsl(parameters) )

if __name__ == '__main__':

    if len(sys.argv) > 1:
        params=parameters_string_to_dict(sys.argv[1])

    else: params={}

    mode   = params.get('mode', '')
    url    = params.get('url', '')
    type_  = params.get('type', '') #type is a python function, try not to use a variable name same as function
    name   = params.get('name', '')


    log( "----------------v{0} {1}:{2} {3}----------------".format( addon.getAddonInfo('version'), mode,type_,(url if mode else '' ) ))


    from resources.lib.slideshow import autoSlideshow
    from resources.lib.autoplay import autoPlay
    from resources.lib.converthtml import readHTML
    from resources.lib.utils import addtoFilter,open_web_browser
    from resources.lib.actions import manage_subreddits, addSubreddit, editSubreddit, removeSubreddit,\
    loopedPlayback,error_message,viewImage, listAlbum, viewTallImage,update_youtube_dl_core,\
    playVideo, playYTDLVideo, playURLRVideo,searchReddits, delete_setting_file, listRelatedVideo
    from resources.lib.reddit import reddit_get_refresh_token, reddit_get_access_token, reddit_revoke_refresh_token, reddit_save
    from resources.lib.main_listing import index, listSubReddit, listLinksInComment

    if mode=='':mode='index'  #default mode is to list start page (index)

    plugin_modes = {'index'                 : index
                    ,'listSubReddit'        : listSubReddit
                    ,'playVideo'            : playVideo
                    ,'addSubreddit'         : addSubreddit
                    ,'editSubreddit'        : editSubreddit
                    ,'removeSubreddit'      : removeSubreddit
                    ,'addtoFilter'          : addtoFilter
                    ,'search'               : searchReddits
                    ,'autoPlay'             : autoPlay
                    ,'autoSlideshow'        : autoSlideshow
                    ,'listAlbum'            : listAlbum        #slideshowAlbum
                    ,'viewImage'            : viewImage
                    ,'viewTallImage'        : viewTallImage
                    ,'readHTML'             : readHTML
                    ,'listLinksInComment'   : listLinksInComment
                    ,'playYTDLVideo'        : playYTDLVideo
                    ,'playURLRVideo'        : playURLRVideo
                    ,'loopedPlayback'       : loopedPlayback
                    ,'error_message'        : error_message
                    ,'manage_subreddits'    : manage_subreddits
                    ,'update_youtube_dl_core':update_youtube_dl_core
                    ,'get_refresh_token'    : reddit_get_refresh_token
                    ,'get_access_token'     : reddit_get_access_token
                    ,'revoke_refresh_token' : reddit_revoke_refresh_token
                    ,'reddit_save'          : reddit_save
                    ,'delete_setting_file'  : delete_setting_file
                    ,'listRelatedVideo'     : listRelatedVideo
                    ,'openBrowser'          : open_web_browser
                    }
    plugin_modes[mode](url,name,type_)
