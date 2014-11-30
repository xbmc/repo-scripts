 INFO FOR SKINNERS
===================

cu.lrclyrics is based on the cu and lrc lyrics scripts.

credits to everyone who worked on these scripts before:
EnderW, Nuka1195, Taxigps, amet, ronie, yannrouillard


the script first tries to find synchronised (lrc) lyrics.
if no lrc lyrics are available, it will continue to search for unsynchronised lyrics.


depending on which options you've enabled, the script searches for lyrics in this order:
- embedded lrc lyrics
- lrc lyrics file
- minilyrics scraper
- ttplayer scraper
- alsong scraper
- baidu scraper
- gomaudio scraper
- lyrdb scraper
- embedded text lyrics
- text lyrics file
- lyricwiki scraper
- lyricsmode scraper
- lyricstime scraper
- darklyrics scraper


when the scripts downloads lyrics through one of the scrapers,
you can optionally save them to a file for future use.


properties for other addons:
Window(Home).Property(culrc.lyrics)  - shows the current lyrics, including timing info in case of lrc lyrics.
Window(Home).Property(culrc.source)  - source or scraper that was used to find the current lyrics.
Window(Home).Property(culrc.haslist) - will be 'true' if multiple lyrics are available, empty if not.
Window(Home).Property(culrc.running) - returns 'true' when the lyrics script is running, empty if not.

If you wish to retrieve lyrics for a specific track (Which is not currently playing) then you can use the
following properties:
Window(Home).Property(culrc.manual) - set to 'true' if manual retrieval is required
Window(Home).Property(culrc.artist) - set by the client to the required artist name
Window(Home).Property(culrc.track) - set by the client to the required track name

other addons may want to set the MusicPlayer.Property(do_not_analyze) to 'true'.
this will tell cu lrc lyrics to skip searching for embedded lyrics.
