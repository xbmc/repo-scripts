# Managing widgets

Skin Shortcuts can be used to let the user select from a wide variety of options - library sources and nodes, playlists, add-on nodes and custom options - to use as a widget for a menu item. The script adds properties to the menu item which the skinner can then use to display the widget the user has selected.

## Defining available widgets

By default, Skin Shortcuts provides a large array of available widgets which can be displayed using the list-filling methods of Kodi. You can define any further widgets in your skins [overrides.xml](./overrides.md) file.

`<widget label="[label]" icon="[icon]" condition="[Condition]" name="name" type="[type]" path="[path]" target="[target]">[widgetID]</widget>`

| Property | Optional | Description |
| :------: | :------: | ----------- |
| `[label]` | | The display name of the widget, to be shown when choosing widgets (can be a localised string) |
| `[icon]` | Yes | An image provided by your skin to be used when selecting widgets |
| `[Condition]` | Yes | Boolean condition that must be true for the background to show in the management dialogs Background Select (evaluated when management dialog is loaded) | 
| `[name]` | Yes | The string that will be assigned to `<property name="widgetName">`. If ommitted, this will be set to the value of `[label]` |
| `[type]` | Yes | The string that will be assigned to `<property name="widgetType">` |
| `[path]` | Yes | The string that will be assigned to `<property name="widgetPath">` |
| `[target]` | Yes | The string that will be assigned to `<property name="widgetTarget">` |
| `[widgetID]` |  | The unique string you use to identify this widget |

If you are customising the [`<widget-groupings />` groupings](./Custom groupings.md), these will be displayed in `<content>widgets</content>`.

## Defining widget defaults

You may wish to define a default widget to one or more menu items. These will be applied when a user first switches to your skin, or when they reset all menu items. This is done in your skins [overrides.xml](./overrides.md) file.

#### To a widget you have defined

To set a default to a widget you have defined, the `labelID` property is used to decide which menu item to set the default to the `widgetID` you specify.

`<widgetdefault labelID="[labelID]" group="[GroupName]">[widgetID]</widgetdefault>`

| Property | Optional | Description |
| :------: | :------: | ----------- |
| `[labelID]` | | The labelID you are setting the default for. (Replace with defaultID="[defaultID]" to set default based on this property instead) |
| `[GroupName]` | Yes | The group that the labelID must be in, for example "movies". If omitted, the property will apply to items in the main menu. |
| `[widgetID]` | | A string you use to identify this widget |

#### To any other widget

To set the default to any other widget, you must directly specify the properties you want added to the menu item with the `labelID` you specify.

`<widgetdefaultnode labelID="[labelID]" group="[GroupName]" label="[label]" type="[type]" path="[path]" target="[target]">[widget]</widgetdefaultnode>`

| Property | Optional | Description |
| :------: | :------: | ----------- |
| `[labelID]` | | The labelID you are setting the default for. (Replace with defaultID="[defaultID]" to set default based on this property instead) |
| `[GroupName]` | Yes | The group that the labelID must be in, for example "movies". If omitted, the property will apply to items in the main menu. |
| `[label]` | Yes | The display name of the widget (can be a localised string) that will be assigned to `<property name="widgetName">` |
| `[type]` | Yes | The string that will be assigned to `<property name="widgetType">` |
| `[path]` | Yes | The string that will be assigned to `<property name="widgetPath">` |
| `[target]` | Yes | The string that will be assigned to `<property name="widgetContent">` |
| `[widget]` | Yes | The string that will be assigned to `<property name="widget">` |

Be careful when setting defaults to library nodes - if the user has customised their nodes, the node may not exist on their system. Only skin-provided playlists should be set as defaults.

## Let the user select a widget

To let the user select a widget, include button 312 in your [Management Dialog](../started/Management Dialog.md).

You can also use the [Just Select](./Just Select.md#just-select-widgets) method to let the user select a widget and save its properties to skin strings.

#### Let the user select additional widgets

You may wish to let the user have more than one widget per menu item. In this case, set the window property `widgetID` to a unique identifier for your additional widget, then send a click to 312.

All widget properties for the additional widget will be suffixed with `.[widgetID]`, where `[widgetID]` is the value you set the window property to.

```
<onclick>SetProperty(widgetID,myWidgetIdentifier)</onclick>
<onclick>SendClick(312)</onclick>
```

## Set submenu widget to mainmenu widget

It may be advantageous for your submenu items to have the same widget properties as your main menu items. In which case, include `&amp;options=clonewidgets` in your build command. Please note, this will only clone the default widget, not any additional widgets you define.

If you want to clone *all* the properties from the main menu item, use `&amp;options=cloneproperties`

Multiple options can be separated with a pipe - | - symbol.

## Prevent user editing widgetName

By default, when using gui 312 to select a widget, Skin Shortcuts will show a keyboard dialog after the widget has been selected so that the user can edit the widgetName property.

If your skin doesn't show the widgetName property, you can disable this function by including the following in the skins [overrides.xml](./overrides.md) file:-

`<widgetRename>False</widgetRename>`

## Returned properties

For every widget that is selected, five properties will be added to the menu item. For widgets you have defined, or for defaults set via `<widgetdefaultnode />`, they will be the values you have defined.

All other widgets will return a widgetTarget property, which is designed to be used in the `target` element of a lists content tag. Other properties returned are:-

#### Library nodes

* `widget` - Library.
* `widgetName` - The name of the library node
* `widgetType` - Either 'video' or 'audio', or the content type specified in the nodes xml file
* `widgetPath` - The path to the selected node

#### Library sources

* `widget` - Source
* `widgetName` - The name of the library source
* `widgetType` - Either 'video', 'audio' or 'picture'
* `widgetPath` - The path to the selected source

#### Playlists

* `widget` - Playlist
* `widgetName` - The name of the playlist
* `widgetType` - The content type specified by the `playlist`
* `widgetPath` - The path to the playlist

#### Add-ons

* `widget` - Addon
* `widgetName` - The name of the add-on + the selected node (if available)
* `widgetType` - Either 'video', 'audio', 'picture' or 'program', or a best-guess at the type of content provided
* `widgetPath` - The path to the selected node

## Displaying the widgets

The five properties returned are designed to be enough for the skin to display the widget to the user. The widgets that Skin Shortcuts returns by default are intended to be used in the `<content />` tag of a list control, with other properties being used to decide what layout to use.

For example, the list used to display movie content may look like this:-

```
<control type="list">
	<include>widgetListPositioning</include>
	<visible>StringCompare(Container(9000).ListItem.Property(widgetType),movies)</visible>
	<itemlayout>
		<control type="image">
			<include>widgetPosterLayout</include>
			<texture>$INFO[ListItem.Art(poster)]</texture>
		</control>
	</itemlayout>
	<focusedlayout>
		<control type="image">
			<include>widgetPosterFocusedLayout</include>
			<texture>$INFO[ListItem.Art(poster)]</texture>
		</control>
	</focusedlayout>
	<content target="$INFO[Container(9000).ListItem.Property(widgetTarget)]">$INFO[Container(9000).ListItem.Property(widgetPath)]</content>
</control>
```

## Notes

#### Updating from previous widget implementaton

When upgrading from the previous Skin Shortcuts implementation (gui button 309), due to the additional properties that the new method returns, there is no upgrade path implemented. This means users will need to reset their widgets.

#### Default Widgets from Skin Helper Service

Skin Shortcuts own widgets groupings provides a 'Default Widgets' node (or the option to install the 'Default Widgets' node) which is powered by the Skin Helper Service, and lets the user choose from widgets provided by the Skin Helper Service itself, the Library Data Provider script, the Extended Info script and the Smart(ish) Widgets script.

To allow the user the chance to install aditional widget providers when browsing the 'Default Widgets', Skin Shortcuts enables the 'Get More...' button of the select dialog and manages installation of the additional widget providers. If you are customising how the widgets presented by Skin Helper Service are displayed, you may wish to remove this link. This is done by including the following in the skins [overrides.xml](./overrides.md) file:-

`<defaultwidgetsGetMore>False</defaultwidgetsGetMore>`

Additionally, when customising the widget groupings, you can enable the button for any node by including the attribute installWidget with the value True:-

`<node label="My widgets" installWidget="True">`

***Quick links*** - [Readme](../../../README.md) - [Getting Started](../started/Getting Started.md) - [Advanced Usage](./Advanced Usage.md)
