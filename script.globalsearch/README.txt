
INFORMATION FOR SKINNERS
------------------------



CONTENTS:
0.   Running the addon 
I.   Infolabels available in script-globalsearch-main.xml
II.  Infolabels available in script-globalsearch-infodialog.xml
III. Control id's used in script-globalsearch-main.xml
IV.  Control id's used in script-globalsearch-infodialog.xml
V.   Control id's used in script-globalsearch-contextmenu.xml
VI.  Available window properties



0. Running the addon
------------------
The addon can be run in two ways:
- the user executes the addon
- the script executes the addon: RunScript(script.globalsearch)

You can specify which categories should be searched (this overrides the user preferences set in the addon settings):
RunScript(script.globalsearch,movies=true)
RunScript(script.globalsearch,tvshows=true&amp;musicvideos=true&amp;songs=true)

available options: epg, movies, tvshows, episodes, musicvideos, artists, albums, songs, actors



I. Infolabels available in script-globalsearch-main.xml
-------------------------------------------------------
EPG:
ListItem.Label
ListItem.Icon
ListItem.Property(Genre)
ListItem.Property(Plot)
ListItem.Property(Duration)
ListItem.Property(Starttime)
ListItem.Property(Endtime)
ListItem.Property(ChannelName)
ListItem.Property(ChannelNumber)
ListItem.Property(Path)


MOVIES (and movies by actor):
ListItem.Label
ListItem.Icon
ListItem.Property(Fanart)
ListItem.Property(Genre)
ListItem.Property(Plot)
ListItem.Property(Plotoutline)
ListItem.Property(Duration)
ListItem.Property(Studio)
ListItem.Property(Tagline)
ListItem.Property(Year) 
ListItem.Property(Trailer)
ListItem.Property(Playcount)
ListItem.Property(Rating)
ListItem.Property(StarRating)
ListItem.Property(Mpaa)
ListItem.Property(Director)
ListItem.Property(Writer)
ListItem.Property(VideoResolution)
ListItem.Property(VideoCodec)
ListItem.Property(VideoAspect)
ListItem.Property(AudioCodec)
ListItem.Property(AudioChannels)
ListItem.Property(Path)


TV SHOWS:
ListItem.Label
ListItem.Icon
ListItem.Property(Episode)
ListItem.Property(Mpaa)
ListItem.Property(Year)
ListItem.Property(Art(Banner))
ListItem.Property(Art(Poster))
ListItem.Property(Fanart)
ListItem.Property(Genre)
ListItem.Property(Plot)
ListItem.Property(Premiered)
ListItem.Property(Studio)
ListItem.Property(Rating)
ListItem.Property(StarRating)
ListItem.Property(Playcount)
ListItem.Property(Path)


SEASONS:
ListItem.Label
ListItem.Icon
ListItem.Property(Episode)
ListItem.Property(Fanart)
ListItem.Property(TvShowTitle)
ListItem.Property(Playcount)
ListItem.Property(Path)


EPISODES:
ListItem.Label
ListItem.Icon
ListItem.Property(Episode)
ListItem.Property(Plot)
ListItem.Property(Rating)
ListItem.Property(StarRating)
ListItem.Property(Director)
ListItem.Property(Fanart)
ListItem.Property(Season)
ListItem.Property(Duration)
ListItem.Property(TvShowTitle)
ListItem.Property(Premiered)
ListItem.Property(Playcount)
ListItem.Property(VideoResolution)
ListItem.Property(VideoCodec)
ListItem.Property(VideoAspect)
ListItem.Property(AudioCodec)
ListItem.Property(AudioChannels)
ListItem.Property(Path)


MUSIC VIDEOS:
ListItem.Label
ListItem.Icon
ListItem.Property(Album)
ListItem.Property(Artist)
ListItem.Property(Fanart)
ListItem.Property(Director)
ListItem.Property(Genre)
ListItem.Property(Plot)
ListItem.Property(Duration)
ListItem.Property(Studio)
ListItem.Property(Year)
ListItem.Property(Playcount)
ListItem.Property(VideoResolution)
ListItem.Property(VideoCodec)
ListItem.Property(VideoAspect)
ListItem.Property(AudioCodec)
ListItem.Property(AudioChannels)
ListItem.Property(Path)


ARTISTS:
ListItem.Label
ListItem.Icon
ListItem.Property(Artist_Born)
ListItem.Property(Artist_Died)
ListItem.Property(Artist_Formed)
ListItem.Property(Artist_Disbanded)
ListItem.Property(Artist_YearsActive)
ListItem.Property(Artist_Mood)
ListItem.Property(Artist_Style)
ListItem.Property(Fanart)
ListItem.Property(Artist_Genre)
ListItem.Property(Artist_Description)
ListItem.Property(Path)


ALBUMS:
ListItem.Label
ListItem.Icon
ListItem.Property(Artist)
ListItem.Property(Album_label)
ListItem.Property(Genre)
ListItem.Property(Fanart)
ListItem.Property(Album_Description)
ListItem.Property(Album_Theme)
ListItem.Property(Album_Style)
ListItem.Property(Album_Rating)
ListItem.Property(StarRating)
ListItem.Property(Album_Type)
ListItem.Property(Album_Mood)
ListItem.Property(Year)
ListItem.Property(Path)


SONGS:
ListItem.Label
ListItem.Icon
ListItem.Property(Artist)
ListItem.Property(Album)
ListItem.Property(Genre)
ListItem.Property(Comment)
ListItem.Property(Track)
ListItem.Property(Rating)
ListItem.Property(StarRating)
ListItem.Property(Playcount)
ListItem.Property(Duration)
ListItem.Property(Fanart)
ListItem.Property(Year)
ListItem.Property(Path)



II. Infolabels available in script-globalsearch-infodialog.xml
--------------------------------------------------------------
You can use the same labels as above, only add a 'Container(100).' prefix to them.
for example:
Container(100).ListItem.Label
Container(100).ListItem.Property(Plot)



III. Control id's used in script-globalsearch-main.xml
------------------------------------------------------
100 - Main group id. All code should be included in this group. The script will set this id to hidden when playing a trailer.


110 - Label containing the number of found movies
111 - Container for found movies
119 - The script will set this id to visible when movies are found

120 - Label containing the number of found tv shows
121 - Container for found tv shows 
129 - The script will set this id to visible when tv shows are found

130 - Label containing the number of found seasons
131 - Container for found seasons  
139 - The script will set this id to visible when seasons are found

140 - Label containing the number of found episodes
141 - Container for found episodes 
149 - The script will set this id to visible when episodes are found

150 - label containing the number of found music videos
151 - Container for found music videos 
159 - The script will set this id to visible when music videos are found

160 - Label containing the number of found artists
161 - Container for found artists 
169 - The script will set this id to visible when artists are found

170 - Label containing the number of found albums
171 - Container for found albums 
179 - The script will set this id to visible when albums are found

180 - Label containing the number of found songs
181 - Container for found songs 
189 - The script will set this id to visible when songs are found

210 - Label containing the number of found movies containing the actor
211 - Container for found movies containing the actor
219 - The script will set this id to visible when movies containing the actor are found

220 - Label containing the number of found programmes
221 - Container for found programmes 
229 - The script will set this id to visible when programmes are found

190 - 'Searching...' label, visible when the script is searching
191 - Search category label, visible when the script is searching
198 - 'New search' button, visible when the script finished searching
199 - 'No results found' label, visible when no results are found



IV. Control id's used in script-globalsearch-infodialog.xml
-----------------------------------------------------------
100 - Hidden list containing the selected ListItem.

110 - The script will set this id to visible when the selected item is a movie or actor
120 - The script will set this id to visible when the selected item is a tv show
130 - The script will set this id to visible when the selected item is a season
140 - The script will set this id to visible when the selected item is a episode
150 - The script will set this id to visible when the selected item is a music video
160 - The script will set this id to visible when the selected item is a artist
170 - The script will set this id to visible when the selected item is a album
180 - The script will set this id to visible when the selected item is a song
200 - The script will set this id to visible when the selected item is a programme

191 - First button (OK), but you can specify a diffrent label for it if you like
192 - Second button. The script will set the button label and the visible condition.
193 - Third button. The script will set the button label and the visible condition.



V. Control id's used in script-globalsearch-contextmenu.xml
-----------------------------------------------------------
997 - Context menu top texture
998 - Context menu middle texture
999 - Context menu bottom texture

1001 - First context menu button, the script will handle the visible condition
1002 - Second context menu button, the script will handle the visible condition
1003 - Third context menu button, the script will handle the visible condition


As always, do not change or remove any of the id's mentioned above!
If you want to get rid of some of them, just position them outside of the screen.

Any id not mentioned above, but used in the default xml files, can safely be changed or removed.



VI.  Available window properties
--------------------------------
Window.Property(GlobalSearch.SearchString) - the string the user is searching for

