import xbmc
import handler

if __name__ ==  '__main__':

    handler.notifyLog('Parameter handler called: add Timer')
    try:
        args = {'channel':xbmc.getInfoLabel('ListItem.ChannelName'),
                'icon':xbmc.getInfoLabel('ListItem.Icon'),
                'date':xbmc.getInfoLabel('ListItem.Date'),
                'title':xbmc.getInfoLabel('ListItem.Title')
                }

        if not handler.setSwitchTimer(args['channel'], args['icon'], args['date'], args['title']):
            handler.notifyLog('Timer couldn\'t or wouldn\'t set', xbmc.LOGERROR)
    except Exception, e:
            handler.notifyLog('Script error, Timer couldn\'t set', xbmc.LOGERROR)