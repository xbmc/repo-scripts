#!/usr/bin/python
# coding: utf-8

########################

import xbmc
import xbmcgui
import time
import random

from resources.lib.helper import *
from resources.lib.kodi_monitor import KodiMonitor

########################

MONITOR = KodiMonitor()
KODIVERSION = get_kodiversion()

########################

log('Service started', force=True)

task_interval = 300
cache_interval = 150
bg_task_interval = 200
bg_interval = 10
master_lock = 'None'
has_reloaded = False

while not MONITOR.abortRequested():

	# Get audio tracks for < Leia
	if KODIVERSION < 18 and PLAYER.isPlayingVideo():
		MONITOR.get_audiotracks()

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
		random.shuffle(fanarts)
		winprop('EmbuaryBackground', fanarts[0])
		bg_interval = 0
	else:
		bg_interval += 10

	# Refresh widgets
	if task_interval >= 300:
		log('Update widget reload property')
		winprop('EmbuaryWidgetUpdate', time.strftime('%Y%m%d%H%M%S', time.gmtime()))
		task_interval = 0
	else:
		task_interval += 10

	# Refresh cache
	if cache_interval >= 150:
		log('Update cache reload property')
		winprop('EmbuaryCacheTime', time.strftime('%Y%m%d%H%M%S', time.gmtime()))
		cache_interval = 0
	else:
		cache_interval += 10

	MONITOR.waitForAbort(10)

del MONITOR

log('Service stopped', force=True)