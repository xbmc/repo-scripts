# Additional shortcuts to choose from

You may wish to provide additional shortcuts for the user to choose from. There are two methods that can be used for this, either using [Custom Groupings](./Custom groupings.md), or by specifying additional shortcuts in the skins [overrides.xml](./overrides.md) file.

`<shortcut label="[label]" type="[type]" grouping="[grouping]" thumbnail="[thumbnail]" icon="[icon]" condition="[Boolean condition]">[action]</shortcut>`

| Property | Optional | Description |
| :------: | :------: | ----------- |
| [label] | | The display name of the shortcut (can be a localised string) |
| [type] | | Indicated the type of shortcut to the user, e.g. "Movie" if this leads to an area of the movie library (can be a localised string) |
| [grouping] | Yes | The shortcut group this should appear within - see below |
| [thumbnail] | Yes | The thumbnail associated with the shortcut |
| [icon] | Yes | The icon associated with the shortcut |
| [Boolean condition] | Yes | Replace with a string that must evaluate to True for the shortcut to appear |
| [action] | | The action associated with this shortcut |

## [grouping]

Shortcut groupings within the management dialog are made up of several smaller groupings, to which you can add your own shortcuts with the grouping parameter. Available groups are:

 - common
 - commands 
 - video
 - videosources
 - music
 - musicsources
 - picturesources
 - pvr-tv
 - pvr-radio
 - playlist-video
 - playlist-audio
 - addon-program
 - addon-video
 - addon-audio
 - addon-image
 - favourite
 
If you do not specify a grouping, it will be added to the end of the common group.

***Quick links*** - [Readme](../../../README.md) - [Getting Started](../started/Getting Started.md) - [Advanced Usage](./Advanced Usage.md)