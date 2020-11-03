[![GitHub release](https://img.shields.io/github/release/add-ons/service.iptv.manager.svg?include_prereleases)](https://github.com/add-ons/service.iptv.manager/releases)
[![Build Status](https://img.shields.io/github/workflow/status/add-ons/service.iptv.manager/CI/master)](https://github.com/add-ons/service.iptv.manager/actions?query=branch%3Amaster)
[![Codecov status](https://img.shields.io/codecov/c/github/add-ons/service.iptv.manager/master)](https://codecov.io/gh/add-ons/service.iptv.manager/branch/master)
[![License: GPLv3](https://img.shields.io/badge/License-GPLv3-yellow.svg)](https://opensource.org/licenses/GPL-3.0)
[![Contributors](https://img.shields.io/github/contributors/add-ons/service.iptv.manager.svg)](https://github.com/add-ons/service.iptv.manager/graphs/contributors)

# IPTV Manager
This Service Add-on allows supported IPTV Add-ons to integrates their Live TV and Radio Channels in the Kodi TV integration.
IPTV Manager will periodically poll those Add-ons for Channels and EPG data, and generate a new M3U playlist and
XMLTV file that the Kodi PVR Addon [IPTV Simple](https://github.com/kodi-pvr/pvr.iptvsimple) can use. IPTV Manager
doesn't require a backend like TVHeadend since it handles all the streams inside Kodi. This is also the only way 
(that we know of) to play DRM protected streams with the Kodi TV integration.

More information and documentation for developers can be found on our [Wiki page](https://github.com/add-ons/service.iptv.manager/wiki).

## Features
* Integrates Live TV Channels with EPG data in Kodi from supported IPTV Add-ons
* Allows playback of past and future programs directly from the EPG

## Screenshots
<table>
  <tr>
    <td><img src="resources/screenshot01.jpg" width=270></td>
    <td><img src="resources/screenshot02.jpg" width=270></td>
    <td><img src="resources/screenshot03.jpg" width=270></td>
  </tr>
  <tr>
    <td><img src="resources/screenshot04.png" width=270></td>
    <td><img src="resources/screenshot05.png" width=270></td>
    <td><img src="resources/screenshot06.png" width=270></td>
  </tr>
</table>

Skin: [Arctic: Zephyr 2](https://forum.kodi.tv/showthread.php?tid=339791)
