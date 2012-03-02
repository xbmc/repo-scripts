'''
   Parsedom for XBMC plugins
   Copyright (C) 2010-2011 Tobias Ussing And Henrik Mosgaard Jensen

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

import sys
import urllib
import urllib2
import re
import io
import inspect
import time
import HTMLParser


version = "0.9.2"
plugin = "CommonFunctions-" + version
print plugin

USERAGENT = "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-GB; rv:1.9.2.8) Gecko/20100722 Firefox/3.6.8"

if hasattr(sys.modules["__main__"], "xbmc"):
    xbmc = sys.modules["__main__"].xbmc
else:
    import xbmc

if hasattr(sys.modules["__main__"], "xbmcgui"):
    xbmcgui = sys.modules["__main__"].xbmcgui
else:
    import xbmcgui

if hasattr(sys.modules["__main__"], "dbg"):
    dbg = sys.modules["__main__"].dbg
else:
    dbg = False

if hasattr(sys.modules["__main__"], "dbglevel"):
    dbglevel = sys.modules["__main__"].dbglevel
else:
    dbglevel = 3

if hasattr(sys.modules["__main__"], "opener"):
    urllib2.install_opener(sys.modules["__main__"].opener)


# This function raises a keyboard for user input
def getUserInput(title="Input", default="", hidden=False):
    log("", 5)
    result = None

    # Fix for when this functions is called with default=None
    if not default:
        default = ""

    keyboard = xbmc.Keyboard(default, title)
    keyboard.setHiddenInput(hidden)
    keyboard.doModal()

    if keyboard.isConfirmed():
        result = keyboard.getText()

    log(repr(result), 5)
    return result


# This function raises a keyboard numpad for user input
def getUserInputNumbers(title="Input", default=""):
    log("", 5)
    result = None

    # Fix for when this functions is called with default=None
    if not default:
        default = ""

    keyboard = xbmcgui.Dialog()
    result = keyboard.numeric(0, title, default)

    log(repr(result), 5)
    return str(result)


# Converts the request url passed on by xbmc to the plugin into a dict of key-value pairs
def getParameters(parameterString):
    log("", 5)
    commands = {}
    splitCommands = parameterString[parameterString.find('?') + 1:].split('&')

    for command in splitCommands:
        if (len(command) > 0):
            splitCommand = command.split('=')
            key = splitCommand[0]
            value = splitCommand[1]
            commands[key] = value

    log(repr(commands), 5)
    return commands


def replaceHTMLCodes(txt):
    log(repr(txt), 5)

    # Fix missing ; in &#<number>;
    txt = re.sub("(&#[0-9]+)([^;^0-9]+)", "\\1;\\2", makeUTF8(txt))

    txt = HTMLParser.HTMLParser().unescape(txt)

    log(repr(txt), 5)
    return txt


def stripTags(html):
    log(repr(html), 5)
    sub_start = html.find("<")
    sub_end = html.find(">")
    while sub_start < sub_end and sub_start > -1:
        html = html.replace(html[sub_start:sub_end + 1], "").strip()
        sub_start = html.find("<")
        sub_end = html.find(">")

    log(repr(html), 5)
    return html


def _getDOMContent(html, name, match, ret):  # Cleanup
    log("match: " + match, 2)

    endstr = "</" + name  # + ">"

    start = html.find(match)
    end = html.find(endstr, start)
    pos = html.find("<" + name, start + 1 )

    log(str(start) + " < " + str(end) + ", pos = " + str(pos) + ", endpos: " + str(end), 8)

    while pos < end and pos != -1:  # Ignore too early </endstr> return
        tend = html.find(endstr, end + len(endstr))
        if tend != -1:
            end = tend
        pos = html.find("<" + name, pos + 1)
        log("loop: " + str(start) + " < " + str(end) + " pos = " + str(pos), 8)

    log("start: %s, len: %s, end: %s" % (start, len(match), end), 2)
    if start == -1 and end == -1:
        result = ""
    elif start > -1 and end > -1:
        result = html[start + len(match):end]
    elif end > -1:
        result = html[:end]
    elif start > -1:
        result = html[start + len(match):]

    if ret:
        endstr = html[end:html.find(">", html.find(endstr)) + 1]
        result = match + result + endstr

    log("done result length: " + str(len(result)), 2)
    return result


def _getDOMAttributes(match, name, ret):
    log("", 2)
    lst = re.compile('<' + name + '.*? ' + ret + '=(.[^>]*?)>', re.M | re.S).findall(match)
    ret = []
    for tmp in lst:
        cont_char = tmp[0]
        if cont_char in "'\"":
            log("Using %s as quotation mark" % cont_char)

            # Limit down to next variable.
            if tmp.find('=' + cont_char, tmp.find(cont_char, 1)) > -1:
                tmp = tmp[:tmp.find('=' + cont_char, tmp.find(cont_char, 1))]

            # Limit to the last quotation mark
            if tmp.rfind(cont_char, 1) > -1:
                tmp = tmp[1:tmp.rfind(cont_char)]
        else:
            log("No quotation mark found", 2)
            if tmp.find(" ") > 0:
                tmp = tmp[:tmp.find(" ")]
            elif tmp.find("/") > 0:
                tmp = tmp[:tmp.find("/")]
            elif tmp.find(">") > 0:
                tmp = tmp[:tmp.find(">")]

        ret.append(tmp.strip())

    log("Done: " + repr(ret), 2)
    return ret

def _getDOMElements(item, name, attrs):
    log("Name: " + repr(name) + " - Attrs:" + repr(attrs) + " - HTML: " + str(type(item)))
    lst = []
    for key in attrs:
        lst2 = re.compile('(<' + name + '[^>]*?(?:' + key + '=[\'"]' + attrs[key] + '[\'"].*?>))', re.M | re.S).findall(item)
        if len(lst2) == 0 and attrs[key].find(" ") == -1:  # Try matching without quotation marks
            lst2 = re.compile('(<' + name + '[^>]*?(?:' + key + '=' + attrs[key] + '.*?>))', re.M | re.S).findall(item)

        if len(lst) == 0:
            log("Setting main list " + repr(lst2), 5)
            lst = lst2
            lst2 = []
        else:
            log("Setting new list " + repr(lst2), 5)
            test = range(len(lst))
            test.reverse()
            for i in test:  # Delete anything missing from the next list.
                if not lst[i] in lst2:
                    log("Purging mismatch " + str(len(lst)) + " - " + repr(lst[i]), 1)
                    del(lst[i])

    if len(lst) == 0 and attrs == {}:
        log("No list found, trying to match on name only", 1)
        lst = re.compile('(<' + name + '>)', re.M | re.S).findall(item)
        if len(lst) == 0:
            lst = re.compile('(<' + name + ' .*?>)', re.M | re.S).findall(item)

    log("Done: " + str(type(lst)))
    return lst

def parseDOM(html, name="", attrs={}, ret=False):
    log("Name: " + repr(name) + " - Attrs:" + repr(attrs) + " - Ret: " + repr(ret) + " - HTML: " + str(type(html)), 1)

    if isinstance(html, str) or isinstance(html, unicode):
        html = [html]
    elif not isinstance(html, list):
        log("Input isn't list or string/unicode.")
        return ""

    if not name.strip():
        log("Missing tag name")
        return ""

    ret_lst = []
    for item in html:
        temp_item = re.compile('(<[^>]*?\n[^>]*?>)').findall(item)
        for match in temp_item:
            item = item.replace(match, match.replace("\n", " "))

        lst = _getDOMElements(item, name, attrs)

        if isinstance(ret, str):
            log("Getting attribute %s content for %s matches " % (ret, len(lst) ), 2)
            lst2 = []
            for match in lst:
                lst2 += _getDOMAttributes(match, name, ret)
            lst = lst2
        else:
            log("Getting element content for %s matches " % len(lst), 2)
            lst2 = []
            for match in lst:
                log("Getting element content for %s" % match, 4)
                temp = _getDOMContent(item, name, match, ret).strip()
                item = item[item.find(temp, item.find(match)) + len(temp):]
                lst2.append(temp)
            lst = lst2
        ret_lst += lst

    log("Done", 1)
    return ret_lst


def extractJSON(data):
    lst = re.compile('({.*?})', re.M | re.S).findall(data)
    return lst


def fetchPage(params={}):
    get = params.get
    link = get("link")
    ret_obj = {}
    if get("post_data"):
        log("called for : " + repr(params['link']))
    else:
        log("called for : " + repr(params))

    if not link or int(get("error", "0")) > 2:
        log("giving up")
        ret_obj["status"] = 500
        return ret_obj

    if get("post_data"):
        if get("hide_post_data"):
            log("Posting data", 2)
        else:
            log("Posting data: " + urllib.urlencode(get("post_data")), 2)

        request = urllib2.Request(link, urllib.urlencode(get("post_data")))
        request.add_header('Content-Type', 'application/x-www-form-urlencoded')
    else:
        log("Got request", 2)
        request = urllib2.Request(link)

    if get("headers"):
        for head in get("headers"):
            request.add_header(head[0], head[1])

    request.add_header('User-Agent', USERAGENT)

    if get("cookie"):
        request.add_header('Cookie', get("cookie"))

    if get("refering"):
        log("Added refering url: %s" % get("refering"))
        request.add_header('Referer', get("refering"))

    try:
        log("connecting to server...", 1)

        con = urllib2.urlopen(request)
        ret_obj["header"] = str(con.info())
        ret_obj["new_url"] = con.geturl()
        if get("no-content", "false") == "false":
            ret_obj["content"] = con.read()

        con.close()

        log("Done")
        ret_obj["status"] = 200
        return ret_obj

    except urllib2.HTTPError, e:
        err = str(e)
        log("HTTPError : " + err)
        log("HTTPError - Headers: " + str(e.headers) + " - Content: " + e.fp.read())

        params["error"] = str(int(get("error", "0")) + 1)
        ret = fetchPage(params)

        if not "content" in ret and e.fp:
            ret["content"] = e.fp.read()
            return ret

        ret_obj["status"] = 500
        return ret_obj

    except urllib2.URLError, e:
        err = str(e)
        log("URLError : " + err)

        time.sleep(3)
        params["error"] = str(int(get("error", "0")) + 1)
        ret_obj = fetchPage(params)
        return ret_obj


def getCookieInfoAsHTML():
    log("", 5)
    if hasattr(sys.modules["__main__"], "cookiejar"):
        cookiejar = sys.modules["__main__"].cookiejar

        cookie = repr(cookiejar)
        cookie = cookie.replace("<_LWPCookieJar.LWPCookieJar[", "")
        cookie = cookie.replace("), Cookie(version=0,", "></cookie><cookie ")
        cookie = cookie.replace(")]>", "></cookie>")
        cookie = cookie.replace("Cookie(version=0,", "<cookie ")
        cookie = cookie.replace(", ", " ")
        log(repr(cookie), 5)
        return cookie

    log("Found no cookie", 5)
    return ""


# This function implements a horrible hack related to python 2.4's terrible unicode handling.
def makeAscii(data):
    log(repr(data), 5)
    #if sys.hexversion >= 0x02050000:
    #        return data

    try:
        return data.encode('ascii', "ignore")
    except:
        log("Hit except on : " + repr(data))
        s = ""
        for i in data:
            try:
                i.encode("ascii", "ignore")
            except:
                log("Can't convert character", 4)
                continue
            else:
                s += i

        log(repr(s), 5)
        return s


# This function handles stupid utf handling in python.
def makeUTF8(data):
    log(repr(data), 5)
    try:
        return data.decode('utf8', 'ignore')
    except:
        log("Hit except on : " + repr(data))
        s = ""
        for i in data:
            try:
                i.decode("utf8", "ignore")
            except:
                log("Can't convert character", 4)
                continue
            else:
                s += i
        log(repr(s), 5)
        return s


def openFile(filepath, options="r"):
    log(repr(filepath) + " - " + repr(options))
    if options.find("b") == -1:  # Toggle binary mode on failure
        alternate = options + "b"
    else:
        alternate = options.replace("b", "")

    try:
        log("Trying normal: %s" % options)
        return io.open(filepath, options)
    except:
        log("Fallback to binary: %s" % alternate)
        return io.open(filepath, alternate)


def log(description, level=0):
    if dbg and dbglevel > level:
        try:
            xbmc.log("[%s] %s : '%s'" % (plugin, inspect.stack()[1][3], description.encode("utf-8", "ignore")), xbmc.LOGNOTICE)
        except:
            xbmc.log("[%s] %s : '%s'" % (plugin, inspect.stack()[1][3], description), xbmc.LOGNOTICE)
