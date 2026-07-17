#
#      Copyright (C) 2013 Tommy Winther
#      http://tommy.winther.nu
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this Program; see the file LICENSE.txt.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#

import random

import xbmcvfs
import xbmcaddon

from resources.lib.quizlib.gui import QuizGui


# Make sure data dir exists
PROFILE = xbmcaddon.Addon().getAddonInfo('profile')
if not xbmcvfs.exists(PROFILE):
    xbmcvfs.mkdirs(PROFILE)

# seed the random number generator used in various places
random.seed()

w = QuizGui()
w.doModal()
del w
