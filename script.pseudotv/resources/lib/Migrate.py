#   Copyright (C) 2011 Jason Anderson
#
#
# This file is part of PseudoTV.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import os
import xbmcaddon, xbmc, xbmcgui
import Settings
import Globals
import ChannelList



class Migrate:
    def log(self, msg, level = xbmc.LOGDEBUG):
        Globals.log('Migrate: ' + msg, level)


    def migrate(self):
        self.log("migration")
        curver = "0.0.0"

        try:
            curver = Globals.ADDON_SETTINGS.getSetting("Version")

            if len(curver) == 0:
                curver = "0.0.0"
        except:
            curver = "0.0.0"

        if curver == Globals.VERSION:
            return True

        Globals.ADDON_SETTINGS.setSetting("Version", Globals.VERSION)
        self.log("version is " + curver)

        if curver == "0.0.0":
            if self.initializeChannels():
                return True

        if self.compareVersions(curver, "1.0.2") < 0:
            self.log("Migrating to 1.0.2")

            # Migrate to 1.0.2
            for i in range(200):
                if os.path.exists(xbmc.translatePath('special://profile/playlists/video') + '/Channel_' + str(i + 1) + '.xsp'):
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(i + 1) + "_type", "0")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(i + 1) + "_1", "special://profile/playlists/video/Channel_" + str(i + 1) + ".xsp")
                elif os.path.exists(xbmc.translatePath('special://profile/playlists/mixed') + '/Channel_' + str(i + 1) + '.xsp'):
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(i + 1) + "_type", "0")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(i + 1) + "_1", "special://profile/playlists/mixed/Channel_" + str(i + 1) + ".xsp")

            currentpreset = 0

            for i in range(Globals.TOTAL_FILL_CHANNELS):
                chantype = 9999

                try:
                    chantype = int(Globals.ADDON_SETTINGS.getSetting("Channel_" + str(i + 1) + "_type"))
                except:
                    pass

                if chantype == 9999:
                    self.addPreset(i + 1, currentpreset)
                    currentpreset += 1

        # Migrate serial mode to rules
        if self.compareVersions(curver, "2.0.0") < 0:
            self.log("Migrating to 2.0.0")

            for i in range(999):
                try:
                    if Globals.ADDON_SETTINGS.getSetting("Channel_" + str(i + 1) + "_type") == '6':
                        if Globals.ADDON_SETTINGS.getSetting("Channel_" + str(i + 1) + "_2") == "6":
                            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(i + 1) + "_rulecount", "2")
                            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(i + 1) + "_rule_1_id", "8")
                            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(i + 1) + "_rule_2_id", "9")
                            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(i + 1) + "_2", "4")
                except:
                    pass

        return True


    def addPreset(self, channel, presetnum):
        networks = ['ABC', 'AMC', 'Bravo', 'CBS', 'Comedy Central', 'Food Network', 'FOX', 'FX', 'HBO', 'NBC', 'SciFi', 'The WB']
        genres = ['Animation', 'Comedy', 'Documentary', 'Drama', 'Fantasy']
        studio = ['Brandywine Productions Ltd.', 'Fox 2000 Pictures', 'GK Films', 'Legendary Pictures', 'Universal Pictures']

        if presetnum < len(networks):
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_type", "1")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_1", networks[presetnum])
        elif presetnum - len(networks) < len(genres):
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_type", "5")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_1", genres[presetnum - len(networks)])
        elif presetnum - len(networks) - len(genres) < len(studio):
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_type", "2")
            Globals.ADDON_SETTINGS.setSetting("Channel_" + str(channel) + "_1", studio[presetnum - len(networks) - len(genres)])


    def compareVersions(self, version1, version2):
        retval = 0
        ver1 = version1.split('.')
        ver2 = version2.split('.')

        for i in range(min(len(ver1), len(ver2))):
            try:
                if int(ver1[i]) < int(ver2[i]):
                    retval = -1
                    break

                if int(ver1[i]) > int(ver2[i]):
                    retval = 1
                    break
            except:
                try:
                    v = int(ver1[i])
                    retval = 1
                except:
                    retval = -1

                break

        if retval == 0:
            if len(ver1) > len(ver2):
                retval = 1
            elif len(ver2) > len(ver1):
                retval = -1

        return retval


    def initializeChannels(self):
        updatedlg = xbmcgui.DialogProgress()
        updatedlg.create("PseudoTV", "Initializing")
        updatedlg.update(1, "Initializing", "Initial Channel Setup")
        chanlist = ChannelList.ChannelList()
        chanlist.background = True
        chanlist.fillTVInfo(True)
        updatedlg.update(30)
        chanlist.fillMovieInfo(True)
        updatedlg.update(60)
        # Now create TV networks, followed by mixed genres, followed by TV genres, and finally movie genres
        currentchan = 1
        mixedlist = []

        for item in chanlist.showGenreList:
            curitem = item[0].lower()

            for a in chanlist.movieGenreList:
                if curitem == a[0].lower():
                    mixedlist.append([item[0], item[1], a[1]])
                    break

        mixedlist.sort(key=lambda x: x[1] + x[2], reverse=True)
        currentchan = self.initialAddChannels(chanlist.networkList, 1, currentchan)
        updatedlg.update(70)

        # Mixed genres
        if len(mixedlist) > 0:
            added = 0.0

            for item in mixedlist:
                if item[1] > 2 and item[2] > 1:
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(currentchan) + "_type", "5")
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(currentchan) + "_1", item[0])
                    added += 1.0
                    currentchan += 1
                    itemlow = item[0].lower()

                    # Remove that genre from the shows genre list
                    for i in range(len(chanlist.showGenreList)):
                        if itemlow == chanlist.showGenreList[i][0].lower():
                            chanlist.showGenreList.pop(i)
                            break

                    # Remove that genre from the movie genre list
                    for i in range(len(chanlist.movieGenreList)):
                        if itemlow == chanlist.movieGenreList[i][0].lower():
                            chanlist.movieGenreList.pop(i)
                            break

                    if added > 10:
                        break

                    updatedlg.update(int(70 + 10.0 / added))

        updatedlg.update(80)
        currentchan = self.initialAddChannels(chanlist.showGenreList, 3, currentchan)
        updatedlg.update(90)
        currentchan = self.initialAddChannels(chanlist.movieGenreList, 4, currentchan)
        updatedlg.close()

        if currentchan > 1:
            return True

        return False


    def initialAddChannels(self, thelist, chantype, currentchan):
        if len(thelist) > 0:
            counted = 0
            lastitem = 0
            curchancount = 1
            lowerlimit = 1
            lowlimitcnt = 0

            for item in thelist:
                if item[1] > lowerlimit:
                    if item[1] != lastitem:
                        if curchancount + counted <= 10 or counted == 0:
                            counted += curchancount
                            curchancount = 1
                            lastitem = item[1]
                        else:
                            break
                    else:
                        curchancount += 1

                    lowlimitcnt += 1

                    if lowlimitcnt == 3:
                        lowlimitcnt = 0
                        lowerlimit += 1
                else:
                    break

            if counted > 0:
                for item in thelist:
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(currentchan) + "_type", str(chantype))
                    Globals.ADDON_SETTINGS.setSetting("Channel_" + str(currentchan) + "_1", item[0])
                    counted -= 1
                    currentchan += 1

                    if counted == 0:
                        break

        return currentchan
