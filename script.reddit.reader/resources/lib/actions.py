# -*- coding: utf-8 -*-
import xbmc
import xbmcgui

import sys
import shutil, os
import re, urllib
import pprint

from default import subredditsFile, addon, addon_path, profile_path, ytdl_core_path, subredditsPickle,CACHE_FILE
from utils import xbmc_busy, log, translation, xbmc_notify
from reddit import get_subreddit_entry_info

ytdl_quality=addon.getSetting("ytdl_quality")
try: ytdl_quality=[0, 1, 2, 3][ int(ytdl_quality) ]
except ValueError: ytdl_quality=1
ytdl_DASH=addon.getSetting("ytdl_DASH")=='true'

def manage_subreddits(subreddit, name, type_):
    from main_listing import index
    log('manage_subreddits(%s, %s, %s)' %(subreddit, name, type_) )

    dialog = xbmcgui.Dialog()

    selected_index = dialog.select(subreddit, [translation(32001), translation(32003), translation(32002)])

    if selected_index == 0:       # 0->first item
        addSubreddit('','','')
    elif selected_index == 1:     # 1->second item
        editSubreddit(subreddit,'','')
    elif selected_index == 2:     # 2-> third item
        removeSubreddit(subreddit,'','')
    else:                         #-1 -> escape pressed or [cancel]
        pass

    xbmc_busy(False)

    index("","","")

def addSubreddit(subreddit, name, type_):
    from utils import colored_subreddit
    from reddit import this_is_a_multireddit, format_multihub
    alreadyIn = False
    with open(subredditsFile, 'r') as fh:
        content = fh.readlines()
    if subreddit:
        for line in content:
            if line.lower()==subreddit.lower():
                alreadyIn = True
        if not alreadyIn:
            with open(subredditsFile, 'a') as fh:
                fh.write(subreddit+'\n')

            get_subreddit_entry_info(subreddit)
        xbmc_notify(colored_subreddit(subreddit), translation(32019) )
    else:


        keyboard = xbmc.Keyboard('', translation(32001))
        keyboard.doModal()
        if keyboard.isConfirmed() and keyboard.getText():
            subreddit = keyboard.getText()

            if this_is_a_multireddit(subreddit):
                subreddit = format_multihub(subreddit)
            else:
                get_subreddit_entry_info(subreddit)

            for line in content:
                if line.lower()==subreddit.lower()+"\n":
                    alreadyIn = True

            if not alreadyIn:
                with open(subredditsFile, 'a') as fh:
                    fh.write(subreddit+'\n')

        xbmc.executebuiltin("Container.Refresh")

def removeSubreddit(subreddit, name, type_):
    log( 'removeSubreddit ' + subreddit)

    with open(subredditsFile, 'r') as fh:
        content = fh.readlines()

    contentNew = ""
    for line in content:
        if line!=subreddit+'\n':

            contentNew+=line
    with open(subredditsFile, 'w') as fh:
        fh.write(contentNew)

    xbmc.executebuiltin("Container.Refresh")

def editSubreddit(subreddit, name, type_):
    from reddit import this_is_a_multireddit, format_multihub
    log( 'editSubreddit ' + subreddit)

    with open(subredditsFile, 'r') as fh:
        content = fh.readlines()

    contentNew = ""

    keyboard = xbmc.Keyboard(subreddit, translation(32003))
    keyboard.doModal()
    if keyboard.isConfirmed() and keyboard.getText():
        newsubreddit = keyboard.getText()

        if this_is_a_multireddit(newsubreddit):
            newsubreddit = format_multihub(newsubreddit)
        else:
            get_subreddit_entry_info(newsubreddit)

        for line in content:
            if line.strip()==subreddit.strip() :      #if matches the old subreddit,

                contentNew+=newsubreddit+'\n'
            else:
                contentNew+=line

        with open(subredditsFile, 'w') as fh:
            fh.write(contentNew)

        xbmc.executebuiltin("Container.Refresh")

def searchReddits(url, subreddit, type_):
    from default import urlMain
    from main_listing import listSubReddit

    if subreddit:
        initial_search_string='restrict_sr=on&sort=relevance&t=all&q='
        initial_url=urlMain+'/r/'+subreddit
    else:
        initial_search_string='sort=relevance&t=year&q='
        initial_url=urlMain

    keyboard = xbmc.Keyboard(initial_search_string, translation(32073))
    keyboard.doModal()
    if keyboard.isConfirmed() and keyboard.getText():

        search_string=keyboard.getText()

        if search_string:
            search_string=urllib.unquote_plus(search_string)

        url = initial_url +"/search.json?" +search_string    #+ '+' + nsfw  # + sites_filter skip the sites filter

        listSubReddit(url, 'Search', "")

def setting_gif_repeat_count():
    srepeat_gif_video= addon.getSetting("repeat_gif_video")
    try: repeat_gif_video = int(srepeat_gif_video)
    except ValueError: repeat_gif_video = 0

    return [0, 1, 3, 10, 100][repeat_gif_video]

def viewImage(image_url, name, preview_url):
    from guis import cGUI

    log('  viewImage %s, %s, %s' %( image_url, name, preview_url))

    msg=""
    li=[]
    liz=xbmcgui.ListItem(label=msg, label2="")
    liz.setInfo( type='video', infoLabels={"plot": msg, } )
    liz.setArt({"thumb": preview_url, "banner":image_url })

    li.append(liz)
    ui = cGUI('view_450_slideshow.xml' , addon_path, defaultSkin='Default', defaultRes='1080i', listing=li, id=53)
    ui.include_parent_directory_entry=False

    ui.doModal()
    del ui
    return


def viewTallImage(image_url, width, height):
    log( 'viewTallImage %s: %sx%s' %(image_url, width, height))


    xbmc_busy(False)

    can_quit=True
    if can_quit==True:
        useWindow=xbmcgui.WindowDialog()
        useWindow.setCoordinateResolution(0)

        try:
            w=int(float(width))
            h=int(float(height))
            optimal_h=int(h*1.5)

            loading_img = xbmc.validatePath('/'.join((addon_path, 'resources', 'skins', 'Default', 'media', 'srr_busy.gif' )))

            img_control = xbmcgui.ControlImage(0, 800, 1920, optimal_h, '', aspectRatio=2)  #(values 0 = stretch (default), 1 = scale up (crops), 2 = scale down (black bars)
            img_loading = xbmcgui.ControlImage(1820, 0, 100, 100, loading_img, aspectRatio=2)

            img_control.setImage(image_url, False)

            useWindow.addControls( [ img_loading, img_control])


            scroll_time=(int(h)/int(w))*20000

            img_control.setAnimations( [
                                        ('conditional', "condition=true effect=fade  delay=0    start=0   end=100   time=4000 "  ) ,
                                        ('conditional', "condition=true effect=slide delay=2000 start=0,-%d end=0,0 tween=sine easing=in time=%d pulse=true" %( (h*1.4), scroll_time) ),
                                        ]  )

            useWindow.doModal()
            useWindow.removeControls( [img_control,img_loading] )
            del useWindow
        except Exception as e:
            log("  EXCEPTION viewTallImage:="+ str( sys.exc_info()[0]) + "  " + str(e) )

    else:

        useWindow = xbmcgui.Window( xbmcgui.getCurrentWindowId() )
        xbmc_busy(False)
        w=int(float(width))
        h=int(float(height))
        optimal_h=int(h*1.5)

        loading_img = xbmc.validatePath('/'.join((addon_path, 'resources', 'skins', 'Default', 'media', 'srr_busy.gif' )))

        img_control = xbmcgui.ControlImage(0, 1080, 1920, optimal_h, '', aspectRatio=2)  #(values 0 = stretch (default), 1 = scale up (crops), 2 = scale down (black bars)
        img_loading = xbmcgui.ControlImage(1820, 0, 100, 100, loading_img, aspectRatio=2)

        img_control.setImage(image_url, False)
        useWindow.addControls( [ img_loading, img_control])
        scroll_time=int(h)*(int(h)/int(w))*10
        img_control.setAnimations( [
                                    ('conditional', "condition=true effect=fade  delay=0    start=0   end=100   time=4000 "  ) ,
                                    ('conditional', "condition=true effect=slide delay=2000 start=0,0 end=0,-%d time=%d pulse=true" %( (h*1.6) ,scroll_time) ),
                                    ('conditional', "condition=true effect=fade  delay=%s   start=100 end=0     time=2000 " %(scroll_time*1.8) ) ,
                                    ]  )
        xbmc.sleep(scroll_time*2)
        useWindow.removeControls( [img_control,img_loading] )

def display_album_from(dictlist, album_name):
    from utils import dictlist_to_listItems

    directory_items=dictlist_to_listItems(dictlist)

    from guis import cGUI


    ui = cGUI('view_450_slideshow.xml' , addon_path, defaultSkin='Default', defaultRes='1080i', listing=directory_items, id=53)
    ui.include_parent_directory_entry=False


    ui.doModal()
    del ui

def listAlbum(album_url, name, type_):
    from slideshow import slideshowAlbum
    from domains import sitesManager
    log("    listAlbum:"+album_url)

    hoster = sitesManager( album_url )


    if hoster:
        dictlist=hoster.ret_album_list(album_url)

        if type_=='return_dictlist':  #used in autoSlideshow
            return dictlist

        if not dictlist:
            xbmc_notify(translation(32200), translation(32055)) #slideshow, no playable items
            return

        if addon.getSetting('use_slideshow_for_album') == 'true':
            slideshowAlbum( dictlist, name )
        else:
            display_album_from( dictlist, name )

def playURLRVideo(url, name, type_):
    dialog_progress_title='URL Resolver'
    dialog_progress_YTDL = xbmcgui.DialogProgressBG()
    dialog_progress_YTDL.create(dialog_progress_title )
    dialog_progress_YTDL.update(10,dialog_progress_title,translation(32014)  )

    import urlresolver
    from urlparse import urlparse
    parsed_uri = urlparse( url )
    domain = '{uri.netloc}'.format(uri=parsed_uri)

    dialog_progress_YTDL.update(20,dialog_progress_title,translation(32012)  )

    try:
        media_url = urlresolver.resolve(url)
        dialog_progress_YTDL.update(80,dialog_progress_title,translation(32013)  )
        if media_url:
            log( '  URLResolver stream url=' + repr(media_url ))

            pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
            pl.clear()
            pl.add(media_url, xbmcgui.ListItem(name))
            xbmc.Player().play(pl, windowed=False)  #scripts play video like this.
        else:
            log( "  Can't URL Resolve:" + repr(url))
            xbmc_notify('URLresolver', translation(32192),icon="type_urlr.png" )  #Failed to get playable url
    except Exception as e:
        xbmc_notify('URLresolver:'+domain, str(e),icon="type_urlr.png" )
    dialog_progress_YTDL.close()

def loopedPlayback(url, name, type_):

    pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    pl.clear()
    pl.add(url, xbmcgui.ListItem(name))
    for _ in range( 0, setting_gif_repeat_count() ):
        pl.add(url, xbmcgui.ListItem(name))

    xbmc.Player().play(pl, windowed=False)

def error_message(message, name, type_):
    if name:
        sub_msg=name  #name is usually the title of the post
    else:
        sub_msg=translation(32021) #Parsing error
    xbmc_notify(message, sub_msg)

def playVideo(url, name, type_):
    xbmc_busy(False)

    pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    pl.clear()

    if url : #sometimes url is a list of url or just a single string
        if isinstance(url, basestring):
            pl.add(url, xbmcgui.ListItem(name))
            xbmc.Player().play(pl, windowed=False)  #scripts play video like this.

        else:
            for u in url:

                pl.add(u, xbmcgui.ListItem(name))
            xbmc.Player().play(pl, windowed=False)
    else:
        log("playVideo(url) url is blank")

def playYTDLVideo(url, name, type_):
    dialog_progress_title='Youtube_dl'  #.format(ytdl_get_version_info())
    dialog_progress_YTDL = xbmcgui.DialogProgressBG()
    dialog_progress_YTDL.create(dialog_progress_title )
    dialog_progress_YTDL.update(10,dialog_progress_title,translation(32014)  )

    from YoutubeDLWrapper import YoutubeDLWrapper, _selectVideoQuality
    from urlparse import urlparse, parse_qs

    o = urlparse(url)
    query = parse_qs(o.query)
    video_index=0

    if 'index' in query:
        try:video_index=int(query['index'][0])
        except (TypeError, ValueError): video_index=0

        dialog_progress_YTDL.update(20,dialog_progress_title,translation(32017)  )
    else:

        dialog_progress_YTDL.update(20,dialog_progress_title,translation(32012)  )

    pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    pl.clear()

    ytdl=YoutubeDLWrapper()
    try:
        ydl_info=ytdl.extract_info(url, download=False)

        video_infos=_selectVideoQuality(ydl_info, quality=ytdl_quality, disable_dash=(not ytdl_DASH) )
        log( "video_infos:\n" + pprint.pformat(video_infos, indent=1, depth=3) )
        dialog_progress_YTDL.update(80,dialog_progress_title,translation(32013)  )

        if video_index > 0:
            add_ytdl_video_info_to_playlist(video_infos[video_index-1], pl, name)
        else:
            for video_info in video_infos:
                add_ytdl_video_info_to_playlist(video_info, pl, name)

        if len(pl)>1:
            xbmc_notify("Multiple video", "{} videos in playlist".format(len(pl)))

        xbmc.Player().play(pl, windowed=False)


    except Exception as e:
        ytdl_ver=dialog_progress_title+' v'+ytdl_get_version_info('local')
        err_msg=str(e)+';'  #ERROR: No video formats found; please report this issue on https://yt-dl.org/bug . Make sure you are using the latest vers....
        short_err=err_msg.split(';')[0]
        log( "playYTDLVideo Exception:" + str( sys.exc_info()[0]) + "  " + str(e) )
        xbmc_notify(ytdl_ver, short_err,icon='type_ytdl.png')

        log('   trying urlresolver...')
        playURLRVideo(url, name, type_)
    finally:
        dialog_progress_YTDL.update(100,dialog_progress_title ) #not sure if necessary to set to 100 before closing dialogprogressbg
        dialog_progress_YTDL.close()

def add_ytdl_video_info_to_playlist(video_info, pl, title=None):
    url=video_info.get('xbmc_url')  #there is also  video_info.get('url')  url without the |useragent...

    url=urllib.quote_plus(url.encode('utf-8'), safe="&$+,/:;=?@#<>[]{}|\^%")

    title=video_info.get('title') or title
    ytdl_format=video_info.get('ytdl_format')
    if ytdl_format:
        description=ytdl_format.get('description')

        try:
            start_time=ytdl_format.get('start_time',0)   #int(float(ytdl_format.get('start_time')))
        except (ValueError, TypeError):
            start_time=0

        video_thumbnail=video_info.get('thumbnail')
    li=xbmcgui.ListItem(label=title,
                        label2='',
                        path=url)
    li.setArt({"thumb": video_thumbnail, "icon":video_thumbnail })
    li.setInfo( type="Video", infoLabels={ "Title": title, "plot": description } )
    li.setProperty('StartOffset', str(start_time))
    pl.add(url, li)

YTDL_VERSION_URL = 'https://yt-dl.org/latest/version'
YTDL_LATEST_URL_TEMPLATE = 'https://yt-dl.org/latest/youtube-dl-{}.tar.gz'

def ytdl_get_version_info(which_one='latest'):
    import urllib2
    if which_one=='latest':
        try:
            newVersion = urllib2.urlopen(YTDL_VERSION_URL).read().strip()
            return newVersion
        except:
            return "0.0"
    else:
        try:

            from youtube_dl.version import __version__
            return __version__
        except Exception as e:
            log('error getting ytdl local version:'+str(e))
            return "0.0"

def update_youtube_dl_core(url,name,action_type):

    import urllib
    import tarfile

    if action_type=='download':
        newVersion=note_ytdl_versions()
        LATEST_URL=YTDL_LATEST_URL_TEMPLATE.format(newVersion)

        profile = xbmc.translatePath(profile_path)  #xbmc.translatePath(addon.getAddonInfo('profile')).decode('utf-8')
        archivePath = os.path.join(profile,'youtube_dl.tar.gz')
        extractedPath = os.path.join(profile,'youtube-dl')
        extracted_core_path=os.path.join(extractedPath,'youtube_dl')


        try:
            if os.path.exists(extractedPath):
                shutil.rmtree(extractedPath, ignore_errors=True)
                update_dl_status('temp files removed')

            update_dl_status('Downloading {0} ...'.format(newVersion))
            log('  From: {0}'.format(LATEST_URL))
            log('    to: {0}'.format(archivePath))
            urllib.urlretrieve(LATEST_URL,filename=archivePath)

            if os.path.exists(archivePath):
                update_dl_status('Extracting ...')

                with tarfile.open(archivePath,mode='r:gz') as tf:
                    members = [m for m in tf.getmembers() if m.name.startswith('youtube-dl/youtube_dl')] #get just the files from the youtube_dl source directory
                    tf.extractall(path=profile,members=members)
            else:
                update_dl_status('Download failed')
        except Exception as e:
            update_dl_status('Error:' + str(e))

        update_dl_status('Updating...')

        if os.path.exists(extracted_core_path):
            log( '  extracted dir exists:'+extracted_core_path)

            if os.path.exists(ytdl_core_path):
                log( '  destination dir exists:'+ytdl_core_path)
                shutil.rmtree(ytdl_core_path, ignore_errors=True)
                update_dl_status('    Old ytdl core removed')
                xbmc.sleep(1000)
            try:
                shutil.move(extracted_core_path, ytdl_core_path)
                update_dl_status('    New core copied')
                xbmc.sleep(1000)
                update_dl_status('Update complete')
                xbmc.Monitor().waitForAbort(2.0)

                setSetting('ytdl_btn_check_version', "")
                setSetting('ytdl_btn_download', "")
            except Exception as e:
                update_dl_status('Failed...')
                log( 'move failed:'+str(e))

    elif action_type=='checkversion':
        note_ytdl_versions()

def note_ytdl_versions():

    setSetting('ytdl_btn_check_version', "checking...")
    ourVersion=ytdl_get_version_info('local')
    setSetting('ytdl_btn_check_version', "{0}".format(ourVersion))

    setSetting('ytdl_btn_download', "checking...")
    newVersion=ytdl_get_version_info('latest')
    setSetting('ytdl_btn_download',      "latest {0}".format(newVersion))

    return newVersion


def update_dl_status(message):
    log(message)
    setSetting('ytdl_btn_download', message)

def setSetting(setting_id, value):
    addon.setSetting(setting_id, value)

def delete_setting_file(url,name,action_type):

    if action_type=='requests_cache':
        file_to_delete=CACHE_FILE+'.sqlite'
    elif action_type=='icons_cache':
        file_to_delete=subredditsPickle
    elif action_type=='subreddits_setting':
        file_to_delete=subredditsFile

    try:
        os.remove(file_to_delete)
        xbmc_notify("Deleting", '..'+file_to_delete[-30:])
    except OSError as e:
        xbmc_notify("Error:", str(e))

def listRelatedVideo(url,name,type_):

    from domains import ClassYoutube
    from utils import dictlist_to_listItems
    from ContextMenus import build_youtube_context_menu_entries

    match=re.compile( ClassYoutube.regex, re.I).findall( url )
    if match:

        yt=ClassYoutube(url)
        try:
            yt.get_thumb_url()
            poster=yt.poster_url


            xbmc_busy(True)
            if type_=='links_in_description':
                links_dictList=yt.get_links_in_description(return_channelID_only=False)
            else: # 'channel' 'related default
                links_dictList=yt.ret_album_list(type_)  #returns a list of dict same as one used for albums
            xbmc_busy(False)

            if links_dictList:

                directory_items=dictlist_to_listItems(links_dictList)
                for li in directory_items:
                    link_url=li.getProperty('link_url')
                    video_id=li.getProperty('video_id')
                    label=li.getProperty('label')
                    li.setProperty('context_menu', str(build_youtube_context_menu_entries(type_,link_url,video_id, title=label)) )

                if type_=='links_in_description':
                    from guis import text_to_links_gui
                    ui = text_to_links_gui('srr_links_in_text.xml' , addon_path, defaultSkin='Default', defaultRes='1080i', listing=directory_items, title=name, poster=poster)

                else: # 'channel' 'related default
                    from guis import cGUI
                    ui = cGUI('srr_related_videos.xml' , addon_path, defaultSkin='Default', defaultRes='1080i', listing=directory_items, id=55, title=name, poster=poster)
                    ui.include_parent_directory_entry=False
                ui.doModal()
                del ui
            else:
                xbmc_notify('Nothing to list', url)

        except ValueError as e:
            xbmc_notify('Error', str(e))
        finally:
            xbmc_busy(False)
    else:
        xbmc_notify('cannot identify youtube url', url)

if __name__ == '__main__':
    pass
