import json
from kodi_six import xbmc, xbmcvfs
from . import utils as utils


class CronSchedule:
    expression = ''
    name = 'library'
    timer_type = 'xbmc'
    command = {'method': 'VideoLibrary.Scan', 'params': {'showdialogs': True}}
    next_run = 0
    on_delay = False  # used to defer processing until after player finishes

    def executeCommand(self):
        jsonCommand = {'jsonrpc': '2.0', 'method': self.command['method'], 'params': self.command['params'], 'id': 44}
        utils.log(json.dumps(jsonCommand))
        xbmc.executeJSONRPC(json.dumps(jsonCommand))

    def cleanLibrarySchedule(self, selectedIndex):
        if(selectedIndex == 1):
            # once per day
            return "* * *"
        elif (selectedIndex == 2):
            # once per week
            return "* * 0"
        else:
            # once per month
            return "1 * *"


class CustomPathFile:
    jsonFile = xbmcvfs.translatePath(utils.data_dir() + "custom_paths.json")
    paths = None
    contentType = 'video'  # all by default

    def __init__(self, contentType):
        self.paths = []
        self.contentType = contentType

        # try and read in the custom file
        self._readFile()

    def getSchedules(self, showDialogs=True):
        schedules = []

        # create schedules from the path information
        for aPath in self.paths:
            if(self.contentType == aPath['content']):
                schedules.append(self._createSchedule(aPath, showDialogs))

        return schedules

    def addPath(self, path):
        path['id'] = self._getNextId()
        self.paths.append(path)

        # save the file
        self._writeFile()

    def deletePath(self, aKey):
        # find the given key
        index = -1
        for i in range(0, len(self.paths)):
            if(self.paths[i]['id'] == aKey):
                index = i

        # if found, delete it
        if(i != -1):
            del self.paths[index]

        # save the file
        self._writeFile()

    def getPaths(self):
        result = []

        for aPath in self.paths:
            # if type matches the one we want
            if(self.contentType == 'all' or self.contentType == aPath['content']):
                result.append(aPath)

        return result

    def _getNextId(self):
        result = 0

        if(len(self.paths) > 0):
            # sort ids, get highest one
            maxId = sorted(self.paths, reverse=True, key=lambda k: k['id'])
            result = maxId[0]['id']

        return result + 1

    def _writeFile(self):
        # sort the ids
        self.paths = sorted(self.paths, reverse=True, key=lambda k: k['id'])

        # create the custom file
        aFile = xbmcvfs.File(self.jsonFile, 'w')
        aFile.write(json.dumps(self.paths))
        aFile.close()

    def _readFile(self):

        if(xbmcvfs.exists(self.jsonFile)):

            # read in the custom file
            aFile = xbmcvfs.File(self.jsonFile)

            # load paths in the format {path:path,expression:expression,content:type}
            tempPaths = json.loads(aFile.read())

            # update values in path
            for aPath in tempPaths:

                # old files are only video, update
                if('content' not in aPath):
                    aPath['content'] = 'video'

                if('id' not in aPath):
                    aPath['id'] = self._getNextId()

                self.paths.append(aPath)

            aFile.close()
        else:
            # write a blank file
            self._writeFile()

    def _createSchedule(self, aPath, showDialogs):

        aSchedule = CronSchedule()
        aSchedule.name = aPath['path']

        # command depends on content type
        if(aPath['content'] == 'video'):
            aSchedule.command = {'method': 'VideoLibrary.Scan', 'params': {'directory': aPath['path'], 'showdialogs': showDialogs}}
        else:
            aSchedule.command = {'method': 'AudioLibrary.Scan', 'params': {'directory': aPath['path'], 'showdialogs': showDialogs}}

        aSchedule.expression = aPath['expression']

        return aSchedule
