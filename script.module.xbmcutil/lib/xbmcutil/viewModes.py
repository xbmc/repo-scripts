"""
	###################### xbmcutil.viewModes ######################
	Copyright: (c) 2013 William Forde (willforde+kodi@gmail.com)
	License: GPLv3, see LICENSE for more details
	
	This file is part of xbmcutil
	
	xbmcutil is free software: you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation, either version 3 of the License, or
	(at your option) any later version.
	
	xbmcutil is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	GNU General Public License for more details.
	
	You should have received a copy of the GNU General Public License
	along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# Call Custom xbmcutil Module
from xbmcutil import plugin, storageDB

class Selector(object):
	# Fetch Current Skin ID
	skin = plugin.xbmc.getSkinDir()
	viewModes = {}
	
	# Main Initializer
	def __init__(self, mode):
		# Create List for display
		showList = [plugin.getstr(571)]
		self.mode = mode
		
		# Load in Skin Codes from Database
		jsonData = storageDB.SkinCodes()
		if self.skin in jsonData:
			# Fetch viewmodes for selected mode
			self.viewModes = self.filterCodes(jsonData[self.skin], mode)
			
			# Append each key of viewModes to show list
			for i in sorted(self.viewModes.keys()):
				showList.append(i)
		
		# Fetch Current Mode if set and Show to user under Custom Mode ID
		self.currentMode = currentMode = plugin.getSetting("%s.%s.view" % (self.skin, mode))
		if currentMode: showList.append("%s (%s)" % (plugin.getstr(636), currentMode))
		else: showList.append(plugin.getstr(636))
		
		# Display List
		self.display(showList)
	
	def filterCodes(self, skinCodes, mode):
		filterList = {}
		if mode in skinCodes: self.filterModes(filterList, skinCodes[mode])
		if "both" in skinCodes: self.filterModes(filterList, skinCodes["both"])
		return filterList
	
	def filterModes(self, filterd, modes):
		# Loop each view and assign to filterd list
		for view in modes:
			# Fetch Localized String
			key = plugin.getuni(view["id"]) if view["id"] is not None else ""
			# If strcomb exists then combine the localized tring to it
			if "strextra" in view: key = "%s %s" % (key, view["strextra"])
			# Assign Modes to Dict
			filterd[key.strip()] = view["mode"]
	
	def display(self, showList):
		# Bold the already selected view mode
		orgList = showList[:]
		if self.currentMode and len(showList) > 2:
			# Convert current viewmode to an interger
			currentMode = int(self.currentMode)
			for key, value in self.viewModes.iteritems():
				# Check if current mode is found in viewModes
				if currentMode == value:
					# When found find its position in the list
					for count, i in enumerate(showList):
						# Check for required key
						if key == i:
							# Wen found, Bold and Indent the value
							showList[count] = "[B]-%s[/B]" % showList[count]
							break
					break
		
		# Display List to User
		ret = plugin.dialogSelect(plugin.getAddonData(self.skin, "name"), showList)
		if ret >= 0:
			# Take action depending on response
			response = orgList[ret]
			if response.startswith(plugin.getstr(636)): self.askForViewID()
			elif response == plugin.getstr(571): plugin.setSetting("%s.%s.view" % (self.skin, self.mode), "")
			else: plugin.setSetting("%s.%s.view" % (self.skin, self.mode), str(self.viewModes[str(response)]))
	
	def askForViewID(self):
		# Display Numeric Dialog
		ret = plugin.dialogNumeric(0, plugin.getstr(611), self.currentMode)
		if ret: plugin.setSetting("%s.%s.view" % (self.skin, self.mode), str(ret))