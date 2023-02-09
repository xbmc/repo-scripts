import xbmc
import xbmcaddon
import xbmcgui
import os
import sys
import json
import urllib.request

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
HOME = xbmcgui.Window(10000)
INFODIALOG = xbmcgui.Window(12003)


def Get_JSON_response(query):
    json_response = xbmc.executeJSONRPC(query)
    return json.loads(json_response)


def media_streamdetails(filename, streamdetails):
    info = {}
    video = streamdetails['video']
    audio = streamdetails['audio']
    if xbmc.getCondVisibility("ListItem.IsStereoscopic"):
        info['videoresolution'] = '3d'
    elif video:
        videowidth = video[0]['width']
        videoheight = video[0]['height']
        if (videowidth <= 720 and videoheight <= 480):
            info['videoresolution'] = "480"
        elif (videowidth <= 768 and videoheight <= 576):
            info['videoresolution'] = "576"
        elif (videowidth <= 960 and videoheight <= 544):
            info['videoresolution'] = "540"
        elif (videowidth <= 1280 and videoheight <= 720):
            info['videoresolution'] = "720"
        elif (videowidth <= 1920 or videoheight <= 1080):
            info['videoresolution'] = "1080"
        elif (videowidth <= 3840 or videoheight <= 2160):
            info['videoresolution'] = "4k"
        elif (videowidth <= 7680 or videoheight <= 4320):
            info['videoresolution'] = "8k"
        else:
            info['videoresolution'] = ""
    elif (('dvd') in filename and not ('hddvd' or 'hd-dvd') in filename) or (filename.endswith('.vob' or '.ifo')):
        info['videoresolution'] = '576'
    elif (('bluray' or 'blu-ray' or 'brrip' or 'bdrip' or 'hddvd' or 'hd-dvd') in filename):
        info['videoresolution'] = '1080'
    elif (('4k') in filename):
        info['videoresolution'] = '4k'
    else:
        info['videoresolution'] = '1080'
    if video:
        info['videocodec'] = video[0]['codec']
        if (video[0]['aspect'] < 1.4859):
            info['videoaspect'] = "1.33"
        elif (video[0]['aspect'] < 1.7190):
            info['videoaspect'] = "1.66"
        elif (video[0]['aspect'] < 1.8147):
            info['videoaspect'] = "1.78"
        elif (video[0]['aspect'] < 2.0174):
            info['videoaspect'] = "1.85"
        elif (video[0]['aspect'] < 2.2738):
            info['videoaspect'] = "2.20"
        else:
            info['videoaspect'] = "2.35"
    else:
        info['videocodec'] = ''
        info['videoaspect'] = ''
    if audio:
        info['audiocodec'] = audio[0]['codec']
        info['audiochannels'] = audio[0]['channels']
    else:
        info['audiocodec'] = ''
        info['audiochannels'] = ''
    return info


def media_path(path):
    # Check for stacked movies
    try:
        path = os.path.split(path)[0].rsplit(' , ', 1)[1].replace(",,", ",")
    except:
        path = os.path.split(path)[0]
    # Fixes problems with rared movies and multipath
    if path.startswith("rar://"):
        path = [os.path.split(urllib.request.url2pathname(path.replace("rar://", "")))[0]]
    elif path.startswith("multipath://"):
        temp_path = path.replace("multipath://", "").split('%2f/')
        path = []
        for item in temp_path:
            path.append(urllib.request.url2pathname(item))
    else:
        path = [path]
    return path[0]


def log(txt):
    if not isinstance (txt, str):
        txt = txt.decode("utf-8")
    message = u'%s: %s' % (ADDON_ID, txt)
    xbmc.log(msg=message, level=xbmc.LOGDEBUG)


def prettyprint(string):
    log(json.dumps(string, sort_keys=True, indent=4, separators=(',', ': ')))


def set_artist_properties(audio):
    count = 1
    latestyear = 0
    firstyear = 0
    playcount = 0
    for item in audio['result']['albums']:
        art = item['art']
        HOME.setProperty('SkinInfo.Artist.Album.%d.Title' % count, item['title'])
        HOME.setProperty('SkinInfo.Artist.Album.%d.Year' % count, str(item['year']))
        HOME.setProperty('SkinInfo.Artist.Album.%d.DBID' % count, str(item.get('albumid')))
        HOME.setProperty('SkinInfo.Artist.Album.%d.Label' % count, item['albumlabel'])
        HOME.setProperty('SkinInfo.Artist.Album.%d.Art(discart)' % count, art.get('discart', ''))
        HOME.setProperty('SkinInfo.Artist.Album.%d.Art(thumb)' % count, art.get('thumb', ''))
        if item['playcount']:
            playcount = playcount + item['playcount']
        if item['year'] > latestyear:
            latestyear = item['year']
        if firstyear == 0 or item['year'] < firstyear:
            firstyear = item['year']
        count += 1
    if firstyear > 0 and latestyear < 2030:
        HOME.setProperty('SkinInfo.Artist.Albums.Newest', str(latestyear))
        HOME.setProperty('SkinInfo.Artist.Albums.Oldest', str(firstyear))
    HOME.setProperty('SkinInfo.Artist.Albums.Count', str(audio['result']['limits']['total']))
    HOME.setProperty('SkinInfo.Artist.Albums.Playcount', str(playcount))

    if ADDON.getSettingBool("enable_debug_json"):
        prettyprint(audio)


def set_album_properties(json_response):
    count = 1
    duration = 0
    discnumber = 0
    tracklist = ""
    for item in json_response['result']['songs']:
        HOME.setProperty('SkinInfo.Album.Song.%d.Title' % count, item['title'])
        tracklist += "[B]" + str(item['track']) + "[/B]: " + item['title'] + "[CR]"
        array = item['file'].split('.')
        HOME.setProperty('SkinInfo.Album.Song.%d.FileExtension' % count, str(array[-1]))
        if item['disc'] > discnumber:
            discnumber = item['disc']
        duration += item['duration']
        count += 1
    minutes = duration / 60
    seconds = duration % 60
    HOME.setProperty('SkinInfo.Album.Songs.Discs', str(discnumber))
    HOME.setProperty('SkinInfo.Album.Songs.Duration', str(minutes).zfill(2) + ":" + str(seconds).zfill(2))
    HOME.setProperty('SkinInfo.Album.Songs.Tracklist', tracklist)
    HOME.setProperty('SkinInfo.Album.Songs.Count', str(json_response['result']['limits']['total']))

    if ADDON.getSettingBool("enable_debug_json"):
        prettyprint(json_response)


def set_movie_properties(json_response):
    count = 1
    runtime = 0
    writer = []
    director = []
    genre = []
    country = []
    studio = []
    years = []
    plot = ""
    title_list = ""
    title_header = "[B]" + str(json_response['result']['setdetails']['limits']['total']) + " " + xbmc.getLocalizedString(20342) + "[/B][CR]"
    for item in json_response['result']['setdetails']['movies']:
        art = item['art']
        streaminfo = media_streamdetails(item['file'].lower(), item['streamdetails'])
        HOME.setProperty('SkinInfo.Set.Movie.%d.DBID' % count, str(item.get('movieid')))
        HOME.setProperty('SkinInfo.Set.Movie.%d.Title' % count, item['label'])
        HOME.setProperty('SkinInfo.Set.Movie.%d.Plot' % count, item['plot'])
        HOME.setProperty('SkinInfo.Set.Movie.%d.PlotOutline' % count, item['plotoutline'])
        HOME.setProperty('SkinInfo.Set.Movie.%d.Path' % count, media_path(item['file']))
        HOME.setProperty('SkinInfo.Set.Movie.%d.Year' % count, str(item['year']))
        HOME.setProperty('SkinInfo.Set.Movie.%d.Duration' % count, str(item['runtime'] // 60))
        HOME.setProperty('SkinInfo.Set.Movie.%d.VideoResolution' % count, streaminfo["videoresolution"])
        HOME.setProperty('SkinInfo.Set.Movie.%d.Art(clearlogo)' % count, art.get('clearlogo', ''))
        HOME.setProperty('SkinInfo.Set.Movie.%d.Art(discart)' % count, art.get('discart', ''))
        HOME.setProperty('SkinInfo.Set.Movie.%d.Art(fanart)' % count, art.get('fanart', ''))
        HOME.setProperty('SkinInfo.Set.Movie.%d.Art(poster)' % count, art.get('poster', ''))
        HOME.setProperty('SkinInfo.Set.Movie.%d.MPAA' % count, item['mpaa'])

        if studio:
            HOME.setProperty('SkinInfo.Set.Movies.Single.Studio', studio[0])

        title_list += "[I]" + item['label'] + " (" + str(item['year']) + ")[/I][CR]"
        if item['plotoutline']:
            plot += "[B]" + item['label'] + " (" + str(item['year']) + ")[/B][CR]" + item['plotoutline'] + "[CR][CR]"
        else:
            plot += "[B]" + item['label'] + " (" + str(item['year']) + ")[/B][CR]" + item['plot'] + "[CR][CR]"
        runtime += item['runtime']
        count += 1
        if item.get("writer"):
            writer += [w for w in item["writer"] if w and w not in writer]
        if item.get("director"):
            director += [d for d in item["director"] if d and d not in director]
        if item.get("genre"):
            genre += [g for g in item["genre"] if g and g not in genre]
        if item.get("country"):
            country += [c for c in item["country"] if c and c not in country]
        if item.get("studio"):
            studio += [s for s in item["studio"] if s and s not in studio]
        years.append(str(item['year']))
    HOME.setProperty('SkinInfo.Set.Movies.Plot', plot)
    HOME.setProperty('SkinInfo.Set.Movies.List', title_header + title_list)
    if json_response['result']['setdetails']['limits']['total'] > 1:
        HOME.setProperty('SkinInfo.Set.Movies.ExtendedPlot', title_header + title_list + "[CR]" + plot)
    else:
        HOME.setProperty('SkinInfo.Set.Movies.ExtendedPlot', plot)
    HOME.setProperty('SkinInfo.Set.Movies.Title', title_list)
    HOME.setProperty('SkinInfo.Set.Movies.Runtime', str(runtime // 60))
    HOME.setProperty('SkinInfo.Set.Movies.Writer', " / ".join(writer))
    HOME.setProperty('SkinInfo.Set.Movies.Director', " / ".join(director))
    HOME.setProperty('SkinInfo.Set.Movies.Genre', " / ".join(genre))
    HOME.setProperty('SkinInfo.Set.Movies.Country', " / ".join(country))
    HOME.setProperty('SkinInfo.Set.Movies.Studio', " / ".join(studio))
    HOME.setProperty('SkinInfo.Set.Movies.Years', " / ".join(years))
    HOME.setProperty('SkinInfo.Set.Movies.Count', str(json_response['result']['setdetails']['limits']['total']))

    if ADDON.getSettingBool("enable_debug_json"):
        prettyprint(json_response)


def clear_properties():
    if xbmc.getCondVisibility("Window.IsActive(videos)"):
        for i in range(1, 40):
            HOME.clearProperty('SkinInfo.Set.Movie.%d.Art(clearlogo)' % i)
            HOME.clearProperty('SkinInfo.Set.Movie.%d.Art(fanart)' % i)
            HOME.clearProperty('SkinInfo.Set.Movie.%d.Art(poster)' % i)
            HOME.clearProperty('SkinInfo.Set.Movie.%d.Art(discart)' % i)
            HOME.clearProperty('SkinInfo.Detail.Movie.%d.Art(poster)' % i)
            HOME.clearProperty('SkinInfo.Detail.Movie.%d.Art(fanart)' % i)
            HOME.clearProperty('SkinInfo.Detail.Movie.%d.Path' % i)
            INFODIALOG.clearProperty('SkinInfo.AudioLanguage.%d' % i)
            INFODIALOG.clearProperty('SkinInfo.AudioCodec.%d' % i)
            INFODIALOG.clearProperty('SkinInfo.AudioChannels.%d' % i)
            INFODIALOG.clearProperty('SkinInfo.SubtitleLanguage.%d' % i)
        HOME.clearProperty('SkinInfo.Set.Movies.Plot')
        HOME.clearProperty('SkinInfo.Set.Movies.ExtendedPlot')
        HOME.clearProperty('SkinInfo.Set.Movies.Runtime')
        HOME.clearProperty('SkinInfo.Set.Movies.Writer')
        HOME.clearProperty('SkinInfo.Set.Movies.Director')
        HOME.clearProperty('SkinInfo.Set.Movies.Genre')
        HOME.clearProperty('SkinInfo.Set.Movies.Country')
        HOME.clearProperty('SkinInfo.Set.Movies.Studio')
        HOME.clearProperty('SkinInfo.Set.Movies.Years')
        HOME.clearProperty('SkinInfo.Set.Movies.Count')
    if xbmc.getCondVisibility("Window.IsActive(music)"):
        for i in range(1, 40):
            HOME.clearProperty('SkinInfo.Artist.Album.%d.Title' % i)
            HOME.clearProperty('SkinInfo.Artist.Album.%d.Plot' % i)
            HOME.clearProperty('SkinInfo.Artist.Album.%d.PlotOutline' % i)
            HOME.clearProperty('SkinInfo.Artist.Album.%d.Year' % i)
            HOME.clearProperty('SkinInfo.Artist.Album.%d.Duration' % i)
            HOME.clearProperty('SkinInfo.Artist.Album.%d.Thumb' % i)
            HOME.clearProperty('SkinInfo.Artist.Album.%d.ID' % i)
            HOME.clearProperty('SkinInfo.Artist.Album.%d.Art(discart)' % i)
            HOME.clearProperty('SkinInfo.Artist.Album.%d.Art(thumb)' % i)
            HOME.clearProperty('SkinInfo.Album.Song.%d.Title' % i)
            HOME.clearProperty('SkinInfo.Album.Song.%d.FileExtension' % i)
            HOME.clearProperty('SkinInfo.Detail.Music.%d.Art(fanart)' % i)
            HOME.clearProperty('SkinInfo.Detail.Music.%d.Art(thumb)' % i)
            HOME.clearProperty('SkinInfo.Detail.Music.%d.DBID' % i)
            HOME.clearProperty('SkinInfo.Detail.Music.%d.Genre' % i)
            HOME.clearProperty('SkinInfo.Detail.Music.%d.Title' % i)
            HOME.clearProperty('SkinInfo.Detail.Music.%d.Year' % i)
            HOME.clearProperty('SkinInfo.Detail.Music.%d.Artist' % i)
        HOME.clearProperty('SkinInfo.Album.Songs.TrackList')
        HOME.clearProperty('SkinInfo.Album.Songs.Discs')
        HOME.clearProperty('SkinInfo.Artist.Albums.Newest')
        HOME.clearProperty('SkinInfo.Artist.Albums.Oldest')
        HOME.clearProperty('SkinInfo.Artist.Albums.Count')
        HOME.clearProperty('SkinInfo.Artist.Albums.Playcount')
        HOME.clearProperty('SkinInfo.Album.Songs.Discs')
        HOME.clearProperty('SkinInfo.Album.Songs.Duration')
        HOME.clearProperty('SkinInfo.Album.Songs.Count')