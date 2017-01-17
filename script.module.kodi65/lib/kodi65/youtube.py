# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import urllib
import itertools

from kodi65 import utils
from kodi65 import VideoItem
from kodi65 import ItemList

YT_KEY = 'AIzaSyB-BOZ_o09NLVwq_lMskvvj1olDkFI4JK0'
BASE_URL = "https://www.googleapis.com/youtube/v3/"
PLUGIN_BASE = "plugin://script.extendedinfo/?info="


def handle_videos(results, extended=False):
    """
    process vidoe api result to ItemList
    """
    videos = ItemList(content_type="videos")
    for item in results:
        snippet = item["snippet"]
        thumb = snippet["thumbnails"]["high"]["url"] if "thumbnails" in snippet else ""
        try:
            video_id = item["id"]["videoId"]
        except Exception:
            video_id = snippet["resourceId"]["videoId"]
        video = VideoItem(label=snippet["title"],
                          path=PLUGIN_BASE + 'youtubevideo&&id=%s' % video_id)
        video.set_infos({'plot': snippet["description"],
                         'mediatype': "video",
                         'premiered': snippet["publishedAt"][:10]})
        video.set_artwork({'thumb': thumb})
        video.set_playable(True)
        video.set_properties({'channel_title': snippet["channelTitle"],
                              'channel_id': snippet["channelId"],
                              'type': "video",
                              'youtube_id': video_id})
        videos.append(video)
    if not extended:
        return videos
    params = {"part": "contentDetails,statistics",
              "id": ",".join([i.get_property("youtube_id") for i in videos])}
    ext_results = get_data(method="videos",
                           params=params)
    if not ext_results:
        return videos
    for item in videos:
        for ext_item in ext_results["items"]:
            if not item.get_property("youtube_id") == ext_item['id']:
                continue
            details = ext_item['contentDetails']
            stats = ext_item['statistics']
            likes = stats.get('likeCount')
            dislikes = stats.get('dislikeCount')
            item.update_infos({"duration": get_duration_in_seconds(details['duration'])})
            props = {"duration": details['duration'][2:].lower(),
                     "formatted_duration": get_formatted_duration(details['duration']),
                     "dimension": details['dimension'],
                     "definition": details['definition'],
                     "caption": details['caption'],
                     "viewcount": utils.millify(stats['viewCount']),
                     "likes": likes,
                     "dislikes": dislikes}
            item.update_properties(props)
            if likes and dislikes:
                vote_count = int(likes) + int(dislikes)
                if vote_count > 0:
                    item.set_info("rating", round(float(likes) / vote_count * 10, 1))
            break
    return videos


def get_duration_in_seconds(duration):
    """
    convert youtube duration string to seconds int
    """
    duration = duration[2:-1].replace("H", "M").split("M")
    if len(duration) == 3:
        return int(duration[0]) * 3600 + int(duration[1]) * 60 + int(duration[2])
    elif len(duration) == 2:
        return int(duration[0]) * 60 + int(duration[1])
    else:
        return int(duration[0])


def get_formatted_duration(duration):
    """
    convert youtube duration string to formatted duration
    """
    duration = duration[2:-1].replace("H", "M").split("M")
    if len(duration) == 3:
        return "{}:{}:{}".format(duration[0].zfill(2), duration[1].zfill(2), duration[2].zfill(2))
    elif len(duration) == 2:
        return "{}:{}".format(duration[0].zfill(2), duration[1].zfill(2))
    else:
        return "00:{}".format(duration[0].zfill(2))


def handle_playlists(results):
    """
    process playlist api result to ItemList
    """
    playlists = ItemList(content_type="videos")
    for item in results:
        snippet = item["snippet"]
        thumb = snippet["thumbnails"]["high"]["url"] if "thumbnails" in snippet else ""
        try:
            playlist_id = item["id"]["playlistId"]
        except Exception:
            playlist_id = snippet["resourceId"]["playlistId"]
        playlist = VideoItem(label=snippet["title"],
                             path=PLUGIN_BASE + 'youtubeplaylist&&id=%s' % playlist_id)
        playlist.set_infos({'plot': snippet["description"],
                            "mediatype": "video",
                            'premiered': snippet["publishedAt"][:10]})
        playlist.set_art("thumb", thumb)
        playlist.set_properties({'youtube_id': playlist_id,
                                 'channel_title': snippet["channelTitle"],
                                 'type': "playlist",
                                 'live': snippet["liveBroadcastContent"].replace("none", "")})
        playlists.append(playlist)
    params = {"id": ",".join([i.get_property("youtube_id") for i in playlists]),
              "part": "contentDetails"}
    ext_results = get_data(method="playlists",
                           params=params)
    for item, ext_item in itertools.product(playlists, ext_results["items"]):
        if item.get_property("youtube_id") == ext_item['id']:
            item.set_property("itemcount", ext_item['contentDetails']['itemCount'])
    return playlists


def handle_channels(results):
    """
    process channel api result to ItemList
    """
    channels = ItemList(content_type="videos")
    for item in results:
        snippet = item["snippet"]
        thumb = snippet["thumbnails"]["high"]["url"] if "thumbnails" in snippet else ""
        try:
            channel_id = item["id"]["channelId"]
        except Exception:
            channel_id = snippet["resourceId"]["channelId"]
        channel = VideoItem(label=snippet["title"],
                            path=PLUGIN_BASE + 'youtubechannel&&id=%s' % channel_id)
        channel.set_infos({'plot': snippet["description"],
                           'mediatype': "video",
                           'premiered': snippet["publishedAt"][:10]})
        channel.set_art("thumb", thumb)
        channel.set_properties({"youtube_id": channel_id,
                                "type": "channel"})
        channels.append(channel)
    channel_ids = [item.get_property("youtube_id") for item in channels]
    params = {"id": ",".join(channel_ids),
              "part": "contentDetails,statistics,brandingSettings"}
    ext_results = get_data(method="channels",
                           params=params)
    for item, ext_item in itertools.product(channels, ext_results["items"]):
        if item.get_property("youtube_id") == ext_item['id']:
            item.set_property("itemcount", ext_item['statistics']['videoCount'])
            item.set_art("fanart", ext_item["brandingSettings"]["image"].get("bannerTvMediumImageUrl"))
    return channels


def get_data(method, params=None, cache_days=0.5):
    """
    fetch data from youtube API
    """
    params = params if params else {}
    params["key"] = YT_KEY
    params = {k: unicode(v).encode('utf-8') for k, v in params.iteritems() if v}
    url = "{base_url}{method}?{params}".format(base_url=BASE_URL,
                                               method=method,
                                               params=urllib.urlencode(params))
    return utils.get_JSON_response(url=url,
                                   cache_days=cache_days,
                                   folder="YouTube")


def search(search_str="", hd="", orderby="relevance", limit=40, extended=True, page="", filters=None, media_type="video"):
    """
    returns ItemList according to search term, filters etc.
    """
    params = {"part": "id,snippet",
              "maxResults": limit,
              "type": media_type,
              "order": orderby,
              "pageToken": page,
              "hd": str(hd and not hd == "false"),
              "q": search_str.replace('"', '')}
    results = get_data(method="search",
                       params=utils.merge_dicts(params, filters if filters else {}))
    if not results:
        return None
    if media_type == "video":
        listitems = handle_videos(results["items"], extended=extended)
    elif media_type == "playlist":
        listitems = handle_playlists(results["items"])
    elif media_type == "channel":
        listitems = handle_channels(results["items"])
    listitems.total_pages = results["pageInfo"]["resultsPerPage"]
    listitems.totals = results["pageInfo"]["totalResults"]
    listitems.next_page_token = results.get("nextPageToken", "")
    listitems.prev_page_token = results.get("prevPageToken", "")
    return listitems


def get_playlist_videos(playlist_id=""):
    """
    returns ItemList from playlist with *playlist_id
    """
    if not playlist_id:
        return []
    params = {"part": "id,snippet",
              "maxResults": "50",
              "playlistId": playlist_id}
    results = get_data(method="playlistItems",
                       params=params)
    if not results:
        return []
    return handle_videos(results["items"])


def get_user_playlists(username=""):
    """
    returns ItemList with user uploads from *username
    """
    params = {"part": "contentDetails",
              "forUsername": username}
    results = get_data(method="channels",
                       params=params)
    if not results["items"]:
        return None
    return results["items"][0]["contentDetails"]["relatedPlaylists"]
