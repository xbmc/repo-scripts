# Providing a vertical menu

Skin Shortcuts has the ability to build the entire menu - main menu and submenus - into a single include intended to be used as a vertical menu. In this scenario, the submenu items are hidden until the user clicks on the main menu item. A second click performs the action the user has selected for that item.

#### Adjust the build line

First, you need to tell Skin Shortcuts to build the vertical menu include, by adding `&amp;mode=single` to the build line.

#### Include the vertical menu

The menu will be built into the include `skinshortcuts-allmenus`. You can include this as the contents of the list you are using to display the vertical menu.

#### Hiding the submenus

Skin Shortcuts includes a function which will hide the submenus once they are visible. Its intended use is in the `<onback />` of the list that is containing the menu.

`RunScript(script.skinshortcuts,type=hidesubmenu&amp;mainmenuID=9000)`

Remember to replace `mainmenuID=9000` with the ID of the list container you are using for the menu.

#### Displaying different layout for main menu and submenu items

You will probably wish to skin the main menu and the submenu items differently from each other, to ensure its clear to the user what they are. This is done by having a visibility condition on the controls in the layout so they only display for the correct menu:-

`<visible>IsEmpty(ListItem.Property(isSubmenu))</visible>` - a main menu item
`<visible>!IsEmpty(ListItem.Property(isSubmenu))</visible>` - a submenu item

***Quick links*** - [Readme](../../../README.md) - [Getting Started](../started/Getting Started.md) - [Advanced Usage](./Advanced Usage.md)