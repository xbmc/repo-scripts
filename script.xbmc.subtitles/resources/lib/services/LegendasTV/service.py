# -*- coding: UTF-8 -*-
# Copyright, 2010, Guilherme Jardim.
# This program is distributed under the terms of the GNU General Public License, version 3.
# http://www.gnu.org/licenses/gpl.txt
# Rev. 2.1.1

from operator import itemgetter
from threading import Thread
from BeautifulSoup import *
from utilities import log, languageTranslate, getShowId
import cookielib
import math
import os
import re
import sys
import time
import urllib
import urllib2
import xbmc
import xbmcvfs
import xbmcgui
if sys.version_info < (2, 7):
    import simplejson
else:
    import json as simplejson

# Service variables
sub_ext = 'srt aas ssa sub smi'
global regex_1, regex_2, regex_3
regex_1 = "<div class=\"f_left\"><p><a href=\"([^\"]*)\">([^<]*)</a></p><p class=\"data\">.*?downloads, nota (\d*?),.*?<img .*? title=\"([^\"]*)\" /></div>"
regex_2 = "<button class=\"ajax\" data-href=\"/util/carrega_legendas_busca/id_filme:\d*/page:\d*\">(\d*)</button>"
regex_3 = "<button class=\"icon_arrow\" onclick=\"window.open\(\'([^\']*?)\', \'_self\'\)\">DOWNLOAD</button>"

# XBMC specific variables
_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__addon__ = sys.modules[ "__main__" ].__addon__

def XBMC_OriginalTitle(OriginalTitle):
    MovieName =  xbmc.getInfoLabel("VideoPlayer.OriginalTitle")
    if MovieName:
        OriginalTitle = MovieName
    else:
        ShowID = getShowId()
        if ShowID:
            HTTPResponse = urllib2.urlopen("http://www.thetvdb.com//data/series/%s/" % str(ShowID)).read()
            if re.findall("<SeriesName>(.*?)</SeriesName>", HTTPResponse, re.IGNORECASE | re.DOTALL):
                OriginalTitle = re.findall("<SeriesName>(.*?)</SeriesName>", HTTPResponse, re.IGNORECASE | re.DOTALL)[0]
    return OriginalTitle.encode('ascii', 'replace')

class LTVThread(Thread):
    def __init__ (self, obj, count, main_id, page):
        Thread.__init__(self)
        self.count = count
        self.main_id = main_id
        self.page = page
        self.obj = obj
        self.status = -1
        
    def run(self):
        fnc = self.obj.pageDownload(self.count, self.main_id, self.page)
        self.status = fnc

class LegendasTV:
    def __init__(self, **kargs):
        self.RegThreads = []
        self.cookie = ""
    
    def Log(self, message):
#        print "####  %s" % message.encode("utf-8")
        log(__name__, message)
        
    def _urlopen(self, request):
        try:
            return urllib2.urlopen(request).read()
        except urllib2.HTTPError:
            return ""

    def login(self, username, password):
        if self.cookie:
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookie))
            urllib2.install_opener(opener)
            return self.cookie
        else:
            self.cookie = cookielib.CookieJar()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookie))
            urllib2.install_opener(opener)
            login_data = urllib.urlencode({'_method':'POST', 'data[User][username]':username, 'data[User][password]':password})
            request = urllib2.Request("http://minister.legendas.tv/login/", login_data)
            response = self._UNICODE(urllib2.urlopen(request).read())
            if response.__contains__(u'Usuário ou senha inválidos'):
                self.Log( u" Login Failed. Check your data at the addon configuration.")
                return 0
            else: 
                return self.cookie

    def chomp(self, s):
        s = re.sub("\s{2,20}", " ", s)
        a = re.compile("(\r|\n|^\s|\s$|\'|\"|,|;|[(]|[)])")
        b = re.compile("(\t|-|:|[/]|[?]|\[|\]|\.)")
        s = b.sub(" ", s)
        s = re.sub("[ ]{2,20}", " ", s)
        s = a.sub("", s)
        return s

    def CleanLTVTitle(self, s):
        s = re.sub("[(]?[0-9]{4}[)]?$", "", s)
        s = re.sub("[ ]?&[ ]?", " ", s)
        s = re.sub("'", " ", s)
        s = self.chomp(s)
        s = s.title()
        return s
    
    def _UNICODE(self,text):
        if text:
            return unicode(BeautifulSoup(text, fromEncoding="utf-8",  smartQuotesTo=None))
        else:
            return text
        
    def CalculateRatio(self, a, b):
        # Calculate the probability ratio and append the result
        counter = 0
        Ratio = 0
        if len(a.split(" ")) > len(b.split(" ")):
            Paradigm, Guess = a, b
        else: 
            Paradigm, Guess = b, a
        if len(Paradigm.split(" ")):
            for Term in Paradigm.split(" "):
                if re.search(r"(^|\s)%s(\s|$)" % re.escape(Term), Guess, re.I):
                    counter += 1
            if counter:
                Ratio = "%.2f" % (float(counter) / float(len(Paradigm.split(" "))))
            else:
                Ratio = "%.2f" % float(0)
        else:
            if re.search("(^|\s)%s(\s|$)" % re.escape(Paradigm), Guess, re.I):
                Ratio = "%.2f" % float(1)
            else:
                Ratio = "%.2f" % float(0)
        return Ratio
                
    def _log_List_dict(self, obj, keys="", maxsize=100):
        Content = ""
        if not len(obj):
            return 0
        for key in keys.split():
            if not obj[0].has_key(key):
                continue
            maximum = max(len(unicode(k[key])) for k in obj)
            maximum = max(maximum+2, len(key)+2)
            if maximum > maxsize: maximum = maxsize
            Content = Content + "%s" % unicode(key)[:maxsize-2].ljust(maximum)
        self.Log(Content)
        for x, Result in enumerate(obj):
            Content = ""
            for key in keys.split():
                if not obj[0].has_key(key):
                    continue
                value = unicode(Result[key])
                if not len(value): continue
                maximum = max(len(unicode(k[key])) for k in obj)
                maximum = max(maximum+2, len(key)+2)
                if maximum > maxsize: maximum = maxsize
                Content = Content + "%s" % unicode(value)[:maxsize-2].ljust(maximum)
            self.Log(Content)
            if x > 30:
                break
        self.Log(" ")
        return 0

    def findID(self, Movie, TVShow, Year, Season, SearchTitle, SearchString):
        allResults, discardedResults, filteredResults, LTVSeason, LTVYear = [], [], [], 0, 0
        Response = self._urlopen("http://minister.legendas.tv/util/busca_titulo/" + urllib.quote_plus(SearchString))
        Response =  simplejson.loads(unicode(Response, 'utf-8', errors='ignore'))
        # Load the results
        # Parse and filter the results
        self.Log("Message: Searching for movie/tvshow list with term(s): [%s]" % SearchString)
        for R in Response:
            LTVSeason = 0
            if R.has_key('Filme') and R['Filme'].has_key('dsc_nome'):
                LTVTitle = self.CleanLTVTitle(R['Filme']['dsc_nome'])
                TitleBR = R['Filme']['dsc_nome_br']
                if re.findall(".*? - (\d{1,2}).*?emporada", TitleBR):
                    LTVSeason = re.findall(".*? - (\d{1,2}).*?emporada", TitleBR)[0]
                ContentID = R['Filme']['id_filme']
                # Calculate the probability ratio and append the result
                Ratio = self.CalculateRatio(LTVTitle, SearchTitle)
                allResults.append({"id" : ContentID, "title" : LTVTitle, "ratio" : Ratio, "year" : LTVYear, "season" : LTVSeason})
        # Return if there are no results
        if not len(allResults):
            self.Log("Message: The search [%s] didn't returned viable results." % SearchString)
            return "", ""
        # Filter tvshows for season or movies by year
        else:
            allResults = sorted(allResults, key=lambda k: k["ratio"], reverse=True)
            for Result in allResults:
                if TVShow:
                    if int(Season) == int(Result["season"]) or (not Result["season"] and Result["ratio"] == "1.00"):
                        if len(filteredResults):
                            if Result["ratio"] == filteredResults[0]["ratio"]:
                                filteredResults.append(Result)
                            else:
                                discardedResults.append(Result)
                        else:
                            filteredResults.append(Result)
                    else:
                        discardedResults.append(Result)
                elif Movie:
#                     if abs(int(Result["year"]) - int(Year)) <= 1 and math.fabs(float(Result["ratio"]) - float(allResults[0]["ratio"])) <= 0.25:
                    if math.fabs(float(Result["ratio"]) - float(allResults[0]["ratio"])) <= 0.25:
                        filteredResults.append(Result)
                    else:
                        discardedResults.append(Result)
            if not len(filteredResults):
                self.Log("Message: After filtration, search [%s] didn't returned viable results." % SearchString)
                self.Log("Discarded results:")
                self._log_List_dict(discardedResults, "ratio year title season id")
                return discardedResults, ""
            else:
                # Log filtered results
                self.Log("Message: After filtration, the search [%s] returned %s viable results." % (SearchString, len(filteredResults)))
                self.Log(" ")
                self.Log("Viable results:")
                self._log_List_dict(filteredResults, "ratio year title season id")
                self.Log("Discarded results:")
                self._log_List_dict(discardedResults, "ratio year title season id")
                return discardedResults, filteredResults
            
    def pageDownload(self, MainID, MainIDNumber, Page):
        # Log the page download attempt.
        self.Log("Message: Retrieving page [%s] for Movie[%s], Id[%s]." % (Page, MainID["title"], MainID["id"]))
        
        Response = self._urlopen("http://minister.legendas.tv/util/carrega_legendas_busca/page:%s/id_filme:%s" % (Page, MainID["id"]))

        if not re.findall(regex_1, Response, re.IGNORECASE | re.DOTALL):
            self.Log("Error: Failed retrieving page [%s] for Movie[%s], Id[%s]." % (Page, MainID["title"], MainID["id"]))
        else:
            for x, content in enumerate(re.findall(regex_1, Response, re.IGNORECASE | re.DOTALL), start=1):
                LanguageName, LanguageFlag, LanguagePreference = "", "", 0
                download_id = content[0]
                title = self._UNICODE(content[1])
                release = self._UNICODE(content[1])
                rating =  content[2]
                lang = self._UNICODE(content[3])
                if re.search("Portugu.s-BR", lang):   LanguageId = "pb" 
                elif re.search("Portugu.s-PT", lang): LanguageId = "pt"
                elif re.search("Ingl.s", lang):       LanguageId = "en" 
                elif re.search("Espanhol", lang):     LanguageId = "es"
                elif re.search("Franc.s", lang):      LanguageId = "fr"
                else: continue
                for Preference, LangName in self.Languages:
                    if LangName == languageTranslate(LanguageId, 2, 0):
                        LanguageName = LangName
                        LanguageFlag = "flags/%s.gif" % LanguageId
                        LanguagePreference = Preference
                        break
                if not LanguageName:
                    continue
                        
                self.DownloadsResults.append({
                                              "main_id_number": int(MainIDNumber),
                                              "page": int(Page),
                                              "position": int(x),
                                              "title": title,
                                              "filename": release,
                                              "language_name": LanguageName,
                                              "ID": download_id,
                                              "format": "srt",
                                              "sync": False,
                                              "rating":rating,
                                              "language_flag": LanguageFlag,
                                              "language_preference": int(LanguagePreference) })

            self.Log("Message: Retrieved [%s] results for page [%s], Movie[%s], Id[%s]." % (x, Page, MainID["title"], MainID["id"]))
                
    def Search(self, **kargs):   
        # Init all variables
        startTime = time.time()
        filteredResults, self.DownloadsResults, self.Languages = [], [], []
        Movie, TVShow, Year, Season, Episode = "", "", 0, 0, 0
        for key, value in kargs.iteritems():
            value = self._UNICODE(value)
            if key == "movie":             Movie = self.CleanLTVTitle(value)
            if key == "tvshow":            TVShow = self.CleanLTVTitle(value)
            if key == "year" and value:    Year = int(value)
            if key == "season" and value:  Season = int(value)
            if key == "episode" and value: Episode = int(value)
            if key == "lang1" and value:   self.Languages.append((0, value))
            if key == "lang2" and value:   self.Languages.append((1, value))
            if key == "lang3" and value:   self.Languages.append((2, value))
        self.Languages.sort()

        if Movie: SearchTitle = Movie
        else: SearchTitle = TVShow
        discardedResults, filteredResults = "", ""
        discardedResults, filteredResults = self.findID(Movie, TVShow, Year, Season, SearchTitle, SearchTitle)
        if not filteredResults:
            # Searching for movie titles/tvshow ids using the lengthiest words
            if len(SearchTitle.split(" ")):
                for SearchString in sorted(SearchTitle.split(" "), key=len, reverse=True):
                    if SearchString in [ 'The', 'O', 'A', 'Os', 'As', 'El', 'La', 'Los', 'Las', 'Les', 'Le' ] or len(SearchString) < 2:
                        continue
                    discardedResults, filteredResults = self.findID(Movie, TVShow, Year, Season, SearchTitle, SearchString)
                    if filteredResults: 
                        break
            else:
                discardedResults, filteredResults = self.findID(Movie, TVShow, Year, Season, SearchTitle, SearchTitle)
        if not filteredResults and len(discardedResults):
            filteredResults = []
            for Result in discardedResults[0:4]:
                if Result["ratio"] == discardedResults[0]["ratio"]:
                    filteredResults.append(Result)
            self.Log("Message: Filtration failed, using discarded results.")
        elif not filteredResults:
            return ""
        # Initiate the "buscalegenda" search to search for all types and languages
        MainIDNumber = 1
        for MainID in filteredResults[0:4]:
            # Find how much pages are to download
            self.Log("Message: Retrieving results to id[%s]" % (MainID["id"]))
            Response = self._urlopen("http://minister.legendas.tv/util/carrega_legendas_busca/page:%s/id_filme:%s" % ("1", MainID["id"]))
            regResponse = re.findall(regex_2, Response)
            TotalPages = len(regResponse) +1
            # Form and execute threaded downloads
            for Page in range(TotalPages):
                Page += 1
                current = LTVThread(self, MainID , MainIDNumber, Page)
                self.RegThreads.append(current)
                current.start()
            MainIDNumber += 1
        # Wait for all threads to finish
        for t in self.RegThreads:
            t.join()
        # Sorting and filtering the results by episode, including season packs
        self.DownloadsResults = sorted(self.DownloadsResults, key=itemgetter('main_id_number', 'page', 'position'))
        IncludedResults = []
        ExcludedResult = []
        if TVShow:
            Episodes, Packs = [], [] 
            for DownloadsResult in self.DownloadsResults:
                if re.search("\(PACK", DownloadsResult["filename"]):
                    DownloadsResult["filename"] = re.sub("\(PACK[^\)]*?\)", "", DownloadsResult["filename"])
                if re.search("(^|\s|[.])[Ss]%.2d(\.|\s|$)" % int(Season), DownloadsResult["filename"]):
                    DownloadsResult["filename"] = "(PACK) " + DownloadsResult["filename"]
                    Packs.append(DownloadsResult) 
                elif re.search("[Ss]%.2d[Ee]%.2d" % (int(Season), int(Episode)), DownloadsResult["filename"]):
                    Episodes.append(DownloadsResult)
                elif re.search("x%.2d" % (int(Episode)), DownloadsResult["filename"]):
                    Episodes.append(DownloadsResult)
                else:
                    ExcludedResult.append(DownloadsResult)
            IncludedResults.extend(Packs)
            IncludedResults.extend(Episodes)
        elif Movie:
            IncludedResults.extend(self.DownloadsResults)
        IncludedResults = sorted(IncludedResults, key=itemgetter('language_preference'))

        # # Log final results
        self.Log(" ")
        self.Log("Included results:")
        self._log_List_dict(IncludedResults, "filename language_name language_preference ID")
        self.Log("Excluded results:") 
        self._log_List_dict(ExcludedResult, "filename language_name language_preference ID")
        self.Log("Message: The service took %s seconds to complete." % (time.time() - startTime))
        # Return results
        return IncludedResults

def _XBMC_Notification(StringID):
    xbmc.executebuiltin("Notification(Legendas.TV,%s,10000])"%( _( StringID ).encode('utf-8') ))
 
def search_subtitles(file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack):  # standard input
    try:
        global LTV
        LTV = LegendasTV()
        subtitles = ""
        if len(title): title = XBMC_OriginalTitle(title)
        elif len(tvshow): tvshow = XBMC_OriginalTitle(tvshow)
        cookie = LTV.login(__addon__.getSetting( "LTVuser" ), __addon__.getSetting( "LTVpass" ))
        if cookie:
            subtitles = LTV.Search(movie=title, tvshow=tvshow, year=year, season=season, 
                                   episode=episode, lang1=lang1, lang2=lang2, lang3=lang3)
        else:
            _XBMC_Notification(756)
        return subtitles, cookie, ""
    except:
        import traceback
        log(__name__, "\n%s" % traceback.format_exc())
        return "", "", _( 755 ).encode('utf-8')

def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    #Create some variables
    subtitle = ""
    extract_path = os.path.join(tmp_sub_dir, "extracted")
    id = subtitles_list[pos][ "ID" ]
    language = subtitles_list[pos][ "language_name" ]
    legendas_tmp = []
    # Download the subtitle using its ID.
    Response = urllib2.urlopen("http://minister.legendas.tv%s" % id).read()
    downloadID = re.findall(regex_3, Response)[0] if re.search(regex_3, Response) else 0
    if not downloadID: return ""
    response = urllib2.urlopen(urllib2.Request("http://minister.legendas.tv%s" % downloadID))
    ltv_sub = response.read()
    # Set the path of file concatenating the temp dir, the subtitle ID and a zip or rar extension.
    # Write the subtitle in binary mode.
    fname = os.path.join(tmp_sub_dir,"subtitle")
    if response.info().get("Content-Disposition").__contains__('rar'):
        fname += '.rar'
    else:
        fname += '.zip'
    f = open(fname,'wb')
    f.write(ltv_sub)
    f.close()

    # brunoga fixed solution for non unicode caracters
    # Ps. Windows allready parses Unicode filenames.
    fs_encoding = sys.getfilesystemencoding()
    extract_path = extract_path.encode(fs_encoding)

    # Use XBMC.Extract to extract the downloaded file, extract it to the temp dir, 
    # then removes all files from the temp dir that aren't subtitles.
    def extract_and_copy(extraction=0):
        i = 0
        for root, dirs, files in os.walk(extract_path, topdown=False):
            for file in files:
                dirfile = os.path.join(root, file)
                
                # Sanitize filenames - converting them to ASCII - and remove them from folders
                f = xbmcvfs.File(dirfile)
                temp = f.read()
                f.close()
                xbmcvfs.delete(dirfile)
                dirfile_with_path_name = os.path.relpath(dirfile, extract_path)
                dirfile_with_path_name = re.sub(r"[/\\]{1,2}","-", dirfile_with_path_name)
                dirfile_with_path_name = LTV._UNICODE(dirfile_with_path_name).encode('ascii', 'ignore')
                new_dirfile = os.path.join(extract_path, dirfile_with_path_name)
                os.write(os.open(new_dirfile, os.O_RDWR | os.O_CREAT), temp)
                
                # Get the file extention
                ext = os.path.splitext(new_dirfile)[1][1:].lower()
                if ext in sub_ext and xbmcvfs.exists(new_dirfile):
                    if not new_dirfile in legendas_tmp:
                        #Append the matching file
                        legendas_tmp.append(new_dirfile)
                elif ext in "rar zip" and not extraction:
                    # Extract compressed files, extracted priorly
                    xbmc.executebuiltin("XBMC.Extract(%s, %s)" % (new_dirfile, extract_path))
                    xbmc.sleep(1000)
                    extract_and_copy(1)
                elif ext not in "idx": 
                    xbmcvfs.delete(new_dirfile)
            for dir in dirs:
                dirfolder = os.path.join(root, dir)
                xbmcvfs.rmdir(dirfolder)

    xbmc.executebuiltin("XBMC.Extract(%s, %s)" % (fname, extract_path))
    xbmc.sleep(1000)
    extract_and_copy()
    
    temp = []
    for sub in legendas_tmp:
        video_file = LTV.chomp(os.path.basename(sys.modules[ "__main__" ].ui.file_original_path))
        sub_striped =  LTV.chomp(os.path.basename(sub))
        Ratio = LTV.CalculateRatio(sub_striped, video_file)
        temp.append([Ratio, sub])
    legendas_tmp = sorted(temp, reverse=True)
    
    if len(legendas_tmp) > 1:
        dialog = xbmcgui.Dialog()
        sel = dialog.select("%s\n%s" % (_( 30152 ).encode("utf-8"), subtitles_list[pos][ "filename" ]) ,
                             [os.path.basename(y) for x, y in legendas_tmp])
        if sel >= 0:
            subtitle = legendas_tmp[sel][1]
    elif len(legendas_tmp) == 1:
        subtitle = legendas_tmp[0][1]
    return False, language, subtitle
