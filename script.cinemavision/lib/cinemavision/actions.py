import os
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

    def _addOutput(self, output):
        self.output += output.splitlines()

    def join(self):
        if self.thread:
            self.thread.join()

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

    def log(self, msg):
        util.DEBUG_LOG(msg)
        self._addOutput(msg)


class SleepCommand(ActionCommand):
    type = 'SLEEP'

    def _threadedExecute(self):
        import time

        try:
            ms = int(self.commandData)
        except:
            util.ERROR()
            self._addOutput(traceback.format_exc())

        time.sleep(ms/1000.0)


class ModuleCommand(ActionCommand):
    type = 'MODULE'
    importPath = os.path.join(util.STORAGE_PATH, 'import')

    def checkImportPath(self):
        import os
        if not os.path.exists(self.importPath):
            os.makedirs(self.importPath)

    def copyModule(self):
        import shutil
        shutil.copyfile(self.commandData, os.path.join(self.importPath, 'cinema_vision_command_module.py'))

    def execute(self):
        self.checkImportPath()
        self.copyModule()

        import sys
        if self.importPath not in sys.path:
            sys.path.append(self.importPath)

        import cinema_vision_command_module
        cinema_vision_command_module.main(*self.args)


class ScriptCommand(ActionCommand):
    type = 'SCRIPT'

    def execute(self):
        command = ['python', self.commandData]
        command += self.args

        import subprocess

        self.log('Action (Script) Command: {0}'.format(repr(' '.join(command)).lstrip('u').strip("'")))

        subprocess.Popen(command)


class CommandCommand(ActionCommand):
    type = 'COMMAND'

    def execute(self):
        command = [self.commandData]
        command += self.args

        import subprocess

        self.log('Action (Script) Command: {0}'.format(repr(' '.join(command)).lstrip('u').strip("'")))

        subprocess.Popen(command)


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


class HTTPCommand(ActionCommand):
    type = 'HTTP'

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

        self.log('Action (HTTP) URL: {0}'.format(self.commandData))

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
        else:
            if method:
                resp = method(self.commandData, headers=headers, data=data)
            else:
                resp = requests.get(self.commandData, headers=headers)

        self.log('Action (HTTP) Response: {0}'.format(repr(resp.text).lstrip('u').strip("'")))


class HTTPSCommand(HTTPCommand):
    def __init__(self, data):
        data = 'https://' + data
        ActionCommand.__init__(self, data)


class ActionFileProcessor:
    commandClasses = {
        'http': HTTPCommand,
        'https': HTTPSCommand,
        'script': ScriptCommand,
        'python': ScriptCommand,
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

    def test(self):
        self._run()
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
                    else:
                        self.parseError(u'Unrecognized command protocol: {0}'.format(name), line, lineno)
                        return
            else:
                if command:
                    self.commands.append(command)
                command = None

        if command:
            self.commands.append(command)
