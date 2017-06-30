# Managing backgrounds

Skin Shortcuts can be used to let the user select a background for a menu item. This can either be a background style, a background image, or a folder containing multiple images. The script adds properties to the menu item which the skinner can then use to display the background the user has selected.

## Defining backgrounds

You can provide a number of default background options in your [overrides.xml](./overrides.md) file.

`<background label="[Label]" icon="[Icon]" condition="[Condition]">[backgroundID]</background>`

| Property | Optional | Description |
| :------: | :------: | ----------- |
| `[Label]` | | The display name of the background (can be a localised string) |
| `[Icon]` | Yes | The icon that will be displayed in the management dialogs Background Select. If omitted, the `backgroundID` will be used if it is the path to a valid image |
| `[Condition]` | Yes | Boolean condition that must be true for the background to show in the management dialogs Background Select (evaluated when management dialog is loaded) |
| `[backgroundID]` | | A string you use to identify the background |

#### Let the user browse for a background image

You can let the user browse for either a single image or a multi-image, by including the following in the overrides.xml file:-

`<backgroundBrowse default="[path]">[True/Single/Multi]</backgroundBrowse>`

| Property | Optional | Description |
| :------: | :------: | ----------- |
| `[path]` | Yes | The path that will be displayed by default in the select dialog |
| `[True]` | | The user can browse for single or multiple images |
| `[Single]` | | The user can only browse for a single image |
| `[Multi]` | | The user can only browse for multi-images |

#### Let the user select a playlist for the background

To let the user select a playlist for a background, when setting the `[Label]` for the `<background />` element, include the string "::PLAYLIST::"

Skin Shortcuts will create multiple copies of this entry, with "::PLAYLIST::" replaced by the name of the users defined playlists.

## Defining background defaults

You may wish to set a default background to one or more menu items. These will be applied when a user first switches to your skin, or when they reset all menu items. This is done in your skins overrides.xml file.

`<backgrounddefault labelID="[LabelID]" group="[GroupName]">[backgroundID]</backgrounddefault>`

| Property | Optional | Description |
| :------: | :------: | ----------- |
| [labelID] | | The labelID you are providing a default for. (Replace with defaultID="[defaultID]" to set default based on this property instead) |
| [GroupName] | Yes | The group that the labelID must be in, for example "movies". If omitted, the default will apply to items in the main menu. |
| [backgroundID] | | A string you use to identify the background |

## Let the user select a background

To let the user select a background, include button 310 in your [Management Dialog](../started/Management Dialog.md).

## Set submenu background to mainmenu background

It may be advantageous for your submenu items to have the same background property as your main menu items. In which case, include `&amp;options=clonebackgrounds` in your build command. If you want to clone *all* the properties from the main menu item, use `&amp;options=cloneproperties`

Multiple options can be separated with a pipe - | - symbol.

## Displaying the background

Skin Shortcuts sets the property `background` to the menu item. This will either be set to the `[backgroundID]` you have set for the background the user has selected, or to the path of the image the user has selected if you have enabled the browse option.

If the user has selected a playlist, then the menu item will also have the additional property `backgroundPlaylist`, which contains the path of the playlist.

If you have defined background styles, you can use a StringCompare to decide whether to display a particular background.

If you are using direct background images, you can use the `background` property as the `<imagepath />` in a multi-image control.

***Quick links*** - [Readme](../../../README.md) - [Getting Started](../started/Getting Started.md) - [Advanced Usage](./Advanced Usage.md)