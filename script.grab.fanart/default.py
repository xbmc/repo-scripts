import sys
import resources.lib.utils as utils

utils.log("updating settings")

if(len(sys.argv) > 1):
    for i in sys.argv:
        args = i
        if('=' in args):
            if(args.startswith('?')):
                args = args[1:]  # legacy in case of url params
            splitString = args.split('=')
            utils.log(splitString[1])
            utils.setSetting(splitString[0], splitString[1])
