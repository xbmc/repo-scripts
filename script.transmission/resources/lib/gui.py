# -*- coding: utf-8 -*-
# Copyright (c) 2010 Correl J. Roush

import os
import sys
import base64
import xbmc
import xbmcgui
from basictypes.bytes import Bytes
from repeater import Repeater

_ = sys.modules[ "__main__" ].__language__
__settings__ = sys.modules[ "__main__" ].__settings__

KEY_BUTTON_BACK = 275
KEY_KEYBOARD_ESC = 61467

EXIT_SCRIPT = ( 6, 10, 247, 275, 61467, 216, 257, 61448, )
CANCEL_DIALOG = EXIT_SCRIPT + ( 216, 257, 61448, )


class TransmissionGUI(xbmcgui.WindowXMLDialog):
    def __init__(self, strXMLname, strFallbackPath, strDefaultName, bforeFallback=0):
        self.list = {}
        self.torrents = {}
        self.repeater = None
    def onInit(self):
        p = xbmcgui.DialogProgress()
        p.create(_(0), _(1)) # 'Transmission', 'Connecting to Transmission'
        params = {
            'address': __settings__.getSetting('rpc_host'),
            'port': __settings__.getSetting('rpc_port'),
            'user': __settings__.getSetting('rpc_user'),
            'password': __settings__.getSetting('rpc_password')
        }
        import transmissionrpc
        try:
            self.transmission = transmissionrpc.Client(**params)
        except:
            p.close()
            self.close()
            d = xbmcgui.Dialog()
            (type, e, traceback) = sys.exc_info()

            message = _(9000) # Unexpected error
            if type is transmissionrpc.TransmissionError:
                if e.original:
                    if e.original.code is 401:
                        message = _(9002) # Invalid auth
                    else:
                        message = _(9001) # Unable to connect
                if d.yesno(_(2), message, _(3)):
                    __settings__.openSettings()
            elif type is ValueError:
                # In python 2.4, urllib2.HTTPDigestAuthHandler will barf up a lung
                # if auth fails and the server wants non-digest authentication
                message = _(9002) # Invalid auth
                if d.yesno(_(2), message, _(3)):
                    __settings__.openSettings()
            else:
                message = _(9000) # Unexpected error
                d.ok(_(2), message)

            return False
        p.close()
        self.updateTorrents()
        self.repeater = Repeater(1.0, self.updateTorrents)
        self.repeater.start()
    def updateTorrents(self):
        list = self.getControl(20)
        torrents = self.transmission.info()
        for i, torrent in torrents.iteritems():
            statusline = "[%(status)s] %(down)s down (%(pct).2f%%), %(up)s up (Ratio: %(ratio).2f)" % \
                {'down': Bytes.format(torrent.downloadedEver), 'pct': torrent.progress, \
                'up': Bytes.format(torrent.uploadedEver), 'ratio': torrent.ratio, \
                'status': torrent.status}
            if torrent.status is 'downloading':
                statusline += " ETA: %(eta)s" % \
                    {'eta': torrent.eta}
            if i not in self.list:
                # Create a new list item
                l = xbmcgui.ListItem(label=torrent.name, label2=statusline)
                list.addItem(l)
                self.list[i] = l
            else:
                # Update existing list item
                l = self.list[i]
            self.torrents = torrents
            l.setLabel(torrent.name)
            l.setLabel2(statusline)
            l.setProperty('TorrentID', str(i))
            l.setProperty('TorrentProgress', "%.2ff" % torrent.progress)
            l.setInfo('torrent', torrent.fields)
            l.setInfo('video', {'episode': int(torrent.progress)})

        removed = [id for id in self.list.keys() if id not in torrents.keys()]
        if len(removed) > 0:
            # Clear torrents from the list that have been removed
            for id in removed:
                del self.list[id]
            list.reset()
            for id, item in self.list.iteritems():
                list.addItem(item)
        list.setEnabled(bool(torrents))

    def onClick(self, controlID):
        list = self.getControl(20)
        if (controlID == 11):
            # Add torrent
            d = xbmcgui.Dialog()
            filename = d.browse(1, _(0), 'files', '.torrent')
            try:
                f = open(filename, 'r')
                data = base64.b64encode(f.read())
                self.transmission.add(data)
            except:
                pass
        if (controlID == 12):
            # Remove selected torrent
            item = list.getSelectedItem()
            if item and xbmcgui.Dialog().yesno(_(0), 'Remove \'%s\'?' % self.torrents[int(item.getProperty('TorrentID'))].name):
                remove_data = xbmcgui.Dialog().yesno(_(0), 'Remove data as well?')
                self.transmission.remove(int(item.getProperty('TorrentID')), remove_data)
        if (controlID == 13):
            # Stop selected torrent
            item = list.getSelectedItem()
            if item:
                self.transmission.stop(int(item.getProperty('TorrentID')))
        if (controlID == 14):
            # Start selected torrent
            item = list.getSelectedItem()
            if item:
                t = int(item.getProperty('TorrentID'))
                self.transmission.start(int(item.getProperty('TorrentID')))
        if (controlID == 15):
            # Stop all torrents
            self.transmission.stop(self.torrents.keys())
        if (controlID == 16):
            # Start all torrents
            self.transmission.start(self.torrents.keys())
        if (controlID == 17):
            # Exit button
            self.close()
        if (controlID == 20):
            # A torrent was chosen, show details
            item = list.getSelectedItem()
            w = TorrentInfoGUI("script-Transmission-details.xml",os.getcwd() ,"Default")
            w.setTorrent(self.transmission, int(item.getProperty('TorrentID')))
            w.doModal()
            del w
    def onFocus(self, controlID):
        pass

    def onAction( self, action ):
        if ( action.getButtonCode() in CANCEL_DIALOG ):
            self.close()
    def close(self):
        if self.repeater:
            self.repeater.stop()
        super(TransmissionGUI, self).close()


class TorrentInfoGUI(xbmcgui.WindowXMLDialog):
    def __init__(self, strXMLname, strFallbackPath, strDefaultName, bforeFallback=0):
        self.transmission = None
        self.torrent_id = None
        self.list = {}
        self.repeater = Repeater(1.0, self.updateTorrent)
    def setTorrent(self, transmission, t_id):
        self.transmission = transmission
        self.torrent_id = t_id
        self.repeater.start()
    def updateTorrent(self):
        pbar = self.getControl(219)
        list = self.getControl(220)
        labelName = self.getControl(1)
        labelStatus = self.getControl(2)
        torrent = self.transmission.info()[self.torrent_id]
        files = self.transmission.get_files(self.torrent_id)[self.torrent_id]

        statusline = "[%(status)s] %(down)s down (%(pct).2f%%), %(up)s up (Ratio: %(ratio).2f)" % \
            {'down': Bytes.format(torrent.downloadedEver), 'pct': torrent.progress, \
            'up': Bytes.format(torrent.uploadedEver), 'ratio': torrent.ratio, \
            'status': torrent.status}
        if torrent.status is 'downloading':
            statusline += " ETA: %(eta)s" % \
                    {'eta': torrent.eta}

        labelName.setLabel(torrent.name)
        labelStatus.setLabel(statusline)
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
    def onInit(self):
        self.updateTorrent()
    def close(self):
        self.repeater.stop()
        super(TorrentInfoGUI, self).close()
    def onAction(self, action):
        if (action.getButtonCode() in CANCEL_DIALOG):
            self.close()
            pass
    def onClick(self, controlID):
        pass
    def onFocus(self, controlID):
        pass
