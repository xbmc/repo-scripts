# *  Function: Revolve/FillPropertyFromTextFile

import sys
import xbmc

import xbmclibrary

FUNCTIONNAME = 'Revolve/FillPropertyFromTextFile'
DEFAULTTARGETPROPERTY = 'TextFileContent'
DEFAULTTARGETWINDOW = '0'
SPECIALFILE = 'special://'

def loadPropertyFromTextFile(filename, targetproperty, targetwindow):
    try:
        with open(xbmclibrary.translatePath(filename)) as file:
            value = file.read()
        xbmclibrary.setItemToProperty(targetproperty, value, targetwindow)
    except IOError:
        xbmclibrary.writeErrorMessage(FUNCTIONNAME, FUNCTIONNAME + ' terminates: Error while reading file ' + filename)

def execute(arguments):
    if len(arguments) > 2:
        filename = arguments[2]

        if len(arguments) > 3:
            targetproperty = arguments[3]
        else:
            targetproperty = DEFAULTTARGETPROPERTY
        
        if len(arguments) > 4:
            targetwindow = arguments[4]
        else:
            targetwindow = DEFAULTTARGETWINDOW
        
        loadPropertyFromTextFile(filename, targetproperty, targetwindow)
    else:
        xbmclibrary.writeErrorMessage(FUNCTIONNAME, FUNCTIONNAME + ' terminates: Missing filename in call to script.')	
