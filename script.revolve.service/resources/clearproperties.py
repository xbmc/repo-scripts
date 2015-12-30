# *  Function: Revolve/ClearProperties

import sys
import xbmc

import xbmclibrary

FUNCTIONNAME = 'Revolve/ClearProperties'
DEFAULTTARGETWINDOW = '0'
DEFAULTTARGETMASK = 'List%02dOption'
TOTALITEMS = 20

def clearPropertiesByMask(targetmask, targetwindow):
    for index in range (1, TOTALITEMS + 1):
        targetbase = targetmask % (index)

        xbmclibrary.clearProperty(targetbase + '.Name', targetwindow)
        xbmclibrary.clearProperty(targetbase + '.Subtitle', targetwindow)
        xbmclibrary.clearProperty(targetbase + '.Thumbnail', targetwindow)
        xbmclibrary.clearProperty(targetbase + '.BackgroundImage', targetwindow)
        xbmclibrary.clearProperty(targetbase + '.Action', targetwindow)

def execute(arguments):
    if len(arguments) > 2:
        targetmask = arguments[2]
    else:
        targetmask = DEFAULTTARGETMASK
    
    if len(arguments) > 3:
        targetwindow = arguments[3]
    else:
        targetwindow = DEFAULTTARGETWINDOW
    
    clearPropertiesByMask(targetmask, targetwindow)
