# -*- coding: UTF-8 -*-
# Copyright, 2010, Guilherme Jardim.
# This program is distributed under the terms of the GNU General Public License, version 3.
# http://www.gnu.org/licenses/gpl.txt
# Rev. 2.0.0

from operator import itemgetter
from threading import Thread
from BeautifulSoup import *
from utilities import log, languageTranslate
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
global regex_1, regex_2
regex_1 = "<span onmouseover=.*?javascript:abredown\(\'(.*?)\'.*?class=\"mais\"><b>(.*?)<\/b>.*?Avalia.*?<\/b> (.*?)<\/td>.*?<img src=\'images\/flag_(..).gif.*?<span class=\"brls\">(.*?)<\/span>"
regex_2 = "<a class=\"paginacaoatual\" href=\".*\">.*</a>\s+<a class=\"paginacao\" href=\".*\">(.*)</a>"

# XBMC specific variables
_ = sys.modules[ "__main__" ].__language__
__scriptname__ = sys.modules[ "__main__" ].__scriptname__
__addon__ = sys.modules[ "__main__" ].__addon__

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

    def login(self, username, password):
        if self.cookie:
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookie))
            urllib2.install_opener(opener)
            return self.cookie
        else:
            self.cookie = cookielib.CookieJar()
            opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookie))
            urllib2.install_opener(opener)
            login_data = urllib.urlencode({'txtLogin':username, 'txtSenha':password})
            request = urllib2.Request("http://legendas.tv/login_verificar.php", login_data)
            response = urllib2.urlopen(request).read()
            if response.__contains__('Dados incorretos'):
                self.Log( u" Login Failed. Check your data at the addon configuration.")
                return 0
            else: 
                return self.cookie

    def chomp(self, s):
        s = re.sub("\s{2,20}", " ", s)
        a = re.compile("(\r|\n|^\s|\s$|\'|\"|,|;|[(]|[)])")
        b = re.compile("(\t|-|:|[/]|[?]|\[|\])")
        s = b.sub(" ", s)
        s = re.sub("[ ]{2,20}", " ", s)
        s = a.sub("", s)
        return s

    def CleanLTVTitle(self, s):
        s = re.sub("[(]?[0-9]{4}[)]?$", "", s)
        s = re.sub("[ ]?&[ ]?", " and ", s)
        s = re.sub("'", " ", s)
        s = self.chomp(s)
        s = s.title()
        return s
    
    def _UNICODE(self,text):
        if text:
            return unicode(BeautifulSoup(text, smartQuotesTo=None))
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
                if re.search("(^|\s)%s(\s|$)" % Term, Guess, re.I):
                    counter += 1
            if counter:
                Ratio = "%.2f" % (float(counter) / float(len(Paradigm.split(" "))))
            else:
                Ratio = "%.2f" % float(0)
        else:
            if re.search("(^|\s)%s(\s|$)" % Paradigm, Guess, re.I):
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
    
    def XBMC_OriginalTitle(self, OriginalTitle):
        json_query = xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.GetItem", "params": { "playerid": 1} ,"id":1}' )
        json_player_getitem = simplejson.loads(unicode(json_query, 'utf-8', errors='ignore'))
#        self.Log("JSON_RPC: %s" % (json_player_getitem))
        if json_player_getitem.has_key('result') and json_player_getitem['result'].has_key('item') and json_player_getitem['result']['item'].has_key('id') and json_player_getitem['result']['item'].has_key('type'):
            if json_player_getitem['result']['item']['type'] == "movie":
                json_query = xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"VideoLibrary.GetMovieDetails", "params": { "movieid": %s, "properties": ["originaltitle"]} ,"id":1}' % (json_player_getitem['result']['item']['id']) )
                json_getmoviedetails = simplejson.loads(unicode(json_query, 'utf-8', errors='ignore'))
#                self.Log("JSON_RPC: %s" % (json_getmoviedetails))
                if json_getmoviedetails.has_key('result') and json_getmoviedetails['result'].has_key('moviedetails') and json_getmoviedetails['result']['moviedetails'].has_key('originaltitle'):
                    OriginalTitle = json_getmoviedetails['result']['moviedetails']['originaltitle']
            elif json_player_getitem['result']['item']['type'] == "episode":
                json_query = xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"VideoLibrary.GetEpisodeDetails", "params": { "episodeid": %s, "properties": ["originaltitle", "tvshowid"]} ,"id":1}' % (json_player_getitem['result']['item']['id']) )
                json_getepisodedetails = simplejson.loads(unicode(json_query, 'utf-8', errors='ignore'))
#                self.Log("JSON_RPC: %s" % (json_getepisodedetails))
                if json_getepisodedetails.has_key('result') and json_getepisodedetails['result'].has_key('episodedetails') and json_getepisodedetails['result']['episodedetails'].has_key('tvshowid'):
                    json_query = xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"VideoLibrary.GetTVShowDetails", "params": { "tvshowid": %s, "properties": ["originaltitle", "imdbnumber"]} ,"id":1}' % (json_getepisodedetails['result']['episodedetails']['tvshowid']) )
                    json_gettvshowdetails = simplejson.loads(unicode(json_query, 'utf-8', errors='ignore'))
#                    self.Log("JSON_RPC: %s" % (json_gettvshowdetails))
                    if json_gettvshowdetails.has_key('result') and json_gettvshowdetails['result'].has_key('tvshowdetails') and json_gettvshowdetails['result']['tvshowdetails'].has_key('imdbnumber'):
                        thetvdb = json_gettvshowdetails['result']['tvshowdetails']['imdbnumber']
                        HTTPResponse = urllib2.urlopen("http://www.thetvdb.com//data/series/"+str(thetvdb)+"/").read()
                        if re.findall("<SeriesName>(.*?)</SeriesName>", HTTPResponse, re.IGNORECASE | re.DOTALL):
                            OriginalTitle = re.findall("<SeriesName>(.*?)</SeriesName>", HTTPResponse, re.IGNORECASE | re.DOTALL)[0]
        OriginalTitle = self._UNICODE(OriginalTitle)
        self.Log("Original title: %s" % OriginalTitle)
        OriginalTitle = OriginalTitle.encode('ascii', 'replace')
        OriginalTitle = self.CleanLTVTitle(OriginalTitle)
        return OriginalTitle

    def findID(self, Movie, TVShow, Year, Season, SearchTitle, SearchString):
        allResults, discardedResults, filteredResults, LTVSeason, LTVYear = [], [], [], 0, 0
        Response = urllib2.urlopen("http://legendas.tv/funcao_lista_filme.php?busca=" +urllib.quote_plus(SearchString)).read()
        # Load the results
        # Parse and filter the results
        self.Log("Message: Searching for movie/tvshow list with term(s): [%s]" % SearchString)
        for ContentID, ContentTitle in re.findall("<option value=\"(\d*?)\">([^<]*?)</option>", Response):
            # Discard bogus results
            if int(ContentID) == 9999999999: continue
            # Search and filter for tvshows or movies
            regex = "(\d{4})(.*?)(\d{1,2})[a-zA-Z]{2} [Ss]eason"
            if re.search(regex, ContentTitle) and TVShow:
                LTVYear, LTVTitle, LTVSeason = re.findall(regex, ContentTitle)[0]
            elif re.search("(\d{4}) - (.*)", ContentTitle):
                LTVYear, LTVTitle = re.findall("(\d{4}) - (.*)", ContentTitle)[0]
                LTVSeason = 0
            else:
                continue
            LTVTitle = self._UNICODE(LTVTitle)
            LTVTitle = self.CleanLTVTitle(LTVTitle)   
            # Calculate the probability ratio and append the result
            Ratio = self.CalculateRatio(LTVTitle, SearchTitle)
            allResults.append({"id" : ContentID, "title" : LTVTitle, "ratio" : Ratio, "year" : LTVYear, "season" : LTVSeason})
        # Return if there are no results
        if not len(allResults):
            self.Log("Message: The search [%s] didn't returned viable results." % SearchString)
            return "",""
        # Filter tvshows for season or movies by year
        else:
            allResults = sorted(allResults, key=lambda k: k["ratio"], reverse=True)
            for Result in allResults:
                if TVShow:
                    if int(Season) == int(Result["season"]):
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
                    if abs(int(Result["year"]) - int(Year)) <= 1 and math.fabs(float(Result["ratio"]) - float(allResults[0]["ratio"])) <= 0.25:
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
        
        Response = urllib2.urlopen("http://legendas.tv/index.php?opcao=buscarlegenda&filme=%s&pagina=%s" % (MainID["id"], Page)).read()

        if not re.findall(regex_1, Response, re.IGNORECASE | re.DOTALL):
            self.Log("Error: Failed retrieving page [%s] for Movie[%s], Id[%s]." % (Page, MainID["title"], MainID["id"]))
        else:
            for x, content in enumerate(re.findall(regex_1, Response, re.IGNORECASE | re.DOTALL), start=1):
                LanguageName, LanguageFlag, LanguagePreference = "", "", 0
                download_id = content[0]
                title = self._UNICODE(content[1])
                release = self._UNICODE(content[4])
                if re.search("\d*/10", content[2]):
                    rating = re.findall("(\d*)/10", content[2])[0]
                else:
                    rating = "0"  
                if content[3] ==   "br": LanguageId = "pb" 
                elif content[3] == "pt": LanguageId = "pt" 
                elif content[3] == "us": LanguageId = "en" 
                elif content[3] == "es": LanguageId = "es"
                elif content[3] == "fr": LanguageId = "fr"
                else: continue
                for Preference, LangName in self.Languages:
                    if LangName == languageTranslate(LanguageId,2,0):
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
        ## Correct parsed values, grab original tvshow name/movie title, and allow manual search to be done
        if sys.modules[ "__main__" ].ui.man_search_str:
            if re.findall("(.*?)[Ss](\d{1,2})[Ee](\d{1,2})", Movie):
                TVShow, Season, Episode = re.findall("(.*?)[Ss](\d{1,2})[Ee](\d{1,2})", Movie)[0]
                TVShow = self.CleanLTVTitle(self._UNICODE(TVShow))
                Season, Episode = int(Season), int(Episode)
                Movie = ""
        elif Movie:
            Movie = self.XBMC_OriginalTitle(Movie)
        elif TVShow: 
            TVShow = self.XBMC_OriginalTitle(TVShow)
        if Movie: SearchTitle = Movie
        else: SearchTitle = TVShow
        
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
            for Result in discardedResults:
                if Result["ratio"] == discardedResults[0]["ratio"]:
                    filteredResults.append(Result)
            self.Log("Message: Filtration failed, using discarded results.")
        elif not filteredResults:
            return ""
        # Initiate the "buscalegenda" search to search for all types and languages
        search_data = urllib.urlencode({'txtLegenda':"-=-=-=-=-", 'selTipo':'1', 'int_idioma':'99'})
        request = urllib2.Request("http://legendas.tv/index.php?opcao=buscarlegenda&filme=1", search_data)
        Response = urllib2.urlopen(request).read()
        MainIDNumber = 1
        for MainID in filteredResults:
            # Find how much pages are to download
            self.Log("Message: Retrieving results to id[%s]" % (MainID["id"]))
            Response = urllib2.urlopen("http://legendas.tv/funcao_lista_legenda.php?f=%s" % (MainID["id"])).read()
            TotalPages = int(math.ceil(len(re.findall("<img src=[^>]*>([^<]*)</span></td>", Response))/20.0))
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

        ## Log final results
        self.Log(" ")
        self.Log("Included results:")
        self._log_List_dict(IncludedResults, "filename language_name language_preference ID")
        self.Log("Excluded results:") 
        self._log_List_dict(ExcludedResult, "filename language_name language_preference ID")
        self.Log("Message: The service took %s seconds to complete." % (time.time()-startTime))
        # Return results
        return IncludedResults

def _XBMC_Notification(StringID):
    xbmc.executebuiltin("Notification(Legendas.TV,%s,10000])"%( _( StringID ).encode('utf-8') ))
 
def search_subtitles(file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack):  # standard input
    try:
        global LTV
        LTV = LegendasTV()
        subtitles = ""
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
    request =  urllib2.Request("http://legendas.tv/info.php?d=%s&c=1" % id)
    response = urllib2.urlopen(request)
    ltv_sub = response.read()
    
    # Set the path of file concatenating the temp dir, the subtitle ID and a zip or rar extension.
    # Write the subtitle in binary mode.
    fname = os.path.join(tmp_sub_dir,str(id))
    if response.info().get('Content-Type').__contains__('rar'):
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
                dirfile_with_path_name = re.sub(extract_path + r"[/\\]{1,2}","", dirfile)
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

    if len(legendas_tmp) > 1:
        dialog = xbmcgui.Dialog()
        sel = dialog.select("%s\n%s" % (_( 30152 ).encode("utf-8"), subtitles_list[pos][ "filename" ]) ,
                             [os.path.basename(x) for x in legendas_tmp])
        if sel >= 0:
            subtitle = legendas_tmp[sel]
    elif len(legendas_tmp) == 1:
        subtitle = legendas_tmp[0]
    return False, language, subtitle
