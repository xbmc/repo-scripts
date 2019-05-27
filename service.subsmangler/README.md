Subtitles Mangler
=================

It is Kodi Media Center service plugin aiming to be a comprehensive subtitle helper.

It allows:
1) invoking subtitle search dialog at playback start taking into account local subtitle files availability
- recognizes if there are subtitle files already downloaded or not
- recognizes 'noautosubs' file (per directory) and '.noautosubs' extension (per file) whose presence prevents subtitle search dialog from opening. Allows to manage it from within UI
- tries to identify if video file includes internal forced subtitles matching preferred language

2) detecting if subtitle file was downloaded locally and perform conversion
- gives ability to customize subtitle font color (foreground) and its background color and transparency, which makes subtitles more easy to read
- support subtitle input formats: microDVD, SubRip, MPL2, Substation Alpha and TMP
- allows to filter subtitle contents based on various Regular Expression type criteria, which gives ability to remove unwanted texts, such as Hearing Impaired tags, advertisements, credits, etc.
- allows to increase subtitle display time to match at least minimum calculated time based on subtitle text length, taking into account start time of the next subtitle line
- allows to shrink subtitle display time to avoid overlapping the next subtitle line

3) detecting if video was removed from local storage and removing any related subtitle files


Note:
- As Kodi 18 (Leia) introduced native support for adding solid background to displayed subtitles and also because Substation Alpha type subtitles are scaled to fit within the bottom of the movie image (not the bottom of the physical screen), an option was added to allow subtitle conversion (filtering contents, correcting duration) without changing it to Substation Alpha format. In this case file is saved in SubRip format.
- Beginning with version 1.3.0 the file extension of subtitle output file was changed to .utf (instead of previous .ass) in order to distinguish converted subtitles from original ones. Substation Alpha format (.ass) is now supported as input format.
