========================================================================
SKIN INJECTOR - README
========================================================================
ID: script.skin.injector
Author: Hitcher
Version: 0.0.1
License: GPL-2.0-only
========================================================================

OVERVIEW:
Skin Injector is a lightweight script designed to dynamically generate 
a Smart Playlist (.xsp) in the temporary folder and "inject" it into a 
skin list container.

This then allows for the use of all available ListItem labels for 
Movies, Episodes, and Music Videos in any window/dialog.

------------------------------------------------------------------------
SKIN IMPLEMENTATION:
------------------------------------------------------------------------

1. DEFINE THE PATH VARIABLE
Use a variable to manage the content path. This ensures the container 
is "force-cleared" while the script is running, preventing it from 
retaining old data (ghosting) and avoiding "Failed to read" errors 
during file I/O.

<variable name="InjectorPath">
    <value condition="String.IsEqual(Window(home).Property(FilterReady),true)">special://profile/addon_data/script.skin.injector/dynamic_filter.xsp</value>
    <value>videodb://movies/titles/?year=9999</value>
</variable>

2. SETUP THE LIST
Point your list container to the variable. Ensure target="videos" is set.

<control type="list" id="999">
    <content target="videos">$VAR[InjectorPath]</content>
</control>

3. TRIGGER THE SCRIPT
Use RunScript to pass the media type and metadata. It is recommended 
to clear the "FilterReady" property before calling to avoid "ghosting."

Example (Movies):
<onclick>ClearProperty(FilterReady,home)</onclick>
<onclick>RunScript(script.skin.injector, "movie", "$INFO[ListItem.Title]", "$INFO[ListItem.Year]")</onclick>

4. RETRIEVE THE DATA
Use the container ID (e.g., 999) to access all library labels in your 
layout.

Examples:
$INFO[Container(999).ListItem.Label]
$INFO[Container(999).ListItem.Rating]
$INFO[Container(999).ListItem.VideoResolution]

------------------------------------------------------------------------
SUPPORTED ARGUMENTS:
------------------------------------------------------------------------

- MOVIES:
  RunScript(script.skin.injector, "movie", "[Title]", "[Year]")

- TV EPISODES:
  RunScript(script.skin.injector, "episode", "[ShowTitle]", "[Season]", "[EpisodeTitle]")

- MUSIC VIDEOS:
  RunScript(script.skin.injector, "musicvideo", "[Artist]", "[Title]")

------------------------------------------------------------------------
TECHNICAL NOTES:
------------------------------------------------------------------------
- Pathing: The script writes to 'special://profile/addon_data/script.skin.injector/dynamic_filter.xsp'.
- Table Switching: The script automatically handles the switch between 
  movie_view, episode_view, and musicvideo_view.
- Sanitization: All strings are HTML-escaped; special characters like 
  '&' will not break the resulting XML.

------------------------------------------------------------------------
ATTRIBUTION:
------------------------------------------------------------------------
Icon created by graphicmall - Flaticon 
(https://flaticon.com)
========================================================================
