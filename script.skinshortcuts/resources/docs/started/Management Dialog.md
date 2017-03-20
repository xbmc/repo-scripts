# Management Dialog

The Management Dialog is the name given to the window that the user uses to choose which shortcuts to display in their menus, as well as to access many of the advanced features of the script.

## Launching management dialog

The management dialog is normally launched from a button in SkinSettings.xml

`RunScript(script.skinshortcuts,type=manage&amp;group=[groupname])`

Where [groupname] is the identified of the menu you wish to edit. To edit the main menu, use mainmenu as the [groupname].

## List of controls

| ID  | Type     | Label | Description |
| :-: | :------: | :---: | ----------- |
| 101 | Label	 | | Current type of shortcut being viewed |
| 102 | Button | | Change type of shortcut being viewed (down) |
| 103 | Button | | Change type of shortcut being viewed (up) |
| 111 | List | | Available shortcuts for the current type being viewed |
| 211 | List | | Shortcuts the user has chosen for the [groupname] |
| 301 | Button | 32000 | Add a new shortcut |
| 302 | Button | 32001 | Delete shortcut |
| 303 | Button | 32002 | Move shortcut up |
| 304 | Button | 32003 | Move shortcut down |
| 305 | Button | 32025 | Change shortcut label |
| 306 | Button | 32026 | Browse for thumbnail |
| 307 | Button | 32027 | Change shortcut action |
| 308 | Button | 32028 | Restore shortcuts |
| 310 | Button | 32045 | Change background |
| 311 | Button | | Select skin-provided thumbnail |
| 312 | Button | 32044 | Change widget (See "Advanced Usage") |
| 313 | Button | | Disable menu item |
| 401 | Button | 32048 | Select shortcut via select dialog |
| 404 | Button | | Set a custom property |
| 405 | Button | | Launch management dialog for submenu / additional menus |
| 406 | Button | | Launch management dialog for additional menu 1 |
| 407 | Button | | Launch management dialog for additional menu 2 |
| 408 | Button | | Launch management dialog for additional menu 3 |
| 409 | Button | | Launch management dialog for additional menu 4 |
| 410 | Button | | Launch management dialog for additional menu 5 |
| 500 | Label | 32071 / 32072 |	Window Title |

## Let the user select shortcuts

The management dialog includes two methods to let the user choose a shortcut for their menu. Either by displaying a list of available shortcuts directly in the management dialog, or letting the user select a shortcut from a select dialog

#### List of available shortcuts in management dialog

For this method, the shortcuts are shown in control 111. Controls 102 and 103 change what type of shortcuts are being viewed, and control 101 displays what type of shortcuts are being viewed.

#### Available shortcuts in a select dialog

In this method, control 401 is used to launch the select dialog

## label and label2

By default, if no label is specified for a control, Skin Shortcuts will automatically set its label to the one shown in the table above. You can stop it doing this by calling the management dialog as follows:-

`RunScript(script.skinshortcuts,type=manage&amp;group=[groupname]&amp;nolabels=true)`

It is common practice to use label2's to display additional information about the current shortcut the user has selected. The shortcuts in list 211 have most of the same properties as they will have when the menu is built. They also have the addition of 'path', which shows the currently selected action formatted for display.

Note that if Skin Shortcuts is setting the labels itself, label2's will not work. The solution is to set the label yourself, to the string ID shown in the table above.

It has been noted that in some situations, accessing the properties of the menu items directly can cause Kodi to hit an internal 'property limit' which causes unusual effects for the end user, such as artwork disappearing. As a workaround, Skin Shortcuts also makes the additional properties of the menu item currently selected available in window properties.

## Editing submenu/additional menu

When editing the main menu, you can let launch another instance of the Management Dialog to edit the submenu with button 405, or for an additional submenu with 406 - 410.

If you want to edit more additional submenu's, set the window property "level", then send a click to 405.

#### Hiding existing Management Dialog

As editing a submenu in this way launches an additional instance of the Management Dialog, you may want to hide the one for the main menu when this is shown. This can be done with the following visibility condition:-

`<visible>IsEmpty(Window.Property(additionalDialog)</visible>`

#### Limiting controls to main menu editor only

You will likely also want to limit some controls to just the main menu. The visibility condition for that:-

`<visible>StringCompare(Window.Property(groupname), mainmenu)</visible>`

#### Change window title for additional dialog

If you wish to display a different label for control 500 when editing a submenu or additional menu, set the window property 'overrideName' before sending a click to 405-410

## Always reset shortcuts with GUI 308

By default, GUI 308 offers the user the choice to either restore a default shortcut that the skin provides for the menu, or to reset all shortcuts in the currently edited menu to the skin defaults. You can choose to only provide one or the other of the options via [the skins overrides.xml file](../advanced/overrides.md) by including one of the following:-

`<alwaysRestore>True</alwaysRestore>` - gui 308 will automatically show the restore a shortcut dialog
`<alwaysReset>True</alwaysReset>` - gui 308 will automatically reset all shortcuts to skin defaults

## Custom focus on back

By default, any attempt to go 'back' will close the management dialog. You may wish to override this behaviour on a control-by-control basis by including the following in the [the skins overrides.xml file](../advanced/overrides.md):-

`<onback to="[id to focus]">[id currently focused]</onback>`

where `[id currently focused]` is the id of control you are specifying the onback behaviour for and `[id to focus]` is the id of the control that will be focused.

## Custom action on control

With most controls you can add an `<action />` element as you would normally when skinning the dialog. There are some occasions where this won't work in which case you can add the following to [the skins overrides.xml file](../advanced/overrides.md):-

`<onclick id="[id of control]">[Kodi function]</onclick>`

where `[id of control]` is the control the onclick will be added to and `[Kodi function]` is any inbuilt Kodi function.

## Disable shortcut (gui 313)

Control 313 allows the user to disable a shortcut, removing it from their menu without actually deleting it.

It's worth bearing in mind that the disabling is a universal setting, which is to say if the user disables a menu in one compatible skin, it will still be disabled if the user switches to another compatible skin.

To avoid a situation where the user can't re-enable a shortcut they disabled on another skin, it's highly encouraged for this control to be included in your management dialog - either directly or via the context menu.

As such, unless the context menu is customised by the skin, the script includes this by default in the context menu for control 211 on Krypton and above.

#### Use via radiobutton

The control can be accessed via a radiobutton control - you can check against the property 'skinshortcuts-disabled' of the selected shortcut. It's value will be 'True' if the shortcut is disabled, 'False' if it is enabled.

***Quick links*** - [Readme](../../../README.md) - [Getting Started](./Getting Started.md) - [Advanced Usage](../advanced/Advanced Usage.md)