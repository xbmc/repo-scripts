# Overriding labels

You can change the label of any available shortcut in the management dialog via the skins [overrides.xml](./overrides.md) file.

`<availableshortcutlabel action="[command]" type="[type]">[New Label]</availableshortcutlabel>`
	
| Property | Optional | Description |
| :------: | :------: | ----------- |
| `[command]` | | The command of the available shortcut whose label you are overriding |
| `[New Label]` | | The label you want to replace the default label with (can be a localised string) |
| `[type]` | Yes | The new label for the type of shortcut (displayed in select dialog as label2) |

***Quick links*** - [Readme](../../../README.md) - [Getting Started](../started/Getting Started.md) - [Advanced Usage](./Advanced Usage.md)