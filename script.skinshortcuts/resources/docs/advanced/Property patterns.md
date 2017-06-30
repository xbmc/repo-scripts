# Custom shortcut property patterns

You can define custom properties patterns in the skins [overrides.xml](./overrides.md) file. Its variables are then filled with real values during include XML building. As opposed to regular custom properties, patterns can't be modified from skin so they aren't saved as custom configuration.

## Getting properties from shortcuts

You can use any element or property as part of your custom property pattern, with the format `::NAME::`.

For example, the following shortcut:-

```
<item id="1">
	<label>$LOCALIZE[10002]</label>
	<icon>DefaultPicture.png</icon>
	<property name="labelID">pictures</property>
	<property name="defaultID">pictures</property>
	<onclick>ActivateWindow(Pictures)</onclick>
	...
</item>
```

Has the following variable available (case insensitive):-

* `::LABEL::`
* `::ICON::`
* `::LABELID::`
* `::DEFAULTID::`
* `::ONCLICK::`

## Creating a property pattern

`<propertypattern labelID="[LabelID]" group="[GroupName]" property="[PropertyName]">[PropertyPattern]</propertypattern>`
	
| Property | Optional | Description |
| :------: | :------: | ----------- |
| [LabelID] | Yes | The labelID of item you are providing a pattern for. If ommited, pattern is used for all items in group. |
| [GroupName] | Yes | The group you are providing a pattern for. |
| [PropertyName] | | The string used to identify the property |
| [PropertyPattern] | | The pattern for the property |

The `[PropertyPattern]` is a string with one or more `::NAME::` elements within it.

## Example

```
<propertypattern group="mainmenu" property="exampleProperty">$INFO[Window(Home).Property(::DEFAULTID::)]</propertypattern>
<propertypattern labelID="pictures" group="mainmenu" property="exampleProperty">$INFO[Window(Home).Property(DefaultID-::DEFAULTID::)]</propertypattern>
```

As result all items in mainmenu will have property "exampleProperty" filled with first pattern, only pictures will be filled with second pattern.

```
<item id="1">
	<label>$LOCALIZE[10002]</label>
	<icon>DefaultPicture.png</icon>
	<property name="labelID">pictures</property>
	<property name="defaultID">pictures</property>
	<property name="exampleProperty">$INFO[Window(Home).Property(DefaultID-pictures)]</property>
	...
</item>
<item id="2">
	<label>$LOCALIZE[10005]</label>
	<icon>DefaultMusicAlbums.png</icon>
	<property name="labelID">music</property>
	<property name="defaultID">music</property>
	<property name="exampleProperty">$INFO[Window(Home).Property(music)]</property>
	...
</item>
...
```

***Quick links*** - [Readme](../../../README.md) - [Getting Started](../started/Getting Started.md) - [Advanced Usage](./Advanced Usage.md)