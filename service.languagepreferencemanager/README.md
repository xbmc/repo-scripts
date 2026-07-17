service.LanguagePreferenceManager
=================================

A manager for audio and subtitle preferences
============================================

This addon provides an easy way to set your preferred audio streams and subtitle languages in Kodi.

You can select which audio tracks and subtitles to automatically activate based on your priorities, and define simple conditional rules like "if audio is xxx then activate subtitles yyy" via drop/down lists.
More advanced custom rules can be defined as well (see changelog for more on the syntax. Note that custom rules always take precedence over others).

Special language codes None(non) for subtitles and Any(any) for audio can be used in Conditional Subtitles Rules, normal or custom.
For example "fre:non>any:fre>any:eng" will disable subtitles if audio is French (except if a french forced subtitles track exists) and activate french subtitles for any other audio language. If these are not available it will try the same finding english subtitles.

Rules are re-evaluated and applied whenever you switch audio while watching (from v0.1.5).

It's now also possible to force ignore "Signs and Songs" subtitles in preferences evaluations, based on name, and/or any other subtitle tracks based on predefined keywords.
For example, most dual audio Anime provides english and japanese audio and two english subtitles. Dialogue subtitles with all the dialogue to go with the japanese audio and Song/Sign subtitles which only translate song lyrics and signs you see on screen to be used with the english audio stream. Previously the addon just picked the first subtitles with the correct language which weren't always the correct ones.

An option allows you to store forced preferences per Movie / TVshow (from v1.0.6). When you manually change audio and/or subtitle tracks during play, this will be saved as an overriding preference, taking precedence over all other rules for the next opening of the Movie, or the next episode of the TVshow (Thx a lot to SgtJalau!)

Special Thanks
==============

- @ace20022 and @scott967 for initial development

- @cyberden for making this addon ready for Kodi Matrix

- @fpatrick for fixing an issue with language mapping

- @KnappeGEIL for ideas how to ignore 'Signs and Songs' subtitles

- @SgtJalau for the complete feature to store specific/overriding preferences per Movie / TVshow
