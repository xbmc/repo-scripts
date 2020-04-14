# -*- coding: utf-8 -*-
# Copyright (c) 2010 Correl J. Roush

from kodi_six import xbmc, xbmcgui
from resources.lib import common
from resources.lib import transmissionrpc
from six import iteritems

import sys
import base64
import threading

KEY_BUTTON_BACK = 275
KEY_KEYBOARD_ESC = 61467
KEY_MENU_ID = 92

EXIT_SCRIPT = ( 6, 10, 247, 275, 61467, 216, 257, 61448, )
CANCEL_DIALOG = EXIT_SCRIPT + ( 216, 257, 61448, )

UPDATE_INTERVAL = 1.0

STATUS_ICONS = {'stopped': 'pause.png',
                'seeding': 'ok.png',
                'downloading': 'down.png'}

def formatBytes(value, multiplier=None, asBits=False ):
    """Special data-type for byte values"""
    KILOBYTES = 1024.0
    MEGABYTES = KILOBYTES*1024
    GIGABYTES = MEGABYTES*1024
    TERABYTES = GIGABYTES*1024

    displayNames = [
        (TERABYTES, 'TB'),
        (GIGABYTES, 'GB'),
        (MEGABYTES, 'MB'),
        (KILOBYTES, 'KB'),
        (0, 'B'),
    ]

    """Format as a string which is back-coercable

    multiplier -- pass in the appropriate multiplier for
        the value (i.e. request 'KB' to get back as kilobytes,
        default (None) indicates that the nearest should
        be used
    asBits -- if True, format a Byte value as bits, suitable
        for display in a "bandwidth" setting, as distinct
        from a simple measure of bytes.
    """
    if value < 0:
        value = abs(value)
        neg = '-'
    else:
        neg = ""
    if asBits:
        value = value * 8
    for threshold, name in displayNames:
        if value >= threshold:
            if threshold:
                value = value/threshold
                value = '%3.1f'%(value,)
            if asBits:
                name = name[:-1] + name[-1].lower()
            return '%s%s %s'%( neg, value, name)
    raise RuntimeError( """A value %r both > 0 and < 0 was encountered?"""%(value,))

class TransmissionGUI(xbmcgui.WindowXMLDialog):
    def __init__(self, strXMLname, strFallbackPath, strDefaultName, bforeFallback=0):
        self.list = {}
        self.torrents = {}
        self.timer = None
    def set_settings(self, params):
        common.set_setting('rpc_host', params['address'])
        common.set_setting('rpc_port', params['port'])
        common.set_setting('rpc_user', params['user'])
        common.set_setting('rpc_password', params['password'])
    def onInit(self):
        p = xbmcgui.DialogProgress()
        p.create(common.get_localized_string(32000), # 'Transmission'
                 common.get_localized_string(32001)) # 'Connecting to Transmission'
        try:
            self.transmission = common.get_rpc_client()
        except:
            p.close()
            self.close()
            (type, e, traceback) = sys.exc_info()
            message = common.get_localized_string(32900) # Unexpected error
            if type is transmissionrpc.TransmissionError:
                if e.original:
                    if e.original.code is 401:
                        message = common.get_localized_string(32902) # Invalid auth
                    else:
                        message = common.get_localized_string(32901) # Unable to connect
                if xbmcgui.Dialog().yesno(common.get_localized_string(32002),
                                          message +
                                          '\n' +
                                          common.get_localized_string(32003)):
                    common.open_settings()
            elif type is ValueError:
                # In python 2.4, urllib2.HTTPDigestAuthHandler will barf up a lung
                # if auth fails and the server wants non-digest authentication
                message = common.get_localized_string(32902) # Invalid auth
                if xbmcgui.Dialog().yesno(common.get_localized_string(32002),
                                          message +
                                          '\n' +
                                          common.get_localized_string(32003)):
                    common.open_settings()
            else:
                message = common.get_localized_string(32900) # Unexpected error
                xbmcgui.Dialog().ok(common.get_localized_string(32002), message)
            return False
        self.updateTorrents()
        p.close()
        self.timer = threading.Timer(UPDATE_INTERVAL, self.updateTorrents)
        self.timer.start()
    def updateTorrents(self):
        list = self.getControl(120)
        self.torrents = self.transmission.info()
        for i, torrent in iteritems(self.torrents):
            statusline = "[%(status)s] %(down)s down (%(pct).2f%%), %(up)s up (Ratio: %(ratio).2f)" % \
                {'down': formatBytes(torrent.downloadedEver), 'pct': torrent.progress, \
                'up': formatBytes(torrent.uploadedEver), 'ratio': torrent.ratio, \
                'status': torrent.status}
            if i not in self.list:
                # Create a new list item
                l = xbmcgui.ListItem(label=torrent.name, label2=statusline)
                list.addItem(l)
                self.list[i] = l
            else:
                # Update existing list item
                l = self.list[i]
            l.setLabel(torrent.name)
            l.setLabel2(statusline)
            l.setProperty('TorrentStatusIcon', STATUS_ICONS.get(torrent.status, 'pending.png'))
            l.setProperty('TorrentID', str(i))
            l.setProperty('TorrentProgress', "%3d%%" % torrent.progress)

        removed = [id for id in self.list.keys() if id not in self.torrents.keys()]
        if len(removed) > 0:
            # Clear torrents from the list that have been removed
            for id in removed:
                del self.list[id]
            list.reset()
            for id, item in iteritems(self.list):
                list.addItem(item)
        list.setEnabled(bool(self.torrents))

        # Update again, after an interval, but only if the timer has not been cancelled
        if self.timer:
          self.timer = threading.Timer(UPDATE_INTERVAL, self.updateTorrents)
          self.timer.start()
    def onClick(self, controlID):
        list = self.getControl(120)
        if (controlID == 111):
            # Add torrent
            filename = xbmcgui.Dialog().browse(1,
                                               common.get_localized_string(32000),
                                               'files',
                                               '.torrent')
            try:
                f = open(filename, 'rb')
                data = base64.b64encode(f.read()).decode('ascii')
                self.transmission.add(data)
            except:
                pass

        if (controlID == 112):
            # Remove selected torrent
            item = list.getSelectedItem()
            if item and xbmcgui.Dialog().yesno(common.get_localized_string(32000),
                                               'Remove \'%s\'?' % self.torrents[int(item.getProperty('TorrentID'))].name):
                remove_data = xbmcgui.Dialog().yesno(common.get_localized_string(32000), 'Remove data as well?')
                self.transmission.remove(int(item.getProperty('TorrentID')), remove_data)
        if (controlID == 113):
            # Stop selected torrent
            item = list.getSelectedItem()
            if item:
                self.transmission.stop(int(item.getProperty('TorrentID')))
        if (controlID == 114):
            # Start selected torrent
            item = list.getSelectedItem()
            if item:
                self.transmission.start(int(item.getProperty('TorrentID')))
        if (controlID == 115):
            # Stop all torrents
            self.transmission.stop(self.torrents.keys())
        if (controlID == 116):
            # Start all torrents
            self.transmission.start(self.torrents.keys())
        if (controlID == 117):
            # Exit button
            self.close()
        if (controlID == 118):
            # Settings button
            prev_settings = common.get_settings()
            common.open_settings()
            p = xbmcgui.DialogProgress()
            p.create(common.get_localized_string(32000), common.get_localized_string(32001)) # 'Transmission', 'Connecting to Transmission'
            try:
                self.transmission = common.get_rpc_client()
                self.updateTorrents()
                p.close()
            except:
                p.close()
                xbmcgui.Dialog().ok(common.get_localized_string(32002), common.get_localized_string(32901))
                # restore settings
                self.set_settings(prev_settings)
                try:
                    self.transmission = common.get_rpc_client()
                except err:
                    xbmcgui.Dialog().ok(common.get_localized_string(32002), common.get_localized_string(32901))
                    self.close()
        if (controlID == 120):
            # A torrent was chosen, show details
            item = list.getSelectedItem()
            w = TorrentInfoGUI("script-Transmission-details.xml", common.get_addon_info('path') ,"Default")
            w.setTorrent(self.transmission, int(item.getProperty('TorrentID')))
            w.doModal()
            del w
    def onFocus(self, controlID):
        pass

    def onAction( self, action ):
        if ( action.getButtonCode() in CANCEL_DIALOG ) or (action.getId() == KEY_MENU_ID):
            self.close()
    def close(self):
        if self.timer:
            self.timer.cancel()
            self.timer.join()
        super(TransmissionGUI, self).close()


class TorrentInfoGUI(xbmcgui.WindowXMLDialog):
    def __init__(self, strXMLname, strFallbackPath, strDefaultName, bforeFallback=0):
        self.transmission = None
        self.torrent_id = None
        self.list = {}
        self.timer = None
    def setTorrent(self, transmission, t_id):
        self.transmission = transmission
        self.torrent_id = t_id
        self.timer = threading.Timer(UPDATE_INTERVAL, self.updateTorrent)
        self.timer.start()
    def updateTorrent(self):
        pbar = self.getControl(219)
        list = self.getControl(220)
        labelName = self.getControl(1)
        labelStatus = self.getControl(2)
        labelProgress = self.getControl(11)
        torrent = self.transmission.info()[self.torrent_id]
        files = self.transmission.get_files(self.torrent_id)[self.torrent_id]

        statusline = "[%(status)s] %(down)s down, %(up)s up (Ratio: %(ratio).2f)" % \
            {'down': formatBytes(torrent.downloadedEver), 'pct': torrent.progress, \
            'up': formatBytes(torrent.uploadedEver), 'ratio': torrent.ratio, \
            'status': torrent.status}
        if torrent.status is 'downloading':
            statusline += " ETA: %(eta)s" % \
                    {'eta': torrent.eta}

        labelName.setLabel(torrent.name)
        labelStatus.setLabel(statusline)
        labelProgress.setLabel('%3d%%' % (torrent.progress))
        pbar.setPercent(torrent.progress)

        for i, file in iteritems(files):
            if i not in self.list:
                # Create a new list item
                l = xbmcgui.ListItem(label=file['name'])
                list.addItem(l)
                self.list[i] = l
            else:
                # Update existing list item
                l = self.list[i]
            l.setProperty('Progress', '[%3d%%]' % (file['completed'] * 100 / file['size']))

        # Update again, after an interval
        self.timer = threading.Timer(UPDATE_INTERVAL, self.updateTorrent)
        self.timer.start()
    def onInit(self):
        self.updateTorrent()
    def close(self):
        if self.timer:
            self.timer.cancel()
            self.timer.join()
        super(TorrentInfoGUI, self).close()
    def onAction(self, action):
        if (action.getButtonCode() in CANCEL_DIALOG) or (action.getId() == KEY_MENU_ID):
            self.close()
            pass
    def onClick(self, controlID):
        if controlID == 111:
            self.close()
    def onFocus(self, controlID):
        pass
