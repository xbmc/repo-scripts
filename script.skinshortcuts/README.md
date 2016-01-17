#Skin Shortcuts - 1.0.2

script.skinshortcuts was written with the intention of making user customizable shortcuts on the home page easier for skinners.


## What's New for Skinners

#### Version 1.0.2 - repo version

- Ability to match multiple values when setting a property in a template - [Read More](./resources/docs/advanced/Templates.md#set-a-property-based-on-the-value-of-a-main-menu-item)
- Ability to specify an 'onback' value for specific controls in management dialog - [Read More](./resources/docs/started/Management Dialog.md#custom-focus-on-back)

#### Version 1.0.0 - previous repo version

- Ability for users to install additional widget providers - [Read More on customising when this is available to users](./resources/docs/advanced/Managing widgets.md#default-widgets-from-skin-helper-service)
- Jarvis changes to music shortcuts - Please be aware that the shortcuts used to access various areas of the music library have changed. Skin Shortcuts will do its best to update any actions to the Jarvis version when the menu is built, but if this doesn't work (or if you are using the 'Just Select' method) the user may need to reset the action for these shortcuts.
- Skin playlists will now additionally be correctly loaded from subdirectories on all platforms
- Ability to set a fallback value for a custom property, used if the user hasn't selected a vlue - [Read More](./resources/docs/advanced/Custom shortcut properties.md#for-all-shortcuts-without-a-user-set-property)
- Ability to set widgetName property separately from label using `<shortcut />` elements in a custom groupings - [Read More](./resources/docs/advanced/Custom groupings.md#shortcut--element---widget) - and when defining available widgets [Read More](./resources/docs/advanced/Managing widgets.md#defining-available-widgets)
 
## With Thanks - Because their names don't deserve to be at the bottom :)

- Huge thanks to Ronie, whose code for listing plugins is used in this script
- Equally huge thanks to Ronie and 'Black, for their favourites code used in this script
- More huge thanks to BigNoid, for the ability to edit shortcuts, and Jeroen, for so many suggestions each of which just made the script better.
- The thanks remain absolutely huge to the translaters on Transifex for localising the script
- There almost isn't enough thanks for schimi2k for the icon and fanart
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
