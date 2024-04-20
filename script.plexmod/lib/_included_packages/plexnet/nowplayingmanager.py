# Most of this is ported from Roku code and much of it is currently unused
# TODO: Perhaps remove unnecessary code
from __future__ import absolute_import
import time

from . import util
from six import moves
import six.moves.urllib.request, six.moves.urllib.parse, six.moves.urllib.error
import six.moves.urllib.parse
from . import plexrequest
from . import callback
from . import http


class ServerTimeline(util.AttributeDict):
    def reset(self):
        self.expires = time.time() + 15

    def isExpired(self):
        return time.time() > self.get('expires', 0)


class TimelineData(util.AttributeDict):
    def __init__(self, timelineType, *args, **kwargs):
        util.AttributeDict.__init__(self, *args, **kwargs)
        self.type = timelineType
        self.state = "stopped"
        self.itemData = None
        self.playQueue = None

        self.controllable = util.AttributeDict()
        self.controllableStr = None

        self.attrs = util.AttributeDict()

        # Set default controllable for all content. Other controllable aspects
        # will be set based on the players content.
        #
        self.setControllable("playPause", True)
        self.setControllable("stop", True)

    def setControllable(self, name, isControllable):
        if isControllable:
            self.controllable[name] = ""
        else:
            if name in self.controllable:
                del self.controllable[name]

        self.controllableStr = None

    def updateControllableStr(self):
        if not self.controllableStr:
            self.controllableStr = ""
            prependComma = False

            for name in self.controllable:
                if prependComma:
                    self.controllableStr += ','
                else:
                    prependComma = True
                self.controllableStr += name


class NowPlayingManager(object):
    def __init__(self):
        # Constants
        self.NAVIGATION = "navigation"
        self.FULLSCREEN_VIDEO = "fullScreenVideo"
        self.FULLSCREEN_MUSIC = "fullScreenMusic"
        self.FULLSCREEN_PHOTO = "fullScreenPhoto"
        self.TIMELINE_TYPES = ["video", "music", "photo"]

        # Members
        self.serverTimelines = util.AttributeDict()
        self.subscribers = util.AttributeDict()
        self.pollReplies = util.AttributeDict()
        self.timelines = util.AttributeDict()
        self.location = self.NAVIGATION

        self.textFieldName = None
        self.textFieldContent = None
        self.textFieldSecure = None

        # Initialization
        for timelineType in self.TIMELINE_TYPES:
            self.timelines[timelineType] = TimelineData(timelineType)

    def updatePlaybackState(self, timelineType, itemData, state, t, playQueue=None, duration=0, force=False):
        timeline = self.timelines[timelineType]
        timeline.state = state
        timeline.itemData = itemData
        timeline.playQueue = playQueue
        timeline.attrs["time"] = str(t)
        timeline.duration = duration

        # self.sendTimelineToAll()

        self.sendTimelineToServer(timelineType, timeline, t, force=force)

    def sendTimelineToServer(self, timelineType, timeline, t, force=False):
        server = util.APP.serverManager.selectedServer
        if not server:
            return

        serverTimeline = self.getServerTimeline(timelineType)

        # Only send timeline if it's the first, item changes, playstate changes or timer pops
        itemsEqual = timeline.itemData and serverTimeline.itemData \
            and timeline.itemData.ratingKey == serverTimeline.itemData.ratingKey
        if itemsEqual and timeline.state == serverTimeline.state and not serverTimeline.isExpired() and not force:
            return

        serverTimeline.reset()
        serverTimeline.itemData = timeline.itemData
        serverTimeline.state = timeline.state

        # It's possible with timers and in player seeking for the time to be greater than the
        # duration, which causes a 400, so in that case we'll set the time to the duration.
        duration = timeline.itemData.duration or timeline.duration
        if t > duration:
            t = duration

        params = util.AttributeDict()
        params["time"] = t
        params["duration"] = duration
        params["state"] = timeline.state
        params["guid"] = timeline.itemData.guid
        params["ratingKey"] = timeline.itemData.ratingKey
        params["url"] = timeline.itemData.url
        params["key"] = timeline.itemData.key
        params["containerKey"] = timeline.itemData.containerKey
        if timeline.playQueue:
            params["playQueueItemID"] = timeline.playQueue.selectedId

        path = "/:/timeline"
        for paramKey in params:
            if params[paramKey]:
                path = http.addUrlParam(path, paramKey + "=" + six.moves.urllib.parse.quote(str(params[paramKey])))

        request = plexrequest.PlexRequest(server, path)

        context = request.createRequestContext("timelineUpdate", callback.Callable(self.onTimelineResponse))
        context.playQueue = timeline.playQueue
        util.APP.startRequest(request, context)

    def getServerTimeline(self, timelineType):
        if not self.serverTimelines.get(timelineType):
            serverTL = ServerTimeline()
            serverTL.reset()

            self.serverTimelines[timelineType] = serverTL

        return self.serverTimelines[timelineType]

    def nowPlayingSetControllable(self, timelineType, name, isControllable):
        self.timelines[timelineType].setControllable(name, isControllable)

    def onTimelineResponse(self, request, response, context):
        context.request.server.trigger("np:timelineResponse", response=response)

        if not context.playQueue or not context.playQueue.refreshOnTimeline:
            return
        context.playQueue.refreshOnTimeline = False
        context.playQueue.refresh(False)
