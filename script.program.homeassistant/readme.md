**HAKA!**

This is an unofficial Home Assistant Kodi Addon (HAKA!). The addon allows users with a Home Assistant installation to browse their Home Assistant entities (such as lights, switches and sensors) in a Kodi directory structure. Depending on the type of device actions are possible such as toggling lights, switches or start a robotic vacuum.

![HAKA! Main menu](https://raw.githubusercontent.com/LaTrappe/HAKA/main/screenshots/screenshot-01.jpg)

Prerequisites:
- Home Assistant 2021.2.1 or higher (older versions have a different API)
- Kodi Leia / Kodi Matrix


**Installation**

1. Download the zip file ([Kodi Leia](https://github.com/LaTrappe/HAKA/raw/main/script.program.homeassistant_1.1.0_leia.zip) / [Kodi Matrix](https://github.com/LaTrappe/HAKA/raw/main/script.program.homeassistant_1.1.0_matrix.zip))
2. In Home Assistant navigate to your profile (bottom icon in the side-menu).

3. Scroll down and generate a long life token (long live the tokens!).

4. Write down the token / carve it in a stone / memorize / use a carrier pigeon and send it to yourself or.... just copy the token.

5. Launch Kodi >> Add-ons >> Get More >> .. >> Install from zip file

6. Enter your Home Assistant IP and port (i.e. https://myfancypansyhainstallation.duckdns.org:8123)

7. Enter the token obtained in step four (don't forget to release the pigeon if you used one)

8. Set up the domains you would like to browse from your couch. 

Enjoy!

**Features**

The following domains are supported:
- Automations (toggle)
- Climate (toggle)
- Group (toggle) 
- Light (toggle)
- Persons (no action)
- Scene (turn on)
- Script (turn on)
- Sensor (no action)
- Switch (toggle)
- Vacuum (start, stop, return to base, locate)

**HAKA! Favorites**

Add home assistant entities in a favorites folder which can be added to Kodi main menu in form of tiles, widget or whatever you want to name them. See the example of HAKA! favorites when using the Embuary skin below.

![HAKA! Favourites in Embuary](https://raw.githubusercontent.com/LaTrappe/HAKA/main/screenshots/screenshot-04.jpg)

**Change log**

Version 1.1.0 (2021-02-21)
- HAKA! Favorites section added (add items via context menu)
- Extra sensor icons and sensor attributes as label
- Persons domain added
- Navigate to settings from within addon menu
- Sort items by friendly name by default
- Fixed issue: Items in Kodi main menu keep refreshing
- Fixed issue: Not ascii characters give errors when generating label

Version 1.0.1 (2020-10-23)
- Debug logging added

Version 1.0.0 (2020-10-22)
- First release!
