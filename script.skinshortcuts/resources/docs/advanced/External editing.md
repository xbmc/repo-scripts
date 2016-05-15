#External Editing

Skin Shortcuts is based around the user using the management dialog to customise their menu. However, there is limited support for aspects of the menu to be edited from outside of the management dialog.

## Context menu add-on

There is a context menu add-on available in the official repo. This allows any node to be added to the users menu from the context menu. If the item is being added to the main menu, rather than a custom menu, it also offers to auto-fill the submenu with any nodes contained within the node being added.

## Change properties of menu items

If you have the `[labelID]` of a given menu item, you can change any additional property of the main menu item from outside of the management dialog:-

`<onclick>RunScript(script.skinshortcuts,type=setProperty&amp;property=[Property]&amp;value=[Value]&amp;labelID=[labelID]&amp;group=[GroupName])</onclick>`

| Property | Optional | Description |
| :------: | :------: | ----------- |
| `[Property]` |  | The property of the menu item you want to change |
| `[Value]` |  | The new value of the property you are changing |
| `[labelID]` |  | The labelID of the menu item you are changing |
| `[GroupName]` | Yes | The group that the menu item must be in. If ommitted defaults to the main menu ]

To change multiple properties for multiple menu items, separate each `[Property]` and `[Value]` with a pipe - | - symbol. If you want to change multiple individual menu items, separate the `[labelID]`'s with a pipe - | - symbol.

Note, the number of `[Property]` and `[Value]`'s given must match. You can either have a single `[labelID]`, or the number of labelID's given must also match.

So, to change the widgetName and widgetType of the main menu item with the labelID movies:-

`<onclick>RunScript(script.skinshortcuts,type=setProperty&amp;property=widgetName|widgetType&amp;value=new|values&amp;labelID=movies)</onclick>`

***Quick links*** - [Readme](../../../README.md) - [Getting Started](../started/Getting Started.md) - [Advanced Usage](./Advanced Usage.md)