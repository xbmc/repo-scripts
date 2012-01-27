# Wake-On-LAN

import socket, ping, os
import xbmc, xbmcgui, xbmcaddon

# Read Settings
settings = xbmcaddon.Addon( id="script.advanced.wol" )
language  = settings.getLocalizedString
mac_address = settings.getSetting("macaddress")
hostorip = settings.getSetting("hostorip")
timeout = int(settings.getSetting("timeout"))

#if the scrpit was called with a 3rd parameter,
#use the mac-address and host/ip from there
try:
	if (len(sys.argv[3])>0):
		arrCustomServer = sys.argv[3].split('@')
		hostorip = arrCustomServer[0]
		mac_address = arrCustomServer[1]
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

# Send Connection Notification
xbmc.executebuiltin('XBMC.Notification("'+language(60000).replace("%hostorip%",hostorip)+'","",5000,"'+iconConnect+'")')

# Send WOL-Packet
xbmc.executebuiltin('XBMC.WakeOnLan("'+mac_address+'")')

# Check for Ping-Answer
try:
	timecount = 1
	while timecount <= timeout:
		delay = ping.do_one(hostorip, 1)
		if delay == None:
			xbmc.executebuiltin('XBMC.Notification("'+language(60001).replace("%hostorip%",hostorip)+'","'+language(60002).replace("%timecount%",str(timecount)).replace("%timeout%",str(timeout))+'",5000,"'+iconConnect+'")')
			timecount = timecount+1
		else:
			break
	if delay == None:
		xbmc.sleep(1000)
		xbmc.executebuiltin('XBMC.Notification("'+language(60003).replace("%hostorip%",hostorip)+'","",5000,"'+iconError+'")')
	else:
		xbmc.sleep(1000)
		if ((launchcommand == True) & (delaycommand == True)):
			xbmc.executebuiltin('XBMC.Notification("'+language(60004).replace("%hostorip%",hostorip)+'","'+language(60007)+'",5000,"'+iconSuccess+'")')
			xbmc.sleep(1000)
			xbmc.executebuiltin(sys.argv[1])
		xbmc.executebuiltin('XBMC.Notification("'+language(60004).replace("%hostorip%",hostorip)+'","",5000,"'+iconSuccess+'")')
except socket.error, (errno, msg):
	xbmc.sleep(1000)
	if errno == 11004:
		xbmc.executebuiltin('XBMC.Notification("'+language(60005)+'","'+language(60006).replace("%hostorip%",hostorip)+'",5000,"'+iconError+'")')
	else:
		xbmc.executebuiltin('XBMC.Notification("'+language(60005)+'","'+msg+'",5000,"'+iconError+'")')
