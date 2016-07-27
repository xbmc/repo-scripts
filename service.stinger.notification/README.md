# Stinger scene notification

This add-on notifies you of stinger scenes in the current movie. It pops up a notification
when the credits roll (or at least towards the end). It uses tags to identify movies
that have a stinger, which can be automatically added by the [Universal Movie Scraper]
from [The Movie Database], as aftercreditsstinger and duringcreditsstinger.

If there are no chapters on your media file, the add-on searches for them on the
[ChapterDb]. If chapters are available, the notification pops up when the last chapter
starts, which is generally the credits, otherwise 10 (configurable) minutes before
the movie ends.

[Support and discussion thread] on the Kodi forums.

[ChapterDb]: http://www.chapterdb.org/
[Universal Movie Scraper]: http://forum.kodi.tv/showthread.php?tid=129821
[The Movie Database]: https://www.themoviedb.org/
[Support and discussion thread]: http://forum.kodi.tv/showthread.php?tid=254004

### Adding tags

It looks for the tags 'aftercreditsstinger' and 'duringcreditsstinger' in your Kodi library.
To add these tags to new movies automatically, use a movie scraper that can set tags
from The Movie Database. The Universal Movie Scraper can be configured with a setting.

If your existing movies don't already have these tags, you can avoid rescraping them
with a handy once-off option in the add-on settings under "Advanced", "Grab stinger
tags from TheMovieDB for all movies", which will run through your library and grab
these tags for all movies from The Movie Database. New movies should still be tagged
by the scraper as described above.

The tags can also be added with [nfo files], if that's your style.

[nfo files]: http://kodi.wiki/view/NFO_files/movies#Movie_tags

### Skinning

It has a simple skinnable window with 2 built in labels: `id="100"` for the stinger
type (During credits, After credits) and `id="101"` for the full message.

The window property **stinger** is set on the window **fullscreenvideo** when the
video starts. Possible values for **stinger** are `duringcreditsstinger`, `aftercreditsstinger`,
`duringcreditsstinger aftercreditsstinger` if the movie has both, and `None`. The
property is only set when a movie in the library is playing, and empty in all other
cases.

### Gotchas

Movies don't always start the last chapter when the credits begin rolling, so the
notification won't be timed right for a handful of movies.
