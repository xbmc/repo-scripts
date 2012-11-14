from resources.lib.backup import XbmcBackup

#run the profile backup
backup = XbmcBackup()

if(backup.isReady()):
    backup.run()
