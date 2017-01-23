#Backup Addon

##About
I've had to recover my database, thumbnails, and source configuration enough times that I just wanted a quick easy way to back them up. That is what this addon is meant to do. 

##Configuration

In the addon settings you can define a remote path for the destination of your Kodi files. Each backup will create a folder named in a YYYYMMDDHHmm format so you can create multiple backups. You can keep a set number of backups by setting the integer value of the Backups to Keep setting greater than 0. 

If you choose to compress your backups there are a few things you need to be aware of. Compressing takes place on the server you are trying to backup and then only the archive is copied to the remote backup location. This means you must have sufficient space available to allow for creating the archive. When restoring a zipped archive the process is the same. It is first copied to your local storage, extracted, and the contents put to their correct locations. The archive is then deleted. Zipped and non-zipped backups can be mixed in the same archive folder.  

On the Backup Selection page you can select which items from your user profile folder will be sent to the backup location. By default all are turned on except the Addon Data directory. 

You can also define non-Kodi directories on your device. See "Custom Directories" for more information on how these are handled. 

###File Selection Options

Here is a breakdown of the file selection options available in the settings. More information about Kodi file paths can be found on [the wiki](http://kodi.wiki/view/Special_protocol)

* User Addons - these are all the addon files located in the main Kodi addons folder. The path is special://home/addons
* Addon Data - this is data saved by addons when changing their settings. The path is special://home/userdata/addon_data
* Database - these are the local Kodi SQLlite databases. Even if using the SQL database there are other DB files such as Addons.db that you would want in this folder. The path is special://home/userdata/Database
* Playlist - Playlists that are created in Kodi. The path is special://home/userdata/playlists
* Profiles - Any files in the profiles folder. Keep in mind this currently includes all database, thumnail and config files in here. The path is special://home/userdata/profiles
* Thumbnails/Fanart - the folder where all thumbnails and fanart is stored. The path is special://home/userdata/Thumbnails
* Config Files - config files refer to a collection of files that Kodi uses for information. This includes the keymaps and peripheral_data, and library directories in the userdata folder. It also includes all the XML files in the root of the userdata directory such as sources.xml, guisettings.xml, favorites.xml, advancedsettings.xml and others. For a full list of files in this directory see the [UserData folder wiki page](http://kodi.wiki/view/The_UserData_Folder)

###Custom Directories

You can define custom directories that are not a part of your Kodi folder structure for backup. These create a "custom_hash" folder in your backup destination. The hash for these folders is very important. During a restore if the hash of the file path in Custom 1 does not match the hash in the restore folder it will not move the files. This is to prevent files from being restored to the wrong location in the event you change file paths in the addon settings. A dialog box will let you know if file paths do not match up. 

Up to 2 Custom directories can be specified. 

##Running the Program

Running the program will allow you to select Backup or Restore as a running mode. Selecting Backup will push files to your remote store using the addon settings you defined. Selecting Restore will give you a list of restore points currently in your remote destination. Selecting one will pull the files matching your selection criteria from the restore point to your local Kodi folders. 

###Restores

During the restore process there are a few checks and post-run procedures to know about. 

The first is a version check. If you are restoring to a different version of Kodi than the one used to create the backup archive you'll get a warning. In most cases it is OK to proceed, just know that some specific items like addons and database files may not work correctly.

The next check is for an advancedsettings.xml file. If you've created this file and it exists in your restore archive you'll be asked to reboot Kodi. This is so that the file can be loaded and used for any special settings, mainly path substitutions, you may have had that would affect the rest of the restore. The Backup addon will prompt you to continue the restore process when you reboot the program. 

The last bit of post-processing is done after all the backup files have been restored. If you have restored your configuration files the addon will attempt to restore any system specific settings that it can from the guisettings.xml file. This is done by comparing the restored file with settings via the JSONPRC Settings.SetSettingValue method. Only system specific settings can be restored so you will get any custom views or skin specific settings back. See the FAQ for how to restore these.  

##Scheduling 

You can schedule backups to be completed on a set interval via the scheduling area. When it is time for the backup to run it will be executed in the background. 

When using the "Shutdown" function this will call Kodi's Shutdown method as defined in System Settings -> Power Saving -> Shutdown Function. This can be simply exiting Kodi, hibernating, or shutting down your htpc. 

##Using Dropbox

Using Dropbox as a storage target adds a few steps the first time you wish to run a backup. First you will need to sign-up for you own developer app key and secret by visiting https://www.dropbox.com/developers. Name your app whatever you want, and make it an "App Folder" type application. Your app can run in developer mode and you should never need to apply for production status. This is to get around Dropbox's rule not allow distribution of production key/secret pairs. 

Once you have your app key and secret add them to the settings. Kodi Backup now needs to have permission to access your Dropbox account. When you see the prompt regarding the Dropbox URL Authorization DO NOT click OK. Check your Kodi log file for a line from "script.xbmcbackup" containing the authorization URL. Cut/paste this into a browser and click Allow. Once this is done you can click "OK" in Kodi and proceed as normal. Kodi Backup will cache the authorization code so you only have to do this once, or if you revoke the Dropbox permissions. 

##Using Google Drive

Using the Google Drive target is very similar to the Dropbox one. You must create a Google API project and authenticate your account via the id and secret. Instructions for enable the Google API for Google Drive can be found here (https://developers.google.com/drive/web/quickstart/quickstart-python). You'll need the client id and client secret generated for the addon settings. You only need to follow Step 1. 

Once you have the client ID and Secret add them to the addon settings and run a backup. You'll get a notification that you need to enter your authorization code. Check your Kodi log file for a line from "script.xbmcbackup" containing the authorization URL. Cut/paste this into a browser and click Allow. Once this is done put the code from your browser into the pop-up dialog. The addon will cache these credentials so it should be a one-time authentication. From there the backup should start to run. 

##Scripting A Backup 

If you wish to script this addon using an outside scheduler or script it can be given parameters via the xbmc.RunScript() or JsonRPC.Addons.ExecuteAddon() methods. Parameters given are either "backup" or "restore" to launch the correct program mode. If mode is "restore", an additional "archive" parameter can be given to set the restore point to be used instead of prompting via the GUI. An example would be: 

Python code: 
```python
RunScript(script.xbmcbackup,mode=backup)
```

JSON Request: 
```
{ "jsonrpc": "2.0", "method": "Addons.ExecuteAddon","params":{"addonid":"script.xbmcbackup","params":{"mode":"restore","archive":"000000000000"}}, "id": 1 }
```

There is also a windows parameter that can be used to check if Kodi Backup is running within a skin or from another program. It is attached to the home window, an example of using it would be the following: 

```python
#kick off the Kodi backup
xbmc.executeJSONRPC('{ "jsonrpc": "2.0", "method": "Addons.ExecuteAddon","params":{"addonid":"script.xbmcbackup","params":{"mode":"backup"}}, "id": 1 }')

#sleep for a few seconds to give it time to kick off
xbmc.sleep(10000)

window = xbmcgui.Window(10000)

while (window.getProperty('script.xbmcbackup.running') == 'true'):
     #do something here, probably just sleep for a few seconds
     xbmc.sleep(5000)

#backup is now done, continue with script
```

##FAQ

1. I can't see any restore points when choosing "Restore", what is the problem? 

	If you've created restore points with an older version of the addon (pre 0.3.6) you may see this issue. New versions of the addon look for a file called xbmcbackup.val to validate that a folder is a valid restore archive. Your older restore folders may not have this file. All you need to do is create a blank text file and rename it to xbmcbackup.val. Then put this file inside the archive directory. Your restore points should show up after selecting "Restore" in the addon again.

	Several settings aren't being restored, this includes views, weather, etc. How do I get these back?

	GUISETTINGS.xml is a configuration file used heavily by Kodi for remembering GUI specific settings. Due to the fact that Kodi reads this file on startup, and writes from memory to this file on shutdown; it is not possible to restore this file while Kodi is running. This addon attempts to restore what settings it can via the JSONRPC interface, however you will still most likely be missing your specific skin settings and view settings. To get these back you must manually move this file from your backup archives if you wish to restore it. User SouthMark has posted the following steps for restoring in the OpenELEC system where this is more difficult:

	1. Run the restore of your backup
	2. SSH using putty to the IP Address of your media centre username: root Password openelec
	3. Type "systemctl stop xbmc.service" - Your media center machine should now go blank
	5. Connect to your machine using WinSCP and copy the guisettings.xml file to the userdata folder (this is the guisettings.xml file from your backup), alternatively you can copy this file directly to an SMB share and use putty to move it to the right spot. 
	6. go back to your putty window and type "systemctl start xbmc.service"

2. Why is the Addon prompting me to restart Kodi to continue? 

	If you have an advancedsettings file in your restore folder the addon will ask you if you want to restore this file and restart Kodi to continue. This is because the advancedsettings file may contain path substitution information that you want to be loaded when doing the rest of your restore. By restoring this file and restarting Kodi it will be loaded and the rest of your files will go where they are supposed to. If you know your file does not contain any path substitutions you can select "no" and continue as normal.
