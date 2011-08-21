import addon
import xbmc

xbmc.log("Updating TVGuide [script.tvguide] channel list caches...")
channelList = addon.SOURCE.getChannelList()

for channel in channelList:
    xbmc.log("Updating TVGuide [script.tvguide] program list caches for channel " + channel.title + "...")
    addon.SOURCE.getProgramList(channel)

xbmc.log("Done updating TVGuide [script.tvguide] caches.")


