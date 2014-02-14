XBMC Backup


About: 
I've had to recover my database, thumbnails, and source configuration enough times that I just wanted a quick easy way to back them up. That is what this addon is meant to do. 

Remote Destination/File Selection: 

In the addon settings you can define a remote path for the destination of your xbmc files. Each backup will create a folder named in a YYYYMMDD format so you can create multiple backups. You can keep a set number of backups by setting the integer value of the Backups to Keep setting greater than 0. 

On the Backup Selection page you can select which items from your user profile folder will be sent to the backup location. By default all are turned on except the Addon Data directory. 

You can also define non-XBMC directories on your device. See "Custom Directories" for more information on how these are handled. 

Scheduling: 

You can schedule backups to be completed on a set interval via the scheduling area. When it is time for the backup to run it will be executed in the background. 

When using the "Shutdown" function this will call XBMC's Shutdown method as defined in System Settings -> Power Saving -> Shutdown Function. This can be simply exiting xbmc, hibernating, or shutting down your htpc. 

Running the Program:

Running the program will allow you to select Backup or Restore as a running mode. Selecting Backup will push files to your remote store using the addon settings you defined. Selecting Restore will give you a list of restore points currently in your remote destination. Selecting one will pull the files matching your selection criteria from the restore point to your local XBMC folders. 

Custom Directories: 

You can define custom directories that are not a part of your XBMC folder structure for backup. These create a custom_hash folder in your backup destination. The hash for these folders is very important. During a restore if the hash of the file path in Custom 1 does not match the hash in the restore folder it will not move the files. This is to prevent files from being restored to the wrong location in the event you change file paths in the addon settings. A dialog box will let you know if file paths do not match up. 

Up to 2 Custom directories can be specified. 

Using Dropbox:

Using Dropbox as a storage target adds a few steps the first time you wish to run a backup. First you will need to sign-up for you own developer app key and secret by visiting https://www.dropbox.com/developers. Name your app whatevery you want, and make it an "App Folder" type application. Your app can run in developer mode and you should never need to apply for production status. This is to get around Dropbox's rule not allow distribution of production key/secret pairs. 

Once you have your app key and secret add them to the settings. XBMC Backup now needs to have permission to access your Dropbox account. When you see the prompt regarding the Dropbox URL Authorization DO NOT click OK. Check your XBMC log file for a line from "script.xbmcbackup" containing the authorization URL. Cut/paste this into a browser and click Allow. Once this is done you can click "OK" in XBMC and proceed as normal. XBMC Backup will cache the authorization code so you only have to do this once, or if you revoke the Dropbox permissions. 


Scripting XBMC Backup: 

If you wish to script this addon using an outside scheduler or script it can be given parameters via the Xbmc.RunScript() or JsonRPC.Addons.ExecuteAddon() methods. Parameters given are either "backup" or "restore" to launch the correct program mode. An example would be: 

RunScript(script.xbmcbackup,backup)


FAQ: 

I can't see any restore points when choosing "Restore", what is the problem? 

If you've created restore points with an older version of the addon (pre 0.3.6) you may see this issue. New versions of the addon look for a file called xbmcbackup.val to validate that a folder is a valid restore archive. Your older restore folders may not have this file. All you need to do is create a blank text file and rename it to xbmcbackup.val. Then put this file inside the archive directory. Your restore points should show up after selecting "Restore" in the addon again. 

Several settings aren't being restored, this includes views, weather, etc. How do I get these back? 

GUISETTINGS.xml is a configuration file used heavily by XBMC for remembering GUI specific settings. Due to the fact that XBMC reads this file on startup, and writes from memory to this file on shutdown; it is not possible to restore this file while XBMC is running. You must manually move this file from your backup archives if you wish to restore it. User SouthMark has posted the following steps for restoring in the OpenELEC system where this is more difficult: 

1. Run the restore of your backup
2. SSH using putty to the IP Address of your media centre username: root Password openelec
3. Type touch /var/lock/xbmc.disabled and then press enter
4. Type kill all -9 xbmc.bin and then press enter - Your media center machine should now go blank
5. Connect to your machine using WinSCP and copy the guisettings.xml file to the userdata folder (this is the guisettings.xml file from your backup)
6. go back to your putty window and type rm /var/lock/xbmc.disabled

Why is the Addon prompting me to restart XBMC to continue? 

If you have an advancedsettings file in your restore folder the addon will ask you if you want to restore this file and restart xbmc to continue. This is because the advancedsettings file may contain path substitution information that you want to be loaded when doing the rest of your restore. By restoring this file and restarting xbmc it will be loaded and the rest of your files will go where they are supposed to. If you know your file does not contain any path substitutions you can select "no" and continue as normal. 

