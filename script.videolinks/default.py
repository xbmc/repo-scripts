# -*- coding: utf-8 -*-

#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
#  (c) 2023 black_eagle

# This addon depends on support from TheAudioDB - Thank you !!

import sys
import xbmc
import xbmcaddon
from lib.videolinks import log, single_artist, process_all_artists

LANGUAGE = xbmcaddon.Addon().getLocalizedString

if len(sys.argv) == 2:
    artist_id = sys.argv[1]
    log(LANGUAGE(30005) + " {}".format(artist_id), xbmc.LOGINFO)
    single_artist(artist_id)
else:
    log(LANGUAGE(30007), xbmc.LOGINFO)
    process_all_artists()
message = LANGUAGE(30000) + " " + LANGUAGE(30018)
log(message, xbmc.LOGINFO)
