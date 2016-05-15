# Provide thumbnails

When using either button 306 or 311 in the [Management Dialog](../started/Management Dialog.md), you can provide a list of thumbnails the user can choose from for their shortcut by providing options in the skins [overrides.xml](./overrides.md) file.

`<thumbnail label="[label]">[path]</thumbnail>`

| Property | Optional | Description |
| :------: | :------: | ----------- |
| `[label]` | | The name displayed to the user in the select dialog |
| `[path]` | | The path to the image. No need to include full path if the thumbnail is included with your skin. |

If you want to provide a 'None' option, set the path to `::NONE::`. In this case you can omit the label if you wish, it will be set to "None" automatically. The item will appear at the top of the list.

## Default browse path

If using button 306 to let the user select the thumbnail, you can set the default path for browsing for a thumbnail with the following in your overrides.xml:-

`<thumbnailBrowseDefault>protocol://path/to/folder</thumbnailBrowseDefault>`

***Quick links*** - [Readme](../../../README.md) - [Getting Started](../started/Getting Started.md) - [Advanced Usage](./Advanced Usage.md)