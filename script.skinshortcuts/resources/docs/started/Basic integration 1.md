# Basic Integration - Main menu and submenu

The most common method of integrating Skin Shortcuts is to use it to provide the whole menu. This method means that your users will have unlimited customisation of their menus, and allows for many of the [Advanced Usage](../advanced/Advanced Usage.md) scenarios.

## Overview

In this method, Skin Shortcuts will be called when entering the home page and when leaving the skin settings page. It will build a file containing the menu items the user has selected in your skins directory.

That file then gets included in the skin, and the contents of the list being used for the main menu and submenu are then filled by using one of the includes built by Skin Shortcuts

## Adding build lines

Firstly, we want to tell Skin Shortcuts to build the menu. We do this by adding two lines - one in home.xml, and one in SkinSettings.xml

This will cause the script to build the users menu's, and write them into the file script-skinshortcuts-includes.xml in your skins directory.

In both cases, remember to replace mainmenuID=9000 with the id of the list you will be using to display the main menu in.

#### Home.xml

`<onload>RunScript(script.skinshortcuts,type=buildxml&amp;mainmenuID=9000)</onload>`

#### SkinSettings.xml

`<onunload>RunScript(script.skinshortcuts,type=buildxml&amp;mainmenuID=9000)</onunload>`

## Including the script-skinshortcuts-includes.xml file

Now the sript is building its includes file, we need to tell Kodi to load it. To do so, we add the following line to Includes.xml

`<include file="script-skinshortcuts-includes.xml"/>`

## Displaying the menus

We now have the menu's built, and Skin Shortcuts includes ready to be used by the skin. The script builds a variety of includes for different situations, but in this case we're interested in just two `skinshortcuts-mainmenu` and `skinshortcuts-submenu`

To use them, we just replace the existing contents of the `<content />` elements of the lists used to display the main and submenus with the Skin Shortcuts includes.

```
<control type="list" id="9000">
	<include>mainmenu-position-and-appearance</include>
	<content><include>skinshortcuts-mainmenu</include></content>
</control>
```

## Let the user edit their menu

Now we have a skin that has a menu system provided by Skin Shortcuts, but as yet the user can't actually customise what shortcuts they can see. So, in SkinSettings.xml, we want to add a button which will launch the Skin Shortcuts Management Dialog.

`RunScript(script.skinshortcuts,type=manage&amp;group=mainmenu)`

It's also generally a good idea to let the user reset all shortcuts to default with another button:-

`RunScript(script.skinshortcuts,type=resetall)`

## Customising the Management Dialog

The management dialog included with Skin Shortcuts isn't particularly well designed or useful, so chances are you're going to want to include your own. See [Management Dialog](./Management Dialog.md) for details.

## Where to go from here

You now have a basic but functional Skin Shortcuts implementation. Make sure you're familiar with the rest of the [Getting Started](./Getting Started.md) documentation, before you begin to explore the rest of the [documentation](../../../README.md).

***Quick links*** - [Readme](../../../README.md) - [Getting Started](./Getting Started.md) - [Advanced Usage](../advanced/Advanced Usage.md)