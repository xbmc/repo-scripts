[![GitHub release](https://img.shields.io/github/release/im85288/service.upnext.svg)](https://github.com/im85288/service.upnext/releases)
[![CI](https://github.com/im85288/service.upnext/workflows/CI/badge.svg)](https://github.com/im85288/service.upnext/actions?query=workflow:CI)
[![Codecov status](https://img.shields.io/codecov/c/github/im85288/service.upnext/master)](https://codecov.io/gh/im85288/service.upnext/branch/master)
[![License: GPLv3](https://img.shields.io/badge/License-GPLv2-yellow.svg)](https://opensource.org/licenses/GPL-2.0)
[![Contributors](https://img.shields.io/github/contributors/im85288/service.upnext.svg)](https://github.com/im85288/service.upnext/graphs/contributors)

# Up Next - Proposes to play the next episode automatically

This Kodi add-on shows a Netflix-style notification for watching the next episode. After a few automatic iterations it asks the user if he is still there watching.

A lot of existing add-ons already integrate with this service out-of-the-box.

## Settings
The add-on has various settings to fine-tune the experience, however the default settings should be fine for most.

  * Simple or fancy mode (defaults to fancy mode, but a more simple interface is possible)
  * The notification time can be adjusted (defaults to 30 seconds before the end)
  * The default action can be configured, i.e. should it advance to the next episode (default) when the user does not respond, or stop
  * The number of episodes to play automatically before asking the user if he is still there (defaults to 3 episodes)

> NOTE: The add-on settings are found in the Kodi add-ons section, in the *Services* category.

For [Addon Integration](https://github.com/im85288/service.upnext/wiki/Integration) and [Skinners](https://github.com/im85288/service.upnext/wiki/Skinners) see the [wiki](https://github.com/im85288/service.upnext/wiki)

## Releases

### v1.1.9 (2023-05-10)
- Fix handling of non-ASCII filenames for Kodi18 (@MoojMidge)
- Fix failing ci workflow (@MoojMidge)
- Update Swedish translation (@Sopor)
- Explicitly set sonarcloud coverage path (@MoojMidge)
- Fix error when kodi is not playing video any longer (@AnonTester)

### v1.1.8 (2022-09-13)
- Never ask if Still Watching? if playedInARow is 0 (@MoojMidge)
- Still Watching? checks number of plays not number+1 (@MoojMidge)

### v1.1.7 (2022-09-03)
- Update check for filename of multi-part episodes (@MoojMidge)
- Check for physical disc or disc image being played (@MoojMidge)
- Translation update to Russian (@ArtyIF)
- Fix CI workflow (@MoojMidge)

### v1.1.6 (2022-03-07)
- Fix for missing mediatype video info with addon video content (@MoojMidge)
- Translation updates to Croatian, Japanese, Korean, Swedish and Finnish (@dsardelic, @Thunderbird2086, @Sopor, @Dis90)
- New translation for Taiwanese Mandarin (@JuenTingShie)
- Use onAVStarted instead of onPlayBackStarted (@MoojMidge)
- Fix for Kodi not using the video player/playlist to play videos (@MoojMidge)
- Fixes misalignment of system.time and endtime (@jojobrogess)

### v1.1.5 (2021-02-21)
- Fix playlists to work with non-library content (@MoojMidge)
- Fix to prevent unwanted playback when using playlist queueing method (@MoojMidge)
- New translation for Finnish (@Dis90)

### v1.1.4 (2020-12-03)
- Fix problem causing pop-up to not appear (@MoojMidge)
- Translation updates to Romanian, Russian and Spanish (@tmihai20, @vlmaksime, @roliverosc)

### v1.1.3 (2020-10-14)
- Enable customPlayTime by default (@dagwieers)
- Do not seek to the end before playing next episode (@dagwieers)
- Add Kodi v17 compatibility (@dagwieers)
- Fix logging on Kodi v19 (Matrix) after recent breakage (@MoojMidge)
- Enqueue the next episode in the playlist (@MoojMidge)
- Translation updates to German (@tweimer)

### v1.1.2 (2020-06-22)
- Small bugfix release (@im85288)
- Translation updates to Japanese and Korean (@Thunderbird2086)

### v1.1.1 (2020-06-21)
- Avoid conflict with external players (@BrutuZ)
- Restore "Ignore Playlist" option (@BrutuZ)
- Fix a known Kodi bug related to displaying hours (@Maven85)
- Improvements to endtime visualization (@dagwieers)
- New translations for Hindi and Romanian (@tahirdon, @tmihai20)
- Translation updates to Hungarian and Spanish (@frodo19, @roliverosc)

### v1.1.0 (2020-01-17)
- Add notification_offset for Netflix add-on (@CastagnaIT)
- Fix various runtime exceptions (@thebertster)
- Implement new settings (@dagwieers)
- Implement new developer mode (@dagwieers)
- Show current time and next endtime in notification (@dagwieers)
- New translations for Brazilian, Czech, Greek, Japanese, Korean (@mediabrasiltv, @svetlemodry, @Twilight0, @Thunderbird2086)
- New translations for Russian, Slovak, Spanish, Swedish (@vlmaksime, @matejmosko, @sagatxxx, @Sopor)
- Translation updates to Croatian, French, German, Hungarian, Italian, Polish (@arvvoid, @zecakeh, @tweimer, @frodo19, @EffeF, @notoco)

### v1.0.7 (2019-12-03)
- Add Up Next in the program add-on section (@dagwieers)
- Update add-on icon to use black background (@dagwieers)
- Fix 24-hour format based on Kodi setting (@dagwieers)
- New translations for Croatian (@arvvoid)
- Translation updates to French, Hungarian, Italian and Polish (@mediaminister, @frodo19, @EffeF, @notoco)

### v1.0.6 (2019-11-26)
- Implement base64 encoding to support newer AddonSignals (@dagwieers)
- Fixes to Python 3.5 support (@anxdpanic)
- Add SPDX identifier for license (@dagwieers)
- Translation updates to German (@tweimer)

### v1.0.5 (2019-11-19)
- Translation fixes (@dagwieers)

### v1.0.4 (2019-11-19)
- Automatic stop playing as option (@notoco)
- Fix exception when add-on is exited (@dagwieers)
- Fix playlist logic (@mediaminister)
- Add support for Python 3 and Kodi v19 (@mediaminister)
- Introduce "Close" button when configured in settings (@dagwieers)
- Add support for a Back-button action to dismiss Up Next pop-up (@dagwieers)
- Always reset state when playback finishes (@mediaminister)
- Various code improvements and fixes (@dagwieers, @mediaminister)
- New translations for Dutch (@dagwieers)
- Translation updates to German (@semool, @beatmasterRS)

### v1.0.3 (2019-07-30)
- Disable tracking for non episode (@angelblue05)

### v1.0.2 (2019-07-24)
- Add JSONRPC method (@angelblue05)
- Add priority to existing playlist (@angelblue05)
- Add endtime prop (@angelblue05)
- Remove enablePlaylist setting (@angelblue05)
