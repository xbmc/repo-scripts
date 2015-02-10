import xbmcaddon

# get translator function
self = xbmcaddon.Addon('service.script.isyevents')
translator = self.getLocalizedString


# function to record messages to log
def log(msg):
    print translator(32301) + msg
