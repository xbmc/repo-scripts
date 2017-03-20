# Context Menu

**The context menu relies on additions to the Python api made in Krypton. It will not function on earlier versions.**

Rather than including all the controls directly within your management dialog, you can choose to make some available via the context menu. The context menu optoins are defined in [the skins overrides.xml file](../advanced/overrides.md), with all controls within a single `<contextmenu />` element.

## Choosing which control the context menu appears on

You can enable the context menu for a particular control by including the following within the `<contextmenu />` element:-

`<enableon>[control id]</enableon>`

where `[control id]` is one of the controls provided by the management dialog, or a custom-defined control.

To enable it for multiple controls, include the `<enableon />` element multiple times.

## Choosing controls for the context menu

Any default control or control id linked to a [custom shortcut property](./Custom shortcut properties.md) can be included in the context menu by including the following within the <contextmenu /> element:-

`<item control="[control id]" condition="[condition]">[label]</item>`

| Property | Optional | Description |
| :------: | :------: | ----------- |
| `[control id]` |  | The ID of any default of custom-defined control |
| `[condition]` | Yes | The visibility condition that must match for the item to be displayed in the context menu |
| `[label]` |  | The label that will be displayed in the context menu |

## Defaults

By default, Skin Shortcuts enabled the context menu for control 211 (the list of shortcuts the user has chosen), and makes control 313 (disable a shortcut) available.

Please note, however, that if you include the `<contextmenu />` element in your skins overrides, the scripts own defaults won't be loaded and so, if you want to replicate this behaviour, you need to define these behaviours yourself.

## Example

```<contextmenu>
	<!-- Enable context menu on controls 211, 303 and 304 -->
	<enableon>211</enableon>
	<enableon>303</enableon>
	<enableon>304</enableon>

	<!-- Add enable/disable controls -->
	<item control="313" condition="String.IsEqual(Container(211).ListItem.Property(skinshortcuts-disabled),False)">Disable</item>
	<item control="313" condition="String.IsEqual(Container(211).ListItem.Property(skinshortcuts-disabled),True)">Enable</item>
</contextmenu>```

***Quick links*** - [Readme](../../../README.md) - [Getting Started](../started/Getting Started.md) - [Advanced Usage](./Advanced Usage.md)