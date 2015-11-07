# Automatic Visibility Conditions

Skin Shortcuts will automatically add visibility conditions to shortcuts in the users menu so that they will only be visible if they are actually usable - for example, movie shortcuts will only appear in the user has movies in their library.

## List of visibility conditions

#### Library shortcuts

| Shortcut | Visibility condition |
| :------: | -------------------- |
| Library nodes | The visibility condition specified by the node |
| `ActivateWindow(weather)` | `!IsEmpty(Weather.Plugin)` |
| `ActivateWindow(Videos,Movie*)` | `Library.HasContent(Movies)` |
| `ActivateWindow(Videos,TVShow*)` | `Library.HasContent(TVShows)` |
| `ActivateWindow(videos,RecentlyAddedEpisodes*)` | `Library.HasContent(TVShows)` |
| `ActivateWindow(Videos,MusicVideo*)` | `Library.HasContent(MusicVideos)` |
| `ActivateWindow(MusicLibrary,MusicVideo*)` | `Library.HasContent(MusicVideos)` |
| `ActivateWindow(Videos,RecentlyAddedMusicVideos*)` | `Library.HasContent(MusicVideos)` |
| `ActivateWindow(MusicLibrary,*)` | `Library.HasContent(Music)` |
| `xbmc.playdvd()` | `System.HasMediaDVD` |
| `ActivateWindow(tv*)` | `PVR.HasTVChannels` |
| `ActivateWindow(radio*)` | `PVR.HasRadioChannels` |

#### Power option shortcuts

| Shortcut | Visibility condition |
| :------: | -------------------- |
| `quit()` | `System.ShowExitButton` |
| `powerdown()` | `System.CanPowerDown` |
| `alarmclock(shutdowntimer,shutdown())` | `!System.HasAlarm(shutdowntimer) + [System.CanPowerDown | System.CanSuspend | System.CanHibernate]` |
| `cancelalarm(shutdowntimer)` | `System.HasAlarm(shutdowntimer)` |
| `suspend()` | `System.CanSuspend` |
| `hibernate()` | `System.CanHibernate` |
| `reset()` | `System.CanReboot` |
| `system.logoff` | `[System.HasLoginScreen | IntegerGreaterThan(System.ProfileCount,1)] + System.Loggedon` |
| `mastermode` | `System.HasLocks` |
| `inhibitidleshutdown(true)` | `System.HasShutdown +!System.IsInhibit` |
| `inhibitidleshutdown(false)` | `System.HasShutdown + System.IsInhibit` |

#### Other shortcuts

| Shortcut | Visibility condition |
| :------: | -------------------- |
| `xbmc.playdvd()` | `System.HasMediaDVD` |


## Notes

#### Music Add-ons

An exception is made for shortcuts to music addons (`ActivateWindow(MusicLibrary,addons*)`), and no visibility condition will be added to this shortcut.

***Quick links*** - [Readme](../../../README.md) - [Getting Started](./Getting Started.md) - [Advanced Usage](../advanced/Advanced Usage.md)