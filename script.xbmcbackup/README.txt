XBMC Backup

About: 
I've had to recover my database, thumbnails, and source configuration enough times that I just wanted a quick easy way to back them up. That is what this addon is meant to do. 

Usage: 

In the addon settings you can define a remote path for the destination of your xbmc files. Each backup will create a folder named in a month, day, year format so you can create multiple backups. You can keep a set number of backups by setting the integer value of the Backups to Keep setting greater than 0. 

On the Backup Selection page you can select which items from your user profile folder will be sent to the backup location. By default all are turned on except the Addon Data directory. 

To restore your data simply switch the Mode from "backup" to "restore" and type the date of the backup you wish to restore from . The files will be copied from your remote directory to the local path. The file selection criteria will be used for the restore as well. 

Scheduling: 

You can also schedule backups to be completed on a set interval via the scheduling area. When it is time for the backup to run it will be executed in the background. 

What this Addon Will Not Do:

This is not meant as an XBMC file sync solution. If you have multiple frontends you want to keep in sync this addon may work in a "poor man's" sort of way but it is not intended for that. 

This backup will not check the backup destination and delete files that do not match. It is best to only do one backup per day so that each folder is correct. 

