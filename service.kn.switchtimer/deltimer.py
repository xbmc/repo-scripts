import xbmc
import handler

if __name__ ==  '__main__':

    handler.notifyLog('Parameter handler called: Delete Timerlist')
    try:
        if not handler.clearTimerList():
            handler.notifyLog('Timerlist couldn\'t deleted', xbmc.LOGERROR)
    except Exception, e:
            handler.notifyLog('Script error, Timer couldn\'t deleted', xbmc.LOGERROR)