# -*- coding: utf-8 -*-
'''
    script.screensaver.football.panel - A Football Panel for Kodi
    RSS Feeds, Livescores and League tables as a screensaver or
    program addon 
    Copyright (C) 2016 enen92

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
from HTMLParser import HTMLParser
from common_addon import *

def get_league_tables_ids():
	tables = []
	if addon.getSetting("t-bpl") == "true": tables.append(4328)
	if addon.getSetting("t-bbva") == "true": tables.append(4335)
	if addon.getSetting("t-seriea") == "true": tables.append(4332)
	if addon.getSetting("t-fleague1") == "true": tables.append(4334)
	if addon.getSetting("t-liganos") == "true": tables.append(4344)
	if addon.getSetting("t-eredivisie") == "true": tables.append(4337)
	if addon.getSetting("t-bundesliga") == "true": tables.append(4331)
	if addon.getSetting("t-russianpl") == "true": tables.append(4355)
	if addon.getSetting("t-jupiler") == "true": tables.append(4338)
	if addon.getSetting("t-scotlandpl") == "true": tables.append(4330)
	if addon.getSetting("t-mls") == "true": tables.append(4346)
	if addon.getSetting("t-argentina") == "true": tables.append(4406)
	if addon.getSetting("t-brasileirao") == "true": tables.append(4351)
	if addon.getSetting("t-ukra") == "true": tables.append(4354)
	if addon.getSetting("t-australia") == "true": tables.append(4356)
	if addon.getSetting("t-greece") == "true": tables.append(4336)
	if addon.getSetting("t-danish") == "true": tables.append(4340)
	if addon.getSetting("t-norway") == "true": tables.append(4358)
	if addon.getSetting("t-china") == "true": tables.append(4359)
	if addon.getSetting("t-sweden1") == "true": tables.append(4347)
	if addon.getSetting("t-echampionship") == "true": tables.append(4329)
	if addon.getSetting("t-eleague1") == "true": tables.append(4396)
	if addon.getSetting("t-eleague2") == "true": tables.append(4397)
	if addon.getSetting("t-sadelante") == "true": tables.append(4400)
	if addon.getSetting("t-fleague2") == "true": tables.append(4401)
	if addon.getSetting("t-ssuperettan") == "true": tables.append(4403)
	if not tables:
		tables.append(4328)
	return tables

def get_league_id_no_games():
	if addon.getSetting("no-livescores-league") == "0": return 4328
	if addon.getSetting("no-livescores-league") == "1": return 4335
	if addon.getSetting("no-livescores-league") == "2": return 4332
	if addon.getSetting("no-livescores-league") == "3": return 4334
	if addon.getSetting("no-livescores-league") == "4": return 4344
	if addon.getSetting("no-livescores-league") == "5": return 4337
	if addon.getSetting("no-livescores-league") == "6": return 4331
	if addon.getSetting("no-livescores-league") == "7": return 4355
	if addon.getSetting("no-livescores-league") == "8": return 4338
	if addon.getSetting("no-livescores-league") == "9": return 4330
	if addon.getSetting("no-livescores-league") == "10": return 4346
	if addon.getSetting("no-livescores-league") == "11": return 4406
	if addon.getSetting("no-livescores-league") == "12": return 4351
	if addon.getSetting("no-livescores-league") == "13": return 4354
	if addon.getSetting("no-livescores-league") == "14": return 4356
	if addon.getSetting("no-livescores-league") == "15": return 4336
	if addon.getSetting("no-livescores-league") == "16": return 4340
	if addon.getSetting("no-livescores-league") == "17": return 4358
	if addon.getSetting("no-livescores-league") == "18": return 4359
	if addon.getSetting("no-livescores-league") == "19": return 4347
	if addon.getSetting("no-livescores-league") == "20": return 4329
	if addon.getSetting("no-livescores-league") == "21": return 4396
	if addon.getSetting("no-livescores-league") == "22": return 4397
	if addon.getSetting("no-livescores-league") == "23": return 4400
	if addon.getSetting("no-livescores-league") == "24": return 4401
	if addon.getSetting("no-livescores-league") == "25": return 4403

class HTMLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)
