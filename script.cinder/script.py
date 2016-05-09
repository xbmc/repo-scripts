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

addon = xbmcaddon.Addon()
resourcelibs = xbmc.translatePath(addon.getAddonInfo('path')).decode('utf-8')
resourcelibs = os.path.join(resourcelibs, u'resources', u'lib')
sys.path.append(resourcelibs)

import CinderRandomPlayer

def main():

    # Add to this list to go beyond the 20 sources defined in the plugin configuration 
    #
    #   example:
    #
    #     additionalSourceList = ["smb://192.168.1.10/TV Shows/South Park", \
    #                             "smb://192.168.1.10/TV Shows/Family Guy", \
    #                             "smb://192.168.1.10/TV Shows/Two and a Half Men", \
    #                             "smb://192.168.1.10/TV Shows/It's Always Sunny in Philadelphia", \
    #                             "smb://192.168.1.10/TV Shows/Rick and Morty", \
    #                             "smb://192.168.1.10/TV Shows/How I Met Your Mother", \
    #                             "smb://192.168.1.10/TV Shows/The Big Bang Theory",
    #                             "smb://192.168.1.10/TV Shows/That '70s Show", \
    #                             "smb://192.168.1.10/TV Shows/Cheers",
    #                             "smb://192.168.1.10/TV Shows/Seinfeld"]
    #

    additionalSourceList = []


    # Add to this weight list to go beyond the 20 sources defined in the plugin configuration 
    #
    #   example:
    #
    #     additionalSourceWeightList = [100, \
    #                                   100, \
    #                                    90, \
    #                                    90, \
    #                                    80, \
    #                                    10, \
    #                                    10, \
    #                                    8, \
    #                                    5, \
    #                                    5]

    additionalSourceWeightList = []

    # note: additionalSourceList and additionalSourceWeightList must be the same length


    # Change this value to adjust the upper limit of the source weight list. 
    # If you want finer granularity increase above the default 100. 
    # For example suppose you want to have a 1 in 1000 chance of watching a given 
    # source instead of the default minimum of 1 in 100 chance. 
    # To do this change maximumSourceWeight to 1000. You can pick any positive integer 
    # between 1 and 1000000 as desired.
    #  note: Changing this value adjusts all configured sources in a way that is not reflected in the 
    #        KODI plugin configuration screen. For example assume that you have a
    #        source weighted at 90% and want it to stay at 90% after bumping maximumSourceWeight 
    #        up to 1000. You would need to change the corresponding weight entry to
    #        900 to have it remain at 90%. You also need to scale the weight of every source
    #        to maintain your desired percentages. You may need to leverage additionalSourceList
    #        and additionalSourceWeightList above to get the desired behavior.
    #
    #             chance of playback = source weight / maximumSourceWeight 
    #           

    maximumSourceWeight = 100


    cinderRandomPlayer = CinderRandomPlayer.CinderRandomPlayer(additionalSourceList, additionalSourceWeightList, maximumSourceWeight)
    cinderRandomPlayer.playRandomEpisodes()

if __name__ == '__main__':
    main()
