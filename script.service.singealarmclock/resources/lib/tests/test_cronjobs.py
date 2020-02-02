# pylint: disable=missing-docstring,invalid-name,import-error

import unittest
from cronjobs import CronTab, TimeSpec, Functor
from datetime import datetime, timedelta
from contextlib import contextmanager


class TestQuartz(CronTab.Quartz):
    def __init__(self, fake_times):
        super(TestQuartz, self).__init__()
        self._fake_times = fake_times

    def spark(self):
        for t in self._fake_times:
            yield t

    @staticmethod
    def ConsecutiveTimes(number_of_minutes):
        t = datetime.now()
        times = [t+timedelta(minutes=n) for n in list(range(number_of_minutes))]
        return TestQuartz(times)


def random_datetime(year=list(range(2017,2056)),
                    month=list(range(1,13)),
                    day=list(range(1,32)),
                    hour=list(range(0,24)),
                    minute=list(range(0,60)),
                    second=list(range(0,60)),
                    microsecond=list(range(0,1001))):
    import random
    while True:
        parts = [ 
            random.choice(year),
            random.choice(month),
            random.choice(day),
            random.choice(hour),
            random.choice(minute),
            random.choice(second),
            random.choice(microsecond)
        ]
        try:
            return datetime(*parts)
        except ValueError:
            continue


class JobTestCase(unittest.TestCase):

    maxDiff = None

    def assertCronTimeToStr(self, expected, **kargs):
        cron_time = TimeSpec(**kargs)
        self.assertEquals(expected, str(cron_time))

    def assertFunctorToStr(self, expected, *args, **kwargs):
        functor = Functor(*args, **kwargs)
        self.assertEquals(expected, str(functor))

    def test_cron_time_to_str(self):
        self.assertCronTimeToStr('* * * * *')
        self.assertCronTimeToStr('0,1,2 * * * *', minute=[0,1,2])
        self.assertCronTimeToStr('* 0,1,2 * * *', hour=[0,1,2])
        self.assertCronTimeToStr('* * 0,1,2 * *', day=[0,1,2])
        self.assertCronTimeToStr('* * * 0,1,2 *', month=[0,1,2])
        self.assertCronTimeToStr('* * * * 0,1,2', dow=[0,1,2])

    def test_functor_to_str(self):
        self.assertFunctorToStr("datetime()", datetime)
        self.assertFunctorToStr("datetime('param1')", datetime, 'param1')
        self.assertFunctorToStr("timedelta('param1', 'param2')", timedelta, 'param1', 'param2')
        self.assertFunctorToStr("datetime(param1='param1')", datetime, param1='param1')
        self.assertFunctorToStr("datetime('positional', kwarg='my_kargs')", datetime, 'positional', kwarg='my_kargs')

    def test_cron_matching_any_time(self):
        ITERATIONS = 50
        cron_time = TimeSpec()
        for n in list(range(ITERATIONS)):
            self.assertTrue(cron_time.is_matchtime(random_datetime()))

    def test_cron_matching_minutes(self):
        ITERATIONS = 50
        cron_time = TimeSpec(minute=[0,3])
        for n in list(range(ITERATIONS)):
            self.assertTrue(cron_time.is_matchtime(random_datetime(minute=(0,3))))
        for n in list(range(ITERATIONS * 10)):
            self.assertFalse(cron_time.is_matchtime(random_datetime(minute=(1,2,4,5,6,7,8,30,31,32,34,42,58,59))))

    def test_cron_matching_hours(self):
        ITERATIONS = 50
        cron_time = TimeSpec(hour=[7,9,15,23])                      
        for n in list(range(ITERATIONS)):
            self.assertTrue(cron_time.is_matchtime(random_datetime(hour=(7,9,15,23))))
        for n in list(range(ITERATIONS * 10)):
            self.assertFalse(cron_time.is_matchtime(random_datetime(hour=(0,1,2,3,4,5,6,8,10,11,12,13,14,16,17,18,19,20,21,22))))

    def test_cron_matching_day_of_month(self):
        ITERATIONS = 50
        cron_time = TimeSpec(day=[7,9,15,23])                      
        for n in list(range(ITERATIONS)):
            self.assertTrue(cron_time.is_matchtime(random_datetime(day=(7,9,15,23))))
        for n in list(range(ITERATIONS * 10)):
            self.assertFalse(cron_time.is_matchtime(random_datetime(day=(0,1,2,3,4,5,6,8,10,11,12,13,14,16,17,18,19,20,21,22,30,31))))

    def test_cron_matching_day_of_month_near_end(self):
        ITERATIONS = 200
        cron_time = TimeSpec(day=[30,31])                      
        for n in list(range(ITERATIONS)):
            self.assertTrue(cron_time.is_matchtime(random_datetime(day=(30,31))))
        for n in list(range(ITERATIONS * 10)):
            self.assertFalse(cron_time.is_matchtime(random_datetime(day=list(range(1,30)))))

    def test_cron_matching_months(self):
        ITERATIONS = 50
        cron_time = TimeSpec(month=[1,4,8,11])                      
        for n in list(range(ITERATIONS)):
            self.assertTrue(cron_time.is_matchtime(random_datetime(month=(1,4,8,11))))
        for n in list(range(ITERATIONS * 10)):
            self.assertFalse(cron_time.is_matchtime(random_datetime(month=(2,3,5,6,7,9,10,12))))

    # TODO: Test Day Of Week
    # Requires knowledge of how to construct a datetime such that datetime.weekday()
    # generates the expected values for testing.
    def _test_cron_matching_day_of_week(self):
        ITERATIONS = 50
        cron_time = TimeSpec(dow=[0,4,6])                      
        for n in list(range(ITERATIONS)):
            self.assertTrue(cron_time.is_matchtime(random_datetime(dow=(0,4,6))))
        for n in list(range(ITERATIONS * 10)):
            self.assertFalse(cron_time.is_matchtime(random_datetime(dow=(1,2,3,5))))

    def test_cron_matching_XXX(self):
        ITERATIONS = 50
        cron_time = TimeSpec(month=[2,7,8,9], hour=[0,4,23], minute=[0,1,2,5,9,12,34,38,49,58,59])                      
        for n in list(range(ITERATIONS)):
            self.assertTrue(cron_time.is_matchtime(random_datetime(month=(2,7,8,9),
                                                                   hour=(0,4,23),
                                                                   minute=(0,1,2,5,9,12,34,38,49,58,59))))
        for n in list(range(ITERATIONS * 10)):
            self.assertFalse(cron_time.is_matchtime(random_datetime(month=(1,3,4,5,6,10,11,12),
                                                                   hour=(0,4,23),
                                                                   minute=(0,1,2,5,9,12,34,38,49,58,59))))
            self.assertFalse(cron_time.is_matchtime(random_datetime(month=(2,7,8,9),
                                                                   hour=(1,2,3,5,6,7,8,9,10,11,15,16,17,18,20,21,22),
                                                                   minute=(0,1,2,5,9,12,34,38,49,58,59))))
            self.assertFalse(cron_time.is_matchtime(random_datetime(month=(2,7,8,9),
                                                                   hour=(0,4,23),
                                                                   minute=(3,4,7,8,10,35,36,37,45,46,47,48,50,51,56,57))))

    @contextmanager
    def crontab_harness(self, expected, minutes):
        call_register = []
        now = datetime.now()

        # Fake run for 5 minutes from now
        quartz = TestQuartz.ConsecutiveTimes(minutes)

        crontab = CronTab(quartz)
        yield crontab, call_register.append, now
        crontab.start()

        self.assertEquals(expected, call_register)

    def test_every_minute_for_five_minutes(self):
        expected = ['Every Minute'] * 5

        with self.crontab_harness(expected, minutes=5) as (crontab, callback, start_time):
            crontab.create_job(TimeSpec(), callback, 'Every Minute')
            crontab.create_job(TimeSpec(start_time.minute +10), callback, 'Past 5 minutes')

    def test_specific_minute_for_3_hours(self):
        expected = ['Half Past the Hour'] * 3

        with self.crontab_harness(expected, minutes=3 * 60) as (crontab, callback, start_time):
            crontab.create_job(TimeSpec(30), callback, 'Half Past the Hour')

    def test_specific_time_for_4_days(self):
        expected = ['7:59'] * 4

        with self.crontab_harness(expected, minutes=4 * 24 * 60) as (crontab, callback, start_time):
            crontab.create_job(TimeSpec(59, 7), callback, '7:59')

    def test_every_minute_for_a_specific_hour_over_a_day(self):
        expected = ['In The Hour'] * 60

        with self.crontab_harness(expected, minutes=24 * 60) as (crontab, callback, start_time):
            crontab.create_job(TimeSpec(hour=12), callback, 'In The Hour')

    def test_for_3_specific_minutes_in_2_specific_hours_over_a_day(self):
        expected = ['Specificed Time'] * 6

        with self.crontab_harness(expected, minutes=24 * 60) as (crontab, callback, start_time):
            crontab.create_job(TimeSpec(minute=(1,2,59), hour=(12,23)), callback, 'Specificed Time')

    def test_a_specific_time_on_2_specific_days(self):
        expected = ['Specificed Time'] * 4

        with self.crontab_harness(expected, minutes=7 * 24 * 60) as (crontab, callback, start_time):
            crontab.create_job(TimeSpec(minute=10, hour=(12,23), dow=(0,4)), callback, 'Specificed Time')

    # TODO: Test Day Of Week
    # More refactoring is needed to completly remove dependency on datetime.now() 
    # in CronTab (or at least mock it out)
    def _test_random_times(self):
        expected = ['+1', '+10', '+60', '+1']
        with self.crontab_harness(expected, minutes=63) as (crontab, callback, start_time):
            crontab.create_job(TimeSpec(start_time.minute +1), callback, 'xx:01')
            crontab.create_job(TimeSpec(start_time.minute +30), callback, 'xx:30')
            crontab.create_job(TimeSpec(hour=start_time.hour +1), callback, '1:xx')
            crontab.create_job(TimeSpec(hour=start_time.hour +3), callback, '3:xx')
            crontab.create_job(TimeSpec(start_time.minute, start_time.hour +1), callback, '1:00')
            crontab.create_job(TimeSpec(start_time.minute, start_time.hour +3), callback, '3:00')


if __name__ == '__main__':
    import logging
    import cronjobs
    logger = logging.getLogger(cronjobs.__name__)
    logger.setLevel(logging.ERROR)
    unittest.main()
