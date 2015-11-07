#Skin Shortcuts - 0.6.6

script.skinshortcuts was written with the intention of making user customizable shortcuts on the home page easier for skinners.


## What's New for Skinners

#### Version 0.6.6 - repo version

- Ability to include multiple $SKINSHORTCUT[] elements and other text in an element when using templates
- Ability to assign menu item ID to a property when using templates
- New <content>addon-program-plugin</content> for groupings and related widget-selection support
- More options for setting a custom property - [Read More](./resources/docs/advanced/Custom shortcut properties.md#set-options)
- New 'Just Select Widget' method - [Read More](./resources/docs/advanced/Just Select.md#just-select-widgets)
- Behaviour change - skin will now ask users to edit widgetName after setting widget. [Read how to prevent](./resources/docs/advanced/Managing widgets.md#prevent-user-editing-widgetname)
- Ability to use a Management Dialog buttonID to set custom property. [Read More](./resources/docs/advanced/Custom shortcut properties.md#notes)
- Label change - GUI 308's label (32028) has changed from "Reset shortcuts" to "Restore shortcuts" to highlight additional functionality. [Read how to override](./resources/docs/started/Management Dialog.md#always-reset-shortcuts-with-gui-308)
- Remove requirement to include an `<action>` element and the `group=` attribute in a global action override.
- Behaviour change - when overriding actions, any action specified in the .DATA.xml file or by an additional shortcut will still by applied to the shortcut 
 
## With Thanks - Because their names don't deserve to be at the bottom :)

- Huge thanks to Ronie, whose code for listing plugins is used in this script
- Equally huge thanks to Ronie and 'Black, for their favourites code used in this script
- More huge thanks to BigNoid, for the ability to edit shortcuts, and Jeroen, for so many suggestions each of which just made the script better.
- The thanks remain absolutely huge to the translaters on Transifex for localising the script
- Everyone who has contributed even one idea or line of code
- And the biggest thanks of all to Annie and my family, for feature suggestions, testing and shouting at me when I broke things

## Where To Get Help

Though hopefully Skin Shortcuts will save you a lot of code in the long-run, it is a relatively complex script and so may take some time to get your head around.

To help, it includes a lot of documentation covering the various features of the script

* [What is Skin Shortcuts](./resources/docs/What is Skin Shortcuts.md)
* [Getting Started](./resources/docs/started/Getting Started.md)
* [Providing default shortcuts](./resources/docs/Providing default shortcuts.md)
* [Advanced usage topics](./resources/docs/advanced/Advanced Usage.md)
* [labelID and localisation](./resources/docs/labelID and Localisation.md)

It's highly recommended to take time to read through these documents before you begin.

If you require any assistance post on the Kodi forum and I'll do my best to assist:

[http://forum.kodi.org/showthread.php?tid=178294](http://forum.kodi.org/showthread.php?tid=178294)

## Documentation for different versions

The documentation with Skin Shortcuts is generally updated as features are added or changed. Therefore, the docs on Git refer to the latest build, and will include details of features that are not yet on the repo.

If you are targetting the repo version of the script you can use the tags to browse the documentation for that particular release.
