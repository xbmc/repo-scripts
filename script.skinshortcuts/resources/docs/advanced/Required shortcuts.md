# Required shortcuts

When using the script to provide the whole menu, you can specify shortcuts that are required for the skin to appear in the main menu. If there is no main menu item with the specified action, an additional shortcut will be created. Users will be unable to delete these shortcuts whilst using your skin.

These are specified in your skins [overrides.xml](./overrides.md) file.

`<requiredshortcut label="[label]" thumbnail="[thumbnail]" icon="[icon]">[action]</requiredshortcut>`

| Property | Optional | Description |
| :------: | :------: | ----------- |
| `[label]` | | The display name of the shortcut (can be a localised string) |
| `[thumbnail]` | Yes | The thumbnail associated with the shortcut |
| `[icon]` | Yes | The icon associated with the shortcut |
| `[action]` | The action associated with this shortcut |

## Notes

The type property will be set to the id of your skin (skin.name) to indicate that it is specific to the skin.

***Quick links*** - [Readme](../../../README.md) - [Getting Started](../started/Getting Started.md) - [Advanced Usage](./Advanced Usage.md)