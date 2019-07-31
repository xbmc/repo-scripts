
try:
    import xbmc
    KODI_ENV = False

    if type(xbmc.getFreeMem()) != int:
        KODI_ENV = False
    else:
        KODI_ENV = True
except:
    KODI_ENV = False
