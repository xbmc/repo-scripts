import collections
import xbmcgui

# JSON keys that don't match info labels
infokey_map = {
    'track': 'tracknumber',
    'runtime': 'duration',
    'showtitle': 'tvshowtitle',
    'imdbnumber': 'code',
    'uniqueid': 'code',
    'firstaired': 'aired'
}

def build_video_listitem(item):
    result = xbmcgui.ListItem(item.get('label'))
    if 'label2' in item:
        result.setLabel2(item['label2'])

    infolabels = {}
    for key, value in item.iteritems():
        if isinstance(value, collections.Mapping):
            continue
        if key in (infokey_map.keys()):
            infolabels[infokey_map[key]] = value

        infolabels[key] = value
        if isinstance(value, basestring):
            result.setProperty(key, value)
        elif isinstance(value, collections.Iterable):
            result.setProperty(key, list_to_str(value))
        else:
            result.setProperty(key, str(value))
    result.setInfo('video', infolabels)

    if 'file' in item:
        result.setPath(item['file'])

    if 'art' in item:
        result.setArt(item['art'])

    if 'streamdetails' in item:
        for streamtype, streams in item['streamdetails'].iteritems():
            for stream in streams:
                result.addStreamInfo(streamtype, stream)
    return result

def list_to_str(input_list):
    if isinstance(input_list, list):
        return ' / '.join(input_list)
    else:
        return str(input_list)
