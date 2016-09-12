# -*- coding: utf-8 -*-
'''
    script.matchcenter - Football information for Kodi
    A program addon that can be mapped to a key on your remote to display football information.
    Livescores, Event details, Line-ups, League tables, next and previous matches by team. Follow what
    others are saying about the match in twitter.
    Copyright (C) 2016 enen92

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import thesportsdb
import xbmcgui
import xbmc
import sys
from resources.lib import livescores
from resources.lib import leaguetables
from resources.lib import eventdetails
from resources.lib import mainmenu
from resources.lib import ignoreleagues
from resources.lib import tweets
from resources.lib import leagueselection
from resources.lib import eventdetails
from resources.lib import matchhistory
from resources.lib.utilities.cache import AddonCache
from resources.lib.utilities import keymapeditor
from resources.lib.utilities import tweet
from resources.lib.utilities.common_addon import *
 
def get_params():
    pairsofparams = []
    if len(sys.argv) >= 2:
        params=sys.argv[1]
        pairsofparams=params.split('/')
        pairsofparams = [parm for parm in pairsofparams if parm]
    return pairsofparams

params=get_params()

if not params:
    if "script-matchcenter-MainMenu.xml" not in xbmc.getInfoLabel('Window.Property(xmlfile)'):
        mainmenu.start()
else:
    #Integration patterns below
    '''
    Eg: xbmc.executebuiltin("RunScript(script.matchcenter, /eventdetails/506227)")
    '''
    
    if params[0] == 'ignoreleagues':
        ignoreleagues.start()
    elif params[0] == 'keymapeditor':
        keymapeditor.run()
    elif params[0] == 'removecache':
        AddonCache.removeCachedData()
    elif params[0] == 'removetwitterhistory':
        tweet.remove_twitter_hashtag_history()
    elif params[0] == 'livescores':
        livescores.start(standalone=True)
    elif params[0] == 'twitter':
        if not params[1]:
            tweets.start()
        else:
            tweets.start(twitterhash=params[1], standalone=True)
    elif params[0] == 'leagueselection':
        leagueselection.start(standalone=True)
    elif params[0] == 'leaguetables' and params[1]:
        leaguetables.start_table(leagueid=params[1])
    elif params[0] == 'matchhistory' and params[1]:
        matchhistory.start(teamid=params[1])
    elif params[0] == 'eventdetails' and params[1]:
        eventdetails.showDetails(match=None,matchid=params[1])


try: xbmcplugin.endOfDirectory(int(sys.argv[1]))
except: sys.exit(0)

