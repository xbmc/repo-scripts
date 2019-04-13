#!/usr/bin/python
# coding: utf-8

########################

import xbmc
import xbmcgui
import random

from resources.lib.helper import *
from resources.lib.kodi_monitor import KodiMonitor

########################

MONITOR = KodiMonitor()
KODIVERSION = get_kodiversion()

########################

log('Service started', force=True)

refresh_interval = 0
bg_task_interval = 200
bg_interval = 10
master_lock = 'None'
has_reloaded = False

while not MONITOR.abortRequested():

	# Workaround for login screen bug
	if not has_reloaded:
		if visible('System.HasLoginScreen + Skin.HasSetting(ReloadOnLogin)'):
			log('System has login screen enabled. Reload the skin to load all strings correctly.')
			execute('ReloadSkin()')
			has_reloaded = True

	# Master lock reload logic for widgets
	if visible('System.HasLocks'):

		if master_lock == 'None':
			master_lock = True if visible('System.IsMaster') else False
			log('Master mode: %s' % master_lock)

		if master_lock == True and not visible('System.IsMaster'):
			log('Left master mode. Reload skin.')
			master_lock = False
			execute('ReloadSkin()')

		elif master_lock == False and visible('System.IsMaster'):
			log('Entered master mode. Reload skin.')
			master_lock = True
			execute('ReloadSkin()')

	elif not master_lock == 'None':
		master_lock = 'None'

	# Grab fanarts
	if bg_task_interval >= 200:
		log('Start new fanart grabber process')
		fanarts = grabfanart()
		bg_task_interval = 0
	else:
		bg_task_interval += 10

	# Set fanart property
	if fanarts and bg_interval >=10:
		winprop('EmbuaryBackground', random.choice(fanarts))
		bg_interval = 0
	else:
		bg_interval += 10

	# Refresh widgets
	if refresh_interval >= 600:
		reload_widgets()
		refresh_interval = 0
	else:
		refresh_interval += 10

	MONITOR.waitForAbort(10)

del MONITOR

log('Service stopped', force=True)