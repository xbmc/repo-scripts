script.skinshortcuts was written with the intention of making user customizable shortcuts on the home page easier for skinners.

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
 
In your overrides.xml file, you need to create a button for each [groupname] that you want to support, with the following in the <onclick> tag
 
	RunScript(script.skinshortcuts,type=manage&amp;group=[groupname])
 
 
3. Display user shortcuts (single group)
 
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
	
	
4. Display user shortcuts based on another list

If your skin provides a main menu you want to display shortcuts for using the script, then you need to add an additional property to each main menu item, called submenuVisibility, containing the [groupname] of the submenu to associate with that main menu.

	<property name="submenuVisibility">[groupname]</property>
	
Then, in the list where you want the submenu to appear, put the following in the <content> tag:

	plugin://script.skinshortcuts?type=submenu&amp;mainmenuID=9000&amp;group=[groupname],[groupname],[groupname]
	
Replace 9000 with the ID of the list you are using for the mainmenu. You should include all [groupname]'s that your skin supports, separated by a comma. The script will then load all of the submenus, and set visibility conditions on each one.


Using the script to provide both main menu and sub-menus
--------------------------------------------------------

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
   
This will fill the list with items with the following properties:

	Label		Label of the item (localized where possible)
	Label2		Type of shortcut
	Icon		Icon image
	Thumbnail	Thumbnail image
	Property(labelID)	Unlocalized string used for sub-menu and for displaying more controls depending on the main menu item
	Property(action)	The action that will be run when the shortcut is selected
	Property(group)		The [groupname] that this shortcut is listed from
	Property(widget)	If your skin uses Skin Shortcuts to manage widgets, the [widgetID] will appear here (mainmenu only)
	Property(background)If your skin uses Skin Shortcuts to manage background, the [backgroundID] will appear here (mainmenu only)

In the list where you want the sub-menu to appear, put the following in the <content> tag:
 
	plugin://script.skinshortcuts?type=submenu&amp;mainmenuID=9000
   
Remember to replace 9000 with the id of the list you are using for the main menu.

To provide additional sub-menus, use the following in the <content> tag:

	plugin://script.skinshortcuts?type=submenu&amp;level=1&amp;mainmenuID=9000
	
Remember to replace 9000 with the id of the list you are using for the main menu. Increase the value of the 'level' property for each additional sub-menu.
	
 
3. Display more controls depending on the mainmenu item

If your skin provides widgets or has custom backgrounds, you can use Skin Shortcuts to manage these. See "Advanced Usage".

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
   
For more information on what labelID may contain, see section "Advanced Usage". A full list of labelID's can be found in the Resources folder.


4. Providing alternative access to settings

One of the side effects of using skinshortcuts to provide the whole main menu is that users have the ability to delete any shortcut, including those that they will later turn out to actually want. Generally, this isn't a problem as they can add them back at any time. However if they delete all links to settings, they will have no way to add it back unless your skin offers an alternative access.

Therefore, it is recommended to have an alternative link to settings. One possible location is in your shutdown menu.


Skinning the management dialog
------------------------------

1. List of controls

To customize the look of the dialog displayed to allow the user to customize shortcuts, your skin needs to provide 'script-skinsettings.xml'. It requires the following controls:

Primary controls:

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
305	Button	Change shortcut label (if control 402 is not included)
306	Button	Change shortcut thumbnail
307	Button	Change shortcut action (if control 403 is not included)
308	Button	Reset shortcuts

Additional controls:

309 Button  Change widget (See "Advanced Usage")
310 Button  Change background (See "Advanced Usage")
311 Label	Selected widget name
312 Label	Selected background name

401 Button	Alternative method to set a shortcut
404 Button	Set a custom property
405 Button	Launch management dialog for submenu / additional menus

You can set a label on any of these controls EXCEPT 101, 311 and 312. If no label is set, Skin Shortcuts will provide a label.

You MUST include a label if you include controls 404 and 405.

Most of these controls are optional (though it is recommended to include them), but you MUST include control 211. Controls 101, 102, 103 and 111 all rely on the others being present.


2. Alternative method to set a shortcut

Rather than using list 111 to let the user select a shortcut, you can include button 401. When clicked it will show the user, via the standard Select dialog, first a list of the available categories of shortcuts, then the shortcuts within that category.

You can also use the button to go straight to the list of shortcuts for a category by first setting the window property "category", then sending a click to the button. The available categories are:

	common		(Items commonly found on a main menu)
	video		(Video library)
	music		(Music library)
	playlists	(Users playlists)
	favourites	(Users favourites)
	addons		(Programs, video add-ons, music add-ons, picture add-ons)
	
Note, you must still include all controls in the 100 range in your xml file. However, they do not have to be visible to the user. After a click to 401 has been registered, the window property "category" will be cleared.


3. Set a custom property

If you want to attach a custom property to a menu item, you can include button 404.

To set a property, first set the following window properties

	customProperty	The name you are giving to the custom property
	customValue		The value of the custom property (to clear a property, don't set this property)
	
Then send a click to control 404. The two properties will be cleared afterwards.

You can set defaults for your custom property in your overrides.xml file. See "Advanced Usage"


4. Launch management dialog for submenu / additional menus

You can give the users a way to launch the management dialog for the submenu or an additional menu from the management dialog.

To do this include the control 405. Clicking it will launch the management dialog for the submenu of the selected item.

To launch the management dialog for an additional sub menu, first set the window property "level", then send a click to 405. The property will be cleared afterwards.

You will likely only want to include this when editing the main menu. You can check the window property "groupname" for the value "mainmenu" to only display it when relevant.


5. Limit controls to main menu only

You may wish to only show some of these controls when the user is editing the main menu only, not a submenu. To do this, check the window property "groupname" for the value "mainmenu".


Providing default shortcuts
---------------------------

If the user has not already selected any shortcuts or if the user resets shortcuts, the script will first attempt to load defaults from a file provided by the skin before trying to load its own.

To provide this optional file, create a new sub-directory in your skin called 'shortcuts', and drop the relevant [groupname].shortcuts file into it.

The easiest way to create this file is to use the script to build a list of shortcuts, then copy it from your userdata folder. See recommended groupname's for ideas of some of the default files you may wish to provide, along with mainmenu.shortcuts if you are using the script to manage the main menu.

The script provides defaults equivalent to Confluence's main menu and sub-menus.


Advanced Usage
--------------

The script includes a number of options and features to try to make a skinners life easier, and to help customise the script for your skin.

* Manage backgrounds
* Manage widgets
* Overrides.xml
* Localisation

For details, see "Advanced Usage.txt" in the Resources folder.


With Thanks
-----------

Huge thanks to Ronie, whose code for listing plugins is used in this script
Equally huge thanks to Ronie and `Black, for their favourites code used in this script
More huge thanks to BigNoid, for the ability to edit shortcuts
And the biggest thanks of all to Annie and my family, for feature suggestions, testing and shouting at me when I broke things
