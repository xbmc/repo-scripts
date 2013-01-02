XBMC Backup

About: 
I've had to recover my database, thumbnails, and source configuration enough times that I just wanted a quick easy way to back them up. That is what this addon is meant to do. 

Remote Destination/File Selection: 

In the addon settings you can define a remote path for the destination of your xbmc files. Each backup will create a folder named in a YYYYMMDD format so you can create multiple backups. You can keep a set number of backups by setting the integer value of the Backups to Keep setting greater than 0. 

On the Backup Selection page you can select which items from your user profile folder will be sent to the backup location. By default all are turned on except the Addon Data directory. 

Scheduling: 

You can also schedule backups to be completed on a set interval via the scheduling area. When it is time for the backup to run it will be executed in the background. 

When using the "Shutdown" function this will call XBMC's Shutdown method as defined in System Settings -> Power Saving -> Shutdown Function. This can be simply exiting xbmc, hibernating, or shutting down your htpc. 

Running the Program:

Running the program will allow you to select Backup or Restore as a running mode. Selecting Backup will push files to your remote store using the addon settings you defined. Selecting Restore will give you a list of restore points currently in your remote destination. Selecting one will pull the files matching your selection criteria from the restore point to your local XBMC folders. 


Using Dropbox:

Using Dropbox as a storage target adds a few steps the first time you wish to run a backup. First you will need to sign-up for you own developer app key and secret by visiting https://www.dropbox.com/developers. Name your app whatevery you want, and make it an "App Folder" type application. Your app can run in developer mode and you should never need to apply for production status. This is to get around Dropbox's rule not allow distribution of production key/secret pairs. 

Once you have your app key and secret add them to the settings. XBMC Backup now needs to have permission to access your Dropbox account. When you see the prompt regarding the Dropbox URL Authorization DO NOT click OK. Check your XBMC log file for a line from "script.xbmcbackup" containing the authorization URL. Cut/paste this into a browser and click Allow. Once this is done you can click "OK" in XBMC and proceed as normal. XBMC Backup will cache the authorization code so you only have to do this once, or if you revoke the Dropbox permissions. 

What this Addon Will Not Do:

This is not meant as an XBMC file sync solution. If you have multiple frontends you want to keep in sync this addon may work in a "poor man's" sort of way but it is not intended for that. 

This backup will not check the backup destination and delete files that do not match. It is best to only do one backup per day so that each folder is correct. 

