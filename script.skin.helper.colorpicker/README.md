# Skin Helper Service Color Picker
### script.skin.helper.colorpicker
### A Color picker to be used by Kodi skins

Usage: see below

## Help needed with maintaining !
I am very busy currently so I do not have a lot of time to work on this project or watch the forums.
Be aware that this is a community driven project, so feel free to submit PR's yourself to improve the code and/or help others with support on the forums etc. If you're willing to really participate in the development, please contact me so I can give you write access to the repo. I do my best to maintain the project every once in a while, when I have some spare time left.
Thanks for understanding!


## Usage instructions

```
RunScript(script.skin.helper.colorpicker,skinstring=XXX)
```
This command will open the color picker of the script. After the user selected a color, the color will be stored in the skin string. 


Required parameter:
skinstring: Skin String inwhich the value of the color (ARGB) will be stored.

In your skin you can just use the skin string to color a control, example: <textcolor>$INFO[Skin.String(defaultLabelColor)]</textcolor>

####Notes:


1) If you want to display the name of the selected color, add a prefix .name to your skin string.

For example: <label>Default color for labels: $INFO[Skin.String(defaultLabelColor.name)]</label>

2) If you want to customize the look and feel of the color picker window, 
make sure to include script-skin_helper_service-ColorPicker.xml in your skin and skin it to your needs.

3) If you want to specify the header title of the color picker, 
make sure to include a label with ID 1 in the XML and add the header= parameter when you launch the script.

For example: RunScript(script.skin.helper.colorpicker,skinstring=MySkinString,header=Set the OSD Foreground Color)

4) By default the colorpicker will provide a list of available colors.
If you want to provide that list yourself, create a file "colors.xml" in skin\extras\colors\colors.xml
See the default colors file in the script's location, subfolder resources\colors




##### Set a skinshortcuts property with the color
If you want to set a Window(home) Property instead of a skin settings:

RunScript(script.skin.helper.colorpicker,winproperty=XXX)

If you want to use the color picker to store the color in a shortcut-property from the skinshortcuts script, 
include a button in your script-skinshortcuts.xml with this onclick-action:

RunScript(script.skin.helper.colorpicker,shortcutproperty=XXX)


##### Multiple color palettes
The color picker supports having multiple color palettes in your colors.xml.
The structure of your colors.xml file will then be layered, like this:

```xml
<colors>
    <palette name="mypalette1">
        <color name="color1">ffffffff</color>
    </palette>
</colors>
```

If you do not create the palette sublevel in your colors.xml, the script will just display all <color> tags.

If you have specified multiple palettes you can use a button with ID 3030 to switch between color palettes.

Also it is possible to launch the color picker with a specific palette, in that case supply the palette= parameter when you open the picker, for example:

```
RunScript(script.skin.helper.colorpicker,skinstring=MySkinString,palette=mypalette1)
```
________________________________________________________________________________________________________
