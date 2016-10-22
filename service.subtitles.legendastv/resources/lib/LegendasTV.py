# -*- coding: UTF-8 -*-
# Copyright, 2010-2016, Guilherme Jardim.
# This program is distributed under the terms of the GNU General Public License, version 3.
# http://www.gnu.org/licenses/gpl.txt

def module_exists(module_name):
    try:
        __import__(module_name)
    except ImportError:
        return False
    else:
        return True

from operator import itemgetter
from threading import Thread
import cookielib
import math
import os
import unicodedata
import re
import sys
import time
import urllib
import urllib2
if module_exists("simplejson"):
    import simplejson
else:
    import json as simplejson

# Service variables
sub_ext = 'srt aas ssa sub smi'
global regex_1, regex_2, regex_3
regex_1 = "<div class=\"([^\"]*?)\">\s*?<span class=\"number .*?<div class=\"f_left\"><p><a href=\"([^\"]*)\">([^<]*)</a></p><p class=\"data\">.*?downloads, nota (\d*?),.*?<img .*? title=\"([^\"]*)\" /></div>"
regex_2 = "class=\"load_more\""
regex_3 = "<button class=\"icon_arrow\" onclick=\"window.open\(\'([^\']*?)\', \'_self\'\)\">DOWNLOAD</button>"

LANGUAGES      = (

    # Full Language name[0]     podnapisi[1]  ISO 639-1[2]   ISO 639-1 Code[3]   Script Setting Language[4]   localized name id number[5]

    ("English"                    , "2",        "en",            "eng",                 "11",                    30212  ),
    ("Portuguese"                 , "32",       "pt",            "por",                 "31",                    30233  ),
    ("Spanish"                    , "28",       "es",            "spa",                 "38",                    30240  ),
    ("English (US)"               , "2",        "en",            "eng",                 "100",                   30212  ),
    ("English (UK)"               , "2",        "en",            "eng",                 "100",                   30212  ),
    ("Portuguese (Brazil)"        , "48",       "pb",            "pob",                 "32",                    30234  ),
    ("Español (Latinoamérica)"    , "28",       "es",            "spa",                 "100",                   30240  ),
    ("Español (España)"           , "28",       "es",            "spa",                 "100",                   30240  ),
    ("Spanish (Latin America)"    , "28",       "es",            "spa",                 "100",                   30240  ),
    ("Español"                    , "28",       "es",            "spa",                 "100",                   30240  ),
    ("Spanish (Spain)"            , "28",       "es",            "spa",                 "100",                   30240  ) )

def languageTranslate(lang, lang_from, lang_to):
    for x in LANGUAGES:
        if lang == x[lang_from] :
            return x[lang_to]

def normalizeString(obj):
    try:
        return unicodedata.normalize('NFKD', unicode(unicode(obj, 'utf-8'))).encode('ascii','ignore')
    except:
        return unicode(str(obj).encode('string_escape'))
    
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

class FuncThread(Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs={}, Verbose=None):
        Thread.__init__(self, group, target, name, args, kwargs, Verbose)
        self._return = None

    def run(self):
        if self._Thread__target is not None:
            self._return = self._Thread__target(*self._Thread__args,**self._Thread__kwargs)

    def join(self):
        Thread.join(self)
        return self._return

class LegendasTV:
    def __init__(self, **kargs):
        self.RegThreads = []
        self.cookie = ""
    
    def Log(self, message, logtype = "NOTICE"):
        print "####  %s: %s" % (logtype, message.encode("utf-8"))
        
    def _urlopen(self, request):
        try:
            self.Log("Opening URL: (%s)" % request, "DEBUG" )
            return urllib2.urlopen(request, timeout=15)
        except urllib2.URLError as e:
            self.Log("Website (%s) could not be reached due to error: %s" % (request, str(e)), "ERROR" )
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
            request = urllib2.Request("http://legendas.tv/login", login_data)
            response = normalizeString(urllib2.urlopen(request).read())
            if response.__contains__(u'Usuário ou senha inválidos'):
                self.Log( u" Login Failed. Check your data at the addon configuration.")
                return None
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
        s = re.sub("[(][0-9]{4}[)]$", "", s)
        s = re.sub("[ ]?&[ ]?", " ", s)
        s = re.sub("'", " ", s)
        s = re.sub('\.(?!(\S[^. ])|\d)', '_', s)
        s = self.chomp(s)
        s = re.sub("_", ".", s)
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

    def findID(self, Movie, TVShow, Year, Season, IMDB, SearchTitle, SearchString):
        allResults, discardedResults, filteredResults, JSONContent, LTVSeason, LTVYear, LTVIMDB = [], [], [], [], 0, 0, None        
        # Load the results
        # Parse and filter the results
        self.Log("Message: Movie:[%s], TVShow:[%s], Year:[%s], Season:[%s], IMDB:[%s]" % (Movie, TVShow, Year, Season, IMDB))
        self.Log("Message: Searching for movie/tvshow list with term(s): [%s]" % SearchString)

        SearchElements = SearchString.split(" ")
        for x in xrange(0,len(SearchElements)):
            fromBegin = " ".join(SearchElements[:x])
            fromEnd   = " ".join(SearchElements[-x:])
            # print "fromBegin[%s] fromEnd[%s]" % (fromBegin, fromEnd)
            for search in [ fromBegin, fromEnd]:
                if len(search):
                    url     = "http://legendas.tv/legenda/sugestao/" + urllib.quote_plus(search)
                    current = FuncThread(target=self._urlopen, args=(url,))
                    current.start()
                    self.RegThreads.append(current)
            # Wait for all threads to finish
            for thread in self.RegThreads:
                try:
                    # Try if thread result is a valid JSON string
                    contents = simplejson.loads(unicode(thread.join().read(), 'utf-8', errors='ignore'))
                    for content in contents:
                        JSONContent.append(content)
                except:
                    # Continue if thread result is an invalid JSON string
                    pass

        for R in JSONContent:
            # print simplejson.dumps(R, sort_keys=True, indent=4, separators=(',', ': '))
            if R.has_key("_source"):
                ContentID = R['_id']
                # Continue if id already exists
                if filter(lambda id: id['id'] == ContentID, discardedResults) or filter(lambda id: id['id'] == ContentID, allResults):
                    continue
                Source    = R["_source"]
                LTVSeason = Source["temporada"] if Source["tipo"] == "S" and Source["temporada"] else 0
                LTVTitle  = self.CleanLTVTitle(Source['dsc_nome'])
                TitleBR   = self.CleanLTVTitle(Source['dsc_nome_br'])
                LTVYear   = Source["dsc_data_lancamento"] if Source["dsc_data_lancamento"].isdigit() else 0
                LTVIMDB   = Source["id_imdb"] if Source["id_imdb"] else None
                # Calculate the probability ratio and append the result
                Ratio     = self.CalculateRatio(LTVTitle, SearchTitle)
                Item      = {"id" : ContentID, "title" : LTVTitle, "ratio" : Ratio, "year" : LTVYear, "season" : LTVSeason, "imdb" : LTVIMDB}
                # If IMDB is supplied, try to filter using it
                if IMDB and LTVIMDB and re.search(LTVIMDB, IMDB):
                    allResults.append(Item)
                elif int(LTVYear) == int(Year):
                    allResults.append(Item)
                elif float(Ratio) > 0.5:
                    allResults.append(Item)
                else:
                    discardedResults.append(Item)
        # Extend with the older version
        if not len(allResults):
            self.Log("Extending results...")
            Response = self._urlopen("http://minister.legendas.tv/util/busca_titulo/" + urllib.quote_plus(SearchString)).read()
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
                    Item  = {"id" : ContentID, "title" : LTVTitle, "ratio" : Ratio, "year" : 0, "season" : LTVSeason, "imdb" : ""}
                    allResults.append(Item)

        # Return if there are no results
        if not len(allResults):
            self.Log("Message: The search [%s] didn't returned viable results." % SearchString)
            self.Log(" ")
            self.Log("Discarded results:")
            self._log_List_dict(discardedResults, "ratio year title season id imdb")
            return "", ""
        # Filter tvshows for season or movies by year
        else:
            allResults       = sorted(allResults, key=lambda k: k["ratio"], reverse=True)
            partialMatch = []
            for Result in allResults:
                if TVShow:
                    if int(Season) == int(Result["season"]):
                        filteredResults.append(Result)
                    elif not Result["season"] and Result["ratio"] == "1.00":
                        partialMatch.append(Result)
                    else:
                        discardedResults.append(Result)

                elif Movie:
#                     if abs(int(Result["year"]) - int(Year)) <= 1 and math.fabs(float(Result["ratio"]) - float(allResults[0]["ratio"])) <= 0.25:
                    if math.fabs(float(Result["ratio"]) - float(allResults[0]["ratio"])) <= 0.25:
                        filteredResults.append(Result)
                    else:
                        discardedResults.append(Result)
            if not len(filteredResults):
                filteredResults.extend(partialMatch)
            discardedResults = sorted(discardedResults, key=lambda k: k["ratio"], reverse=True)
            if not len(filteredResults):
                self.Log("Message: After filtration, search [%s] didn't returned viable results." % SearchString)
                self.Log("Discarded results:")
                self._log_List_dict(discardedResults, "ratio year title season id imdb")
                return discardedResults, ""
            else:
                # Log filtered results
                self.Log("Message: After filtration, the search [%s] returned %s viable results." % (SearchString, len(filteredResults)))
                self.Log(" ")
                self.Log("Viable results:")
                self._log_List_dict(filteredResults, "ratio year title season id imdb")
                self.Log("Discarded results:")
                self._log_List_dict(discardedResults, "ratio year title season id imdb")
                return discardedResults, filteredResults
            
    def pageDownload(self, MainID, MainIDNumber, Page):
        # Log the page download attempt.
        self.Log("Message: Retrieving page [%s] for Movie[%s], Id[%s]." % (Page, MainID["title"], MainID["id"]))
        
#        Response = self._urlopen("http://minister.legendas.tv/util/carrega_legendas_busca/page:%s/id_filme:%s" % (Page, MainID["id"]))
        Response = self._urlopen("http://legendas.tv/util/carrega_legendas_busca_filme/%s/-/-/%s" % (MainID["id"], Page)).read()
        if not re.findall(regex_1, Response, re.IGNORECASE | re.DOTALL):
            self.Log("Error: Failed retrieving page [%s] for Movie[%s], Id[%s]." % (Page, MainID["title"], MainID["id"]))
        else:
            for x, content in enumerate(re.findall(regex_1, Response, re.IGNORECASE | re.DOTALL), start=1):
                LanguageName, LanguageFlag, LanguagePreference = "", "", 0
                download_id = "%s%s" % ("http://legendas.tv", content[1])
                release_type = content[0] if not content[0] == "" else "zero"
                title = normalizeString(content[2])
                release = normalizeString(content[2])
                rating =  content[3]
                lang = normalizeString(content[4])
                if re.search("Portugues-BR", lang):   LanguageId = "pb" 
                elif re.search("Portugues-PT", lang): LanguageId = "pt"
                elif re.search("Ingles", lang):       LanguageId = "en" 
                elif re.search("Espanhol", lang):     LanguageId = "es"
                elif re.search("Frances", lang):      LanguageId = "fr"
                else: continue
                for Preference, LangName in self.Languages:
                    if LangName == languageTranslate(LanguageId, 2, 0):
                        LanguageName = LangName
                        LanguageFlag = LanguageId
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
                                              "url": download_id,
                                              "format": "srt",
                                              "sync": False,
                                              "rating":rating,
                                              "language_flag": LanguageFlag,
                                              "language_preference": int(LanguagePreference),
                                              "type" : release_type})

            self.Log("Message: Retrieved [%s] results for page [%s], Movie[%s], Id[%s]." % (x, Page, MainID["title"], MainID["id"]))


    def Download(self, url):
        Response = self._urlopen(url).read()
        downloadID = re.findall(regex_3, Response)[0] if re.search(regex_3, Response) else 0
        if not downloadID:
            return None, None
        Response = self._urlopen("http://legendas.tv%s" % downloadID)
        Sub = Response.read()
        Type = 'rar' if Response.url.__contains__('.rar') else 'zip'
        return Sub, Type

    def Search(self, **kargs):   
        # Init all variables
        startTime = time.time()
        filteredResults, self.DownloadsResults, self.Languages = [], [], []
        Movie, TVShow, Year, Season, Episode, IMDB = "", "", 0, 0, 0, ""
        for key, value in kargs.iteritems():
            if key == "title":             Movie   = self.CleanLTVTitle(value)
            if key == "tvshow":            TVShow  = self.CleanLTVTitle(value)
            if key == "year"    and value: Year    = int(value)
            if key == "season"  and value: Season  = int(value)
            if key == "episode" and value: Episode = int(value)
            if key == "imdb"    and value: IMDB    = value
            if key == "lang"    and value:
                for x, lang in enumerate(value):
                    self.Languages.append((x, lang))
        self.Languages.sort()

        self.Log("IMDB: "+IMDB)

        if TVShow:
            SearchTitle = TVShow
        else:
            SearchTitle = Movie

        discardedResults, filteredResults = "", ""
        discardedResults, filteredResults = self.findID(Movie, TVShow, Year, Season, IMDB, SearchTitle, SearchTitle)
        # if not filteredResults:
        #     # Searching for movie titles/tvshow ids using the lengthiest words
        #     if len(SearchTitle.split(" ")):
        #         for SearchString in sorted(SearchTitle.split(" "), key=len, reverse=True):
        #             if SearchString in [ 'The', 'O', 'A', 'Os', 'As', 'El', 'La', 'Los', 'Las', 'Les', 'Le' ] or len(SearchString) < 2:
        #                 continue
        #             discardedResults, filteredResults = self.findID(Movie, TVShow, Year, Season, IMDB, SearchTitle, SearchString)
        #             if filteredResults: 
        #                 break
        #     else:
        #         discardedResults, filteredResults = self.findID(Movie, TVShow, Year, Season, IMDB, SearchTitle, SearchTitle)
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
            TotalPages=3
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
                if DownloadsResult["type"] == "pack":
                    if re.search("\(PACK", DownloadsResult["filename"]):
                        DownloadsResult["filename"] = re.sub("\(PACK[^\)]*?\)", "", DownloadsResult["filename"])
                    if re.search("\([Pp]\)", DownloadsResult["filename"]):
                        DownloadsResult["filename"] = re.sub("\([Pp]\)", "", DownloadsResult["filename"])
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
        IncludedResults = sorted(IncludedResults, key=itemgetter('type', 'language_preference'))

        # # Log final results
        self.Log(" ")
        self.Log("Included results:")
        self._log_List_dict(IncludedResults, "filename language_name language_preference type")
        self.Log("Excluded results:") 
        self._log_List_dict(ExcludedResult, "filename language_name language_preference type")
        self.Log("Message: The service took %0.2f seconds to complete." % (time.time() - startTime))
        # Return results
        return IncludedResults
