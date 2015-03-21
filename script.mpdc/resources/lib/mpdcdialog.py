
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

LIST = 120
ACTION_CLOSE = [9,10]
STATUS = 100
SETTINGS = 101

class Dialog ( xbmcgui.WindowXMLDialog ) :
	
	def __init__(self,*args,**kwargs):
		super(xbmcgui.WindowXMLDialog, self).__init__('menu-dialog.xml',xbmcaddon.Addon('script.mpdc').getAddonInfo('path'),'Confluence','0')
		self.result = -1
		self.list = []
		self.title=''		
	
	def onFocus (self,controlId ):
		self.controlId = controlId
	
	def onInit (self ):
		self.getControl(STATUS).setLabel(self.title)		
		for item in self.list:
			litem = xbmcgui.ListItem(label=item)
			self.getControl(LIST).addItem(litem)	
			

	    	
	def onAction(self, action):
		if action.getId() in ACTION_CLOSE:
			self.result = -1
			self.close()		
	
	def onClick( self, controlId ):
		if controlId == LIST:
			self.result = self.getControl(LIST).getSelectedPosition()
			self.close()


