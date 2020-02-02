import xbmc, xbmcaddon
import os, sys
__cwd__      = xbmc.translatePath( xbmcaddon.Addon().getAddonInfo('path') ).decode("utf-8")
__resource__ = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) ).decode("utf-8")
sys.path.append(__resource__)

import logging
import time
from alarm_clock import Alarm, AlarmClock
from cronjobs import CronTab
import settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(format='[%(levelname)-7s] %(asctime)s %(name)s: %(message)s')


def CEC_activate_source():
    try:
        xbmc.executebuiltin('CECActivateSource')
    except Exception:
        logger.debug("CECActivateSource not supported")


def CEC_deactivate_source():
    try:
        xbmc.executebuiltin('CECStandby')
    except Exception:
        logger.debug("CECActivateSource not supported")


def set_volume(volume):
    xbmc.executebuiltin('SetVolume(%s)' % volume)


def stop_playing():
    xbmc.Player().stop()


def fade_volume(start, end, fade_seconds):
    if fade_seconds == 0:
        set_volume(end)
    else:
        volume_delta = float(end - start)
        volume_step = 1 if volume_delta > 0 else -1
        pause_duration = abs(fade_seconds / volume_delta)

        for vol in range(start, end + volume_step, volume_step):
            set_volume(vol)
            time.sleep(pause_duration)


def fade_volume_in(volume, fade_seconds):
    fade_volume(0, volume, fade_seconds)


def play_with_volume_fade_in(file, max_volume, fade_seconds):
    set_volume(0)
    xbmc.Player().play(file)
    fade_volume_in(max_volume, fade_seconds)


def stop_with_volume_fade_out(fade_seconds):
    original_volume = fade_volume_out(fade_seconds)
    stop_playing()
    set_volume(original_volume)



class KodiQuartz(CronTab.Quartz):
    def __init__(self, monitor):
        super(KodiQuartz, self).__init__()
        self.monitor = monitor

    def is_still_alive(self):
        return super(KodiQuartz, self).is_still_alive() \
                and not xbmc.abortRequested

    def _sleep(self, delay_seconds):
        self.monitor.waitForAbort(delay_seconds)


class Speakers(object):
    def play(self, data):
        if data['cec'] == 1:
            CEC_activate_source()
        elif data['cec'] == 2:
            CEC_deactivate_source()

        logger.info("Playing %s" % data['play'])
        play_with_volume_fade_in(data['play'], data['volume'], fade_seconds=data['fade'])

    def pause(self):
        logger.info("Pausing alarm")
        stop_playing()


class AlarmClockMonitor(xbmc.Monitor):
    """Monitor subclass listening on configuration changes and termination
    requests."""
    def __init__(self, alarmClock):
        xbmc.Monitor.__init__(self)
        self.alarmClock = alarmClock
        self.onSettingsChanged()


    def onSettingsChanged(self):
        logger.info("Settings Changed")
        alarms = settings.getAlarms()
        trigger_id = settings.get_triggered_alarm()
        if trigger_id:
            logger.info("Trigger Alarm ID: %s" % trigger_id)
            for alarm, data in alarms:
                if alarm.id == int(trigger_id):
                    self.alarmClock.start_alarm(alarm.ToNow(), data)
                    break
            settings.reset_triggerd_alarm()
        else:
            alarms = [(alarm, data) for alarm, data in alarms if data['enabled']]
            self.alarmClock.applySettings(alarms)


    def onAbortRequested(self):
        logger.debug("Abort Requested")
        self.alarmClock.crontab.quartz.kill()


if __name__ == '__main__':

    logger.info('Starting service' + ' '.join(sys.argv))
    crontab = CronTab()
    speakers = Speakers()
    alarmClock = AlarmClock(crontab, speakers)
    monitor = AlarmClockMonitor(alarmClock)

    quartz = KodiQuartz(monitor)
    crontab.quartz = quartz

    alarmClock.crontab.start()

    logger.info('Ended service' + ' '.join(sys.argv))
