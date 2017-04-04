# script.skin.helper.skinbackup
a backup script for Kodi skins



## Skin backup feature
The script comes with a backup/restore feature. It supports backup of ALL skin settings including skin shortcuts (when script.skinshortcuts is also used). 

- Backup all settings to file
- Restore all settings from file
- Reset the skin to default settings (wipe all settings)

###Backup the skin settings (including preferences for skinshortcuts)
```
RunScript(script.skin.helper.skinbackup,action=backup)             
```

Optional parameter: filter
```
It is possible to apply a filter to the backup. In that case only skin settings containing a specific phrase will be back-upped.
Can be usefull if you want to use the backup function for something else in your skin.
To use the filter you have to add the filter= argument and supply one or more phrases (separated by |)
For example:
RunScript(script.skin.helper.skinbackup,action=backup,filter=color|view|font)    
The filter is not case sensitive
```

Optional parameter: promptfilename
```
If you want to prompt the user for the filename (instead of auto generating one), you can supply the promptfilename=true parameter to the script.
```

Optional parameter: silent
```
If you want to silently perform a backup, you can supply the silent= parameter with the full path to the zipfile that has to be created.
RunScript(script.skin.helper.skinbackup,action=backup,silent=mypath\backup.zip)    
```

###Restore the skin settings
```
RunScript(script.skin.helper.skinbackup,action=restore)             
```

Optional parameter: silent
```
If you want to silently restore a backup, you can supply the silent= parameter with the full path to the zipfile that has to be restored.
RunScript(script.skin.helper.skinbackup,action=restore,silent=mypath\backup.zip)    
```


###Reset the skin to defaults:
```
RunScript(script.skin.helper.skinbackup,action=reset)             

This will reset ALL skin settings.
Both the filter and silent arguments will also work with the reset feature.
```
________________________________________________________________________________________________________
________________________________________________________________________________________________________



## Color themes feature
The script comes with a color theme feature. Basically it's just a simplified version of the skin backup/restore feature but it only backs up the colorsettings. Color Themes has the following features:

- Present a list of skin provided color themes including screenshots.
- Let's the user save his custom settings to a color theme.
- Let's the user export his custom color theme to file.
- Let's the user import a custom color theme from file.

________________________________________________________________________________________________________


###Present the dialog with all available color themes:
```
RunScript(script.skin.helper.skinbackup,action=colorthemes)   

The user can pick a colortheme and apply that, create a new one etc.          
```

________________________________________________________________________________________________________



###Provide color themes with your skin
```
It is possible to deliver skin provided color themes. Those colorthemes should be stored in the skin's extras\skinthemes folder.
If you want to create one or more skinprovided color themes (for example the defaults):

- Create a folder "skinthemes" in your skin's "extras" folder. 
- Make all color modifications in your skin to represent the colortheme
- Hit the button to save your colortheme (createcolortheme command)
- Name it and select the correct screenshot
- On the filesystem navigate to Kodi userdata\addon_data\[YOURSKIN]\themes
- Copy both the themename.theme and the themename.jpg file to your above created skinthemes directory
- Do this action for every theme you want to include in your skin.
- It is possible to change the description of the theme, just open the .themes file in a texteditor. You can change both the THEMENAME and the DESCRIPTION values to your needs.
```

Instead of storing your skinthemes into a folder inside your skin structure, you can also choose to store all your skinthemes in a Kodi resource addon.

Example: https://github.com/marcelveldt/resource.skinthemes.titan

If the resource addon with your skinname is present, themes will be picked from that addon instead of the subfolder in your skin's extras directory.

________________________________________________________________________________________________________


###What settings are stored in the theme file ?
```
All Skin Settings settings that contain one of these words: color, opacity, texture.
Also the skin's theme will be saved (if any). So, to make sure the skin themes feature works properly you must be sure that all of your color-settings contain the word color. If any more words should be supported, please ask.
```

________________________________________________________________________________________________________



###Automatically set a color theme at day/night
```
You can have the script set a specified theme during day or night.
This will allow the user to have some more relaxing colors at night time and more fluid/bright during day time.

To enable this feature you must set the skin Bool SkinHelper.EnableDayNightThemes to true.

To setup the theme (and time) to use at day time:  XBMC.RunScript(script.skin.helper.skinbackup,action=ColorThemes,daynight=day)
To setup the theme (and time) to use at night time:  XBMC.RunScript(script.skin.helper.skinbackup,action=ColorThemes,daynight=night)

The script will auto set the correct theme at the specified times and fill these Skin Settings:
Skin.String(SkinHelper.ColorTheme.[day/night].label --> A formatted string of the selected theme and the time it will apply for day or night
Skin.String(SkinHelper.ColorTheme.[day/night].theme --> Only the name of the chosen theme
Skin.String(SkinHelper.ColorTheme.[day/night].time --> Only the time of the chosen theme
Skin.String(SkinHelper.ColorTheme.[day/night].file --> Only the filename of the chosen theme
SkinHelper.LastColorTheme --> This will always hold the name of the last chosen theme (also if this day/night mode is disabled)
```


Some example code to use:

```xml
<control type="radiobutton" id="15033">
    <label>Enable day/night color themes</label>
    <onclick>Skin.ToggleSetting(SkinHelper.EnableDayNightThemes)</onclick>
    <selected>Skin.HasSetting(SkinHelper.EnableDayNightThemes)</selected>
</control>

<control type="button" id="15034">
    <label>Theme to use at day time: $INFO[Skin.String(SkinHelper.ColorTheme.Day)]</label>
    <onclick>XBMC.RunScript(script.skin.helper.skinbackup,action=ColorThemes,daynight=day)</onclick>
    <visible>Skin.HasSetting(SkinHelper.EnableDayNightThemes)</visible>
</control>
<control type="button" id="15035">
    <label>Theme to use at night time: $INFO[Skin.String(SkinHelper.ColorTheme.Night)]</label>
    <onclick>XBMC.RunScript(script.skin.helper.skinbackup,action=ColorThemes,daynight=night)</onclick>
    <visible>Skin.HasSetting(SkinHelper.EnableDayNightThemes)</visible>
</control>
```

________________________________________________________________________________________________________
________________________________________________________________________________________________________

