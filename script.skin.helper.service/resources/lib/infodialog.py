#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
    script.skin.helper.service
    Helper service and scripts for Kodi skins
    infodialog.py
    Wrapper around the videoinfodialog which can be used for widgets for example
    only used for Kodi Jarvis because as of Kodi Krypton this is handled by Kodi natively
'''

import xbmc
import xbmcgui
from metadatautils import MetadataUtils, extend_dict, KodiDb
from utils import get_current_content_type

CANCEL_DIALOG = (9, 10, 92, 216, 247, 257, 275, 61467, 61448, )
ACTION_SHOW_INFO = (11, )


class DialogVideoInfo(xbmcgui.WindowXMLDialog):
    '''Wrapper around the videoinfodialog'''
    result = None

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self)
        self.listitem = kwargs.get("listitem")

    def onInit(self):
        '''triggered when the dialog is drawn'''
        if self.listitem:
            self.clearList()
            kodidb = KodiDb()
            if isinstance(self.listitem, dict):
                self.listitem = kodidb.prepare_listitem(self.listitem)
                self.listitem = kodidb.create_listitem(self.listitem, False)
            del kodidb
            self.addItem(self.listitem)

        # disable some controls if existing
        disable_controls = [9, 7, 101, 6]
        for item in disable_controls:
            try:
                self.getControl(item).setVisible(False)
            except Exception:
                pass

        # enable some controls if existing
        disable_controls = [351, 352]
        for item in disable_controls:
            try:
                self.getControl(item).setVisible(True)
                self.getControl(item).setEnabled(True)
            except Exception:
                pass

    def onClick(self, controlid):
        '''triggers if one of the controls is clicked'''
        if controlid == 8:
            # play button
            self.result = True
            self.close()
            if "videodb:" in self.listitem.getfilename():
                xbmc.executebuiltin('ReplaceWindow(Videos,"%s")' % self.listitem.getfilename())
            else:
                xbmc.executebuiltin('PlayMedia("%s")' % self.listitem.getfilename())
        if controlid == 103:
            # trailer button
            pass

    def onAction(self, action):
        '''triggers on certain actions like user navigating'''
        if action.getId() in CANCEL_DIALOG:
            self.close()
        if action.getId() in ACTION_SHOW_INFO:
            self.close()


def get_cur_listitem(cont_prefix):
    '''gets the current selected listitem details'''
    if xbmc.getCondVisibility("Window.IsActive(busydialog)"):
        xbmc.executebuiltin("Dialog.Close(busydialog)")
        xbmc.sleep(1000)
    dbid = xbmc.getInfoLabel("%sListItem.DBID" % cont_prefix).decode('utf-8')
    if not dbid or dbid == "-1":
        dbid = xbmc.getInfoLabel("%sListItem.Property(DBID)" % cont_prefix).decode('utf-8')
        if dbid == "-1":
            dbid = ""
    dbtype = xbmc.getInfoLabel("%sListItem.DBTYPE" % cont_prefix).decode('utf-8')
    if not dbtype:
        dbtype = xbmc.getInfoLabel("%sListItem.Property(DBTYPE)" % cont_prefix).decode('utf-8')
    if not dbtype:
        dbtype = get_current_content_type(cont_prefix)
    return (dbid, dbtype)


def get_cont_prefix():
    '''gets the container prefix if we're looking at a widget container'''
    widget_container = xbmc.getInfoLabel("Window(Home).Property(SkinHelper.WidgetContainer)")
    if widget_container:
        cont_prefix = "Container(%s)." % widget_container
    else:
        cont_prefix = ""
    return cont_prefix


def show_infodialog(dbid="", media_type=""):
    '''shows the special info dialog for this media'''
    cont_prefix = get_cont_prefix()
    metadatautils = MetadataUtils()
    item_details = {}

    # if dbid is provided we prefer that info else we try to locate the dbid and dbtype
    if not (dbid and media_type):
        dbid, media_type = get_cur_listitem(cont_prefix)

    if media_type.endswith("s"):
        media_type = media_type[:-1]

    # get basic details from kodi db if we have a valid dbid and dbtype
    if dbid and media_type:
        if hasattr(metadatautils.kodidb.__class__, media_type):
            item_details = getattr(metadatautils.kodidb, media_type)(dbid)

    # only proceed if we have a media_type
    if media_type:
        title = xbmc.getInfoLabel("%sListItem.Title" % cont_prefix).decode('utf-8')
        # music content
        if media_type in ["album", "artist", "song"]:
            artist = xbmc.getInfoLabel("%sListItem.AlbumArtist" % cont_prefix).decode('utf-8')
            if not artist:
                artist = xbmc.getInfoLabel("%sListItem.Artist" % cont_prefix).decode('utf-8')
            album = xbmc.getInfoLabel("%sListItem.Album" % cont_prefix).decode('utf-8')
            disc = xbmc.getInfoLabel("%sListItem.DiscNumber" % cont_prefix).decode('utf-8')
            if artist:
                item_details = extend_dict(item_details, metadatautils.get_music_artwork(artist, album, title, disc))
        # movieset
        elif media_type == "movieset" and dbid:
            item_details = extend_dict(item_details, metadatautils.get_moviesetdetails(dbid))
        # pvr item
        elif media_type in ["tvchannel", "tvrecording", "channel", "recording"]:
            channel = xbmc.getInfoLabel("%sListItem.ChannelName" % cont_prefix).decode('utf-8')
            genre = xbmc.getInfoLabel("%sListItem.Genre" % cont_prefix)
            item_details["type"] = media_type
            item_details = extend_dict(item_details, metadatautils.get_pvr_artwork(title, channel, genre))

    metadatautils.close()
    # proceed with infodialog if we have details
    if item_details:
        win = DialogVideoInfo("DialogVideoInfo.xml", "", listitem=item_details)
        win.doModal()
        del win
