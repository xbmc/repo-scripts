# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
#
# The Original Code is plugin.games.xbmame.
#
# The Initial Developer of the Original Code is Olivier LODY aka Akira76.
# Portions created by the XBMC team are Copyright (C) 2003-2010 XBMC.
# All Rights Reserved.

from os import path, popen, listdir
from re import *

from Constants import *
from GameItem import *

from xbmcgui import *

class MameImport:

    def __init__(self, xbmame):
        __settings__ = xbmame.__settings__
        __language__ = xbmame.__settings__.getLocalizedString
	db = xbmame._db
        progress = DialogProgress()
        db.setSetting("database-version", DB_VERSION)
        db.dropTable("Games")
        db.dropTable("BiosSets")
        db.dropTable("Dipswitches")
        db.dropTable("DipswitchesValues")
        db.execute("CREATE TABLE Games (id INTEGER PRIMARY KEY, romset TEXT, cloneof TEXT, romof TEXT, biosset TEXT, driver TEXT, gamename TEXT, gamecomment TEXT, manufacturer TEXT, year TEXT, isbios BOOLEAN, hasdisk BOOLEAN, isworking BOOLEAN, emul BOOLEAN, color BOOLEAN, graphic BOOLEAN, sound BOOLEAN, hasdips BOOLEAN, view INTEGER, rotate INTEGER, backdrops BOOLEAN, overlays BOOLEAN, bezels BOOLEAN, zoom BOOLEAN, have BOOLEAN, thumb BOOLEAN, history INTEGER, info INTEGER)")
        db.execute("CREATE TABLE BiosSets (id INTEGER PRIMARY KEY, romset_id INTEGER, name TEXT, description TEXT)")
        db.execute("CREATE TABLE Dipswitches (id INTEGER PRIMARY KEY, romset_id integer, name TEXT, tag TEXT, mask INTEGER, defvalue INTEGER, value INTEGER)")
        db.execute("CREATE TABLE DipswitchesValues (id INTEGER PRIMARY KEY, dipswitch_id INTEGER, name TEXT, value TEXT)")
        db.commit()
        pstep = 0
        psteps = 3
        xbmame._mameinfo_dat.dropTable()
        xbmame._history_dat.dropTable()
        if xbmame._mameinfo_dat.data:psteps+=1
        if xbmame._history_dat.data:psteps+=1
#        xbmcgui.unlock()
        progress.create(__language__(30000))
        pstep += 1
        progress.update((pstep-1)*10, __language__(30604), __language__(30605) % (pstep, psteps),  __language__(30606))
        import commands
        xml = popen(__settings__.getSetting("mame_exe_path").replace("\\", "/") + " -listxml").read()
        pstep += 1
        progress.update((pstep-1)*10, __language__(30604), __language__(30605) % (pstep, psteps),  __language__(30607))
        if not progress.iscanceled():
            xml = sub("\r|\t|\n|<rom.*?/>", "", xml)
            if not progress.iscanceled():
                files = {}
                tmpfiles = listdir(__settings__.getSetting("mame_rom_path").replace("\\", "/"))
                for file in tmpfiles:files[file.replace(".zip", "").replace(".rar", "").replace(".7z","")] = 1
                items = findall("(<game.*?>.*?</game>)", xml, M)
                pstep += 1
                count = len(items)
                progress.update((pstep-1)*10, __language__(30604), __language__(30605) % (pstep, psteps),  __language__(30610) % (0, count))
                step = 0
                index = 0
                for item in items:
                    if progress.iscanceled(): break
                    index += 1
                    game = GameItem(db, xml=item)
                    try:
                        if files[str(game.romset)]:game.have = 1
                    except KeyError:
                        game.have = 0
                    game.writeDB()
                    if index==count/((11-psteps)*2):
                        step+=1
                        index=0
                        db.commit()
                        progress.update((pstep-1)*10+step*5, __language__(30604), __language__(30605) % (pstep, psteps), __language__(30610) % (step*count/((11-psteps)*2), count))
                if xbmame._mameinfo_dat.data:
                    pstep += 1
                    progress.update((pstep-2)*10+step*5, __language__(30604), __language__(30605) % (pstep, psteps),  __language__(30608))
                    xbmame._mameinfo_dat.parse()
                    db.commit()
                if xbmame._history_dat.data:
                    pstep += 1
                    progress.update((pstep-2)*10+step*5, __language__(30604), __language__(30605) % (pstep, psteps),  __language__(30609))
                    xbmame._history_dat.parse()
                    db.commit()
        db.commit()
        progress.close()

class InfoFile(object):

    def __init__(self, db, mamepath=""):
        self._db = db
        self.createTable()
        datpath1 = path.join(mamepath, "mameinfo.dat")
        datpath2 = path.join(mamepath, "inp", "mameinfo.dat")
        data = ""
        if mamepath:
            if path.exists(datpath1):
                file = open(datpath1)
                data = file.read()
                file.close()
            elif path.exists(datpath2):
                file = open(datpath2)
                data = file.read()
                file.close()
        self.data = data.decode("iso-8859-1")

    def parse(self):
        self.dropTable()
        self.createTable()
        data = re.sub("\r\n", "&&", self.data)
        items = re.findall("(\$info=.*?\$end)", data , re.S+re.M)
        for item in items:
            InfoItem(self._db, data=item).writeDB()
        self._db.commit()

    def dropTable(self):
        self._db.dropTable("MameInfo")

    def createTable(self):
        if not self._db.tableExists("MameInfo"):
            self._db.execute("CREATE TABLE MameInfo (id INTEGER PRIMARY KEY, testmode TEXT, note TEXT, setup TEXT, levels TEXT, romsetinfo TEXT, todo TEXT, bugs TEXT, wip TEXT, otheremu TEXT, games TEXT, driver BOOL, samples BOOL, artwork BOOL)")

class InfoItem(object):

    def __init__(self, db, data="", id=""):
        self._db = db
        self.romset=""
        self.testmode=""
        self.note=""
        self.setup=""
        self.levels=""
        self.romsetinfo=""
        self.todo=""
        self.bugs=""
        self.wip=""
        self.otheremu=""
        self.games=""
        self.driver = False
        self.samples = False
        self.artwork = False
        if data:self.fromData(data)
        elif id:self.fromDB(id)

    def writeDB(self):
        id = self._db.execute("INSERT INTO MameInfo VALUES (null, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (self.testmode, self.note, self.setup, self.levels, self.romsetinfo, self.todo,
            self.bugs, self.wip, self.otheremu, self.games, self.driver, self.samples, self.artwork,))
        self._db.execute("UPDATE Games SET info=? WHERE romset=? or romof=?", (id, self.romset, self.romset))

    def fromDB(self, id):
        sql = "SELECT testmode, note, setup, levels, romsetinfo, todo, bugs, wip, otheremu, games, driver, samples, artwork FROM MameInfo WHERE id=?"
        results = self._db.Query(sql, (id,))
        for data in results:
            self.testmode=data[0]
            self.note=data[1]
            self.setup=data[2]
            self.levels=data[3]
            self.romsetinfo=data[4]
            self.todo=data[5]
            self.bugs=data[6]
            self.wip=data[7]
            self.otheremu=data[8]
            self.games=data[9]
            self.driver=data[10]
            self.samples=data[11]
            self.artwork=data[12]

    def fromData(self, data):
        try:
            self.romset = re.findall("\$info=(.*?)&&", data)[0].strip()
        except IndexError:
            pass
        try:
            self.testmode = re.findall("TEST MODE:(.*?)&&&&&&", data)[0].replace("&&&&", "\n").strip()
        except IndexError:
            pass
        try:
            self.note = re.findall("NOTE:(.*?)&&&&&&", data)[0].replace("&&&&", "\n").strip()
        except IndexError:
            pass
        try:
            self.setup = re.findall("SETUP:(.*?)&&&&&&", data)[0].replace("&&&&", "\n").strip()
        except IndexError:
            pass
        try:
            self.levels = re.findall("LEVELS:(.*?)&&&&", data)[0].strip()
        except IndexError:
            pass
        try:
            self.romsetinfo = re.findall("Romset:(.*?)&&&&", data)[0].strip()
        except IndexError:
            pass
        self.driver = bool(re.search("(\$drv)", data))
        self.samples = bool(re.search("(Samples required)", data))
        self.artwork = bool(re.search("(Artwork available)", data))
        try:
            self.todo = re.findall("TODO:&&&&(.*?)&&&&&&", data)[0].replace("&&&&", "\n").strip().replace("* ", "")
        except IndexError:
            pass
        try:
            self.bugs = re.findall("Bugs:&&&&(.*?)&&&&&&", data)[0].replace("&&&&", "\n").strip().replace("- ", "")
        except IndexError:
            pass
        try:
            self.wip = re.findall("WIP:&&&&(.*?)&&&&&&", data)[0].replace("&&&&", "\n").strip().replace("- ", "")
        except IndexError:
            pass
        try:
            self.otheremu = re.findall("Other Emulators:&&&&(.*?)&&&&&&", data)[0].replace("&&&&", "\n").replace("* ", "").strip()
        except IndexError:
            pass
        try:
            relatedgames = re.findall("Recommended Games.*?:&&&&(.*?)&&&&&&", data)
            for games in relatedgames:
                self.games += re.sub(".\((.*?)\)", "", games.replace("&&&&", ",").strip())
        except IndexError:
            pass

class HistoryFile(object):

    def __init__(self, db, mamepath=""):
        self._db = db
        self.createTable()
        data = ""
        if mamepath:
            datpath1 = path.join(mamepath, "history.dat")
            datpath2 = path.join(mamepath, "inp", "history.dat")
            if path.exists(datpath1):
                file = open(datpath1)
                data = file.read()
                file.close()
            elif path.exists(datpath2):
                file = open(datpath2)
                data = file.read()
                file.close()
        self.data = data.decode("iso-8859-1")

    def parse(self):
        self.dropTable()
        self.createTable()
        data = re.sub("\r\n", "&&", self.data)
        items = re.findall("(\$info=.*?\$end)", data , re.S+re.M)
        for item in items:
            HistoryItem(self._db, data=item).writeDB()
        self._db.commit()

    def dropTable(self):
        self._db.dropTable("MameHistory")

    def createTable(self):
        if not self._db.tableExists("MameHistory"):
            self._db.execute("CREATE TABLE MameHistory (id INTEGER PRIMARY KEY, bio TEXT, technical TEXT, trivia TEXT, scoring TEXT, updates TEXT, tips TEXT, series TEXT, staff TEXT, ports TEXT, sources TEXT)")

class HistoryItem(object):

    def __init__(self, db, data="", id=0):
        self._db = db
        self.romsets=""
        self.bio=""
        self.trivia=""
        self.technical=""
        self.scoring=""
        self.updates=""
        self.tips=""
        self.series=""
        self.staff=""
        self.ports=""
        self.sources = ""
        if data:self.fromData(data)
        elif id:self.fromDB(id)

    def writeDB(self):
        id = self._db.execute("INSERT INTO MameHistory VALUES (null, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (self.bio, self.technical, self.trivia, self.scoring, self.updates, self.tips,
            self.series, self.staff, self.ports, self.sources,))
        self._db.execute("UPDATE Games SET history=? WHERE romset IN (%s)" % self.romsets, (id,))

    def fromData(self, data):
        try:
            romsets = re.findall("\$info=(.*?),&&", data)[0].strip().split(",")
            for romset in romsets:
                self.romsets += "'%s'," % romset
            self.romsets = self.romsets[0:len(self.romsets)-1]

        except IndexError:
            pass
        try:
            self.bio = re.findall("\$bio(.*?)(\$end|- .* -)", data)[0][0].replace("&&&&", "\n").strip().replace("&&", "")
        except IndexError:
            pass
        try:
            self.technical = re.findall("- TECHNICAL -(.*?)(\$end|- .* -)", data)[0][0].replace("&&&&", "\n").strip().replace("&&", "")
        except IndexError:
            pass
        try:
            self.trivia = re.findall("- TRIVIA -(.*?)(\$end|- .* -)", data)[0][0].replace("&&&&", "\n").strip().replace("&&", "")
        except IndexError:
            pass
        try:
            self.scoring = re.findall("- SCORING -(.*?)(\$end|- .* -)", data)[0][0].replace("&&&&", "\n").strip().replace("&&", "")
        except IndexError:
            pass
        try:
            self.updates = re.findall("- UPDATES -(.*?)(\$end|- .* -)", data)[0][0].replace("&&&&", "\n").strip().replace("&&", "")
        except IndexError:
            pass
        try:
            self.tips = re.findall("- TIPS AND TRICKS -(.*?)(\$end|- .* -)", data)[0][0].replace("&&&&", "\n").strip().replace("&&", "")
        except IndexError:
            pass
        try:
            self.series = re.findall("- SERIES -(.*?)(\$end|- .* -)", data)[0][0].replace("&&&&", "\n").strip().replace("&&", "")
        except IndexError:
            pass
        try:
            self.staff = re.findall("- STAFF -(.*?)(\$end|- .* -)", data)[0][0].replace("&&&&", "\n").strip().replace("&&", "")
        except IndexError:
            pass
        try:
            self.ports = re.findall("- PORTS -(.*?)(\$end|- .* -)", data)[0][0].replace("&&&&", "\n").strip().replace("&&", "").replace("* ", "")
        except IndexError:
            pass
        try:
            self.sources = re.findall("- SOURCES -(.*?)(\$end|- .* -)", data)[0][0].replace("&&&&", "\n").strip().replace("&&", "")
        except IndexError:
            pass
        return self

    def fromDB(self, id):
        sql = "SELECT bio, technical, trivia, scoring, updates, tips, series, staff, ports, sources FROM MameHistory WHERE id=?"
        results = self._db.Query(sql, (id,))
        for data in results:
            self.bio=data[0]
            self.technical=data[1]
            self.trivia=data[2]
            self.scoring=data[3]
            self.updates=data[4]
            self.tips=data[5]
            self.series=data[6]
            self.staff=data[7]
            self.ports=data[8]
            self.sources=data[9]
        return self

    def isEmpty(self):
        return not(self.bio or self.technical or self.trivia or self.scoring or\
        self.updates or self.tips or self.series or self.staff or self.ports or self.sources)
