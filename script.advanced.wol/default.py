# Wake-On-LAN

import socket, ping, os, sys, time
import xbmc, xbmcgui, xbmcaddon

def main(isAutostart=False):
	
	print 'script.advanced.wol: Starting WOL script'
	
	####### Read Settings
	settings = xbmcaddon.Addon( id="script.advanced.wol" )
	language  = settings.getLocalizedString
	# basic settings
	macAddress = settings.getSetting("macAddress")
	hostOrIp = settings.getSetting("hostOrIp")	
	#notification settings
	enableLaunchNotifies = settings.getSetting("enableLaunchNotifies")
	enablePingCounterNotifies = settings.getSetting("enablePingCounterNotifies")
	enableHostupNotifies = settings.getSetting("enableHostupNotifies")
	enableErrorNotifies = settings.getSetting("enableErrorNotifies")
	#advanced settings
	pingTimeout = int(settings.getSetting("pingTimeout"))
	hostupWaitTime = int(settings.getSetting("hostupWaitTime"))
	disablePingHostupCheck = settings.getSetting("disablePingHostupCheck")	
	continuousWol = settings.getSetting("continuousWol")
	continuousWolDelay = int(settings.getSetting("continuousWolDelay"))
	continuousWolAfterStandby = settings.getSetting("continuousWolAfterStandby")
	updateVideoLibraryAfterWol = settings.getSetting("updateVideoLibraryAfterWol")
	updateMusicLibraryAfterWol = settings.getSetting("updateMusicLibraryAfterWol")
	libraryUpdatesDelay = int(settings.getSetting("libraryUpdatesDelay"))

	#if the scrpit was called with a 3rd parameter,
	#use the mac-address and host/ip from there
	try:
		if (len(sys.argv[3])>0):
			arrCustomServer = sys.argv[3].split('@')
			hostOrIp = arrCustomServer[0]
			macAddress = arrCustomServer[1]
	except:
		pass

	# Set Icons
	rootDir = settings.getAddonInfo('path')
	if rootDir[-1] == ';':rootDir = rootDir[0:-1]
	resDir = os.path.join(rootDir, 'resources')
	iconDir = os.path.join(resDir, 'icons')
	iconConnect = os.path.join(iconDir, 'server_connect.png')
	iconError = os.path.join(iconDir, 'server_error.png')
	iconSuccess = os.path.join(iconDir, 'server.png')

	launchcommand = False
	delaycommand = False
	try:
		if (len(sys.argv[1])>0):
			launchcommand = True
			if (str(sys.argv[2]) == str(True)):
				delaycommand = True
	except:
		pass

	# Launch additional command passed with parameters, if it should not be delayed to after successful wakeup
	if ((launchcommand == True) & (delaycommand == False)):
		xbmc.executebuiltin(sys.argv[1])

	# Send WOL-Packet
	xbmc.executebuiltin('XBMC.WakeOnLan("'+macAddress+'")')
	print 'script.advanced.wol: WakeOnLan signal sent to MAC-Address '+macAddress
	
	# Send Connection Notification
	if (enableLaunchNotifies == "true"):		
		xbmc.executebuiltin('XBMC.Notification("'+language(60000).replace("%hostOrIp%",hostOrIp)+'","",5000,"'+iconConnect+'")')
	
	# Determine wakeup-success
	hostupConfirmed = False
	if (disablePingHostupCheck == "true"):
		#with this setting, we just wait for "hostupWaitTime" seconds and assume a successful wakeup then.
		timecount = 1
		while timecount <= hostupWaitTime:
			xbmc.sleep(1000)
			if (enablePingCounterNotifies == "true"):
				xbmc.executebuiltin('XBMC.Notification("'+language(60001).replace("%hostOrIp%",hostOrIp)+'","'+language(60002).replace("%timecount%",str(timecount)).replace("%timeout%",str(hostupWaitTime))+'",5000,"'+iconConnect+'")')
			timecount = timecount+1
		if (enableHostupNotifies == "true"):
			xbmc.executebuiltin('XBMC.Notification("'+language(60011).replace("%hostOrIp%",hostOrIp)+'","",5000,"'+iconSuccess+'")')
		hostupConfirmed = True
	else:
		#otherwise we determine the success by pinging (default behaviour)
		try:
			timecount = 1
			while timecount <= pingTimeout:
				delay = ping.do_one(hostOrIp, 1)
				if delay == None:
					if (enablePingCounterNotifies == "true"):
						xbmc.executebuiltin('XBMC.Notification("'+language(60001).replace("%hostOrIp%",hostOrIp)+'","'+language(60002).replace("%timecount%",str(timecount)).replace("%timeout%",str(pingTimeout))+'",5000,"'+iconConnect+'")')
					timecount = timecount+1
				else:
					break
			if delay == None:
				xbmc.sleep(1000)
				if (enableHostupNotifies == "true"):
					xbmc.executebuiltin('XBMC.Notification("'+language(60003).replace("%hostOrIp%",hostOrIp)+'","",5000,"'+iconError+'")')
			else:
				xbmc.sleep(1000)
				if (enableHostupNotifies == "true"):
					xbmc.executebuiltin('XBMC.Notification("'+language(60004).replace("%hostOrIp%",hostOrIp)+'","",5000,"'+iconSuccess+'")')
				hostupConfirmed = True
				
		except socket.error, (errno, msg):
			xbmc.sleep(1000)
			print 'script.advanced.wol: Error No.: '+str(errno)+' / Error Msg.: '+msg.decode("utf-8","ignore")
			if (enablePingCounterNotifies == "true"):
				if errno == 11004:
					xbmc.executebuiltin('XBMC.Notification("'+language(60005)+'","'+language(60006).replace("%hostOrIp%",hostOrIp)+'",10000,"'+iconError+'")')
				elif errno == 10013:
					if sys.platform == 'win32':
						xbmc.executebuiltin('XBMC.Notification("'+language(60005)+'","'+language(60009)+'",20000,"'+iconError+'")')			
				elif errno == 1:
					if sys.platform == 'linux2':
						xbmc.executebuiltin('XBMC.Notification("'+language(60005)+'","'+language(60010)+'",20000,"'+iconError+'")')		
				else:
					xbmc.executebuiltin('XBMC.Notification("'+language(60005)+'","'+msg.decode("utf-8","ignore")+'",20000,"'+iconError+'")')
	
	# Things to perform after successful wake-up
	if (hostupConfirmed == True):
	
		# Launch additional command passed with parameters, if it should be delayed to after successful wakeup
		if ((launchcommand == True) & (delaycommand == True)):
			if (enableHostupNotifies == "true"):
				xbmc.executebuiltin('XBMC.Notification("'+language(60004).replace("%hostOrIp%",hostOrIp)+'","'+language(60007)+'",5000,"'+iconSuccess+'")')
			xbmc.sleep(1000)
			xbmc.executebuiltin(sys.argv[1])
			
		# Initiate XBMC-library-updates, if we are in autostart and it is set in the settings.
		if (isAutostart == True):
		
			if (((updateVideoLibraryAfterWol == "true") or (updateMusicLibraryAfterWol == "true")) and (libraryUpdatesDelay > 0)):
				xbmc.sleep(libraryUpdatesDelay*1000)
		
			if (updateVideoLibraryAfterWol == "true"):
				print 'script.advanced.wol: Initiating Video Library Update'
				xbmc.executebuiltin('UpdateLibrary("video")')
				
			if (updateMusicLibraryAfterWol == "true"):
				print 'script.advanced.wol: Initiating Music Library Update'
				xbmc.executebuiltin('UpdateLibrary("music")')
		

	# Continue sending WOL-packets, if configured in the settings
	if (continuousWol == "true"):
		xbmc.sleep(5000)
		
		if (enableLaunchNotifies == "true"):
			# Send Notification regarding continuous WOL-packets
			xbmc.executebuiltin('XBMC.Notification("'+language(53020)+'","'+language(60008).replace("%continuousWolDelay%",str(continuousWolDelay))+'",5000,"'+iconSuccess+'")')
		
		# the previousTime-functionality to stop continuous WOL-packets after XBMC returns from standby was suggested by XBMC-forum-user "jandias" (THANKS!)
		previousTime = time.time()
		countingSeconds = 0
		while (not xbmc.abortRequested):
			if ((continuousWolAfterStandby == "false") and ( time.time()-previousTime > 5)):
				break
			else:
				previousTime = time.time()
				xbmc.sleep(1000)
				if (countingSeconds == continuousWolDelay):
					xbmc.executebuiltin('XBMC.WakeOnLan("'+macAddress+'")')
					print 'script.advanced.wol: WakeOnLan signal sent to MAC-Address '+macAddress
					countingSeconds = 0
				else:
					countingSeconds+=1	

	print 'script.advanced.wol: Closing WOL script'
	return
	
if __name__ == '__main__':
	main()