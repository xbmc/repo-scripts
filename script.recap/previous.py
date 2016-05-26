# -*- coding: utf-8 -*-

# Import the common settings
from resources.lib.settings import log
from resources.lib.core import runRecap


#########################
# Main
#########################
if __name__ == '__main__':
    log("Recap Previous: Started")

    runRecap(True)

    log("Recap Previous: Ended")
