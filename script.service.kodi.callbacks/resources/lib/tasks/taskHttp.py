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
        super(TaskHttp, self).__init__()
        self.runtimeargs = ''

    @staticmethod
    def validate(taskKwargs, xlog=KodiLogger.log):
        o = urlparse(taskKwargs['http'])
        if o.scheme != '' and o.netloc != '':
            return True
        else:
            xlog(msg=_('Invalid url: %s') % taskKwargs['http'])
            return False

    def sendRequest(self, session, verb, url, postget=False):
        if postget or verb == 'POST' or verb == 'PUT':
            url, data = url.split('??', 1)
            if postget:
                data = None
        else:
            data = None
        req = requests.Request(verb, url, data=data)
        prepped = session.prepare_request(req)
        if verb == 'POST' or verb == 'PUT':
            prepped.headers['Content-Type'] = self.taskKwargs['content-type']
        msg = 'Prepped URL: %s\nBody: %s' % (prepped.url, prepped.body)
        try:
            resp = session.send(prepped, timeout=20)
            msg += '\nStatus: %s' % str(resp.status_code)
            resp.raise_for_status()
            err = False
            if resp.text == '':
                respmsg = 'No response received'
            else:
                respmsg = resp.text
            msg += '\nResponse for %s: %s' %(verb, respmsg)
            resp.close()
        except requests.ConnectionError as e:
            err = True
            msg = _('Requests Connection Error')
        except requests.HTTPError as e:
            err = True
            msg = '%s: %s' %(_('Requests HTTPError'), str(e))
        except requests.URLRequired as e:
            err = True
            msg = '%s: %s' %(_('Requests URLRequired Error'), str(e))
        except requests.Timeout as e:
            err = True
            msg = '%s: %s' %(_('Requests Timeout Error'), str(e))
        except requests.RequestException as e:
            err = True
            msg = '%s: %s' %(_('Generic Requests Error'), str(e))
        except urllib2.HTTPError, e:
            err = True
            msg = _('HTTPError = ') + str(e.code)
        except urllib2.URLError, e:
            err = True
            msg = _('URLError\n') + e.reason
        except httplib.BadStatusLine:
            err = False
            self.log(msg=_('Http Bad Status Line caught and passed'))
        except httplib.HTTPException, e:
            err = True
            msg = _('HTTPException')
            if hasattr(e, 'message'):
                msg = msg + '\n' + e.message
        except socket.timeout:
            err = True
            msg = _('The request timed out, host unreachable')
        except Exception:
            err = True
            e = sys.exc_info()[0]
            if hasattr(e, 'message'):
                msg = str(e.message)
            msg = msg + '\n' + traceback.format_exc()
        return err, msg


    def run(self):
        if self.taskKwargs['notify'] is True:
            notify(_('Task %s launching for event: %s') % (self.taskId, str(self.topic)))
        if isinstance(self.runtimeargs, list):
            if len(self.runtimeargs) > 0:
                self.runtimeargs = ''.join(self.runtimeargs)
            else:
                self.runtimeargs = ''
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
            msg = '\n'.join([msg, msg2])

        s.close()
        self.threadReturn(err, msg)

