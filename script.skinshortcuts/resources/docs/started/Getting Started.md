#Getting Started

## Basic Integration

Basic integration of Skin Shortcuts is designed to be relatively easy, though how you go about it depends on what level of integration you want with the script.

#### Main menu and submenu

In this scenario, you are using Skin Shortcuts to manage the whole menu system.

[Basic Integration](./Basic integration 1.md)

#### Submenu only

In this scenario, you are still managing the main menu, but are using Skin Shortcuts to provide submenus to the main menus

[Basic Integration](./Basic integration 2.md)

#### 'Just Select' method

In this scenario, you are managing the whole menu, but are using Skin Shortcuts to allow the user to select which shortcuts they want.

[Advanced Usage - 'Just Select' method](../advanced/Just Select.md)

## Management Dialog

The Management Dialog is the name given to the window users use to choose what shortcuts they want in their menus. It's also where lots of additional functionality of the script is exposed to the user.

[Read More](./Management Dialog.md)

## What properties does Skin Shortcuts return

Shortcuts provided by Skin Shortcuts provide lots of properties you can make use of. Feel free to look in script-skinshortcuts-includes.xml for a complete list, but some of the more important ones:-

| Property | Description |
| :------: | ------------|
| Label | Label of the item (localized where possible) |
| Label2 | Type of shortcut |
| Icon | Icon image |
| Thumbnail | Thumbnail image |
| property(labelID) | Unlocalized string used for sub-menu and for displaying more controls depending on the main menu item |
| property(defaultID) | Permanent form of the labelID |
| property(action) | The action that will be run when the shortcut is selected |
| property(list) | The action of the shortcut, without any 'ActivateWindow' elements |
| property(group) | The [groupname] that this shortcut is listed from |

Various other properties will be returned if you are using Skin Shortcuts to manage widgets or backgrounds, and in other situations. See the relevant documentation for details.

## Notes

#### script-skinshortcuts-includes.xml

It's important to note that using Skin Shortcuts means the script will write an extra file to your skins directory.

#### Automatic visibility conditions

Skin Shortcuts automatically adds visibility conditions to shortcuts when they are built. [Read here](./Visibility Conditions.md) for more details.

#### Shortcut to Settings

One side-effect of using Skin Shortcuts to manage the whole menu is that the user has the possibility to delete any shortcut, including those that they may later decide they do want. In general, this is no issue as they can also add any shortcut, but if they delete a shortcut to settings it can lead to them being unable to edit the menu to add it back.

There are a few methods you can use to prevent (or at least warn) the user deleted settings (see [Advanced Usage](../advanced/Advanced Usage.md)) but it's also worth considering adding alternative access to settings - such as on the shutdown menu - and be prepared to offer support to users who have deleted the link.

***Quick links*** - [Readme](../../../README.md) - [Getting Started](./Getting Started.md) - [Advanced Usage](../advanced/Advanced Usage.md)