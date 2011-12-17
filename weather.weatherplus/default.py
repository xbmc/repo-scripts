# coding: utf-8

#***********************************************************
# 
#     Weather Plus XBMC Addon
#
#                           created by brightsr
#                           - based on Nuka1195's script
#
#***********************************************************

import xbmc

__plugin__ = "Weather Plus"
__version__ = "3.0.0"

xbmc.log( "[PLUGIN] '%s: Version - %s' initialized!" % ( __plugin__, __version__ ), xbmc.LOGNOTICE )     

if ( __name__ == "__main__" ):
    from main import Main
    Main()
    
