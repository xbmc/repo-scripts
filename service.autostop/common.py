import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import time

msgdialogprogress = xbmcgui.DialogProgress()
addon = xbmcaddon.Addon()
addon_path = addon.getAddonInfo("path")
addon_icon = addon_path + '/resources/icon.png'
notifycount = 0

def translate(text):
    return addon.getLocalizedString(text)


def settings(setting, value = None):
    # Get or add addon setting
    if value:
        xbmcaddon.Addon().setSetting(setting, value)
    else:
        return xbmcaddon.Addon().getSetting(setting)


def playCount(plcount, padjust, plflag, paflag, asevlog):       #  Calculate play counter

    match = 0    
    if plflag == 0 and paflag == 0:                             #  No file playing or paused
        plcount = 0
        match = 1
    elif padjust == 'None':                                     #  Count uninterrupted by pause
        plcount += 1
        match = 2
    elif padjust == 'Pause' and plflag == 1:                    #  Continue counter
        plcount += 1
        match = 3
    elif padjust == 'Pause' and paflag == 1:                    #  Pause counter 
        plcount = plcount
        match = 4
    elif padjust == 'Reset' and plflag == 1:                    #  Continue counter
        plcount += 1
        match = 5
    elif padjust == 'Reset' and paflag == 1:                    #  Reset counter
        plcount = 0
        match = 6

    if asevlog == 'true' and plcount % 10 == 0:
        xbmc.log('Autostop playCount: ' + str(plcount) + ' ' + padjust + ' ' +   \
        str(plflag) + ' ' + str(paflag) + ' ' + str(match), xbmc.LOGINFO)

    return plcount


def sleepNotify(plcount, plstoptime, plflag, plnotify, plextend, asevlog, paflag):

    global notifycount
    extime = float(settings('extime'))
    notifyset = settings('notifyset')
    varextnotify = settings('varextnotify')
    totalstoptime = plstoptime + extime
    if plstoptime > 0 and plcount + plnotify >= totalstoptime \
    * 60 and (plflag > 0 or (plflag == 0 and paflag == 1)):     #  Set or update notification
        xbmc.log('Autostop sleepNotify set notification.', xbmc.LOGDEBUG)
        if notifyset == 'no' and varextnotify =='no':           #  Notifications not set
            msgdialogprogress.create(translate(30307), translate(30308))
            settings('notifyset', 'yes')
            notifycount = 0
            xbmc.log('Autostop notify counter started.', xbmc.LOGINFO)
        elif notifyset == 'yes':                                # Update notification
            notifycount += 1
            if notifycount >= plnotify:                         # Upper bounds check
                percent = 0
                tremain = '0'
                msgdialogprogress.close()
            else:
                percent = 100 - int(float(notifycount) / float(plnotify) * 100)
                tremain = str(plnotify - notifycount)  
            message = translate(30308) + tremain + translate(30311)           
            msgdialogprogress.update(percent, message)
            if asevlog == 'true' and plcount % 10 == 0:
                xbmc.log('Autostop notify counter: ' + str(plcount) + ' ' + str(plnotify) + ' ' +   \
                str(totalstoptime * 60) + ' ' + str(percent) + ' ' + str(notifycount) + ' ' +       \
                str(plstoptime), xbmc.LOGINFO)
            if (msgdialogprogress.iscanceled()):
                if plextend > 0:                                # Fixed extension
                    extime = extime + plextend
                    settings('extime', str(extime))             # Extend sleep counter 
                    extmins = str(plextend)
                else:                                           # Get variable extension time
                    extmins = varExtension(totalstoptime, plcount, asevlog)
                    extime = extime + float(extmins) 
                    settings('extime', str(extime))             
                msgdialogprogress.close()
                dialog = xbmcgui.Dialog()
                mgenlog = translate(30309) + extmins + translate(30313)
                xbmc.log(mgenlog, xbmc.LOGINFO)
                dialog.notification(translate(30310), mgenlog, addon_icon, 3000)
                settings('notifyset', 'no')                     # Clear notification flag
    elif notifyset == 'yes' and plflag == 0 and paflag == 0:                    
        msgdialogprogress.close()   
        settings('notifyset', 'no')                             # Clear notification flag

    if plflag > 0 and asevlog == 'true' and plcount % 10 == 0:  # Activity logging
        xbmc.log('Autostop sleepNotify counter: ' +            \
        str(plcount + plnotify) + ' ' +  str(plstoptime * 60)  \
        + ' ' + str(totalstoptime * 60), xbmc.LOGINFO)

    if plflag == 0 and paflag == 0 and extime > 0:              # Check for playback ended
        settings('extime', '0')                                 # Temporary extension clear       


def varExtension(plstoptime, plcount, asevlog):                 # Get variable extension time
    
    pselect = ["10 minutes", "20 minutes", "30 minutes", "40 minutes",           \
    "50 minutes", "60 minutes", "90 minutes"]
    remtime = checkTime(plstoptime, plcount, asevlog)           # Get remaining playback time 
    if float(remtime) > 0:
        pselect.extend(["End of current file (" + remtime + " mins)"])    
    if settings('stopplay') == 'true':                          # Add stop now playback option       
        pselect.extend(["[COLOR blue]Stop Playback Now[/COLOR]"]) 

    ddialog = xbmcgui.Dialog()    
    selection = ddialog.select(translate(30315), pselect)
    if selection < 0:                                           # User cancel. Default is 5
        extension = '5'                                         # minutes to avoid GUI loop
    elif 'minutes' in (pselect[selection]):
        extension = (pselect[selection])[:2]                    # Get minutes from selection
    elif 'End' in (pselect[selection]):
        extension = checkTime(plstoptime, plcount, asevlog)     # Get remaining playback time
    elif 'Stop' in (pselect[selection]):
        extension = '0'
        notifymsg = translate(30310)
        logmsg = translate(30318)
        stopPlayback(notifymsg, logmsg)                         # User requested stop playback

    return extension


def stopPlayback(notifymsg, logmsg):                            # Function to stop playback
                                                                # log and notify user
    try:
        if xbmc.Player().isPlayingVideo():
            ptag = xbmc.Player().getVideoInfoTag()
            ptitle = ptag.getTitle()
        elif xbmc.Player().isPlayingAudio():
            ptag = xbmc.Player().getMusicInfoTag()
            ptitle = ptag.getTitle()                
        else:
            ptitle = "playing file"
        pos = xbmc.Player().getTime()
        xbmc.Player().stop()
        mgenlog = logmsg + ptitle + ' at: ' + time.strftime("%H:%M:%S",    \
        time.gmtime(pos))
        xbmc.log(mgenlog, xbmc.LOGINFO)
        dialog = xbmcgui.Dialog()
        dialog.notification(notifymsg, mgenlog, addon_icon, 5000)
        if settings('screensaver') == 'true':                   #  Active screensaver if option selected
            xbmc.executebuiltin('ActivateScreensaver')
        if settings('asreset') == 'true':                       #  Reset sleep timer if option selected
            settings('plstop', '0')
            mgenlog = "Autostop sleep timer reset enabled.  Sleep timer reset to 0."
            xbmc.log(mgenlog, xbmc.LOGINFO)
        settings('notifyset', 'no')                             # Clear notification flag
        settings('varextnotify', 'no')                          # Clear notification flag
    except:
        xbmc.log('Autostop error when stopping playback.', xbmc.LOGINFO)        


def checkTime(plstoptime, plcount, asevlog):                    # Calculate remaining playback time

    try:
        currpos = xbmc.Player().getTime()
        endpos = int(xbmc.Player().getTotalTime())
        remaintime = endpos - currpos - (plstoptime * 60 - plcount) -   \
        (10 - plcount % 10) - 1                                 # 1 second less than end time
        if remaintime > 10800:                                  # Maximum 3 hrs
            remaintime = 10800
        extension = '{:.2f}'.format(remaintime / float(60))     # Calculate to .01 min
        if asevlog == 'true':
            xbmc.log('Autostop calculating extension time. ' + str(currpos) + ' ' +     \
            str(endpos) + ' ' + str(plcount) + ' ' + str(remaintime) + ' ' + extension  \
            + ' ' + str(plstoptime * 60), xbmc.LOGINFO)
        settings('varextnotify', 'yes')                         # Only display progress bar once  
        return extension
    except:
        xbmc.log('Autostop error getting remaining extension time.', xbmc.LOGINFO)
        return '-1'

    
def checkNotify():                                              # Verify plstop and plnotify are both 10 minutes

    try:
        plnotify = int(settings('plnotify'))
        plstoptime = int(settings('plstop')) 

        if plnotify == plstoptime * 60:
            settings('plnotify', '300')                         # Stop timer and notification timer cannot be the same
            notifymsg = translate(30310)
            mgenlog = translate(30321)
            xbmc.log(mgenlog, xbmc.LOGINFO)
            dialog = xbmcgui.Dialog()
            dialog.notification(notifymsg, mgenlog, addon_icon, 5000)
    except:
        xbmc.log('Autostop error processing checkNotify comparison.', xbmc.LOGINFO)                            


