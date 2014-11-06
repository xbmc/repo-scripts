# -*- coding: utf-8 -*-
import xbmc, xbmcgui
import urllib
import YDStreamExtractor as StreamExtractor
import YDStreamUtils as StreamUtils
import common

def getURLMediaType(url):
    if url.startswith('http'):
        videoTypes = xbmc.getSupportedMedia('video')
        musicTypes = xbmc.getSupportedMedia('music')
        imageTypes = xbmc.getSupportedMedia('picture')
        ext = url.rsplit('.',1)[-1]
        if ext in videoTypes:
            return 'video'
        elif ext in musicTypes:
            return 'audio'
        elif ext in imageTypes:
            return 'image'
    return protocolMediaType(url)

def canHandle(data):
    if data.get('type') == 'link':
        url = data.get('url','')
        if StreamExtractor.mightHaveVideo(url): return 'video'
        mediaType = getURLMediaType(url)
        if mediaType: return mediaType
        return canPlayURL(url) and 'video' or None
    elif data.get('type') == 'file':
        fType = data.get('file_type','')[:5]
        if fType in ('image','video','audio'): return fType
    elif data.get('type') == 'note':
        return 'note'
    elif data.get('type') == 'list':
        return 'list'
    elif data.get('type') == 'address':
        return 'address'
    return None

def checkForWindow():
    if not xbmc.getCondVisibility('IsEmpty(Window.Property(pushbullet))'):
        xbmc.executebuiltin('Action(info)')
        return True

def handlePush(data,from_gui=False):
    if not from_gui and checkForWindow(): #Do nothing if the window is open
        return False
    if data.get('type') == 'link':
        url = data.get('url','')
        if StreamExtractor.mightHaveVideo(url):
            vid = StreamExtractor.getVideoInfo(url)
            if vid:
                if vid.hasMultipleStreams():
                    vlist = []
                    for info in vid.streams():
                        vlist.append(info['title'] or '?')
                    idx = xbmcgui.Dialog().select(common.localise(32091),vlist)
                    if idx < 0: return
                    vid.selectStream(idx)
                playMedia(vid.streamURL(),vid.title,vid.thumbnail,vid.description)
                return True
        if canPlayURL(url):
            handleURL(url)
            return True
        media = getURLMediaType(url)
        if media == 'video' or media == 'audio':
            url += '|' + urllib.urlencode({'User-Agent':getURLUserAgent(url)})
            playMedia(url,playlist_type='video' and xbmc.PLAYLIST_VIDEO or xbmc.PLAYLIST_MUSIC)
            return True
        elif media == 'image':
            import gui
            gui.showImage(url)
            return True
    elif data.get('type') == 'file':
        if data.get('file_type','').startswith('image/'):
            import gui
            gui.showImage(data.get('file_url',''))
            return True
        elif data.get('file_type','').startswith('video/') or data.get('file_type','').startswith('audio/'):
            playMedia(data.get('file_url',''))
            return True
    elif data.get('type') == 'note':
        import gui
        gui.showNote(data.get('body',''))
        return True
    elif data.get('type') == 'list':
        import gui
        gui.showList(data)
        return True
    elif data.get('type') == 'address':
        cmd = 'XBMC.RunScript({0},MAP,{1},None,)'.format(common.__addonid__,urllib.quote(data.get('address','')))
        xbmc.executebuiltin(cmd)
        return True

    return False
    
protocolURLs = {
    'sop':'plugin://plugin.video.p2p-streams/?url={url}&mode=2&name=title+sopcast',
    'acestream':'plugin://plugin.video.p2p-streams/?url={url}&mode=1&name=acestream+title',
    'mms':'{url}',
    'rtsp':'{url}',
    'rtmp':'{url}'
}
def protocolMediaType(url):
    protocol = url.split('://',1)[0]
    if protocol in protocolURLs: return 'video'
    return None
    
def canPlayURL(url):
    protocol = url.split('://',1)[0]
    return protocol in protocolURLs

def handleURL(url):
    protocol = url.split('://',1)[0]
    if protocol in protocolURLs:
        pluginURL = protocolURLs[protocol].format(url=url)
        playMedia(pluginURL)

def getURLUserAgent(url):
    if url.lower().endswith('.mov'): #TODO: perhaps do a regex instead in case of params after file name, and perhaps only if apple.com
        return 'QuickTime compatible (Kodi)'
    return  'Mozilla/5.0 (X11; Linux x86_64; rv:10.0) Gecko/20100101 Firefox/10.0 (Chrome)'

def playMedia(url,title='',thumb='',description='',playlist_type=xbmc.PLAYLIST_VIDEO):
    common.log('Play media: ' + url)
   
    li = xbmcgui.ListItem(label=title,label2=description,iconImage=thumb,thumbnailImage=thumb)
    li.setPath(url)
    li.setInfo('video',{'title':title,'tagline':description})
    pl = xbmc.PlayList(playlist_type)
    pl.clear()
    pl.add(url,li)
    xbmc.Player().play(pl)

def mediaPlaying(): #TODO: make sure we're checking for all media
    return StreamUtils.isPlaying()

#    xbmc.executeJSONRPC('{"jsonrpc":"2.0","id":1,"method":"Playlist.Clear","params":{"playlistid":1}}')
#    xbmc.executeJSONRPC('{"jsonrpc":"2.0","id":1,"method":"Playlist.Add","params":{"playlistid":1,"item":{"file":"' + str(url) + '"}}}')
#    return xbmc.executeJSONRPC('{"jsonrpc":"2.0","id":1,"method":"Player.Open","params":{"item":{"playlistid":1,"position":0}}}')

    
    '''{u'iden': u'ujxCHwc6fiSsjAl11HK7y0',
        u'created': 1411009240.141888,
        u'receiver_email': u'ruuk25@gmail.com',
        u'items': [],
        u'target_device_iden': u'ujxCHwc6fiSsjz477zOU0a',
        u'file_url': u'https://s3.amazonaws.com/pushbullet-uploads/ujxCHwc6fiS-wnH7qXNVOruppCCglRlC6iUXWHWR5xEV/IMG_20140827_164312.jpg',
        u'modified': 1411009240.149686, u'dismissed': False,
        u'sender_email_normalized': u'ruuk25@gmail.com',
        u'file_type': u'image/jpeg',
        u'image_url': u'https://pushbullet.imgix.net/ujxCHwc6fiS-wnH7qXNVOruppCCglRlC6iUXWHWR5xEV/IMG_20140827_164312.jpg',
        u'sender_email': u'ruuk25@gmail.com',
        u'file_name': u'IMG_20140827_164312.jpg',
        u'active': True,
        u'receiver_iden': u'ujxCHwc6fiS',
        u'sender_iden': u'ujxCHwc6fiS',
        u'type': u'file',
        u'receiver_email_normalized': u'ruuk25@gmail.com'}'''
