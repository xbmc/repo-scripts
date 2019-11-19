# script.embuary.info

Script to provide skinners the option to call The Movie DB for actor and video infos.
Unlike ExtendedInfo it requires a skin integration and it does not include a browser and it only crawls for the most basic and required information.

## Search by string

Some examples
*  ```RunScript(script.embuary.info,call=person,query='"Bruce Willis"')```
*  ```RunScript(script.embuary.info,call=tv,query='"Californication"')```
*  ```RunScript(script.embuary.info,call=movie,query='"Iron Man"')```
*  ```RunScript(script.embuary.info,call=movie,query='"Iron Man"',year=2008)```

`'" "'` is not required, but useful if a string contains special characters. which needs to be escaped.

*Multiple results*
The script provides a selection dialog if multiple results were returned.

## Search by The Movie DB, IMBDb or TVDb ID

*  ```RunScript(script.embuary.info,call=person,tmbd_id=65)```
*  ```RunScript(script.embuary.info,call=tv,tmbd_id=65)```
*  ```RunScript(script.embuary.info,call=tv,tmbd_id=65,season=1)```
*  ```RunScript(script.embuary.info,call=tv,external_id=70559)``` (ID must be TVDb or IMDb)
*  ```RunScript(script.embuary.info,call=tv,dbid=1)``` (fetches TVDb from uniqueid table in the database if available; title + year is used as fallback)
*  ```RunScript(script.embuary.info,call=movie,tmbd_id=65)```
*  ```RunScript(script.embuary.info,call=movie,external_id=tt0371746)``` (IMDb ID)
*  ```RunScript(script.embuary.info,call=movie,dbid=1)``` (fetches IMDb ID from uniqueid table in the database if available; title + year is used as fallback)

## Options

* An TMDb API key is already shipped but can be replaced in the add-on settings
* To get support for Rotten Tomatoes or IMDb ratings it's required to add a own OMDb key in the settings
* EN is used as default language. It can be changed in the add-on settings, but will still be used if important informations are missing from the result (The Movie DB doesn't have a own fallback logic).
* US is used as default country locale for certifications. Other supported locales can be set in the add-on settings.

## Required windows, reserved IDs and properties
*Important*
* I hate it if a script takes control about the focus. Because of that it's up to the skinner to add a `<defaultcontrol>` tag.
* `ListItem.DBID` is filled if the found item is part of the local library.
* All actions on the control IDs below are controlled by the script.
* The script doesn't set any window property for the called item. You have to call it from the main container. Examples: `$INFO[Container(10051).ListItem.Directors]`, `$INFO[Container(10051).ListItem.Rating]`, `$INFO[Container(10051).ListItem.Art(thumb)]`

*script-embuary-person.xml*
* List control ID `10051` = All available information of the called person.
* List control ID `10052` = All movies starring with actor xyz
* List control ID `10053` = All shows starring with actor xyz
* List control ID `10054` = Actor portraits

Special properties:
* `Container(10051).ListItem.Property(TotalMedia)` = Total count of media which is also available in your library
* `Container(10051).ListItem.Property(TotalTVShows)` = Total count of shows which is also available in your library
* `Container(10051).ListItem.Property(TotalMovies)` = Total count of movies which is also available in your library
* `Container(10051).ListItem.Property(Birthday)` = Date of birth
* `Container(10051).ListItem.Property(Deathday)` = Date of death
* `Container(10051).ListItem.Property(Age)` = Current age / died at the age of
* `Container(10051).ListItem.Property(Place_Of_Birth)` = Place of birth
* `Container(10051).ListItem.Property(Known_For_Department)` = Known for department (acting, directing, etc.)
* `Container(10051).ListItem.Property(Gender)` = Gender (male/female)
* `Container(10051).ListItem.Property(Biography)` = Biography
* `Container(10052).ListItem.Property(Role)` = Character role
* `Container(10053).ListItem.Property(Role)` = Character role

*script-embuary-video.xml*
* List control ID `10051` = All available information of the called item.
* List control ID `10052` = Cast
* List control ID `10053` = Similar titles
* List control ID `10054` = YouTube results
* List control ID `10055` = Backdrop images
* List control ID `10056` = Crew (for seasons it is used to display guest stars)
* List control ID `10057` = Collection items
* List control ID `10058` = Seasons
* List control ID `10059` = Poster images

Special properties for all items:
* `Container(id).ListItem.Property(UnwatchedEpisodes)` = Local unwatched episodes
* `Container(id).ListItem.Property(WatchedEpisodes)` = Local watched episodes
* `Container(id).ListItem.Property(TotalEpisodes)` = Local available episodes
* `Container(id).ListItem.Property(File)` = Local filename and path of movie

Special properties:
* `Container(10051).ListItem.Property(Votes.IMDB)` = IMDb votes
* `Container(10051).ListItem.Property(Rating.IMDB)` = IMDb rating
* `Container(10051).ListItem.Property(Rating.Rotten)` = Rotten Tomatoes rating
* `Container(10051).ListItem.Property(Rating.Metacritic)` = Metacritic rating
* `Container(10051).ListItem.Property(Release)` = Retail release date
* `Container(10051).ListItem.Property(Budget)` = Budget
* `Container(10051).ListItem.Property(Revenue)` = Revenue
* `Container(10051).ListItem.Property(Awards)` = Awards
* `Container(10051).ListItem.Property(Homepage)` = Homepage
* `Container(10051).ListItem.Property(Network.%i)` = Network name (%i = 0,1,2,3,...)
* `Container(10051).ListItem.Property(Network.icon.%i)` = Network icon (%i = 0,1,2,3,...)
* `Container(10051).ListItem.Property(Studio.%i)` = Studio name (%i = 0,1,2,3,...)
* `Container(10051).ListItem.Property(Studio.icon.%i)` = Studio icon (%i = 0,1,2,3,...)
* `Container(10051).ListItem.Property(Collection)` = Belongs to collection
* `Container(10051).ListItem.Property(Collection_id)` = Collection ID
* `Container(10051).ListItem.Property(Collection_poster)` = Collection poster art
* `Container(10051).ListItem.Property(Collection_fanart)` = Collection fanart
* `Container(10051).ListItem.Property(NextEpisode)` = Next aired episode name
* `Container(10051).ListItem.Property(NextEpisode_number)` = Next aired episode number
* `Container(10051).ListItem.Property(NextEpisode_season)` = Next aired episode season number
* `Container(10051).ListItem.Property(NextEpisode_plot)` = Next aired episode plot
* `Container(10051).ListItem.Property(NextEpisode_date)` = Next aired episode date
* `Container(10051).ListItem.Property(NextEpisode_thumb)` = Next aired episode thumb
* `Container(10051).ListItem.Property(LastEpisode)` = Last aired episode name
* `Container(10051).ListItem.Property(LastEpisode_number)` = Last aired episode number
* `Container(10051).ListItem.Property(LastEpisode_season)` = Last aired episode season number
* `Container(10051).ListItem.Property(LastEpisode_plot)` = Last aired episode plot
* `Container(10051).ListItem.Property(LastEpisode_date)` = Last aired episode date
* `Container(10051).ListItem.Property(LastEpisode_thumb)` = Last aired episode thumb
* `Container(10051).ListItem.Property(Region_release)` = Movie release date of set country if it's different to ListItem.Premiered

*script-embuary-image.xml*
* List control ID `1` = Is used to display a portrait/backdrop images in fullscreen.
* Scrollbar control ID `2` = Will be the focused on window init.

*additional properties*
* Configured language code `Window(home).Property(script.embuary.info-language_code)`
* Configured country code `Window(home).Property(script.embuary.info-country_code)`

## Overwriting onback or provide an additional onclose action
You can add a custom onback or a general onclose action in script-embuary-video.xml and script-embuary-person.xml

*Example*

* `<onload>SetProperty(onclose,SetFocus(100))</onload>` = To set a general action if a window is going to be closed. Like reseting the focus to a default control.
* `<onload>SetProperty(onback_10052,SetFocus(900))</onload>` = Don't close the window, but set focus to ID 900 if onback was called while container 10052 was in focus.

## Widgets
The script ships following widgets:

* `plugin://script.embuary.info/?info=trending&amp;call=movie&amp;get=week` = trending movies
* `plugin://script.embuary.info/?info=movies&amp;call=upcoming` = upcoming movies
* `plugin://script.embuary.info/?info=movies&amp;call=now_playing` = now playing movies
* `plugin://script.embuary.info/?info=movies&amp;call=top_rated` = top rated movies
* `plugin://script.embuary.info/?info=movies&amp;call=popular` = popular movies
* `plugin://script.embuary.info/?info=trending&amp;call=tv&amp;get=week` = trending shows
* `plugin://script.embuary.info/?info=tvshows&amp;call=top_rated` = top rates shows
* `plugin://script.embuary.info/?info=tvshows&amp;call=popular` = popular shows
* `plugin://script.embuary.info/?info=tvshows&amp;call=airing_today` = shows airing today
* `plugin://script.embuary.info/?info=tvshows&amp;call=on_the_air` = shows on the air

All of them can be accessed by the addons -> video addons node so it's easy to set them with the skinshortcuts script.


