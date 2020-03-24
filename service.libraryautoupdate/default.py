import resources.lib.utils as utils
from resources.lib.service import AutoUpdater

# run the program
utils.log("Update Library Service starting...")
AutoUpdater().runProgram()
