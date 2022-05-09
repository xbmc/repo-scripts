import time
import xbmc
import xbmcvfs
import xml.dom.minidom
import datetime
from . import croniter
from . import utils


class CronJob:
    def __init__(self):
        self.id = -1
        self.name = ""
        self.command = ""
        self.expression = []
        self.show_notification = "false"
        self.addon = None
        self.last_run = datetime.datetime.now().timestamp()
        self.run_if_skipped = "false"
        self.command_type = 'built-in'

    def getType(self):
        types = {'built-in': 'Built-In Function', 'json': 'JSON Command'}

        return types[self.command_type]


class CronManager:
    CRONFILE = 'special://profile/addon_data/service.cronxbmc/cron.xml'
    jobs = {}  # format {job_id:job_obj}
    last_read = time.time()

    def __init__(self):
        self.jobs = self._readCronFile()

    def addJob(self, job):

        try:
            # verify the cron expression here, throws ValueError if wrong
            croniter.croniter(job.expression)
        except:
            # didn't work
            return False

        # set the addon id if there isn't one
        if(job.addon is None):
            job.addon = utils.addon_id()

        self._refreshJobs()

        if(job.id >= 0):
            # replace existing job
            self.jobs[job.id] = job
        else:
            # set the job id
            job.id = self._nextId()

            # add a new job
            self.jobs[job.id] = job

        # write the file
        self._writeCronFile()

        return True

    def deleteJob(self, jId):
        self._refreshJobs()

        self.jobs.pop(jId)

        self._writeCronFile()

    def getJobs(self, show_all=True):
        self._refreshJobs()

        if show_all:
            result = self.jobs.values()
        else:
            # filter on currently loaded addon
            result = list(filter(lambda x: x.addon == utils.addon_id(), self.jobs.values()))

        return result

    def getJob(self, jId):
        self._refreshJobs()

        return self.jobs[jId]

    def nextRun(self, cronJob):
        # create a cron expression
        now = datetime.datetime.now()
        cron_exp = croniter.croniter(cronJob.expression, now)

        # compare now with next date
        nextRun = cron_exp.get_next(datetime.datetime)
        cronDiff = (nextRun - now).total_seconds()
        hours = int((cronDiff / 60) / 60)
        minutes = int(cronDiff / 60 - hours * 60)

        # we always have at least one minute
        if minutes == 0:
            minutes = 1

        result = str(hours) + " h " + str(minutes) + " m"
        if hours == 0:
            result = str(minutes) + " m"
        elif hours > 36:
            # just show the date instead
            result = utils.getRegionalTimestamp(nextRun, ['dateshort', 'time'])
        elif hours > 24:
            days = int(hours / 24)
            hours = hours - days * 24
            result = str(days) + " d " + str(hours) + " h " + str(minutes) + " m"

        return result

    def _nextId(self):
        result = 0

        # find the next largest id
        for k in self.jobs.keys():
            if(k >= result):
                result = k + 1

        return result

    def _refreshJobs(self):

        # check if we should read in a new files list
        stat_file = xbmcvfs.Stat(xbmcvfs.translatePath(self.CRONFILE))

        if(stat_file.st_mtime() > self.last_read):
            utils.log("File update, loading new jobs")
            # update the file
            self.jobs = self._readCronFile()
            self.last_read = time.time()

    def _readCronFile(self):
        if(not xbmcvfs.exists(xbmcvfs.translatePath('special://profile/addon_data/service.cronxbmc/'))):
            xbmcvfs.mkdir(xbmc.translatePath('special://profile/addon_data/service.cronxbmc/'))

        adv_jobs = {}
        try:
            doc = xml.dom.minidom.parse(xbmcvfs.translatePath(self.CRONFILE))

            for node in doc.getElementsByTagName("job"):
                tempJob = CronJob()
                tempJob.name = str(node.getAttribute("name"))
                tempJob.command = str(node.getAttribute("command"))
                tempJob.expression = str(node.getAttribute("expression"))
                tempJob.show_notification = str(node.getAttribute("show_notification"))

                # catch for older cron.xml where no id was saved
                if(node.getAttribute('id') == ''):
                    tempJob.id = len(adv_jobs)
                else:
                    tempJob.id = int(node.getAttribute('id'))

                # catch for older cron.xml files
                if(node.getAttribute('addon') != ''):
                    tempJob.addon = str(node.getAttribute('addon'))
                else:
                    tempJob.addon = utils.__addon_id__

                # catch for older cron.xml files
                if(node.getAttribute('last_run') != ''):
                    tempJob.last_run = float(node.getAttribute('last_run'))

                if(node.getAttribute('run_if_skipped') != ''):
                    tempJob.run_if_skipped = str(node.getAttribute('run_if_skipped'))

                # catch for prior versions where only built in methods were supported
                if(node.getAttribute('command_type') != ''):
                    tempJob.command_type = str(node.getAttribute('command_type'))

                utils.log(tempJob.name + " " + tempJob.expression + " loaded")
                adv_jobs[tempJob.id] = tempJob

        except IOError:
            # the file doesn't exist, return empty array
            doc = xml.dom.minidom.Document()
            rootNode = doc.createElement("cron")
            doc.appendChild(rootNode)

            # write the file
            with xbmcvfs.File(xbmcvfs.translatePath(self.CRONFILE), "w") as f:
                doc.writexml(f, indent='', addindent='  ', newl='\n')

        return adv_jobs

    def _writeCronFile(self):

        # write the cron file in full
        try:
            doc = xml.dom.minidom.Document()
            rootNode = doc.createElement("cron")
            doc.appendChild(rootNode)

            for aJob in self.jobs.values():

                # create the child
                newChild = doc.createElement("job")
                newChild.setAttribute('id', str(aJob.id))
                newChild.setAttribute("name", aJob.name)
                newChild.setAttribute('command_type', aJob.command_type)
                newChild.setAttribute("expression", aJob.expression)
                newChild.setAttribute("command", aJob.command)
                newChild.setAttribute("show_notification", aJob.show_notification)
                newChild.setAttribute("addon", aJob.addon)
                newChild.setAttribute("last_run", str(aJob.last_run))
                newChild.setAttribute('run_if_skipped', aJob.run_if_skipped)

                rootNode.appendChild(newChild)

            # write the file
            with xbmcvfs.File(xbmcvfs.translatePath(self.CRONFILE), "w") as f:
                doc.writexml(f, indent='', addindent='  ', newl='\n')

        except IOError:
            utils.log("error writing cron file", xbmc.LOGERROR)


class CronService:
    last_check = -1
    manager = None

    def __init__(self):
        self.manager = CronManager()

    def runProgram(self):
        monitor = xbmc.Monitor()
        startup = True

        # run until abort requested
        while(True):

            structTime = time.localtime()
            now = datetime.datetime.now()

            # only do all this if we are in a new minute
            if(structTime[4] != self.last_check):
                self.last_check = structTime[4]

                # get a list of all the cron jobs
                cron_jobs = self.manager.getJobs()

                for command in cron_jobs:
                    # create a cron expression for this command (on startup use last_run if we care about skipped runs otherwise use previous minute)
                    start_time = datetime.datetime.fromtimestamp(command.last_run) if (
                        startup and command.run_if_skipped == 'true') else (now - datetime.timedelta(seconds=60))
                    cron_exp = croniter.croniter(command.expression, start_time)

                    runTime = cron_exp.get_next(datetime.datetime)
                    # if this command should run then run it
                    if(runTime <= now):
                        command.last_run = now.timestamp()
                        self.runJob(command)
                        utils.log(command.name + " will run again on " + utils.getRegionalTimestamp(cron_exp.get_next(datetime.datetime), ['dateshort', 'time']))

            startup = False

            # calculate the sleep time (next minute)
            currentSec = datetime.datetime.now()
            if(monitor.waitForAbort(60 - currentSec.second)):
                break

    def runJob(self, cronJob, override_notification=False):
        utils.log("running command " + cronJob.name + " for addon " + cronJob.addon)

        if(cronJob.show_notification == "true" or override_notification):
            # show a notification that this command is running
            utils.showNotification("Cron", cronJob.name + " is executing")

        # run the command
        if(cronJob.command_type == 'built-in'):
            xbmc.executebuiltin(cronJob.command)
        else:
            xbmc.executeJSONRPC(cronJob.command)

        # save the last run time
        self.manager.addJob(cronJob)
