# Audio Profiles
Audio Profiles is a Kodi addon to help you easily switch between certain audio and video settings in Kodi.  Version 1.2 is the last version available for Kodi 17 and earlier. Version 1.42 or later is required for proper functioning on Kodi 18 or later.

## Features
*  save up to four different profiles that include the settings from System/Audio, System/Display (optional), Player/Videos (optional), and the Kodi volume.
*  send an HDMI-CEC command when a profile is activated (Toggle State, Standby, or Wakeup)
*  switch between profiles using different keymaps for each profile
*  rotate through profiles using a single keymap
*  select a profile using a pop up dialog box
*  option to show a dialog box to select an audio profile any time Kodi starts playing a media file
*  option to automatically select a profile based on media playing
*  option to load a profile when Kodi starts

## How to use this addon

### Configuration
By default two of the four available profiles are enabled and named Digital (profile 1) and Analog (profile 2). From the settings (see below for details on the settings) you can rename the profiles and configure the other settings.

### Saving Profiles
Audio Profiles saves the options from a handful of areas within the Kodi settings.  Those are:
*  System/Audio
*  System/Display (always saved, only changed on profile change if enabled in settings)
*  Player/Videos (always saved, only changed on profile change if enabled in settings)
*  Kodi system volume (always saved, only changed on profile change if enabled in settings)

Once you have configured those areas they way you want, go to the Audio Profiles addon and run it.  A dialog box will pop up asking you to select a profile in which to save the settings.  After saving the settings, make the changes you want to the Kodi settings, and run the addon again to save to another profile.  You may save up to four profiles.  If you ever want to make changes to a profile, load it (see usage below on how to change profiles), make your changes, and then run the addon to select the profile you want to update.

### Switching Profiles Using Keymaps
You can assign keys and remote buttons in Kodi using keymaps.  For more information on keymaps (including how to create them and where to store them), please see [the Kodi wiki page on keymaps](https://kodi.wiki/view/Keymap).  You assign a key to run a particular Kodi function that will either select a profile, pop up a dialog box for you to pick, or rotate through your profiles.  You don't need to have a keymap for every option, just the ones you want to use.  Here's an example of all those options for reference where each action is mapped to a function key:

```xml
    <keymap>
      <global>
        <keyboard>
          <F1>RunScript(script.audio.profiles,1)</F1>      <!-- switches to profile 1 -->
          <F2>RunScript(script.audio.profiles,2)</F2>      <!-- switches to profile 2 -->
          <F3>RunScript(script.audio.profiles,3)</F3>      <!-- switches to profile 3 -->
          <F4>RunScript(script.audio.profiles,4)</F4>      <!-- switches to profile 4 -->
          <F5>RunScript(script.audio.profiles,popup)</F5>  <!-- displays a dialog for you to pick a profile -->
          <F6>RunScript(script.audio.profiles,0)</F6>      <!-- rotates through the profiles -->
        </keyboard>
      </global>
    </keymap>
```

You will need to restart Kodi for the new keymaps to be active.

## Addon settings

### Profiles
**Profile 1:** (default True)<br />
Toggle this option to turn profile 1 on or off.  Profile 2 is on by default.<br />
*Name of Profile 1:* (default Digital)<br />
The name for profile 1 (shown in the popup menus and notifications)<br />
*Send HDMI-CEC command when profile activated:* (default None)<br />
If set to something other than None, sends the selected HDMI-CEC command when profile 1 is activated (Toggle State, Standby, or Wakeup)

**Profile 2:** (default True)<br />
Toggle this option to turn profile 2 on or off.  Profile 2 is on by default.<br />
*Name of Profile 2:* (default Analog)<br />
The name for profile 2 (shown in the popup menus and notifications)<br />
*Send HDMI-CEC command when profile activated:* (default None)<br />
If set to something other than None, sends the selected HDMI-CEC command when profile 2 is activated (Toggle State, Standby, or Wakeup)

**Profile 3:** (default False)<br />
Toggle this option to turn profile 3 on or off.  Profile 3 is off by default.<br />
*Name of Profile 3:* (default Headphones)<br />
The name for profile 3 (shown in the popup menus and notifications)<br />
*Send HDMI-CEC command when profile activated:* (default None)<br />
If set to something other than None, sends the selected HDMI-CEC command when profile 3 is activated (Toggle State, Standby, or Wakeup)

**Profile 4:** (default False)<br />
Toggle this option to turn profile 4 on or off.  Profile 4 is off by default.<br />
*Name of Profile 4:* (default HDMI)<br />
The name for profile 4 (shown in the popup menus and notifications)<br />
*Send HDMI-CEC command when profile activated:* (default None)<br />
If set to something other than None, sends the selected HDMI-CEC command when profile 4 is activated (Toggle State, Standby, or Wakeup)

### Settings
**Include volume level** (default False)<br />
if activated, all profiles will save and change the Kodi system volume level when profiles are activated.

**Include video player settings** (default False)<br />
If activated, all profiles will save and change the settings in the Kodi settings area Player/Videos.

**Include display settings** (default False)<br />
If active, all profiles will save and change the settings in the Kodi settings area System/Display.

**Show audio stream select menu on start playing** (default False)<br />
If activated, any time Kodi starts playing any media file a dialog box will popup so you can select the profile you want to use.<br>
*Auto close select menu* (default False)<br>
If activated, the menu will disappear after a certain amount of time (see next setting below). Please note that if you stop playing media, the dialog box will close immediately.<br />
*Delay before close* (default 10 seconds)<br>
If the auto close option is activated, Kodi will wait this many seconds before closing the dialog box automatically.  You may select between 5 and 30 seconds.

### Notifications
**Notifications:** (default True)<br />
By default, any time a profile is changed Kodi will display a notification indicating which profile just became active. Turn this off to disable that behavior.

**Enable debug logging** (default False)<br />
When enabled, if you have Kodi logging set to DEBUG you will get a very verbose set of information in your log file. You should only need to activate this when troubleshooting issues.

## Getting help
If you need assistance using Audio Profiles, please see the support thread on the Kodi forums at <https://forum.kodi.tv/showthread.php?tid=353852>.

## Beta Testing
If you are interested in beta testing new versions of this add on (or just like being on the bleeding edge of up to date), you can install beta versions (Leia or later, there will be no more updates for earlier versions) from my addon beta repository - either [for Leia](https://github.com/pkscout/repository.beta.pkscout/raw/helix/repository.beta.pkscout-1.1.1.zip) or [for Matrix](https://github.com/pkscout/repository.beta.pkscout/raw/matrix/repository.beta.pkscout-1.1.2.zip) (these are zip downloads). You can also monitor the support thread, as links to particular beta releases will be available there as well.




