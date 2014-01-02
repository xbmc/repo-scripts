script.skinshortcuts was written with the intention of making user customizable shortcuts on the home page easier for skins to handle.

There are two ways to use this script. You can either (1) provide your own main menu items, and use the script to provide items for a sub-menu, or (2) use the script to provide both the main menu and sub-menu

Using the script to provide sub-menus
-------------------------------------

1. Recommended [groupname]'s
 
The script uses group=[groupname] property in order to determine which set of shortcuts to show. In order to share users customized shortcuts across different skins using this script, there are a few recommended [groupname]'s to use for your sub-menus
	videos
	movies
	tvshows
	livetv
	music
	musicvideos
	pictures
	weather
	programs
	dvd
	settings
 
2. Let users manage their shortcuts
 
In your skinsettings.xml file, you need to create a button for each [groupname] that you want to support, with the following in the <onclick> tag
 
	RunScript(script.skinshortcuts?type=manage&amp;group=[groupname])
 
3. Display user shortcuts
 
Uses new method of filling the contents of a list in Gotham. In the list where you want the submenu to appear, put the following in the <content> tag:
 
	plugin://script.skinshortcuts?type=list&amp;group=[groupname]
   
This will fill the list with items with the following properties:

	Label		Label of the item (localized where possible)
	Label2		Type of shortcut
	Icon		Icon image
	Thumbnail	Thumbnail image
	Property(labelID)	Unlocalized string primarily used when displaying both main menu and sub-menus
	Property(action)	The action that will be run when the shortcut is selected
	Property(group)		The [groupname] that this shortcut is listed from


Using the script to provide both main menu and sub-menus
--------------------------------------------------------

1. Information
 
This is a work in progress - it may not fully work as you expect, may require some creative skinning to get it looking right, and definitely has known issues!
 
2. Let users manage their main menu and sub-menu shortcuts
 
The script can provide a list of controls for your skinsettings.xml to let the user manage both main menu and sub-menu.
  
Uses new method of filling the contents of a list in Gotham. In the list where you want these controls to appear, put the following in the <content> tag:
  
	plugin://script.skinshortcuts?type=settings&amp;property=$INFO[Window(10000).Property("skinshortcuts")]
 
3. Display main menu and shortcuts
 
This details the simplest method of displaying main menu and sub-menus, using two lists. When the user focuses on an item in the main menu list, the sub-menu list will update with the shortcuts for that item.
  
In the list where you want the main menu to appear, put the following in the <content> tag:
 
	plugin://script.skinshortcuts?type=list&amp;group=mainmenu
   
This will fill the list with items with the following properties:

	Label		Label of the item (localized where possible)
	Label2		Type of shortcut
	Icon		Icon image
	Thumbnail	Thumbnail image
	Property(labelID)	Unlocalized string used for sub-menu and for displaying more controls depending on the main menu item
	Property(action)	The action that will be run when the shortcut is selected
	Property(group)		The [groupname] that this shortcut is listed from

In the list where you want the sub-menu to appear, put the following in the <content> tag:
 
	plugin://script.skinshortcuts?type=list&amp;group=$INFO[Container(9000).ListItem.Property(labelID)]
   
Remember to replace Container(9000) with the id of the list you are using for the main menu.
 
4. Display more controls depending on the mainmenu item
 
If you want to display more controls onscreen when the user focuses on a main menu item (for instance, to display a list of recently added movies when a "Movies" main menu item is focused) you can set the visibility of your additional controls using listitem.property(labelID). For common main menu items, it will contain one of the following strings:
	videos
	movies
	tvshows
	livetv
	music
	musicvideos
	pictures
	weather
	programs
	dvd
	settings
  
So, for example, you could set visibility for your list of recently added movies like so
  
	<visible>StringCompare(Container(50).ListItem.Property(labelID), movies)</visible>
   
For more information on what labelID may contain, see section on localization. A full list of labelID's can be found in the Resources folder.

5. Providing alternative access to settings

One of the side effects of using skinshortcuts to provide the whole main menu is that users have the ability to delete any shortcut, including those that they will later turn out to actually want. Generally, this isn't a problem as they can add them back at any time. However if they delete all links to settings, they will have no way to add it back unless your skin offers an alternative access.

Therefore, the script will set a property on the home window if the user doesn't have any way to access settings in their customized menu. If the property "SettingsShortcut" is set to "False", and it doesn't already, then you should consider providing an alternative way for the user to access settings. For instance, you could have a button for settings with the visibility set as follows:

	<visible>StringCompare(Window(10000).Property(SettingsShortcut),False)</visible>


Skinning the management dialog
------------------------------

To customize the look of the dialog displayed to allow the user to customize shortcuts, your skin needs to provide script-skinshortcuts.xml. It requires the following controls:

ID	Type	Description
101	Label	Current type of shortcut being viewed
102	Button	Change type of shortcut being viewed (down)
103	Button	Change type of shortcut being viewed (up)
111	List	Available shortcuts for the current type being viewed
211	List	Shortcuts the user has chosen for the [groupname]
301	Button	Add a new shortcut
302	Button	Delete shortcut
303	Button	Move shortcut up
304	Button	Move shortcut down
305	Button	Change shortcut label
306	Button	Change shortcut thumbnail
307	Button	Change shortcut action
308	Button	Reset shortcuts


Providing default shortcuts
---------------------------

If the user has not already selected any shortcuts or if the user resets shortcuts, the script will first attempt to load defaults from a file provided by the skin before trying to load its own.

To provide this optional file, create a new sub-directory in your skin called 'shortcuts', and drop the relevant [groupname].shortcuts file into it.

The easiest way to create this file is to use the script to build a list of shortcuts, then copy it from your userdata folder. See recommended groupname's for ideas of some of the default files you may wish to provide, along with mainmenu.shortcuts if you are using the script to manage the main menu.

The script provides defaults equivalent to Confluence's main menu and sub-menus.


Overriding Actions
------------------

It's possible to override an action, allowing the skin to provide additional functionality from a menu item - for example, you may wish to override the default action for Movies (to go to the titles view) and run a script such as Cinema Experience instead.

To do this, you need to provide an optional file called 'overrides.xml' in a sub-directory of your skin called 'shortcuts'. The file format is as follows:

<?xml version="1.0" encoding="UTF-8"?>
<overrides>
	<override action="[command]">
		<condition>[Boolean condition]</condition>
		<action>[XBMC function]</action>
	<override>
	<override action="ActivateWindow(Videos,MovieTitles,return)">
		<condition>Skin.HasSetting(CinemaExperience)</condition>
		<condition>System.HasAddon(script.cinema.experience)</condition>
		<action>RunScript(script.cinema.experience,movietitles)</action>
	</override>
</overrides>

In <override action="[command]"> specify the action that you are overriding.

<condition> is optional, and contains an XBMC boolean condition that must be met for the custom action to run. Multiple <condition> tags can be included to check multiple conditions. If multiple conditions are specified, all of them must be satisfied for the custom action to run.

<action> specified which action should be run. Multiple <action> tags can be included to run multiple actions.

Users can also provide the file in special://profile/ - if provided here then any overrides will carry over between skins. Additionally, overrides in this file will take precedent over overrides provided by the skin.


Overriding Thumbnails
---------------------

The script tries to provide reasonable default images for all shortcuts, with a fallback on "DefaultShortcut.png", however you may wish to override images to specific ones provided by your skin.

This can be done by providing an optional file called 'overrides.xml' in a sub-directory of your skin called 'shortcuts'. It provides two ways to override images, either overriding the image for a specific labelID, or overriding all instances of a particular image. The file format is as follows:

<?xml version="1.0" encoding="UTF-8"?>
<overrides>
	<thumbnail labelID="[labelID]>[New image]</thumbnail>
	<thumbnail labelID="movies">My Movie Image.png</thumbnail>
	<thumbnail image="[Old image]>[New image]</thumbnail>
	<thumbnail image="DefaultShortcut.png">My Shortcut Image.png</thumbnail>
</overrides>

Note, any thumbnail image the user has set will take precedence over skin-provided overrides.

A full list of labelID's and default thumbnail images can be found in the Resources folder.


Localization
------------

If you are providing default shortcuts and want to localize your label, you can do it using the format

  ::LOCAL::[id]
  
Where [id] is any string id provided by XBMC or your skin. However, you should generally avoid using strings provided by your skin as they won't carry over if the user switches to a different skin.

In order to make things easier for skinners using this script to provide the main menu, listitems returned by the script have the property labelID. This is a non-localized string that can be tested against (for visibility, for example).

For common main menu items, it will contain one of the following strings
	videos
	movies
	tvshows
	livetv
	music
	musicvideos
	pictures
	weather
	programs
	dvd
	settings
	
For other localized strings, it will contain the id of the string. For non-localized strings, it will contain the string in lowercase and without any spaces.

A full list of labelID's can be found in the Resources folder.


With Thanks
-----------

Huge thanks to Ronie, whose code for listing plugins is used in this script
Equally huge thanks to Ronie and `Black, for their favourites code used in this script
More huge thanks to BigNoid, for the ability to edit shortcuts
