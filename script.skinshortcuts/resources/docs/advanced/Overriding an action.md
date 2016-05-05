# Overriding an action

You may wish to override an action in order to provide additional functionality. For example, you could override the default action for Movies (to go to the Movie Title view) to run Cinema Experience instead.

There are three methods available to override an action, all of which are based on the skins [overrides.xml](./overrides.md) file.

* Override a specific action - useful to provide extra functionality, such as CinemaVision for example
* Override all shortcuts action in a menu - useful to provide a 'first click' function, for example
* Add a supplemantary action to all shortcuts in a menu - useful for a power menu, for example

## Override a specific action

```
<override action="[Action]" group="[GroupName]" version="[Kodi Major Version]">
	<condition>[Boolean condition]</condition>
	<action>[New action]</action>
<override>
```
	
| Property | Optional | Description |
| :------: | :------: | ----------- |
| `[Action]` | | The action you are overriding |
| `[GroupName]` | Yes | The group that the override applies to, for example "movies". If omitted, the property will be apply to all items which match the action. |
| `[Kodi Major Version]` | Yes | The major Kodi version on which this override will occur, for example "15" for Isengard |
| `[Boolean condition]` | Yes | Replace with a string that must evaluate to True for the custom action to be run
| `[New action]` | | Replace with the action that should be run instead. You may include multiple <action> tags. Omit to run the original command. |

Note, any override will replace the original menu item with one which is only visible when any conditions are met. This means you will also need an override for when the conditions are not met.

Users can also provide an overrides.xml file to override actions in special://profile/

## Override all actions in a menu (global override)

It is possible to override all shortcuts in the list with a custom action. This can be usefull for example when you want to launch something in your skin when a shortcut is pressed when a specific condition is applies.

This is done by setting the `[Action]` of an `<override />` element to `globaloverride`.

For example:

```
<override action="globaloverride" group="mainmenu">
	<condition>![Skin.HasSetting(OpenSubMenuOnClick) + IntegerGreaterThan(Container(9001).NumItems,0)]</condition>
</override>
<override action="globaloverride" group="mainmenu">
	<condition>[Skin.HasSetting(OpenSubMenuOnClick) + IntegerGreaterThan(Container(9001).NumItems,0)]</condition>
	<action>SetFocus(4444)</action>
</override>
```

The above example changes the action to focus the submenu if the skinsetting OpenSubMenuOnClick is true.
If the OpenSubMenuOnClick setting is false it will use the default action for the shortcut.

#### Notes

If you do not specify a `group=` element, the override will be applied to all shortcuts in all menus.

If you do not specify an `<action>` element, the original action will be run.

You can include multiple `<action>` elements. If you want to run the original command as one of them, use `<action>::ACTION::</action>`.

## Add a supplemental action to all shortcuts in a menu.

It is possible to supply an additional onclick action for all shortcuts in the list.
Note that this doesn't override the action, it just adds an additional action to the menu item.

`<groupoverride group="[GroupName]" condition="[Boolean condition]">[Action]</groupoverride>`

| Property | Optional | Description |
| :------: | :------: | ----------- |
| `[GroupName]` | | The group that the override applies to, for example "movies". If omitted, the property will be apply to all items which match the action. |
| `Boolean condition]` | Yes | Replace with a string that must evaluate to True for the custom action to be run |
| `[Action]` | | The additional action that will be run |

Important note: If you are using skinshortcuts to provide the powermenu (DialogButtonMenu.xml) in your skin, you MUST use this feature from Kodi Isengard (15) and higher. This is because of a change in that dialog that requires you to first close the dialog before launching any other windows.

Example (assuming the name of your powermenu is powermenu):
`<groupoverride group="powermenu" condition="Window.IsActive(DialogButtonMenu.xml)">Close</groupoverride>`

## Run a different command based on automatic visibility condition

Skin Shortcuts adds automatic visibility conditions to relevant shortcuts - such as ensuring library nodes have the relevant content. If you wish, rather than having the visibility condition applied, you can run a different action if the visibility condition doesn't match

`<visibleoverride group="[GroupName]" condition="[Condition]">[Action]</visibleoverride>`

| Property | Optional | Description |
| :------: | :------: | ----------- |
| `[GroupName]` | Yes | The group that the override applies to, for example "mainmenu" or "movies". If omitted, the override will apply to all menus |
| `Condition]` | | The visibility condition that is being matched (not case sensitive) |
| `[Action]` | | The action that will be run if the condition does not match |

# Notes

#### Respecting user choice

It's always expected that user choice will be respected. That means that if a user has selected a particular shortcut, if it is overriden it should be clear why this is being done, or the option should be tied to a skin setting.

***Quick links*** - [Readme](../../../README.md) - [Getting Started](../started/Getting Started.md) - [Advanced Usage](./Advanced Usage.md)