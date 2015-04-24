List of possible ExtendedInfo script calls.
All calls can also be done by using a plugin path.

Example:
<content>plugin://script.extendedinfo?info=discography&amp;&amp;artistname=INSERT_ARTIST_NAME_HERE</content>
- keep Attention to the parameter separators ("&amp;&amp;")


##Rotten Tomatoes

Run:
RunScript(script.extendedinfo,info=intheaters)          --> InTheatersMovies.%d.xxx
RunScript(script.extendedinfo,info=comingsoon)          --> ComingSoonMovies.%d.xxx
RunScript(script.extendedinfo,info=opening)             --> Opening.%d.xxx
RunScript(script.extendedinfo,info=boxoffice)           --> BoxOffice.%d.xxx
RunScript(script.extendedinfo,info=toprentals)          --> TopRentals.%d.xxx
RunScript(script.extendedinfo,info=currentdvdreleases)  --> CurrentDVDs.%d.xxx
RunScript(script.extendedinfo,info=newdvdreleases)      --> NewDVDs.%d.xxx
RunScript(script.extendedinfo,info=upcomingdvds)        --> UpcomingDVDs.%d.xxx

Available Properties:

'Title':        Movie Title
'Art(poster)':  Movie Poster
'imdbid':       IMDB ID
'Duration':     Movie Duration
'Year':         Release Year
'Premiered':    Release Date
'mpaa':         MPAA Rating
'Rating':       Audience Rating (0-10)
'Plot':         Movie Plot


##The MovieDB

Run:

RunScript(script.extendedinfo,info=incinemas)           --> InCinemasMovies.%d
RunScript(script.extendedinfo,info=upcoming)            --> UpcomingMovies.%d
RunScript(script.extendedinfo,info=popularmovies)       --> PopularMovies.%d
RunScript(script.extendedinfo,info=topratedmovies)      --> TopRatedMovies.%d
RunScript(script.extendedinfo,info=similarmovies)       --> SimilarMovies.%d
-- required additional parameters: dbid=
RunScript(script.extendedinfo,info=set)                 --> MovieSetItems.%d
- fetches a list of movies from the same Set
-- required additional parameters: dbid=
RunScript(script.extendedinfo,info=directormovies)      --> DirectorMovies.%d
-- required additional parameters: director=
RunScript(script.extendedinfo,info=writermovies)        --> WriterMovies.%d
-- required additional parameters: writer=
RunScript(script.extendedinfo,info=studio)              --> StudioInfo.%d
- fetches a list of movies from the same studio
-- required additional parameters: studio=


Available Properties:

'Art(fanart)':      Movie Fanart
'Art(poster)':      Movie Poster
'Title':            Movie Title
'OriginalTitle':    Movie OriginalTitle
'ID':               TheMovieDB ID
'Rating':           Movie Rating (0-10)
'Votes':            Vote Count for Rating
'Year':             Release Year
'Premiered':        Release Date


Run:

RunScript(script.extendedinfo,info=populartvshows)      --> PopularTVShows.%d
RunScript(script.extendedinfo,info=topratedtvshows)     --> TopRatedTVShows.%d
RunScript(script.extendedinfo,info=onairtvshows)        --> OnAirTVShows.%d
RunScript(script.extendedinfo,info=airingtodaytvshows)  --> AiringTodayTVShows.%d

Available Properties:

'Title':            TVShow Title
'ID':               TVShow MovieDB ID
'OriginalTitle':    TVShow OriginalTitle
'Rating':           TVShow Rating
'Votes':            Number of Votes for Rating
'Premiered':        TV Show First Air Date
'Art(poster)':      TVShow Poster
'Art(fanart)':      TVShow Fanart


##Trakt.tv

Run:
RunScript(script.extendedinfo,info=trendingmovies)  --> TrendingMovies.%d
RunScript(script.extendedinfo,info=similarmoviestrakt)     --> SimilarMovies.%d
-- required additional parameters: dbid= (database id) or id= (imdb id)

'Title'
'Plot'
'Tagline'
'Genre'
'Rating'
'mpaa'
'Year'
'Premiered'
'Runtime'
'Trailer'
'Art(poster)'
'Art(fanart)'


Run:

RunScript(script.extendedinfo,info=trendingshows)           --> TrendingShows.%d
RunScript(script.extendedinfo,info=similartvshowstrakt)     --> SimilarTVShows.%d
-- required additional parameters: dbid= (database id) or id= (tvdb id)

'TVShowTitle':      TVShow Title
'Duration':         Duration (?)
'Plot':             Plot
'ID':               ID
'Genre':            Genre
'Rating':           Rating
'mpaa':             mpaa
'Year':             Release Year
'Premiered':        First Air Date
'Status':           TVShow Status
'Studio':           TVShow Studio
'Country':          Production Country
'Votes':            Amount of Votes
'Watchers':         Amount of Watchers
'AirDay':           Day episode is aired
'AirShortTime':     Time episode is aired
'Art(poster)':      TVShow Poster
'Art(banner)':      TVShow Banner
'Art(fanart)':      TVShow Fanart


RunScript(script.extendedinfo,info=airingshows)         --> AiringShows.%d
RunScript(script.extendedinfo,info=premiereshows)       --> PremiereShows.%d

'Title':         Episode Title
'TVShowTitle':   TVShow Title
'Plot':          Episode Plot
'Genre':         TVShow Genre
'Runtime':       Episode Duration
'Year':          Episode Release Year
'Certification': TVShow Mpaa Rating
'Studio':        TVShow Studio
'Thumb':         Episode Thumb
'Art(poster)':   TVShow Poster
'Art(banner)':   TVShow Banner
'Art(fanart)':   TVShow Fanart


##TheAudioDB

RunScript(script.extendedinfo,info=discography)         --> Discography.%d
- fetches the artist discography (Last.FM)
-- required additional parameters: artistname=

'Label':           Album Title
'artist':          Album Artist
'mbid':            Album MBID
'id':              Album AudioDB ID
'Description':     Album Description
'Genre':           Album Genre
'Mood':            Album Mood
'Speed':           Album Speed
'Theme':           Album Theme
'Type':            Album Type
'thumb':           Album Thumb
'year':            Album Release Year
'Sales':           Album Sales


RunScript(script.extendedinfo,info=mostlovedtracks)         --> MostLovedTracks.%d
- fetches most loved tracks for the given artist (TheAudioDB)
-- required additional parameters: artistname=
RunScript(script.extendedinfo,info=albuminfo)               --> TrackInfo.%d
-- required additional parameters: id= ???

'Label':       Track Name
'Artist':      Artist Name
'mbid':        Track MBID
'Album':       Album Title
'Thumb':       Album Thumb
'Path':        Link to Youtube Video


RunScript(script.extendedinfo,info=artistdetails) ???



#LastFM

RunScript(script.extendedinfo,info=albumshouts)
- fetches twitter shouts for given album
-- required additional parameters: artistname=, albumname=
RunScript(script.extendedinfo,info=artistshouts)
- fetches twitter shouts for given artist
-- required additional parameters: artistname=

'comment':  Tweet Content
'author':   Tweet Author
'date':     Tweet Date


RunScript(script.extendedinfo,info=topartists)
- fetches a lists of the most popular artists
RunScript(script.extendedinfo,info=hypedartists)


'Title':        Artist Name
'mbid':         Artist MBID
'Thumb':        Artist Thumb
'Listeners':    actual Listeners


RunScript(script.extendedinfo,info=nearevents)       --> NearEvents.%d
-- optional parameters: lat=, lon=, location=, distance=, festivalsonly=, tag=

'date':         Event Date
'name':         Venue Name
'venue_id':     Venue ID
'event_id':     Event ID
'street':       Venue Street
'eventname':    Event Title
'website':      Event Website
'description':  Event description
'postalcode':   Venue PostalCode
'city':         Venue city
'country':      Venue country
'lat':          Venue latitude
'lon':          Venue longitude
'artists':      Event artists
'headliner':    Event Headliner
'googlemap':    GoogleMap of venue location
'artist_image': Artist image
'venue_image':  Venue image



##YouTube

RunScript(script.extendedinfo,info=youtubesearch)           --> YoutubeSearch.%d
-- required additional parameters: id=
RunScript(script.extendedinfo,info=youtubeplaylist)         --> YoutubePlaylist.%d
-- required additional parameters: id=
RunScript(script.extendedinfo,info=youtubeusersearch)       --> YoutubeUserSearch.%d
-- required additional parameters: id=

'Thumb':        Video Thumbnail
'Description':  Video Description
'Title':        Video Title
'Date':         Video Upload Date


##Misc Images

RunScript(script.extendedinfo,info=xkcd)          --> XKCD.%d
- fetches a daily random list of XKCD webcomics
RunScript(script.extendedinfo,info=cyanide)       --> CyanideHappiness.%d
- fetches a daily random list of Cyanide & Happiness webcomics
RunScript(script.extendedinfo,info=dailybabe)     --> DailyBabe.%d
RunScript(script.extendedinfo,info=dailybabes)    --> DailyBabes.%d

'Thumb':        Image
'Title':        Image Title
'Description':  Image Description (only XKCD)



info=similarlocal
    Property Prefix: SimilarLocalMovies
    needed parameters:
    -dbid: DBID of any movie in your library

fetches similar movies from local database



info=json
    Property Prefix: RSS
    needed parameters:
    -feed: url to json feed

fetches items from a json feed (yahoo pipes, youtube JSON API)



Misc Calls:

info=artistdetails
    needed parameters:
        artistname: Artist to search for

- also fetches Discography and MusicVideos ATM

info=albuminfo ## todo
    needed parameters:
        artistname: Artist to search for

- also fetches Discography and MusicVideos ATM











##ActorInfo / MovieInfo Dialogs (script.metadata.actors replacement)


XBMC.RunScript(script.extendedinfo,info=extendedactorinfo,name=ACTORNAME)
XBMC.RunScript(script.extendedinfo,info=extendedactorinfo,id=ACTOR_TMDB_ID)

------------------------------------------------------------------------------------------------------------------------------------

###List of Built In Controls Available In script-ExtendedInfo Script-DialogInfo.xml:

150 -> container -> movies list
250 -> container -> youtube videos


###Labels Available In script-Actors-DialogInfo.xml:

Labels of the currently selected actor / director / writer / artist.
Window(home).Property(Title) --------------------> Name
Window(home).Property(Label) --------------------> Same as Title
Window(home).Property(Poster)---------------------> Poster
Window(home).Property(Plot)---------------------> Biography
Window(home).Property(Biography) ------> Same as Plot
Window(home).Property(Biooutline) -----> (currently not used)
Window(home).Property(TotalMovies) ----> Total of Known Movies (acting / directing / writing)
Window(home).Property(Birthday) -------> Date of Birthday
Window(home).Property(HappyBirthday) --> return true or empty
Window(home).Property(Age) ------------> Age (30)
Window(home).Property(AgeLong) --------> Age long format (age 30)
Window(home).Property(Deathday) -------> Date of Deathday
Window(home).Property(Deathage) -------> Age of dead (30)
Window(home).Property(DeathageLong) ---> Age of dead long format (age 30)
Window(home).Property(PlaceOfBirth) ---> Place of birth
Window(home).Property(AlsoKnownAs) ----> Also Known Name
Window(home).Property(Homepage) -------> Link of homepage, you can use onclick for open web browser directly on homepage: RunScript(script.metadata.actors,homepage=$INFO[Window(home).Property(Homepage)])
Window(home).Property(Adult) ----------> Is Adult Actor (no / yes)
Window(home).Property(fanart) ---> Fanart


Labels of Known Movies list
Container(150).ListItem.Label ---------------------> Title of movie
Container(150).ListItem.Title ---------------------> same as label
Container(150).ListItem.originaltitle -------------> originaltitle
Container(150).ListItem.Year ----------------------> year
Container(150).Listitem.Icon ----------------------> icon of movie
Container(150).ListItem.Property(role) ------------> role in currently slected movie
Container(150).ListItem.Property(job) -------------> job in currently slected movie (director / writer / etc)
Container(150).ListItem.Property(releasedate) -----> release date of movie
Container(150).ListItem.Property(year) ------------> same as year, but not return empty
Container(150).ListItem.Property(DBID)             -> return 1 or empty, if movie exists in library
Container(150).ListItem.Property(Playcount) -------> Playcount of movie (default is 0)
Container(150).ListItem.Property(file) ------------> media to play

Labels of thumbs list
Container(250).ListItem.Label --------------------> Image résolution (512x720)
Container(250).Listitem.Icon ---------------------> Image
Container(250).ListItem.Property(aspect_ratio) ---> Aspect Ratio (0.66)

[...] (WIP)

------------------------------------------------------------------------------------------------------------------------------------

##SKINNING ADD-ON DIALOGS:

Please have a look at reference implementation, too much to cover. For the infodialogs it is important to include ALL lists (if you dont want to use them just hide them)





