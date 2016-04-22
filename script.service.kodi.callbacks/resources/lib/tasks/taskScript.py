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
import os
import stat
import subprocess
import traceback
from resources.lib.taskABC import AbstractTask, notify, KodiLogger
from resources.lib.utils.detectPath import process_cmdline
import xbmc
import xbmcvfs
from resources.lib.utils.poutil import KodiPo
kodipo = KodiPo()
_ = kodipo.getLocalizedString
__ = kodipo.getLocalizedStringId

sysplat = sys.platform
isAndroid = 'XBMC_ANDROID_SYSTEM_LIBS' in os.environ.keys()

class TaskScript(AbstractTask):
    tasktype = 'script'
    variables = [
        {
            'id':u'scriptfile',
            'settings':{
                'default':u'',
                'label':u'Script executable file',
                'type':'sfile'
            }
        },
        {
            'id':u'use_shell',
            'settings':{
                'default':u'false',
                'label':u'Requires shell?',
                'type':'bool'
            }
        },
        {
            'id':u'waitForCompletion',
            'settings':{
                'default':u'true',
                'label':u'Wait for script to complete?',
                'type':'bool'
            }
        }
    ]


    def __init__(self):
        super(TaskScript, self).__init__()

    @staticmethod
    def validate(taskKwargs, xlog=KodiLogger.log):

        tmpl = process_cmdline(taskKwargs['scriptfile'])
        found = False
        for tmp in tmpl:
            tmp = xbmc.translatePath(tmp)
            if xbmcvfs.exists(tmp) or os.path.exists(tmp) and found is False:
                try:
                    mode = os.stat(tmp).st_mode
                    mode |= stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
                    os.chmod(tmp, mode)
                except OSError:
                    if sysplat.startswith('win') is False:
                        xlog(msg=_('Failed to set execute bit on script: %s') % tmp)
                finally:
                    found = True
        return True

    def run(self):
        msg = ''
        if self.taskKwargs['notify'] is True:
            notify(_('Task %s launching for event: %s') % (self.taskId, str(self.topic)))
        try:
            needs_shell = self.taskKwargs['use_shell']
        except KeyError:
            needs_shell = False
        try:
            wait = self.taskKwargs['waitForCompletion']
        except KeyError:
            wait = True
        tmpl = process_cmdline(self.taskKwargs['scriptfile'])
        filefound = False
        basedir = None
        sysexecutable = None
        for i, tmp in enumerate(tmpl):
            tmp = xbmc.translatePath(tmp)
            if os.path.exists(tmp) and filefound is False:
                basedir, fn = os.path.split(tmp)
                basedir = os.path.realpath(basedir)
                tmpl[i] = fn
                filefound = True
                if i == 0:
                    if os.path.splitext(fn)[1] == u'.sh':
                        if isAndroid:
                            sysexecutable = '/system/bin/sh'
                        elif not sysplat.startswith('win'):
                            sysexecutable = '/bin/bash'
            else:
                tmpl[i] = tmp
        if sysexecutable == '/system/bin/sh':
            tmpl.insert(0, 'sh')
        elif sysexecutable == '/bin/bash':
            tmpl.insert(0, 'bash')

        cwd = os.getcwd()
        args = tmpl + self.runtimeargs
        if needs_shell:
            args = ' '.join(args)
        err = False
        msg += 'taskScript ARGS = %s\n    SYSEXEC = %s\n BASEDIR = %s\n' % (args, sysexecutable, basedir)
        sys.exc_clear()
        try:
            if basedir is not None:
                os.chdir(basedir)
            if sysexecutable is not None:
                if isAndroid or sysplat.startswith('darwin'):
                    p = subprocess.Popen(args, stdout=subprocess.PIPE, shell=needs_shell, stderr=subprocess.STDOUT, executable=sysexecutable)
                else:
                    p = subprocess.Popen(args, stdout=subprocess.PIPE, shell=needs_shell, stderr=subprocess.STDOUT, executable=sysexecutable, cwd=basedir)
            else:
                if isAndroid or sysplat.startswith('darwin'):
                    p = subprocess.Popen(args, stdout=subprocess.PIPE, shell=needs_shell, stderr=subprocess.STDOUT)
                else:
                    p = subprocess.Popen(args, stdout=subprocess.PIPE, shell=needs_shell, stderr=subprocess.STDOUT, cwd=basedir)
            if wait:
                stdoutdata, stderrdata = p.communicate()
                if stdoutdata is not None:
                    stdoutdata = str(stdoutdata).strip()
                    if stdoutdata != '':
                        msg += _('Process returned data: [%s]\n') % stdoutdata
                    else:
                        msg += _('Process returned no data\n')
                else:
                    msg += _('Process returned no data\n')
                if stderrdata is not None:
                    stderrdata = str(stderrdata).strip()
                    if stderrdata != '':
                        msg += _('Process returned error: %s') % stdoutdata
        except ValueError, e:
            err = True
            msg = str(e)
        except subprocess.CalledProcessError, e:
            err = True
            msg = e.output
        except Exception:
            e = sys.exc_info()[0]
            err = True
            if hasattr(e, 'message'):
                msg = str(e.message)
            msg = msg + '\n' + traceback.format_exc()
        finally:
            os.chdir(cwd)
        self.threadReturn(err, msg)

