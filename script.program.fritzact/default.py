#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
Documentation for the login procedure
http://www.avm.de/de/Extern/files/session_id/AVM_Technical_Note_-_Session_ID.pdf

Smart Home interface:
https://avm.de/fileadmin/user_upload/Global/Service/Schnittstellen/AHA-HTTP-Interface.pdf
'''

import hashlib
import os
import requests
import resources.lib.tools as t
import resources.lib.slider as Slider

import sys
from time import time
import urllib
import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin
from xml.etree import ElementTree as ET
import re

__addon__ = xbmcaddon.Addon()
__addonID__ = __addon__.getAddonInfo('id')
__addonname__ = __addon__.getAddonInfo('name')
__version__ = __addon__.getAddonInfo('version')
__path__ = __addon__.getAddonInfo('path')
__LS__ = __addon__.getLocalizedString

__s_on__ = xbmc.translatePath(os.path.join(__path__, 'resources', 'lib', 'media', 'dect_on.png'))
__s_off__ = xbmc.translatePath(os.path.join(__path__, 'resources', 'lib', 'media', 'dect_off.png'))
__s_absent__ = xbmc.translatePath(os.path.join(__path__, 'resources', 'lib', 'media', 'dect_absent.png'))
__t_on__ = xbmc.translatePath(os.path.join(__path__, 'resources', 'lib', 'media', 'comet_on.png'))
__t_absent__ = xbmc.translatePath(os.path.join(__path__, 'resources', 'lib', 'media', 'comet_absent.png'))
__gs_on__ = xbmc.translatePath(os.path.join(__path__, 'resources', 'lib', 'media', 'dect_group_on.png'))
__gs_off__ = xbmc.translatePath(os.path.join(__path__, 'resources', 'lib', 'media', 'dect_group_off.png'))
__gt_on__ = xbmc.translatePath(os.path.join(__path__, 'resources', 'lib', 'media', 'comet_group_on.png'))
__gt_absent__ = xbmc.translatePath(os.path.join(__path__, 'resources', 'lib', 'media', 'comet_group_absent.png'))

class Device():

    def __init__(self, device):

        # Device attributes

        self.actor_id = device.attrib['identifier']
        self.device_id = device.attrib['id']
        self.fwversion = device.attrib['fwversion']
        self.productname = device.attrib['productname']
        self.manufacturer = device.attrib['manufacturer']
        self.functionbitmask = int(device.attrib['functionbitmask'])

        self.name = device.find('name').text
        self.present = int(device.find('present').text or '0')
        self.b_present = 'true' if self.present == 1 else 'false'

        self.is_thermostat = self.functionbitmask & (1 << 6) > 0        # Comet DECT (Radiator Thermostat)
        self.has_powermeter = self.functionbitmask & (1 << 7) > 0       # Energy Sensor
        self.has_temperature = self.functionbitmask & (1 << 8) > 0      # Temperature Sensor
        self.is_switch = self.functionbitmask & (1 << 9) > 0            # Power Switch
        self.is_repeater = self.functionbitmask & (1 << 10) > 0         # DECT Repeater

        self.state = 'n/a'
        self.b_state = 'n/a'
        self.power = 'n/a'
        self.energy = 'n/a'
        self.temperature = 'n/a'
        self.mode = 'n/a'
        self.lock = 'n/a'

        self.set_temp = ['n/a']
        self.comf_temp = ['n/a']
        self.lowering_temp = ['n/a']
        self.bin_slider = 0

        # Switch attributes

        if self.is_switch:
            self.type = 'switch'
            self.state = int(device.find('switch').find('state').text or '0')
            self.b_state = 'true' if self.state == 1 else 'false'
            self.mode = device.find('switch').find('mode').text
            self.lock = int(device.find('switch').find('lock').text or '0')

        if self.is_thermostat:
            self.type = 'thermostat'
            self.set_temp = self.bin2degree(int(device.find('hkr').find('tsoll').text or '0'))
            self.comf_temp = self.bin2degree(int(device.find('hkr').find('komfort').text or '0'))
            self.lowering_temp = self.bin2degree(int(device.find('hkr').find('absenk').text or '0'))

            # get temp for slider value

            self.bin_slider = int(device.find('hkr').find('tsoll').text or '0')

        # Power attributes

        try:
            if self.has_powermeter:
                self.power = '{:0.2f}'.format(float(device.find('powermeter').find('power').text)/1000) + ' W'
                self.energy = '{:0.2f}'.format(float(device.find('powermeter').find('energy').text)/1000) + ' kWh'
        except TypeError:
            pass

        # Temperature attributes

        try:
            if self.has_temperature:
                self.temperature = '{:0.1f}'.format(float(device.find("temperature").find("celsius").text)/10) + ' °C'.decode('utf-8')
        except TypeError:
            pass

        _group = re.match('([A-F]|\d){2}:([A-F]|\d){2}:([A-F]|\d){2}-([A-F]|\d){3}', self.actor_id)
        if _group is not None:
            self.type = 'group'

            # ToDo: change back to group ^^

            '''
            self.type = 'thermostat'
            self.temperature = '22.0' + ' °C'.decode('utf-8')
            self.bin_slider = 44
            self.set_temp = self.bin2degree(self.bin_slider)
            '''

        if self.is_repeater:
            self.type = 'switch'

    @classmethod

    def bin2degree(cls, binary_value = 0):
        if 16 <= binary_value <= 56: return '{:0.1f}'.format((binary_value - 16)/2.0 + 8) + ' °C'.decode('utf-8')
        elif binary_value == 253: return ['off']
        elif binary_value == 254: return ['on']
        return ['invalid']


class FritzBox():

    def __init__(self):
        self.getSettings()
        self.base_url = self.__fbtls + self.__fbserver

        self.session = requests.Session()

        if self.__fbSID is None or (int(time()) - self.__lastLogin > 600):

            t.writeLog('SID is none/last login more than 10 minutes ago, try to login')
            sid = None

            try:
                response = self.session.get(self.base_url + '/login_sid.lua', verify=False)
                xml = ET.fromstring(response.text)
                if xml.find('SID').text == "0000000000000000":
                    challenge = xml.find('Challenge').text
                    url = self.base_url + '/login_sid.lua'
                    response = self.session.get(url, params={
                        "username": self.__fbuser,
                        "response": self.calculate_response(challenge, self.__fbpasswd),
                    }, verify=False)
                    xml = ET.fromstring(response.text)
                    if xml.find('SID').text == "0000000000000000":
                        blocktime = int(xml.find('BlockTime').text)
                        t.writeLog("Login failed, please wait %s seconds" % (blocktime), xbmc.LOGERROR)
                        t.notifyOSD(__addonname__, __LS__(30012) % (blocktime))
                    else:
                        sid = xml.find('SID').text

            except (requests.exceptions.ConnectionError, TypeError):
                t.writeLog('FritzBox unreachable', level=xbmc.LOGERROR)
                t.notifyOSD(__addonname__, __LS__(30010))

            self.__fbSID = sid
            self.__lastLogin = int(time())
            __addon__.setSetting('SID', self.__fbSID)
            __addon__.setSetting('lastLogin', str(self.__lastLogin))

    @classmethod

    def calculate_response(cls, challenge, password):

        # Calculate response for the challenge-response authentication

        to_hash = (challenge + "-" + password).encode("UTF-16LE")
        hashed = hashlib.md5(to_hash).hexdigest()
        return '%s-%s' % (challenge, hashed)

    def getSettings(self):
        self.__fbserver = __addon__.getSetting('fbServer')
        self.__fbuser = __addon__.getSetting('fbUsername')
        self.__fbpasswd = t.crypt('fbPasswd', 'fb_key', 'fb_token')
        self.__fbtls = 'https://' if __addon__.getSetting('fbTLS').upper() == 'TRUE' else 'http://'
        self.__prefAIN = __addon__.getSetting('preferredAIN')
        self.__readonlyAIN = __addon__.getSetting('readonlyAIN').split(',')
        #
        self.__lastLogin = int(__addon__.getSetting('lastLogin') or 0)
        self.__fbSID = __addon__.getSetting('SID') or None

    def get_actors(self, handle=None, devtype=None):

        # Returns a list of Actor objects for querying SmartHome devices.

        actors = []
        devices = None

        _devicelist = self.switch('getdevicelistinfos')
        if _devicelist is not None:

            devices = ET.fromstring(_devicelist)

            for device in devices:

                actor = Device(device)

                if devtype is not None and devtype != actor.type: continue

                if actor.is_switch:
                    actor.icon = __s_absent__
                    if actor.present == 1:
                        actor.icon = __gs_on__ if actor.type == 'group' else __s_on__
                        if actor.state == 0: actor.icon = __gs_off__ if actor.type == 'group' else __s_off__
                elif actor.is_thermostat:
                    actor.icon = __t_absent__
                    if actor.present == 1:
                        actor.icon = __gt_on__ if actor.type == 'group' else __t_on__
                        if actor.state == 0: actor.icon = __gt_absent__ if actor.type == 'group' else __t_absent__

                actors.append(actor)

                if handle is not None:
                    wid = xbmcgui.ListItem(label=actor.name, label2=actor.actor_id, iconImage=actor.icon)
                    wid.setProperty('type', actor.type)
                    wid.setProperty('present', __LS__(30032 + actor.present))
                    wid.setProperty('b_present', actor.b_present)
                    if isinstance(actor.state, int):
                        wid.setProperty('state', __LS__(30030 + actor.state))
                    else:
                        wid.setProperty('state', actor.state)
                    wid.setProperty('b_state', actor.b_state)
                    wid.setProperty('mode', actor.mode)
                    wid.setProperty('temperature', unicode(actor.temperature))
                    wid.setProperty('power', actor.power)
                    wid.setProperty('energy', actor.energy)

                    wid.setProperty('set_temp', unicode(actor.set_temp))
                    wid.setProperty('comf_temp', unicode(actor.comf_temp))
                    wid.setProperty('lowering_temp', unicode(actor.lowering_temp))

                    xbmcplugin.addDirectoryItem(handle=handle, url='', listitem=wid)

                t.writeLog('<<<<', xbmc.LOGDEBUG)
                t.writeLog('----- current state of AIN %s -----' % (actor.actor_id), level=xbmc.LOGDEBUG)
                t.writeLog('Name:          %s' % (actor.name), level=xbmc.LOGDEBUG)
                t.writeLog('Type:          %s' % (actor.type), level=xbmc.LOGDEBUG)
                t.writeLog('Presence:      %s' % (actor.present), level=xbmc.LOGDEBUG)
                t.writeLog('Device ID:     %s' % (actor.device_id), level=xbmc.LOGDEBUG)
                t.writeLog('Temperature:   %s' % (actor.temperature), level=xbmc.LOGDEBUG)
                t.writeLog('State:         %s' % (actor.state), level=xbmc.LOGDEBUG)
                t.writeLog('Icon:          %s' % (actor.icon), level=xbmc.LOGDEBUG)
                t.writeLog('Power:         %s' % (actor.power), level=xbmc.LOGDEBUG)
                t.writeLog('Consumption:   %s' % (actor.energy), level=xbmc.LOGDEBUG)
                t.writeLog('soll Temp.:    %s' % (actor.set_temp), level=xbmc.LOGDEBUG)
                t.writeLog('comfort Temp.: %s' % (actor.comf_temp), level=xbmc.LOGDEBUG)
                t.writeLog('lower Temp.:   %s' % (actor.lowering_temp), level=xbmc.LOGDEBUG)
                t.writeLog('>>>>', xbmc.LOGDEBUG)

            if handle is not None:
                xbmcplugin.endOfDirectory(handle=handle, updateListing=True)
            xbmc.executebuiltin('Container.Refresh')

        else:
            t.writeLog('no device list available', xbmc.LOGDEBUG)
        return actors

    def switch(self, cmd, ain=None, param=None, label=None):

        t.writeLog('Provided command: %s' % (cmd), level=xbmc.LOGDEBUG)
        t.writeLog('Provided ain:     %s' % (ain), level=xbmc.LOGDEBUG)
        t.writeLog('Provided param:   %s' % (param), level=xbmc.LOGDEBUG)
        t.writeLog('Provided device:  %s' % (label), level=xbmc.LOGDEBUG)

        # Call an actor method

        if self.__fbSID is None:
            t.writeLog('Not logged in or no connection to FritzBox', level=xbmc.LOGERROR)
            return

        params = {
            'switchcmd': cmd,
            'sid': self.__fbSID,
        }
        if ain:

            # check if readonly AIN

            for li in self.__readonlyAIN:
                if ain == li.strip():
                    xbmcgui.Dialog().notification(__addonname__, __LS__(30013), xbmcgui.NOTIFICATION_WARNING, 3000)
                    return

            params['ain'] = ain

        if cmd == 'sethkrtsoll':
            slider = Slider.SliderWindow.createSliderWindow()
            slider.label = __LS__(30035) % (label)
            slider.initValue = (param - 16) * 100 / 40
            slider.doModal()
            slider.close()

            _sliderBin = int(slider.retValue) * 2

            t.writeLog('Thermostat binary before/now: %s/%s' % (param, _sliderBin), level=xbmc.LOGDEBUG)
            del slider

            if param == _sliderBin: return
            else:
                t.writeLog('set thermostat %s to %s' % (ain, _sliderBin), level=xbmc.LOGDEBUG)
                param = str(_sliderBin)

            if param: params['param'] = param

        try:
            response = self.session.get(self.base_url + '/webservices/homeautoswitch.lua', params=params, verify=False)
            response.raise_for_status()
        except (requests.exceptions.HTTPError, TypeError):
            t.writeLog('Bad request, action could not performed', level=xbmc.LOGERROR)
            xbmcgui.Dialog().notification(__addonname__, __LS__(30014), xbmcgui.NOTIFICATION_ERROR, 3000)
            return None

        return response.text.strip()

# _______________________________
#
#           M A I N
# _______________________________

action = None
ain = None
dev_type = None

_addonHandle = None

fritz = FritzBox()

arguments = sys.argv

if len(arguments) > 1:
    if arguments[0][0:6] == 'plugin':
        _addonHandle = int(arguments[1])
        arguments.pop(0)
        arguments[1] = arguments[1][1:]
        t.writeLog('Refreshing dynamic list content with plugin handle #%s' % (_addonHandle), level=xbmc.LOGDEBUG)

    params = t.paramsToDict(arguments[1])
    action = urllib.unquote_plus(params.get('action', ''))
    ain = urllib.unquote_plus(params.get('ain', ''))
    dev_type = urllib.unquote_plus(params.get('type', ''))

    if dev_type not in ['switch', 'thermostat', 'repeater', 'group']: dev_type = None

    t.writeLog('Parameter hash: %s' % (arguments[1:]), level=xbmc.LOGDEBUG)

actors = fritz.get_actors(handle=_addonHandle, devtype=dev_type)

if _addonHandle is None:

    name = None
    param = None
    cmd = None

    if action == 'toggle':
        cmd = 'setswitchtoggle'

    elif action == 'on':
        cmd = 'setswitchon'

    elif action == 'off':
        cmd = 'setswitchoff'

    elif action == 'temp':
        for device in actors:
            if device.actor_id == ain:
                cmd = 'sethkrtsoll'
                ain = ain
                name = device.name
                param = device.bin_slider
                break

    elif action == 'setpreferredain':
        _devlist = [__LS__(30006)]
        _ainlist = ['']
        for device in actors:
            if device.type == 'switch':
                _devlist.append(device.name)
                _ainlist.append(device.actor_id)
        if len(_devlist) > 0:
            dialog = xbmcgui.Dialog()
            _idx = dialog.select(__LS__(30020), _devlist)
            if _idx > -1:
                __addon__.setSetting('preferredAIN', _ainlist[_idx])

    elif action == 'setreadonlyain':
        _devlist = [__LS__(30006)]
        _ainlist = ['']
        for device in actors:
            _devlist.append(device.name)
            _ainlist.append(device.actor_id)
        if len(_devlist) > 0:
            dialog = xbmcgui.Dialog()
            _idx = dialog.multiselect(__LS__(30020), _devlist)
            if _idx is not None:
                __addon__.setSetting('readonlyAIN', ', '.join([_ainlist[i] for i in _idx]))
    else:
        cmd = 'setswitchtoggle'
        if __addon__.getSetting('preferredAIN') != '':
            ain =  __addon__.getSetting('preferredAIN')
        else:
            if len(actors) == 1 and actors[0].is_switch:
                ain = actors[0].actor_id
            else:
                _devlist = []
                _ainlist = []
                for device in actors:
                    '''
                    if device.is_switch:
                        _alternate_state = __LS__(30031) if device.b_state == 'false' else __LS__(30030)
                        _devlist.append('%s: %s' % (device.name, _alternate_state))
                    elif device.is_thermostat:
                        _devlist.append('%s: %s' % (device.name, device.temperature))
                    '''
                    if device.is_switch:
                        L2 = __LS__(30041) if device.b_state == 'false' else __LS__(30040)
                    elif device.is_thermostat:
                        L2 = device.temperature
                    liz = xbmcgui.ListItem(label=device.name, label2=L2, iconImage=device.icon)
                    liz.setProperty('ain', device.actor_id)
                    _devlist.append(liz)
                    _ainlist.append(device)

                if len(_devlist) > 0:
                    dialog = xbmcgui.Dialog()
                    _idx = dialog.select(__LS__(30020), _devlist, useDetails=True)
                    if _idx > -1:
                        device = _ainlist[_idx]
                        ain = device.actor_id

                        if device.is_thermostat:
                            cmd = 'sethkrtsoll'
                            name = device.name
                            param = device.bin_slider
    if cmd is not None:
        fritz.switch(cmd, ain=ain, param=param, label=name)
        t.writeLog('Last command on device %s was: %s' % (ain, cmd), xbmc.LOGDEBUG)
        ts = int(time())
        tsp = int(xbmcgui.Window(10000).getProperty('fritzact.timestamp') or '0')
        if ts - tsp > 5:
            t.writeLog('Set timestamp: %s' % (str(ts)), xbmc.LOGDEBUG)
            xbmcgui.Window(10000).setProperty('fritzact.timestamp', str(ts))
