script.skinshortcuts was written with the intention of making user customizable shortcuts on the home page easier for skinners.


What's New for Skinners (version 0.3.0)
-----------------------

 - (Includes method) Menu items now only have the "hasSubmenu" property if there is a submenu
 - Test of an alternative includes method for including whole menu in a single list, see "Alternative Listings Method" in Advanced Usage.txt
 - Numerous management dialog changes - see resources/Management Dialog.txt for full details - including
	> Advice change - skins should now provide labels for all controls
	> Labels 311 and 312 (background and widget name) replaced with listitem properties
 - Management dialog will now list skin-provided playlists - this affects defaults, see "Providing Default Shortcuts" below
 - Management dialog can now list skin-recommended shortcuts - see "Skin-Recommended Shortcuts" in Advanced Usage.txt
 - If you prefer to manage menus yourself, the script can now be used to select a shortcut, then pass this to the skin to manage - see "Just select shortcuts" in Advanced Usage.txt
 
Note: The code to manage additional properties including backgrounds and widgets has been re-written in this revision. The new method is not backwards compatible, so any backgrounds/widgets/additional properties will need to be re-set.
 
 
Where To Get Help
-----------------

Though hopefully Skin Shortcuts will save you a lot of code in the long-run, it is a relatively complex script and so may take some time to get your head around.

To help, it includes several documentation files:
	readme.txt - This file, containing basics of integrating the script
	
	resources/Advanced Usage.txt - Contains details of more advanced configuration and customisation
	
	resources/Management Dialog.txt - Contains details of how to skin the management dialog the user will interact with to manage their shortcuts
	
	resources/labelID.txt - Contains details of the labelID system used to identify shortcuts.

It's highly recommended to take time to read through all of these documents before you begin.

If you require any assistance post on the XBMC forum and I'll do my best to assist:

	http://forum.xbmc.org/showthread.php?tid=178294

 
Before you Begin
----------------

Before you can add the script to your skin, you have two decisions to make:

Decision: Which method to use to list menus?
			- Via the new XBMC 'Gotham' method of filling a list
			- Via <include>'s
			
Decision: How much of the menu system should the script manage?
			- Main menu and sub-menus
			- Sub-menus only
			
If you are using the script to provide main menu and sub-menu, I recommend using the <includes> method.
			- The script will generate a file in your skins directory on first run and after menu changes
			- Once this file is generated, the skin will reload so it can load the latest changes
			- The menus will then perform as more traditional skin-provided menus
			
If the script is just providing sub-menus, I recommend Gotham's method of filling a list
			- The menus are generated on the fly when needed
			- There will be a slight delay for them to appear
			- There is no need for the script to reload the skin
			
Whichever combination of methods and menu systems you choose, details of how to implement are below. Below that, there is information common to all methods which you should also read.

You may also choose to manage menu's yourself, and just make use of the scripts list of available shortcuts. For more details see "Just Select Shortcuts" in Advanced Usage.txt


Using the 'Gotham' method of filling a list - Sub-menus only
-------------------------------------------

1. Let the user manage their shortcuts

In your skinsettings.xml file, you need to create a button for each [groupname] that you want to support, with the following in the <onclick> tag
 
	RunScript(script.skinshortcuts,type=manage&amp;group=[groupname])

	
2. Display user shortcuts (single group)
 
In the list where you want the submenu to appear, put the following in the <content> tag:
 
	plugin://script.skinshortcuts?type=list&amp;group=[groupname]
	
	
3. Display user shortcuts based on another list

If your skin provides a main menu you want to display shortcuts for using the script, then you need to add an additional property to each main menu item, called submenuVisibility, containing the [groupname] of the submenu to associate with that main menu.

	<property name="submenuVisibility">[groupname]</property>
	
Then, in the list where you want the submenu to appear, put the following in the <content> tag:

	plugin://script.skinshortcuts?type=submenu&amp;mainmenuID=9000&amp;group=[groupname],[groupname],[groupname]
	
Replace 9000 with the ID of the list you are using for the mainmenu. You should include all [groupname]'s that your skin supports, separated by a comma. The script will then load all of the submenus, and set visibility conditions on each one.
	

Using the 'Gotham' method of filling a list - Main menu and sub-menus
-------------------------------------------

1. Let users manage their main menu and sub-menu shortcuts
 
The script can provide a list of controls for your overrides.xml to let the user manage both main menu and sub-menu.
  
Uses new method of filling the contents of a list in Gotham. In the list where you want these controls to appear, put the following in the <content> tag:
  
	plugin://script.skinshortcuts?type=settings&amp;property=$INFO[Window(10000).Property("skinshortcuts")]
	
Alternatively, you can create a button with the following onclick method:

	RunScript(script.skinshortcuts,type=manage&amp;group=mainmenu)
	
Then, within the management dialog, provide a button with the id 405 to let the user manage sub-menus. You must use this method if you want to provide more than one sub-menu.

If using the second method, you may also want to provide a reset button, with the following in the onclick method:

	RunScript(script.skinshortcuts,type=resetall)
 
 
2. Display main menu and shortcuts
 
This details the simplest method of displaying main menu and sub-menus, using two lists. When the user focuses on an item in the main menu list, the sub-menu list will update with the shortcuts for that item.
  
In the list where you want the main menu to appear, put the following in the <content> tag:
 
	plugin://script.skinshortcuts?type=list&amp;group=mainmenu
   
In the list where you want the sub-menu to appear, put the following in the <content> tag:
 
	plugin://script.skinshortcuts?type=submenu&amp;mainmenuID=9000
   
Remember to replace 9000 with the id of the list you are using for the main menu.

To provide additional sub-menus, use the following in the <content> tag:

	plugin://script.skinshortcuts?type=submenu&amp;level=1&amp;mainmenuID=9000
	
Remember to replace 9000 with the id of the list you are using for the main menu. Increase the value of the 'level' property for each additional sub-menu.
	
 
3. Display more controls depending on the mainmenu item

If your skin provides widgets or has custom backgrounds, you can use Skin Shortcuts to manage these. You can also use Skin Shortcuts to manage any additional properties you wish. See "Advanced Usage".

Otherwise, you can set visibility of any additional controls based on the labelID of the main menu listitems property 'labelID'. For information on what labelID may contain, see section "Advanced Usage". A full list of labelID's can be found in the Resources folder.


Using <includes> - sub-menu only
----------------

1. Include the necessary file, and run the script

This method runs the script when the user enters the main menu or has left the skin settings. If a change to the menu has been made, it writes out the new menu into a file that you can <include> in your skin.

*IMPORTANT*

Using this method WILL WRITE AN ADDITIONAL FILE TO YOUR SKINS DIRECTORY called script-skinshortcut-includes.xml!

First the file must be imported - in your includes.xml add the line:

	<include file="script-skinshortcuts-includes.xml"/>
	
In home.xml, add the line:

	<onload>RunScript(script.skinshortcuts,type=buildxml&amp;mainmenuID=9000&amp;group=[groupname],[groupname],[groupname])</onload>

And in skinsettings.xml, the line:

	<onunload>RunScript(script.skinshortcuts,type=buildxml&amp;mainmenuID=9000&amp;group=[groupname]|[groupname]|[groupname])</onunload>
	
Replace 9000 with the ID of the list you are using for the mainmenu. You should include all [groupname]'s that your skin supports, separated by a pipe. The script will then load all of the submenus, and set visibility conditions on each one.


2. Let the user manage their shortcuts

In your skinsettings.xml file, you need to create a button for each [groupname] that you want to support, with the following in the <onclick> tag
 
	RunScript(script.skinshortcuts,type=manage&amp;group=[groupname])

	
3. Display user shortcuts (single group)
 
In the list where you want the submenu to appear, put the following in the <content> tag:
 
	<include>skinshortcuts-[groupname]</include>
	
	
4. Display user shortcuts based on another list

If your skin provides a main menu you want to display shortcuts for using the script, then you need to add an additional property to each main menu item, called submenuVisibility, containing the [groupname] of the submenu to associate with that main menu.

	<property name="submenuVisibility">[groupname]</property>
	
Then, in the list where you want the submenu to appear, put the following in the <content> tag:

	<include>skinshortcuts-submenu</include>
	

Using <includes> - Main menu and sub-menus
----------------

1. Include the necessary file, and run the script

This method runs the script when the user enters the main menu or has left the skin settings. If a change to the menu has been made, it writes out the new menu into a file that you can <include> in your skin.

*IMPORTANT*

Using this method WILL WRITE AN ADDITIONAL FILE TO YOUR SKINS DIRECTORY called script-skinshortcut-includes.xml!

First the file must be imported - in your includes.xml add the line:

	<include file="script-skinshortcuts-includes.xml"/>
	
In home.xml, add the line:

	<onload>RunScript(script.skinshortcuts,type=buildxml&amp;mainmenuID=9000&amp;levels=0)</onload>

And in skinsettings.xml, the line:

	<onunload>RunScript(script.skinshortcuts,type=buildxml&amp;mainmenuID=9000&amp;levels=0)</onunload>
	
Replace 9000 with the ID of the list you are using for the mainmenu. If you are providing more than one sub-menu per main-menu item, increase the levels accordingly.


2. Let users manage their main menu and sub-menu shortcuts
 
The script can provide a list of controls for your overrides.xml to let the user manage both main menu and sub-menu.
  
Uses new method of filling the contents of a list in Gotham. In the list where you want these controls to appear, put the following in the <content> tag:
  
	plugin://script.skinshortcuts?type=settings&amp;property=$INFO[Window(10000).Property("skinshortcuts")]
	
Alternatively, you can create a button with the following onclick method:

	RunScript(script.skinshortcuts,type=manage&amp;group=mainmenu)
	
Then, within the management dialog, provide a button with the id 405 to let the user manage sub-menus. You must use this method if you want to provide more than one sub-menu.

If using the second method, you may also want to provide a reset button, with the following in the onclick method:

	RunScript(script.skinshortcuts,type=resetall)
 
 
3. Display main menu and shortcuts
 
This details the simplest method of displaying main menu and sub-menus, using two lists. When the user focuses on an item in the main menu list, the sub-menu list will update with the shortcuts for that item.
  
In the list where you want the main menu to appear, put the following in the <content> tag:
 
	<include>skinshortcuts-mainmenu</include>
   
In the list where you want the sub-menu to appear, put the following in the <content> tag:
 
	<include>skinshortcuts-submenu</include>
   
Remember to replace 9000 with the id of the list you are using for the main menu.

To provide additional sub-menus, use the following in the <content> tag:

	<include>skinshortcuts-submenu-[level]</include>
	
Where level indicates the additional submenu level, starting from 1.


Recommended [groupname]'s
-------------------------

If providing only the sub-menu, the script uses the [groupname] property to determind which set of shortcuts to show. In order to share users customized shortcuts across different skins using this script, there are a few recommended [groupname]'s to use:

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
	
	
Providing default shortcuts
---------------------------

If the user has not already selected any shortcuts or if the user resets shortcuts, the script will first attempt to load defaults from a file provided by the skin before trying to load its own.

To provide this optional file, create a new sub-directory in your skin called 'shortcuts', and drop the relevant [groupname].shortcuts file into it.

The easiest way to create this file is to use the script to build a list of shortcuts, then copy it from your userdata folder. See "Recommended [groupname]'s" for ideas of some of the default files you may wish to provide, along with mainmenu.shortcuts if you are using the script to manage the main menu.

The script provides defaults equivalent to Confluence's main menu and sub-menus.

If you want to provide a default which links to a playlist you include with your skin, then make sure the .shortcuts file uses the special protocol (e.g. special://skin/) as the URI to it. The script will replace this with a localised version, so that the playlist link will continue to work even if the user switches to another skin supporting skin shortcuts.
	
	
Properties returned
-------------------

Regardless of which method you use, the script will always return a list with a few standard properties:

	Label		Label of the item (localized where possible)
	Label2		Type of shortcut
	Icon		Icon image
	Thumbnail	Thumbnail image
	Property(labelID)	Unlocalized string used for sub-menu and for displaying more controls depending on the main menu item
	Property(action)	The action that will be run when the shortcut is selected
	Property(group)		The [groupname] that this shortcut is listed from
	Property(widget)	If your skin uses Skin Shortcuts to manage widgets, the [widgetID] will appear here (mainmenu only)
	Property(widgetName)        - The display name of the widget will appear here
	Property(background)If your skin uses Skin Shortcuts to manage background, the [backgroundID] will appear here (mainmenu only)
	Property(backgroundName)    - The display name of the widget will appear here

You can also use the script to manage any additional properties you would like. See "resources/Management Dialog.txt" and "resources/Advanced Usage.txt" - "Overrides.xml" - section 5 (Custom shortcut properties)
	
	
Display more controls depending on the mainmenu item
----------------------------------------------------

If your skin provides widgets or has custom backgrounds, you can use Skin Shortcuts to manage these. See resources/Advanced Usage.txt

Otherwise, you can set visibility of any additional controls based on the labelID of the main menu listitems property 'labelID'. For common main menu items, it will contain one of the following strings:
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
   
A full list of labelID's can be found in the Resources folder.


Providing alternative access to settings
----------------------------------------

One of the side effects of using skinshortcuts to provide the whole main menu is that users have the ability to delete any shortcut, including those that they will later turn out to actually want. Generally, this isn't a problem as they can add them back at any time. However if they delete all links to settings, they will have no way to add it back unless your skin offers an alternative access.

Therefore, it is recommended to have an alternative link to settings. One possible location is in your shutdown menu.


Skinning the management dialog
------------------------------

For details on skinning the management dialog, see resources/Management Dialog.txt.


Advanced Usage
--------------

The script includes a number of options and features to try to make a skinners life easier, and to help customise the script for your skin.

* Manage backgrounds
* Manage widgets
* Overrides.xml
* Localisation

For details, see "resources/Advanced Usage.txt".


With Thanks
-----------

Huge thanks to Ronie, whose code for listing plugins is used in this script
Equally huge thanks to Ronie and `Black, for their favourites code used in this script
More huge thanks to BigNoid, for the ability to edit shortcuts
And the biggest thanks of all to Annie and my family, for feature suggestions, testing and shouting at me when I broke things
