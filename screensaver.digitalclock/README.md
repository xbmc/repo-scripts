Digital clock screensaver
=================
**Branches guide:**
 - **master:** Works on Kodi v19 Codename Matrix and up
 - **krypton:** Works on Kodi v17 Codename Krypton and on Kodi V18 Codename Leia

Digital clock screensaver with a lot of options.

These are the options:

__Movement__
- Movement on the screen (Random position, Bounce movement, Fixed in the center, Custom position)
- Bounce movement speed
- Number of seconds to stay in place (Number of seconds that the clock will stay in place before moving to a random location)

__Format__
- Time format (17:14, 05:14, 05:14 PM, 5:14 No hour zero padding Windows, 5:14 PM No hour zero padding Windows, 5:14 No hour zero padding Unix, 5:14 PM No hour zero padding Unix)
- Colon blink
- Date format (Hide date, Saturday 30. May 2015, 30.05.2015, 05.30.2015, Custom)
- Custom date format:
- Day: d(1-31) dd(01-31) ddd(Mon-Sun) DDD(Monday-Sunday)
- Month: m(1-12) mm(01-12) mmm(Jan-Dec) MMM(January-December)
- Year: yy(2-digit year) yyyy(4-digit year)

__Additional Information__
- Enable additional information
- Number of seconds for information switch (Number of seconds before the information will be switched with another one, i.e. Artist - Song - Weather information)
- Enable now playing information
- Combine song artist and title  (Song artist - song title)
- Show only music information (If this is enabled and a song is playing, only song info will be shown)
- Enable album art
- Enable weather information
- Weather icons
- Enable CPU usage information
- Enable battery level information
- Enable free memory information
- CPU temperature (Depends on the system if it will work or not)
- GPU temperature (Depends on the system if it will work or not)
- HDD temperature (Depends on the system if it will work or not)
- FPS
- Current uptime
- Total uptime
- Enable movie library information (Total, Watched, Unwatched)
- Enable TV show library information (Total, Watched, Unwatched)
- Enable music library information (Artists, Albums, Songs)

__Color | Opacity__ (Users can choose color and opacity for every element, along with random color and random opacity) - Implemented using script.skin.helper.colorpicker - Thanks Marcel!
- Choose hour color and opacity
- Random hour color
- Random hour opacity
- Choose colon color and opacity
- Random colon color
- Random colon opacity
- Choose minute color and opacity
- Random minute color
- Random minute opacity
- Choose AM/PM color and opacity
- Random AM/PM color
- Random AM/PM opacity
- Choose date color and opacity
- Random date color
- Random date opacity
- Choose additional information color and opacity
- Random additional information color
- Random additional information opacity
- Choose icon color and opacity
- Random icon color
- Random icon opacity

__Background__
- Choose text shadow color
- Chose background image aspect ratio
- Choose background (One color, Single image, Slideshow, Skin Helper, Dim)
- Choose background color
- Choose image
- Choose slideshow directory
- Random images (Screensaver chooses a random image from the folder for the background)
- Change background picture every
- Choose Skin Helper background (Movie random fanart, TV show random fanart, Music artist random fanart, Random fanart of all media types)
- Brightness level

__Extra Options__
- Element Size Increase (%) (Users can increase the size of text and icons)
- Log out
- Stop now playing media
- Log out after (minutes)
- Enable RSS (The screensaver will show the same RSS Kodi shows, so make sure it's properly configured and enabled in Kodi)

This screensaver is configured for every skin separately since it has to use Fonts defined by the skin!

Skin developers have an option to use script-screensaver-digitalclock-custom.xml in their skins 1080i, 720p... folder.
They should provide and maintain that xml file with their skin!
Screensaver will check for skin folders in this order: 1080i, 720p, 21x9, 16x9, 4x3Hirez.
If no script-screensaver-digitalclock-custom.xml is found screensaver will look for an appropriate xml file within screensavers folder.
If there is no appropriate xml file it will use skin.default.xml

If the skin is not on the list screensaver will use default font names from confluence (It might not look pretty but it will work with any skin):

- Ace2
- Adonic
- Aeon Nox 5
- Aeon Nox Silvo
- Aeon Tajo
- Aeon MQ5
- Aeon MQ5
- Aeon MQ6
- Aeon MQ8
- Amber
- AppTV
- Arctic: Zephyr
- Arctic: Zephyr 2
- Aura
- Bello 6
- Bello 7
- Black Glass Nova
- Box
- Chroma
- Confluence
- Embuary-Leia
- Eminence.2
- Estouchy
- Estuary
- Ftv
- (Fuse)neue
- Grid
- Horizon
- Madnox
- Metropolis
- Mimic
- Nebula
- Omni
- OSMC
- Pellucid
- Phenomenal
- Quartz
- Rapier
- Retouched
- Reestuarized
- Revolve
- Titan
- Transparency
- Unity
- Xperience1080

If your skin is not on the list, and you would like it to be - send me a message.

Possible issues:
Depending on your language and selected date format the date text might become ... that means that the text for the date is too long, I can fix that easily, just let me know if it happens. (Screenshot would be great including which language you are using and how many letters are supposed to be on the screen).

Everything else should work just fine, let me know if you encounter any bugs or issues.

We're on Transifex!
Feel free to translate screensaver.digitalclock to your language: https://www.transifex.com/teamxbmc/kodi-addons/screensaver-digitalclock/
