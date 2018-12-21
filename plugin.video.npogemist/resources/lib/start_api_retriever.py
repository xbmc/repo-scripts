import json
try:
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError
except ImportError:
    from urllib2 import urlopen, Request, HTTPError

import errors


def json_request(url):
    try:
        req = Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:25.0) Gecko/20100101 Firefox/25.0')
        req.add_header('ApiKey', 'e45fe473feaf42ad9a215007c6aa5e7e')
        response = urlopen(req)
        data = json.load(response)
        response.close()
        return data
    except HTTPError:
        # not found.
        raise errors.NPOContentError


def retrieve_epg_by_date(npo_date):
    return json_request("https://start-api.npo.nl/epg/{0}?type=tv".format(npo_date))

def retrieve_episode_by_id(episode_code):
    return json_request("https://start-api.npo.nl/page/episode/{0}".format(episode_code))

def retrieve_series_by_id(series_code):
    return json_request("https://start-api.npo.nl/page/franchise/{0}".format(series_code))

def retrieve_filters():
    return json_request("https://start-api.npo.nl/page/catalogue?pageSize=0")

def retrieve_series(letter):
    return json_request("https://start-api.npo.nl/page/catalogue?az={0}&pageSize=1000".format(letter))

def retrieve_series_random():
    return json_request("https://start-api.npo.nl/page/catalogue?pageSize=500")

def retrieve_series_genre(genre):
    return json_request("https://start-api.npo.nl/page/catalogue?genreId={0}&pageSize=1000".format(genre))

def retrieve_items_by_search(search_name):
    return json_request("https://start-api.npo.nl/search?query={0}&pageSize=1000".format(search_name))

def retrieve_video_data(mid):
    # request token
    tokendata = json_request("http://ida.omroep.nl/app.php/auth")
    token = tokendata["token"]
    # request video url
    odidata = json_request("http://ida.omroep.nl/app.php/{0}?adaptive=yes&part=1&token={1}".format(mid, token))
    # pick the first url to find the video file
    odiurl = get_video_url(odidata)
    # change the jsonp parameter to json
    jsonodiurl = odiurl.replace("type=jsonp", "type=json")
    # get the endpoint
    videodata = json_request(jsonodiurl)
    return videodata


def get_video_url(odidata):
    return odidata['items'][0][0]['url']


if __name__ == '__main__':
    import pprint
    mid = "KN_1699117"
    tokendata = json_request("http://ida.omroep.nl/app.php/auth")
    print("auth at http://ida.omroep.nl/app.php/auth")
    pprint.pprint(tokendata)
    token = tokendata["token"]
    print(token)
    # request video url
    odidata = json_request("http://ida.omroep.nl/app.php/{0}?adaptive=yes&part=1&token={1}".format(mid, token))
    print "video data at " + "http://ida.omroep.nl/app.php/{0}?adaptive=yes&part=1&token={1}".format(mid, token)
    pprint.pprint(odidata)
    # pick the first url to find the video file
    for iteml in odidata['items']:
        for item in iteml:
            odiurl = item['url']
            print(odiurl)
            # change the jsonp parameter to json
            jsonodiurl = odiurl.replace("type=jsonp", "type=json")
            print(jsonodiurl)
            # get the endpoint
            videodata = json_request(jsonodiurl)
            pprint.pprint(videodata)

    # https://content1a.omroep.nl/urishieldv2/l27m698d15cd1cdece9c005c1cf7ad000000.e544c8d040f32bb8f2caf83a9b777971/ceresodi/h264/p/00/10/10/c3/std_KN_1699117.m4v?odiredirecturl=%2Fvideo%2Fida%2Fh264_std%2F97da9841bdd5d2344f086833954b2bd3%2F5c1cf7ac%2FKN_1699117%2F1%3Ftype%3Djson%26callback%3D%3F