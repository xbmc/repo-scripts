# Custom shortcut properties

You can use Skin Shortcuts to add a custom property to any shortcut. You can either set a property to a specific value, or allow the user to choose from a range of values.

## Set to a specific value

To set the property to a specific value, include button 404 in your [Management Dialog](../started/Management Dialog.md). Set the window property `customProperty` to the name of the property you want to set, `customValue` to the value of the property, and send a click to 404.

```
<onclick>SetProperty(customProperty,myCustomProperty)</onclick>
<onclick>SetProperty(customValue,theValueIWantItSetTo)</onclick>
<onclick>SendClick(404)</onclick>
```

## Allow user to choose value

#### Define available options

The available options the user will be able to choose from are defined in the skins [overrides.xml](./overrides.md) file.

`<property property="[Property]" label="[label]" icon="[icon]" condition="[condition]">[Property Value]</property>`

| Property | Optional | Description |
| :------: | :------: | ----------- |
| `[Property]` | | The property of the shortcut that will be set |
| `[label]` | Yes | The label that will be displayed to the user. If ommitted, the [Property value] will be used. |
| `[icon]` | Yes | The icon that will be displayed to the user |
| `[condition]` | Yes | A Kodi boolean condition that must evaluate to True for the property to be shown to the user |
| `[Property Value]` | | The value that will be set to the property |

#### Set options

You can optionally use a `<propertySettings />` element in your overrides.xml to adjust how the dialog will be called and displayed when the user chooses the custom property:-

`<propertySettings property="[Property]" buttonID="[buttonID]" requires="[requires]" templateonly="[True/False]" title="[Dialog title]" showNone="[True/False]" imageBrowse="[True/False]" />`

| Property | Optional | Description |
| :------: | :------: | ----------- |
| `[Property]` | | The property of the shortcut that will be set |
| `[buttonID]` | Yes | The ID of the button that will be used to set this property. If ommitted, you must set the window property 'chooseProperty' to `[Property]` and send a click to 404 |
| `[Requires]` | Yes | The name of another property that must be present in the shortcut for this property to be added to it |
| templateonly `[True/False]` | Yes | A boolean indicating whether a property is only used by templates. If True, the property will not be written to the shortcut in the includes file. Defaults to False. |
| `[Dialog title]` | Yes | The title of the dialog that will be shown to the user |
| showNone `[True/False]` | Yes | A boolean indicating whether a None option will be shown when the user is setting the property. Defaults to True. |
| imageBrowse `[True/False]` | Yes | A boolean indicating whether the user will be able to browse for an image or folder of images. Defaults to False. |

## Allow user to toggle a property

You can use a `<propertySettings />` element to define a button to toggle a given property between empty and "True"

`<propertySettings toggle="[Property]" buttonID="[buttonID]" requires="[requires]" templateonly="[True/False]" />`

| Property | Optional | Description |
| :------: | :------: | ----------- |
| `[Property]` | | The property of the shortcut that will be set |
| `[buttonID]` | Yes | The ID of the button that will be used to set this property. If ommitted, you must set the window property 'chooseProperty' to `[Property]` and send a click to 404 |
| `[Requires]` | Yes | The name of another property that must be present in the shortcut for this property to be added to it |
| `[True/False]` | Yes | A boolean indicating whether a property is only used by templates. If True, the property will not be written to the shortcut in the includes file. Defaults to False. |

You can then use `!IsEmpty(Container(211).ListItem.Property([Property])` as the `<selected />` value for a radio button in your management dialog.

## Set defaults

#### For a specific shortcut

You can set a shortcut to have a custom property by default with the propertydefault elements:-

`<propertydefault labelID="[LabelID]" group="[GroupName]" property="[Property]">[Property Value]</propertydefault>`
	
| Property | Optional | Description |
| :------: | :------: | ----------- |
| `[labelID]` | | The labelID you are providing a default for. |
| `[GroupName]` | Yes | The group that the labelID must be in, for example "movies". If omitted, the property will be apply to items in the main menu. |
| `[Property]` | | The property of the shortcut that will be set |
| `[Property Value]` | | The default value of the property |

These will be applied when the user first switches to your skin, or when they reset all shortcuts.

#### For all shortcuts without a user set property

You can set what value should be used for all shortcuts in a given group, if the user hasn't selected an alternative value:-

`<propertyfallback group="[GroupName]"" property="[Property]" attribute="[Attribute]" value="[Value]">[Property Value]</propertyfallback>`

| Property | Optional | Description |
| :------: | :------: | ----------- |
| `[GroupName]` | Yes | The group that the labelID must be in, for example "movies". If omitted, the property will be apply to items in the main menu. |
| `[Property]` | | The property of the shortcut that will be set |
| `[Attribute]` | Yes | If property is conditional, the attribute that will be matched against |
| `[Value]` | Yes | If property is conditional, the value that the attribute specified must have |
| `[Property Value]` | | The default value of the property |

You can include multiple `<propertyfallback />` elements for a specific property. The property will be set to the first one matched.

When using conditions, both the [Attribute] and [Value] must be specified. So, if you wanted to match the fallback to a shortcut with the attribute 'widgetType' set to the value 'movies':-

`<propertyfallback property="customProperty" attribute="widgetType" value="movies">Fallback Value</propertyfallback>`

Note:- This will be applied to all shortcuts when the menu is built, and will show in the management dialog, but the fallback property will not be saved as part of the skins .properties file.

## Let user choose a property

If using a `<propertySettings />` you can define the ID of the button that will allow the user to select the custom property. Just include a button with the ID you specify in your Management Dialog or include it in the [context menu](./Context menu.md).

Otherwise, you need to include button 404 in your Management Dialog, then set the window property `chooseProperty` to the `[Property]` you want to set, and send a click to 404.

## Notes

When using `<propertySettings />`, it's possible to set the `buttonID` to the same ID as one of the inbuilt control ID's used by Skin Shortcuts Management Dialog.

In this case, the property select dialog will be shown to the user after the normal action associated with that button has completed. However, the property select dialog will *not* show if the user cancels, or if they select a 'None' option provided by the default control.

***Quick links*** - [Readme](../../../README.md) - [Getting Started](../started/Getting Started.md) - [Advanced Usage](./Advanced Usage.md)