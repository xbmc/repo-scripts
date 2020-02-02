from collections import namedtuple
from datetime import datetime, timedelta
import logging

from cronjobs import CronTab

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(format='[%(levelname)-7s] %(asctime)s %(name)s: %(message)s')


def minutes_to_days_hours_minutes(total_minutes):
    minute = total_minutes % 60
    hour = total_minutes / 60
    days = hour / 24
    hour %= 24
    return days, hour, minute


def _increase_time(daysOfWeek, hour, minute, duration):
    total_minutes = hour * 60 + minute + duration
    days, hours, minutes = minutes_to_days_hours_minutes(total_minutes)
    daysOfWeek = [(day + days) % 7 for day in daysOfWeek]
    daysOfWeek.sort()
    return daysOfWeek, hours, minutes


class Alarm(namedtuple('Alarm_', 'id label day hour minute duration')):
    def __repr__(self):
        return repr(self.label)

    def ToNow(self):
        return Alarm.Now(self.id, self.label, self.duration)

    def GetStop(self):
        days, hours, minutes = _increase_time(self.day, self.hour, self.minute, self.duration)
        return Alarm(self.id, self.label, days, hours, minutes, 0)

    def AddDuration(self, duration):
        return Alarm(self.id, self.label, self.day, self.hour, self.minute, duration)

    def ToCronSpec(self):
        return CronTab.TimeSpec(self.minute, self.hour, dow=self.day)

    @staticmethod
    def Now(id, label, duration):
        now = datetime.now()
        return Alarm(id, label, [now.isoweekday()-1], now.hour, now.minute, duration)

    @staticmethod
    def FromNow(id, label, start_delay, duration):
        return Alarm.Now(id, label, start_delay) \
                    .GetStop() \
                    .AddDuration(duration)


class AlarmClock(object):
    """Main alarm clock application class."""
    
    def __init__(self, crontab, speakers):
        self.crontab = crontab
        self.speakers = speakers
        self._stop_jobs = []
        self._active = None


    def applySettings(self, alarms):
        self.crontab.clear()
        for alarm, data in alarms:
            self.create_new_alarm(alarm, data)
        for alarm, data in self._stop_jobs:
            self._create_stop_job(alarm, data)


    def _create_stop_job(self, alarm, data):
        logger.info("Creating Stop Alarm [{0.label}] {1} + {0.duration} minutes"
                .format(alarm, alarm.ToCronSpec()))

        time_spec = alarm.GetStop().ToCronSpec()
        self.crontab.create_job(time_spec, self._stop_alarm, alarm, data)


    def create_new_alarm(self, alarm, data):
        logger.info("Creating Alarm [{0.label}] {1}" \
                .format(alarm, alarm.ToCronSpec()))

        time_spec = alarm.ToCronSpec()
        self.crontab.create_job(time_spec, self.start_alarm, alarm, data)


    def start_alarm(self, alarm, data):
        logger.info("Starting Alarm [{0.label}] {1}"
                .format(alarm, alarm.ToCronSpec()))

        self._active = (alarm, data)
        self.speakers.play(data)

        if alarm.duration > 0:
            self._create_stop_job(alarm, data)
            self._stop_jobs.append((alarm, data))


    def _stop_alarm(self, alarm, data):
        self._stop_jobs = [other for other in self._stop_jobs \
                           if not other == (alarm, data)]
        if self._active == (alarm, data):
            self._active = None
            self.speakers.pause()


if __name__ == '__main__':
    logger.setLevel(logging.DEBUG)

    import sys
    sys.path.append('resources/lib')

    class Speakers(object):
        def play(self, data):
            logging.info('SPEAKERS STARTING ' + data[0])

        def pause(self):
            logging.info('SPEAKERS STOPPING')

    class TestQuartz(CronTab.Quartz):
        def spark(self):
            t = datetime.now()
            for n in range(5):
                yield t
                t += timedelta(minutes=1)

    quartz = TestQuartz()
    crontab = CronTab(quartz)
    speakers = Speakers()
    alarmClock = AlarmClock(crontab, speakers)

    data = 'http://my-radio-station/playlist.m3u',
    alarm = Alarm.FromNow('ID', 'Demo Alarm', start_delay=1, duration=2)
    alarmClock.create_new_alarm(alarm, data)

    alarmClock.crontab.start()



