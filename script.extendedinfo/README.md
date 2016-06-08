# ExtendedInfo add-on [![License](https://img.shields.io/badge/License-GPL%20v2%2B-blue.svg)](https://github.com/phil65/script.extendedinfo/blob/master/LICENSE.txt)

List of possible ExtendedInfo script calls.
All calls can also be done by using a plugin path.

Example:
```
<content>plugin://script.extendedinfo?info=discography&amp;&amp;artistname=INSERT_ARTIST_NAME_HERE</content>
```
- keep Attention to the parameter separators ("&amp;&amp;")


### Rotten Tomatoes

```
RunScript(script.extendedinfo,info=intheatermovies)
```
```
RunScript(script.extendedinfo,info=comingsoonmovies)
```
```
RunScript(script.extendedinfo,info=openingmovies)
```
```
RunScript(script.extendedinfo,info=boxofficemovies)
```
```
RunScript(script.extendedinfo,info=toprentalmovies)
```
```
RunScript(script.extendedinfo,info=currentdvdmovies)
```
```
RunScript(script.extendedinfo,info=newdvdmovies)
```
```
RunScript(script.extendedinfo,info=upcomingdvdmovies)
```

Available Properties:

- 'Title':        Movie Title
- 'imdb_id':       IMDB ID
- 'duration':     Movie duration
- 'Year':         Release Year
- 'Premiered':    Release Date
- 'mpaa':         MPAA Rating
- 'Rating':       Audience Rating (0-10)
- 'Plot':         Movie Plot

Available Art:
- 'Poster':  Movie Poster


### TheMovieDB

```
RunScript(script.extendedinfo,info=incinemamovies)           --> InCinemasMovies.%d
```
```
RunScript(script.extendedinfo,info=upcomingmovies)            --> UpcomingMovies.%d
```
```
RunScript(script.extendedinfo,info=popularmovies)       --> PopularMovies.%d
```
```
RunScript(script.extendedinfo,info=topratedmovies)      --> TopRatedMovies.%d
```
```
RunScript(script.extendedinfo,info=similarmovies)       --> SimilarMovies.%d
```
  - required additional parameters: dbid=
```
RunScript(script.extendedinfo,info=set)                 --> MovieSetItems.%d
```
- fetches a list of movies from the same Set
  - required additional parameters: dbid=
```
RunScript(script.extendedinfo,info=personmovies)      --> PersonMovies.%d
```
  - required additional parameters: person=
```
RunScript(script.extendedinfo,info=studio)              --> StudioInfo.%d
```
- fetches a list of movies from the same studio
  - required additional parameters: studio=


Available Properties:

- 'Title':            Movie Title
- 'OriginalTitle':    Movie OriginalTitle
- 'ID':               TheMovieDB ID
- 'Rating':           Movie Rating (0-10)
- 'Votes':            Vote Count for Rating
- 'Year':             Release Year
- 'Premiered':        Release Date

Available Art:

- 'Fanart':      Movie Fanart
- 'Poster':      Movie Poster


```
RunScript(script.extendedinfo,info=populartvshows)      --> PopularTVShows.%d
```
```
RunScript(script.extendedinfo,info=topratedtvshows)     --> TopRatedTVShows.%d
```
```
RunScript(script.extendedinfo,info=onairtvshows)        --> OnAirTVShows.%d
```
```
RunScript(script.extendedinfo,info=airingtodaytvshows)  --> AiringTodayTVShows.%d
```

Available Properties:

- 'Title':            TVShow Title
- 'ID':               TVShow MovieDB ID
- 'OriginalTitle':    TVShow OriginalTitle
- 'Rating':           TVShow Rating
- 'Votes':            Number of Votes for Rating
- 'Premiered':        TV Show First Air Date

Available Art:

- 'Poster':      TVShow Poster
- 'Fanart':      TVShow Fanart


### Trakt.tv

```
RunScript(script.extendedinfo,info=trendingmovies)  --> TrendingMovies.%d
```
```
RunScript(script.extendedinfo,info=traktsimilarmovies)     --> SimilarMovies.%d
```
  - required additional parameters: dbid= (database id) or id= (imdb id)

Available Properties:

- 'Title'
- 'Plot'
- 'Tagline'
- 'Genre'
- 'Rating'
- 'mpaa'
- 'Year'
- 'Premiered'
- 'Runtime'
- 'Trailer'

Available Art:

- 'Poster'
- 'Fanart'


```
RunScript(script.extendedinfo,info=trendingshows)           --> TrendingShows.%d
```
```
RunScript(script.extendedinfo,info=traktsimilartvshows)     --> SimilarTVShows.%d
```
  - required additional parameters: dbid= (database id) or id= (tvdb id)

Available Properties:

- 'TVShowTitle':      TVShow Title
- 'duration':         Duration (?)
- 'Plot':             Plot
- 'ID':               ID
- 'Genre':            Genre
- 'Rating':           Rating
- 'mpaa':             mpaa
- 'Year':             Release Year
- 'Premiered':        First Air Date
- 'Status':           TVShow Status
- 'Studio':           TVShow Studio
- 'Country':          Production Country
- 'Votes':            Amount of Votes
- 'Watchers':         Amount of Watchers
- 'AirDay':           Day episode is aired
- 'AirShortTime':     Time episode is aired

Available Art:

- 'Poster':      TVShow Poster
- 'Banner':      TVShow Banner
- 'Fanart':      TVShow Fanart

```
RunScript(script.extendedinfo,info=airingshows)         --> AiringShows.%d
```
```
RunScript(script.extendedinfo,info=premiereshows)       --> PremiereShows.%d
```
Available Properties:

- 'Title':         Episode Title
- 'TVShowTitle':   TVShow Title
- 'Plot':          Episode Plot
- 'Genre':         TVShow Genre
- 'Duration':      Episode Duration
- 'Year':          Episode Release Year
- 'mpaa':          TVShow Mpaa Rating
- 'Studio':        TVShow Studio
- 'Thumb':         Episode Thumb

Available Art:

- 'Poster':   TVShow Poster
- 'Banner':   TVShow Banner
- 'Fanart':   TVShow Fanart


### TheAudioDB

```
RunScript(script.extendedinfo,info=discography)         --> Discography.%d
```
- fetches the artist discography (Last.FM)
  - required additional parameters: artistname=

Available Properties:

- 'label':           Album Title
- 'artist':          Album Artist
- 'mbid':            Album MBID
- 'id':              Album AudioDB ID
- 'Description':     Album Description
- 'Genre':           Album Genre
- 'Mood':            Album Mood
- 'Speed':           Album Speed
- 'Theme':           Album Theme
- 'Type':            Album Type
- 'thumb':           Album Thumb
- 'year':            Album Release Year
- 'Sales':           Album Sales

```
RunScript(script.extendedinfo,info=mostlovedtracks)         --> MostLovedTracks.%d
```
- fetches most loved tracks for the given artist (TheAudioDB)
  - required additional parameters: artistname=
```
RunScript(script.extendedinfo,info=albuminfo)               --> TrackInfo.%d
```
  - required additional parameters: id= ???

Available Properties:

- 'label':       Track Name
- 'Artist':      Artist Name
- 'mbid':        Track MBID
- 'Album':       Album Title
- 'Thumb':       Album Thumb
- 'Path':        Link to Youtube Video

```
RunScript(script.extendedinfo,info=artistdetails) ???
```


### LastFM

```
RunScript(script.extendedinfo,info=topartists)
```
- fetches a lists of the most popular artists

Available Properties:

- 'Title':        Artist Name
- 'mbid':         Artist MBID
- 'Thumb':        Artist Thumb
- 'Listeners':    actual Listeners


### YouTube
```
RunScript(script.extendedinfo,info=youtubesearchvideos)
```
  - required additional parameters: id=
```
RunScript(script.extendedinfo,info=youtubeplaylistvideos)
```
  - required additional parameters: id=
```
RunScript(script.extendedinfo,info=youtubeusersearchvideos)
```
  - required additional parameters: id=

Available Properties:

- 'Thumb':        Video Thumbnail
- 'Description':  Video Description
- 'Title':        Video Title
- 'Date':         Video Upload Date


info=similarlocalmovies
    needed parameters:
    -dbid: DBID of any movie in your library

fetches similar movies from local database



### Misc Calls:

info=artistdetails
    needed parameters:
        artistname: Artist to search for

- also fetches Discography and MusicVideos ATM

info=albuminfo ## todo
    needed parameters:
        artistname: Artist to search for

- also fetches Discography and MusicVideos ATM





### ActorInfo / MovieInfo Dialogs (script.metadata.actors replacement)

possible script call for Actor Info Dialog:
```
RunScript(script.extendedinfo,info=extendedactorinfo,name=ACTORNAME)
```
```
RunScript(script.extendedinfo,info=extendedactorinfo,id=ACTOR_TMDB_ID)
```
possible script calls for Movie Info Dialog:
```
RunScript(script.extendedinfo,info=extendedinfo,name=MOVIENAME)
```
```
RunScript(script.extendedinfo,info=extendedinfo,id=MOVIE_TMDB_ID)
```
```
RunScript(script.extendedinfo,info=extendedinfo,dbid=MOVIE_DBID)
```
```
RunScript(script.extendedinfo,info=extendedinfo,imdb_id=IMDB_ID)
```

----

## SKINNING ADD-ON DIALOGS:

Please have a look at reference implementation, too much to cover. Consider the following docs as outdated, needs some updating.


#### List of Built In Controls for add-on dialogs :
 - MOVIES, TVSHOWS, SEASONS, EPISODES: script-script.extendedinfo-DialogVideoInfo.xml
 - ACTORS: script-script.extendedinfo-DialogInfo.xml

| IDS     | MOVIES    | TVSHOWS   | SEASONS   | EPISODES | ACTORS      |
|---------|-----------|-----------|-----------|----------|-------------|
| 150     | Similar   | Similar   | ---       | ---      | Movie Roles |
| 250     | Sets      | Seasons   | ---       | ---      | TV Roles    |
| 350     | Youtube   | Youtube   | Youtube   | Youtube  | Youtube     |
| 450     | Lists     | ---       | ---       | ---      | Images      |
| 550     | Studios   | Studios   | ---       | ---      | Movie Crew  |
| 650     | Releases  | Certific  | ---       | ---      | TV Crew     |
| 750     | Crew      | Crew      | Crew      | Crew     | Tagged Img  |
| 850     | Genres    | Genres    | ---       | ---      | ---         |
| 950     | Keywords  | Keywords  | ---       | ---      | ---         |
| 1000    | Actors    | Actors    | Actors    | Actors   | ---         |
| 1050    | Reviews   | ---       | ---       | ---      | ---         |
| 1150    | Videos    | Videos    | Videos    | Videos   | ---         |
| 1250    | Images    | Images    | Images    | ---      | ---         |
| 1350    | Backdrops | Backdrops | Backdrops | Images   | ---         |
| 1450    | ---       | Networks  | ---       | ---      | ---         |
| 2000    | ---       | ---       | Episodes  | ---      | ---         |

#### Labels Available In script-Actors-DialogInfo.xml:

Labels of the currently selected actor / director / writer / artist.
- Window(home).Property(Title) ----------> Name
- Window(home).Property(Label) ----------> Same as Title
- Window(home).Property(Poster)----------> Poster
- Window(home).Property(Plot)------------> Biography
- Window(home).Property(Biography) ------> Same as Plot
- Window(home).Property(TotalMovies) ----> Total of Known Movies (acting / directing / writing)
- Window(home).Property(Birthday) -------> Date of Birthday
- Window(home).Property(HappyBirthday) --> return true or empty
- Window(home).Property(Age) ------------> Age (30)
- Window(home).Property(AgeLong) --------> Age long format (age 30)
- Window(home).Property(Deathday) -------> Date of Deathday
- Window(home).Property(PlaceOfBirth) ---> Place of birth
- Window(home).Property(AlsoKnownAs) ----> Also Known Name
- Window(home).Property(Homepage) -------> Link of homepage
- Window(home).Property(Adult) ----------> Is Adult Actor (no / yes)
- Window(home).Property(fanart) ---------> Fanart


Labels of Known Movies list
- Container(150).ListItem.Label ---------------------> Title of movie
- Container(150).ListItem.Title ---------------------> same as label
- Container(150).ListItem.originaltitle -------------> originaltitle
- Container(150).ListItem.Year ----------------------> year
- Container(150).Listitem.Icon ----------------------> icon of movie
- Container(150).ListItem.Property(role) ------------> role in currently slected movie
- Container(150).ListItem.Property(job) -------------> job in currently slected movie (director / writer / etc)
- Container(150).ListItem.Premiered -----------------> release date of movie
- Container(150).ListItem.Year ----------------------> production year
- Container(150).ListItem.DBID ----------------------> returns the dbid, or empty if not available.
- Container(150).ListItem.PlayCount -----------------> Playcount of movie (default is 0)
- Container(150).ListItem.File ----------------------> media to play

Labels of thumbs list
- Container(250).ListItem.Label --------------------> Image résolution (512x720)
- Container(250).Listitem.Icon ---------------------> Image
- Container(250).ListItem.Property(aspect_ratio) ---> Aspect Ratio (0.66)

[...](WIP)

#### Labels Available In script-Actors-DialogVideoInfo.xml:

[...](WIP)
