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
from resources.lib.utils.detectPath import process_cmdline, fsencode
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
        super(TaskScript, self).__init__(name='TaskScript')

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
        msg = u''
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
        fse = sys.getfilesystemencoding()
        if fse is None:
            fse = 'utf-8'
        cmd = self.taskKwargs['scriptfile']
        if sysplat.startswith('win'):
            if cmd.encode('utf-8') != cmd.encode(fse):
                cmd = fsencode(self.taskKwargs['scriptfile'])
        tmpl = process_cmdline(cmd)
        filefound = False
        basedir = None
        sysexecutable = None
        for i, tmp in enumerate(tmpl):
            tmp = unicode(xbmc.translatePath(tmp), encoding='utf-8')
            if os.path.exists(tmp) and filefound is False:
                basedir, fn = os.path.split(tmp)
                basedir = os.path.realpath(basedir)
                tmpl[i] = fn
                filefound = True
                if i == 0:
                    if os.path.splitext(fn)[1] == u'.sh':
                        if isAndroid:
                            sysexecutable = u'/system/bin/sh'
                        elif not sysplat.startswith('win'):
                            sysexecutable = u'/bin/bash'
            else:
                tmpl[i] = tmp
        if sysexecutable == u'/system/bin/sh':
            tmpl.insert(0, u'sh')
        elif sysexecutable == u'/bin/bash':
            tmpl.insert(0, u'bash')

        cwd = os.getcwd()
        argsu = tmpl + self.runtimeargs

        args = []
        for arg in argsu:
            try:
                args.append(arg.encode(fse))
            except UnicodeEncodeError:
                msg += u'Unicode Encode Error for: "%s" Encoder: %s' % (arg, fse)
        if needs_shell:
            args = ' '.join(args)
        err = False
        msg += u'taskScript ARGS = %s\n    SYSEXEC = %s\n BASEDIR = %s\n' % (args, sysexecutable, basedir)
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
                    stdoutdata = stdoutdata.decode(fse, 'ignore').strip()
                    if stdoutdata != '':
                        msg += _(u'Process returned data: [%s]\n') % stdoutdata
                    else:
                        msg += _(u'Process returned no data\n')
                else:
                    msg += _(u'Process returned no data\n')
                if stderrdata is not None:
                    stderrdata = stderrdata.decode(fse, 'ignore').strip()
                    if stderrdata != '':
                        msg += _(u'Process returned error: %s') % stderrdata
        except ValueError, e:
            err = True
            msg = unicode(e)
        except subprocess.CalledProcessError, e:
            err = True
            if hasattr(e, 'output'):
                msg = unicode(e.output)
            else:
                msg = unicode(e)
        except Exception:
            e = sys.exc_info()[0]
            err = True
            if hasattr(e, 'message'):
                msg = unicode(e.message)
            msg = msg + u'\n' +traceback.format_exc().decode('utf-8', 'ignore')
        finally:
            os.chdir(cwd)
        self.threadReturn(err, msg)

