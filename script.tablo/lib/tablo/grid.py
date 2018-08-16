import os
import json
import time
import datetime

from lib import tablo

from lib import backgroundthread
from lib import util

SAVE_VERSION = 1
INTERVAL_HOURS = 2
INTERVAL_TIMEDELTA = datetime.timedelta(hours=INTERVAL_HOURS)

PENDING_UPDATE = {}


def addPending(path=None, airing=None):
    path = path or airing.data['airing_details']['channel_path']
    PENDING_UPDATE[path] = 1


class ChannelTask(backgroundthread.Task):
    def setup(self, channel, callback):
        self.path = channel.path
        self.channel = channel
        self.callback = callback

    def run(self):
        n = tablo.api.UTCNow()
        start = n - tablo.compat.datetime.timedelta(minutes=n.minute % 30, seconds=n.second, microseconds=n.microsecond)
        data = tablo.API.views.livetv.channels(self.channel.object_id).get(start=start.strftime('%Y-%m-%dT%H:%MZ'), duration=86400 + (5400 * INTERVAL_HOURS))
        if self.isCanceled():
            return

        util.DEBUG_LOG('Retrieved channel: {0}'.format(self.channel.object_id))

        self.callback(self.path, data)


class Grid(object):
    def __init__(self, work_path, update_callback):
        self.channels = {}
        self.paths = []
        self._airings = {}
        self._hasData = {}
        self.updateCallback = update_callback
        self._tasks = []
        self.workPath = os.path.join(work_path, 'grid')
        self.oldestUpdate = datetime.datetime.now()
        self.pendingUpdate = {}
        self.initSave()

    def initSave(self):
        if not os.path.exists(self.workPath):
            os.makedirs(self.workPath)

    def saveVersion(self):
        data = {'version': SAVE_VERSION}
        with open(os.path.join(self.workPath, 'version'), 'w') as f:
            json.dump(data, f)

    # def saveChannelData(self, data):
    #     with open(os.path.join(self.workPath, 'channels.data'), 'w') as f:
    #         json.dump(data, f)

    def saveChannelAiringData(self, channel, data):
        with open(os.path.join(self.workPath, str(channel.object_id) + '.air'), 'w') as f:
            json.dump(
                {'updated': time.mktime(datetime.datetime.now().timetuple()), 'data': data}, f
            )

    def updateChannelAiringData(self, channel=None, path=None):
        channel = channel or self.channels[path]
        # os.remove(os.path.join(self.workPath, str(channel.object_id) + '.air'))
        with open(os.path.join(self.workPath, str(channel.object_id) + '.air'), 'r') as f:
            data = json.load(f)
        data['updated'] = 0
        with open(os.path.join(self.workPath, str(channel.object_id) + '.air'), 'w') as f:
            json.dump(data, f)
        self.getChannelData(channel)

    def loadVersion(self):
        path = os.path.join(self.workPath, 'version')
        if not os.path.exists(path):
            return None

        with open(path, 'r') as f:
            data = json.load(f)
            return data

    def loadChannels(self):
        self.cancelTasks()
        # path = os.path.join(self.workPath, 'channels.data')
        # if not os.path.exists(path):
        #     return False

        # util.DEBUG_LOG('Loading saved grid data...')
        # with open(path, 'r') as f:
        #     self.channels = json.load(f)
        util.DEBUG_LOG('Loading grid data...')

        self.channels = {}
        channels = tablo.API.batch.post(self.paths)

        for path in channels:
            channel = tablo.Channel(channels[path])
            self.channels[path] = channel

            if path not in self._airings:
                self._airings[path] = []

            self.updateCallback(channel)

            self.loadAirings(channel)

        for path in channels:
            self.getChannelData(self.channels[path])

        util.DEBUG_LOG('Loading of grid data done.')

        return True

    def loadAirings(self, channel):
        path = os.path.join(self.workPath, str(channel.object_id) + '.air')
        if not os.path.exists(path):
            self._airings[channel.path] = []
            return False

        with open(path, 'r') as f:
            data = json.load(f)

        ret = True

        updated = datetime.datetime.fromtimestamp(int(data['updated']))
        age = (datetime.datetime.now() - updated)
        if age > INTERVAL_TIMEDELTA:
            ret = False

        if updated < self.oldestUpdate:
            self.oldestUpdate = updated

        self._airings[channel.path] = [tablo.GridAiring(a) for a in data['data']]

        if self._airings[channel.path]:
            self.updateCallback(channel)
            return ret

        return False

    def getChannelData(self, channel=None, path=None):
        channel = channel or self.channels[path]
        t = ChannelTask()
        self._tasks.append(t)
        t.setup(channel, self.channelDataCallback)

        backgroundthread.BGThreader.addTask(t)

    def channelDataCallback(self, path, data):
        self._hasData[path] = data and True or False

        self.saveChannelAiringData(self.channels[path], data)  # This only works HERE - before we convert the airing data

        self._airings[path] = [tablo.GridAiring(a) for a in data]

        self.updateCallback(self.channels[path])

    def cancelTasks(self):
        if not self._tasks:
            return

        util.DEBUG_LOG('Canceling {0} tasks (GRID)'.format(len(self._tasks)))
        for t in self._tasks:
            t.cancel()
        self._tasks = []

    def getChannels(self, paths=None):
        self.paths = paths or tablo.API.guide.channels.get()

        self.loadChannels()

        self.saveVersion()

    def triggerUpdates(self):
        for path in self.channels:
            self.updateCallback(self.channels[path])

    def airings(self, start, cutoff, channel_path=None, channel=None):
        channel = channel or self.channels[channel_path]
        return [a for a in self._airings[channel.path] if a.datetimeEnd > start and a.datetime < cutoff]

    def hasNoData(self, path):
        return self._hasData.get(path) is False

    def getAiring(self, path):
        for c in self._airings.values():
            for a in c:
                if a.path == path:
                    return a
        return None

    def updatePending(self):
        global PENDING_UPDATE

        for p in PENDING_UPDATE.keys():
            self.getChannelData(path=p)
        PENDING_UPDATE = {}
