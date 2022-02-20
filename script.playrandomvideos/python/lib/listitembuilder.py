import collections
from collections import abc
import xbmcgui


infokey_map = {
    'title': 'title',
    'season': 'season',
    'episode': 'episode',
    'playcount': 'playcount',
    'rating': 'rating',
    'userrating': 'userrating',
    # JSON keys that don't match info labels
    'track': 'tracknumber',
    'runtime': 'duration',
    'showtitle': 'tvshowtitle',
    'firstaired': 'aired'
}

mediatype_map = {'episodeid': 'episode',
    'movieid': 'movie',
    'musicvideoid': 'musicvideo'}

def build_video_listitem(item):
    result = xbmcgui.ListItem(item.get('label'))
    if 'label2' in item:
        result.setLabel2(item['label2'])

    infolabels = {}
    for key, value in item.items():
        if isinstance(value, abc.Mapping):
            continue
        if key in infokey_map:
            infolabels[infokey_map[key]] = value
        elif key in mediatype_map:
            infolabels['dbid'] = value
            infolabels['mediatype'] = mediatype_map[key]

    result.setInfo('video', infolabels)

    if 'file' in item:
        result.setPath(item['file'])

    if 'art' in item:
        result.setArt(item['art'])

    if 'streamdetails' in item:
        for streamtype, streams in item['streamdetails'].items():
            for stream in streams:
                result.addStreamInfo(streamtype, stream)
    return result

def list_to_str(input_list):
    if isinstance(input_list, list):
        return ' / '.join(input_list)
    else:
        return str(input_list)
