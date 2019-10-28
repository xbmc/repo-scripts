info for skinners:

- if a song can be loved, you can use this visible condition to display the love button:
Window(Home).Property(LastFM.CanLove)

- add this onclick action to the love button:
RunScript(service.scrobbler.lastfm,action=LastFM.Love)
