#!/usr/bin/python
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

''' A script to clone the front end of LazyTV install to allow multiple Home menu items with different settings '''

import os
import xbmc
import xbmcaddon
import xbmcgui
import sys
import string
import shutil
import time
import traceback
import re
from xml.etree import ElementTree as et
import fileinput


__addon__        = xbmcaddon.Addon('script.lazytv')
__addonid__      = __addon__.getAddonInfo('id')
__setting__      = __addon__.getSetting
dialog           = xbmcgui.Dialog()
scriptPath       = __addon__.getAddonInfo('path')
addon_path       = xbmc.translatePath('special://home/addons')
keep_logs        = True if __setting__('logging') == 'true' else False

start_time       = time.time()
base_time        = time.time()

def lang(id):
	san = __addon__.getLocalizedString(id).encode( 'utf-8', 'ignore' )
	return san 

def sanitize_strings(dirtystring):

	dirtystring.strip()
	valid_chars = "-_.()%s%s " % (string.ascii_letters, string.digits)
	san_name = ''.join(c for c in dirtystring if c in valid_chars)
	san_name = san_name.replace(' ','_').lower()
	return san_name


def log(message, label = '', reset = False):
	if keep_logs:
		global start_time
		global base_time
		new_time     = time.time()
		gap_time     = "%5f" % (new_time - start_time)
		start_time   = new_time
		total_gap    = "%5f" % (new_time - base_time)
		logmsg       = '%s : %s :: %s ::: %s - %s ' % (__addonid__, total_gap, gap_time, label, message)
		xbmc.log(msg = logmsg)
		base_time    = start_time if reset else base_time


def errorHandle(exception, trace, new_path=False):

		log('An error occurred while creating the clone.')
		log(str(exception))
		log(str(trace))

		dialog.ok('LazyTV', lang(32140),lang(32141))
		if new_path:
			shutil.rmtree(new_path, ignore_errors=True)
		sys.exit()


def Main():
	first_q = dialog.yesno('LazyTV',lang(32142),lang(32143),lang(32144))
	if first_q != 1:
		sys.exit()
	else:
		keyboard = xbmc.Keyboard(lang(32139))
		keyboard.doModal()
		if (keyboard.isConfirmed()):
			clone_name = keyboard.getText()
		else:
			sys.exit()

	# if the clone_name is blank then use default name of 'Clone'
	if not clone_name:
		clone_name = 'Clone'

	san_name = 'script.lazytv.' + sanitize_strings(clone_name)
	new_path = os.path.join(addon_path, san_name)

	log('clone_name = ' + str(clone_name))
	log('san_name = ' + str(san_name))
	log('new_path = ' + str(new_path))
	log('script path = ' + str(scriptPath))

	#check if folder exists, if it does then abort
	if os.path.isdir(new_path):

		log('That name is in use. Please try another')

		dialog.ok('LazyTV',lang(32145))
		__addon__.openSettings()
		sys.exit()

	try:

		# copy current addon to new location
		IGNORE_PATTERNS = ('.pyc','CVS','.git','tmp','.svn')
		shutil.copytree(scriptPath,new_path, ignore=shutil.ignore_patterns(*IGNORE_PATTERNS))


		# remove the unneeded files
		addon_file = os.path.join(new_path,'addon.xml')

		os.remove(os.path.join(new_path,'service.py'))
		os.remove(addon_file)
		#os.remove(os.path.join(new_path,'resources','selector.py'))
		os.remove(os.path.join(new_path,'resources','settings.xml'))
		os.remove(os.path.join(new_path,'resources','clone.py'))

		# replace the settings file and addon file with the truncated one
		shutil.move( os.path.join(new_path,'resources','addon_clone.xml') , addon_file )
		shutil.move( os.path.join(new_path,'resources','settings_clone.xml') , os.path.join(new_path,'resources','settings.xml') )

	except Exception as e:
		ex_type, ex, tb = sys.exc_info()
		errorHandle(e, tb, new_path)

	# edit the addon.xml to point to the right folder
	tree = et.parse(addon_file)
	root = tree.getroot()
	root.set('id', san_name)
	root.set('name', clone_name)
	tree.find('.//summary').text = clone_name
	tree.write(addon_file)

	# replace the id on these files, avoids Access Violation
	py_files = [os.path.join(new_path,'resources','selector.py') , os.path.join(new_path,'resources','playlists.py'),os.path.join(new_path,'resources','update_clone.py'),os.path.join(new_path,'resources','episode_exporter.py')]

	for py in py_files:
		for line in fileinput.input(py, inplace = 1): # Does a list of files, and writes redirects STDOUT to the file in question
			print line.replace('script.lazytv',san_name),

	# stop and start the addon to have it show in the Video Addons window
	try:
		xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":1,"params":{"addonid":"%s","enabled":false}}' % san_name)
		xbmc.sleep(1000)
		xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Addons.SetAddonEnabled","id":1,"params":{"addonid":"%s", "enabled":true}}' % san_name)
	except:
		pass

	dialog.ok('LazyTV', lang(32146),lang(32147))


if __name__ == "__main__":

	log('Cloning started')

	Main()

	log('Cloning complete')
