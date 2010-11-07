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
Addon = xbmcaddon.Addon(id=os.path.basename(os.getcwd()))

__settings__ = xbmcaddon.Addon(id=os.path.basename(os.getcwd()))

__language__ = __settings__.getLocalizedString

SERVER_LIST = 120
ACTION_CLOSE = [10]
STATUS = 100
SETTINGS = 101
sys.path.append( os.path.join ( os.getcwd(), 'resources','lib') )
import gui,mpd,dialog

STATUS_ON='on'
STATUS_OFF='off'
STR_CONNECTING=Addon.getLocalizedString(30007)
STR_CONNECTING_TITLE=Addon.getLocalizedString(30015) 
STR_SELECT_PROFILE=Addon.getLocalizedString(30008)
STR_HOST_ONLINE=Addon.getLocalizedString(30009)
STR_HOST_OFFLINE=Addon.getLocalizedString(30010)
class MpdProfile:
	
	def __init__(self,profile_id):
		self.id=profile_id
		self.addon = xbmcaddon.Addon(id=os.path.basename(os.getcwd()))
		self.name = self.addon.getSetting(self.id+'_name')
		self.host = self.addon.getSetting(self.id+'_mpd_host')	
		self.port = self.addon.getSetting(self.id+'_mpd_port')
		self.stream_url = self.addon.getSetting(self.id+'_stream_url')
		self.password = self.addon.getSetting(self.id+'_mpd_pass')
		self.status = STR_HOST_OFFLINE
		self.stat = STATUS_OFF

	def update(self):
		self.name = self.addon.getSetting(self.id+'_name')
		self.host = self.addon.getSetting(self.id+'_mpd_host')	
		self.port = self.addon.getSetting(self.id+'_mpd_port')
		self.stream_url = self.addon.getSetting(self.id+'_stream_url')
		self.password = self.addon.getSetting(self.id+'_mpd_pass')
		self.status = STR_HOST_OFFLINE
		self.stat=STATUS_OFF
		try:
			client = mpd.MPDClient()
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
			Addon.openSettings()
			self.update_servers()
		if controlId == SERVER_LIST:
			seekid = self.getControl( SERVER_LIST ).getSelectedItem().getProperty('id')
			if self.getControl( SERVER_LIST ).getSelectedItem().getProperty('stat') == STATUS_ON:
				ui = gui.GUI( 'mpd-client-main.xml',os.getcwd(), self.skin,seekid)
				ui.doModal()
				del ui

skin = 'Confluence'
current_skin=str(xbmc.getSkinDir().lower())
if current_skin.find('pm3') > -1:
	skin = 'PM3.HD'
if current_skin.find('transparency') > -1:
	skin = 'transparency'
skip_selector = Addon.getSetting('skip-selector')
if 'true' == skip_selector:
	ui = gui.GUI( 'mpd-client-main.xml',os.getcwd(), skin,'0')
	ui.doModal()
	del ui
else:
	selectorUI = SelectMPDProfile( 'select-profile.xml',os.getcwd(), skin)		
	selectorUI.profiles = [MpdProfile('0'),MpdProfile('1'),MpdProfile('2')]
	selectorUI.doModal()
	del selectorUI
sys.modules.clear()
