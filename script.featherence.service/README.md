![](http://i.imgur.com/zfdrpSG.png)

# **Features:**

* This addon is a core for every Featherence's addon.
* Wide range of tools to be used from within Kodi.
* Wide range of modules to be used by addons developers.
* Widget to be used on any supported skin.
* IR remote control for OpenELEC os.
* Please note that many modules are being used in Featherence skin and are not possible on others skins yet.


# **Available scripts commands:**

```
OPEN DIALOG SELECT WINDOW
RunScript(script.featherence.service,,?mode=29&amp;value=list&amp;value2=command&amp;value3=header&amp;value4=1)
TIP:
	- You may add more values to list and command by adding "|".
	- For set SkinString use 0.<skin.string> in value2.
	- For set different value upon select add -[x]- in value.
	- For set same value upon select when different value is also used (-[x]-) add _name in value2 command.
	- Use value4 = 0 for removing the exit button.
```

```
OPEN CUSTOM DIALOG TEXT VIEWER
RunScript(script.featherence.service,,?mode=31&amp;value=header&amp;value2=message)
```

```
SOFT-RESTART (Terminal supported)
RunScript(script.featherence.service,,?mode=50)
```

```
RESTART (Terminal supported)
RunScript(script.featherence.service,,?mode=51)
```

```
SUSPEND (Terminal supported)
RunScript(script.featherence.service,,?mode=52)
```

```
POWEROFF (Terminal supported)
RunScript(script.featherence.service,,?mode=53)
```

```
QUIT (Terminal supported)
RunScript(script.featherence.service,,?mode=54)
```

```
LAUNCH EXTENDEDINFO MOVIES INFO
RunScript(script.featherence.service,,?mode=70&amp;value=0)
```

```
LAUNCH EXTENDEDINFO TVSHOWS INFO
RunScript(script.featherence.service,,?mode=70&amp;value=1)
```

```
LAUNCH EXTENDEDINFO ACTORS INFO
RunScript(script.featherence.service,,?mode=70&amp;value=3)
```

```
LAUNCH EXTENDEDINFO DIRECTOR INFO
RunScript(script.featherence.service,,?mode=70&amp;value=4)
```



```
READ FROM FILE AND DISPLAY
RunScript(script.featherence.service,,?mode=31&amp;value=header&amp;value2=message&amp;value3=filepath)
```

# **Integrating Widget:**
* [Match Skin Widgets Property](http://kodi.wiki/view/Add-on:Skin_Widgets)

```
Run Widget Recent Movie
<onclick>RunScript(script.featherence.service,,?mode=24&amp;value=RecentMovie.1)</onclick>
```

```
Run Widget Random Movie Trailer Full screen
<onclick>RunScript(script.featherence.service,,?mode=24&amp;value=RecentMovie.1&amp;value2=trailers)</onclick>
```

```
Run Widget Random Movie Trailer
<onclick>RunScript(script.featherence.service,,?mode=24&amp;value=RecentMovie.10&amp;value2=trailers2)</onclick>
```

```
Run Widget Recent Episode
<onclick>RunScript(script.featherence.service,,?mode=24&amp;value=RecentEpisode.1)</onclick>
```

```
Run Widget Recommended Episode
<onclick>RunScript(script.featherence.service,,?mode=24&amp;value=RecommendedEpisode.10)</onclick>
```

```
Auto Refresh Widget contents upon end of Movie / Episode
VideoFullScreen.xml
<onload condition="IsEmpty(Window(home).Property(mode10))">RunScript(script.featherence.service,,?mode=10)</onload>
```

```
Refresh Widget
RunScript(script.featherence.service,,?mode=23)
```

```
PLAY RANDOM TRAILERS
RunScript(script.featherence.service,,?mode=25)
```

# **Create your own plugin:**
* **modules.py:**
  * **addDir:**
	```
	addDir form
	addDir('<name>','<url>',<mode number>,'<iconimage>','<description>','<optional>',"<viewtype>", '<fanart>')
	```
	
	```
	PLAY VIDEO
	METHOD 1: MODE 4 | URL = text
	METHOD 2: MODE 5/17 | URL = text
		  - YOUTUBE VIDEO ID: URL = &youtube_id=text
		  - YOUTUBE PLAYLIST ID: URL = &youtube_pl=text
		  - DAILYMOTION VIDEO ID: URL = &dailymotion_id=text
		  - DAILYMOTION PLAYLIST ID: URL = &dailymotion=text
		  - *ANY VIDEO FROM ADDON: URL = &custom4=text
		  *use ctrl+shift+P on the preferred location!
	```
	
	```
	SHOW FROM ADDON
	METHOD 1: MODE 8 | URL = text
	METHOD 2: MODE 6/17 | URL = text
		- *ANY VIDEO FROM ADDON: URL = &custom8=text
		*use ctrl+shift+P on the preferred location!
	```
	
	```
	SHOW PLAYLIST
	METHOD 1: MODE 13 | URL = text
	METHOD 2: MODE 6/17 | URL = text
		  - YOUTUBE PLAYLIST ID: URL = &youtube_pl=text
		  - DAILYMOTION PLAYLIST ID: URL = &dailymotion_id=text
	```
	
	```
	SHOW YOUTUBE CHANNEL
	METHOD 1: MODE 9 | URL = text
	METHOD 2: MODE 6/17 | URL = text
		- YOUTUBE CHANNEL ID: URL = &youtube_ch=text
		TIP: You may add '/playlists' after that channel id!
	```
	
	```
	SEARCH YOUTUBE
	OPEN: MODE 3 | URL = text
	FEATHERENCE: MODE 5/6/17 | URL = &youtube_se=text
	TIP: You may use:
	"&videoDuration=text&" | text = short/medium/long
	"&videoDefinition=text&" | text = standard/high
	```
	
	```
	READ LINE BY LINE FROM FILE AND SEARCH IN YOUTUBE
	PLAY ALL: MODE 2 | URL = <file path>
	TIP: os.path.join(addonPath, 'resources', 'templates2', '')
	addonPath = current addon
	```
	
	```
	SDAROT TV ADDON
	FEATHERENCE: MODE 5/6/17 | URL = &sdarot=text
	TIP: use ctrl+shift+P on the preferred location!
	```
	
	```
	WALLA NEW ADDON
	FEATHERENCE: MODE 5/6/17 | URL = &wallaNew=text
	TIP: use ctrl+shift+P on the preferred location!
	```
	
	```
	HOT VOD ADDON
	FEATHERENCE: MODE 5/6/17 | URL = &hotVOD=text
	TIP: use ctrl+shift+P on the preferred location!
	```
	
	```
	GET ADDON INFO
	ADDON = <ADDON ID>
	thumb, fanart, summary, description, plot = getAddonInfo(addon)
	```
	
	```
	GET INFO FROM YOUTUBE
	OPTIONAL = 'getAPIdata=<text>'
	text = &youtube_se=#Lion
	in that addDir put 'getAPIdata' in any of those:
		name, iconimage, desc, fanart
	```
	
	```
	SHOW ALL
	METHOD 1: MODE 6 | URL = <anything with '&xxx=text'>
	TIP: URL must be a list []
	     Modify default sublabel using '&name_=text&' inside the url.
	```
	
	```
	PLAY ALL
	METHOD 1: MODE 5 | URL = <anything with '&xxx=text'>
	TIP: URL must be a list []
	```
	
	```
	TVMODE
	METHOD 1: MODE 17 | URL = <anything with '&xxx=text'>
	TIP: URL must be a list []
	```
	
	```
	RANDOM PLAY ALL (ANY FOLDER + SUBFOLDERS IN CURRENT CONTAINER)
	METHOD 1: MODE 1
	TIP: Simply use: CATEGORIES102A()
	```
	
# **Links:**

* [Facebook](https://www.facebook.com/groups/featherence/)
* [YouTube](https://www.youtube.com/user/finalmakerr)
* [Featherence Repository](https://github.com/finalmakerr/featherence/raw/master/repository.featherence/repository.featherence-1.1.0.zip)
