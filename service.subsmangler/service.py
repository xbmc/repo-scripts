import xbmc
from resources.lib import globals
from resources.lib import smangler

# SubsMangler's service entry point
if __name__ == '__main__':
    # prepare plugin environment
    smangler.PreparePlugin()

    # monitor whether Kodi is running
    # http://kodi.wiki/view/Service_add-ons
    while not globals.monitor.abortRequested():
        # wait for about 5 seconds
        if globals.monitor.waitForAbort(5):
            # Abort was requested while waiting. The addon should exit
            globals.rt.stop()
            xbmc.log("SubsMangler: Abort requested. Exiting.", level=xbmc.LOGINFO)
            break

        # run supplementary code periodically
        smangler.SupplementaryServices()
