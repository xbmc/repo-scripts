#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2014 KenV99
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import sys
import traceback
import requests
import urllib2
import httplib
from urlparse import urlparse
import socket
from resources.lib.taskABC import AbstractTask, KodiLogger, notify
from resources.lib.utils.poutil import KodiPo
kodipo = KodiPo()
_ = kodipo.getLocalizedString
__ = kodipo.getLocalizedStringId

class TaskHttp(AbstractTask):
    tasktype = 'http'
    variables = [
        {
            'id':u'http',
            'settings':{
                'default':u'',
                'label':u'HTTP string (without parameters)',
                'type':'text'
            }
        },
        {
            'id':u'user',
            'settings':{
                'default':u'',
                'label':u'user for Basic Auth (optional)',
                'type':'text'
            }
        },
        {
            'id':u'pass',
            'settings':{
                'default':u'',
                'label':u'password for Basic Auth (optional)',
                'type':'text',
                'option':u'hidden'
            }
        },
        {
            'id': u'request-type',
            'settings': {
                'default': u'GET',
                'label': u'Request Type',
                'type': u'labelenum',
                'values': [u'GET', u'POST', u'POST-GET', u'PUT', u'DELETE', u'HEAD', u'OPTIONS']
            }
        },
        {
            'id': u'content-type',
            'settings': {
                'default': u'application/json',
                'label': u'Content-Type (for POST or PUT only)',
                'type': u'labelenum',
                'values': [u'application/json', u'application/x-www-form-urlencoded', u'text/html', u'text/plain']
            }
        }
    ]

    def __init__(self):
        super(TaskHttp, self).__init__(name='TaskHttp')
        self.runtimeargs = u''

    @staticmethod
    def validate(taskKwargs, xlog=KodiLogger.log):
        o = urlparse(taskKwargs['http'])
        if o.scheme != '' and o.netloc != '':
            return True
        else:
            xlog(msg=_('Invalid url: %s') % taskKwargs['http'])
            return False

    def sendRequest(self, session, verb, url, postget=False):
        if (postget or verb == 'POST' or verb == 'PUT') and '??' in url:
            url, data = url.split(u'??', 1)
            try:
                data = data.encode('utf-8', 'replace')
            except UnicodeEncodeError:
                pass
            if postget:
                data = None
        else:
            data = None
        req = requests.Request(verb, url, data=data)
        try:
            prepped = session.prepare_request(req)
        except httplib.InvalidURL as e:
            err = True
            msg = unicode(e, 'utf-8')
            return err, msg
        if verb == 'POST' or verb == 'PUT':
            prepped.headers['Content-Type'] = self.taskKwargs['content-type']
        try:
            pu = prepped.url.decode('utf-8')
        except (AttributeError, UnicodeDecodeError):
            pu = u''
        try:
            pb = prepped.body.decode('utf-8')
        except (AttributeError, UnicodeDecodeError):
            pb = u''
        msg = u'Prepped URL: %s\nBody: %s' % (pu, pb)
        sys.exc_clear()
        try:
            resp = session.send(prepped, timeout=20)
            msg += u'\nStatus: %s' % resp.status_code
            resp.raise_for_status()
            err = False
            if resp.text == '':
                respmsg = u'No response received'
            else:
                respmsg = resp.text.decode('unicode_escape', 'ignore')
            msg += u'\nResponse for %s: %s' %(verb, respmsg)
            resp.close()
        except requests.ConnectionError:
            err = True
            msg = _(u'Requests Connection Error')
        except requests.HTTPError as e:
            err = True
            msg = u'%s: %s' %(_(u'Requests HTTPError'), str(e))
        except requests.URLRequired as e:
            err = True
            msg = u'%s: %s' %(_(u'Requests URLRequired Error'), str(e))
        except requests.Timeout as e:
            err = True
            msg = u'%s: %s' %(_(u'Requests Timeout Error'), str(e))
        except requests.RequestException as e:
            err = True
            msg = u'%s: %s' %(_(u'Generic Requests Error'), str(e))
        except urllib2.HTTPError, e:
            err = True
            msg = _(u'HTTPError = ') + unicode(e.code)
        except urllib2.URLError, e:
            err = True
            msg = _(u'URLError\n') + unicode(e.reason)
        except httplib.BadStatusLine:
            err = False
            self.log(msg=_(u'Http Bad Status Line caught and passed'))
        except httplib.HTTPException, e:
            err = True
            msg = _(u'HTTPException')
            if hasattr(e, 'message'):
                msg = msg + u'\n' + unicode(e.message)
        except socket.timeout:
            err = True
            msg = _(u'The request timed out, host unreachable')
        except Exception:
            err = True
            e = sys.exc_info()[0]
            if hasattr(e, 'message'):
                msg = unicode(e.message, errors='ignore')
            msg = msg + u'\n' + unicode(traceback.format_exc(), errors='ignore')
        return err, msg


    def run(self):
        if self.taskKwargs['notify'] is True:
            notify(_('Task %s launching for event: %s') % (self.taskId, str(self.topic)))
        if isinstance(self.runtimeargs, list):
            if len(self.runtimeargs) > 0:
                self.runtimeargs = u''.join(self.runtimeargs)
            else:
                self.runtimeargs = u''
        s = requests.Session()
        url = self.taskKwargs['http']+self.runtimeargs
        if self.taskKwargs['user'] != '' and self.taskKwargs['pass'] != '':
            s.auth = (self.taskKwargs['user'], self.taskKwargs['pass'])
        if self.taskKwargs['request-type'] == 'POST-GET':
            verb = 'POST'
        else:
            verb = self.taskKwargs['request-type']

        err, msg = self.sendRequest(s, verb, url)

        if self.taskKwargs['request-type'] == 'POST-GET':
            err2, msg2 = self.sendRequest(s, 'GET', url, postget=True)
            err = err or err2
            msg = u'\n'.join([msg, msg2])

        s.close()
        self.threadReturn(err, msg)

