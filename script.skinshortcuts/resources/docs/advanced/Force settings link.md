# Force settings link

When using Skin Shortcuts to provide the whole main menu, it is possible for the user to delete any shortcut to settings. This could leave them in a position where they are unable to further edit the menu to put it back.

It is recommended that you provide an alternative access to settings somewhere in your skin, such as the power menu. However, if you do not, then it is possible to force the script to add a Settings option to the end of the main menu, if there is no other link to settings in the menu structure by including the following in  the skins [overrides.xml](./overrides.md) file.

`<forcesettings>True</forcesettings>`

Please note, this will cause the script to create a shortcut with the action `ActivateWindow(Settings)` if none exists. It doesn't look for any other settings area links. It also doesn't take into account any overrides or visibility conditions that may be attached to a shortcut.

***Quick links*** - [Readme](../../../README.md) - [Getting Started](../started/Getting Started.md) - [Advanced Usage](./Advanced Usage.md)