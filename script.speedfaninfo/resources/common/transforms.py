#v.0.1.1

import imghdr, os
try:
    import xbmc
    isXBMC = True
except:
    import hashlib
    isXBMC = False

def itemHash(item):
    if isXBMC:
        return xbmc.getCacheThumbName(item).replace('.tbn', '')
    else:
        return hashlib.md5( item.encode() ).hexdigest()
    
def itemHashwithPath(item, thepath):
    if isXBMC:
        thumb = xbmc.getCacheThumbName(item).replace('.tbn', '')
    else:
        thumb = hashlib.md5( item.encode() ).hexdigest()
    thumbpath = os.path.join( thepath, thumb.encode( 'utf-8' ) )
    return thumbpath
    
def getImageType( filename ):
    try:
        new_ext = '.' + imghdr.what( filename ).replace( 'jpeg', 'jpg' )
    except Exception, e:
        new_ext = '.tbn'
    return new_ext
