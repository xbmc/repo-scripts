#   Copyright (C) 2025 Lunatixz
#
#
# This file is part of CPU Benchmark.
#
# CPU Benchmark is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# CPU Benchmark is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CPU Benchmark.  If not, see <http://www.gnu.org/licenses/>.
# https://pybenchmarks.org/u64q/performance.php?test=pystone

import re, os, sys, time, platform, subprocess, textwrap, requests

try:
    import multiprocessing
    cpu_count   = multiprocessing.cpu_count()
    ENABLE_POOL = True
except:
    ENABLE_POOL = False
    cpu_count   = os.cpu_count()

from resources.lib import pystone
from kodi_six      import xbmc, xbmcaddon, xbmcplugin, xbmcgui, xbmcvfs, py2_encode, py2_decode

LIMIT = 45
LINE  = 64
LOOP  = 50000

# Plugin Info
ADDON_ID       = 'script.pystone.benchmark'
REAL_SETTINGS  = xbmcaddon.Addon(id=ADDON_ID)
ADDON_NAME     = REAL_SETTINGS.getAddonInfo('name')
ADDON_PATH     = REAL_SETTINGS.getAddonInfo('path')
ADDON_VERSION  = REAL_SETTINGS.getAddonInfo('version')
SETTINGS_LOC   = REAL_SETTINGS.getAddonInfo('profile')
ICON           = REAL_SETTINGS.getAddonInfo('icon')
FANART         = REAL_SETTINGS.getAddonInfo('fanart')
LANGUAGE       = REAL_SETTINGS.getLocalizedString

# System Info
cpu_name              = platform.processor()
os_name               = platform.system() # Get the OS name
os_version            = platform.release()# Get the OS version
platform_info         = platform.platform()# Get a general platform identifier
python_implementation = platform.python_implementation()# Get the Python implementation
python_version        = platform.python_version()# Get the Python version
machine_arch          = platform.machine()# Get the machine architecture
architecture          = platform.architecture()
is_arm                = platform.machine().startswith('arm')
kodi_info             = xbmc.getInfoLabel('System.BuildVersion')

try:
    system_info   = platform.uname()
    sys_processor = system_info.processor 
    sys_machine   = system_info.machine
    sys_system    = system_info.system
except:
    system_info   = None
    sys_processor = None
    sys_machine   = None
    sys_system    = None

def log(msg, level=xbmc.LOGDEBUG):
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,msg),level)

def _repeat(length=LIMIT, fill='█'):
   length = int(round(length))
   return (fill * int((length/len(fill))+1))[:length]
   
def replace_with_k(number_string):
    number = int(number_string)
    if number >= 1000: return f"{number // 1000}k"
    else:              return number_string
    
def progress_bar(iteration, total, length=LIMIT, fill='█'):
    percent = ("{0:.1f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    if filled_length > 10: bar_with_percent = f"{bar[:length//2 - len(percent)//2]}{percent}%{bar[length//2 - len(percent)//2 + len(percent):]}"
    else:                  bar_with_percent = bar
    return f'|{bar_with_percent}|'

def score_bar(stones, pyseed, pydur, avg, length=LIMIT):
    def _insert(value, score):
        fill   = _repeat(length-4)
        if value >= 100: value = 90
        value  = (100-value)
        sindex = int(length * ((length / 100) * value / length))
        colors = ['green','yellow','orange','red','dimgrey','dimgrey']
        chunks = textwrap.wrap(fill[:sindex - len(score)//2] + score + fill[sindex + len(score)//2:], length//4)
        bars   = ''.join([LANGUAGE(30004)%(colors.pop(0),chunk) for chunk in chunks if len(colors) > 0 ])
        return f'| {bars} | {replace_with_k(pyseed)} in %ss'%("{0:.2f}".format(pydur))
    return _insert(avg, f'| {stones} |')

def get_info():   
    def __rpi():
        try: # Attempt to retrieve CPU frequency (Pi only, from /proc/device-tree/model)
            with open("/proc/device-tree/model", "r") as f:
                return f' {f.read().strip()}' # Remove leading/trailing whitespace
        except: return ''
 
    def __cpu():
        try:
            if is_arm or system_info.system == "Linux":# Attempt to retrieve CPU frequency (Linux only, from /proc/cpuinfo)
                try:
                    with open("/proc/cpuinfo", "r") as f:
                        cpu_info = re.search(r'model name\s*:\s*(.+)', f.read()).group(1).strip()
                        if is_arm: return f'{cpu_info}{__rpi()}'
                        else:      return cpu_info
                except: pass
            elif system_info.system == "Darwin":
                return subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"]).strip()
            elif system_info.system == "Windows":
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"Hardware\Description\System\CentralProcessor\0")
                cpu_info = winreg.QueryValueEx(key, "ProcessorNameString")[0]
                winreg.CloseKey(key)
                return cpu_info
        except Exception as e: log("__cpu, failed! %s"%(e), xbmc.LOGERROR)

    return '[CR]'.join([
                      (f"Kodi Build: [B]{kodi_info}[/B]"),
                      (f"Operating System: [B]{(sys_system or os_name)} v.{os_version} ({platform_info})[/B]"),
                      (_repeat(LINE,'_')),
                      (f"Processor: [B]{__cpu() or sys_processor or cpu_name}[/B]"),
                      (f"Machine Architecture: [B]{(sys_machine or machine_arch)} {' '.join(architecture)}[/B]"),
                      (f"Logical CPU Cores (including Hyperthreading if applicable): [B]{cpu_count}[/B]"),
                      (_repeat(LINE,'_')),
                      (f"Python: [B]{python_implementation} v.{python_version}[/B][CR]Benchmark: [B]pystone v.{pystone.__version__}[/B] n={LOOP}"),
                      (_repeat(LINE,'_'))
                      ])

class TEXTVIEW(xbmcgui.WindowXMLDialog):
    textbox = None
    
    def __init__(self, *args, **kwargs):
        self.head = f'{ADDON_NAME} v.{ADDON_VERSION}'
        self.text = get_info()
        self.doModal()
            
    def _updateText(self, txt):
        try:
            self.textbox.setText(txt)
            xbmc.executebuiltin('SetFocus(3000)')
            xbmc.executebuiltin('AlarmClock(down,Action(down),.5,true,false)')
            xbmc.executebuiltin('AlarmClock(down,Action(down),.5,true,false)')
        except: pass

    def onInit(self):
        self.getControl(1).setLabel(self.head)
        self.textbox = self.getControl(5)
        self._updateText(self.text)
        self._run([LOOP for i in range(cpu_count)]) #todo multiprocessing?

    def onClick(self, control_id):
        pass

    def onFocus(self, control_id):
        pass

    def onAction(self, action):
        if action in [xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK]:
            self.close()

    def _run(self, seeds=[50000]):
        ranks = []
        for i, pyseed in enumerate(seeds):
            prog = progress_bar(i, len(seeds))
            self._updateText(f"{self.text}[CR]{prog}")
            pydur, pystonefloat = pystone.pystones(pyseed)
            ranks.append({'core':i,'seed':pyseed,'duration':pydur,'score':pystonefloat})
            if len(seeds) > 1:
                self.text = f'{self.text}[CR]Pass {i+1}{self._rank(int(pystonefloat),pyseed,pydur)}'
                self._updateText(self.text)
        self._updateText(self._total(ranks))

    def _rank(self, stones, pyseed, pydur, maxseed=200000):
        return score_bar(stones,pyseed, pydur,((stones) * 100) // maxseed)

    def _total(self, ranks):
        seeds     = []
        scores    = []
        durations = []
        for i, rank in enumerate(ranks):
            if "seed"     in rank: seeds.append(rank["seed"])
            if "score"    in rank: scores.append(rank["score"])
            if "duration" in rank: durations.append(rank["duration"])
        rank = self._rank(int(sum(scores) / len(scores)), int(sum(seeds) / len(seeds)), (sum(durations) / len(durations)))
        text = f"{self.text}[CR]{LANGUAGE(30002)} {rank}[CR]{_repeat(LINE,'_')}"
        exit = LANGUAGE(30004)%('dimgrey',LANGUAGE(30005))
        post, link = self._post(text)
        if post: text = f'{text}[CR]{LANGUAGE(30003)}: [B]{link}[/B]'
        return f"{text}[CR]{exit}"
             
    def _post(self, data):
        def __clean(text):
            text = text.replace('[CR]','\n')
            text = re.sub(r'\[COLOR=(.+?)\]', '', text)
            text = re.sub(r'\[/COLOR\]', '', text)
            text = text.replace("[B]",'').replace("[/B]",'')
            text = text.replace("[I]",'').replace("[/I]",'')
            return text
        try:
            session = requests.Session()
            response = session.post('https://paste.kodi.tv/' + 'documents', data=__clean(data).encode('utf-8'), headers={'User-Agent':'%s: %s'%(ADDON_ID, ADDON_VERSION)})
            if 'key' in response.json(): 
                url = 'https://paste.kodi.tv/' + response.json()['key']
                log('_post, successful url = %s'%(url))
                return True, url
            elif 'message' in response.json():
                log('_post, upload failed, paste may be too large')
                return False, response.json()['message']
            else:
                log('_post failed! %s'%response.text)
                return False, "Error making post"
        except:
            log('_post, unable to retrieve the paste url')
            return False, "Failed to retrieve the paste url"
              