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
---
**1.1.6**
- Added missing PVR windows to background monitor expression

**1.1.5**
- Fixed bug in actor_credits() where the current infoscreen item was not being removed from the 'More from X' actor credits widget if the infoscreen was for an episode, because it was expecting to find the TV show title in ListItem.Label and instead receiving the episode name, which wouldn't ever match.

**1.1.4**
- Fixed bug with infoscreen widgets not updating when navigating between infoscreens by ensuring director and genre properties update each time the infoscreen is loaded, even if the underlying list hasn't been scrolled
- Added season info monitoring
- Added a window property that is set to true while set progress is being calculated in get_collection_status()

**1.1.3**
- Fixed conditional that was preventing cropped clearlogo paths from being fetched for home widgets

**.1.1.2**
- Support for more edge case conversions of different image modes in clearlogo_cropper().
- Added method to service monitor to calculate watched percentage of sets and return as a property

**.1.1.1**
- Fixed bug in previous version causing dark cropped clearlogos to always be served in certain scenarios

**.1.1.0**
- Cropper automatically disabled if animation transitions are disabled in Copacetic skin.
- Clearlogo cropper will resize larger crops to 1600x620 max, this is 2x the Kodi standard clearlogo requirement https://kodi.wiki/view/Artwork_types#clearlogo
- SlideshowMonitor() will now check for cropped clearlogos or crop them if no cropped version present
- Additional error handling for images

**1.0.18**
- Added subtitle_limiter() script, which sets subtitles to the first stream in the desired language if it's available and then toggles between this subtitle stream and 'off'. If the preferred language stream is not available it will toggle through all available subtitles instead.

**1.0.17**
- Parse args for script actions to enable values with special characters to be properly escaped from Kodi using '"$INFO[ListItem.Title]"'

**1.0.16**
- Added tvchannels/radiochannels to background_slideshow()
- Error handling for clearlogos that aren't in a supported PIL mode https://github.com/realcopacetic/script.copacetic.helper/issues/3
- Added landscape to movieartwhitelist/tvshowartwhitelist recommended settings
- SlideshowMonitor class extended to accept custom paths to folders of images e.g. special://profile/backgrounds/ - it can now populate background slideshows sourced from library paths, playlists, plugin sources (e.g. themoviedbhelper) and folders
- Rebuilt wideget_move() to account for new widget settings

**1.0.15**
- Global search action to open keyboard and return value to relevant skin string.
- Minor error catching in play_all()

**1.0.14**
- Test fix for issue: IndexError: list index out of range https://github.com/realcopacetic/script.copacetic.helper/issues/5

**1.0.13**
- Player monitor captures Set ID for currently playing movie and passes to a window property for skin.copacetic to use for Now_Playing indicator on sets 

**1.0.12**
- Removed visualisation waveform setting from list of settings changed by SettingsMonitor

**1.0.11**
- Reordered addon.xml back to how it was before 1.0.9 due to removal of script.copacetic.helper as a plugin source selectable for widgets.
- Enhanced Slideshow_Monitor class so that it can now fetch fanarts from containers with plugin sources when they are available then use these fanarts in the custom background slideshow. In this way, you can use a custom path to populate a global custom fanart slideshow even without any content in your local library

**1.0.10**
- fanart_read() method added in 1.0.10 now triggers on services monitor initialise rather than the first time that the SlideShow monitor is run so it should display backgrounds slightly quicker

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