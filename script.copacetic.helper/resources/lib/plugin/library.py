# author: realcopacetic, sualfred

import xbmc
from xbmcgui import ListItem


def add_items(li, json_query, type):
    for item in json_query:
        if type == 'movie':
            set_movie(li, item)
        elif type == 'tvshow':
            set_tvshow(li, item)
        elif type == 'episode':
            set_episode(li, item)
        elif type == 'musicvideo':
            set_musicvideo(li, item)


def set_movie(li, item):
    li_item = ListItem(item['title'], offscreen=True)
    videoInfoTag = li_item.getVideoInfoTag()
    videoInfoTag.setDbId(item['movieid'])
    videoInfoTag.setDuration(item['runtime'])
    videoInfoTag.setLastPlayed(item['lastplayed'])
    videoInfoTag.setMediaType('movie')
    videoInfoTag.setPlaycount(item['playcount'])
    videoInfoTag.setResumePoint(
        item['resume']['position'], item['resume']['total']
    )
    videoInfoTag.setTitle(item['title'])
    videoInfoTag.setTrailer(item['trailer'])
    videoInfoTag.setYear(item['year'])
    videoInfoTag.setStudios(item['studio'])
    videoInfoTag.setMpaa(item['mpaa'])
    for key, value in iter(list(item['streamdetails'].items())):
        for stream in value:
            if 'video' in key:
                videostream = xbmc.VideoStreamDetail(**stream)
                videoInfoTag.addVideoStream(videostream)
            elif 'audio' in key:
                audiostreamlist = list(stream.values())
                audiostream = xbmc.AudioStreamDetail(*audiostreamlist)
                videoInfoTag.addAudioStream(audiostream)

    li_item.setArt(item['art'])
    li_item.setArt({'icon': 'DefaultMovies.png'})
    li.append((item['file'], li_item, False))


def set_tvshow(li, item):
    season = item['season']
    episode = int(item['episode'])
    watchedepisodes = int(item['watchedepisodes'])
    li_item = ListItem(item['title'], offscreen=True)
    videoInfoTag = li_item.getVideoInfoTag()
    videoInfoTag.setDbId(item['tvshowid'])
    videoInfoTag.setLastPlayed(item['lastplayed'])
    videoInfoTag.setMediaType('tvshow')
    videoInfoTag.setTitle(item['title'])
    videoInfoTag.setYear(item['year'])
    videoInfoTag.setStudios(item['studio'])
    videoInfoTag.setMpaa(item['mpaa'])
    if episode > 0 and watchedepisodes > 0:
        watchedepisodepercent = int(((watchedepisodes / episode) * 100))
    else:
        watchedepisodepercent = 0

    if episode > watchedepisodes:
        unwatchedepisodes = int(episode - watchedepisodes)
    else:
        unwatchedepisodes = 0

    li_item.setProperty('totalseasons', str(season))
    li_item.setProperty('totalepisodes', str(episode))
    li_item.setProperty('watchedepisodes', str(watchedepisodes))
    li_item.setProperty('unwatchedepisodes', str(unwatchedepisodes))
    li_item.setProperty('watchedepisodepercent', str(watchedepisodepercent))
    li_item.setArt(item['art'])
    li_item.setArt({'icon': 'DefaultTVShows.png'})
    li.append((item['file'], li_item, True))


def set_episode(li, item):
    if item['episode'] < 10:
        episode_number = f"0{item['episode']}"
    else:
        episode_number = item['episode']
    label = f"{item['season']}x{episode_number}"
    li_item = ListItem(label, offscreen=True)
    videoInfoTag = li_item.getVideoInfoTag()
    videoInfoTag.setDbId(item['episodeid'])
    videoInfoTag.setDuration(item['runtime'])
    videoInfoTag.setEpisode(item['episode'])
    videoInfoTag.setLastPlayed(item['lastplayed'])
    videoInfoTag.setMediaType('episode')
    videoInfoTag.setPlaycount(item['playcount'])
    videoInfoTag.setPremiered(item['firstaired'])
    videoInfoTag.setResumePoint(
        item['resume']['position'], item['resume']['total']
    )
    videoInfoTag.setSeason(item['season'])
    videoInfoTag.setTitle(item['title'])
    videoInfoTag.setTvShowTitle(item['showtitle'])
    videoInfoTag.setStudios(item['studio'])
    videoInfoTag.setMpaa(item['mpaa'])
    for key, value in iter(list(item['streamdetails'].items())):
        for stream in value:
            if 'video' in key:
                videostream = xbmc.VideoStreamDetail(**stream)
                videoInfoTag.addVideoStream(videostream)
            elif 'audio' in key:
                audiostreamlist = list(stream.values())
                audiostream = xbmc.AudioStreamDetail(*audiostreamlist)
                videoInfoTag.addAudioStream(audiostream)

    li_item.setArt(item['art'])
    li_item.setArt({'icon': 'DefaultTVShows.png'})
    li.append((item['file'], li_item, False))


def set_musicvideo(li, item):
    li_item = ListItem(item['title'], offscreen=True)
    videoInfoTag = li_item.getVideoInfoTag()
    videoInfoTag.setArtists(item['artist'])
    videoInfoTag.setDbId(item['musicvideoid'])
    videoInfoTag.setDuration(item['runtime'])
    videoInfoTag.setLastPlayed(item['lastplayed'])
    videoInfoTag.setMediaType('musicvideo')
    videoInfoTag.setResumePoint(
        item['resume']['position'], item['resume']['total']
    )
    videoInfoTag.setPlaycount(item['playcount'])
    videoInfoTag.setTitle(item['title'])
    videoInfoTag.setYear(item['year'])
    for key, value in iter(list(item['streamdetails'].items())):
        for stream in value:
            if 'video' in key:
                videostream = xbmc.VideoStreamDetail(**stream)
                videoInfoTag.addVideoStream(videostream)
            elif 'audio' in key:
                audiostreamlist = list(stream.values())
                audiostream = xbmc.AudioStreamDetail(*audiostreamlist)
                videoInfoTag.addAudioStream(audiostream)

    li_item.setArt(item['art'])
    li_item.setArt({'icon': 'DefaultVideo.png'})
    li.append((item['file'], li_item, False))
