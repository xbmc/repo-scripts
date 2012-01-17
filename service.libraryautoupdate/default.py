import xbmc
from service import AutoUpdater

#run the program
xbmc.log("Update Library Service starting...")
AutoUpdater().runProgram()
