# *  Function: Revolve/PopulateSubmenuFromSkinVariables

import sys
import xbmc

import baselibrary
import xbmclibrary

FUNCTIONNAME = 'Revolve/PopulateSubmenuFromSkinVariables'
DEFAULTTARGETMASK = 'MySubmenu%02dOption'
DEFAULTTARGETWINDOW = '0'
TOTALITEMS = 20

def copyProperties(sourcemask, targetmask, targetwindow):
    for index in range (1, TOTALITEMS + 1):
        sourcebase = sourcemask % (index)
        targetbase = targetmask % (index)

        xbmclibrary.copySkinSettingToProperty(sourcebase + '.Type', targetbase + '.Type', targetwindow)
        xbmclibrary.copyBooleanSkinSettingToProperty(sourcebase + '.Active', targetbase + '.Active', targetwindow)
        xbmclibrary.copySkinSettingToProperty(sourcebase + '.Name', targetbase + '.Name', targetwindow)
        xbmclibrary.copySkinSettingToProperty(sourcebase + '.Subtitle', targetbase + '.Subtitle', targetwindow)
        xbmclibrary.copySkinSettingToProperty(sourcebase + '.BackgroundImage', targetbase + '.BackgroundImage', targetwindow)
        xbmclibrary.copySkinSettingToProperty(sourcebase + '.MenuTitle', targetbase + '.MenuTitle', targetwindow)
        xbmclibrary.copySkinSettingToProperty(sourcebase + '.SourceInfo', targetbase + '.SourceInfo', targetwindow)
        xbmclibrary.copySkinSettingToProperty(sourcebase + '.Window', targetbase + '.Window', targetwindow)
        xbmclibrary.copySkinSettingToProperty(sourcebase + '.Action', targetbase + '.Action', targetwindow)

def execute(arguments):
    if len(arguments) > 2:
        sourcemask = arguments[2]
        targetmask = baselibrary.extractArgument(arguments, 3, DEFAULTTARGETMASK)
        targetwindow = baselibrary.extractArgument(arguments, 4, DEFAULTTARGETWINDOW)
        
        copyProperties(sourcemask, targetmask, targetwindow)
    else:
        xbmclibrary.writeErrorMessage(FUNCTIONNAME, FUNCTIONNAME + ' terminates: Missing argument(s) in call to script.')	
