# *  Script: Revolve/Helper Script

import sys

import resources.xbmclibrary as xbmclibrary
import resources.populatestaticitemsfromhomeproperties as populatestaticitemsfromhomeproperties
import resources.populatesubmenufromskinvariables as populatesubmenufromskinvariables
import resources.clearproperties as clearproperties
import resources.fillpropertyfromtextfile as fillpropertyfromtextfile
import resources.generaterandomnumber as generaterandomnumber

SCRIPTNAME = 'Revolve/Main'

function = "-"
if len(sys.argv) > 1:
    try:
        function = sys.argv[1]
         
        if function == "PopulateStaticItemsFromHomeProperties":
            populatestaticitemsfromhomeproperties.execute(sys.argv)
        elif function == "PopulateSubmenuFromSkinVariables":
            populatesubmenufromskinvariables.execute(sys.argv)
        elif function == "ClearProperties":
            clearproperties.execute(sys.argv)
        elif function == "FillPropertyFromTextFile":
            fillpropertyfromtextfile.execute(sys.argv)
        elif function == "GenerateRandomNumber":
            generaterandomnumber.execute(sys.argv)
        else:
            xbmclibrary.writeErrorMessage(SCRIPTNAME, SCRIPTNAME + ' terminates: function ' + function + ' is unknown.')
    except BaseException as exception:
        xbmclibrary.writeErrorMessage(SCRIPTNAME, SCRIPTNAME + ' terminates: ' + str(exception) + '.')
else:
    xbmclibrary.writeErrorMessage(SCRIPTNAME, SCRIPTNAME + ' terminates: Missing argument(s) in call to script.')
