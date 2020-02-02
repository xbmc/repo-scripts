# pylint: disable=missing-docstring,invalid-name,import-error

import unittest
import alarm_clock
from alarm_clock import AlarmClock, Alarm
from cronjobs import CronTab
from datetime import datetime, timedelta
from contextlib import contextmanager


class TestSpeakers(object):
    def __init__(self):
        self.call_recorder = []

    def play(self, data):
        self.call_recorder.append(('START', data))

    def pause(self):
        self.call_recorder.append(('STOP',))

class TestQuartz(CronTab.Quartz):
    def spark(self):
        t = datetime.now()
        for n in list(range(60)):
            yield t
            t += timedelta(minutes=1)


class JobTestCase(unittest.TestCase):

    maxDiff = None

    def test_minutes_to_days_hours_minutes(self):
        self.assertEquals((0, 0, 0 ), alarm_clock.minutes_to_days_hours_minutes(0))
        self.assertEquals((0, 0, 59), alarm_clock.minutes_to_days_hours_minutes(60 -1))
        self.assertEquals((0, 1, 0 ), alarm_clock.minutes_to_days_hours_minutes(60))
        self.assertEquals((0, 1, 1 ), alarm_clock.minutes_to_days_hours_minutes(60 +1))
        self.assertEquals((0, 23,59), alarm_clock.minutes_to_days_hours_minutes(24*60 -1))
        self.assertEquals((1, 0, 0 ), alarm_clock.minutes_to_days_hours_minutes(24*60))
        self.assertEquals((1, 0, 1 ), alarm_clock.minutes_to_days_hours_minutes(24*60 +1))
        self.assertEquals((6, 23,59), alarm_clock.minutes_to_days_hours_minutes(7*24*60 -1))
        self.assertEquals((7, 0, 0 ), alarm_clock.minutes_to_days_hours_minutes(7*24*60))
        self.assertEquals((7, 0, 1 ), alarm_clock.minutes_to_days_hours_minutes(7*24*60 +1))
        self.assertEquals((3, 4, 37), alarm_clock.minutes_to_days_hours_minutes(3*24*60 + 4*60 + 37))

    def assertStopTime(self, expected, days, hour, minute, duration):
        alarm = Alarm('id', 'label', days, hour, minute, duration)
        self.assertEquals(expected, str(alarm.GetStop().ToCronSpec()))

    def test_alarm_stop_time(self):
        for days in list(range(9)):
            self.assertStopTime('0 0 * * *',       [0,1,2,3,4,5,6], 0, 0,     days * 24*60)
            self.assertStopTime('59 23 * * *',     [0,1,2,3,4,5,6], 23, 59,   days * 24*60)

        self.assertStopTime('0 0 * * 0',           [0], 0, 0,                 0)

        self.assertStopTime('1 0 * * 0',           [0], 0, 0,                 1)
        self.assertStopTime('0 1 * * 0',           [0], 0, 59,                1)
        self.assertStopTime('9 1 * * 0',           [0], 0, 59,                10)
        self.assertStopTime('0 2 * * 0',           [0], 0, 59,                61)

        self.assertStopTime('0 0 * * 1',           [0], 0, 0,                 24*60)
        self.assertStopTime('0 0 * * 6',           [4], 0, 0,                 2*24*60)
        self.assertStopTime('0 0 * * 0',           [4], 0, 0,                 3*24*60)

        self.assertStopTime('37 4 * * 1,2,4,5',    [1,2,5,6], 0, 0,           3*24*60 + 4*60 + 37)
        self.assertStopTime('25 5 * * 2,3,5,6',    [1,2,5,6], 13, 48,         3*24*60 + 15*60 + 37)

    def test_running_alarm(self):
        quartz = TestQuartz()
        crontab = CronTab(quartz)
        speakers = TestSpeakers()
        alarmClock = AlarmClock(crontab, speakers)

        alarm = Alarm.FromNow(456, 'Test Alarm', start_delay=1, duration=2)
        alarmClock.create_new_alarm(alarm, 'A1')

        alarmClock.crontab.start()

        expected = [
            ('START', 'A1'),
            ('STOP', ),
        ]
        self.assertEqual(expected, speakers.call_recorder)


    def test_running_two_alarms(self):
        quartz = TestQuartz()
        crontab = CronTab(quartz)
        speakers = TestSpeakers()
        alarmClock = AlarmClock(crontab, speakers)

        alarm = Alarm.FromNow(123, 'Test Alarm 1', start_delay=1, duration=2)
        alarmClock.create_new_alarm(alarm, 'A1')

        alarm = Alarm.FromNow(456, 'Test Alarm 2', start_delay=10, duration=2)
        alarmClock.create_new_alarm(alarm, 'A2')

        alarmClock.crontab.start()

        expected = [
            ('START', 'A1'),
            ('STOP', ),
            ('START', 'A2'),
            ('STOP', ),
        ]
        self.assertEqual(expected, speakers.call_recorder)


    def test_running_two_overlapping_alarms(self):
        quartz = TestQuartz()
        crontab = CronTab(quartz)
        speakers = TestSpeakers()
        alarmClock = AlarmClock(crontab, speakers)

        alarm = Alarm.FromNow(123, 'Test Alarm 1', start_delay=1, duration=20)
        alarmClock.create_new_alarm(alarm, 'A1')

        alarm = Alarm.FromNow(456, 'Test Alarm 2', start_delay=10, duration=20)
        alarmClock.create_new_alarm(alarm, 'A2')

        alarmClock.crontab.start()

        expected = [
            ('START', 'A1'),
            ('START', 'A2'),
            ('STOP', ),
        ]
        self.assertEqual(expected, speakers.call_recorder)


if __name__ == '__main__':
    import logging
    import alarm_clock, cronjobs

    logger = logging.getLogger(alarm_clock.__name__)
    logger.setLevel(logging.ERROR)

    logger = logging.getLogger(cronjobs.__name__)
    logger.setLevel(logging.ERROR)
    unittest.main()
