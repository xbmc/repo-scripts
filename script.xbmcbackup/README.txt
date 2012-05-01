XBMC Backup

About: 
I've had to recover my database, thumbnails, and source configuration enough times that I just wanted a quick easy way to back them up. That is what this addon is meant to do. 

Usage: 

In the addon settings you can define a remote path for the destination of your xbmc files. You must also include a backup folder name, all of your files will be in this folder once the backup runs. 

On the Backup Selection page you can select which items from your user profile folder will be sent to the backup location. By default all are turned on except the Addon Data directory. 

To restore your data simply switch the Mode from "backup" to "restore" and the files will be copied from your remote directory to the local path. The file selection criteria will be used for the restore as well. 

What this Addon Will Not Do:

This is not meant as an XBMC file sync solution. If you have multiple frontends you want to keep in sync this addon may work in a "poor man's" sort of way but it is not intended for that. 

Your remote folder will not be "pruned" of files you have deleted. This behavior may change in the future but right now it is up to you to remove obsolete items from the remote path. The easiest way is to just delete the remote folder before doing a full backup. 

