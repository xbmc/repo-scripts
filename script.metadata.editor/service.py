#!/usr/bin/python
# coding: utf-8

########################

import xbmc

from resources.lib.helper import *
from resources.lib.database import *
from resources.lib.editor import *
from resources.lib.nfo_updater import *

########################

class Service(xbmc.Monitor):
    def __init__(self):
        while not self.abortRequested():
            self.waitForAbort(100)

    def onNotification(self, sender, method, data):
        if method in ['VideoLibrary.OnUpdate', 'Player.OnStop']:
            data = eval(data.replace(':true', ': True').replace(':false', ': False'))
            item = data.get('item', {})
            dbid = item.get('id')
            dbtype = item.get('type', '')

            if dbid and (dbtype in ['movie', 'episode']):

                if method == 'VideoLibrary.OnUpdate' and ADDON.getSettingBool('nfo_updating') and ADDON.getSettingBool('write_watched_stated') and ADDON.getSettingBool('playback_update_playcount'):
                    if data.get('playcount') is not None:
                        update_nfo(dbid=dbid, dbtype=dbtype)

                if method == 'Player.OnStop' and ADDON.getSettingBool('playback_user_rating'):
                    if data.get('end'):
                        # give Kodi time to return to the UI
                        xbmc.sleep(1000)

                        if not condition('Player.HasMedia'):
                            db = Database(dbid=dbid, dbtype=dbtype)
                            getattr(db, dbtype)()
                            details = db.result().get(dbtype)[0]
                            del db

                            title = details.get('title')
                            showtitle = details.get('showtitle')
                            episode = details.get('episode')
                            season = details.get('season')

                            if season < 10:
                                season = '0' + str(season)
                            if episode < 10:
                                episode = '0' + str(episode)

                            msg_title = title if dbtype == 'movie' else '%s - S%sE%s - %s' % (showtitle, season, episode, title)

                            if DIALOG.yesno(ADDON.getLocalizedString(32001), ADDON.getLocalizedString(32054) + '[CR]' + msg_title):
                                editor = EditDialog(dbid=dbid, dbtype=dbtype)
                                editor.set(key='userrating', type='userrating')
                                del editor


if __name__ == "__main__":
    Service()