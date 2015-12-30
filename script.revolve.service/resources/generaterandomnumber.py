# *  Function: Revolve/GenerateRandomNumber

import random
import sys
import xbmc

import xbmclibrary

FUNCTIONNAME = 'Revolve/GenerateRandomNumber'
DEFAULTTARGETWINDOW = '0'

def execute(arguments):
    if len(sys.argv) > 4:
        minimumvalue = sys.argv[2]
        maximumvalue = sys.argv[3]
        targetproperty = sys.argv[4]
        
        if len(sys.argv) > 5:
            targetwindow = sys.argv[5]
        else:
            targetwindow = DEFAULTTARGETWINDOW
        
        randomvalue = randint(minimumvalue, maximumvalue)
        xbmclibrary.setItemToProperty(targetproperty, randomvalue, targetwindow)
    else:
        xbmclibrary.writeErrorMessage(FUNCTIONNAME, FUNCTIONNAME + ' terminates: Missing argument(s) in call to script.')	
