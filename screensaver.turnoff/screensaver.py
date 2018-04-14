import sys
import subprocess

import xbmc
import xbmcaddon
import xbmcgui


def log_error(msg='', level=xbmc.LOGERROR):
    xbmc.log(msg='[%s] %s' % (addon_name, msg), level=level)


def log_notice(msg='', level=xbmc.LOGNOTICE):
    xbmc.log(msg='[%s] %s' % (addon_name, msg), level=level)


def popup(heading='', msg='', delay=10000, icon=''):
    if not heading:
        heading = '%s screensaver failed' % addon_name
    if not icon:
        icon = addon_icon
    xbmcgui.Dialog().notification(heading, msg, icon, delay)


def run_builtin(builtin):
    log_notice(msg="Executing builtin '%s'" % builtin)
    try:
        xbmc.executebuiltin(builtin)
    except Exception as e:
        log_error(msg="Exception executing builtin '%s': %s" % (builtin, e))
        popup(msg="Exception executing builtin '%s': %s" % (builtin, e))


def run_command(command, shell=False):
    # TODO: Add options for running using su or sudo
    try:
        cmd = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=shell)
        (out, err) = cmd.communicate()
        if cmd.returncode == 0:
            log_notice(msg="Running command '%s' returned rc=%s" % (' '.join(command), cmd.returncode))
        else:
            log_error(msg="Running command '%s' failed with rc=%s" % (' '.join(command), cmd.returncode))
            if err:
                log_error(msg="Command '%s' returned on stderr: %s" % (command[0], err))
            if out:
                log_error(msg="Command '%s' returned on stdout: %s " % (command[0], out))
            popup(msg="%s\n%s" % (out, err))
            sys.exit(1)
    except Exception as e:
        log_error(msg="Exception running '%s': %s" % (command[0], e))
        popup(msg="Exception running '%s': %s" % (command[0], e))
        sys.exit(2)


class Screensaver(xbmcgui.WindowXMLDialog):

    class Monitor(xbmc.Monitor):

        def __init__(self, callback):
            self._callback = callback

        def onScreensaverDeactivated(self):
            self._callback()

    def __init__(self, *args, **kwargs):
        pass

    def onInit(self):
        self._monitor = self.Monitor(self.exit)

        # Power off system
        if power_method != 0:
            log_notice(msg='Turn system off using method %s' % power_method)
        if power_method == '1':  # Suspend (built-in)
            run_builtin('Suspend')
        elif power_method == '2':  # Hibernate (built-in)
            run_builtin('Hibernate')
        elif power_method == '3':  # Quit (built-in)
            run_builtin('Quit')
        elif power_method == '4':  # ShutDown action (built-in)
            run_builtin('ShutDown')
        elif power_method == '5':  # Reboot (built-in)
            run_builtin('Reboot')
        elif power_method == '6':  # PowerDown (built-in)
            run_builtin('PowerDown')
        elif power_method == '7':  # Android POWER key event (using input)
            run_command(['su', '-c', 'input keyevent KEYCODE_POWER'], shell=True)

    def onAction(self, action):
        self.exit()

    def exit(self):
        # Unmute audio
        if mute == 'true':
            run_builtin('Mute')

        # Turn on display
        if display_method != 0:
            log_notice(msg='Turn display signal back on using method %s' % display_method)
        if display_method == '1':  # CEC (built-in)
            run_builtin('CECActivateSource')
        elif display_method == '2':  # No Signal on Raspberry Pi (using vcgencmd)
            run_command(['vcgencmd', 'display_power', '1'])
        elif display_method == '3':  # DPMS (built-in)
            run_builtin('ToggleDPMS')
        elif display_method == '4':  # DPMS (using xset)
            run_command(['xset', 'dpms', 'force', 'on'])
        elif display_method == '5':  # DPMS (using vbetool)
            run_command(['vbetool', 'dpms', 'on'])
        elif display_method == '6':  # DPMS (using xrandr)
            # NOTE: This needs more outside testing
            run_command(['xrandr', '--output CRT-0', 'on'])
        elif display_method == '7':  # CEC on Android (kernel)
            # NOTE: This needs more outside testing
            run_command(['su', '-c', 'echo 1 >/sys/devices/virtual/graphics/fb0/cec'], shell=True)

        del self._monitor
        self.close()

if __name__ == '__main__':
    addon = xbmcaddon.Addon()

    addon_name = addon.getAddonInfo('name')
    addon_path = addon.getAddonInfo('path')
    addon_icon = addon.getAddonInfo('icon')
    display_method = addon.getSetting('display_method')
    power_method = addon.getSetting('power_method')
    logoff = addon.getSetting('logoff')
    mute = addon.getSetting('mute')

    # Turn off display
    if display_method != 0:
        log_notice(msg='Turn display signal off using method %s' % display_method)
    if display_method == '1':  # CEC (built-in)
        run_builtin('CECStandby')
    elif display_method == '2':  # No Signal on Raspberry Pi (using vcgencmd)
        run_command(['vcgencmd', 'display_power', '0'])
    elif display_method == '3':  # DPMS (built-in)
        run_builtin('ToggleDPMS')
    elif display_method == '4':  # DPMS (using xset)
        run_command(['xset', 'dpms', 'force', 'off'])
    elif display_method == '5':  # DPMS (using vbetool)
        run_command(['vbetool', 'dpms', 'off'])
    elif display_method == '6':  # DPMS (using xrandr)
        # NOTE: This needs more outside testing
        run_command(['xrandr', '--output CRT-0', 'off'])
    elif display_method == '7':  # CEC on Android (kernel)
        # NOTE: This needs more outside testing
        run_command(['su', '-c', 'echo 0 >/sys/devices/virtual/graphics/fb0/cec'], shell=True)


    # FIXME: Screensaver always seems to log off when logged in ?
    # Log off user
    if logoff == 'true':
        run_builtin('System.Logoff()')

    # Mute audio
    if mute == 'true':
        run_builtin('Mute')

    # Do not start screensaver when command fails
    screensaver = Screensaver('screensaver-turnoff.xml', addon_path, 'default')
    screensaver.doModal()
    del screensaver
