#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at: http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# Original speedtest-cli DEV by Matt Martz (https://github.com/sivel/speedtest-cli)

from __future__ import absolute_import, division, unicode_literals

import os.path
import sys
import math
import platform
import socket
import threading
import timeit

try:  # Python 3
    from xml.etree import ElementTree
except ImportError:
    try:  # Python 2
        from xml.etree import cElementTree as ElementTree
    except ImportError:
        from xml.dom import minidom

try:  # Python 3
    from hashlib import md5
except ImportError:  # Python 2
    from md5 import md5

try:  # Python 3
    from queue import Queue
except ImportError:  # Python 2
    from Queue import Queue

try:  # Python 3
    from http.client import HTTPConnection, HTTPSConnection
    from urllib.parse import parse_qs, urlparse
    from urllib.request import urlopen, Request, HTTPError, URLError
except ImportError:
    try:  # Python 2.6 and newer
        from httplib import HTTPConnection, HTTPSConnection
        from urllib2 import urlopen, Request, HTTPError, URLError
        from urlparse import parse_qs, urlparse
    except ImportError:  # Python 2.5 and older
        # pylint: disable=ungrouped-imports
        from cgi import parse_qs  # pylint: disable=deprecated-method
        from httplib import HTTPConnection, HTTPSConnection
        from urllib.parse import urlparse
        from urllib2 import urlopen, Request, HTTPError, URLError

from xbmc import Monitor
from xbmcgui import ControlButton, ControlImage, ControlLabel, ControlTextBox, WindowXMLDialog

try:  # Kodi v19 or newer
    from xbmcvfs import translatePath
except ImportError:  # Kodi v18 and older
    # pylint: disable=ungrouped-imports
    from xbmc import translatePath

from kodiutils import addon_path, localize, log


IMAGE_RESULT = None
SOURCE = None
SHUTDOWN_EVENT = None
SOCKET_SOCKET = socket.socket
USER_AGENT = 'Mozilla/5.0 ({system}; U; {arch}; en-us) Python/{version} (KHTML, like Gecko)'.format(
    system=platform.system(),
    arch=platform.architecture()[0],
    version=platform.python_version(),
)


class SpeedtestCliServerListError(Exception):
    """ Stub exception """


def bound_socket(*args, **kwargs):
    global SOURCE  # pylint: disable=global-statement
    sock = SOCKET_SOCKET(*args, **kwargs)
    sock.bind((SOURCE, 0))
    return sock


def distance(origin, destination):
    (lat1, lon1) = origin
    (lat2, lon2) = destination
    radius = 6371  # km

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    aaa = math.sin(dlat / 2) * math.sin(dlat / 2) \
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) \
        * math.sin(dlon / 2) * math.sin(dlon / 2)
    ccc = 2 * math.atan2(math.sqrt(aaa), math.sqrt(1 - aaa))
    return radius * ccc


def build_request(url, data=None, headers=None):
    if headers is None:
        headers = dict()
    headers['User-Agent'] = USER_AGENT
    return Request(url, data=data, headers=headers)


def catch_request(request):
    try:
        return urlopen(request)
    except (HTTPError, URLError, socket.error):
        exc = sys.exc_info()[1]
        return (None, exc)


class FileGetter(threading.Thread):
    def __init__(self, url, start):
        self.url = url
        self.result = None
        self.starttime = start
        threading.Thread.__init__(self)

    def run(self):
        self.result = [0]
        try:
            if timeit.default_timer() - self.starttime <= 10:
                request = build_request(self.url)
                handler = urlopen(request)
                while not SHUTDOWN_EVENT.isSet():
                    self.result.append(len(handler.read(10240)))
                    if not self.result[-1]:
                        break
                handler.close()
        except IOError:
            pass


class FilePutter(threading.Thread):
    def __init__(self, url, start, size):
        self.url = url
        chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        data = chars * int(round(int(size) / 36.0))
        self.data = ('content1=%s' % data[0:int(size) - 9]).encode()
        del data
        self.result = None
        self.starttime = start
        threading.Thread.__init__(self)

    def run(self):
        try:
            if timeit.default_timer() - self.starttime <= 10 and not SHUTDOWN_EVENT.isSet():
                request = build_request(self.url, data=self.data)
                handler = urlopen(request)
                handler.read(11)
                handler.close()
                self.result = len(self.data)
            else:
                self.result = 0
        except IOError:
            self.result = 0


def get_attributes_by_tag_name(dom, tag_name):
    elem = dom.getElementsByTagName(tag_name)[0]
    return dict(list(elem.attributes.items()))


def get_config():
    request = build_request('http://www.speedtest.net/speedtest-config.php')
    handler = catch_request(request)
    if handler is False:
        log(0, 'Could not retrieve speedtest.net configuration')
        sys.exit(1)
    configxml = []
    while True:
        configxml.append(handler.read(10240))
        if not configxml[-1]:
            break
    if int(handler.code) != 200:
        return None
    handler.close()
    if 'minidom' in sys.modules:
        try:
            root = minidom.parseString(''.join(configxml))
        except SyntaxError as exc:
            log(0, 'CONFIG XML:\n{config}', config=''.join(configxml))
            log(0, 'Failed to parse speedtest.net configuration: {error}', error=exc)
            raise
        config = dict(
            client=get_attributes_by_tag_name(root, 'client'),
            times=get_attributes_by_tag_name(root, 'times'),
            download=get_attributes_by_tag_name(root, 'download'),
            upload=get_attributes_by_tag_name(root, 'upload'),
        )
    else:
        try:
            root = ElementTree.fromstring(''.encode().join(configxml))
        except SyntaxError as exc:
            log(0, 'CONFIG XML:\n{config}', config=''.encode().join(configxml))
            log(0, 'Failed to parse speedtest.net configuration: {error}', error=exc)
            raise
        config = dict(
            client=root.find('client').attrib,
            times=root.find('times').attrib,
            download=root.find('download').attrib,
            upload=root.find('upload').attrib,
        )
    del root
    del configxml
    return config


def closest_servers(client, total=False):

    urls = [
        'https://www.speedtest.net/speedtest-servers-static.php',
        'http://c.speedtest.net/speedtest-servers-static.php',
    ]
    errors = []
    servers = {}
    for url in urls:
        try:
            request = build_request(url)
            handler = catch_request(request)
            if handler is False:
                # errors.append('%s' % e)
                raise SpeedtestCliServerListError
            serversxml = []
            while not Monitor().abortRequested():
                serversxml.append(handler.read(10240))
                if not serversxml[-1]:
                    break
            if int(handler.code) != 200:
                handler.close()
                raise SpeedtestCliServerListError
            handler.close()
            try:
                if 'minidom' in sys.modules:
                    root = minidom.parseString(''.join(serversxml))
                    elements = root.getElementsByTagName('server')
                else:
                    root = ElementTree.fromstring(''.encode().join(serversxml))
                    elements = root.iter(tag='server')
            except SyntaxError:
                raise SpeedtestCliServerListError  # pylint: disable=raise-missing-from
            for server in elements:
                try:
                    attrib = server.attrib
                except AttributeError:
                    attrib = dict(list(server.attributes.items()))
                ddd = distance([float(client['lat']), float(client['lon'])], [float(attrib.get('lat')), float(attrib.get('lon'))])
                attrib['d'] = ddd
                if ddd not in servers:
                    servers[ddd] = [attrib]
                else:
                    servers[ddd].append(attrib)
            del root
            del serversxml
            del elements
        except SpeedtestCliServerListError:
            continue
        if servers:
            break
    if not servers:
        log(0, 'Failed to retrieve list of speedtest.net servers: {errors}', errors='\n'.join(errors))
        sys.exit(1)
    closest = []
    for ddd in sorted(servers.keys()):
        for sss in servers[ddd]:
            closest.append(sss)
            if len(closest) == 5 and not total:
                break
        else:
            continue
        break
    del servers
    return closest


def get_best_server(servers):
    results = {}
    for server in servers:
        cum = []
        url = '%s/latency.txt' % os.path.dirname(server['url'])
        urlparts = urlparse(url)
        for _ in range(0, 3):
            try:
                if urlparts[0] == 'https':
                    handler = HTTPSConnection(urlparts[1])
                else:
                    handler = HTTPConnection(urlparts[1])
                headers = {'User-Agent': USER_AGENT}
                start = timeit.default_timer()
                handler.request('GET', urlparts[2], headers=headers)
                response = handler.getresponse()
                total = timeit.default_timer() - start
            except (HTTPError, URLError, socket.error):
                cum.append(3600)
                continue
            text = response.read(9)
            if int(response.status) == 200 and text == 'test=test'.encode():
                cum.append(total)
            else:
                cum.append(3600)
            handler.close()
        avg = round(sum(cum) / 6 * 1000, 3)
        results[avg] = server
    fastest = sorted(results.keys())[0]
    best = results[fastest]
    best['latency'] = fastest
    return best


class Animation(WindowXMLDialog):
    def __init__(self, xmlFilename, scriptPath, defaultSkin='Default', defaultRes='720p'):  # pylint: disable=unused-argument
        super(Animation, self).__init__(xmlFilename, scriptPath, defaultSkin, defaultRes)
        self.doModal()


class SpeedTest(Animation):
    def __init__(self, xmlFilename, scriptPath, defaultSkin='Default', defaultRes='720p'):
        self.button_close = None
        self.button_close_glow = None
        self.button_close_id = None
        self.button_run = None
        self.button_run_glow = None
        self.button_run_id = None
        self.dl_textbox = None
        self.dlul_prog_textbox = None
        self.image_dir = translatePath(os.path.join(addon_path(), 'resources', 'skins', 'Default', 'media'))
        self.image_background = None
        self.image_shadow = None
        self.image_progress = None
        self.image_ping = None
        self.image_ping_glow = None
        self.image_gauge = None
        self.image_gauge_arrow = None
        self.image_button_run = None
        self.image_button_run_glow = None
        self.image_speedtestresults = None
        self.image_centertext_testingping = None
        self.image_result = None
        self.img_centertext = None
        self.img_final_results = None
        self.img_gauge = None
        self.img_gauge_arrow = None
        self.img_ping = None
        self.img_ping_glow = None
        self.img_progress = None
        self.img_results = None
        self.ping_textbox = None
        self.please_wait_textbox = None
        self.rec_speed = None
        self.screenx = 1920
        self.screeny = 1080
        self.textbox = None
        self.ul_textbox = None

        if sys.version_info.major == 2:
            WindowXMLDialog.__init__(self, xmlFilename, scriptPath, defaultSkin, defaultRes)  # pylint: disable=non-parent-init-called
            self.doModal()
        elif sys.version_info.major == 3:
            super().__init__(xmlFilename, scriptPath, defaultSkin, defaultRes)  # pylint: disable=missing-super-argument

    def onInit(self):  # pylint: disable=invalid-name
        self.screenx = 1920
        self.screeny = 1080

        self.image_background = os.path.join(self.image_dir, 'bg_screen.jpg')
        self.image_shadow = os.path.join(self.image_dir, 'shadowframe.png')
        self.image_progress = os.path.join(self.image_dir, 'ajax-loader-bar.gif')
        self.image_ping = os.path.join(self.image_dir, 'ping_progress_bg.png')
        self.image_ping_glow = os.path.join(self.image_dir, 'ping_progress_glow.png')
        self.image_gauge = os.path.join(self.image_dir, 'gauge_bg.png')
        self.image_gauge_arrow = os.path.join(self.image_dir, 'gauge_ic_arrow.png')
        self.image_button_run = os.path.join(self.image_dir, 'btn_start_bg.png')
        self.image_button_run_glow = os.path.join(self.image_dir, 'btn_start_glow_active.png')
        self.image_speedtestresults = os.path.join(self.image_dir, 'speedtest_results_wtext.png')
        self.image_centertext_testingping = os.path.join(self.image_dir, 'testing_ping.png')
        self.image_result = self.image_speedtestresults
        self.textbox = ControlTextBox(50, 50, 880, 500, textColor='0xFFFFFFFF')
        self.addControl(self.textbox)
        self.display_button_run()
        self.display_button_close()
        self.setFocus(self.button_run)

    def onAction(self, action):  # pylint: disable=invalid-name
        if action in (10, 92):
            self.save_close()

    def display_button_run(self, function='true'):
        if function == 'true':
            button_run_glowx = int((self.screenx / 3) - (300 / 2))
            button_run_glowy = int((self.screeny / 3) - (122 / 2) + 50)

            self.button_run_glow = ControlImage(button_run_glowx, button_run_glowy, 300, 122, '', aspectRatio=0)
            self.addControl(self.button_run_glow)
            self.button_run_glow.setVisible(False)
            self.button_run_glow.setImage(self.image_button_run_glow)
            self.button_run_glow.setAnimations([
                ('conditional', 'effect=fade start=0 time=1000 condition=true pulse=true')
            ])

            self.button_run = ControlButton(button_run_glowx, button_run_glowy, 300, 122, localize(30950),
                                            focusTexture=self.image_button_run, noFocusTexture=self.image_button_run,
                                            alignment=2 | 4, textColor='0xFF000000', focusedColor='0xFF000000',
                                            shadowColor='0xFFCCCCCC', disabledColor='0xFF000000')

            self.addControl(self.button_run)
            self.setFocus(self.button_run)
            self.button_run.setVisible(False)
            self.button_run.setAnimations([(
                'conditional',
                'effect=fade start=100 end=0 time=300 condition=!Control.IsEnabled(%d)' % self.button_run.getId()
            )])
            self.button_run_id = self.button_run.getId()
            self.button_run.setEnabled(True)
            self.button_run.setVisible(True)
            self.button_run_glow.setEnabled(True)
            self.button_run_glow.setVisible(True)
        else:
            self.button_run.setEnabled(False)
            self.button_run.setVisible(False)
            self.button_run_glow.setEnabled(False)
            self.button_run_glow.setVisible(False)

    def display_button_close(self, function='true'):
        if function == 'true':
            self.button_close_glow = ControlImage(880, 418, 300, 122, '', aspectRatio=0)
            self.addControl(self.button_close_glow)
            self.button_close_glow.setVisible(False)
            self.button_close_glow.setImage(self.image_button_run_glow)
            self.button_close_glow.setAnimations([(
                'conditional',
                'effect=fade start=0 time=1000 delay=2000 pulse=true condition=Control.IsVisible(%d)' % self.button_close_glow.getId()
            )])

            self.button_close = ControlButton(99999, 99999, 300, 122, localize(30951),
                                              focusTexture=self.image_button_run, noFocusTexture=self.image_button_run,
                                              alignment=2 | 4, textColor='0xFF000000', focusedColor='0xFF000000',
                                              shadowColor='0xFFCCCCCC', disabledColor='0xFF000000')

            self.addControl(self.button_close)
            self.button_close.setVisible(False)
            self.button_close.setPosition(880, 418)
            self.button_close_id = self.button_close.getId()
            self.button_close.setAnimations([(
                'conditional',
                'effect=fade start=0 end=100 delay=1000 time=1000 condition=Control.IsVisible(%d)' % self.button_close.getId()
            )])
        elif function == 'visible':
            self.button_close.setVisible(True)
            self.button_close_glow.setVisible(True)
            self.setFocus(self.button_close)
        else:
            self.button_close.setVisible(False)
            self.button_close_glow.setVisible(False)

    def display_ping_test(self, function='true'):
        if function == 'true':
            img_centertextx = int((self.screenx / 3) - (320 / 2))
            img_centertexty = int((self.screeny / 3) - (130 / 2) + 50)
            self.img_centertext = ControlImage(img_centertextx, img_centertexty, 320, 130, ' ', aspectRatio=0)
            self.addControl(self.img_centertext)

            img_pingx = int((self.screenx / 3) - (600 / 2))
            img_pingy = int((self.screeny / 3) - (400 / 2))
            self.img_ping = ControlImage(img_pingx, img_pingy, 600, 400, '', aspectRatio=1)
            self.img_ping_glow = ControlImage(img_pingx, img_pingy, 600, 400, '', aspectRatio=1)
            self.addControl(self.img_ping)
            self.addControl(self.img_ping_glow)
            self.img_ping.setVisible(False)
            self.img_ping_glow.setVisible(False)
            self.img_ping.setImage(self.image_ping)
            self.img_ping_glow.setImage(self.image_ping_glow)
            self.img_ping.setAnimations([(
                'conditional',
                'effect=fade start=0 end=100 delay=1000 time=1000 condition=Control.IsVisible(%d)' % self.img_ping.getId()
            ), (
                'conditional',
                'effect=fade start=100 end=0 time=300 condition=!Control.IsEnabled(%d)' % self.img_ping.getId()
            )])
            self.img_ping_glow.setAnimations([(
                'conditional',
                'effect=fade start=0 time=1000 pulse=true condition=Control.IsEnabled(%d)' % self.img_ping_glow.getId()
            ), (
                'conditional',
                'effect=fade start=0 end=100 delay=1000 time=1000 condition=Control.IsVisible(%d)' % self.img_ping_glow.getId()
            ), (
                'conditional',
                'effect=fade start=100 end=0 time=300 condition=!Control.IsEnabled(%d)' % self.img_ping_glow.getId()
            )])
            self.img_centertext.setAnimations([(
                'conditional', 'effect=fade start=70 time=1000 condition=true pulse=true'
            )])
        elif function == 'visible':
            self.img_ping.setVisible(True)
            self.img_ping_glow.setVisible(True)
        else:
            self.img_ping.setVisible(False)
            self.img_ping_glow.setVisible(False)

            self.img_centertext.setVisible(False)

    def display_gauge_test(self, function='true'):
        if function == 'true':

            img_gaugex = int((self.screenx / 3) - (548 / 2))
            img_gaugey = int((self.screeny / 3) - (400 / 2))

            img_gauge_arrowx = int((self.screenx / 3) - (66 / 2) - 5)
            img_gauge_arrowy = int((self.screeny / 3) - (260 / 2) - 60)
            self.img_gauge = ControlImage(img_gaugex, img_gaugey, 548, 400, '', aspectRatio=0)
            self.img_gauge_arrow = ControlImage(img_gauge_arrowx, img_gauge_arrowy, 66, 260, '', aspectRatio=0)
            self.addControl(self.img_gauge)
            self.addControl(self.img_gauge_arrow)
            self.img_gauge.setVisible(False)
            self.img_gauge_arrow.setVisible(False)
            self.img_gauge.setImage(self.image_gauge)
            self.img_gauge_arrow.setImage(self.image_gauge_arrow)
            self.img_gauge.setAnimations([(
                'conditional',
                'effect=fade start=0 end=100 delay=1000 time=1000 condition=Control.IsVisible(%d)' % self.img_gauge.getId()
            ), (
                'conditional',
                'effect=fade start=100 end=0 time=300 condition=!Control.IsEnabled(%d)' % self.img_gauge.getId()
            )])
            self.img_gauge_arrow.setAnimations([(
                'conditional',
                'effect=fade start=0 end=100 time=1000 condition=Control.IsVisible(%d)' % self.img_gauge_arrow.getId()
            ), (
                'conditional',
                'effect=fade start=100 end=0 time=300 condition=!Control.IsEnabled(%d)' % self.img_gauge_arrow.getId()
            )])

            dlul_prog_textboxx = int((self.screenx / 3) - (200 / 2))
            dlul_prog_textboxy = int((self.screeny / 3) - (50 / 2) + 170)
            self.dlul_prog_textbox = ControlLabel(dlul_prog_textboxx, dlul_prog_textboxy, 200, 50, label='',
                                                  textColor='0xFFFFFFFF', font='font30', alignment=2 | 4)
            self.addControl(self.dlul_prog_textbox)
        elif function == 'visible':
            self.img_gauge.setEnabled(True)
            self.img_gauge.setVisible(True)
            self.img_gauge_arrow.setEnabled(True)
            self.img_gauge_arrow.setVisible(True)
        else:
            self.img_gauge.setEnabled(False)
            self.img_gauge.setVisible(False)
            self.img_gauge_arrow.setEnabled(False)
            self.img_gauge_arrow.setVisible(False)
            self.dlul_prog_textbox.setLabel('')

    def display_progress_bar(self, function='true'):
        if function == 'true':
            self.img_progress = ControlImage(340, 640, 600, 20, '', aspectRatio=0, colorDiffuse="0xFF00AACC")
            self.addControl(self.img_progress)
            self.img_progress.setVisible(False)
            self.img_progress.setImage(self.image_progress)
            self.img_progress.setAnimations([(
                'conditional',
                'effect=fade start=0 end=100 time=500 condition=Control.IsVisible(%d)' % self.img_progress.getId()
            ), (
                'conditional',
                'effect=fade start=100 end=0 time=300 condition=!Control.IsEnabled(%d)' % self.img_progress.getId()
            )])
            self.img_progress.setVisible(True)
            img_progressx = int((self.screenx / 3) - (200 / 2))
            img_progressy = int((self.screeny / 3) - (50 / 2) + 270)
            self.please_wait_textbox = ControlLabel(img_progressx, img_progressy, 200, 50, label=localize(30952),
                                                    textColor='0xFFFFFFFF', alignment=2 | 4)
            self.addControl(self.please_wait_textbox)
        elif function == 'visible':
            self.please_wait_textbox.setVisible(True)
            self.img_progress.setEnabled(True)
            self.img_progress.setVisible(True)
        else:
            self.please_wait_textbox.setVisible(False)
            self.img_progress.setEnabled(False)
            self.img_progress.setVisible(False)

    def display_results(self, function='true'):
        if function == 'true':
            self.img_results = ControlImage(932, 40, 320, 144, '', aspectRatio=0)
            self.addControl(self.img_results)
            self.img_results.setVisible(False)
            self.img_results.setImage(self.image_speedtestresults)
            self.img_results.setAnimations([(
                'conditional',
                'effect=fade start=100 end=0 time=300 delay=1000 condition=!Control.IsEnabled(%d)' % self.img_results.getId()
            )])
            self.img_results.setVisible(True)

            self.ping_textbox = ControlLabel(955, 133, 75, 50, label='', textColor='0xFFFFFFFF')
            self.addControl(self.ping_textbox)

            self.dl_textbox = ControlLabel(1035, 133, 75, 50, label='', textColor='0xFFFFFFFF')
            self.addControl(self.dl_textbox)

            self.ul_textbox = ControlLabel(1153, 133, 75, 50, label='', textColor='0xFFFFFFFF')
            self.addControl(self.ul_textbox)

        elif function == 'visible':
            self.img_results.setEnabled(True)
            self.img_results.setVisible(True)
        else:
            self.img_results.setEnabled(False)
            self.dl_textbox.setLabel('')
            self.ul_textbox.setLabel('')
            self.ping_textbox.setLabel('')

    def show_end_result(self):
        self.img_final_results = ControlImage(932, 40, 320, 144, '', aspectRatio=0)
        self.addControl(self.img_final_results)
        self.img_final_results.setVisible(False)
        self.img_final_results.setEnabled(False)

        self.img_final_results.setImage(IMAGE_RESULT)
        self.img_final_results.setAnimations([(
            'conditional',
            'effect=fade start=0 end=100 time=1000 delay=100 condition=Control.IsVisible(%d)' % self.img_final_results.getId()
        ), (
            'conditional',
            'effect=zoom end=175 start=100 center=%s time=2000 delay=3000 condition=Control.IsVisible(%d)' % ('auto', self.img_final_results.getId())
        ), (
            'conditional',
            'effect=slide end=-100,25 time=2000 delay=3000 tween=linear easing=in condition=Control.IsVisible(%d)' % self.img_final_results.getId()
        )])
        self.img_final_results.setVisible(True)
        self.img_final_results.setEnabled(True)

    def show_end_result_sp(self):
        self.rec_speed = ControlTextBox(325, 475, 600, 300, textColor='0xFFFFFFFF')
        self.addControl(self.rec_speed)
        self.rec_speed.setVisible(False)
        self.rec_speed.setEnabled(False)
        self.rec_speed.setText('\n'.join([localize(30980), localize(30981), localize(30982), localize(30983), localize(30984), localize(30985)]))
        self.rec_speed.setAnimations([(
            'conditional',
            'effect=fade start=0 end=100 time=1000 delay=100 condition=Control.IsVisible(%d)' % self.rec_speed.getId()
        )])
        self.rec_speed.setVisible(True)
        self.rec_speed.setEnabled(True)

    def onClick(self, control):  # pylint: disable=invalid-name
        if control == self.button_run_id:
            self.display_button_run(False)
            self.display_results()
            self.display_progress_bar()
            self.display_ping_test()
            self.display_gauge_test()
            self.speedtest(share=True, simple=True)
            self.display_progress_bar(False)
            self.display_ping_test(False)
            self.display_gauge_test(False)
            self.display_results(False)
            self.show_end_result()
            self.show_end_result_sp()
            self.display_button_close('visible')
        if control == self.button_close_id:
            self.save_close()

    def save_close(self):
        self.close()

    def update_textbox(self, text):
        self.textbox.setText("\n".join(text))

    def config_gauge(self, speed, last_speed=0, time=1000):
        if last_speed == 0:
            last_speed = 122
        current_s = 0
        if speed <= 1:
            current_s = 122 - float((float(speed) - float(0))) * float(
                (float(31) / float(1)))
        elif speed <= 2:
            current_s = 90 - float((float(speed) - float(1))) * float(
                (float(31) / float(1)))
        elif speed <= 3:
            current_s = 58 - float((float(speed) - float(2))) * float(
                (float(29) / float(1)))
        elif speed <= 5:
            current_s = 28 - float((float(speed) - float(3))) * float(
                (float(28) / float(2)))
        elif speed <= 10:
            current_s = float((float(speed) - float(5))) * float(
                (float(28) / float(5)))
        elif speed <= 20:
            current_s = 29 + float((float(speed) - float(10))) * float(
                (float(29) / float(10)))
        elif speed <= 30:
            current_s = 59 + float((float(speed) - float(20))) * float(
                (float(31) / float(10)))
        elif speed <= 50:
            current_s = 91 + float((float(speed) - float(30))) * float(
                (float(31) / float(20)))
        elif speed > 50:
            current_s = 122
        speed_n = "%.0f" % float(current_s)
        if speed > 5:
            speed_n = '-' + str(speed_n)

        img_gauge_arrowx = (self.screenx / 3) - (66 / 2) + 28
        img_gauge_arrowy = (self.screeny / 3) + (260 / 2) - 88
        self.img_gauge_arrow.setAnimations([(
            'conditional',
            'effect=rotate start=%d end=%d center=%d,%d condition=Control.IsVisible(%d) time=%d' % (
                int(last_speed), int(speed_n), img_gauge_arrowx, img_gauge_arrowy, self.img_gauge.getId(), time
            )
        )])
        return speed_n

    def download_speed(self, files, quiet=False):
        start = timeit.default_timer()

        def producer(queue, files):
            for filename in files:
                thread = FileGetter(filename, start)
                thread.start()
                queue.put(thread, True)

                if not quiet and not SHUTDOWN_EVENT.isSet():
                    sys.stdout.write('.')
                    sys.stdout.flush()

        finished = []

        def consumer(queue, total_files):
            speed_dl = 0
            while len(finished) < total_files:
                thread = queue.get(True)
                while thread.is_alive():
                    thread.join(timeout=0.1)
                finished.append(sum(thread.result))
                speed_f = ((sum(finished) / (timeit.default_timer() - start)) / 1000 / 1000) * 8
                speed_dl = self.config_gauge(speed_f, speed_dl)
                self.dlul_prog_textbox.setLabel('%.02f Mbps' % speed_f)
                del thread

        queue = Queue(6)
        prod_thread = threading.Thread(target=producer, args=(queue, files))
        cons_thread = threading.Thread(target=consumer, args=(queue, len(files)))
        start = timeit.default_timer()
        prod_thread.start()
        cons_thread.start()
        while prod_thread.is_alive():
            prod_thread.join(timeout=0.1)
        while cons_thread.is_alive():
            cons_thread.join(timeout=0.1)
        return sum(finished) / (timeit.default_timer() - start)

    def upload_speed(self, url, sizes, quiet=False):
        start = timeit.default_timer()

        def producer(queue, sizes):
            for size in sizes:
                thread = FilePutter(url, start, size)
                thread.start()
                queue.put(thread, True)
                if not quiet and not SHUTDOWN_EVENT.isSet():
                    sys.stdout.write('.')
                    sys.stdout.flush()
        finished = []

        def consumer(queue, total_sizes):
            speed_dl = 0
            while len(finished) < total_sizes:
                thread = queue.get(True)
                while thread.is_alive():
                    thread.join(timeout=0.1)
                finished.append(thread.result)
                speed_f = ((sum(finished) / (timeit.default_timer() - start)) / 1000 / 1000) * 8
                speed_dl = self.config_gauge(speed_f, speed_dl)
                self.dlul_prog_textbox.setLabel('%.02f Mbps' % speed_f)
                del thread

        queue = Queue(6)
        prod_thread = threading.Thread(target=producer, args=(queue, sizes))
        cons_thread = threading.Thread(target=consumer, args=(queue, len(sizes)))
        start = timeit.default_timer()
        prod_thread.start()
        cons_thread.start()
        while prod_thread.is_alive():
            prod_thread.join(timeout=0.1)
        while cons_thread.is_alive():
            cons_thread.join(timeout=0.1)
        return sum(finished) / (timeit.default_timer() - start)

    def speedtest(self, share=False, simple=False, src=None, timeout=10):
        self.img_ping.setVisible(True)
        self.img_ping_glow.setVisible(True)
        start_st = [localize(30960)]  # Running Speed Test add-on

        global SHUTDOWN_EVENT, SOURCE  # pylint: disable=global-statement
        SHUTDOWN_EVENT = threading.Event()

        socket.setdefaulttimeout(timeout)

        if src:
            SOURCE = src
            socket.socket = bound_socket

        start_st.append(localize(30961))  # Retrieving speedtest.net configuration
        self.update_textbox(start_st)
        try:
            config = get_config()
        except URLError:
            return False

        start_st.append(localize(30962))  # Retrieving speedtest.net server list
        self.update_textbox(start_st)
        self.img_centertext.setImage(self.image_centertext_testingping)

        servers = closest_servers(config['client'])

        start_st.append(localize(30963, **config['client']))  # Testing from ISP
        self.update_textbox(start_st)

        best = get_best_server(servers)

        start_st.append(localize(30964))  # Selecting best server based on latency
        start_st.append(localize(30965, **best))  # Hosted by: {sponsor}
        start_st.append(localize(30966, **best))  # 'Host server: {host}
        start_st.append(localize(30967, **best))  # City, State: {name}
        start_st.append(localize(30968, **best))  # Country: {country}
        self.update_textbox(start_st)

        # km2mi = 0.62
        # km = '%(d)0.2f ' % best
        # Distance = float(km)
        # miles = Distance * km2mi
        # start_st.append('Distance: %s mi' % miles)
        start_st.append(localize(30969, **best))  # Distance: {d}
        start_st.append(localize(30970, **best))  # Ping: {latency}
        self.update_textbox(start_st)
        self.ping_textbox.setLabel("%.0f" % float(best['latency']))

        self.img_centertext.setImage(' ')
        self.img_ping.setEnabled(False)
        self.img_ping_glow.setEnabled(False)

        sizes = [350, 500, 750, 1000, 1500, 2000, 2500, 3000, 3500, 4000]
        urls = []
        for size in sizes:
            for _ in range(0, 4):
                urls.append('%s/random%sx%s.jpg' % (os.path.dirname(best['url']), size, size))
        self.img_gauge.setVisible(True)
        Monitor().waitForAbort(1)
        self.config_gauge(0)
        self.img_gauge_arrow.setVisible(True)

        start_st.append(localize(30971))  # Testing download speed...
        self.update_textbox(start_st)
        dlspeed = self.download_speed(urls, simple)
        start_st[-1] = localize(30972, speed=dlspeed * 8 / 1000 / 1000)  # Download speed
        self.update_textbox(start_st)
        self.dl_textbox.setLabel('%0.2f' % float(dlspeed * 8 / 1000 / 1000))

        sizesizes = [int(.25 * 1000 * 1000), int(.5 * 1000 * 1000)]
        sizes = []
        for size in sizesizes:
            for _ in range(0, 25):
                sizes.append(size)

        start_st.append(localize(30973))  # Testing upload speed...
        self.update_textbox(start_st)
        ulspeed = self.upload_speed(best['url'], sizes, simple)
        start_st[-1] = localize(30974, speed=ulspeed * 8 / 1000 / 1000)  # Upload speed
        self.update_textbox(start_st)
        self.ul_textbox.setLabel('%.2f' % float(ulspeed * 8 / 1000 / 1000))
        self.config_gauge(0, ulspeed * 8 / 1000 / 1000, time=3000)
        Monitor().waitForAbort(2)

        if share:
            dlspeedk = int(round(dlspeed * 8 / 1000, 0))
            ping = int(round(best['latency'], 0))
            ulspeedk = int(round(ulspeed * 8 / 1000, 0))

            api_data = [
                'download=%s' % dlspeedk,
                'ping=%s' % ping,
                'upload=%s' % ulspeedk,
                'promo=',
                'startmode=%s' % 'pingselect',
                'recommendedserverid=%s' % best['id'],
                'accuracy=%s' % 1,
                'serverid=%s' % best['id'],
                'hash=%s' % md5(('%s-%s-%s-%s' % (ping, ulspeedk, dlspeedk, '297aae72')).encode()).hexdigest()]

            headers = {'Referer': 'https://c.speedtest.net/flash/speedtest.swf'}
            request = build_request('https://www.speedtest.net/api/api.php', data='&'.join(api_data).encode(), headers=headers)
            fdesc = catch_request(request)
            if fdesc is False:
                log(0, 'Could not submit results to speedtest.net')
                return False
            response = fdesc.read()
            code = fdesc.code
            fdesc.close()

            if int(code) != 200:
                log(0, 'Could not submit results to speedtest.net')
                return False

            qsargs = parse_qs(response.decode())  # pylint: disable=deprecated-method
            resultid = qsargs.get('resultid')
            if not resultid or len(resultid) != 1:
                log(0, 'Could not submit results to speedtest.net')
                return False

            global IMAGE_RESULT  # pylint: disable=global-statement
            IMAGE_RESULT = 'https://www.speedtest.net/result/%s.png' % resultid[0]

        return True


def run():
    """Addon entry point from wrapper"""
    speedtest = SpeedTest('script-speedtester_main.xml', addon_path(), 'Default')
    del speedtest
