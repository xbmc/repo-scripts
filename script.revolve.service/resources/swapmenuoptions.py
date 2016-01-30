# *  Function: Revolve/swapMenuSkinSettings

import sys
import xbmc

import baselibrary
import xbmclibrary

FUNCTIONNAME = 'Revolve/swapMenuSkinSettings'
LOCKPROPERTY = '.Lock'

def getLockOnOption(optionbase, targetwindow):
    return xbmclibrary.getItemFromProperty(optionbase + LOCKPROPERTY, targetwindow)

def setLockOnOption(optionbase, targetwindow, lockid):
    if getLockOnOption(optionbase, targetwindow) == '':
        xbmclibrary.setItemToLockedProperty(optionbase + LOCKPROPERTY, lockid, targetwindow)
    return getLockOnOption(optionbase, targetwindow) == lockid

def releaseLockOnOption(optionbase, targetwindow):
    xbmclibrary.clearProperty(optionbase + LOCKPROPERTY, targetwindow)

def checkMenuOptionLocks(sourcebase, targetbase, targetwindow, lockid):    
    return (getLockOnOption(sourcebase, targetwindow) == lockid) and (getLockOnOption(targetbase, targetwindow) == lockid)
    
def setMenuOptionLocks(propertymask, targetwindow, index, otherindex, lockid):
    sourcebase = propertymask % (index)
    targetbase = propertymask % (otherindex)

    if checkMenuOptionLocks(sourcebase, targetbase, targetwindow, ''):
        if setLockOnOption(sourcebase, targetwindow, lockid):
            setLockOnOption(targetbase, targetwindow, lockid)
    
    return checkMenuOptionLocks(sourcebase, targetbase, targetwindow, lockid)

def releaseMenuOptionLocks(propertymask, targetwindow, index, otherindex):
    sourcebase = propertymask % (index)
    releaseLockOnOption(sourcebase, targetwindow)

    targetbase = propertymask % (otherindex)
    releaseLockOnOption(targetbase, targetwindow)

def swapMenuProperties(propertymask, targetwindow, index, otherindex):
    sourcebase = propertymask % (index)
    targetbase = propertymask % (otherindex)

    xbmclibrary.swapProperties(sourcebase + '.Type', targetbase + '.Type', targetwindow)
    xbmclibrary.swapProperties(sourcebase + '.Active', targetbase + '.Active', targetwindow)
    xbmclibrary.swapProperties(sourcebase + '.Name', targetbase + '.Name', targetwindow)
    xbmclibrary.swapProperties(sourcebase + '.Subtitle', targetbase + '.Subtitle', targetwindow)
    xbmclibrary.swapProperties(sourcebase + '.BackgroundImage', targetbase + '.BackgroundImage', targetwindow)
    xbmclibrary.swapProperties(sourcebase + '.MenuTitle', targetbase + '.MenuTitle', targetwindow)
    xbmclibrary.swapProperties(sourcebase + '.SourceInfo', targetbase + '.SourceInfo', targetwindow)
    xbmclibrary.swapProperties(sourcebase + '.Window', targetbase + '.Window', targetwindow)
    xbmclibrary.swapProperties(sourcebase + '.Action', targetbase + '.Action', targetwindow)

def swapMenuSkinSettings(skinsettingmask, index, otherindex):
    sourcebase = skinsettingmask % (index)
    targetbase = skinsettingmask % (otherindex)
    
    xbmclibrary.swapSkinSettings(sourcebase + '.Type', targetbase + '.Type')
    xbmclibrary.swapBooleanSkinSettings(sourcebase + '.Active', targetbase + '.Active')
    xbmclibrary.swapSkinSettings(sourcebase + '.Name', targetbase + '.Name')
    xbmclibrary.swapSkinSettings(sourcebase + '.Subtitle', targetbase + '.Subtitle')
    xbmclibrary.swapSkinSettings(sourcebase + '.BackgroundImage', targetbase + '.BackgroundImage')
    xbmclibrary.swapSkinSettings(sourcebase + '.MenuTitle', targetbase + '.MenuTitle')
    xbmclibrary.swapSkinSettings(sourcebase + '.SourceInfo', targetbase + '.SourceInfo')
    xbmclibrary.swapSkinSettings(sourcebase + '.Window', targetbase + '.Window')
    xbmclibrary.swapSkinSettings(sourcebase + '.Action', targetbase + '.Action')

    
def execute(arguments):
    if len(arguments) > 6:
        skinsettingmask = arguments[2]
        propertymask = arguments[3]
        index = int(arguments[4])
        otherindex = int(arguments[5])
        targetwindow = arguments[6]
        lockid = 'Lock' + str(index) + str(otherindex) + str(baselibrary.getTimeInMilliseconds())

        if setMenuOptionLocks(propertymask, targetwindow, index, otherindex, lockid):
            swapMenuSkinSettings(skinsettingmask, index, otherindex)
            swapMenuProperties(propertymask, targetwindow, index, otherindex)
            releaseMenuOptionLocks(propertymask, targetwindow, index, otherindex)
    else:
        xbmclibrary.writeErrorMessage(FUNCTIONNAME, FUNCTIONNAME + ' terminates: Missing argument(s) in call to script.')	
