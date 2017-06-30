# Additional submenu's or other menus

When using Skin Shortcuts to manage the whole menu, by default it manages a single submenu for each menu item. It is possible to use the script to manage multiple submenus, as well as for other menu's which are not linked to the main menu.

## Additional submenu's

#### Adjust the build line

If you wish more than one submenu, the build line needs to be adjusted to tell Skin Shortcuts to build the additional menu's. This is done by adding the `levels` property, and saying how many additional submenus are to be built.

So, for two additional submenus (above the standard submenu, making three submenus in total):-

`RunScript(script.skinshortcuts,type=buildxml&amp;mainmenuID=9000&amp;levels=2)`

#### Display the additional submenu's

The additional submenu's will be built into an include which can be used the same way as the original submenu. Their name is `skinshortcuts-submenu-x`, where `x` is the number of the additional menu starting from 1.

`<include>skinshortcuts-submenu-1</include>`

#### Editing the additional submenu's

The management dialog includes 5 buttons - 406 through 410 - which let the user edit additional submenu's 1 through 5.

If you require more than 5 additional submenu's, set the `level` window property, then send a click to 405:-

```
<onclick>SetProperty(level,6)</onclick>
<onclick>SendClick(405)</onclick>
```

## Other menus

#### Adjust the build line

If you want to build a menu unlinked to the main menu, you need to adjust the build line to tell Skin Shortcuts to build it. This is done by including the group parameter, and including `mainmenu` and the id of any additional group you want, seperated by a pipe - | - symbol.

`RunScript(script.skinshortcuts,type=buildxml&amp;mainmenuID=9000&amp;group=mainmenu|[groupname]|[groupname]|[groupname]...`

Note, `mainmenu` must be the first item in the group property.

The additional groups will be treated completely seperately from the main menu. See [integration details for Submenu Only](../started/Basic integration 2.md) for examples of how to use them.

***Quick links*** - [Readme](../../../README.md) - [Getting Started](../started/Getting Started.md) - [Advanced Usage](./Advanced Usage.md)