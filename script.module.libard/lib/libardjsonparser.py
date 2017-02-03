# -*- coding: utf-8 -*-
import json
import libmediathek3 as libMediathek

pluginpath = 'plugin://script.module.libArd/'

def parse(url):
	response = libMediathek.getUrl(url)
	j = json.loads(response)
	
def parseDate(url):
	l = []
	response = libMediathek.getUrl(url)
	j = json.loads(response)
	j1 = j["sections"][-1]["modCons"][0]["mods"][0]["inhalte"]
	for entry in j1:
		j2 = entry["inhalte"]
		for entry in j2:
			d = {}
			d["_airedtime"] = entry["dachzeile"]
			#d["_name"] = entry["dachzeile"] + ' - '
			#d["_name"] += entry["ueberschrift"] + ' - '
			d["_name"] = entry["ueberschrift"] + ' - '
			duration = 0
			for j3 in entry["inhalte"]:
				if runtimeToInt(j3["unterzeile"]) > duration:
					duration = runtimeToInt(j3["unterzeile"])
					d["_name"] += j3["ueberschrift"]
					#d["_channel"] = j3["unterzeile"]
					#d["_thumb"] = j3["bilder"][0]["schemaUrl"].replace("##width##","0")
					d["_thumb"] = j3["bilder"][0]["schemaUrl"].replace("##width##","384")
					d["url"] = j3["link"]["url"]
					d["documentId"] = j3["link"]["url"].split("player/")[1].split("?")[0]
					d["_duration"] = str(runtimeToInt(j3["unterzeile"]))
					#d["_pluginpath"] = pluginpath
					d["_type"] = 'date'
					d['mode'] = 'libArdPlay'
			l.append(d)
	return l
		
def parseAZ(letter='A'):
	if letter == "0-9":
		letter = '#'
	l = []
	response = libMediathek.getUrl("http://www.ardmediathek.de/appdata/servlet/tv/sendungAbisZ?json")
	j = json.loads(response)
	j1 = j["sections"][0]["modCons"][0]["mods"][0]["inhalte"]
	for entry in j1:
		#if entry["ueberschrift"] == letter.upper():
		if True:
			for entry in entry["inhalte"]:
				d = {}
				d["_name"] = entry["ueberschrift"].encode("utf-8")
				d["_channel"] = entry["unterzeile"].encode("utf-8")
				d["_entries"] = int(entry["dachzeile"].encode("utf-8").split(' ')[0])
				#d["thumb"] = entry["bilder"][0]["schemaUrl"].replace("##width##","0").encode("utf-8")
				d["_thumb"] = entry["bilder"][0]["schemaUrl"].replace("##width##","1920").encode("utf-8")
				d["url"] = entry["link"]["url"].encode("utf-8")
				d['mode'] = 'libArdListVideos'
				#d["documentId"] = entry["link"]["url"].split("documentId=")[1].split("&")[0]
				#d["pluginpath"] = pluginpath
				d["_type"] = 'shows'
				l.append(d)
		
		
	return l
	
def parseVideos(url):
	l = []
	response = libMediathek.getUrl(url)
	j = json.loads(response)
	#j1 = j["sections"][-1]["modCons"][-1]["mods"][-1]
	#j1 = j["sections"][-1]["modCons"][-1]["mods"][-1]
	j1 = j["sections"][-1]["modCons"][-1]["mods"][-1]
	
	for j2 in j1["inhalte"]:
		d = {}
		if "ueberschrift" in j2:
			d["_name"] = j2["ueberschrift"].encode("utf-8")
			if 'Hörfassung' in d["_name"] or 'Audiodeskription' in d["_name"]:
				d["_name"] = d["_name"].replace(' - Hörfassung','').replace(' - Audiodeskription','')
				d["_name"] = d["_name"].replace(' (mit Hörfassung)','').replace(' (mit Audiodeskription)','')
				d["_name"] = d["_name"].replace(' mit Hörfassung','').replace(' mit Audiodeskription','')
				d["_name"] = d["_name"].replace(' (Hörfassung)','').replace(' (Audiodeskription)','')
				d["_name"] = d["_name"].replace(' Hörfassung','').replace(' Audiodeskription','')
				d["_name"] = d["_name"].replace('Hörfassung','').replace('Audiodeskription','')
				d["_name"] = d["_name"].strip()
				if d["_name"].endswith(' -'):
					d["_name"] = d["_name"][:-2]
				d["_name"] = d["_name"] + ' - Hörfassung'
				d["_audioDesc"] = True
				
		if "unterzeile" in j2:
			d["_duration"] = str(runtimeToInt(j2["unterzeile"]))
		if "bilder" in j2:
			d["_thumb"] = j2["bilder"][0]["schemaUrl"].replace("##width##","384").encode("utf-8")
		if "teaserTyp" in j2:
			if j2["teaserTyp"] == "PermanentLivestreamClip" or j2["teaserTyp"] == "PodcastClip":
				continue
			elif j2["teaserTyp"] == "OnDemandClip":
				d["_type"] = 'video'
				d['mode'] = 'libArdPlay'
			elif j2["teaserTyp"] == "Sammlung":
				d["_type"] = 'dir'
				d['mode'] = 'libArdListVideos'
			else:
				libMediathek.log('json parser: unknown item type: ' + j2["teaserTyp"])
				d["_type"] = 'dir'
				d['mode'] = 'libArdListVideos'
				
		if "link" in j2:
			d["url"] = j2["link"]["url"].encode("utf-8")
			d["documentId"] = j2["link"]["url"].split("/player/")[-1].split("?")[0].encode("utf-8")
		if "dachzeile" in j2:
			d["_releasedate"] = j2["dachzeile"].encode("utf-8")
		if 'ut' in j2['kennzeichen']:
			d["_subtitle"] = True
		if 'geo' in j2['kennzeichen']:
			d['_geo'] = 'DACH'
		if 'fsk6' in j2['kennzeichen']:
			d['_mpaa'] = 'FSK6'
		if 'fsk12' in j2['kennzeichen']:
			d['_mpaa'] = 'FSK12'
		if 'fsk16' in j2['kennzeichen']:
			d['_mpaa'] = 'FSK16'
		if 'fsk18' in j2['kennzeichen']:
			d['_mpaa'] = 'FSK18'
		#d["_pluginpath"] = pluginpath
		
		
		l.append(d)
	
	aktiv = False
	for buttons in j1['buttons']:
		if buttons["label"]["text"] == "Seiten":
			for button in buttons["buttons"]:
				if aktiv:
					d = {}
					d["url"] = button["buttonLink"]["url"]
					d["type"] = 'nextPage'
					d['mode'] = 'libArdListVideos'
					l.append(d)
				aktiv = button['aktiv']
	return l
	
	
def runtimeToInt(runtime):
	try:
		if '|' in runtime:
			for s in runtime.split('|'):
				if 'Min' in s:
					runtime = s
		if '<br>' in runtime:
			runtime = runtime.split('<br>')[0]
		t = runtime.replace('Min','').replace('min','').replace('.','').replace(' ','').replace('|','').replace('UT','')
		HHMM = t.split(':')
		if len(HHMM) == 1:
			return int(HHMM[0])*60
		else:
			return int(HHMM[0])*60 + int(HHMM[1])
	except: 
		return ''