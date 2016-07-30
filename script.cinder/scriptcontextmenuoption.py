# This file is part of Cinder.
#
# Cinder is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Cinder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Cinder.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import xbmc
import xbmcaddon
import xbmcgui

addon = xbmcaddon.Addon()
resourcelibs = xbmc.translatePath(addon.getAddonInfo('path')).decode('utf-8')
resourcelibs = os.path.join(resourcelibs, u'resources', u'lib')
sys.path.append(resourcelibs)

import CinderRandomPlayer
import pykodi

# This entry point allows the user to select a particular TV Show or season to
# pick random episodes from. It is outside of the scope of the configured sources
# and can be executed on any title or season folder. 
# Other random options and number of episodes to queue up still apply.

def main():
    contextMenuSource = sys.listitem.getfilename()

    # see if the user selected a directory. display an error and exit if the 
    # user selected anything other than a directory 
    jsonRequest = pykodi.get_base_json_request('Files.GetDirectory')
    jsonRequest['params'] = {'directory': contextMenuSource}
    jsonResponse = pykodi.execute_jsonrpc(jsonRequest)
    if 'error' in jsonResponse: 
        xbmcgui.Dialog().notification(addon.getLocalizedString(32400), \
                                      addon.getLocalizedString(32406), \
                                      xbmcgui.NOTIFICATION_WARNING)
        pykodi.log(str(jsonResponse), xbmc.LOGNOTICE)
        sys.exit(1)

    # these parameters do not apply if the user chose the "Run Cinder from here"
    # context menu option

    # Changing these variables will not change how Cinder behaves
    additionalSourceList = []
    additionalSourceWeightList = []
    maximumSourceWeight = 100

    cinderRandomPlayer = CinderRandomPlayer.CinderRandomPlayer(additionalSourceList, additionalSourceWeightList, maximumSourceWeight, contextMenuSource)
    cinderRandomPlayer.playRandomEpisodes()


if __name__ == '__main__':
    main()
