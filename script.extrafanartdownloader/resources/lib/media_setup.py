import re
import xbmc
import urllib

def log(txt, severity=xbmc.LOGDEBUG):
    """Log to txt xbmc.log at specified severity"""
    message = 'script.extrafanartdownloader: %s' % txt
    xbmc.log(msg=message, level=severity)

### get list of all tvshows and movies with their imdbnumber from library
### copied from script.logo-downloader, thanks to it's authors
def media_listing(media_type):
    json_query = xbmc.executeJSONRPC('{"jsonrpc": "2.0", "method": "VideoLibrary.Get%s", "params": {"properties": ["file", "imdbnumber"], "sort": { "method": "label" } }, "id": 1}' % media_type)
    json_response = re.compile( "{(.*?)}", re.DOTALL ).findall(json_query)
    Medialist = []
    for mediaitem in json_response:
        findmedianame = re.search( '"label":"(.*?)","', mediaitem )
        if findmedianame:
            medianame = ( findmedianame.group(1) )
            findpath = re.search( '"file":"(.*?)","', mediaitem )
            if findpath:
                path = (findpath.group(1))
                findimdbnumber = re.search( '"imdbnumber":"(.*?)","', mediaitem )
                if findimdbnumber:
                    imdbnumber = (findimdbnumber.group(1))
                    Media = {}
                    Media["name"] = medianame
                    Media["id"] = imdbnumber
                    Media["path"] = path
                    Medialist.append(Media)
    return Medialist
