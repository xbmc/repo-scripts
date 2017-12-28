#
#      Copyright (C) 2013 Tommy Winther
#      http://tommy.winther.nu
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with XBMC; see the file COPYING.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#
#
import datetime
import os
import platform
import simplejson
import sys
import traceback
import urllib2
import smtplib
from email.mime.text import MIMEText
import xbmc
import xbmcaddon

import buggalo_userflow as userflow


def gatherData(etype, value, tracebackInfo, extraData, globalExtraData):
    """
    This method gathers all available data and bundles it in one dict object

    @param etype: Type of the raised exception (output of sys.exc_info)
    @param value: ... (output of sys.exc_info)
    @param tracebackInfo: ... (output of sys.exc_info)
    @param extraData: Additional data given for the specific try-except-clause
    @param globalExtraData: Data assembled over the whole runtime of the addon
    """
    data = dict()
    data['version'] = 4
    data['timestamp'] = datetime.datetime.now().isoformat()

    exception = dict()
    exception['stacktrace'] = traceback.format_tb(tracebackInfo)
    exception['type'] = str(etype)
    exception['value'] = str(value)
    data['exception'] = exception

    system = dict()
    try:
        if hasattr(os, 'uname'):
            # Works on recent unix flavors
            (sysname, nodename, release, version, machine) = os.uname()
        else:
            # Works on Windows (and others?)
            (sysname, nodename, release, version, machine, processor) = platform.uname()

        system['nodename'] = nodename
        system['sysname'] = sysname
        system['release'] = release
        system['version'] = version
        system['machine'] = machine
    except Exception, ex:
        system['sysname'] = sys.platform
        system['exception'] = str(ex)
    data['system'] = system

    addon = xbmcaddon.Addon()
    addonInfo = dict()
    addonInfo['id'] = addon.getAddonInfo('id')
    addonInfo['name'] = addon.getAddonInfo('name')
    addonInfo['version'] = addon.getAddonInfo('version')
    addonInfo['path'] = addon.getAddonInfo('path')
    addonInfo['profile'] = addon.getAddonInfo('profile')
    data['addon'] = addonInfo

    xbmcInfo = dict()
    xbmcInfo['buildVersion'] = xbmc.getInfoLabel('System.BuildVersion')
    xbmcInfo['buildDate'] = xbmc.getInfoLabel('System.BuildDate')
    xbmcInfo['skin'] = xbmc.getSkinDir()
    xbmcInfo['language'] = xbmc.getInfoLabel('System.Language')
    data['xbmc'] = xbmcInfo

    execution = dict()
    execution['python'] = sys.version
    execution['sys.argv'] = sys.argv
    data['execution'] = execution

    data['userflow'] = userflow.loadUserFlow()

    extraDataInfo = dict()
    try:
        # convert globalExtraData to a dict that can be processed by BuggaloDialog, submitData and emailData (as part of data)
        for (key, value) in globalExtraData.items():
            if isinstance(value, str):
                extraDataInfo[key] = value.decode('utf-8', 'ignore') # convert to unicode
            elif isinstance(value, unicode):
                extraDataInfo[key] = value
            else:
                extraDataInfo[key] = str(value)

        if isinstance(extraData, dict):
            for (key, value) in extraData.items():
                if isinstance(extraData, str):
                    extraDataInfo[key] = value.decode('utf-8', 'ignore')
                elif isinstance(extraData, unicode):
                    extraDataInfo[key] = value
                else:
                    extraDataInfo[key] = str(value)
        elif extraData is not None:
            if isinstance(extraData, unicode):
                extraDataInfo[''] = extraData
            else:
                extraDataInfo[''] = str(extraData)
    except Exception, ex:
        (etype, value, tb) = sys.exc_info()
        traceback.print_exception(etype, value, tb)
        extraDataInfo['exception'] = str(ex)
    data['extraData'] = extraDataInfo

    return data


def submitData(serviceUrl, data):
    for attempt in range(0, 3):
        try:
            json = simplejson.dumps(data)
            req = urllib2.Request(serviceUrl, json)
            req.add_header('Content-Type', 'text/json')
            u = urllib2.urlopen(req)
            u.read()
            u.close()
            break  # success; no further attempts
        except Exception:
            pass # probably timeout; retry


def emailData(emailConfig, data):
    """

    @param recipient:
    @param data:
    @return:
    """

    # build html table with data (with unicode character set)
    body = u'<table border="1">'
    for group in sorted(data.keys()):
        values = data[group]
        if type(values) == dict:
            body += u'<tr><td colspan="2"><h2>%s</h2></td></tr>' % group.capitalize()
            keys = values.keys()
            if group == u'userflow':
                keys = sorted(keys)

            for key in keys:
                body += u'<tr><td>%s</td>' % str(key)
                if key == u'stacktrace':
                    body += u'<td><pre>'
                    for item in values[key]:
                        body += item + '\n'
                    body += u'</pre></td>'
                elif key == u'type':
                    body += u'<td>%s</td>' % str(values[key][5:-2])
                elif group == u'extraData':
                    body += u'<td style="white-space: pre">%s</td>' % values[key] # values in extraData are unicode
                else:
                    body += u'<td>%s</td>' % str(values[key])
                body += u'</tr>'
        else:
            body += '<tr><td><h2>%s</h2></td><td>%s</td></tr>' % (group.capitalize(), str(values))
    body += u'</table>'

    msg = MIMEText(body, 'html', 'utf-8')
    msg['Subject'] = '[Buggalo][%s] v%s: %s' % (data['addon']['id'], data['addon']['version'], data['exception']['value'])
    if 'sender' in emailConfig:
        msg['From'] = emailConfig['sender']
    else:
        msg['From'] = 'Buggalo@buggalo.com'
    msg['To'] = emailConfig['recipient']
    msg['X-Mailer'] = 'Buggalo Exception Collector'

    if not 'server' in emailConfig:
        emailConfig['server'] = 'gmail-smtp-in.l.google.com'

    if not 'method' in emailConfig:
        emailConfig['method'] = 'default'
        
    if emailConfig['method'] == 'ssl':
        smtp = smtplib.SMTP_SSL(emailConfig['server'])
    else:
        # smtp on port 25
        smtp = smtplib.SMTP(emailConfig['server'])

    if 'user' in emailConfig and 'pass' in emailConfig:
        # necessary for ssl connection
        smtp.login(emailConfig['user'], emailConfig['pass'])
    smtp.sendmail(msg['From'], msg['To'], msg.as_string(9))
    smtp.quit()
