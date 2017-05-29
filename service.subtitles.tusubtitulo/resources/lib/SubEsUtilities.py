# -*- coding: utf-8 -*-


import xbmc
import urllib
from operator import itemgetter
from bs4 import BeautifulSoup
from utils import languages
import re
import json
#import pprint
#pp = pprint.PrettyPrinter(indent=4)


APIKey = "AIzaSyAm6QlezxEd4N2flR2QO6aVYQ3cx_K4xsw";
CSX = "006098004307864223219:fwks5vba0co";
main_url = "https://www.tusubtitulo.com/"

def log(module, msg):
	xbmc.log((u"### [%s] - %s" % (module,msg,)).encode('utf-8'), level=xbmc.LOGDEBUG)

def search_tvshow(tvshow, season, episode, languages, filename):
    subs = list()
    subs.extend(getAllSubInfo(buildURL(tvshow, season, episode), tvshow, season, episode))
    subs = clean_subtitles_list(subs)
    subs = order_subtitles_list(subs)
    return subs


def cleanLang(lang):
	lang = lang.replace("ñ".decode("utf-8"), "n")
	lang = lang.replace("á".decode("utf-8"), "a")
	lang = lang.replace("é".decode("utf-8"), "e")
	return lang


def buildURL(tvshow, season, episode):
	googleCSE = "https://www.googleapis.com/customsearch/v1?key=" + APIKey + "&cx=" + CSX + "&fields=items(title,link)&q="; #separe spaces with +
	searchURL = googleCSE + tvshow.replace(" ", "+")

	page = urllib.urlopen(searchURL).read()
	data = json.loads(page)
	showIdWord = data["items"][0]["title"].strip().strip("TuSubtitulo").strip().strip("-").strip().replace(" ", "-")

	episodeFetch = "https://www.tusubtitulo.com/showsub.php?ushow=" + showIdWord.lower() + "&useason=" + str(season) + "&uepisode=" + str(episode)

	return episodeFetch

def getAllSubInfo(url, tvshow, season, episode):
    data = {}
    page = urllib.urlopen(url).read()
    soup = BeautifulSoup(page, 'html.parser')
    #soup.original_encoding'ISO-8859-7'

    versions = soup.find_all(id=re.compile("^version"))
    episodeData = []

    for version in versions:
        ver = dict()
        verName = version.find_all(class_="title-sub")[0].get_text().strip().replace("ó".decode("utf-8"), "o").strip("Version").strip()
        temp = []
        for i in range(len(verName)-16):
            temp.append(verName[i])
        verName = "".join(temp).strip().strip("megabytes").strip().strip("0.00").strip().strip(",")
        ver["name"] = verName
        ver["subs"] = []
        subs = version.find_all(class_="sslist")
        for sub in subs:
            completion = sub.find_all(class_=re.compile("^li-estado"))[0].get_text().strip()
            if completion == "Completado":
                thisSub = dict()
                thisSub["lang"] = cleanLang(sub.find_all(class_="li-idioma")[0].get_text().strip())
                linkSection = sub.find_all(class_=re.compile("^rng download"))[0].find_all("a")
                thisSub["link"] = linkSection[len(linkSection)-2].get('href')
                ver["subs"].append(thisSub)
        episodeData.append(ver)
    #return episodeData
	############ PART 2 #################
    subtitles_list = []
	#data = getAllSubInfo(buildURL(tvshow, season, episode))
    for i in range(len(episodeData)):
        ver = episodeData[i]
        for sub in ver["subs"]:
            lang = sub["lang"]
            #filename = tvshow.replace(" ", ".") + "." + str(season) + "x" + str(episode)
            filename = tvshow + " " + str(season) + "x" + str(episode)
            #filename = "Prueba"
            if lang in languages:
                languageshort = languages[lang][1]
                languagelong = languages[lang][0]
                #filename = filename + " (" + ver["name"] + ").(%s)" % languages[lang][2]
                filename = filename + " (" + ver["name"] + ")"
                server = filename
                order = 1 + languages[lang][3]
            else:
                lang = "Unknown"
                languageshort = languages[lang][1]
                languagelong = languages[lang][0]
                #filename = filename + " (" + ver["name"] + ").(%s)" % languages[lang][2]
                filename = filename + " (" + ver["name"] + ")"
                server = filename
                order = 1 + languages[lang][3]
            data = dict()
            id = sub["link"]
            data["rating"] = "5"
            data["no_files"] = 1
            data["filename"] = filename
            data["server"] = server
            data["sync"] = True
            data["id"] = id
            data["language_flag"] = languageshort + '.gif'
            data["language_name"] = languagelong
            data["hearing_imp"] = False
            data["link"] = main_url + id
            data["lang"] = languageshort
            data["order"] = order
            subtitles_list.append(data)
    #pp.pprint(subtitles_list)
    return subtitles_list

def clean_subtitles_list(subtitles_list):
    seen = set()
    subs = []
    for sub in subtitles_list:
        filename = sub['link']
        #log(__name__, "Filename: %s" % filename)
        if filename not in seen:
            subs.append(sub)
            seen.add(filename)
    return subs

def order_subtitles_list(subtitles_list):
	return sorted(subtitles_list, key=itemgetter('order'))

#pp.pprint(getAllSubInfo(buildURL("doctor who 2005", 10, 3), "doctor who 2005", 10, 3))
