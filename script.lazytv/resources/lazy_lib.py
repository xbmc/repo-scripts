# declare file encoding
# -*- coding: utf-8 -*-

#  Copyright (C) 2013 KodeKarnage
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
#  along with XBMC; see the file COPYING.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html

import json, xbmc, xbmcaddon, xbmcgui
import sys
import time, datetime

_addon_ = xbmcaddon.Addon("script.lazytv")
_setting_ = _addon_.getSetting
lang = _addon_.getLocalizedString
dialog = xbmcgui.Dialog()

def proc_ig(ignore_list, ignore_by):
	il = ignore_list.split("|")
	return [i.replace(ignore_by+":-:","") for i in il if ignore_by+":-:" in i]

def gracefail(message):
	dialog.ok("LazyTV",message)
	sys.exit()

def json_query(query, ret):
	try:
		xbmc_request = json.dumps(query)
		result = xbmc.executeJSONRPC(xbmc_request)
		if ret:
			return json.loads(result)['result']
		else:
			return json.loads(result)
	except:
		#failure notification
		gracefail(lang(32200))

def player_start():
	#the play list is now complete, this next part starts playing
	play_command = {'jsonrpc': '2.0','method': 'Player.Open','params': {'item': {'playlistid':1}},'id': 1}
	json_query(play_command, False)  

def dict_engine(show, add_by):
	d = {}
	d['jsonrpc'] = '2.0'
	d['method'] = 'Playlist.Add'
	d['id'] = 1	
	d['params'] = {}
	d['params']['item'] = {}
	d['params']['item'][add_by] = show
	d['params']['playlistid'] = 1
	return d

def playlist_selection_window():
	'Purpose: launch Select Window populated with smart playlists'
	plf = {"jsonrpc": "2.0", "method": "Files.GetDirectory", "params": {"directory": "special://profile/playlists/video/", "media": "video"}, "id": 1}
	playlist_files = json_query(plf, True)['files']
	if playlist_files != None:
		plist_files = dict((x['label'],x['file']) for x in playlist_files)
		playlist_list =  plist_files.keys()
		playlist_list.sort()
		inputchoice = xbmcgui.Dialog().select(lang(32048), playlist_list)
		return plist_files[playlist_list[inputchoice]]
	else:
		return 'empty'

def fix_name(name):
	try:
		str(name).lower
		n = name
	except:
		n = name.encode("utf-8")#.encode('latin').decode('latin').encode('utf-8')
	return n

def day_calc(date_string, todate, output):
	op_format = '%Y-%m-%d %H:%M:%S'
	lw = time.strptime(date_string, op_format)
	if output == 'diff':
		lw_date = datetime.date(lw[0],lw[1],lw[2])
		day_string = str((todate - lw_date).days) + " days)"
		return day_string
	else:
		lw_max = datetime.datetime(lw[0],lw[1],lw[2],lw[3],lw[4],lw[5])
		date_num = time.mktime(lw_max.timetuple())
		return date_num
		
