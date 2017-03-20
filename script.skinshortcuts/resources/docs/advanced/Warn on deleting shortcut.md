# Warn on deleting shortcut

You may wish to warn the user before deleting a given shortcut and give them the chance to cancel. This can be useful, for example, for links to settings or for specific functions used by your skin.

You can do this by providing the following element in the skins [overrides.xml](./overrides.md) file.

`<warn heading="[heading]" message="[message]">[Action]</warn>`

| Property | Optional | Description |
| :------: | :------: | ----------- |
| `[heading]` | | The heading of the Yes/No dialog that will be shown to the user (can be a localised string) |
| `[message]` | | The message in the Yes/No dialog that will be shown to the user (can be a localised string) |
| `[action]` | | The action of the existing shortcut that will trigger this message when the user tries to delete/replace it, or edit its action |

***Quick links*** - [Readme](../../../README.md) - [Getting Started](../started/Getting Started.md) - [Advanced Usage](./Advanced Usage.md)