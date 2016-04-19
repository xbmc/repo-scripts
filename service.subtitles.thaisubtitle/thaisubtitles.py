#from cStringIO import StringIO
from pprint import pprint
from urlparse import urljoin
#import xml.etree.ElementTree as et
import string
import sys
import re
import urllib2
import urllib
from BeautifulSoup import BeautifulSoup

try:
    import xbmc
    DEBUG = False
    from service import log
except:
    DEBUG = False

    def log(module, msg):
        print msg

MAIN_URL = "http://www.thaisubtitle.com"




def prepare_search_string(s):
    s = string.strip(s)
    s = re.sub(r'\(\d\d\d\d\)$', '', s)  # remove year from title
    return s


def geturl(url):
    log(__name__, "Getting url: %s" % url)
    try:
        response = urllib2.urlopen(url)
        content = response.read()
        #Fix non-unicode characters in movie titles
        strip_unicode = re.compile("([^-_a-zA-Z0-9!@#%&=,/'\";:~`\$\^\*\(\)\+\[\]\.\{\}\|\?<>\\]+|[^\s]+)")
        content = strip_unicode.sub('', content)
        return_url = response.geturl()
    except:
        log(__name__, "Failed to get url: %s" % url)
        content = None
        return_url = None
    return content, return_url


def search_movie(title, year, languages, filename):
    title = string.strip(title)
    search_string = prepare_search_string(title)

    log(__name__, "Search movie = %s" % search_string)
    url = MAIN_URL + "manage/search.php?movie_name=" + urllib.quote_plus(search_string)
    content, response_url = geturl(url)

    if content is not None:
        log(__name__, "Multiple movies found, searching for the right one ...")
        subspage_url = find_movie(content, title, year)
        if subspage_url is not None:
            log(__name__, "Movie found in list, getting subs ...")
            url = MAIN_URL + subspage_url
            content, response_url = geturl(url)
            if content is not None:
                getallsubs(content, languages, filename)
        else:
            log(__name__, "Movie not found in list: %s" % title)
            if string.find(string.lower(title), "&") > -1:
                title = string.replace(title, "&", "and")
                log(__name__, "Trying searching with replacing '&' to 'and': %s" % title)
                subspage_url = find_movie(content, title, year)
                if subspage_url is not None:
                    log(__name__, "Movie found in list, getting subs ...")
                    url = MAIN_URL + subspage_url
                    content, response_url = geturl(url)
                    if content is not None:
                        getallsubs(content, languages, filename)
                else:
                    log(__name__, "Movie not found in list: %s" % title)



def search_manual(searchstr, languages, filename):
    search_string = prepare_search_string(searchstr)
    url = MAIN_URL + "/manage/search.php?movie_name=" + urllib.quote_plus(search_string)
    if DEBUG:
        content = open("test.html").read()
    else:
        content, response_url = geturl(url)

    if content is not None:
        return getallsubs(content, languages, filename)
    else:
        return []


def getallsubs(content, allowed_languages, filename="", search_string=""):

    #parser = HTMLParser()
#    parser = et.XMLParser(html=1)
#    html = et.fromstring(content, parser).getroot()
#    html = ElementSoup.parse(StringIO(content))

    soup = BeautifulSoup(content)
    #elements = html.findall(".//tr[./td/a/img[@title='Download Thai Subtitle']]")

    subtitles = []
    sub_list = soup.fetch("div", dict(id="subtitle_list"))
    if not sub_list:
        return []
    table = sub_list[0].fetch("table")[0]
    if table is None:
        return []

    for element in table.findAll("tr")[1:]:
        num, title, edit, rating, translate, upload, download = element.findAll("td")
        subtitle_name = title.find('br').previousSibling.strip().strip(" [En]")
        rating = int(round(float(rating.getText().strip('%'))/100.0*5))
        sync = False
        if filename != "" and string.lower(filename) == string.lower(subtitle_name):
            sync = True

        for lang_name, _, let2, let3, _, _  in [
            ("Thai", "0", "th", "tha", "41", 30243),
            ("English", "2", "en", "eng", "11", 30212)
        ]:
            if let3 not in allowed_languages:
                continue
            # rating is really the completeness. 0 means no thai, so not point showing it
            if let3 == 'tha' and rating < 1:
                continue

            link = download.fetch("img",{'title':'Download %s Subtitle'%lang_name})[0].parent['href']
            link = urljoin(MAIN_URL + "/manage/", link)
            lang = {'name': lang_name, '2let': let2, '3let': let3}

            subtitles.append({'rating': str(rating),
                              'filename': subtitle_name,
                              'sync': sync,
                              'link': link,
                              'lang': lang,
                              'hearing_imp': False})

    log(__name__, "got %s results" % len(subtitles))
#    subtitles.sort(key=lambda x: [not x['sync']])
    return subtitles

if __name__ == "__main__":
    try:
        _, filename, search = sys.argv
    except:
        _, filename = sys.argv
        search = filename


    pprint(search_manual(search, "tha", filename))
