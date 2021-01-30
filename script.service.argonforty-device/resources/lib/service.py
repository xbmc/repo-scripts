# -*- coding: utf-8 -*-

#from resources.lib import kodiutils
#from resources.lib import kodilogging
#import logging
import time
import xbmc
import xbmcaddon

from threading import Thread
from resources.lib import argon


def thread_powerbutton():
	argon.shutdown_check()


def thread_fan():
	argon.temp_check()


def run():
	ADDON = xbmcaddon.Addon()
	#logger = logging.getLogger(ADDON.getAddonInfo('id'))

	#monitor = xbmc.Monitor()
	monitor = argon.SettingMonitor()

	t1 = Thread(target = thread_fan)
	t1.start()

	powerbutton = ADDON.getSettingBool('powerbutton')
	if powerbutton == True:
		t2 = Thread(target = thread_powerbutton)
		t2.start()

	while not monitor.abortRequested():
		# Sleep/wait for abort for 10 seconds
		if monitor.waitForAbort(10):
			# Abort was requested while waiting. We should exit
			break
		#logger.debug("ArgonForty Device addon! %s" % time.time())

	argon.cleanup()

