from Utils import *

YT_KEY = 'AI39si4DkJJhM8cm7GES91cODBmRR-1uKQuVNkJtbZIVJ6tRgSvNeUh4somGAjUwGlvHFj3d0kdvJdLqD0aQKTh6ttX7t_GjpQ'
YT_KEY_2 = 'AIzaSyB-BOZ_o09NLVwq_lMskvvj1olDkFI4JK0'


def HandleYouTubeVideoResults(results):
    videos = []
    log("starting HandleYouTubeVideoResults")
    for item in results:
            thumb = ""
            if "thumbnails" in item["snippet"]:
                thumb = item["snippet"]["thumbnails"]["high"]["url"]
            try:
                videoid = item["id"]["videoId"]
            except:
                videoid = item["snippet"]["resourceId"]["videoId"]
            video = {'Thumb': thumb,
                     'youtube_id': videoid,
                     'Play': 'plugin://script.extendedinfo/?info=youtubevideo&&id=%s' % videoid,
                     'Path': 'plugin://script.extendedinfo/?info=youtubevideo&&id=%s' % videoid,
                     'Description': item["snippet"]["description"],
                     'Title': item["snippet"]["title"],
                     # 'Author': item["author"][0]["name"]["$t"],
                     'Date': item["snippet"]["publishedAt"].replace("T", " ").replace(".000Z", "")[:-3]}
            videos.append(video)
    return videos


def GetYoutubeSearchVideos(search_string="", hd="", orderby="relevance", limit=50):
    results = []
    if hd and not hd == "false":
        hd_string = "&hd=true"
    else:
        hd_string = ""
    search_string = url_quote(search_string.replace('"', ''))
    base_url = 'https://www.googleapis.com/youtube/v3/search?part=id%2Csnippet&type=video'
    url = '&q=%s&order=%s&key=%s%s&maxResults=%i' % (search_string, orderby, YT_KEY_2, hd_string, int(limit))
    results = Get_JSON_response(base_url + url, 0.5)
    if results:
        return HandleYouTubeVideoResults(results["items"])
    else:
        return []


def GetYoutubePlaylistVideos(playlistid=""):
    base_url = 'https://www.googleapis.com/youtube/v3/playlistItems?part=id%2Csnippet&maxResults=50'
    url = '&playlistId=%s&key=%s' % (playlistid, YT_KEY_2)
    results = Get_JSON_response(base_url + url, 0.5)
    if results:
        return HandleYouTubeVideoResults(results["items"])
    else:
        return []


def GetUserPlaylists(username=""):
    base_url = 'https://www.googleapis.com/youtube/v3/channels?part=contentDetails'
    url = '&forUsername=%s&key=%s' % (username, YT_KEY_2)
    results = Get_JSON_response(base_url + url, 30)
    return results["items"][0]["contentDetails"]["relatedPlaylists"]
