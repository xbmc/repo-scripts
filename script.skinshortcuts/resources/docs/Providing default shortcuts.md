# Providing default shortcuts

By default, new menus (or reset menus) will be set to the defaults that are included with Skin Shortcuts, which are based on the default menus of Confluence. You may wish to include your own defaults with your skin.

## Location of defaults

Your defaults should go into a shortcuts folder in the root folder of your skin

## Format of defaults

Defaults are stored in a `[menuidentifier].DATA.xml` file

```
<?xml version='1.0' encoding='UTF-8'?>
<shortcuts>
	<shortcut>
		<label>Label of shortcut, can be localised string</label>
		<label2>Type of shortcut, can be localised string</label2>
		<icon>The default icon to use for the shortcut</icon>
		<thumb>The default thumbnail to use for the shortcut (optional)</thumb>
		<action>The default action of the shortcut</action>
		<visible>Visibility condition for the shortcut (optional)</visible>
		<defaultID>The defaultID of the menu item</defaultID>
	</shortcut>
</shortcuts>
```

## Naming of the files

The file for the main menu defaults should be `mainmenu.DATA.xml`. For submenu's, it should be `[labelID].DATA.xml`. See [LabelID and localisation](./labelID and Localisation.md) for details of what the labelID will be set to.

## Notes

#### Linking to skin-provided playlist

If you want to include a default which links to a playlist you include with your skin, ensure you use the special protocol (e.g. special://skin/) as the URI to it.

Skin Shortcuts will then replace this with a localised version, so that the shortcut will continue to work even if the user switches to another skin that supports the script.

#### Library nodes

Skin Shortcuts fully supports library nodes, so you should ensure that any defaults you provide use library node links.

For example, a link to movie titles should be:

`<action>ActivateWindow(10025,videodb://movies/titles/,return)</action>`
	
rather than

`<action>ActivateWindow(10025,MovieTitles,return)</action>`

***Quick links*** - [Readme](../../README.md) - [Getting Started](./started/Getting Started.md) - [Advanced Usage](./advanced/Advanced Usage.md)