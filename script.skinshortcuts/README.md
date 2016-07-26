#Skin Shortcuts - 1.0.10

script.skinshortcuts was written with the intention of making user customizable shortcuts on the home page easier for skinners.


## What's New for Skinners

#### Version 1.0.10 - repo version

- Ability to move controls from management dialog to context menu (Krypton only) - [Read More](./resources/docs/advanced/Context menu.md)
- Ability to disable menu items via GUI 313 - Please note this control is made available by default on the context menu - [Read More](./resources/docs/started/Management Dialog.md)
- Default icons for all available shortcuts in the Common, Commands and Settings available shortcut groupings - [Read More](./resources/docs/advanced/Overriding icons.md)
- Behaviour change: When using mode=single, only the main menu (and corresponding submenu's) will be added to the allmenus include - additional groups that are being built will no longer be added
- Please be aware of the removal of deprecated window names in Krypton. The script will attempt to update VideoLibrary and MusicLibrary to Videos and Music respectively, but you should ensure that any default shortcuts you provide with your skin are up to date as this behaviour may change in the future.

#### Version 1.0.8 - previous version

- Ability to set additional properties of menu items from outside of the management dialog - [Read More](./resources/docs/advanced/External editing.md#change-properties-of-menu-items)
- Skinner can now set that their skin should not use the users shared menu - [Read More](./resources/docs/started/Getting Started.md#shared-menu)
- backgroundbrowse override can now be used to specify whether only a single or multi image should be selected - [Read More](./resources/docs/advanced/Managing backgrounds.md#let-the-user-browse-for-a-background-image)
- Ability to add a 'None' option when using GUI 311 to select thumbnail - [Read More](./resources/docs/advanced/Provide thumbnails.md)
- Ability to override an action based on its automatic visibility condition - [Read More](./resources/docs/advanced/Overriding an action.md#run-a-different-command-based-on-automatic-visibility-condition)
- Ability to define a control ID to toggle a custom property - [Read More](./resources/docs/advanced/Custom shortcut properties.md#allow-user-to-toggle-a-property)
- Build option to not build `skinshortcuts-group-[name]` includes - [Read More](./resources/docs/started/Getting Started.md#don't-build-individual-groups)
- Template improvements
 - Match multiple properties to a single value - [Read More](./resources/docs/advanced/Templates.md#set-a-property-based-on-multiple-elements)
 - Property groups shared between templates - [Read More](./resources/docs/advanced/Templates.md#property-groups)
 - New submenuOther templates - [Read More](./resources/docs/advanced/Templates.md#types-of-templates)
 - Get value from Python - [Read More](./resources/docs/advanced/Templates.md#get-value-from-python)
- Plugin-based widgets selected via the GUI 312 method will now have a reload parameter added to them automatically. This means that they will update after media has been played. (Requires Skin Helper Service)
 
## With Thanks - Because their names don't deserve to be at the bottom :)

- Huge thanks to Ronie, whose code for listing plugins is used in this script
- Equally huge thanks to Ronie and 'Black, for their favourites code used in this script
- More huge thanks to BigNoid, for the ability to edit shortcuts, and Jeroen, for so many suggestions each of which just made the script better.
- The thanks remain absolutely huge to the translaters on Transifex for localising the script
- There almost isn't enough thanks for schimi2k for the icon and fanart
- Everyone who has contributed even one idea or line of code
- And the biggest thanks of all to Annie and my family, for feature suggestions, testing and shouting at me when I broke things

## Where To Get Help - Users

[End User FAQ](./resources/docs/FAQ.md)

If you have issues with using the script, your first port of call should be the End User FAQ. If your query isn't listed there, then the next place to ask for help is the [Kodi forum for the skin that you are using](http://forum.kodi.tv/forumdisplay.php?fid=67). There are a lot of very knowledgeable skinners and users who will be able to answer most questions.

When a question comes up that no-one in the thread can answer, the skinner may direct you to the [Skin Shortcuts thread](http://forum.kodi.tv/showthread.php?tid=178294) in the skin development for further help.

If you experience an error with the script, you are welcome to ask for help directly in the Skin Shortcuts thread in the skin development forum. However, we _require_ a [debug log](http://kodi.wiki/view/Debug_log).

Please note that this thread is primarily aimed at skin developers - if you haven't already asked in the revelant skins forum, included a debug log or are asking a question related to [banned add-ons](http://kodi.wiki/view/Official:Forum_rules/Banned_add-ons), you are not likely to recieve a warm welcome.

## Where To Get Help - Skinners

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
