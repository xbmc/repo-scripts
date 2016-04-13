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
OPEN DIALOG KEYBOARD WINDOW
RunScript(script.featherence.service,,?mode=30&amp;value=input&amp;value2=header&amp;value3=option&amp;value4=action&amp;value5=id&amp;value6=addon)
TIP:
	- value3 (option):
		0 - xbmcgui.INPUT_ALPHANUM (standard keyboard)
		1 - xbmcgui.INPUT_NUMERIC (format: #)
		2 - xbmcgui.INPUT_DATE (format: DD/MM/YYYY)
		3 - xbmcgui.INPUT_TIME (format: HH:MM)
		4 - xbmcgui.INPUT_IPADDRESS (format: #.#.#.#)
		5 - xbmcgui.INPUT_PASSWORD (return md5 hash of input, input is masked)
		
	- value4 (action):
	  Action to executed a sec after the virtual keyboard is open. 
	- value5 (id):
	  write up the skin string and that's it!
	- value6 (addon):
	  write up the addon ID then write the actual addon's settings ID in value5.
```

```
OPEN CUSTOM DIALOG TEXT VIEWER
RunScript(script.featherence.service,,?mode=31&amp;value=header&amp;value2=message)
```

```
OPEN OS WEB BROWSER
RunScript(script.featherence.service,,?mode=512&value=url)
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

* **CREATE PLAYLIST FROM PATH:**
	```
	path = 'special://userdata/library/videos/'
	RunScript(script.featherence.service,,?mode=211&amp;value=path&amp;value2=video&amp;value3=10)
	value2: video or music.
	value3: level to go deep path's subdirs.
	```

* **CREATE PLAYLIST FROM PATH:**
	```
	path = 'special://userdata/library/videos/'
	RunScript(script.featherence.service,,?mode=211&amp;value=path&amp;value2=video&amp;value3=10)
	value2: video or music.
	value3: level to go deep path's subdirs.
	```

* **DIALOG YES NO AND SET FILE OR PATH:**
	```
	RunScript(script.featherence.service,,?mode=22&amp;value=header&amp;value2=message&amp;value3=No!&amp;value4=Yes!&amp;value5=skinstring&amp;value6=type)
	value1: header.
	value2: message.
	value3: No Label.
	value4: Yes Label.
	value5: SkinString (without $INFO)
	value6: video or music.
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

* **plugin.video.featherence.be_creative:**
 * **What to do with it?:**
   * Install the addon from ZIP.
   * Edit addon.xml and rename the ID and addon's folder name.
   * Edit modules.py.

* **modules.py:**
  * **addDir:**
	```
	addDir form
	addDir('<name>','<url>',<mode>,'<iconimage>','<description>','<optional>','<viewtype>', '<fanart>')
	
	- mode: see list of available modes down below!
	- optional: 
	- viewtype: Currently have no usage - keep empty ('').
	- fanart: simply put the fanart URL or use getAddonFanart(<category number>, default=<URL>, custom=<URL>)
	The idea behind getAddonFanart is:
		When using this method there will always be a fanart (if the user allow it in the addon settings).
		<category number> = Let the user choose thier own fanart for any category.
		<default> = fanart to be used if the user is not customize any. Otherwise default addon fanart for given addDir.
		<custom> = Otherwise default and category - Fixed fanart for given addDIr.
	```

	 * **Available Modes:**
		
		* **MODE 4 - PLAY VIDEO / PLAYLIST:**
			```
			list = []
		    list.append('&youtube_pl=PLGnTTJWIWt4dcv7Z_cLyZVERGWsuHIt18')
		    list.append('&youtube_id=WFwHq6cY0403')
			list.append('&dailymotion_pl=x3e520')
		    list.append('&dailymotion_id=x26cyah')
		    list.append('&googledrive=0B7-ya5fAYJHWS0RQS244LTh6akU')
		    list.append('&custom4=plugin://plugin.video.youtube/play/?video_id=uwHQEpmRjhw')
			addDir("MODE 4 - PLAY DIRECT VIDEO",list,44,'http://i.imgur.com/ZVxYi7I.png','description','1','viewtype', getAddonFanart(background="", default="http://i.imgur.com/U2ufQo3.png", custom=""))
			  
			- &custom4: ANY VIDEO FROM ADDON. See GET CURRENT PATH INFORMATION.
			  
		* **MODE 44 - PLAY DIRECT VIDEO:**
			```
			list = []
			list.append('&direct4=' + <DIRECT URL>)
			addDir("MODE 44 - PLAY DIRECT VIDEO",list,44,'http://i.imgur.com/ZVxYi7I.png','description','1','viewtype', getAddonFanart(background="", default="http://i.imgur.com/U2ufQo3.png", custom=""))
			```		
		
		* **MODE 42 - LIST DIRECT VIDEO:**
			```
			list = []
			list.append('&direct4=' + <DIRECT URL>)
			addDir("MODE 42 - LIST DIRECT VIDEO",list,44,'http://i.imgur.com/ZVxYi7I.png','description','1','viewtype', getAddonFanart(background="", default="http://i.imgur.com/U2ufQo3.png", custom=""))
			```	
		
		* **MODE 8 - SHOW FROM ANOTHER ADDON:**
			```
			* addDir("MODE 8 - SHOW FROM ANOTHER ADDON",'plugin://plugin.video.featherence.kids/',8,'http://i.imgur.com/ZVxYi7I.png','description','1','viewtype', getAddonFanart(background="", default="http://i.imgur.com/U2ufQo3.png", custom=""))
			* list = []
			  list.append('&custom8=plugin://plugin.video.featherence.docu/')
			  list.append('&custom8=plugin://plugin.video.featherence.extreme/')
			  list.append('&custom8=plugin://plugin.video.featherence.kids/')
			  list.append('&custom8=plugin://plugin.video.featherence.music/')
			  addDir("MODE 8 - SHOW FROM ANOTHER ADDON",list,6,'http://i.imgur.com/ZVxYi7I.png','description','1','viewtype', getAddonFanart(background="", default="http://i.imgur.com/U2ufQo3.png", custom=""))
			```	

		* **MODE 13 - SHOW FROM PLAYLIST:**
			```
			* addDir("*MODE 13 - SHOW FROM PLAYLIST",'PLGnTTJWIWt4dcv7Z_cLyZVERGWsuHIt18',13,'http://i.imgur.com/ZVxYi7I.png','description','1','viewtype', getAddonFanart(background="", default="http://i.imgur.com/U2ufQo3.png", custom=""))
			* list = []
			  list.append('&youtube_pl=PLGnTTJWIWt4dcv7Z_cLyZVERGWsuHIt18')
			  addDir("*MODE 13 - SHOW FROM PLAYLIST",list,6,'http://i.imgur.com/ZVxYi7I.png','description','1','viewtype', getAddonFanart(background="", default="http://i.imgur.com/U2ufQo3.png", custom=""))
			```	
		
		* **MODE 40 - SHOW FROM SPECIFIC WEBSITES: (WIP!!)**
			```
			list = []
			list.append('&direct8=' + <URL>)
			addDir("MODE 40 - SHOW FROM SPECIFIC WEBSITES",list,6,'http://i.imgur.com/ZVxYi7I.png','description','1','viewtype', getAddonFanart(background="", default="http://i.imgur.com/U2ufQo3.png", custom=""))
			```
		
		* **MODE 41 - LIST & PLAY FROM SPECIFIC WEBSITES: (WIP!!)**
			```
			list = []
			list.append('&direct4=' + <URL>)
			addDir("MODE 41 - LIST & PLAY FROM SPECIFIC WEBSITES",list,6,'http://i.imgur.com/ZVxYi7I.png','description','1','viewtype', getAddonFanart(background="", default="http://i.imgur.com/U2ufQo3.png", custom=""))
			```	
		
		* **MODE 9 - SHOW FROM SHOW YOUTUBE CHANNEL:**
			```
			list = []
			list.append('&youtube_ch=finalmakerr')
			list.append('&youtube_ch=finalmakerr/playlists')
			addDir("*MODE 9 - SHOW FROM SHOW YOUTUBE CHANNEL",list,6,'http://i.imgur.com/ZVxYi7I.png','description','1','viewtype', getAddonFanart(background="", default="http://i.imgur.com/U2ufQo3.png", custom=""))
			```	
		
		* **MODE 3 - YOUTUBE SEARCH:**
			```
			list = []
			list.append('&youtube_se=Featherence')
			list.append('&youtube_se=Kodi')
			addDir('MODE 3 - YOUTUBE SEARCH',list,17,featherenceserviceicons_path + 'se.png',addonString_servicefeatherence(23).encode('utf-8') % ('Featherence & Kodi'),'1',"", getAddonFanart(background="", default="", custom=""))
			```	
		
		* **MODE 2 - MULTI YOUTUBE SEARCH:**
			```
			file = os.path.join(addonPath, 'resources', 'templates2', 'Featherence.txt')
			addDir('MODE 2 - MULTI YOUTUBE SEARCH',file,2,featherenceserviceicons_path + 'se.png','description','1',"", getAddonFanart(background="", default="", custom=""))
			```
			
			* **File Structure:**
			```
			Featherence
			```
			
		* **MODE 11 - MULTI COMMANDS FROM TXT:**
			```
			file = os.path.join(addonPath, 'resources', 'templates2', 'Featherence2.txt')
			list = []
			list.append('&custom_se11=' + file)
			addDir('MODE 11 - MULTI COMMANDS FROM TXT',list,17,'http://i.imgur.com/ZVxYi7I.png','description','1',"", getAddonFanart(background="", default="", custom=""))
			```
			
			* **File Structure:**
			```
			<url="&googledrive=0B7-ya5fAYJHWS0RQS244LTh6akU"/><title="Episode 1"/><thumb="http://i.imgur.com/ZVxYi7I.png"/><desc="description"/>
			```
		
		```
		GET INFO FROM API TO ADDDIR
		num = 'getAPIdata=<text>'
		in that addDir put 'getAPIdata' in any of those:
			name, iconimage, desc, fanart
		EXAMPLES USAGE:
			 * addDir('Go-Pro',list,17,'getAPIdata','getAPIdata','&getAPIdata=&youtube_ch=GoProCamera',58, getAddonFanart(background, default='getAPIdata', custom="https://i.vimeocdn.com/video/531419538.jpg?mw=1920&mh=1080&q=70"))
			 * 
		```
		
		* **Group Modes:**
			```
			The following modes require URL to be a list (not a string!), use the following as example before the actual addDir module:
			list = []
		    list.append('&youtube_ch=finalmakerr')
		    list.append('&youtube_pl=PLGnTTJWIWt4dcv7Z_cLyZVERGWsuHIt18')
		    list.append('&youtube_id=WFwHq6cY0403')
			```
				* **MODE 6 - SHOW ALL:**
				```
				* addDir("MODE 6 - SHOW ALL",list,6,'http://i.imgur.com/ZVxYi7I.png','description','1','viewtype', getAddonFanart(background="", default="http://i.imgur.com/U2ufQo3.png", custom=""))	
				```
				
				* **MODE 5 - PLAY ALL:**
				```
				* addDir("MODE 5 - PLAY ALL",list,5,'http://i.imgur.com/ZVxYi7I.png','description','1','viewtype', getAddonFanart(background="", default="http://i.imgur.com/U2ufQo3.png", custom=""))
				```
				
				* **MODE 17 - TV MODE:**
				```
				* addDir("MODE 17 - TV MODE",list,17,'http://i.imgur.com/ZVxYi7I.png','description','1','viewtype', getAddonFanart(background="", default="http://i.imgur.com/U2ufQo3.png", custom=""))
				```
				
				* **EXTRAS:**
					* **Rename specific variable in a list:**
					```
					USAGE: '&name_=<text>&'
					EXAMPLES USAGE:
					   * mylabel = 'Featherence'
						 list.append('&youtube_id=WFwHq6cY0403&name_='+ mylabel +'&')
					```
				
					* **GET CURRENT PATH INFORMATION:**
					```
					RunScript(script.featherence.service,,?mode=32&amp;value=1)
					<keymap>
						<global>
							<keyboard>
								<p mod="ctrl,shift" description="containerfolderpath">RunScript(script.featherence.service,,?mode=32&amp;value=1)</p>
					        </keyboard>
						</global>
					</keymap>		
					```
				

		
* **getAddonInfo(addon):**
		```
		GET ADDON INFO FOR ADDDIR
		EXAMPLES USAGE:
			addon = 'plugin.video.featherence.kids'
			thumb, fanart, summary, description, plot = getAddonInfo(addon)
			addDir('Featherence Kids','plugin://'+addon,8,thumb,plot,addon,"", getAddonFanart(background, custom=fanart))
		```

  * **PLAY ALL:**
		```
		PLAY ALL [MODE1]
		CATEGORIES_RANDOM(background="", default="", custom="")
		<category number> = Let the user choose thier own fanart for any category.
		<default> = fanart to be used if the user is not customize any. Otherwise default addon fanart for given addDir.
		<custom> = Otherwise default and category - Fixed fanart for given addDIr.
		```

  * **AVAILABLE CATEGORIES:**
		```
		CATEGORIES() = MAIN
		CATEGORIES100(name, iconimage, desc, fanart) = SUB (100-139)
		CATEGORIES200() = LIST OF COUNTRIES/LANGUAGES
		CATEGORIES10001(name, iconimage, desc, fanart) = SUB2 (10001-10009)
		CATEGORIES10101(name, iconimage, desc, fanart) = SUB2 (10101-10109)
		CATEGORIES10201(name, iconimage, desc, fanart) = SUB2 (10201-10209)
		CATEGORIES10301(name, iconimage, desc, fanart) = SUB2 (10301-10309)
		CATEGORIES10401(name, iconimage, desc, fanart) = SUB2 (10401-10409)
		CATEGORIES10501(name, iconimage, desc, fanart) = SUB2 (10501-10509)
		CATEGORIES10601(name, iconimage, desc, fanart) = SUB2 (10601-10609)
		CATEGORIES10701(name, iconimage, desc, fanart) = SUB2 (10701-10709)
		CATEGORIES10801(name, iconimage, desc, fanart) = SUB2 (10801-10809)
		CATEGORIES10901(name, iconimage, desc, fanart) = SUB2 (10901-10909)
		
		CATEGORIES_RANDOM(background="", default="", custom="")
		<category number> = Let the user choose thier own fanart for any category.
		<default> = fanart to be used if the user is not customize any. Otherwise default addon fanart for given addDir.
		<custom> = Otherwise default and category - Fixed fanart for given addDIr.
		```

	
	
# **Links:**

* [Facebook](https://www.facebook.com/groups/featherence/)
* [YouTube](https://www.youtube.com/user/finalmakerr)
* [Featherence Repository](https://github.com/finalmakerr/featherence/raw/master/repository.featherence/repository.featherence-1.1.0.zip)
