import os
import sys
import util
import threading
import traceback


class ActionCommand:
    type = None

    def __init__(self, data):
        self.thread = None
        self.commandData = data
        self.args = []
        self.output = []
        self.path = None

    def _addOutput(self, output):
        self.output += output.splitlines()

    def _absolutizeCommand(self):
        return os.path.normpath(os.path.join(os.path.dirname(self.path), self.commandData))

    def join(self):
        if self.thread:
            self.thread.join()

    def setPath(self, path):
        self.path = path

    def addArg(self, arg):
        self.args.append(arg)

    def _threadedExecute(self):
        self.thread = threading.Thread(target=self._execute)
        self.thread.start()

    def _execute(self):
        try:
            self.execute()
        except:
            util.ERROR()
            self._addOutput('ERROR: ' + '[CR]'.join(traceback.format_exc().splitlines()))

    def execute(self):
        return False

    def _test(self):
        self._threadedExecute()

    def log(self, msg):
        util.DEBUG_LOG(msg)
        self._addOutput(msg)


class SleepCommand(ActionCommand):
    type = 'SLEEP'

    def _threadedExecute(self):
        import time

        try:
            totalMS = int(self.commandData)
        except:
            util.ERROR()
            self._addOutput(traceback.format_exc())

        import xbmc
        import time

        now = time.time()
        end = now + (totalMS / 1000.0)
        ms = min(totalMS, 200)

        self.log('Action (Sleep) Start: {0} ({1})'.format(self.commandData, now))

        while not xbmc.abortRequested and now < end and xbmc.getInfoLabel('Window(10000).Property(script.cinemavision.running)'):
            xbmc.sleep(ms)
            now = time.time()
            ms = min(int((end - now) * 1000), 200)

        self.log('Action (Sleep) End: {0} ({1})'.format(self.commandData, now))

    def _test(self):
        try:
            totalMS = int(self.commandData)
            testMS = min(totalMS, 1000)
            self.commandData = str(testMS)
            if testMS != totalMS:
                 self.log('Action (Sleep) Changed for test: {0} to {1}'.format(totalMS, testMS))
        except:
            pass

        self._threadedExecute()


class ModuleCommand(ActionCommand):
    type = 'MODULE'
    importPath = os.path.join(util.STORAGE_PATH, 'import')

    def checkImportPath(self):
        if not os.path.exists(self.importPath):
            os.makedirs(self.importPath)

    def copyModule(self):
        import shutil
        shutil.copyfile(self._absolutizeCommand(), os.path.join(self.importPath, 'cinema_vision_command_module.py'))

    def execute(self):
        self.checkImportPath()
        self.copyModule()

        try:
            self.log('Action (Module) Executing: {0} ({1})'.format(self.commandData, ', '.join(self.args)))
            if self.importPath not in sys.path:
                sys.path.append(self.importPath)

            import cinema_vision_command_module
            reload(cinema_vision_command_module)

            result = cinema_vision_command_module.main(*self.args)
            self.log('Action (Module) Succeded: {0} ({1}) - Result: {2}'.format(self.commandData, ', '.join(self.args), result))
        except:
            util.ERROR()
            self._addOutput(traceback.format_exc())


class SubprocessActionCommand(ActionCommand):
    def getStartupInfo(self):
        import subprocess
        if hasattr(subprocess, 'STARTUPINFO'):  # Windows
            startupinfo = subprocess.STARTUPINFO()
            try:
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW  # Suppress terminal window
            except:
                startupinfo.dwFlags |= 1
            return startupinfo

        return None


class ScriptCommand(SubprocessActionCommand):
    type = 'SCRIPT'

    def execute(self):
        command = ['python', self._absolutizeCommand()]
        command += self.args
        import subprocess

        self.log('Action (Script) Command: {0}'.format(repr(' '.join(command)).lstrip('u').strip("'")))

        subprocess.Popen(command, startupinfo=self.getStartupInfo())


class CommandCommand(SubprocessActionCommand):
    type = 'COMMAND'

    def execute(self):
        command = [self._absolutizeCommand()]
        command += self.args

        import subprocess

        self.log('Action (Script) Command: {0}'.format(repr(' '.join(command)).lstrip('u').strip("'")))

        subprocess.Popen(command, startupinfo=self.getStartupInfo())


class AddonCommand(ActionCommand):
    type = 'ADDON'

    def execute(self):
        try:
            import xbmc
        except:
            return False

        xbmc.executebuiltin('RunScript({commandData},{args})'.format(commandData=self.commandData, args=','.join(self.args)))

        self.log('Action (Addon) Executing: {0} ({1})'.format(self.commandData, ', '.join(self.args)))

        return True

class PythonCommand(ActionCommand):
    type = 'PYTHON'

    def execute(self):

        try:
            import xbmc
            import xbmcgui
            import xbmcvfs
            import xbmcaddon
        except:
            return False

        _CV_COMMAND_RESULT_ = None

        if self.commandData:
            with open(self._absolutizeCommand(), 'r') as f:
                exec(f)
            self.log('Action (Python) Executed: {0} Result: {1}'.format(self.commandData, _CV_COMMAND_RESULT_))
            return True

        if len(self.args) == 1:
            arg = self.args[0]
            self.log('Action (Python) Executed: {0} Result: {1}'.format(arg, eval(arg)))
        else:
            code = '\n'.join(self.args)
            exec(code)
            self.log('Action (Python) Executed: {0} Lines - Result: {1}'.format(len(self.args), _CV_COMMAND_RESULT_))

        return True


class HTTPCommand(ActionCommand):
    type = 'HTTP'
    commandID = 0

    def __init__(self, data):
        data = 'http://' + data
        ActionCommand.__init__(self, data)

    def execute(self):
        import requests
        import json

        headers = None
        method = None
        data = None
        args = list(self.args)

        HTTPCommand.commandID += 1
        commandID = self.commandID

        self.log('Action (HTTP) [{0}] URL: {1}'.format(commandID, self.commandData))

        while args:
            arg = args.pop()
            if arg.startswith('PUT:'):
                data = arg[4:].lstrip()
                method = requests.put
            elif arg.startswith('DELETE:'):
                method = requests.delete
            elif arg.startswith('HEADERS:'):
                headers = json.loads(arg[8:].lstrip())
            else:
                if arg.startswith('POST:'):
                    data = arg[5:].lstrip()
                    method = requests.post
                else:
                    data = arg
                    method = method or requests.post

        if method:
            resp = method(self.commandData, headers=headers, data=data)
        else:
            resp = requests.get(self.commandData, headers=headers)

        self.log('Action (HTTP) [{0}] Response: {1}'.format(commandID, repr(resp.text).lstrip('u').strip("'")))


class HTTPSCommand(HTTPCommand):
    def __init__(self, data):
        data = 'https://' + data
        ActionCommand.__init__(self, data)


class ActionFileProcessor:
    commandClasses = {
        'http': HTTPCommand,
        'https': HTTPSCommand,
        'script': ScriptCommand,
        'python': PythonCommand,
        'addon': AddonCommand,
        'module': ModuleCommand,
        'command': CommandCommand,
        'sleep': SleepCommand
    }

    def __init__(self, path, test=False):
        self._test = test
        self.path = path
        self.fileExists = None
        self.commands = []
        self.parserLog = []
        self.init()

    def __repr__(self):
        return 'AFP ({0})'.format(','.join([a.type for a in self.commands]))

    def setCVRunning(self, running=True):
        try:
            from lib import kodiutil
            kodiutil.setGlobalProperty('running', running and '1' or '')
        except:
            util.ERROR()

    def logParseErrorLine(self, msg, type_):
        if not self._test:
            util.DEBUG_LOG('    -| {0}'.format(msg))
        self.parserLog.append((type_, msg))

    def parseError(self, msg, line, lineno, type_='ERROR'):
        self.logParseErrorLine(u'ACTION {0} (line {1}): {2}'.format(type_, lineno, repr(self.path).lstrip('u').strip("'")), type_)
        self.logParseErrorLine(u'{0}'.format(repr(line)), type_)
        self.logParseErrorLine(u'{0}'.format(msg), type_)

    def init(self):
        try:
            self._loadCommands()
        except:
            util.ERROR()

    def readFile(self):
        if util.vfs.exists(self.path):
            self.fileExists = True
            with util.vfs.File(self.path, 'r') as f:
                return f.read()
        else:
            self.fileExists = False
            return None

    def run(self):
        threading.Thread(target=self._run).start()

    def _run(self):
        for c in self.commands:
            c._threadedExecute()

    def _testRun(self):
        self.setCVRunning()

        try:
            for c in self.commands:
                c._test()
        finally:
            self.setCVRunning(False)

    def test(self):
        self._testRun()
        output = []
        for c in self.commands:
            c.join()
            output += c.output
            output.append('')
        return output

    def _prepareLine(self, line):
        if line.startswith('\\'):
            line = line[1:]
        return line

    def _loadCommands(self):
        data = self.readFile()
        if not data:
            return

        command = None
        lineno = 0
        for line in data.splitlines():
            lineno += 1
            if line:
                if line.startswith('#'):
                    continue

                if command:
                    try:
                        name, data = line.split('://', 1)
                        if name in self.commandClasses:
                            self.parseError(
                                'Argument looks like a command - actions must be separated by a blank line. Prefix with \\ to hide this warning',
                                line,
                                lineno,
                                type_='WARNING'
                            )
                    except ValueError:
                        pass

                    command.addArg(self._prepareLine(line))
                else:
                    try:
                        name, data = self._prepareLine(line).split('://', 1)
                    except ValueError:
                        self.parseError('First action line must have the form: <protocol>://<protocol data>', line, lineno)
                        return

                    if name in self.commandClasses:
                        command = self.commandClasses[name](data)
                        command.setPath(self.path)
                    else:
                        self.parseError(u'Unrecognized command protocol: {0}'.format(repr(name)), line, lineno)
                        return
            else:
                if command:
                    self.commands.append(command)
                command = None

        if command:
            self.commands.append(command)
