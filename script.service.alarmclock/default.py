import xbmc, xbmcaddon
import os, sys, time

__cwd__        = xbmc.translatePath( xbmcaddon.Addon().getAddonInfo('path') ).decode("utf-8")
__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) ).decode("utf-8")
sys.path.append (__resource__)
from cronjobs import CronTab, Job


class AlarmClock:
  """Main alarm clock application class."""
  
  def __init__(self):
    self.addon = xbmcaddon.Addon()
    self.crontab = CronTab(xbmc)


  def applySettings(self):
    """Gets the current configuration and updates the scheduler."""
    self.addon = xbmcaddon.Addon()
    self.crontab.jobs = self._getAlarms()


  def start(self):
    """Starts the alarm clock, ie. activates the defined alarms."""
    self.crontab.start()


  def stop(self):
    """Stops the alarm clock."""
    self.crontab.stop()


  def _getAlarms(self):
    """Get a list of the cron jobs for the enabled alarms."""
    jobs = []

    for i in range(1,6):
      if self.addon.getSetting("alarm%d" % i) == "true":
        jobs.extend(self._getJobs(i))
    xbmc.log("events fetched: %s" % str(jobs), xbmc.LOGDEBUG)
    return jobs


  def _getJobs(self, number):
    """Initialize jobs(s) for alarm number.
    If the alarm has a duration enabled, both the start and the stop job
    are returned in the list."""
    daysOfWeek = int(self.addon.getSetting("day%d" % number))
    if daysOfWeek == 7:
      daysOfWeek = range(5)
    if daysOfWeek == 8:
      daysOfWeek = range(7)

    action = self.addon.getSetting("action%d" % number)
    if action == "0":
      file = self.addon.getSetting("file%d" % number)
    else:
      file = self.addon.getSetting("text%d" % number)

    jobs = [Job(self._play,
              int(self.addon.getSetting("minute%d" % number)),
              int(self.addon.getSetting("hour%d" % number)),
              dow=daysOfWeek,
                    args=[file, self.addon.getSetting("volume%d" % number)])]
    
    if self.addon.getSetting("turnOff%d" % number) == "true":
      jobs.append(Job(self._stopPlaying,
          int(self.addon.getSetting("minute%d" % number))
            + (int(self.addon.getSetting("duration%d" % number)) % 60),
          int(self.addon.getSetting("hour%d" % number))
            + (int(self.addon.getSetting("duration%d" % number)) / 60),
          dow=daysOfWeek))
    return jobs


  def _play(self, item, volume):
    xbmc.executebuiltin('SetVolume(%s)' % volume)
    xbmc.Player().play(item)


  def _stopPlaying(self):
    xbmc.Player().stop()



class AlarmClockMonitor(xbmc.Monitor):
  """Monitor subclass listening on configuration changes and termination
  requests."""
  def __init__(self, alarmClock):
    xbmc.Monitor.__init__(self)
    self.alarmClock = alarmClock
    self.alarmClock.applySettings()


  def onSettingsChanged(self):
    self.alarmClock.applySettings()


  def onAbortRequested(self):
    self.alarmClock.stop()    



alarmClock = AlarmClock()
monitor = AlarmClockMonitor(alarmClock)

xbmc.log("Starting alarm clock..", xbmc.LOGDEBUG)
alarmClock.start()
