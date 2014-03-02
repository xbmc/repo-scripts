
How to use this addon in your skin:


I) Startup.xml:
RunScript(script.tv.show.next.aired,silent=True)

The script will scan your library and tries to fetch next aired info for every show.
There is no need to specify an alarm -- the script will will run a background update at regular intervals.

For shows that are airing today, the script will set the window properties listed below.

Window(Home).Property(NextAired.%d.*):
Label               (tv show name)
Thumb               (tv show icon)
AirTime             (eg. 'Wednesday, Thursday: 09:00 PM')
Path                (tv show path)
Library             (eg. videodb://2/2/1/ or videodb://tvshows/titles/1/)
Status              (eg. 'New Series'/'Returning Series'/'Cancelled/Ended')
StatusID            (id of the status)
Network             (name of the tv network that's airing the show)
Started             (airdate of the first episode, eg. 09/24/07, 'Mon, Sep 24, 2007', etc.)
Classification      (type of show; N.B. not currently supported)
Genre               (genre of the show)
Premiered           (year the first episode was aired, eg. '1999')
Country             (production country of the tv show, eg. 'USA')
Runtime             (duration of the episode in minutes)
Fanart              (tv show fanart)
Today               (will return 'True' if the show is aired today, otherwise 'False')
NextDate            (date the next episode will be aired)
NextTitle           (name of the next episode)
NextNumber          (season/episode number of the next episode, eg. '04x01')
NextEpisodeNumber   (episode number of the next episode, eg. '04')
NextSeasonNumber    (season number of the next episode, eg. '01')
LatestDate          (date the last episode was aired)
LatestTitle         (name of the last episode)
LatestNumber        (season/episode number of the last episode)
LatestEpisodeNumber (episode number of the last episode)
LatestSeasonNumber  (season number of the last episode)
AirDay              (day(s) of the week the show is aired, eg 'Tuesday')
ShortTime           (time the show is aired, eg. '08:00 PM')
Art(poster)         (tv show poster)
Art(banner)         (tv show banner)
Art(fanart)         (tv show fanart)
Art(landscape)      (tv show landscape - artwork downloader required)
Art(clearlogo)      (tv show logo - artwork downloader required)
Art(clearart)       (tv show clearart - artwork downloader required)
Art(characterart)   (tv show characterart - artwork downloader required)

Status ids:
0 - Returning Series
1 - Cancelled/Ended
2 - TBD/On The Bubble
4 - New Series
6 - Final Season
-1 - Undefined

---

Window(Home).Property(NextAired.*):
Total               (number of running shows)
TodayTotal          (number of shows aired today)
TodayShow           (list of shows aired today)


II) MyVideoNav.xml:
RunScript(script.tv.show.next.aired,backend=True)

the script will run in the background and provide next aired info for the focussed listitem.
the infolabels listed above are available, using this format:

Window(Home).Property(NextAired.*)


use !IsEmpty(Window(Home).Property(NextAired.NextDate)) as a visible condition!


example code:
<control type="group">
	<visible>!IsEmpty(Window(Home).Property(NextAired.NextDate))</visible>
	<control type="label">
		<posx>0</posx>
		<posy>0</posy>
		<width>800</width>
		<height>20</height>
		<label>$INFO[Window(Home).Property(NextAired.NextTitle)]</label>
	</control>
	<control type="label">
		<posx>0</posx>
		<posy>20</posy>
		<width>800</width>
		<height>20</height>
		<label>$INFO[Window(Home).Property(NextAired.NextDate)]</label>
	</control>
</control>



III) if you run the script without any options (or if it's started by the user),
the script will provide a TV Guide window (script-NextAired-TVGuide.xml).

this window is fuly skinnable.


a list of required id's:
200 - container / shows aired on monday
201 - container / shows aired on tuesday
202 - container / shows aired on wednesday
203 - container / shows aired on thursday
204 - container / shows aired on friday
205 - container / shows aired on saturday
206 - container / shows aired on sunday
8 - in case all the containers above are empty, we set focus to this id

a list of available infolabels:
ListItem.Label          (tv show name)
ListItem.Thumb          (tv show thumb)
ListItem.Property(*)    (see above)

totals are available using the window properties listed above.

Window(home).Property(NextAired.TodayDate)              (todays date)
Window(home).Property(NextAired.%d.Date)                (date for the lists, eg NextAired.1.Date will show the date for monday)

a list of available infolabels, related to the available add-on settings:
Window(home).Property(TVGuide.ThumbType)                (thumb type selected by the user: 0=poster, 1=banner, 2=logo)
Window(home).Property(TVGuide.BackgroundFanart)         (1=user selected to show fanart, empty if disabled)
Window(home).Property(TVGuide.PreviewThumbs)            (1=user selected to show 16:9 showthumbs, empty if disabled)


all other id's and properties in the default script window are optional and not required by the script.


IV) To force an update of the nextaired database ahead of its next scheduled time:
RunScript(script.tv.show.next.aired,force=True)

To force an update as well as reset all the existing data (forcing a fresh scan of everything) use the reset option:
RunScript(script.tv.show.next.aired,reset=True)

The force update and reset options are also available in the addon settings.
