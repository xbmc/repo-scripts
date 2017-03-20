# Basic Integration - Submenu only

If you want more control over your main menu than Skin Shortcuts allows, it is very possible to use it to just manage submenus.

## Overview

In this method, Skin Shortcuts will be called when entering the home page and when leaving the skin settings page to build individual menus for each submenu you want. It will build a file containing the menu items the user has selected in your skins directory.

That file then gets included in the skin, and the contents of the list being used for the submenu is then filled by using one of the includes built by Skin Shortcuts

## Adding build lines

Firstly, we want to tell Skin Shortcuts to build the menu. We do this by adding two lines - one in home.xml, and one in SkinSettings.xml

This will cause the script to build the users menu's, and write them into the file script-skinshortcuts-includes.xml in your skins directory.

In both cases, remember to replace mainmenuID=9000 with the id of the list you will be using to display the main menu in.

You need to include a [groupname] for each submenu that you want to build, separated by a pipe - `|` character.

#### Home.xml

`<onload>RunScript(script.skinshortcuts,type=buildxml&amp;mainmenuID=9000&amp;group=[groupname]|[groupname]|[groupname])</onload>`

#### SkinSettings.xml

`<onunload>RunScript(script.skinshortcuts,type=buildxml&amp;mainmenuID=9000&amp;group=[groupname]|[groupname]|[groupname])</onunload>`

## Including the script-skinshortcuts-includes.xml file

Now the sript is building its includes file, we need to tell Kodi to load it. To do so, we add the following line to Includes.xml

`<include file="script-skinshortcuts-includes.xml"/>`

## Displaying the menus

We now have the menu's built, and Skin Shortcuts includes ready to be used by the skin. The script builds a variety of includes for different situations, but in this case we're interested in just the ones called `skinshortcuts-group-[groupname]`

To use them, include them as the `<content />` of the list you want to use for each submenu.

```
<control type="list" id="9010">
	<include>submenu-position-and-appearance</include>
	<content><include>skinshortcuts-group-[groupname]</include></content>
</control>
```

And add a visibility condition so this list is only visible when the correct main menu item is selected.

## Let the user edit their menu

Now we have a skin that has a menu system provided by Skin Shortcuts, but as yet the user can't actually customise what shortcuts they can see. So, in SkinSettings.xml, we want to add a button for each submenu which will launch the Skin Shortcuts Management Dialog.

`RunScript(script.skinshortcuts,type=manage&amp;group=[groupname])`

## Customising the Management Dialog

The management dialog included with Skin Shortcuts isn't particularly well designed or useful, so chances are you're going to want to include your own. See [Management Dialog](./Management Dialog.md) for details.

## Recommended [groupname]'s

In order to share users customised submenu's across different skins using Skin Shortcuts, there are a few recommended [groupname]'s to use

- videos
- movies
- tvshows
- livetv
- radio
- music
- musicvideos
- pictures
- weather
- progras
- dvd
- settings

## Where to go from here

You now have a basic but functional Skin Shortcuts implementation. Make sure you're familiar with the rest of the [Getting Started](./Getting Started.md) documentation, before you begin to explore the rest of the [documentation](../../../README.md).

***Quick links*** - [Readme](../../../README.md) - [Getting Started](./Getting Started.md) - [Advanced Usage](../advanced/Advanced Usage.md)