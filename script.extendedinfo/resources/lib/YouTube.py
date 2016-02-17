# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

from Utils import *
import urllib
import itertools

YT_KEY = 'AIzaSyB-BOZ_o09NLVwq_lMskvvj1olDkFI4JK0'
BASE_URL = "https://www.googleapis.com/youtube/v3/"
PLUGIN_BASE = "plugin://script.extendedinfo/?info="


def handle_videos(results, extended=False):
    videos = []
    for item in results:
        thumb = ""
        if "thumbnails" in item["snippet"]:
            thumb = item["snippet"]["thumbnails"]["high"]["url"]
        try:
            video_id = item["id"]["videoId"]
        except:
            video_id = item["snippet"]["resourceId"]["videoId"]
        video = {'thumb': thumb,
                 'youtube_id': video_id,
                 'Play': PLUGIN_BASE + 'youtubevideo&&id=%s' % video_id,
                 'path': PLUGIN_BASE + 'youtubevideo&&id=%s' % video_id,
                 'Description': item["snippet"]["description"],
                 'title': item["snippet"]["title"],
                 'channel_title': item["snippet"]["channelTitle"],
                 'channel_id': item["snippet"]["channelId"],
                 'Date': item["snippet"]["publishedAt"].replace("T", " ").replace(".000Z", "")[:-3]}
        videos.append(video)
    if not extended:
        return videos
    params = {"part": "contentDetails,statistics",
              "id": ",".join([i["youtube_id"] for i in videos])}
    ext_results = get_data(method="videos",
                           params=params)
    if not ext_results:
        return videos
    for item in videos:
        for ext_item in ext_results["items"]:
            if not item["youtube_id"] == ext_item['id']:
                continue
            item["duration"] = ext_item['contentDetails']['duration'][2:].lower()
            item["dimension"] = ext_item['contentDetails']['dimension']
            item["definition"] = ext_item['contentDetails']['definition']
            item["caption"] = ext_item['contentDetails']['caption']
            item["viewcount"] = millify(ext_item['statistics']['viewCount'])
            item["likes"] = ext_item['statistics'].get('likeCount')
            item["dislikes"] = ext_item['statistics'].get('dislikeCount')
            if item["likes"] and item["dislikes"]:
                vote_count = float(int(item["likes"]) + int(item["dislikes"]))
                if vote_count > 0:
                    item["rating"] = format(float(item["likes"]) / vote_count * 10, '.2f')
            break
        else:
            item["duration"] = ""
    return videos


def handle_playlists(results):
    playlists = []
    for item in results:
        thumb = ""
        if "thumbnails" in item["snippet"]:
            thumb = item["snippet"]["thumbnails"]["high"]["url"]
        try:
            playlist_id = item["id"]["playlistId"]
        except:
            playlist_id = item["snippet"]["resourceId"]["playlistId"]
        playlist = {'thumb': thumb,
                    'youtube_id': playlist_id,
                    'Play': PLUGIN_BASE + 'youtubeplaylist&&id=%s' % playlist_id,
                    'path': PLUGIN_BASE + 'youtubeplaylist&&id=%s' % playlist_id,
                    'title': item["snippet"]["title"],
                    'description': item["snippet"]["description"],
                    'channel_title': item["snippet"]["channelTitle"],
                    'live': item["snippet"]["liveBroadcastContent"].replace("none", ""),
                    'Date': item["snippet"]["publishedAt"].replace("T", " ").replace(".000Z", "")[:-3]}
        playlists.append(playlist)
    params = {"id": ",".join([i["youtube_id"] for i in playlists]),
              "part": "contentDetails"}
    ext_results = get_data(method="playlists",
                           params=params)
    for item, ext_item in itertools.product(playlists, ext_results["items"]):
        if item["youtube_id"] == ext_item['id']:
            item["itemcount"] = ext_item['contentDetails']['itemCount']
    return playlists


def handle_channels(results):
    channels = []
    for item in results:
        thumb = ""
        if "thumbnails" in item["snippet"]:
            thumb = item["snippet"]["thumbnails"]["high"]["url"]
        try:
            channel_id = item["id"]["channelId"]
        except:
            channel_id = item["snippet"]["resourceId"]["channelId"]
        channel = {'thumb': thumb,
                   'youtube_id': channel_id,
                   'Play': PLUGIN_BASE + 'youtubechannel&&id=%s' % channel_id,
                   'path': PLUGIN_BASE + 'youtubechannel&&id=%s' % channel_id,
                   'Description': item["snippet"]["description"],
                   'title': item["snippet"]["title"],
                   'Date': item["snippet"]["publishedAt"].replace("T", " ").replace(".000Z", "")[:-3]}
        channels.append(channel)
    channel_ids = [item["youtube_id"] for item in channels]
    params = {"id": ",".join(channel_ids),
              "part": "contentDetails,statistics,brandingSettings"}
    ext_results = get_data(method="channels",
                           params=params)
    for item, ext_item in itertools.product(channels, ext_results["items"]):
        if item["youtube_id"] == ext_item['id']:
            item["itemcount"] = ext_item['statistics']['videoCount']
            item["fanart"] = ext_item["brandingSettings"]["image"].get("bannerTvMediumImageUrl", "")
    return channels


def get_data(method, params={}, cache_days=0.5):
    params["key"] = YT_KEY
    # params = {k: v for k, v in params.items() if v}
    params = dict((k, v) for (k, v) in params.iteritems() if v)
    params = dict((k, unicode(v).encode('utf-8')) for (k, v) in params.iteritems())
    url = "{base_url}{method}?{params}".format(base_url=BASE_URL,
                                               method=method,
                                               params=urllib.urlencode(params))
    return get_JSON_response(url=url,
                             cache_days=cache_days,
                             folder="YouTube")


def search(search_str="", hd="", orderby="relevance", limit=40, extended=True, page="", filters={}, media_type="video"):
    params = {"part": "id,snippet",
              "maxResults": int(limit),
              "type": media_type,
              "order": orderby,
              "pageToken": page,
              "hd": str(hd and not hd == "false"),
              "q": search_str.replace('"', '')}
    params = merge_dicts(params, filters)
    results = get_data(method="search",
                       params=params)
    if media_type == "video":
        listitems = handle_videos(results["items"], extended=extended)
    elif media_type == "playlist":
        listitems = handle_playlists(results["items"])
    elif media_type == "channel":
        listitems = handle_channels(results["items"])
    if not listitems:
        return {}
    return {"listitems": listitems,
            "results_per_page": results["pageInfo"]["resultsPerPage"],
            "total_results": results["pageInfo"]["totalResults"],
            "next_page_token": results.get("nextPageToken", ""),
            "prev_page_token": results.get("prevPageToken", "")}


def get_playlist_videos(playlist_id=""):
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
    params = {"part": "contentDetails",
              "forUsername": username}
    results = get_data(method="channels",
                       params=params)
    if not results["items"]:
        return None
    return results["items"][0]["contentDetails"]["relatedPlaylists"]
