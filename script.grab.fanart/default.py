import resources.lib.utils as utils

utils.log("updating settings",xbmc.LOGDEBUG)
if(len(sys.argv) > 1):
    for arg in sys.argv:
        #make sure it is a key/value pair
        if "=" in arg:
            splitString = arg.split('=')
            utils.log(splitString[0])
            utils.setSetting(splitString[0],splitString[1])
            
            
