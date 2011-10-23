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
    Medialist = []
    if media_type == 'Movies':
        sql_data = "select c00 as name,c09 as imdb, strPath as path from movie join files on files.idFile=movie.idFile join path on path.idPath = files.idPath"
    elif media_type == 'TVShows':
        sql_data = "select tvshow.c00, tvshow.c12, path.strPath from tvshow, path, tvshowlinkpath where path.idPath = tvshowlinkpath.idPath AND tvshow.idShow = tvshowlinkpath.idShow"
    else: return Medialist
    ### SQL statement for xbmc database
    log('Populating Medialist', xbmc.LOGNOTICE)
    xml_data = xbmc.executehttpapi("QueryVideoDatabase(%s)" % urllib.quote_plus(sql_data), )
    log("### DB XML data: %s" % xml_data, xbmc.LOGNOTICE)
    match = re.findall("<field>(.*?)</field><field>(.*?)</field><field>(.*?)</field>", xml_data, re.DOTALL)
    for item in match:
        Media = {}
        Media["name"] = repr(item[0]).strip("'u")
        Media["id"] = repr(item[1]).strip("'u")
        Media["path"] = item[2]
        Medialist.append(Media)
    return Medialist
