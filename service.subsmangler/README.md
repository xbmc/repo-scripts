Subtitles Mangler
=================

It is Kodi Media Center service plugin aiming to be a comprehensive subtitle helper.

It allows:
1) invoking subtitle search dialog at playback start taking into account local subtitle files availability
- recognizes if there are subtitle files already downloaded or not
- recognizes 'noautosubs' file (per directory) and '.noautosubs' extension (per file) whose presence prevents subtitle search dialog from opening
- tries to identify if video file includes internal forced subtitles matching preferred language

2) detecting if subtitle file was downloaded locally and perform conversion
- gives ability to customize subtitle font color (foreground) and its background color and transparency, which makes subtitles more easy to read
- support subtitles input formats: microDVD, SubRip, MPL2 and TMP
- allows to filter subtitle contents based on various Regular Expression type criteria, which gives ability to remove unwanted texts, such as Hearing Impaired tags, advertisements, credits, etc.
- allows to increase subtitle display time to match at least minimum calculated time based on subtitle text length, taking into account start time of the next subtitle line

3) detecting if video was removed from local storage and removing any related subtitle files