#v.0.1.0

import imghdr, os, xbmc

def itemHash(item):
    return xbmc.getCacheThumbName(item).replace('.tbn', '')
    
def itemHashwithPath(item, thepath):
    thumb = xbmc.getCacheThumbName(item).replace('.tbn', '')
    thumbpath = os.path.join(thepath, thumb.encode('utf-8'))
    return thumbpath
    
def getImageType( filename ):
    try:
        new_ext = '.' + imghdr.what( filename ).replace( 'jpeg', 'jpg' )
    except Exception, e:
        new_ext = '.'
    if new_ext == '.':
        new_ext = '.tbn'
    return new_ext
