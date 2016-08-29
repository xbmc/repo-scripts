import sys
import time
import datetime
import xbmc, xbmcaddon, xbmcgui
import os
import operator

__addon__ = xbmcaddon.Addon()
__addonid__ = __addon__.getAddonInfo('id')
__addonname__ = __addon__.getAddonInfo('name')
__path__ = __addon__.getAddonInfo('path')
__version__ = __addon__.getAddonInfo('version')
__LS__ = __addon__.getLocalizedString

__IconDefault__ = xbmc.translatePath(os.path.join( __path__,'resources', 'media', 'default.png'))
__IconAlert__ = xbmc.translatePath(os.path.join( __path__,'resources', 'media', 'alert.png'))
__IconOk__ = xbmc.translatePath(os.path.join( __path__,'resources', 'media', 'ok.png'))

__confirmTmrAdded__ = True if __addon__.getSetting('confirmTmrAdded').upper() == 'TRUE' else False

OSD = xbmcgui.Dialog()
OSDProgress = xbmcgui.DialogProgress()

def getSetting(setting):
    return __addon__.getSetting(setting)

def getDateFormat():
    df = xbmc.getRegion('dateshort')
    tf = xbmc.getRegion('time').split(':')

    try:
        # time format is 12h with am/pm
        return df + ' ' + tf[0][0:2] + ':' + tf[1] + ' ' + tf[2].split()[1]
    except IndexError:
        # time format is 24h with or w/o leading zero
        return df + ' ' + tf[0][0:2] + ':' + tf[1]

def notifyLog(message, level=xbmc.LOGNOTICE):
    xbmc.log('[%s] %s' % (__addonid__, message.encode('utf-8')), level)

def notifyOSD(header, message, icon=__IconDefault__, time=5000):
    OSD.notification(header.encode('utf-8'), message.encode('utf-8'), icon, time)

def date2timeStamp(date, format=getDateFormat()):
    try:
        dtime = datetime.datetime.strptime(date, format)
    except TypeError:
        try:
            dtime = datetime.datetime.fromtimestamp(time.mktime(time.strptime(date, format)))
        except ValueError:
            notifyLog('Couldn\'t parse date: %s' % (date), xbmc.LOGERROR)
            notifyOSD(__LS__(30000), __LS__(30020), icon=__IconAlert__)
            return False
    except Exception:
        notifyLog('Couldn\'t parse date: %s' % (date), xbmc.LOGERROR)
        notifyOSD(__LS__(30000), __LS__(30020), icon=__IconAlert__)
        return False
    return int(time.mktime(dtime.timetuple()))

def readTimerStrings():
    xbmc.sleep(1000)
    timers = []
    for prefix in ['t0:', 't1:', 't2:', 't3:', 't4:', 't5:', 't6:', 't7:', 't8:', 't9:']:
        if xbmc.getInfoLabel('Skin.String(%s)' % (prefix + 'date')) != '':
            timers.append({'channel': xbmc.getInfoLabel('Skin.String(%s)' % (prefix + 'channel')),
                           'icon': xbmc.getInfoLabel('Skin.String(%s)' % (prefix + 'icon')),
                           'date': xbmc.getInfoLabel('Skin.String(%s)' % (prefix + 'date')),
                           'utime': date2timeStamp(xbmc.getInfoLabel('Skin.String(%s)' % (prefix + 'date'))),
                           'title': xbmc.getInfoLabel('Skin.String(%s)' % (prefix + 'title'))
                          })
    return timers

def writeTimerStrings(timers):
    timers.sort(key=operator.itemgetter('utime'))
    _idx = 0
    for prefix in ['t0:', 't1:', 't2:', 't3:', 't4:', 't5:', 't6:', 't7:', 't8:', 't9:']:
        if _idx < len(timers):
            # Set the Skin Strings

            xbmc.executebuiltin('Skin.SetString(%s,%s)' % (prefix + 'channel', timers[_idx]['channel']))
            xbmc.executebuiltin('Skin.SetString(%s,%s)' % (prefix + 'icon', timers[_idx]['icon']))
            xbmc.executebuiltin('Skin.SetString(%s,%s)' % (prefix + 'date', timers[_idx]['date']))
            xbmc.executebuiltin('Skin.SetString(%s,%s)' % (prefix + 'title', timers[_idx]['title']))
            _idx += 1
        else:
            # Reset the skin strings
            clearTimer(prefix, update=False)

    if __addon__.getSetting('cntTmr') != str(_idx):
        __addon__.setSetting('cntTmr', str(_idx))
        xbmc.executebuiltin('Skin.SetString(SwitchTimerActiveItems,%s)' % (str(_idx)))

def setSwitchTimer(channel, icon, date, title):
    utime = date2timeStamp(date)

    if not utime: return False

    if int(time.time()) > utime:
        notifyLog('Timer date is in the past')
        notifyOSD(__LS__(30000), __LS__(30022), icon=__IconAlert__)
        return False

    timers = readTimerStrings()

    for timer in timers:
        if timer['utime'] == utime:
            notifyLog('Timer already set')
            notifyOSD(__LS__(30000), __LS__(30023), icon=__IconAlert__)
            return False

    timers.append({'channel': channel, 'icon': icon, 'date': date, 'utime': utime, 'title': title})

    if len(timers) > 10:
        notifyLog('Timer limit exceeded, no free slot', xbmc.LOGERROR)
        notifyOSD(__LS__(30000), __LS__(30024), icon=__IconAlert__)
        return False

    writeTimerStrings(timers)
    notifyLog('Timer added @%s, %s, %s' % (date, channel.decode('utf-8'), title.decode('utf-8')))
    if __confirmTmrAdded__: notifyOSD(__LS__(30000), __LS__(30021), icon=__IconOk__)
    return True

def clearTimerList():
    for prefix in ['t0:', 't1:', 't2:', 't3:', 't4:', 't5:', 't6:', 't7:', 't8:', 't9:']: clearTimer(prefix, update=False)
    writeTimerStrings(readTimerStrings())
    return True

def clearTimer(timer, update=True):
    if xbmc.getInfoLabel('Skin.String(%s)' % (timer + 'date')) != '':
        xbmc.executebuiltin('Skin.Reset(%s)' % (timer + 'channel'))
        xbmc.executebuiltin('Skin.Reset(%s)' % (timer + 'icon'))
        xbmc.executebuiltin('Skin.Reset(%s)' % (timer + 'date'))
        xbmc.executebuiltin('Skin.Reset(%s)' % (timer + 'title'))
        notifyLog('Timer %s deleted' % (timer[:-1]))
        if update: writeTimerStrings(readTimerStrings())

if __name__ ==  '__main__':

    notifyLog('Parameter handler called')
    try:
        if sys.argv[1]:
            args = {'action':None, 'channel':'', 'icon': '','date':'', 'title':''}
            pars = sys.argv[1:]
            for par in pars:
                try:
                    item, value = par.split('=')
                    args[item] = value
                except ValueError:
                    args[item] += ', ' + par
            if args['action'] == 'add':
                if not setSwitchTimer(args['channel'], args['icon'], args['date'], args['title']):
                    notifyLog('Timer couldn\'t or wouldn\'t set', xbmc.LOGERROR)
            elif args['action'] == 'del':
                clearTimer(args['timer'] + ':')
            elif args['action'] == 'delall':
                clearTimerList()
    except IndexError:
            notifyLog('Calling this script without parameters is not allowed', xbmc.LOGERROR)
            OSD.ok(__LS__(30000),__LS__(30030))
    except Exception, e:
            notifyLog('Script error, Timer couldn\'t set', xbmc.LOGERROR)
