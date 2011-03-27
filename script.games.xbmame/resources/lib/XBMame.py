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

from os import path, makedirs, remove
from shutil import *
from urllib import *
from DBHelper import DBHelper
from Constants import *
from InfoDialog import *
from MameImport import *
from ContextMenu import *
from xbmc import *
from xbmcgui import *
from xbmcaddon import *

dialog = xbmcgui.Dialog()

class XBMame:

    def __init__(self, ADDON_ID, arg):
        self.__settings__ = Addon(ADDON_ID)
        self.__language__ = Addon(ADDON_ID).getLocalizedString
        self.__profile__ = Addon(ADDON_ID).getAddonInfo("profile")

	self.MEDIA_PATH = path.join(Addon(ADDON_ID).getAddonInfo("path"), "resources", "skins", "Default", "media")
	self._MAME_CONFIG_PATH = translatePath(path.join(self.__profile__, "cfg"))
        self._MAME_NVRAM_PATH = translatePath(path.join(self.__profile__, "nvram"))
        if not path.exists(self._MAME_CONFIG_PATH): makedirs(self._MAME_CONFIG_PATH)
        self._MAME_CACHE_PATH = translatePath(path.join(self.__profile__, "titles"))
        if not path.exists(self._MAME_CACHE_PATH): makedirs(self._MAME_CACHE_PATH)

        SETTINGS_PLUGIN_ID = "%s.settings" % ADDON_ID
        SETTINGS_PLUGIN_PATH = path.join(path.dirname(Addon(ADDON_ID).getAddonInfo("path")), SETTINGS_PLUGIN_ID)
        try:
            Addon(SETTINGS_PLUGIN_ID)
	    self.SETTINGS_PLUGIN_ID=SETTINGS_PLUGIN_ID
	except Exception:
            if not path.exists(path.join(SETTINGS_PLUGIN_PATH, "resources")): makedirs(path.join(SETTINGS_PLUGIN_PATH, "resources"))
            plugin = open(path.join(SETTINGS_PLUGIN_PATH, "addon.xml"), "w")
            plugin.write("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?><addon id=\"%s\" name=\"DIP Switches\"><extension point=\"xbmc.python.library\" library=\"default.py\" />  <extension point=\"xbmc.addon.metadata\"><platform>all</platform><summary></summary><description></description></extension></addon>" % SETTINGS_PLUGIN_ID)
            plugin.close()
            dialog.ok(self.__language__(30000), self.__language__(30704), self.__language__(30705))
            executebuiltin("RestartApp")

        self._FILTERS = ""
        
        if not path.exists(self.__profile__): makedirs(self.__profile__)

	self._MAME_DATABASE_PATH = translatePath(path.join(self.__settings__.getAddonInfo("profile"), "XBMame.db"))
        self._db = DBHelper(self._MAME_DATABASE_PATH)

        self.getSettings()

        while self._MAME_EXE_PATH=="":
            self.__settings__.openSettings()
            self.getSettings()

	command = arg.split(":")

	if command[0]=="exec": self.execute(command[1:])
	else:
	    if self._db.isEmpty():MameImport(self)
            dbver = self._db.getSetting("database-version")
	    if dbver=="":dbver="1.0"
	    if dbver!=DB_VERSION:
                dialog.ok(self.__language__(30600), self.__language__(30620), self.__language__(30621) % (dbver, DB_VERSION), self.__language__(30622))
		MameImport(self)
	    if len(command)==1:Path="/"
	    else: Path = "/%s" % command[1]
            XBMameGUI("XBMame.xml", self.__settings__.getAddonInfo("path"), "default", "720p", Plugin=self, Path=Path)

    def getSettings(self):
	    self._MAME_PARAMS = {}
	    self._FILTERS = ""
    # Fetching settings

        # General settings
            self._MAME_EXE_PATH = self.__settings__.getSetting("mame_exe_path").replace("\\", "/")
            self._MAME_ROM_PATH = self.__settings__.getSetting("mame_rom_path").replace("\\", "/")
            self._MAME_SAMPLES_PATH = self.__settings__.getSetting("mame_samples_path").replace("\\", "/")
            self._USE_MAMEINFO = self.__settings__.getSetting("mame_mameinfo")=="true"
            self._USE_HISTORY = self.__settings__.getSetting("mame_history")=="true"

        # Thumbnails settings
            self._MAME_TITLES_PATH = self.__settings__.getSetting("mame_titles_path").replace("\\", "/")
            self._CACHE_TITLES = self.__settings__.getSetting("cache_titles")=="true"
            self._ONLINE_TITLES = self.__settings__.getSetting("online_titles")=="true"
            self._HIRES_TITLES = self.__settings__.getSetting("hires_titles")=="true"
            self._ROMSET_TITLES = self.__settings__.getSetting("romset_titles")=="true"

        # ROM filters
            if self.__settings__.getSetting("hide_clones")=="true":self._FILTERS +=" AND cloneof=''"
            if self.__settings__.getSetting("hide_nothave")=="true":self._FILTERS += " AND have"
            if self.__settings__.getSetting("hide_notworking")=="true":self._FILTERS += " AND isworking"
            if self.__settings__.getSetting("hide_impemul")=="true":self._FILTERS += " AND emul"
            if self.__settings__.getSetting("hide_impcolor")=="true":self._FILTERS += " AND color"
            if self.__settings__.getSetting("hide_graphics")=="true":self._FILTERS += " AND graphic"
            if self.__settings__.getSetting("hide_impsound")=="true":self._FILTERS += " AND sound"

    # Emulator settings

        # Video related
            if self.__settings__.getSetting("mame_video")=="Direct3D":
                self._MAME_PARAMS["-video"] = "d3d"
                self._MAME_PARAMS["-d3dversion"] = self.__settings__.getSetting("mame_d3dversion")
            if self.__settings__.getSetting("mame_video")=="DirectDraw":self._MAME_PARAMS["-video"] = "ddraw"
            if self.__settings__.getSetting("mame_video")=="GDI":self._MAME_PARAMS["-video"] = "gdi"
            if self.__settings__.getSetting("mame_switchres")=="true": self._MAME_PARAMS["-switchres"] = ""
            if self.__settings__.getSetting("mame_filter")=="true": self._MAME_PARAMS["-filter"] = ""
            if self.__settings__.getSetting("mame_scanlines")=="true": self._MAME_PARAMS["-effect"] = "scanlines.png"

        # Other settings
            if self.__settings__.getSetting("mame_multithread")=="true": self._MAME_PARAMS["-multithreading"] = ""
            if self.__settings__.getSetting("mame_cheat")=="true": self._MAME_PARAMS["-waitvsync"] = ""
            if self.__settings__.getSetting("mame_gameinfo")=="false": self._MAME_PARAMS["-skip_gameinfo"] = ""

            if self._USE_MAMEINFO:
                self._mameinfo_dat = InfoFile(self._db, path.dirname(self._MAME_EXE_PATH))
            else:
                self._mameinfo_dat = InfoFile(self._db)
            if self._USE_HISTORY:
                self._history_dat = HistoryFile(self._db, path.dirname(self._MAME_EXE_PATH))
            else:
                self._history_dat = HistoryFile(self._db)

	    self.TITLES_PATH = ""
	    if self._MAME_TITLES_PATH:
		if self._MAME_CACHE_PATH:
		    self.TITLES_PATH = self._MAME_CACHE_PATH
                else:
                    self.TITLES_PATH = self._MAME_TITLES_PATH
	    elif self._MAME_CACHE_PATH:
		self.TITLES_PATH = self._MAME_CACHE_PATH
            try:
		self.GUI.populateList(self.browse(self.GUI.path))
	    except AttributeError:
		pass
	    
    def execute(self, args):
	print args
	if args[0]=="builddb":MameImport(self)
        elif args[0]=="config":
            if len(args)==1:
                self.__settings__.openSettings()
            else:
		self._gameSettings(args[1])
            self.getSettings()
	elif args[0]=="buildthumb":
	    self._thumbNails()
            try:
		self.GUI.populateList(self.browse(self.GUI.path))
	    except AttributeError:
		pass
	elif args[0]=="havemiss":
	    self._haveList()
            try:
		self.GUI.populateList(self.browse(self.GUI.path))
	    except AttributeError:
		pass
	elif args[0]=="addfav":
	    self._db.execute("INSERT INTO Favorites VALUES (null,?);", (args[1],))
	    self._db.commit()
	elif args[0]=="delfav":
	    self._db.execute("DELETE FROM Favorites WHERE gamename=?;", (args[1],))
	    self._db.commit()
	    self.GUI.populateList(self.browse(self.GUI.path))
	elif args[0]=="game":
	    self._runGame(args[1])
        elif args[0]=="info":
            game = GameItem(self._db, id=args[1])
	    InfoDialog("InfoDialog.xml", self.__settings__.getAddonInfo("path"), "Default", "720p", game=game, Plugin=self)
        elif args[0]=="search":
            if len(args)>1:
		lock()
                self.GUI.populateList(self._gameCollection("", search=args[1]))
		unlock()
            else:
		kbd = Keyboard(heading=self.__language__(30106))
		kbd.doModal()
		if kbd.isConfirmed():
		    if len(kbd.getText()): self.execute(["search", kbd.getText()])
        elif args[0]=="related":
	    lock()
            self.GUI.populateList(self._gameCollection("", related=args[1]))
	    unlock()

    def browse(self, Path):
        Path = Path[1:].split("/")
        lock()
        items = []
        if Path[0]=="":
            items.append(self._item(self.__language__(30100), ICON_YEAR, "browse:/year"))
            items.append(self._item(self.__language__(30101), ICON_BIOS, "browse:/bios"))
            items.append(self._item(self.__language__(30102), ICON_MANUFACTURER, "browse:/manu"))
            items.append(self._item(self.__language__(30103), ICON_NAME, "browse:/name"))
            items.append(self._item(self.__language__(30104), ICON_HDD, "browse:/hdd"))
            items.append(self._item(self.__language__(30105), ICON_ALL, "browse:/all"))
            items.append(self._item(self.__language__(30108), ICON_FAVORITES, "browse:/favorites"))
            items.append(self._item(self.__language__(30106), ICON_SEARCH, "exec:search"))
        elif Path[0]=="year":
            if len(Path)>1:
                items.append(self._item(self.__language__(30500), "parent.png", "browse:/year"))
                items = self._gameCollection("year", year=Path[1])
            else:
                items.append(self._item(self.__language__(30500), "parent.png", "browse:/"))
                sql = "SELECT year FROM Games WHERE id>0 %s GROUP BY year ORDER BY year" % self._FILTERS
                years = self._db.Query(sql, ())
                for year in years:
                    items.append(self._item(year[0], ICON_YEAR, "browse:/year/%s" % year[0]))
        elif Path[0]=="bios":
            if len(Path)>1:
                items.append(self._item(self.__language__(30500), "parent.png", "browse:/bios"))
                items = self._gameCollection("bios", bios=Path[1])
            else:
                items.append(self._item(self.__language__(30500), "parent.png", "browse:/"))
                sql = "SELECT gamename, romset FROM Games WHERE isbios AND romset IN (SELECT romof FROM Games WHERE romof<>'' %s GROUP BY romof) ORDER BY gamename" % self._FILTERS
                bioses = self._db.Query(sql, ())
                for bios in bioses:
                    items.append(self._item(bios[0], ICON_BIOS, "browse:/bios/%s" % bios[1]))
        elif Path[0]=="manu":
            if len(Path)>1:
                items.append(self._item(self.__language__(30500), "parent.png", "browse:/manu"))
                items = self._gameCollection("manu", manufacturer=Path[1])
            else:
                items.append(self._item(self.__language__(30500), "parent.png", "browse:/"))
                sql = "SELECT manufacturer FROM Games WHERE id>0 %s GROUP BY manufacturer ORDER BY manufacturer" % self._FILTERS
                manufacturers = self._db.Query(sql, ())
                for manufacturer in manufacturers:
                    items.append(self._item(manufacturer[0], ICON_BIOS, "browse:/manu/%s" % manufacturer[0]))
        elif Path[0]=="name":
            if len(Path)>1:
                items.append(self._item(self.__language__(30500), "parent.png", "browse:/name"))
                if Path[1]=="#":
                    criteria = "("
                    for i in range(10):
                        criteria += "gamename LIKE '" + str(i) + "%'"
                        if i < 9:
                            criteria += " OR " 
                    criteria += ")"
                else:
                    criteria = "gamename LIKE '" + Path[1] + "%'"
                items = self._gameCollection("name", letter=criteria)
            else:
                items.append(self._item(self.__language__(30500), "parent.png", "browse:/"))
                folders = ['#', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']
                for folder in folders:
                    items.append(self._item(self.__language__( 30107 ) % folder.upper(), ICON_NAME, "browse:/name/%s" % folder))
        elif Path[0]=="hdd":
            items = self._gameCollection("", hasdisk=1)
        elif Path[0]=="all":
            items = self._gameCollection("")
        elif Path[0]=="favorites":
            items = self._gameCollection("", favorites=1)
        unlock()
        return items
        
    def _item(self, caption, image, action="", menu = ""):
	menu = "%s,exec:config," % self.__language__(30803) + menu
	if menu[-1]==",": menu=menu[:-1]
        if image=="":
            item = ListItem(label = caption)
            item.setProperty("action", action)
            item.setProperty("menu", menu)
        else:
            item = ListItem(label = caption, thumbnailImage = image)
            item.setProperty("action", action)
            item.setProperty("menu", menu)
        return item

    def _gameCollection(self, parentpath, year="", bios="", manufacturer="", letter="", search="", hasdisk=0, list="", related="", favorites=0, cache=False):
#        xbmcgui.lock()
        sql = "SELECT id, gamename, gamecomment, thumb, romset, hasdips FROM Games WHERE NOT isbios %s %s ORDER BY gamename"
        criteria=""
        values=""
        if year:
            criteria="AND year=?"
            values = (year,)
        if bios:
            criteria="AND romof=?"
            values = (bios,)
        if hasdisk:
            criteria="AND hasdisk"
            values = ""
        if manufacturer:
            criteria="AND manufacturer=?"
            values = (manufacturer,)
        if letter:
            criteria="AND %s" % letter
            values = ()
        if list:
            criteria="AND id IN (%s)" % list
            values = ()
        if related:
            criteria="AND gamename IN (%s)" % related
            values = ()
        if favorites:
            criteria="AND romset IN (SELECT gamename FROM Favorites)"
            values = ()
        if search:
            criteria="AND gamename LIKE '%" + search + "%'"
            values = ()
        sql =  "SELECT id, gamename, gamecomment, thumb, romset, hasdips, info, history FROM Games WHERE NOT isbios %s %s ORDER BY gamename" % (criteria, self._FILTERS)
        games = self._db.Query(sql, values)
        item = self._item(self.__language__(30500), "parent.png", "browse:/%s" % parentpath)
        item.setProperty("menu", "%s,%s" %(self.__language__( 30900 ), "exec:config"))
        items = [item]
        for game in games:
	    thumb = path.join(self.TITLES_PATH, "%s.png" % str(game[4]))
	    if not path.exists(thumb): thumb = "default.png"
            if str(game[2])!="": label = "%s (%s)" % (str(game[1]), str(game[2]))
            else: label = str(game[1])
            item = xbmcgui.ListItem(label=label, thumbnailImage=thumb)
            item.setProperty("action", "exec:game:%s" % game[0])
            menu = "%s,exec:config,%s,exec:config:%s,%s,exec:info:%s" %(self.__language__( 30803 ), self.__language__( 30800 ), game[0], self.__language__( 30802 ), game[0])
	    if not favorites: menu+=",%s,exec:addfav:%s" % (self.__language__(30804), game[4])
	    else:menu+=",%s,exec:delfav:%s" % (self.__language__(30805), game[4])
            item.setProperty("menu", menu)
            items.append(item)
#        xbmcgui.unlock()
        return items
        del games
	
    def _runGame(self, romset):
        game = GameItem(self._db, id=romset)
        if game.have:
            self._MAME_PARAMS["-cfg_directory"] = "\"%s\"" % self._MAME_CONFIG_PATH.replace("\\", "/")
            self._MAME_PARAMS["-nvram_directory"] = "\"%s\"" % self._MAME_NVRAM_PATH.replace("\\", "/")
            self._MAME_PARAMS["-rompath"] = "\"%s\"" % self._MAME_ROM_PATH.replace("\\", "/")
            self._MAME_PARAMS["-artpath"] = "\"%s\"" % self.MEDIA_PATH.replace("\\", "/")
            if self._MAME_SAMPLES_PATH:
                self._MAME_PARAMS["-samplepath"] = "\"%s\"" % self._MAME_SAMPLES_PATH.replace("\\", "/")
            if game.biosset:
                self._MAME_PARAMS["-bios"] = game.biosset
            cfgxml = "<?xml version=\"1.0\"?><mameconfig version=\"10\"><system name=\"%s\"><input>" % game.romset
            for switch in game.dipswitches:
                switch = DIPSwitch(self._db, switch[0])
                cfgxml+= "<port tag=\"%s\" type=\"DIPSWITCH\" mask=\"%s\" defvalue=\"%s\" value=\"%s\" />" % (switch.tag,switch.mask,switch.defvalue,switch.value)
            cfgxml+="</input><video>"
            cfgxml+="<target index=\"0\" view=\"%s\" rotate=\"%s\" backdrops=\"%s\" overlays=\"%s\" bezels=\"%s\" zoom=\"%s\" />" % (game.view, game.rotate, game.backdrops, game.overlays, game.bezels, game.zoom)
            cfgxml+="</video></system></mameconfig>"
            cfg = open(path.join(self._MAME_CONFIG_PATH, "%s.cfg" % game.romset), "w")
            cfg.write(cfgxml)
            cfg.close()
            command = self._MAME_EXE_PATH
            for key in self._MAME_PARAMS.keys():
                command += " %s %s " % (key, self._MAME_PARAMS[key])
            command+=game.romset
            command = "System.Exec(\"%s\")" % command.replace("\"", "\\\"")
            executebuiltin(command)
        else:
            if dialog.yesno(self.__language__(30701), self.__language__(30702), self.__language__(30703)):MameImport(self)

    def _gameSettings(self, romset_id):
        __fakesettings__ = Addon(self.SETTINGS_PLUGIN_ID)
	SETTINGS_PLUGIN_XML_TEMPLATE = path.join(__fakesettings__.getAddonInfo("path"), "resources", "settings.xml")
	SETTINGS_PLUGIN_XML_DOCUMENT = translatePath(path.join(__fakesettings__.getAddonInfo("profile"), "settings.xml"))
        game = GameItem(self._db, id=romset_id)
        rotate_by_name = {self.__language__(30916):0,self.__language__(30917):90,self.__language__(30918):180,self.__language__(30919):270}
        rotate_by_value = {0:self.__language__(30916),90:self.__language__(30917),180:self.__language__(30918),720:self.__language__(30919)}
        view_by_name = {self.__language__(30921):0,self.__language__(30922):1,self.__language__(30923):2,self.__language__(30924):3}
        view_by_value = {0:self.__language__(30921),1:self.__language__(30922),2:self.__language__(30923),2:self.__language__(30924)}
        bool_by_name = {"false":0, "true":1}
        bool_by_value = {0:"false", 1:"true"}

        settings_xml ="<settings>"

        settings_xml +="<category label=\"%s\">" % self.__language__(30914)
        settings_xml +="<setting label=\"%s\" type=\"labelenum\" id=\"display_rotate\" values=\"%s|%s|%s|%s\" default=\"%s\"/>" % \
            (self.__language__(30915), self.__language__(30916), self.__language__(30917), self.__language__(30918), self.__language__(30919), view_by_value[game.view])
        settings_xml +="<setting label=\"%s\" type=\"labelenum\" id=\"display_view\" values=\"%s|%s|%s|%s\" default=\"%s\"/>" % \
            (self.__language__(30920), self.__language__(30921), self.__language__(30922), self.__language__(30923), self.__language__(30924), rotate_by_value[game.rotate])
        settings_xml +="<setting label=\"%s\" type=\"bool\" id=\"display_backdrops\" default=\"%s\"/>" % (self.__language__(30925), bool_by_value[game.backdrops])
        settings_xml +="<setting label=\"%s\" type=\"bool\" id=\"display_overlays\" default=\"%s\"/>" % (self.__language__(30926), bool_by_value[game.overlays])
        settings_xml +="<setting label=\"%s\" type=\"bool\" id=\"display_bezels\" default=\"%s\"/>" % (self.__language__(30927), bool_by_value[game.bezels])
        settings_xml +="<setting label=\"%s\" type=\"bool\" id=\"display_zoom\" default=\"%s\"/>" % (self.__language__(30928), bool_by_value[game.zoom])
        settings_xml +="</category>"
        switches = self._db.getList("Dipswitches", ["id"], {"romset_id=":romset_id})

        if len(game.biossets):
            values = ""
            for biosset in game.biossets:
                if game.biosset==biosset.name:default = biosset.description
                values+="|%s" % biosset.description
            settings_xml +="<category label=\"%s\">" % self.__language__(30937)
            settings_xml +="<setting label=\"%s\" type=\"labelenum\" id=\"biosset\" values=\"%s\" default=\"%s\"/>" % \
                (self.__language__(30938), values[1:], default)
            settings_xml +="</category>"

        settings_xml +="<category label=\"%s\">" % self.__language__(30801)
        for switch in switches:
            switch = DIPSwitch(self._db, id=switch["id"])
            values = ""
            for value in switch.values_by_value:
                values+="|%s" % value
            if values=="|On|Off" or values=="|Yes|No":
                if switch.values_by_name[str(switch.value)]=="On" or switch.values_by_name[str(switch.value)]=="Yes":
                    default="true"
                else:
                    default="false"
                settings_xml += "<setting label=\"%s\" type=\"bool\" id=\"S%s\" default=\"%s\"/>" % (switch.name, switch.id, default)
            else:
                settings_xml += "<setting label=\"%s\" type=\"labelenum\" id=\"S%s\" default=\"%s\"  values=\"%s\"/>" % (switch.name, switch.id, switch.values_by_name[str(switch.value)], values[1:])
        settings_xml+="</category>"
        settings_xml+="</settings>"
        settings_xml_file = open(SETTINGS_PLUGIN_XML_TEMPLATE, "w")
        settings_xml_file.write(settings_xml.encode('utf8'))
        settings_xml_file.close()
        __fakesettings__.openSettings()
        if path.exists(SETTINGS_PLUGIN_XML_DOCUMENT):
            src = open(SETTINGS_PLUGIN_XML_DOCUMENT, "r")
            xml = src.read()
            src.close()
            xml = re.sub("\r|\t|\n", "", xml)
            settings = XMLHelper().getNodes(xml, "setting")
            for setting in settings:
                if XMLHelper().getAttribute(setting, "setting", "id")=="display_view":
                    game.view = view_by_name[XMLHelper().getAttribute(setting, "setting", "value")]
                elif XMLHelper().getAttribute(setting, "setting", "id")=="display_rotate":
                    game.rotate = rotate_by_name[XMLHelper().getAttribute(setting, "setting", "value")]
                elif XMLHelper().getAttribute(setting, "setting", "id")=="display_backdrops":
                    game.backdrops = bool_by_name[XMLHelper().getAttribute(setting, "setting", "value")]
                elif XMLHelper().getAttribute(setting, "setting", "id")=="display_overlays":
                    game.overlays = bool_by_name[XMLHelper().getAttribute(setting, "setting", "value")]
                elif XMLHelper().getAttribute(setting, "setting", "id")=="display_bezels":
                    game.bezels = bool_by_name[XMLHelper().getAttribute(setting, "setting", "value")]
                elif XMLHelper().getAttribute(setting, "setting", "id")=="display_zoom":
                    game.zoom = bool_by_name[XMLHelper().getAttribute(setting, "setting", "value")]
                elif XMLHelper().getAttribute(setting, "setting", "id")=="biosset":
                    game.biosset = BiosSet(self._db).getByDescription(XMLHelper().getAttribute(setting, "setting", "value")).name
                else:
                    switch = DIPSwitch(self._db, id=XMLHelper().getAttribute(setting, "setting", "id")[1:])
                    value = XMLHelper().getAttribute(setting, "setting", "value")
                    if value=="true":
                        try:
                            switch.value = switch.values_by_value["On"]
                        except KeyError:
                         switch.value = switch.values_by_value["Yes"]
                    elif value=="false":
                        try:
                            switch.value = switch.values_by_value["Off"]
                        except KeyError:
                            switch.value = switch.values_by_value["No"]
                    else:
                        switch.value=switch.values_by_value[XMLHelper().getAttribute(setting, "setting", "value")]
                    switch.writeDB()
                game.writeDB()
                self._db.commit()
            remove(SETTINGS_PLUGIN_XML_DOCUMENT)
        remove(SETTINGS_PLUGIN_XML_TEMPLATE)

    def _thumbNails(self):
        if self._MAME_TITLES_PATH or self._ONLINE_TITLES:
            progress = DialogProgress()
            progress.create(self.__language__(30615))
            if self._ROMSET_TITLES:
                files = self._db.runQuery("SELECT romset FROM Games WHERE have")
            else:
                files = self._db.runQuery("SELECT romset FROM Games")
            count = len(files)
            step = count/20
            index = 0
            for file in files:
                romset = file["romset"]
                if progress.iscanceled():
		    break
                index += 1
                if self._MAME_TITLES_PATH:
                    filename = path.join(self._MAME_TITLES_PATH, "%s.png" % romset)
                    if self._CACHE_TITLES:
                        cachefile = path.join(self._MAME_CACHE_PATH, "%s.png" % romset)
                    if not path.exists(cachefile):
                        if path.exists(filename):
                            copyfile(filename, cachefile)
                            filename = cachefile
                if self._ONLINE_TITLES:
                    filename = path.join(self._MAME_CACHE_PATH, "%s.png" % romset)
                    if self._HIRES_TITLES:res="hi"
                    else:res="lo"
                    if not path.exists(filename):
                        urlcleanup()
                        urlretrieve("https://www.otaku-realm.net/xbmame/%s/%s.png" % (res, romset), filename)
                        progress.update(int((float(index)/float(count)) * 100), self.__language__(30616), self.__language__(30617) % romset, self.__language__(30618) % (index, count))
                if index % step == 0:
                    progress.update(int((float(index)/float(count)) * 100), self.__language__(30616), self.__language__(30617) % romset, self.__language__(30618) % (index, count))
            progress.close()

    def _haveList(self):
        progress = DialogProgress()
        progress.create(self.__language__(30611))
        files = listdir(self._MAME_ROM_PATH)
        count = len(files)
        step = count/20
        index = 0
        for file in files:
            if progress.iscanceled(): break
            index += 1
            romset = file.replace(".zip", "").replace(".rar", "").replace(".7z","")
            if index % step == 0:
                progress.update(int((float(index)/float(count)) * 100), self.__language__(30612), self.__language__(30613) % romset, self.__language__(30614) % (index, count))
            self._db.execute("UPDATE Games SET have=1 WHERE romset=?", (romset,))
        self._db.commit()
        progress.close()

class XBMameGUI(WindowXML):

    _LISTCONTAINER = 30301
    
    def __init__(self, *args, **kwargs):
        self.parent = kwargs["Plugin"]
        try:
            self.path = kwargs["Path"]
        except KeyError:
            self.path = "/"
	self.parent.GUI = self
	self.doModal()

    def onInit(self):
        self._LIST = self.getControl(self._LISTCONTAINER)
        self.populateList(self.parent.browse(self.path))
    
    def onClick(self, controlId):
        if controlId==self._LISTCONTAINER:
            action = self._LIST.getSelectedItem().getProperty("action").split(":")
            if action[0]=="browse":
		self.path = action[1]
                self.populateList(self.parent.browse(action[1]))
            elif action[0]=="exec":
		self.parent.execute(action[1:])

    def onFocus(self, controlId):
	pass
    
    def onAction(self, action):
        if action.getId()==10:
            self.close()
        elif action.getId()==117:
            obj = self._LIST.getSelectedItem()
            if obj.getProperty("menu")!="":
                menu = ContextMenu("ContextMenu.xml", self.parent.__settings__.getAddonInfo("path"), "Default", "720p", menu=obj.getProperty("menu"))
                action = menu.action.split(":")
                if action[0]=="exec":
		    self.parent.execute(action[1:])
		    
    def populateList(self, items):
        self._LIST.reset()
        self._LIST.addItems(items)
