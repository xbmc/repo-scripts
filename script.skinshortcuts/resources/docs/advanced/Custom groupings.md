# Customise groupings of shortcuts

Groupings are the name given to how the shortcuts that are shown to the user when they select a shortcut or widget are arranged and grouped together.

Skin Shortcuts has three groupings in its overrides.xml file:-

#### `<flatgroupings>`

Used to describe how shortcuts are arranged when using list 111 to display shortcuts to the user.

#### `<groupings>`

Used to describe how shortcuts are arranged to the user when using GUI buttons 401 and 307, and with the ['Just Select' method](./Just Select.md)

#### `<widget-groupings>`

Used to describe how widgets are arranged to the user when using GUI button 312

## Customising the groups

You can include any of the above groupings in your scripts own [overrides.xml](./overrides.md) file to change how the shortcuts are presented when using your skin.

There are various `<content />` tags, which will show available shortcuts in that category, which you can rearrange between (or into new) `<node />` elements.

Note:- when customising `<widget-groupings />`, only the `<content />` tags that are present in Skin Shortcuts own implementation should be used, as others won't provide shortcuts than can be used as widgets.

#### `<shortcut />` element - non-widget

You can also add individual shortcuts directly into the groupings with a `<shortcut />` element

`<shortcut label="[label]" type="[type]" icon="[icon]">[action]</shortcut>`

| Property | Optional | Description |
| :------: | :-------: | ----------- |
| `[label]` | | The label that will be shown to the user, and set as the name of the shortcut |
| `[type]` | | The type of shortcut, this will be displayed to the user as label2 |
| `[icon]` | Yes | The icon of the shortcut |
| `[action]` | | The action for the shortcut

#### `<shortcut />` element - widget

`<shortcut label="[label]" type="[type]" icon="[icon]" widget="[widget]" widgetName="[widgetName]" widgetType="[widgetType]" widgetTarget="[widgetTarget]">[widgetPath]</shortcut>`

| Property | Optional | Description |
| :------: | :-------: | ----------- |
| `[label]` | | The label that will be shown to the user |
| `[type]` | Yes | The type of widget, this will be displayed to the user as label2 |
| `[icon]` | Yes | The icon that will be displayed to the user |
| `[widget]` | Yes | The value that will be set as the widget property |
| `[widgetName]` | Yes | THe value that will be set at the widgetName property. If ommitted, widgetName will be set to `[label]` |
| `[widgetType]` | Yes | The value that will be set as the widgetType property |
| `[widgetTarget]` | Yes | The value that will be set as the widgetTarget property |
| `[widgetPath]` |  | The value that will be set as the widgetPath property |

See [Managing widgets](./Managing widgets.md) for more details of the various widget properties.

## Custom Groupings

You can create entirely custom groupings in addition to the three below to customise how the shortcuts are displayed in particular situations.

To do so, create a new element in your overrides.xml, and name it [groupname]-groupings. You can then include any `<node />`, `<content />` and `<shortcut />` elements that you wish.

#### Displaying custom groupings - gui 401 or 307

Set the window property `custom-grouping` to the `[groupname]` you wish to display, then send a click to 401 or 307.

```
<onclick>SetProperty(custom-grouping,[groupname])</onclick>
<onclick>SendClick(401)</onclick>
```

#### Displaying custom groupings - 'Just Select' method

See ['Just Select' method](./Just Select.md)

## Notes

#### `<widget-groupings>`

The widget groupings are handled differently from all other groupings, in that they will not display any prompt to the user about what they want the shortcut they have chosen to do - for example, no prompt if they want to play or display a playlist. Instead, it will always default to displaying the shortcut.

***Quick links*** - [Readme](../../../README.md) - [Getting Started](../started/Getting Started.md) - [Advanced Usage](./Advanced Usage.md)