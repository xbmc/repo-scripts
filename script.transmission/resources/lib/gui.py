# -*- coding: utf-8 -*-
# Copyright (c) 2010 Correl J. Roush

import sys
import base64
import threading
import xbmc
import xbmcgui
from basictypes.bytes import Bytes
import transmissionrpc
import search
import common

_ = sys.modules[ "__main__" ].__language__
__settings__ = sys.modules[ "__main__" ].__settings__

KEY_BUTTON_BACK = 275
KEY_KEYBOARD_ESC = 61467
KEY_MENU_ID = 92

EXIT_SCRIPT = ( 6, 10, 247, 275, 61467, 216, 257, 61448, )
CANCEL_DIALOG = EXIT_SCRIPT + ( 216, 257, 61448, )

UPDATE_INTERVAL = 1.0

STATUS_ICONS = {'stopped': 'pause.png',
                'seeding': 'ok.png',
                'downloading': 'down.png'}

class TransmissionGUI(xbmcgui.WindowXMLDialog):
    def __init__(self, strXMLname, strFallbackPath, strDefaultName, bforeFallback=0):
        self.list = {}
        self.torrents = {}
        self.timer = None
    def set_settings(self, params):
        __settings__.setSetting('rpc_host', params['address'])
        __settings__.setSetting('rpc_port', params['port'])
        __settings__.setSetting('rpc_user', params['user'])
        __settings__.setSetting('rpc_password', params['password'])
    def onInit(self):
        p = xbmcgui.DialogProgress()
        p.create(_(32000), _(32001)) # 'Transmission', 'Connecting to Transmission'
        try:
            self.transmission = common.get_rpc_client()
        except:
            p.close()
            self.close()
            (type, e, traceback) = sys.exc_info()
            message = _(32900) # Unexpected error
            if type is transmissionrpc.TransmissionError:
                if e.original:
                    if e.original.code is 401:
                        message = _(32902) # Invalid auth
                    else:
                        message = _(32901) # Unable to connect
                if xbmcgui.Dialog().yesno(_(32002), message, _(32003)):
                    __settings__.openSettings()
            elif type is ValueError:
                # In python 2.4, urllib2.HTTPDigestAuthHandler will barf up a lung
                # if auth fails and the server wants non-digest authentication
                message = _(32902) # Invalid auth
                if xbmcgui.Dialog().yesno(_(32002), message, _(32003)):
                    __settings__.openSettings()
            else:
                message = _(32900) # Unexpected error
                xbmcgui.Dialog().ok(_(32002), message)
            return False
        self.updateTorrents()
        p.close()
        self.timer = threading.Timer(UPDATE_INTERVAL, self.updateTorrents)
        self.timer.start()
    def updateTorrents(self):
        list = self.getControl(120)
        self.torrents = self.transmission.info()
        for i, torrent in self.torrents.iteritems():
            statusline = "[%(status)s] %(down)s down (%(pct).2f%%), %(up)s up (Ratio: %(ratio).2f)" % \
                {'down': Bytes.format(torrent.downloadedEver), 'pct': torrent.progress, \
                'up': Bytes.format(torrent.uploadedEver), 'ratio': torrent.ratio, \
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
            for id, item in self.list.iteritems():
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
            engines = [
                (_(32200), None),
                (_(32202), search.TPB),
                (_(32203), search.Mininova),
                (_(32204), search.Kickass),
            ]
            selected = xbmcgui.Dialog().select(_(32000), [i[0] for i in engines])
            if selected < 0:
                return
            engine = engines[selected][1]
            if not engine:
                filename = xbmcgui.Dialog().browse(1, _(32000), 'files', '.torrent')
                try:
                    f = open(filename, 'r')
                    data = base64.b64encode(f.read())
                    self.transmission.add(data)
                except:
                    pass
            else:
                kb = xbmc.Keyboard('', engines[selected][0])
                kb.doModal()
                if not kb.isConfirmed():
                    return
                terms = kb.getText()
                p = xbmcgui.DialogProgress()
                p.create(_(32000), _(32290))
                try:
                    results = engine().search(terms)
                except:
                    p.close()
                    xbmcgui.Dialog().ok(_(32000), _(32292))
                    return
                p.close()
                if not results:
                    xbmcgui.Dialog().ok(_(32000), _(32291))
                    return
                selected = xbmcgui.Dialog().select(_(32000), ['[S:%d L:%d] %s' % (t['seeds'], t['leechers'], t['name']) for t in results])
                if selected < 0:
                    return
                try:
                    self.transmission.add_torrent(results[selected]['url'])
                except:
                    xbmcgui.Dialog().ok(_(32000), _(32293))
                    return
        if (controlID == 112):
            # Remove selected torrent
            item = list.getSelectedItem()
            if item and xbmcgui.Dialog().yesno(_(32000), 'Remove \'%s\'?' % self.torrents[int(item.getProperty('TorrentID'))].name):
                remove_data = xbmcgui.Dialog().yesno(_(32000), 'Remove data as well?')
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
            __settings__.openSettings()
            p = xbmcgui.DialogProgress()
            p.create(_(32000), _(32001)) # 'Transmission', 'Connecting to Transmission'
            try:
                self.transmission = common.get_rpc_client()
                self.updateTorrents()
                p.close()
            except:
                p.close()
                xbmcgui.Dialog().ok(_(32002), _(32901))
                # restore settings
                self.set_settings(prev_settings)
                try:
                    self.transmission = common.get_rpc_client()
                except err:
                    xbmcgui.Dialog().ok(_(32002), _(32901))
                    self.close()
        if (controlID == 120):
            # A torrent was chosen, show details
            item = list.getSelectedItem()
            w = TorrentInfoGUI("script-Transmission-details.xml", __settings__.getAddonInfo('path') ,"Default")
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
            {'down': Bytes.format(torrent.downloadedEver), 'pct': torrent.progress, \
            'up': Bytes.format(torrent.uploadedEver), 'ratio': torrent.ratio, \
            'status': torrent.status}
        if torrent.status is 'downloading':
            statusline += " ETA: %(eta)s" % \
                    {'eta': torrent.eta}

        labelName.setLabel(torrent.name)
        labelStatus.setLabel(statusline)
        labelProgress.setLabel('%3d%%' % (torrent.progress))
        pbar.setPercent(torrent.progress)

        for i, file in files.iteritems():
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
