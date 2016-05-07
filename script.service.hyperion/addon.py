'''
    Kodi video capturer for Hyperion
	
	Copyright (c) 2013-1016 Hyperion Team

	Permission is hereby granted, free of charge, to any person obtaining a copy
	of this software and associated documentation files (the "Software"), to deal
	in the Software without restriction, including without limitation the rights
	to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
	copies of the Software, and to permit persons to whom the Software is
	furnished to do so, subject to the following conditions:

	The above copyright notice and this permission notice shall be included in
	all copies or substantial portions of the Software.

	THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
	IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
	FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
	AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
	LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
	OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
	THE SOFTWARE.
'''

import xbmc
import xbmcaddon
import xbmcgui
import os

# Add the library path before loading Hyperion
__addon__      = xbmcaddon.Addon()
__cwd__        = __addon__.getAddonInfo('path')
sys.path.append(xbmc.translatePath(os.path.join(__cwd__, 'resources', 'lib')))
		
from settings import Settings
from state import DisconnectedState

if  __name__ == "__main__":
	# read settings
	settings = Settings()

	# initialize the state
	state = DisconnectedState(settings)
	
	# start looping
	while not settings.abort:
		# execute the current state
		next_state = state.execute()
		
		# delete the old state if necessary
		if state != next_state:
			del state
			
		# advance to the next state
		state = next_state
		
	# clean up the state closing the connection if present
	del state
	del settings
