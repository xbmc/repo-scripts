# Overring icons

Skin Shortcuts provides default icons for all available shortcuts, with a fallback on "DefaultShortcut.png". However, you may prefer to define specific icons for the shortcuts.

This function is implemented entirely though the skins [overrides.xml](./overrides.md) file.

## Overriding image for a specific labelID

To override all shortcuts with a particular labelID, use the following in your overrides.xml:-

`<icon labelID="[labelID]" group="[GroupName]" grouping="[Grouping]">[New image]</icon>`

| Property | Optional | Description |
| :------: | :------: | ----------- |
| `[labelID]` |  | The labelID of the shortcut whose icon you wish to override |
| `[GroupName]` | Yes | The group that must be being editing for the override to apply. If ommitted, will apply to groups |
| `[Grouping]` | Yes | The `<content />` grouping that the icon must be in to be overrided. If ommitted, will be applied to all groupings. See [Custom groupings](./Custom groupings.md) for details |
| `[New image]` | | The replacement image |

For details of the labelID system that Skin Shortcut employs, and the likely values of this property, see here.

## Overriding all instances of a particular image

To override all instances of a particular image, use the following in your overrides.xml:-

`<icon image="[Original image]" group="[GroupName]" grouping="[Grouping]">[New image]</icon>`

| Property | Optional | Description |
| :------: | :------: | ----------- |
| `[Original image]` |  | The image you are overriding |
| `[GroupName]` | Yes | The group that must be being editing for the override to apply. If ommitted, will apply to groups |
| `[content]` | Yes | The `<content />` grouping that the icon must be in to be overrided. If ommitted, will be applied to all groupings. See [Custom groupings](./Custom groupings.md) for details. |
| `[New image]` |  | The replacement image |

## Icons versus Thumbnails

In most instances, Skin Shortcuts only allows skinners to set or override the icon image, whilst it provides functions so that the user can set the thumbnail image.

Whilst there are a few reasons for this whithin the script, the primary reason is that the thumb image overrides the icon image in most cases, meaning that any image that the user selects will have precedence over anything the skin sets.

One area where this becomes more complicated is with certain add-ons and favourites, which may use the thumbnail property for the default images. If you wish to override these images, you need to tell the script to use the thumbnail images as the (overridable) icon image with the following in you overrides.xml:-

`<useDefaultThumbAsIcon>True</useDefaultThumbAsIcon>`

They can then be overriden as normal.

## Default icons

Where possible, Skin Shortcuts sets the icon of available shortcuts to an appropriate [Default Icon]() - [Read More]().

Where there is no default icon, Skin Shortcuts sets it to a generic value so that the skinner can override the icon and provide a specific one for their skin. Please see the code for details - gui.py, the functions 'common', 'more' and 'settings'

***Quick links*** - [Readme](../../../README.md) - [Getting Started](../started/Getting Started.md) - [Advanced Usage](./Advanced Usage.md)