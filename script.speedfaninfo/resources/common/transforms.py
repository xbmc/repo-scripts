#v.0.3.1

import imghdr, os, re
try:
    from kodi_six import xbmc
    isXBMC = True
except:
    import hashlib
    isXBMC = False

def itemHash(item):
    if isXBMC:
        try:
            hash_item = xbmc.getCacheThumbName(item).replace('.tbn', '')
        except TypeError:
            hash_item = ''  
    else:
        try:
            hash_item = hashlib.md5( item.encode() ).hexdigest()
        except TypeError:
            hash_item = ''  
    return hash_item
    
def itemHashwithPath(item, thepath):
    if isXBMC:
        try:
            thumb = xbmc.getCacheThumbName(item).replace('.tbn', '')
        except TypeError:
            return ''  
    else:
        try:
            thumb = hashlib.md5( item.encode() ).hexdigest()
        except TypeError:
            return ''  
    thumbpath = os.path.join( thepath, thumb.encode( 'utf-8' ) )
    return thumbpath
    
def getImageType( filename ):
    try:
        new_ext = '.' + imghdr.what( filename ).replace( 'jpeg', 'jpg' )
    except Exception as e:
        new_ext = '.tbn'
    return new_ext

def replaceWords( text, word_dic ):
    """
    take a text and replace words that match a key in a dictionary with
    the associated value, return the changed text
    """
    rc = re.compile( '|'.join( map( re.escape, word_dic ) ) )
    def translate(match):
        return word_dic[match.group(0)]
    return rc.sub(translate, text)
