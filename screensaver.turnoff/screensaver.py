# -*- coding: utf-8 -*-
# Copyright: (c) 2018, Dag Wieers (@dagwieers) <dag@wieers.com>
# GNU General Public License v2.0 (see COPYING or https://www.gnu.org/licenses/gpl-2.0.txt)
''' This Kodi addon turns off display devices when Kodi goes into screensaver-mode '''

from __future__ import absolute_import, division, unicode_literals
import sys
import atexit
from xbmc import Monitor
from xbmcgui import WindowXMLDialog

# NOTE: The below order relates to resources/settings.xml
DISPLAY_METHODS = [
    dict(name='do-nothing', title='Do nothing',
         function='log',
         args_off=[2, 'Do nothing to power off display'],
         args_on=[2, 'Do nothing to power back on display']),
    dict(name='cec-builtin', title='CEC (buil-in)',
         function='run_builtin',
         args_off=['CECStandby'],
         args_on=['CECActivateSource']),
    dict(name='no-signal-rpi', title='No Signal on Raspberry Pi (using vcgencmd)',
         function='run_command',
         args_off=['vcgencmd', 'display_power', '0'],
         args_on=['vcgencmd', 'display_power', '1']),
    dict(name='dpms-builtin', title='DPMS (built-in)',
         function='run_builtin',
         args_off=['ToggleDPMS'],
         args_on=['ToggleDPMS']),
    dict(name='dpms-xset', title='DPMS (using xset)',
         function='run_command',
         args_off=['xset', 'dpms', 'force', 'off'],
         args_on=['xset', 'dpms', 'force', 'on']),
    dict(name='dpms-vbetool', title='DPMS (using vbetool)',
         function='run_command',
         args_off=['vbetool', 'dpms', 'off'],
         args_on=['vbetool', 'dpms', 'on']),
    # TODO: This needs more outside testing
    dict(name='dpms-xrandr', title='DPMS (using xrandr)',
         function='run_command',
         args_off=['xrandr', '--output CRT-0', 'off'],
         args_on=['xrandr', '--output CRT-0', 'on']),
    # TODO: This needs more outside testing
    dict(name='cec-android', title='CEC on Android (kernel)',
         function='run_command',
         args_off=['su', '-c', 'echo 0 >/sys/devices/virtual/graphics/fb0/cec'],
         args_on=['su', '-c', 'echo 1 >/sys/devices/virtual/graphics/fb0/cec']),
    # NOTE: Contrary to what one might think, 1 means off and 0 means on
    dict(name='backlight-rpi', title='Backlight on Raspberry Pi (kernel)',
         function='run_command',
         args_off=['su', '-c', 'echo 1 >/sys/class/backlight/rpi_backlight/bl_power'],
         args_on=['su', '-c', 'echo 0 >/sys/class/backlight/rpi_backlight/bl_power']),
    dict(name='backlight-odroid-c2', title='Backlight on Odroid C2 (kernel)',
         function='run_command',
         args_off=['su', '-c', 'echo 0 >/sys/class/amhdmitx/amhdmitx0/phy'],
         args_on=['su', '-c', 'echo 1 >/sys/class/amhdmitx/amhdmitx0/phy']),
]

POWER_METHODS = [
    dict(name='do-nothing', title='Do nothing',
         function='log', kwargs_off=dict(level=2, message='Do nothing to power off system')),
    dict(name='suspend-builtin', title='Suspend (built-in)',
         function='jsonrpc', kwargs_off=dict(method='System.Suspend')),
    dict(name='hibernate-builtin', title='Hibernate (built-in)',
         function='jsonrpc', kwargs_off=dict(method='System.Hibernate')),
    dict(name='quit-builtin', title='Quit (built-in)',
         function='jsonrpc', kwargs_off=dict(method='Application.Quit')),
    dict(name='shutdown-builtin', title='ShutDown action (built-in)',
         function='jsonrpc', kwargs_off=dict(method='System.Shutdown')),
    dict(name='reboot-builtin', title='Reboot (built-in)',
         function='jsonrpc', kwargs_off=dict(method='System.Reboot')),
    dict(name='powerdown-builtin', title='Powerdown (built-in)',
         function='jsonrpc', kwargs_off=dict(method='System.Powerdown')),
]


class SafeDict(dict):
    ''' A safe dictionary implementation that does not break down on missing keys '''
    def __missing__(self, key):
        ''' Replace missing keys with the original placeholder '''
        return '{' + key + '}'


def from_unicode(text, encoding='utf-8'):
    ''' Force unicode to text '''
    if sys.version_info.major == 2 and isinstance(text, unicode):  # noqa: F821; pylint: disable=undefined-variable
        return text.encode(encoding)
    return text


def to_unicode(text, encoding='utf-8'):
    ''' Force text to unicode '''
    return text.decode(encoding) if isinstance(text, bytes) else text


def addon_icon():
    ''' Cache and return VRT NU Add-on icon '''
    if not hasattr(addon_icon, 'cached'):
        from xbmcaddon import Addon
        addon_icon.cached = to_unicode(Addon().getAddonInfo('icon'))
    return getattr(addon_icon, 'cached')


def addon_id():
    ''' Cache and return VRT NU Add-on ID '''
    if not hasattr(addon_id, 'cached'):
        from xbmcaddon import Addon
        addon_id.cached = to_unicode(Addon().getAddonInfo('id'))
    return getattr(addon_id, 'cached')


def addon_name():
    ''' Cache and return VRT NU Add-on name '''
    if not hasattr(addon_name, 'cached'):
        from xbmcaddon import Addon
        addon_name.cached = to_unicode(Addon().getAddonInfo('name'))
    return getattr(addon_name, 'cached')


def addon_path():
    ''' Cache and return VRT NU Add-on path '''
    if not hasattr(addon_path, 'cached'):
        from xbmcaddon import Addon
        addon_path.cached = to_unicode(Addon().getAddonInfo('path'))
    return getattr(addon_path, 'cached')


def log(level=1, message='', **kwargs):
    ''' Log info messages to Kodi '''
    if not hasattr(log, 'debug_logging'):
        log.debug_logging = get_global_setting('debug.showloginfo')  # Returns a boolean
    max_log_level = int(get_setting('max_log_level', 0))
    if not getattr(log, 'debug_logging') and not (level <= max_log_level and max_log_level != 0):
        return
    if kwargs:
        from string import Formatter
        message = Formatter().vformat(message, (), SafeDict(**kwargs))
    message = '[{addon}] {message}'.format(addon=addon_id(), message=message)
    from xbmc import log as xlog
    xlog(from_unicode(message), level % 3 if getattr(log, 'debug_logging') else 2)


def log_error(message, **kwargs):
    ''' Log error messages to Kodi '''
    if kwargs:
        from string import Formatter
        message = Formatter().vformat(message, (), SafeDict(**kwargs))
    message = '[{addon}] {message}'.format(addon=addon_id(), message=message)
    from xbmc import log as xlog
    xlog(from_unicode(message), 4)


def jsonrpc(**kwargs):
    ''' Perform JSONRPC calls '''
    from json import dumps, loads
    from xbmc import executeJSONRPC
    if 'id' not in kwargs:
        kwargs.update(id=1)
    if 'jsonrpc' not in kwargs:
        kwargs.update(jsonrpc='2.0')
    result = loads(executeJSONRPC(dumps(kwargs)))
    if hasattr(log, 'debug_logging'):
        log(3, "Sending JSON-RPC payload: '{payload}' returns '{result}'", payload=kwargs, result=result)
    return result


def get_setting(setting_id, default=None):
    ''' Get an add-on setting '''
    from xbmcaddon import Addon
    value = to_unicode(Addon().getSetting(setting_id))
    if value == '' and default is not None:
        return default
    return value


def get_global_setting(setting):
    ''' Get a Kodi setting '''
    result = jsonrpc(method='Settings.GetSettingValue', params=dict(setting=setting))
    return result.get('result', {}).get('value')


def notification(heading='', message='', icon='', time=4000):
    ''' Show a Kodi notification '''
    from xbmcgui import Dialog
    if not heading:
        heading = addon_name()
    if not icon:
        icon = addon_icon()
    Dialog().notification(heading=heading, message=message, icon=icon, time=time)


def set_mute(toggle=True):
    ''' Set mute using Kodi JSON-RPC interface '''
    jsonrpc(method='Application.SetMute', params=dict(mute=toggle))


def activate_window(window='home'):
    ''' Set mute using Kodi JSON-RPC interface '''
#    result = jsonrpc(method='GUI.ActivateWindow', params=dict(window=window, parameters=['Home']))
    jsonrpc(method='GUI.ActivateWindow', params=dict(window=window))


def run_builtin(builtin):
    ''' Run Kodi builtins while catching exceptions '''
    from xbmc import executebuiltin
    log(2, "Executing builtin '{builtin}'", builtin=builtin)
    executebuiltin(builtin, True)


def run_command(*command, **kwargs):
    ''' Run commands on the OS while catching exceptions '''
    import subprocess
    # TODO: Add options for running using su or sudo
    try:
        cmd = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, **kwargs)
        (out, err) = cmd.communicate()
        if cmd.returncode == 0:
            log(2, "Running command '{command}' returned rc={rc}", command=' '.join(command), rc=cmd.returncode)
        else:
            log_error("Running command '{command}' failed with rc={rc}", command=' '.join(command), rc=cmd.returncode)
            if err:
                log_error("Command '{command}' returned on stderr: {stderr}", command=command[0], stderr=err)
            if out:
                log_error("Command '{command}' returned on stdout: {stdout} ", command=command[0], stdout=out)
            notification(message="%s\n%s" % (out, err))
            sys.exit(1)
    except OSError as exc:
        log_error("Exception running '{command}': {exc}", command=command[0], exc=exc)
        notification(message="Exception running '%s': %s" % (command[0], exc))
        sys.exit(2)


def func(function, *args, **kwargs):
    ''' Execute a global function with arguments '''
    return globals()[function](*args, **kwargs)


class TurnOffDialog(WindowXMLDialog, object):
    ''' The TurnOffScreensaver class managing the XML gui '''

    def __init__(self, *args):  # pylint: disable=super-init-not-called,unused-argument
        ''' Initialize dialog '''
        self.display = None
        self.logoff = None
        self.monitor = None
        self.mute = None
        self.power = None
        atexit.register(self.exit)

    def onInit(self):  # pylint: disable=invalid-name
        ''' Perform this when the screensaver is started '''
        self.logoff = get_setting('logoff', 'false')
        self.mute = get_setting('mute', 'true')

        display_method = int(get_setting('display_method', 0))
        self.display = DISPLAY_METHODS[display_method]

        power_method = int(get_setting('power_method', 0))
        self.power = POWER_METHODS[power_method]

        log(3, 'display_method={display}, power_method={power}, logoff={logoff}, mute={mute}',
            display=self.display.get('name'), power=self.power.get('name'), logoff=self.logoff, mute=self.mute)

        # Turn off display
        if self.display.get('name') != 'do-nothing':
            log(1, "Turn display off using method '{name}'", **self.display)
        func(self.display.get('function'), *self.display.get('args_off'))

        # FIXME: Screensaver always seems to lock when started, requires unlock and re-login
        # Log off user
        if self.logoff == 'true':
            log(1, 'Log off user')
#            run_builtin('System.LogOff')
            activate_window('loginscreen')
#            run_builtin('ActivateWindow(loginscreen)')
#            run_builtin('ActivateWindowAndFocus(loginscreen,return)')

        # Mute audio
        if self.mute == 'true':
            log(1, 'Mute audio')
            set_mute(toggle=True)

        self.monitor = TurnOffMonitor(action=self.resume)
        self.monitor.waitForAbort(1)

        # Power off system
        if self.power.get('name') != 'do-nothing':
            log(1, "Turn system off using method '{name}'", **self.power)
        func(self.power.get('function'), **self.power.get('kwargs_off', {}))

    def resume(self):
        ''' Perform this when the Screensaver is stopped '''
        # Unmute audio
        if self.mute == 'true':
            log(1, 'Unmute audio')
            set_mute(toggle=False)

        # Turn on display
        if self.display.get('name') != 'do-nothing':
            log(1, "Turn display back on using method '{name}'", **self.display)
        func(self.display.get('function'), *self.display.get('args_on'))

        # Clean up everything
        self.exit()

    def exit(self):
        ''' Clean up function '''
        self.monitor = None
        self.close()


class TurnOffMonitor(Monitor, object):
    ''' This is the monitor to exit TurnOffScreensaver '''

    def __init__(self, **kwargs):  # pylint: disable=super-init-not-called
        ''' Initialize monitor '''
        self.action = kwargs.get('action')

    def onScreensaverDeactivated(self):  # pylint: disable=invalid-name
        ''' Perform cleanup function '''
        self.action()


def run():
    ''' Runs the screensaver '''
    from xbmc import getCondVisibility

    # If player has media, avoid running
    if getCondVisibility("Player.HasMedia"):
        log(1, 'Screensaver not started because player has media.')
        return

    TurnOffDialog('gui.xml', addon_path(), 'default').doModal()
