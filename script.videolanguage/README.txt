This script is designed to use in the video info dialog and sets properties for all audio and subtitle languages of a video file.

Add this to DialogVideoInfo.xml
<onload condition="System.HasAddon(script.videolanguage) + [Container.Content(movies) | Container.Content(episodes) | Container.Content(musicvideos)]">RunScript(script.videolanguage,movieid=$INFO[ListItem.DBID])</onload>

or run it in background by adding the following line to MyVideoNav.xml. If the script runs in background, you don't need to run it in DialogVideoInfo.xml.
<onload condition="System.HasAddon(script.videolanguage)">RunScript(script.videolanguage,background=True)</onload>

The following properties are available
Window(movieinformation).Property(AudioLanguage.%d)
Window(movieinformation).Property(AudioCodec.%d)
Window(movieinformation).Property(AudioChannels.%d)
Window(movieinformation).Property(SubtitleLanguage.%d)

Force the content type by adding type=movie, type=episode or type=musicvideo