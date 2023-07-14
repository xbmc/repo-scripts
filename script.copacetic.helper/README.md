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