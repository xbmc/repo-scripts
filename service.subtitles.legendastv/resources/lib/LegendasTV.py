import json
import math
import re
import time
from collections import defaultdict
from http.cookiejar import CookieJar
from operator import itemgetter
from threading import Thread
from urllib.error import URLError
from urllib.parse import quote_plus, urlencode
from urllib.request import Request, \
    urlopen, \
    build_opener, \
    install_opener, \
    HTTPCookieProcessor

from resources.lib.LTVutilities import normalizeString, log

# Service variables
sub_ext = (
    'srt',
    'aas',
    'ssa',
    'sub',
    'smi'
)
regex_1 = re.compile(
    r"<div class=\"([^\"]*?)\">\s*?<span class=\"number .*?<div class=\"f_left\"><p><a href=\"([^\"]*)\">([^<]*)</a></p><p class=\"data\">.*?downloads, nota (\d*?),.*?<img .*? title=\"([^\"]*)\" /></div>",
    flags=re.IGNORECASE | re.DOTALL)
regex_2 = re.compile(r"class=\"load_more\"")
regex_3 = re.compile(r"http://legendas\.tv/download/([^/]*?)/")

LANGUAGES = (
    # Full Language name [0]
    # podnapisi [1]
    # ISO 639-1 [2]
    # ISO 639-1 Code[3]
    # Script Setting Language[4]
    # Localized name id number[5]
    ("English", "2", "en", "eng", "11", 30212),
    ("Portuguese", "32", "pt", "por", "31", 30233),
    ("Spanish", "28", "es", "spa", "38", 30240),
    ("English (US)", "2", "en", "eng", "100", 30212),
    ("English (UK)", "2", "en", "eng", "100", 30212),
    ("Portuguese (Brazil)", "48", "pb", "pob", "32", 30234),
    ("Español (Latinoamérica)", "28", "es", "spa", "100", 30240),
    ("Español (España)", "28", "es", "spa", "100", 30240),
    ("Spanish (Latin America)", "28", "es", "spa", "100", 30240),
    ("Español", "28", "es", "spa", "100", 30240),
    ("Spanish (Spain)", "28", "es", "spa", "100", 30240)
)


def languageTranslate(lang, lang_from, lang_to):
    for x in LANGUAGES:
        if lang == x[lang_from]:
            return x[lang_to]


class LTVThread(Thread):
    def __init__(self, obj, count, main_id, page):
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
    def __init__(
            self,
            group=None,
            target=None,
            name=None,
            args=(),
            kwargs=None):
        if kwargs is None:
            kwargs = {}
        Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None

    def run(self):
        if self._target is not None:
            self._return = self._target(
                *self._args,
                **self._kwargs)

    def join(self, *args):
        Thread.join(self, *args)
        return self._return


def get_episode_range(DownloadsResult, Season):
    name = DownloadsResult["filename"]
    episode_patterns = (
        re.search(r"S%.2d[.x]?E([0-9]{2,})(?:-(?:S%.2d[.x]?E|E)?([0-9]{2,}))?(?:[._-]|\s|$)" % (Season, Season), name, flags=re.I),
        re.search(r"%.2d[.x]([0-9]+)(?:%.2d[.x])?(?:-([0-9]+))?(?:[._-]|\s|$)" % (Season, Season), name, flags=re.I),
        re.search(r"%d[.x]([0-9]+)(?:%d[.x])?(?:-([0-9]+))?(?:[._-]|\s|$)" % (Season, Season), name, flags=re.I),
        re.search(
                  r"S?%.2d(?:[.x]|[.x]?E)([0-9]+)(?:[._-]|\s)+(?:ao|to|-)(?:[._-]|\s)+(?:S?%.2d(?:[.x]|[.x]?E))?([0-9]+)(?:[._-]|\s|$)" %
                  (Season, Season),
                  name,
                  flags=re.I),
        re.search(
                  r"S?%d(?:[.x]|[.x]?E)([0-9]+)(?:[._-]|\s)+(?:ao|to|-)(?:[._-]|\s)+(?:S?%d(?:[.x]|[.x]?E))?([0-9]+)(?:[._-]|\s|$)" %
                  (Season, Season),
                  name,
                  flags=re.I)
    )
    candidates = []
    for pattern in episode_patterns:
        if pattern and pattern:
            minimum, maximum = pattern.group(1), pattern.group(2)
            log(f"{name} got range {(minimum, maximum)}")
            if maximum:
                return int(minimum.lstrip('0')), int(maximum.lstrip('0'))
            candidates.append((int(minimum.lstrip('0')),))
    if candidates:
        return candidates[0]
    return ()


def calculate_pack_score(DownloadsResult, Season, Episode) -> int:
    if DownloadsResult["type"] == "pack":
        return 1

    name = DownloadsResult["filename"]
    if re.search(r"\(PACK[^)]*\)", name, flags=re.I) \
            or re.search(r"\(P\)", name, flags=re.I):
        return 2

    episode_range = get_episode_range(DownloadsResult, Season)
    log("%s got range %s" % (name, episode_range))
    if len(episode_range) == 1:
        return 0
    elif len(episode_range) == 2:
        return 3 if (episode_range[0] <= Episode <= episode_range[1]) else 0

    if re.search(r"%d[a]?([._-]|\s)+temporada" % Season, name, flags=re.I) \
            or re.search(r"%.2d[a]?([._-]|\s)+temporada" % Season, name, flags=re.I) \
            or re.search(r"season([._-]|\s)+%d" % Season, name, flags=re.I) \
            or re.search(r"season([._-]|\s)+%.2d" % Season, name, flags=re.I) \
            or re.search(r"S%.2d([._-]|\s)+[^E]" % Season, name, flags=re.I):
        return 4

    if re.search(r"([._-]|\s)complet[ae]([._-]|\s)", name, flags=re.I):
        return 5

    return 0


class LegendasTV:
    def __init__(self):
        self.RegThreads = []
        self.cookie = ""

    def Log(self, message, logtype="INFO"):
        print("####  %s: %s" % (logtype, message))

    def _urlopen(self, request):
        try:
            self.Log("Opening URL: (%s)" % request, "DEBUG")
            return urlopen(request, timeout=15)
        except URLError as e:
            self.Log("Website (%s) could not be reached due to error: %s" % (
                request, str(e)), "ERROR")
            return ""

    def login(self, username, password):
        if self.cookie:
            opener = build_opener(
                HTTPCookieProcessor(self.cookie))
            install_opener(opener)
            return self.cookie
        else:
            self.cookie = CookieJar()
            opener = build_opener(
                HTTPCookieProcessor(self.cookie))
            install_opener(opener)
            login_data = urlencode({
                '_method': 'POST',
                'data[User][username]': username,
                'data[User][password]': password
            })
            request = Request("http://legendas.tv/login", login_data.encode('utf-8'))
            response = normalizeString(urlopen(request).read())
            if response.__contains__('Usuario ou senha invalidos'):
                self.Log(
                    "Login Failed. Check your data at the addon configuration.")
                return None
            else:
                return self.cookie

    def chomp(self, s):
        s = re.sub(r"\s{2,20}", " ", s)
        a = re.compile(r"(\r|\n|^\s|\s$|'|\"|,|;|[(]|[)])")
        b = re.compile(r"(\t|-|:|[/]|[?]|\[|]|\.)")
        s = b.sub(r" ", s)
        s = re.sub(r"[ ]{2,20}", " ", s)
        s = a.sub(r"", s)
        return s

    def CleanLTVTitle(self, s):
        s = re.sub(r"[(][0-9]{4}[)]$", "", s)
        s = re.sub(r"[ ]?&[ ]?", " ", s)
        s = re.sub(r"'", " ", s)
        s = re.sub(r'\.(?!(\S[^. ])|\d)', '_', s)
        s = self.chomp(s)
        s = re.sub(r"_", ".", s)
        s = s.title()
        return s

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
                if re.search(r"(^|\s)%s(\s|$)" % re.escape(Term), Guess, flags=re.I):
                    counter += 1
            if counter:
                Ratio = "%.2f" % (
                        float(counter) / float(len(Paradigm.split(" "))))
            else:
                Ratio = "%.2f" % float(0)
        else:
            if re.search(r"(^|\s)%s(\s|$)" % re.escape(Paradigm), Guess, flags=re.I):
                Ratio = "%.2f" % float(1)
            else:
                Ratio = "%.2f" % float(0)
        return Ratio

    def _log_List_dict(self, obj, keys="", maxsize=100):
        Content = ""
        if not len(obj):
            return 0
        for key in keys.split():
            if key not in obj[0]:
                continue
            maximum = max(len(str(k[key])) for k in obj)
            maximum = max(maximum + 2, len(key) + 2)
            if maximum > maxsize:
                maximum = maxsize
            Content = Content + "%s" % str(key)[:maxsize - 2].ljust(maximum)
        self.Log(Content)
        for x, Result in enumerate(obj):
            Content = ""
            for key in keys.split():
                if key not in obj[0]:
                    continue
                value = str(Result[key])
                if not len(value):
                    continue
                maximum = max(len(str(k[key])) for k in obj)
                maximum = max(maximum + 2, len(str(key)) + 2)
                if maximum > maxsize:
                    maximum = maxsize
                Content = Content + "%s" % value[:maxsize - 2].ljust(maximum)
            self.Log(Content)
            if x > 30:
                if len(obj) >= x:
                    self.Log('...')
                break
        self.Log(" ")
        return 0

    def findID(self, Movie, TVShow, Year, Season, IMDB, SearchTitle,
            SearchString):
        allResults, discardedResults, filteredResults, JSONContent, LTVSeason, LTVYear, LTVIMDB = [], [], [], [], 0, 0, None
        # Load the results
        # Parse and filter the results
        self.Log(
            "Message: Movie:[%s], TVShow:[%s], Year:[%s], Season:[%s], IMDB:[%s]" % (
                Movie, TVShow, Year, Season, IMDB))
        self.Log(
            "Message: Searching for movie/tvshow list with term(s): [%s]" % SearchString)

        SearchElements = SearchString.split(" ")
        for x in range(0, len(SearchElements)):
            fromBegin = " ".join(SearchElements[:x])
            fromEnd = " ".join(SearchElements[-x:])
            # print("fromBegin[%s] fromEnd[%s]" % (fromBegin, fromEnd))
            for search in [fromBegin, fromEnd]:
                if len(search):
                    url = "http://legendas.tv/legenda/sugestao/%s" \
                          % quote_plus(search)
                    current = FuncThread(target=self._urlopen, args=(url,))
                    current.start()
                    self.RegThreads.append(current)
            # Wait for all threads to finish
            for thread in self.RegThreads:
                try:
                    # Try if thread result is a valid JSON string
                    contents = json.loads(thread.join().read())
                    for content in contents:
                        JSONContent.append(content)
                except:
                    # Continue if thread result is an invalid JSON string
                    pass

        for R in JSONContent:
            # print json.dumps(R, sort_keys=True, indent=4, separators=(',', ': '))
            if "_source" in R:
                ContentID = R['_id']
                # Continue if id already exists
                if [id for id in discardedResults if id['id'] == ContentID] or [
                    id for id in allResults if id['id'] == ContentID]:
                    continue
                Source = R["_source"]
                LTVSeason = Source["temporada"] if Source["tipo"] == "S" and \
                                                   Source["temporada"] else 0
                LTVTitle = self.CleanLTVTitle(Source['dsc_nome'])
                TitleBR = self.CleanLTVTitle(Source['dsc_nome_br'])
                LTVYear = Source["dsc_data_lancamento"] if Source[
                    "dsc_data_lancamento"].isdigit() else 0
                LTVIMDB = Source["id_imdb"] if Source["id_imdb"] else None
                # Calculate the probability ratio and append the result
                Ratio = self.CalculateRatio(LTVTitle, SearchTitle)
                Item = {
                    "id": ContentID,
                    "title": LTVTitle,
                    "ratio": Ratio,
                    "year": LTVYear,
                    "season": LTVSeason,
                    "imdb": LTVIMDB
                }
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
            Response = self._urlopen("http://legendas.tv/util/busca_titulo/%s"
                                     % quote_plus(SearchString))
            Response = json.loads(Response.read())
            # Load the results
            # Parse and filter the results
            self.Log(
                "Message: Searching for movie/tvshow list with term(s): [%s]" % SearchString)
            for R in Response:
                LTVSeason = 0
                if 'Filme' in R and 'dsc_nome' in R['Filme']:
                    LTVTitle = self.CleanLTVTitle(R['Filme']['dsc_nome'])
                    TitleBR = R['Filme']['dsc_nome_br']
                    if re.findall(r".*? - (\d{1,2}).*?emporada", TitleBR):
                        LTVSeason = \
                            re.findall(r".*? - (\d{1,2}).*?emporada", TitleBR)[0]
                    ContentID = R['Filme']['id_filme']
                    # Calculate the probability ratio and append the result
                    Ratio = self.CalculateRatio(LTVTitle, SearchTitle)
                    Item = {
                        "id": ContentID,
                        "title": LTVTitle,
                        "ratio": Ratio,
                        "year": 0,
                        "season": LTVSeason,
                        "imdb": ""
                    }
                    allResults.append(Item)

        # Return if there are no results
        if not len(allResults):
            self.Log(
                "Message: The search [%s] didn't returned viable results." % SearchString)
            self.Log(" ")
            self.Log("Discarded results:")
            self._log_List_dict(discardedResults,
                                "ratio year title season id imdb")
            return "", ""
        # Filter tvshows for season or movies by year
        else:
            allResults = sorted(allResults, key=lambda k: k["ratio"],
                                reverse=True)
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
                    if math.fabs(float(Result["ratio"]) - float(
                            allResults[0]["ratio"])) <= 0.25:
                        filteredResults.append(Result)
                    else:
                        discardedResults.append(Result)
            if not len(filteredResults):
                filteredResults.extend(partialMatch)
            discardedResults = sorted(discardedResults,
                                      key=lambda k: k["ratio"], reverse=True)
            if not len(filteredResults):
                self.Log(
                    "Message: After filtration, search [%s] didn't returned viable results." % SearchString)
                self.Log("Discarded results:")
                self._log_List_dict(discardedResults,
                                    "ratio year title season id imdb")
                return discardedResults, ""
            else:
                # Log filtered results
                self.Log(
                    "Message: After filtration, the search [%s] returned %s viable results." % (
                        SearchString, len(filteredResults)))
                self.Log(" ")
                self.Log("Viable results:")
                self._log_List_dict(filteredResults,
                                    "ratio year title season id imdb")
                self.Log("Discarded results:")
                self._log_List_dict(discardedResults,
                                    "ratio year title season id imdb")
                return discardedResults, filteredResults

    def pageDownload(self, MainID, MainIDNumber, Page):
        # Log the page download attempt.
        self.Log("Message: Retrieving page [%d] for Movie[%s], Id[%s]." % (
            Page, MainID["title"], MainID["id"]))

        #        Response = self._urlopen("http://legendas.tv/util/carrega_legendas_busca/page:%s/id_filme:%s" % (Page, MainID["id"]))
        Response = self._urlopen(
            "http://legendas.tv/legenda/busca/-/-/-/%s/%s" % (
                Page, MainID["id"])).read().decode('utf-8')
        if not regex_1.findall(Response):
            self.Log(
                "Error: Failed retrieving page [%d] for Movie[%s], Id[%s]." % (
                    Page, MainID["title"], MainID["id"]))
        else:
            results = regex_1.findall(Response)
            for x, content in enumerate(results, start=1):
                LanguageName, LanguageFlag, LanguagePreference = "", "", 0
                download_id = "%s%s" % ("http://legendas.tv", content[1])
                release_type = content[0] if not content[0] == "" else "zero"
                title = normalizeString(content[2])
                release = normalizeString(content[2])
                rating = content[3]
                lang = normalizeString(content[4])
                if re.search(r"Portugues-BR", lang, flags=re.I):
                    LanguageId = "pb"
                elif re.search(r"Portugues-PT", lang, flags=re.I):
                    LanguageId = "pt"
                elif re.search(r"Ingles", lang, flags=re.I):
                    LanguageId = "en"
                elif re.search(r"Espanhol", lang, flags=re.I):
                    LanguageId = "es"
                elif re.search(r"Frances", lang, flags=re.I):
                    LanguageId = "fr"
                else:
                    self.Log("Message: Unknown language: %s" % lang)
                    continue
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
                    "rating": rating,
                    "language_flag": LanguageFlag,
                    "language_preference": int(LanguagePreference),
                    "type": release_type,
                    'ratio': float(MainID['ratio'])
                })

            self.Log(
                "Message: Retrieved [%d] results for page [%d], Movie[%s], Id[%s]." % (
                    len(results), Page, MainID["title"], MainID["id"]))

    def Download(self, url):
        downloadID = '/downloadarquivo/' + regex_3.findall(url)[0]
        self.Log('DOWNLOAD ID: %s' % downloadID)
        if not downloadID:
            return None, None
        Response = self._urlopen("http://legendas.tv%s" % downloadID)
        Sub = Response.read()
        ext_match = re.search(r'\.([^.]+)$', Response.url)
        Type = ext_match.group(1).lower() if ext_match else 'zip'
        return Sub, Type

    def Search(self, **kargs):
        # Init all variables
        startTime = time.time()
        filteredResults, self.DownloadsResults, self.Languages = [], [], []
        Movie, TVShow, Year, Season, Episode, IMDB = "", "", 0, 0, 0, ""
        for key, value in list(kargs.items()):
            if key == "title":
                Movie = self.CleanLTVTitle(value)
            if key == "tvshow":
                TVShow = self.CleanLTVTitle(value)
            if key == "year" and value:
                Year = int(value)
            if key == "season" and value:
                Season = int(value)
            if key == "episode" and value:
                Episode = int(value)
            if key == "imdb" and value:
                IMDB = value
            if key == "lang" and value:
                for x, lang in enumerate(value):
                    self.Languages.append((x, lang))
        self.Languages.sort()

        self.Log("IMDB: " + IMDB)

        if TVShow:
            SearchTitle = TVShow
        else:
            SearchTitle = Movie

        discardedResults, filteredResults = "", ""
        discardedResults, filteredResults = self.findID(Movie, TVShow, Year,
                                                        Season, IMDB,
                                                        SearchTitle,
                                                        SearchTitle)
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
            # FIXME Find how many pages we should download
            self.Log("Message: Retrieving results to id[%s]" % (MainID["id"]))
            TotalPages = 3
            # Form and execute threaded downloads
            for Page in range(TotalPages):
                current = LTVThread(self, MainID, MainIDNumber, Page)
                self.RegThreads.append(current)
                current.start()
            MainIDNumber += 1
        # Wait for all threads to finish
        for t in self.RegThreads:
            t.join()
        # Sorting and filtering the results by episode, including season packs
        self.DownloadsResults.sort(key=itemgetter(
            'main_id_number',
            'page',
            'position'))
        Results = defaultdict(lambda: {
            'primary': {
                'packs': [],
                'episodes': []
            },
            'secondary': {
                'packs': [],
                'episodes': []
            }
        })
        if TVShow:
            for DownloadsResult in self.DownloadsResults:
                ratio = DownloadsResult['ratio']
                name = DownloadsResult["filename"]
                pack_score = calculate_pack_score(DownloadsResult, Season, Episode)
                self.Log("File %s got a pack score of %d" % (name, pack_score))
                if pack_score > 0:
                    name = re.sub(r"\(PACK[^)]*\)\s*", "", name, flags=re.I)
                    name = re.sub(r"\(P\)\s*", "", name, flags=re.I)
                    DownloadsResult["filename"] = "(PACK) %s" % name
                    if pack_score == 1:
                        DownloadsResult["type"] = "pack"
                        Results[ratio]['primary']['packs'].append(DownloadsResult)
                    else:
                        DownloadsResult["type"] = "pack_maybe_%d" % pack_score
                        Results[ratio]['secondary']['packs'].append(DownloadsResult)
                elif re.search(r"S%.2d[.x]?E%.2d" % (Season, Episode), name, flags=re.I):
                    Results[ratio]['primary']['episodes'].append(DownloadsResult)
                elif re.search(r"%.2d[.x]%.2d" % (Season, Episode), name, flags=re.I):
                    Results[ratio]['primary']['episodes'].append(DownloadsResult)
                elif re.search(r"%d[.x]%.2d" % (Season, Episode), name, flags=re.I):
                    Results[ratio]['primary']['episodes'].append(DownloadsResult)
                elif re.search(r"%d[.x]%d([^0-9]|$)" % (Season, Episode), name, flags=re.I):
                    Results[ratio]['primary']['episodes'].append(DownloadsResult)
                else:
                    Results[ratio]['secondary']['episodes'].append(DownloadsResult)
        elif Movie:
            for DownloadsResult in self.DownloadsResults:
                ratio = DownloadsResult['ratio']
                Results[ratio]['primary']['episodes'].append(DownloadsResult)

        for _, ratioEntry in Results.items():
            for _, categoryEntry in ratioEntry.items():
                for _, resultsForType in categoryEntry.items():
                    resultsForType.sort(key=itemgetter(
                        'type',
                        'language_preference',
                        'page',
                        'position'))

        FinalResults = []
        for ratio in sorted(Results.keys(), reverse=True):
            entry = Results[ratio]
            sub_results = entry['primary']['packs'] \
                + entry['primary']['episodes'] \
                + entry['secondary']['packs']
            sub_results.sort(key=itemgetter(
                'type',
                'language_preference',
                'page',
                'position'))
            FinalResults.extend(sub_results)
            FinalResults.extend(entry['secondary']['episodes'])

        # # Log final results
        self.Log(" ")
        self.Log("Final results:")
        self._log_List_dict(FinalResults,
                            "filename language_name language_preference type")
        self.Log("Message: The service took %0.2f seconds to complete." % (
                time.time() - startTime))
        # Return results
        return FinalResults
