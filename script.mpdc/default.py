#/*
# *      Copyright (C) 2010 lzoubek
# *
# *
# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with this program; see the file COPYING.  If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html
# *
# */
import sys,os
import xbmc,xbmcaddon,xbmcgui,xbmcplugin
__scriptid__ = 'script.mpdc'
__addon__ = xbmcaddon.Addon(id=__scriptid__)
SERVER_LIST = 120
ACTION_CLOSE = [9,10,92]
STATUS = 100
SETTINGS = 101
sys.path.append( os.path.join ( __addon__.getAddonInfo('path'), 'resources','lib') )
import xbmpc
import mpdcdialog as dialog
STATUS_ON='on'
STATUS_OFF='off'
STR_CONNECTING=__addon__.getLocalizedString(30007)
STR_CONNECTING_TITLE=__addon__.getLocalizedString(30015) 
STR_SELECT_PROFILE=__addon__.getLocalizedString(30008)
STR_HOST_ONLINE=__addon__.getLocalizedString(30009)
STR_HOST_OFFLINE=__addon__.getLocalizedString(30010)
class MpdProfile:
	
	def __init__(self,profile_id):
		self.id=profile_id
		self.addon = xbmcaddon.Addon(id=__scriptid__)
		self.name = self.addon.getSetting(self.id+'_name')
		self.host = self.addon.getSetting(self.id+'_mpd_host')	
		self.port = self.addon.getSetting(self.id+'_mpd_port')
		self.stream_url = self.addon.getSetting(self.id+'_stream_url')
		self.password = self.addon.getSetting(self.id+'_mpd_pass')
		self.status = STR_HOST_OFFLINE
		self.stat = STATUS_OFF
		self.enabled=False
		if self.addon.getSetting(self.id+'_enabled') == 'true':
			self.enabled=True

	def update(self):
		self.addon = xbmcaddon.Addon(id=__scriptid__)
		self.name = self.addon.getSetting(self.id+'_name')
		self.host = self.addon.getSetting(self.id+'_mpd_host')	
		self.port = self.addon.getSetting(self.id+'_mpd_port')
		self.stream_url = self.addon.getSetting(self.id+'_stream_url')
		self.password = self.addon.getSetting(self.id+'_mpd_pass')
		self.status = STR_HOST_OFFLINE
		self.stat=STATUS_OFF
		self.enabled=False
		if self.addon.getSetting(self.id+'_enabled') == 'true':
			self.enabled=True
		if not self.enabled:
			return
		try:
			client = xbmpc.MPDClient()
			client.connect(self.host,int(self.port))
			client.close()
			client.disconnect()
			self.status = STR_HOST_ONLINE
			self.stat=STATUS_ON
			
		except:
			pass


class SelectMPDProfile ( xbmcgui.WindowXMLDialog ) :
	
	def __init__( self, *args, **kwargs ):
		self.profiles = []
		self.skin=args[2]	
	
	def onFocus (self,controlId ):
		self.controlId=controlId
		
	def onInit (self ):		
		self.update_servers()
			
	def update_servers( self ):
		self.getControl( SERVER_LIST ).reset()
		self.getControl( STATUS ).setLabel( STR_CONNECTING )
		p = xbmcgui.DialogProgress()
		p.create(STR_CONNECTING_TITLE,STR_CONNECTING)
		percent = 0
		for item in self.profiles:
			item.update()
			if p.iscanceled():
				break
			percent = percent+33
			p.update(percent)
			if item.enabled:
				listitem = xbmcgui.ListItem( label=item.name)
				listitem.setProperty( 'id', item.id )
				listitem.setProperty( 'status', item.status )
				listitem.setProperty( 'stat', item.stat )
				self.getControl( SERVER_LIST ).addItem( listitem )
		self.getControl( STATUS ).setLabel( STR_SELECT_PROFILE )
		p.close()
	    	
	def onAction(self, action):
		if action.getId() in ACTION_CLOSE:
			self.close()
	
	def onClick( self, controlId ):
		if controlId == SETTINGS:
			__addon__.openSettings()
			self.update_servers()
		if controlId == SERVER_LIST:
			seekid = self.getControl( SERVER_LIST ).getSelectedItem().getProperty('id')
			if self.getControl( SERVER_LIST ).getSelectedItem().getProperty('stat') == STATUS_ON:
				import gui
				ui = gui.GUI( 'mpd-client-main.xml',__addon__.getAddonInfo('path'), self.skin,seekid)
				ui.doModal()
				del ui

skin = 'Confluence'
current_skin=str(xbmc.getSkinDir().lower())
#if current_skin.find('pm3') > -1:
#	skin = 'PM3.HD'
#if current_skin.find('transparency') > -1:
#	skin = 'transparency'
skip_selector = __addon__.getSetting('skip-selector')
if 'true' == skip_selector:
	import gui
	ui = gui.GUI( 'mpd-client-main.xml',__addon__.getAddonInfo('path'), skin,'0')
	ui.doModal()
	del ui
else:
	selectorUI = SelectMPDProfile( 'select-profile.xml',__addon__.getAddonInfo('path'), skin)
	selectorUI.profiles = [MpdProfile('0'),MpdProfile('1'),MpdProfile('2')]
	selectorUI.doModal()
	del selectorUI
sys.modules.clear()
