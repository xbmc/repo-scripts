# End User FAQ

There are a number of questions that come up repeatedly with Skin Shortcuts use. Before asking your question in the [Kodi forum for the skin that you are using](http://forum.kodi.tv/forumdisplay.php?fid=67), please check if it has been answered below.

* [Where to get help](../../README.md#where-to-get-help---users)
* [Banned add-on policy](#banned-add-on-policy)
* [Link to add-on shows cached listings](#link-to-addon-shows-cached-listings)
* [Widget shows old listings](#widget-shows-old-listings)
* [Copying menu to another system](#copying-menu-to-another-system)
* [Cannot access settings](#cannot-access-settings)
* [Cannot set backgrounds](#cannot-set-backgrounds)
* [Changes to script-skinshortcuts-includes.xml are overwritten](#changes-to-script-skinshortcuts-includesxml-are-overwritten)
* [Cannot Build or Save Menu error](#cannot-build-or-save-menu-error)
* [Cannot hide a menu entry](#cannot-hide-a-menu-entry)

## Banned add-on policy

Skin Shortcuts fully supports Kodi's banned add-on policy. It is only ever tested against, and supported with, add-ons that are in the official repo or discussed on the official forum.

If it is not working in any way with any add-on that cannot be discussed on the Kodi forums, you need to find a forum where the add-on in question is supported, and ask your question there.

Please note that if you need to provide a [debug log](http://kodi.wiki/view/Debug_log), we expect you to disable any banned add-ons within Kodi before capturing the log. If there are banned add-ons within the log, you will not receive any support.

## Link to addon shows cached listings

This is a known Kodi issue which we hope will be fixed in an upcoming release - please see [this Trac ticket](http://trac.kodi.tv/ticket/16676) for details.

It is possible to trick Kodi into never using a cached version by editing the shortcut. If the shortcut already has a ? anywhere it, add the following to the end:

`&trickToReload=$INFO[System.Time(hh:mm:ss)]`

If it doesn't have a ?, add the following:

`?trickToReload=$INFO[System.Time(hh:mm:ss)]`

Note, this will not work with all shortcuts. If the shortcut doesn't work afterwards, delete the addition you made.

## Widget shows old listings

If your widget is provided by an add-on, recreate the widget with version 1.0.8 or higher of the script. The widget will be refreshed when media finishes playing.

## Copying menu to another system

The way that Skin Shortcuts saves your customised menus are not designed to be shared between systems. Having said that, it is possible to use the backup and restore functions of the Skin Helper Service script to do this.

If the skin you are using has the functions integrated, use the options provided to create and then restore a backup of your skin settings, which will include your custom menu items and associated properties.

If it is not integrated, you can create your own shortcuts to the settings. To backup, create a shortcut with the following actions:

`RunScript(script.skin.helper.service,action=backup)`

To restore, create a shortcut with the following action:

`RunScript(script.skin.helper.service,action=restore)`

## Cannot access settings

It is possible to delete any shortcuts to the Kodi settings area. Don't worry, there are a couple of ways to get back to it.

Many skins provide alternative access to settings on the shutdown menu. If there is no menu item to bring up the menu, hit 's'.

Otherwise, you can remove the contents of [userdata](http://kodi.wiki/view/Userdata)/addon_data/script.skinshortcuts - this will cause the menu to be reset to default next time you enter the home screen. From there you can get to settings and then restore the contents of the folder.

## Cannot set backgrounds

When trying to set a background for a menu item, you may not see the source where your backgrounds are contained in the select dialog.

This occurs when any sources have been added to Kodi's [File Manager](http://kodi.wiki/view/File_manager). To get access to your backgrounds, add the location where they are contained as a source within the file manager.

## Changes to script-skinshortcuts-includes.xml are overwritten

This file is not able to be directly edited - if it is, Skin Shortcuts will detect that the menu has been changed and re-write the menu. Make any changes you want through the menu editor. If you do need to manually edit part of the menu, see the developer documentation for help.

## Cannot Build or Save Menu error

If you get this error you will need to provide a debug log in order to recieve assistance. If you have the Debug Log Uploaded add-on installed, the script will prompt you to upload a log after the error occurs. Otherwise, see here for details on providing a debug log.

Most common causes for this is either the skin has been installed to a read-only location (such at Kodi's system-Addons folder, rather than the profiles Addons folder), or you have found a bug in the script.

## Cannot hide a menu entry

Version 1.0.9 of the script introduces a new control for the management dialog - GUI 313 - which can be used to disable a menu entry.

In many skins, the script is able to automatically enable this control by adding it to the context menu for GUI 211 (the list of menu items in the custom menu), but we are not able to do this on all skins, and so some skins will need manually updating to support it.