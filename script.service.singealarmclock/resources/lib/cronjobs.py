from collections import namedtuple
from datetime import datetime, timedelta
import time
import logging
import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(format='[%(levelname)-7s] %(asctime)s %(name)s: %(message)s')


class Functor(object):
    def __init__(self, fn, *args, **kwargs):
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def __str__(self):
        params = list(repr(x) for x in self._args) + \
                 list('%s=%r' % (k,v) for (k,v) in list(self._kwargs.items()))
        return '%s(%s)' % (self._fn.__name__, ', '.join(params))

    def __call__(self):
        return self._fn(*self._args, **self._kwargs)


def _conv_to_set(obj):
    if isinstance(obj, (int,long)):
        obj = [obj]
    return tuple(obj)


class TimeSpec(namedtuple('TimeElements', 'minute hour day month dow')):
    AnyDayOfWeek  = tuple(range(7)) # mon=0, sun=6
    AnyHour       = tuple(range(24))
    AnyMinute     = tuple(range(60))
    AnyDayOfMonth = tuple(range(32)) # Max 31 days in the month
    AnyMonth      = tuple(range(1,13))

    def __new__(cls, minute=AnyMinute, hour=AnyHour, day=AnyDayOfMonth, month=AnyMonth, dow=AnyDayOfWeek):
        parts = [_conv_to_set(x) for x in (minute, hour, day, month, dow)]
        self = super(TimeSpec, cls).__new__(cls, *parts)
        return self

    def is_matchtime(self, time):
        """Does this time spec match the given time"""
        t = time.minute, time.hour, time.day, time.month, time.weekday()
        return all(x in y for x, y in zip(t, self))

    def __str__(self):
        def cron_unit(complete_set, values):
            if complete_set == values:
                return '*'
            return ','.join(str(x) for x in sorted(values))

        return ' '.join(cron_unit(*x) for x in zip(TimeSpec(), self))

class Job(namedtuple('Job_', 'time_spec functor')):
    def __str__(self):
        return ' '.join(str(x) for x in self)


class Quartz(object):
    def __init__(self):
        self.life = True

    def spark(self):
        while self.is_still_alive():
            now_to_minute = datetime(*datetime.now().timetuple()[:5])
            next_time = now_to_minute + timedelta(minutes=1)

            yield now_to_minute

            now = datetime.now()
            if now < next_time:
                self._sleep(min(60, (next_time-now).seconds +1))

    def is_still_alive(self):
        return self.life

    def kill(self):
        self.life = False

    def _sleep(self, delay_seconds):
        import time
        time.sleep(delay_seconds)

class CronTab(object):
    """Simulates basic cron functionality by checking for firing jobs every
    minute."""

    Quartz = Quartz
    TimeSpec = TimeSpec

    def __init__(self, quartz=None):
        self.quartz = quartz or Quartz()
        self._jobs = []

    def start(self):
        """Check every quartz spark for jobs to run"""
        for time in self.quartz.spark():
            if not self.quartz.is_still_alive():
                break
            for job in self._jobs[:]:
                logger.debug("Checking Job %s against %s" % (str(job), str(time)))

                if job.time_spec.is_matchtime(time):
                    logger.info("Running Job %s" % str(job))
                    job.functor()

    def clear(self):
        self._jobs = []

    def create_job(self, time_spec, fn, *args, **kwargs):
        job = Job(time_spec, Functor(fn, *args, **kwargs))
        self._jobs.append(job)
        logger.debug("Added Job %s" % str(job))



if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)

    cron_time = TimeSpec(minute=[0,1,2])
    job = Job(cron_time, Functor(time.sleep, 4))
    logger.info(str(job))

    def printer(message):
        logger.info(message)

    now = datetime.now()
    crontab = CronTab()
    crontab.create_job(TimeSpec(now.minute +0, now.hour), printer, 'Now')
    crontab.create_job(TimeSpec(now.minute +1, now.hour), printer, 'The next minute')
    crontab.create_job(TimeSpec(now.minute +2, now.hour), lambda : crontab.quartz.kill())
    crontab.start()



