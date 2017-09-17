# Kodi Add-on Data Sync (for Dropbox)
This is a simple Kodi service add-on that sync (bi-directional) add-on data. Currently only Dropbox is supported. It is still heavily in development.

## Backups! Yes, you need them
This add-on can seriously *mess up* your Kodi's _addon_data_ folder. Before you continue to use this add-on, please, please, please, **backup** those folders on all machines and Kodi profiles you are going to run the sync with.  

## Prerequisites
You will need to have the following in order to make this all work:

1. Full backups of your _addon_data_ folders (yes, again a reminder!)
1. Kodi Krypton (or higher) installed on either Linux, Windows or Android.
1. A Dropbox account with some storage available.
1. A Dropbox Developer App API Key:
    * Currently this add-on does not (yet) provide OAuth authentication. So you will need to create your own app to make it work.
    * Head over to [Dropbox.com's App Console](https://www.dropbox.com/developers/apps).
    * Create a new app there with the Dropbox API.
    * Select the "_App Folder_" access option.
    * And give the app an appropriate name. 
    * Then go into the app's settings and select "_Generated access token_".
    * Configure that token in the Kodi Add-on settings for the Dropbox.
1. Think of a nice name for _sync group_

## How it works
Within the add-on settings for this add-on you specify a _Sync Group_. All _Kodi Add-on Data Sync (for Dropbox)_ add-ons with the same _Sync Group_ configured will sync add-on data with each other using Dropbox. You can create multiple _Sync Groups_ that group different Kodi installs or even Kodi logins into different _Sync Groups_. However, you can only sync each instance of the add-on to a single _Sync Group_.

There are two main sync modes:

* Selective Sync
* Sync All

The _Sync All_ mode is the most simple, it will simply sync **all** add-on data to Dropbox. However, when _Selective Sync_ is enabled via the add-on settings, not all add-ons will be synced. In this case only those add-ons that you have selected for syncing will by synced with Dropbox. 

Marking an add-on for syncing can be done from the Kodi Add-on Manager. All installed add-ons in the Add-on manager will have a context menu item "Add-on Data Sync". From there you can add and remove an add-on from syncing. **However**, Kodi's context menu items are very simple and cannot distinguish a syncing and non-syncing add-on. So there will always be two sub menu items: _Add_ and _Remove_ regardless of the current sync state.  

## How is stuff synced?
Depending on the situation files will update uploaded or download. The following table describes what happens in what scenario:

Local \ Remote | Added | Existing | Non-Existing | Deleted
---------|---------|---------|---------|-------------
**Added** | Sync most recent. | Should not happen but if then we sync the most recent. | Upload local file. | Upload local file.
**Existing** | Should not happen but if then we sync the most recent. | Sync most recent, or if no changes then don't sync. | Upload local file. | Was the local file updated after the last sync? Yes, then upload, else delete locally.
**Non-Existing** | Download remote file. | Download remote file. | No action (Duh!) | No action.
**Deleted** | Download remote file. | Was the remote file updated after the last sync? Yes, then download, else delete remotely. | No action needed. | No action needed.

Let's look into some examples:

* A file exists both locally as remote. This will lead to _Sync most recent, or if no changes then don't sync_ and thus the add-on will check what he most recent version. If the local one is newer, it will be upload. If the remote version is newer, that version will be downloaded. If they did not change, nothing will happen.
* What if I add a new add-on locally? The settings for that add-on are _Added_ locally an _Non-Existing_ remotely: so they will be uploaded. 
* In the previous case, other instances of Kodi will see the setting files as _Added_ remotely and _Non-Existing_ locally and they will thus be downloaded.
* **Special**: What if you add new Kodi instance? Then some files might exist in both locations. In that situation if files exist both locally and remotely, the remote files will always be downloaded. 

## Troubleshooting
If you run into any issues, make sure to enable DEBUG (or TRACE) logging for the first. This can be done via the add-ons settings of the _Kodi Add-on Data Sync_ add-on. After another sync, you can upload your log files via the built-in option, again via the add-on settings.

With that log file you can create a new issue at the BitBucket [issue tracker](https://bitbucket.org/basrieter/service.addondata.sync/issues) and attach these log files with your issue. Other discussion can be one at the Kodi forum [thread](https://forum.kodi.tv/showthread.php?tid=319572).   
