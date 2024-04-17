# Copacetic Helper [![License](https://img.shields.io/badge/License-GPLv3-blue)](https://github.com/realcopacetic/script.copacetic.helper/blob/main/LICENSE.txt)

All code contained in this project is licensed under GPL 3.0.

### Credit
---
* __sualfred__ for [script.embuary.helper](https://github.com/sualfred/script.embuary.helper), which served as the basis for several parts of this addon. The script and service sections are completely rewritten/modified, but some of the code and structure of the plugin section remains a very simplified version of Sualfred's work. Credit included in each file where code remains.

* __Dodi Achmad on Unsplash__ for image used in addon [fanart.jpg](https://unsplash.com/photos/3qaojaP-6cE). Free for use under Unsplash licence.

### Special thanks
---
* __jurialmunkey__ for all the best-practice code examples from [plugin.video.themoviedb.helper](https://github.com/jurialmunkey/plugin.video.themoviedb.helper) and forum support.

### Changelog
**1.0.13**
- Player monitor captures Set ID for currently playing movie and passes to a window property for skin.copacetic to use for Now_Playing indicator on sets 

**1.0.12**
- Removed visualisation waveform setting from list of settings changed by SettingsMonitor

**1.0.11**
- Reordered addon.xml back to how it was before 1.0.9 due to removal of script.copacetic.helper as a plugin source selectable for widgets.
- Enhanced Slideshow_Monitor class so that it can now fetch fanarts from containers with plugin sources when they are available then use these fanarts in the custom background slideshow. In this way, you can use a custom path to populate a global custom fanart slideshow even without any content in your local library

**1.0.10**
- read_fanart() method added in 1.0.10 now triggers on services monitor initialise rather than the first time that the SlideShow monitor is run so it should display backgrounds slightly quicker

**1.0.10**
- Custom path for Global slideshows can now be refreshed on first entry or on change of path without needing Kodi to restart https://github.com/realcopacetic/script.copacetic.helper/issues/6
- Added new methods to SlideShow monitor class enabling the service monitor to save current global slideshow fanarts to XML on exit, then make these available during initialisation. The aim of this is to serve the last fanart URL from the previous session while new fanarts are being fetched by the slideshow monitor, which should minimise the black-screen delay on starting up Kodi on slower hardware while fanarts are fetched for the first time https://github.com/realcopacetic/script.copacetic.helper/issues/4

**1.0.9**
- Background slideshows from custom paths/playlists are now generated via the background fanart fetching service and available globally throughout the skin, via a window property. Previously this was done in-skin using a container so would not be available persistently across windows.
- Removed glitch in background slideshows causing them to fetch new fanarts too often
- Removed unnecessary conditions from background monitor
- Added toggle_addon action to script.
- Switched incorrect labels Enabled/Disabled for script enabler toggle function
- Reordered addon.xml extension points to update how addon is categorised in Kodi repository

**1.0.8**
- Push dbid of corresponding cropped clearlogo to window prop for comparison so cropped clearlogos only show on correct listitems.

**1.0.7**
- Add tvguide to SlideShowMonitor() whitelist

**1.0.6**
- Moved director/writer/studio/genre splitting to monitoring service

**1.0.5**
- Added script for easily re-ordering widgets in Copacetic settings screen

**1.0.4**
- Return dominant colour for home widgets when clearlogo cropper is active
- Added fanart multiart to backgtround slideshows

**1.0.3**
- Updated fanart.

**1.0.2**
- Fixes for errors flagged by Kodi Addon Checker workflow during submission process.

**1.0.1**
- Fix for an error when the label passessd to the function clean_filename() was not escaped properly. Now to avoid the issue, by default, if no label is provided, the function will pull the listitem label directly using xbmc.getInfoLabel('ListItem.Label')

**1.0.0** 
- Initial release.