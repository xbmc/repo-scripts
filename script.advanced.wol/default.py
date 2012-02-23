# Wake-On-LAN

import socket, ping, os, sys
import xbmc, xbmcgui, xbmcaddon

def main():
	# Read Settings
	settings = xbmcaddon.Addon( id="script.advanced.wol" )
	language  = settings.getLocalizedString
	macAddress = settings.getSetting("macAddress")
	hostOrIp = settings.getSetting("hostOrIp")
	pingTimeout = int(settings.getSetting("pingTimeout"))
	enableNotifies = settings.getSetting("enableNotifies")
	enableVerificationNotifies = settings.getSetting("enableVerificationNotifies")
	continuousWol = settings.getSetting("continuousWol")
	continuousWolDelay = int(settings.getSetting("continuousWolDelay"))

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

	if ((launchcommand == True) & (delaycommand == False)):
		xbmc.executebuiltin(sys.argv[1])

	# Send WOL-Packet
	xbmc.executebuiltin('XBMC.WakeOnLan("'+macAddress+'")')
	print 'WakeOnLan signal sent to MAC-Address '+macAddress

	if (enableNotifies == "true"):

		# Send Connection Notification
		xbmc.executebuiltin('XBMC.Notification("'+language(60000).replace("%hostOrIp%",hostOrIp)+'","",5000,"'+iconConnect+'")')
		
		if (enableVerificationNotifies == "true"):

			# Check for Ping-Answer
			try:
				timecount = 1
				while timecount <= pingTimeout:
					delay = ping.do_one(hostOrIp, 1)
					if delay == None:
						xbmc.executebuiltin('XBMC.Notification("'+language(60001).replace("%hostOrIp%",hostOrIp)+'","'+language(60002).replace("%timecount%",str(timecount)).replace("%timeout%",str(pingTimeout))+'",5000,"'+iconConnect+'")')
						timecount = timecount+1
					else:
						break
				if delay == None:
					xbmc.sleep(1000)
					xbmc.executebuiltin('XBMC.Notification("'+language(60003).replace("%hostOrIp%",hostOrIp)+'","",5000,"'+iconError+'")')
				else:
					xbmc.sleep(1000)
					if ((launchcommand == True) & (delaycommand == True)):
						xbmc.executebuiltin('XBMC.Notification("'+language(60004).replace("%hostOrIp%",hostOrIp)+'","'+language(60007)+'",5000,"'+iconSuccess+'")')
						xbmc.sleep(1000)
						xbmc.executebuiltin(sys.argv[1])
					xbmc.executebuiltin('XBMC.Notification("'+language(60004).replace("%hostOrIp%",hostOrIp)+'","",5000,"'+iconSuccess+'")')
			except socket.error, (errno, msg):
				xbmc.sleep(1000)
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

	# Continue sending WOL-packets, if configured in the settings
	if (continuousWol == "true"):
		xbmc.sleep(5000)
		
		if (enableNotifies == "true"):
			# Send Connection Notification
			xbmc.executebuiltin('XBMC.Notification("'+language(60008).replace("%continuousWolDelay%",str(continuousWolDelay))+'","",5000,"'+iconSuccess+'")')
		count = 0
		while (not xbmc.abortRequested):
			xbmc.sleep(1000)
			if (count == continuousWolDelay):
				xbmc.executebuiltin('XBMC.WakeOnLan("'+macAddress+'")')
				print 'WakeOnLan signal sent to MAC-Address '+macAddress
				count = 0
			else:
				count+=1
	
	return
	
if __name__ == '__main__':
	main()