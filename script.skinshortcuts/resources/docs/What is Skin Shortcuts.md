# What is Skin Shortcuts

Skin Shortcuts is a script for Kodi which manages lists of shortcuts the user has selected on behalf of skins which have integrated it. It allows the user to have as many or as few shortcuts in their list as they want, linking to anything they want and re-arrangeable as they want.

Additionally, it can manage a main menu and its submenu's. In this case, it can also manage additional properties for each menu item - such as the selected background or widget.

### How it works

Skin Shortcuts writes an additional file into the skins directory - script-skinshortcuts-includes.xml. In this file are a variety of `<include />`'s that the skin can use to fill content element of the list control they wish to show the users controls in.

The additional properties - for widgets, backgrounds and so forth - can be used by the skinner to decide what other 'furniture' should be displayed, and to fill the contents of it, such as the texture in an image control.

***Quick links*** - [Readme](../../README.md) - [Getting Started](./started/Getting Started.md) - [Advanced Usage](./advanced/Advanced Usage.md)