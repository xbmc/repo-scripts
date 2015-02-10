from datetime import datetime, timedelta
import time

class CronTab(object):
  """Simulates basic cron functionality by checking for firing jobs every
  minute."""

  def __init__(self, xbmc):
    self.xbmc = xbmc
    self.jobs = []
    self.__enabled = True

  def stop(self):
    """Stops the crontab."""
    self.__enabled = False

  def start(self):
    """Starts to check every minute, if the registered jobs should run."""
    t = datetime(*datetime.now().timetuple()[:5])
    while self.__enabled:
      if self.xbmc and not self.xbmc.abortRequested:
        for job in self.jobs:
          self.xbmc.log("checking job %s against %s" % (str(job), str(t)), 
                          self.xbmc.LOGDEBUG)
          job.check(t)
      
        t += timedelta(minutes=1)
        if datetime.now() < t:
          if self.xbmc:
            self.xbmc.sleep((t - datetime.now()).seconds * 1000)
          else:
            time.sleep((t - datetime.now()).seconds)


class AllMatch(set):
  """Universal set - match everything"""
  def __contains__(self, item): return True


class Job(object):
  """Cron job abstraction."""

  def conv_to_set(self, obj):
    """Convert obj to a set containing obj if necessary."""
    if isinstance(obj, (int,long)):
      return set([obj])
    if not isinstance(obj, set):
      obj = set(obj)
    return obj

  def __init__(self, action, min=AllMatch(), hour=AllMatch(),
                     day=AllMatch(), month=AllMatch(), dow=AllMatch(),
                     args=(), kwargs={}):
    self.mins = self.conv_to_set(min)
    self.hours = self.conv_to_set(hour)
    self.days = self.conv_to_set(day)
    self.months = self.conv_to_set(month)
    self.dow = self.conv_to_set(dow)
    self.action = action
    self.args = args
    self.kwargs = kwargs


  def __str__(self):
    return str(self.mins) + ", " + str(self.hours) + ", "\
                 + str(self.days) + ", " + str(self.months) + ", "\
                 + str(self.dow) + ", " + str(self.action) + ", "\
                 + str(self.args) + ", " + str(self.kwargs)


  def is_matchtime(self, t):
    """Is t the job's scheduled time"""
    return ((t.minute in self.mins) and
            (t.hour in self.hours) and
            (t.day in self.days) and
            (t.month in self.months) and
            (t.weekday() in self.dow))


  def check(self, t):
    """Checks if t is the scheduled time and executes the job if so."""
    if self.is_matchtime(t):
      self.action(*self.args, **self.kwargs)
