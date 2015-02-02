'''
   Simple Downloader plugin for XBMC
   Copyright (C) 2010-2011 Tobias Ussing And Henrik Mosgaard Jensen

   This program is free software: you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation, either version 3 of the License, or
   (at your option) any later version.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import sys
import urllib2
import os
import time
import subprocess
import DialogDownloadProgress


#http://wiki.openelec.tv/index.php?title=How_to_make_OpenELEC_addon_-_on_MuMuDVB_sample
class SimpleDownloader():
    dialog = u""

    def __init__(self):
        self.version = u"1.9.4"
        self.plugin = u"SimpleDownloader-" + self.version

        if hasattr(sys.modules["__main__"], "common"):
            self.common = sys.modules["__main__"].common
        else:
            import CommonFunctions
            self.common = CommonFunctions

        self.common.log("")

        try:
            import StorageServer
            self.cache = StorageServer.StorageServer("Downloader")
        except:
            import storageserverdummy as StorageServer
            self.cache = StorageServer.StorageServer("Downloader")

        if hasattr(sys.modules["__main__"], "xbmcaddon"):
            self.xbmcaddon = sys.modules["__main__"].xbmcaddon
        else:
            import xbmcaddon
            self.xbmcaddon = xbmcaddon

        self.settings = self.xbmcaddon.Addon(id='script.module.simple.downloader')

        if hasattr(sys.modules["__main__"], "xbmc"):
            self.xbmc = sys.modules["__main__"].xbmc
        else:
            import xbmc
            self.xbmc = xbmc

        if hasattr(sys.modules["__main__"], "xbmcvfs"):
            self.xbmcvfs = sys.modules["__main__"].xbmcvfs
        else:
            try:
                import xbmcvfs
                self.xbmcvfs = xbmcvfs
            except ImportError:
                import xbmcvfsdummy as xbmcvfs
                self.xbmcvfs = xbmcvfs

        if hasattr(sys.modules["__main__"], "dbglevel"):
            self.dbglevel = sys.modules["__main__"].dbglevel
        else:
            self.dbglevel = 3

        if hasattr(sys.modules["__main__"], "dbg"):
            self.dbg = sys.modules["__main__"].dbg
        else:
            self.dbg = True

        self.language = self.settings.getLocalizedString
        self.hide_during_playback = self.settings.getSetting("hideDuringPlayback") == "true"
        self.notification_length = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10][int(self.settings.getSetting("notification_length"))] * 1000

        if self.settings.getSetting("rtmp_binary"):
            self.rtmp_binary = self.settings.getSetting("rtmp_binary")
        else:
            self.rtmp_binary = "rtmpdump"

        if self.settings.getSetting("vlc_binary"):
            self.vlc_binary = self.settings.getSetting("vlc_binary")
        else:
            self.vlc_binary = "vlc"

        if self.settings.getSetting("mplayer_binary"):
            self.mplayer_binary = self.settings.getSetting("mplayer_binary")
        else:
            self.mplayer_binary = "mplayer"

        self.__workersByName = {}

        self.temporary_path = self.xbmc.translatePath(self.settings.getAddonInfo("profile"))
        if not self.xbmcvfs.exists(self.temporary_path):
            self.common.log("Making path structure: " + repr(self.temporary_path))
            self.xbmcvfs.mkdir(self.temporary_path)
        self.cur_dl = {}
        self.common.log("Done")

    def download(self, filename, params={}, async=True):
        self.common.log("", 5)
        if async:
            self.common.log("Async", 5)
            self._run_async(self._startDownload, filename, params)
        else:
            self.common.log("Normal", 5)
            self._startDownload(filename, params)
        self.common.log("Done", 5)

    def _startDownload(self, filename, params={}):
        self.common.log("", 5)
        if self.cache.lock("SimpleDownloaderLock"):
            self.common.log("Downloader not active, initializing downloader.")
            self._addItemToQueue(filename, params)
            self._processQueue()
            self.cache.unlock("SimpleDownloaderLock")
        else:
            self.common.log("Downloader is active, Queueing item.")
            self._addItemToQueue(filename, params)
        self.common.log("Done", 5)

    def _setPaths(self, filename, params={}):
        self.common.log(filename, 5)
        # Check utf-8 stuff here
        params["path_incomplete"] = os.path.join(self.temporary_path.decode("utf-8"), self.common.makeUTF8(filename))
        params["path_complete"] = os.path.join(params["download_path"].decode("utf-8"), self.common.makeUTF8(filename))
        self.common.log(params["path_incomplete"], 5)
        self.common.log(params["path_complete"], 5)

        if self.xbmcvfs.exists(params["path_complete"]):
            self.common.log("Removing existing %s" % repr(params["path_complete"]))
            self.xbmcvfs.delete(params["path_complete"])

        if self.xbmcvfs.exists(params["path_incomplete"]):
            self.common.log("Removing incomplete %s" % repr(params["path_incomplete"]))
            self.xbmcvfs.delete(params["path_incomplete"])

        self.common.log("Done", 5)

    def _processQueue(self):
        self.common.log("")
        item = self._getNextItemFromQueue()
        if item:
            (filename, item) = item

            if item:
                if not self.dialog:
                    self.dialog = DialogDownloadProgress.DownloadProgress()
                    self.dialog.create(self.language(201), "")

                while item:
                    status = 500
                    self._setPaths(filename, item)

                    if not "url" in item:
                        self.common.log("URL missing : %s" % repr(item))
                    elif item["url"].find("ftp") > -1 or item["url"].find("http") > -1:
                        status = self._downloadURL(filename, item)
                    else:
                        self._detectStream(filename, item)
                        if "cmd_call" in item:
                            status = self._downloadStream(filename, item)
                        else:
                            self._showMessage(self.language(301), filename)

                    if status == 200:
                        if self.xbmcvfs.exists(item["path_incomplete"]):
                            self.common.log("Moving %s to %s" % (repr(item["path_incomplete"]), repr(item["path_complete"])))
                            self.xbmcvfs.rename(item["path_incomplete"], item["path_complete"])
                            self._showMessage(self.language(203), filename)
                        else:
                            self.common.log("Download complete, but file %s not found" % repr(item["path_incomplete"]))
                            self._showMessage(self.language(204), "ERROR")
                    elif status != 300:
                        self.common.log("Failure: " + repr(item) + " - " + repr(status))
                        self._showMessage(self.language(204), self.language(302))

                    if status == 300:
                        item = False
                    else:
                        self._removeItemFromQueue(filename)
                        item = self._getNextItemFromQueue()
                        if item:
                            (filename, item) = item

                self.common.log("Finished download queue.")
                self.cache.set("StopQueue", "")
                if self.dialog:
                    self.dialog.close()
                    self.common.log("Closed dialog")
                self.dialog = u""

    def _runCommand(self, args):
        self.common.log(" ".join(args))
        try:
            proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            self.cur_dl["proc"] =  proc
        except:
            self.common.log("Couldn't run command")
            return False
        else:
            self.common.log("Returning process", 5)
            return proc

    def _readPipe(self, proc):
        self.common.log("", 50)
        try:
            return proc.communicate()[0]
        except:
            return ""

    def _rtmpDetectArgs(self, probe_args, item):
        get = item.get
        self.common.log("")

        if get("url"):
            probe_args += ["--rtmp", get("url")]
        elif get("rtmp"):
            probe_args += ["--rtmp", get("url")]
            
        if get("host"):
            probe_args += ["--host", get("host")]
            
        if get("port"):
            probe_args += ["--port", get("port")]

        if get("protocol"):
            probe_args += ["--protocol", get("protocol")]

        if get("app"):
            probe_args += ["--app", get("app")]

        if get("tcUrl"):
            probe_args += ["--tcUrl", get("tcUrl")]

        if get("pageUrl"):
            probe_args += ["--pageUrl", get("pageUrl")]

        if get("swfUrl"):
            probe_args += ["--swfUrl", get("swfUrl")]

        if get("flashVer"):
            probe_args += ["--flashVer", get("flashVer")]

        if get("auth"):
            probe_args += ["--auth", get("auth")]

        if get("conn"):
            probe_args += ["--conn", get("conn")]

        if get("playpath"):
            probe_args += ["--playpath", get("playpath")]

        if get("playlist"):
            probe_args += ["--playlist"]

        if get("live"):
            probe_args += ["--live"]

        if get("subscribe"):
            probe_args += ["--subscribe", get("subscribe")]

        if get("resume"):
            probe_args += ["--resume"]

        if get("skip"):
            probe_args += ["--skip", get("skip")]

        if get("start"):
            probe_args += ["--start", get("start")]

        if get("stop") and "--stop" not in probe_args:
            probe_args += ["--stop", str(get("stop"))]
        elif get("duration") and "--stop" not in probe_args:
            probe_args += ["--stop", str(get("duration"))]

        if get("buffer"):
            probe_args += ["--buffer", get("buffer")]

        if get("timeout"):
            probe_args += ["--timeout", get("timeout")]

        if get("token"):
            probe_args += ["--token", get("token")]

        if get("swfhash"):
            probe_args += ["--swfhash", get("swfhash")]

        if get("swfsize"):
            probe_args += ["--swfsize", get("swfsize")]

        if get("player_url"):
            probe_args += ["--swfVfy", get("player_url")]
        elif get("swfVfy"):
            probe_args += ["--swfVfy", get("player_url")]

        if get("swfAge"):
            probe_args += ["--swfAge", get("swfAge")]

        self.common.log("Done: " + repr(probe_args))
        return probe_args

    def _detectStream(self, filename, item):
        get = item.get
        self.common.log(get("url"))

        # RTMPDump
        if get("url").find("rtmp") > -1 or get("use_rtmpdump"):
            self.common.log("Trying rtmpdump")
            # Detect filesize
            probe_args = [self.rtmp_binary, "--stop", "1"]

            probe_args = self._rtmpDetectArgs(probe_args, item)

            proc = self._runCommand(probe_args)
            if proc:
                output = ""
                now = time.time()
                while not proc.poll():
                    temp_output = self._readPipe(proc)
                    output += temp_output
                    if now + 15 < time.time() or output.find("Starting") > -1:
                        self.common.log("Breaking, duration: " + repr(time.time() - now))
                        break

                if output.find("Starting") > -1:  # If download actually started
                    if output.find("filesize") > -1:
                        item["total_size"] = int(float(output[output.find("filesize") + len("filesize"):output.find("\n", output.find("filesize"))]))
                    elif get("live"):
                        item["total_size"] = 0

                    cmd_call = self._rtmpDetectArgs([self.rtmp_binary], item)

                    cmd_call += ["--flv", item["path_incomplete"]]
                    item["cmd_call"] = cmd_call

                try:
                    proc.kill()
                except:
                    pass

        # VLC
        # Fix getting filesize
        if ("total_size" not in item and "cmd_call" not in item) or get("use_vlc"):
            self.common.log("Trying vlc")
            # Detect filesize
            probe_args = [self.vlc_binary, "-I", "dummy", "-v", "-v", "--stop-time", "1", "--sout", "file/avi:" + item["path_incomplete"], item["url"], "vlc://quit"]

            proc = self._runCommand(probe_args)
            if proc:
                output = ""
                now = time.time()
                while not proc.poll():
                    temp_output = self._readPipe(proc)
                    output += temp_output
                    if now + 15 < time.time() or output.find(get("url") + "' successfully opened") > -1:
                        self.common.log("Breaking, duration: " + repr(time.time() - now))
                        break

                if output.find(get("url") + "' successfully opened") > -1:
                    if output.find("media_length:") > -1 and False:
                        item["total_size"] = int(float(output[output.find("media_length:") + len("media_length:"):output.find("s", output.find("media_length:"))]))
                    elif get("live"):
                        item["total_size"] = 0

                    # Download args
                    cmd_call = [self.vlc_binary, "-v", "-v", "-I", "dummy", "--sout", "file/avi:" + get("path_incomplete")]

                    if "duration" in item:
                        cmd_call += ["--stop-time", str(get("duration"))]

                    cmd_call += [get("url"), "vlc://quit"]
                    item["cmd_call"] = cmd_call

                try:
                    proc.kill()
                except:
                    pass

        # Mplayer
        # -endpos doesn't work with dumpstream.
        if ("total_size" not in item and "cmd_call" not in item) or get("use_mplayer"):
            self.common.log("Trying mplayer")
            # Detect filesize
            probe_args = [self.mplayer_binary, "-v", "-endpos", "1", "-vo", "null", "-ao", "null", get("url")]

            proc = self._runCommand(probe_args)
            if proc:
                output = ""
                now = time.time()
                while not proc.poll():
                    temp_output = self._readPipe(proc)
                    output += temp_output
                    if now + 15 < time.time() or output.find("Starting playback") > -1:
                        self.common.log("Breaking, duration: " + repr(time.time() - now))
                        break

                if output.find("Starting playback") > -1:
                    if output.find("filesize") > -1:
                        item["total_size"] = int(float(output[output.find("filesize: ") + len("filesize: "):output.find("\n", output.find("filesize: "))]))
                    elif get("live"):
                        item["total_size"] = 0

                    item["cmd_call"] = [self.mplayer_binary, "-v", "-dumpstream", "-dumpfile", item["path_incomplete"], get("url")]

                try:
                    proc.kill()
                except:
                    pass

        if not "total_size" in item:
            item["total_size"] = 0

    def _stopCurrentDownload(self):
        self.common.log("")
        if "proc" in self.cur_dl:
            self.common.log("Killing: " + repr(self.cur_dl))
            proc = self.cur_dl["proc"]
            try:
                proc.kill()
                self.common.log("Killed")
            except:
                self.common.log("Couldn't kill")
        self.common.log("Done")

    def _downloadStream(self, filename, item):
        get = item.get
        self.common.log(filename)
        self.common.log(get("cmd_call"))


        same_bytes_count = 0
        retval = 1

        params = {"bytes_so_far": 0, "mark": 0.0, "queue_mark": 0.0, "obytes_so_far": 0}
        item["percent"] = 0.1
        item["old_percent"] = -1
        delay = 0.3
        stall_timeout = self.settings.getSetting("stall_timeout")
        proc = self._runCommand(get("cmd_call"))
        output = ""
        if proc:
            while proc.returncode == None and "quit" not in params:
                temp_output = proc.stdout.read(23) 
                if len(output) > 10000:
                    output = output[0:500] + "\r\n\r\n\r\n"
                output += temp_output

                if self.xbmcvfs.exists(item["path_incomplete"]):
                    params["bytes_so_far"] = os.path.getsize(item["path_incomplete"])
                    if params["mark"] == 0.0 and params["bytes_so_far"] > 0:
                        params["mark"] = time.time()
                        self.common.log("Mark set")

                if params["bytes_so_far"] == params["obytes_so_far"]:
                    if same_bytes_count == 0:
                        now = time.time()
                    same_bytes_count += 1
                    #if delay < 3:
                    #    delay = delay * 1.2

                    if same_bytes_count >= 300 and (item["total_size"] != 0 or params["bytes_so_far"] != 0) and (now + int(stall_timeout) < time.time()):
                        self.common.log("Download complete. Same bytes for 300 times in a row.")
                        if (item["total_size"] > 0 and item["total_size"] * 0.998 < params["bytes_so_far"]):
                            self.common.log("Size disrepancy: " + str(item["total_size"] - params["bytes_so_far"]))
                        retval = 0
                        break
                    else:
                        self.common.log("Sleeping: " + str(delay) + " - " + str(params["bytes_so_far"]), 5)
                        time.sleep(delay)
                        continue
                else:
                    same_bytes_count = 0
                    #if delay > 0.3:
                    #    delay = delay * 0.8
                    self.common.log("Bytes updated: " + str(delay) + " - " + str(params["bytes_so_far"]), 5)

                self.common.log("bytes_so_far : " + str(params["bytes_so_far"]), 5)

                self._generatePercent(item, params)

                if "duration" in item and repr(get("cmd_call")).find("mplayer") > -1 and item["percent"] > 105:
                    self.common.log("Mplayer over percentage %s. Killing! " % repr(item["percent"]))
                    retval = 0
                    proc.kill()
                    break
     
                if item["percent"] > item["old_percent"] or time.time() - params["queue_mark"] > 3:
                    self._updateProgress(filename, item, params)
                    item["old_percent"] = item["percent"]

                if params["bytes_so_far"] >= item["total_size"] and item["total_size"] != 0:
                    self.common.log("Download complete. Matched size")
                    retval = 0
                    break

                if "duration" in item and params["mark"] > 0.0 and (params["mark"] + int(get("duration")) + 10 < time.time()) and False:
                    self.common.log("Download complete. Over duration.")
                    retval = 0
                    break

                # Some rtmp streams seem abort after ~ 99.8%. Don't complain for those.
                if (item["total_size"] != 0 and get("url").find("rtmp") > -1 and item["total_size"] * 0.998 < params["bytes_so_far"]):
                    self.common.log("Download complete. Size disrepancy: " + str(item["total_size"] - params["bytes_so_far"]) + " - " + str(same_bytes_count))
                    retval = 0
                    break

                params["obytes_so_far"] = params["bytes_so_far"]
            
            try:
                output += proc.stdout.read()
                proc.kill()
            except:
                pass

        if "quit" in params:
            self.common.log("Download aborted.")
            return 300
        if retval == 1:
            self.common.log("Download failed, binary output: %s" % output)
            return 500

        self.common.log("Done")
        return 200

    def _downloadURL(self, filename, item):
        self.common.log(filename)

        url = urllib2.Request(item["url"])
        if "useragent" in item:
            url.add_header("User-Agent", item["useragent"])
        else:
            url.add_header("User-Agent", self.common.USERAGENT)
        if "cookie" in item:
            if item["cookie"]!=False  :
                url.add_header("Cookie", item["cookie"])
        
        file = self.common.openFile(item["path_incomplete"], "wb")
        con = urllib2.urlopen(url)

        item["total_size"] = 0
        chunk_size = 1024 * 8

        if con.info().getheader("Content-Length").strip():
            item["total_size"] = int(con.info().getheader("Content-Length").strip())

        params = {"bytes_so_far": 0, "mark": 0.0, "queue_mark": 0.0, "obytes_so_far": 0}
        item["percent"] = 0.1
        item["old_percent"] = -1
        try:
            while "quit" not in params:
                chunk = con.read(chunk_size)
                file.write(chunk)
                params["bytes_so_far"] += len(chunk)

                if params["mark"] == 0.0 and params["bytes_so_far"] > 0:
                    params["mark"] = time.time()
                    self.common.log("Mark set")

                self._generatePercent(item, params)

                self.common.log("recieved chunk: %s - %s" % ( repr(item["percent"] > item["old_percent"]), repr(time.time() - params["queue_mark"])), 4)
                if item["percent"] > item["old_percent"] or time.time() - params["queue_mark"] > 30:
                    self._run_async(self._updateProgress(filename, item, params))

                    item["old_percent"] = item["percent"]

                params["obytes_so_far"] = params["bytes_so_far"]

                if not chunk:
                    break
            self.common.log("Loop done")

            con.close()
            file.close()
        except:
            self.common.log("Download failed.")
            try:
                con.close()
            except:
                self.common.log("Failed to close download stream")

            try:
                file.close()
            except:
                self.common.log("Failed to close file handle")

            self._showMessage(self.language(204), "ERROR")
            return 500

        if "quit" in params:
            self.common.log("Download aborted.")
            return 300

        self.common.log("Done")
        return 200

    def _convertSecondsToHuman(self, seconds):
        seconds = int(seconds)
        if seconds < 60:
            return "~%ss" % (seconds)
        elif seconds < 3600:
            return "~%sm" % (seconds / 60)

    def _generatePercent(self, item, params):
        self.common.log("", 5)
        get = params.get
        iget = item.get

        new_delta = False
        if "last_delta" in item:
            if time.time() - item["last_delta"] > 0.2:
                new_delta = True
        else:
            item["last_delta"] = 0.0
            new_delta = True

        if item["total_size"] > 0 and new_delta:
            self.common.log("total_size", 5)
            item["percent"] = float(get("bytes_so_far")) / float(item["total_size"]) * 100
        elif iget("duration") and get("mark") != 0.0 and new_delta:
            time_spent = time.time() - get("mark")
            item["percent"] = time_spent / int(iget("duration")) * 100
            self.common.log("Time spent: %s. Duration: %s. Time left: %s (%s)" % (int(time_spent), int(iget("duration")),
                                                                                  int(int(iget("duration")) - time_spent),
                                                                                  self._convertSecondsToHuman(int(iget("duration")) - time_spent)), 5)

        elif new_delta:
            self.common.log("cycle - " + str(time.time() - item["last_delta"]), 5)
            delta = time.time() - item["last_delta"]
            if delta > 10 or delta < 0:
                delta = 5

            item["percent"] = iget("old_percent") + delta
            if item["percent"] >= 100:
                item["percent"] -= 100
                item["old_percent"] = item["percent"]

        if new_delta:
            item["last_delta"] = time.time()

    def _getQueue(self):
        self.common.log("")
        queue = self.cache.get("SimpleDownloaderQueue")

        try:
                items = eval(queue)
        except:
            items = {}

        self.common.log("Done: " + str(len(items)))
        return items

    def _updateProgress(self, filename, item, params):
        self.common.log("", 3)
        get = params.get
        iget = item.get
        queue = False
        new_mark = time.time()

        if new_mark == get("mark"):
            speed = 0
        else:
            speed = int((get("bytes_so_far") / 1024) / (new_mark - get("mark")))

        if new_mark - get("queue_mark") > 1.5:
            queue = self.cache.get("SimpleDownloaderQueue")
            self.queue = queue
        elif hasattr(self, "queue"):
            queue = self.queue

        self.common.log("eval queue", 2)

        try:
            items = eval(queue)
        except:
            items = {}

        if new_mark - get("queue_mark") > 1.5:
            heading = u"[%s] %sKb/s (%.2f%%)" % (len(items), speed, item["percent"])
            self.common.log("Updating %s - %s" % (heading, self.common.makeUTF8(filename)), 2)
            params["queue_mark"] = new_mark

        if self.xbmc.Player().isPlaying() and self.xbmc.getCondVisibility("VideoPlayer.IsFullscreen"):
            if self.dialog:
                self.dialog.close()
                self.dialog = u""
        else:
            if not self.dialog:
                self.dialog = DialogDownloadProgress.DownloadProgress()
                self.dialog.create(self.language(201), "")

            heading = u"[%s] %s - %.2f%%" % (len(items), self.language(202), item["percent"])

            if iget("Title"):
                self.dialog.update(percent=item["percent"], heading=heading, label=iget("Title"))
            else:
                self.dialog.update(percent=item["percent"], heading=heading, label=filename)
        self.common.log("Done", 3)

    #============================= Download Queue =================================
    def _getNextItemFromQueue(self):
        if self.cache.lock("SimpleDownloaderQueueLock"):
            items = []

            queue = self.cache.get("SimpleDownloaderQueue")
            self.common.log("queue loaded : " + repr(queue))

            if queue:
                try:
                    items = eval(queue)
                except:
                    items = False

                item = {}
                if len(items) > 0:
                    item = items[0]
                    self.common.log("returning : " + item[0])

                self.cache.unlock("SimpleDownloaderQueueLock")
                if items:
                    return item
                else:
                    return False
            else:
                self.common.log("Couldn't aquire lock")

    def _addItemToQueue(self, filename, params={}):
        if self.cache.lock("SimpleDownloaderQueueLock"):

            items = []
            if filename:
                queue = self.cache.get("SimpleDownloaderQueue")
                self.common.log("queue loaded : " + repr(queue), 3)

                if queue:
                    try:
                        items = eval(queue)
                    except:
                        items = []

                append = True
                for index, item in enumerate(items):
                    (item_id, item) = item
                    if item_id == filename:
                        append = False
                        del items[index]
                        break

                if append:
                    items.append((filename, params))
                    self.common.log("Added: " + filename + " to queue - " + str(len(items)))
                else:
                    items.insert(1, (filename, params)) # 1 or 0?
                    self.common.log("Moved " + filename + " to front of queue. - " + str(len(items)))

                self.cache.set("SimpleDownloaderQueue", repr(items))

                self.cache.unlock("SimpleDownloaderQueueLock")
                self.common.log("Done")
        else:
            self.common.log("Couldn't lock")

    def _removeItemFromQueue(self, filename):
        if self.cache.lock("SimpleDownloaderQueueLock"):
            items = []

            queue = self.cache.get("SimpleDownloaderQueue")
            self.common.log("queue loaded : " + repr(queue), 3)

            if queue:
                try:
                    items = eval(queue)
                except:
                    items = []

                for index, item in enumerate(items):
                    (item_id, item) = item
                    if item_id == filename:
                        del items[index]
                        self.cache.set("SimpleDownloaderQueue", repr(items))
                        self.common.log("Removed: " + filename + " from queue")

                self.cache.unlock("SimpleDownloaderQueueLock")
                self.common.log("Done")
            else:
                self.common.log("Exception")

    def movieItemToPosition(self, filename, position):
        if position > 0 and  self.cache.lock("SimpleDownloaderQueueLock"):
            items = []
            if filename:
                queue = self.cache.get("SimpleDownloaderQueue")
                self.common.log("queue loaded : " + repr(queue), 3)

                if queue:
                    try:
                        items = eval(queue)
                    except:
                        items = []

                    self.common.log("pre items: %s " % repr(items), 3)
                    for index, item in enumerate(items):
                        (item_id, item) = item
                        if item_id == filename:
                            print "FOUND ID"
                            del items[index]
                            items = items[:position] + [(filename, item)] + items[position:]
                            break
                    self.common.log("post items: %s " % repr(items), 3)

                    self.cache.set("SimpleDownloaderQueue", repr(items))

                    self.cache.unlock("SimpleDownloaderQueueLock")
                    self.common.log("Done")
        else:
            self.common.log("Couldn't lock")

    def isRTMPInstalled(self):
        basic_args = ["rtmpdump", "-V"]

        try:
            p = subprocess.Popen(basic_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = p.communicate()[1]
            return output.find("RTMPDump") > -1
        except:
            return False

    def isVLCInstalled(self):
        basic_args = ["vlc", "--version"]

        try:
            p = subprocess.Popen(basic_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = p.communicate()[0]
            self.common.log(repr(output))
            return output.find("VLC") > -1
        except:
            return False

    def isMPlayerInstalled(self):
        basic_args = ["mplayer"]

        try:
            p = subprocess.Popen(basic_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = p.communicate()[0]
            self.common.log(repr(output))
            return output.find("MPlayer") > -1
        except:
            return False

    def _run_async(self, func, *args, **kwargs):
        from threading import Thread
        worker = Thread(target=func, args=args, kwargs=kwargs)
        self.__workersByName[worker.getName()] = worker
        worker.start()
        return worker

    # Shows a more user-friendly notification
    def _showMessage(self, heading, message):
        self.xbmc.executebuiltin((u'XBMC.Notification("%s", "%s", %s)' % (heading, self.common.makeUTF8(message), self.notification_length)).encode("utf-8"))
