# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

from Utils import *

YT_KEY = 'AIzaSyB-BOZ_o09NLVwq_lMskvvj1olDkFI4JK0'
BASE_URL = "https://www.googleapis.com/youtube/v3/"


def handle_youtube_videos(results, extended=False):
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
                 'Play': 'plugin://script.extendedinfo/?info=youtubevideo&&id=%s' % video_id,
                 'path': 'plugin://script.extendedinfo/?info=youtubevideo&&id=%s' % video_id,
                 'Description': item["snippet"]["description"],
                 'title': item["snippet"]["title"],
                 'channel_title': item["snippet"]["channelTitle"],
                 'channel_id': item["snippet"]["channelId"],
                 'Date': item["snippet"]["publishedAt"].replace("T", " ").replace(".000Z", "")[:-3]}
        videos.append(video)
    if not extended:
        return videos
    video_ids = [item["youtube_id"] for item in videos]
    url = "videos?id=%s&part=contentDetails%%2Cstatistics&key=%s" % (",".join(video_ids), YT_KEY)
    ext_results = get_JSON_response(url=BASE_URL + url,
                                    cache_days=0.5,
                                    folder="YouTube")
    if not ext_results:
        return videos
    for i, item in enumerate(videos):
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


def handle_youtube_playlists(results):
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
                    'Play': 'plugin://script.extendedinfo/?info=youtubeplaylist&&id=%s' % playlist_id,
                    'path': 'plugin://script.extendedinfo/?info=youtubeplaylist&&id=%s' % playlist_id,
                    'title': item["snippet"]["title"],
                    'description': item["snippet"]["description"],
                    'channel_title': item["snippet"]["channelTitle"],
                    'live': item["snippet"]["liveBroadcastContent"].replace("none", ""),
                    'Date': item["snippet"]["publishedAt"].replace("T", " ").replace(".000Z", "")[:-3]}
        playlists.append(playlist)
    playlist_ids = [item["youtube_id"] for item in playlists]
    url = "playlists?id=%s&part=contentDetails&key=%s" % (",".join(playlist_ids), YT_KEY)
    ext_results = get_JSON_response(url=BASE_URL + url,
                                    cache_days=0.5,
                                    folder="YouTube")
    for i, item in enumerate(playlists):
        for ext_item in ext_results["items"]:
            if item["youtube_id"] == ext_item['id']:
                item["itemcount"] = ext_item['contentDetails']['itemCount']
    return playlists


def handle_youtube_channels(results):
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
                   'Play': 'plugin://script.extendedinfo/?info=youtubechannel&&id=%s' % channel_id,
                   'path': 'plugin://script.extendedinfo/?info=youtubechannel&&id=%s' % channel_id,
                   'Description': item["snippet"]["description"],
                   'title': item["snippet"]["title"],
                   'Date': item["snippet"]["publishedAt"].replace("T", " ").replace(".000Z", "")[:-3]}
        channels.append(channel)
    channel_ids = [item["youtube_id"] for item in channels]
    url = "channels?id=%s&part=contentDetails%%2Cstatistics%%2CbrandingSettings&key=%s" % (",".join(channel_ids), YT_KEY)
    ext_results = get_JSON_response(url=BASE_URL + url,
                                    cache_days=0.5,
                                    folder="YouTube")
    for i, item in enumerate(channels):
        for ext_item in ext_results["items"]:
            if item["youtube_id"] == ext_item['id']:
                item["itemcount"] = ext_item['statistics']['videoCount']
                item["fanart"] = ext_item["brandingSettings"]["image"].get("bannerTvMediumImageUrl", "")
    return channels


def search_youtube(search_str="", hd="", orderby="relevance", limit=40, extended=False, page="", filter_str="", media_type="video"):
    if page:
        page = "&pageToken=%s" % page
    if hd and not hd == "false":
        hd = "&hd=true"
    else:
        hd = ""
    search_str = "&q=%s" % url_quote(search_str.replace('"', ''))
    url = 'search?part=id%%2Csnippet&type=%s%s%s&order=%s&%skey=%s%s&maxResults=%i' % (media_type, page, search_str, orderby, filter_str, YT_KEY, hd, int(limit))
    results = get_JSON_response(url=BASE_URL + url,
                                cache_days=0.5,
                                folder="YouTube")
    if media_type == "video":
        videos = handle_youtube_videos(results["items"], extended=True)
    elif media_type == "playlist":
        videos = handle_youtube_playlists(results["items"])
    elif media_type == "channel":
        videos = handle_youtube_channels(results["items"])
    if videos:
        info = {"listitems": videos,
                "results_per_page": results["pageInfo"]["resultsPerPage"],
                "total_results": results["pageInfo"]["totalResults"],
                "next_page_token": results.get("nextPageToken", ""),
                "prev_page_token": results.get("prevPageToken", ""),
                }
        return info
    else:
        return {}


def get_youtube_playlist_videos(playlist_id=""):
    url = 'playlistItems?part=id%%2Csnippet&maxResults=50&playlistId=%s&key=%s' % (playlist_id, YT_KEY)
    results = get_JSON_response(url=BASE_URL + url,
                                cache_days=0.5,
                                folder="YouTube")
    if results:
        return handle_youtube_videos(results["items"])
    else:
        return []


def get_youtube_user_playlists(username=""):
    url = 'channels?part=contentDetails&forUsername=%s&key=%s' % (username, YT_KEY)
    results = get_JSON_response(url=BASE_URL + url,
                                cache_days=0.5,
                                folder="YouTube")
    if results["items"]:
        return results["items"][0]["contentDetails"]["relatedPlaylists"]
    else:
        return None
