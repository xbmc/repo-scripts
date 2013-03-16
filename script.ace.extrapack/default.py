import xbmc, xbmcaddon
import os, re, sys, time, signal, threading
from updater_class import *

SCRIPTID = "script.ace.updater"
ADDONNAME = "Ace"
TARGETID = "skin.ace.extrapack"

if ( __name__ == "__main__" ):
	
	xbmc.log('start ace updater')
		
	updater = Updater()
	
	updater.SFAddress = "http://mod-skin.googlecode.com/svn/trunk/skin.ace.extrapack/"
	updater.SFViewVC = ""
	updater.SVNPathAddress = updater.SFAddress + updater.SFViewVC
		
	xbmc.log('target url  = ' +str(updater.SVNPathAddress))
	
	addonDataPath = xbmc.translatePath('special://profile/addon_data/')	
	addonBasePath = os.path.join(addonDataPath, SCRIPTID)
			
	__language__ = xbmc.getLocalizedString
	
	updater.BackupBasePath = os.path.join(addonBasePath, "backup")
	updater.UpdateTempDir = os.path.join(addonBasePath, "updates")
	updater.UpdateTargetPath = os.path.join(addonDataPath, TARGETID)
	
	executionmode = 'mode=default'
	
	try:	
		executionmode = sys.argv[1]
		xbmc.log("executionmode: " +str(executionmode))
	except:
		xbmc.log("Error reading launch parameters. Will run in default mode")
	
	revisionPath = os.path.join(addonBasePath,"revision.xml")
	if(os.path.exists(revisionPath)):
		updater.CurrentRevision = int(re.findall("<revision>([^<]*)</revision>",open(revisionPath,"r").read())[0])
	else:
		updater.CurrentRevision = 0
	
	xbmc.log('current revision = ' +str(updater.CurrentRevision))
	updater.Language(__language__)
	
	HasUpdate = 1
	if(executionmode == 'mode=forcerefresh'):
		xbmc.log("Force update of all files")
		updater.CleanDirectory(updater.UpdateTargetPath)
		updater.HeadRevision = int(re.findall("mod-skin - Revision ([0-9]+):",urllib2.urlopen(updater.SVNPathAddress).read())[0])
		updater.MakeDirectories()
		HasUpdate = 1
	else:
		HasUpdate = updater.HasUpdate()	
		
	xbmc.log('result HasUpdate = ' +str(HasUpdate))

	if HasUpdate:
		
		UpdateStatus = UpdaterThread(updater)
		UpdateStatus.start()
		UpdateStatus.join()
			
		if UpdateStatus.status == 1:
			new_revision = "<version>\r\n\t<revision>"+str(updater.HeadRevision)+"</revision>\r\n</version>"
			f = open(revisionPath,"w").write(new_revision)
			xbmc.executebuiltin("Notification(%s,%s,5000])"%(ADDONNAME.encode('utf-8'), __language__(31971).encode('utf-8')))
		else:
			xbmc.executebuiltin("Notification(%s,%s,5000])"%(ADDONNAME.encode('utf-8'), __language__(31972).encode('utf-8') ))
	else:
		xbmc.executebuiltin("Notification(%s,%s,5000])"%(ADDONNAME.encode('utf-8'), __language__(31973).encode('utf-8') ))
	
	xbmc.log('Update finished')
