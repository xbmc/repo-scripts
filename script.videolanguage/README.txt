This script is designed to use in the video info dialog and sets properties for all audio and subtitle languages of a video file.

Add this to DialogVideoInfo.xml
<onload condition="System.HasAddon(script.videolanguage) + [Container.Content(movies) | Container.Content(episodes)]">RunScript(script.videolanguage,movieid=$INFO[ListItem.DBID])</onload>

The following properties are available
Window(movieinformation).Property(AudioLanguage.%d)
Window(movieinformation).Property(AudioCodec.%d)
Window(movieinformation).Property(AudioChannels.%d)
Window(movieinformation).Property(SubtitleLanguage.%d)

