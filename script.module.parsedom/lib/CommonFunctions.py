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


version = "0.9.1"
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
    txt = makeUTF8(txt)
    # Fix missing ; in &#<number>;
    txt = re.sub("(&#[0-9]+)([^;^0-9]+)", "\\1;\\2", txt)

    import HTMLParser
    h = HTMLParser.HTMLParser()
    txt = h.unescape(txt)

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


def _getDOMContent(html, name, match):
    log("match: " + match, 2)
    start = html.find(match)
    endstr = "</" + name + ">"
    end = html.find(endstr, start)

    pos = html.find("<" + name, start + 1 )
    log(str(start) + " < " + str(end) + ", pos = " + str(pos) + ", endpos: " + str(end), 8)

    while pos < end and pos != -1:
        tend = html.find(endstr, end + len(endstr))
        if tend != -1:
            end = tend
        pos = html.find("<" + name, pos + 1)
        log("loop: " + str(start) + " < " + str(end) + " pos = " + str(pos), 8)

    log("start: %s, len: %s, end: %s" % (start, len(match), end), 2)
    if start == -1 and end == -1:
        html = ""
    elif start > -1 and end > -1:
        html = html[start + len(match):end]
    elif end > -1:
        html = html[:end]
    elif start > -1:
        html = html[start + len(match):]

    log("done html length: " + str(len(html)), 2)
    return html


def _getDOMAttributes(lst):
    log("", 2)
    ret = []
    for tmp in lst:
        cont_char = tmp[0]
        if tmp.find('="', tmp.find(cont_char, 1)) > -1:
            tmp = tmp[:tmp.find('="', tmp.find(cont_char, 1))]

        if tmp.find('=\'', tmp.find(cont_char, 1)) > -1:
            tmp = tmp[:tmp.find('=\'', tmp.find(cont_char, 1))]

        tmp = tmp[1:]
        if tmp.rfind(cont_char) > -1:
            tmp = tmp[:tmp.rfind(cont_char)]
        tmp = tmp.strip()
        ret.append(tmp)

    log("Done: " + repr(ret), 2)
    return ret


def parseDOM(html, name="", attrs={}, ret=False):
    # html <- text to scan.
    # name <- Element name
    # attrs <- { "id": "my-div", "class": "oneclass.*anotherclass", "attribute": "a random tag" }
    # ret <- Return content of element
    # Default return <- Returns a list with the content
    log("start: " + repr(name) + " - " + repr(attrs) + " - " + repr(ret) + " - " + str(type(html)), 1)

    if not isinstance(html, str) and not isinstance(html, list) and not isinstance(html, unicode):
        log("Input isn't list or string/unicode.")
        return ""

    if not isinstance(html, list):
        html = [html]

    if not name.strip():
        log("Missing tag name")
        return ""

    ret_lst = []

    # Find all elements with the tag

    i = 0
    for item in html:
        item = item.replace("\n", "")
        lst = []

        for key in attrs:
            scripts = ['(<' + name + ' [^>]*?(?:' + key + '=[\'"]' + attrs[key] + '[\'"][^>]*?>))',  # Hit often.
                       '(<' + name + ' (?:' + key + '=[\'"]' + attrs[key] + '[\'"])[^>]*?>)',  # Hit twice
                       '(<' + name + ' [^>]*?(?:' + key + '=[\'"]' + attrs[key] + '[\'"])[^>]*?>)']

            lst2 = []
            for script in scripts:
                if len(lst2) == 0:
                    #log("scanning " + str(i) + " " + str(len(lst)) + " Running :" + script, 2)
                    lst2 = re.compile(script).findall(item)
                    i += 1

                if len(lst2) > 0:
                    if len(lst) == 0:
                        lst = lst2
                        lst2 = []
                    else:
                        test = range(len(lst))
                        test.reverse()
                        for i in test:  # Delete anything missing from the next list.
                            if not lst[i] in lst2:
                                log("Purging mismatch " + str(len(lst)) + " - " + repr(lst[i]), 1)
                                del(lst[i])

        if len(lst) == 0 and attrs == {}:
            log("no list found, making one on just the element name", 1)
            lst = re.compile('(<' + name + ' [^>]*?>)').findall(item)

            if len(lst) == 0:  # If the elemnt doesn't exist with args, try it without args.
                lst = re.compile('(<' + name + '>)').findall(item)

        if ret != False:
            log("Getting attribute %s content for %s matches " % (ret, len(lst) ), 2)
            lst2 = []
            for match in lst:
                tmp_list = re.compile('<' + name + '.*?' + ret + '=([\'"][^>]*?)>').findall(match)
                lst2 += _getDOMAttributes(tmp_list)
                log(lst, 3)
                log(match, 3)
                log(lst2, 3)
            lst = lst2
        elif name != "img":
            log("Getting element content for %s matches " % len(lst), 2)
            lst2 = []
            for match in lst:
                log("Getting element content for %s" % match, 4)
                temp = _getDOMContent(item, name, match).strip()
                item = item[item.find(temp, item.find(match)) + len(temp):]
                lst2.append(temp)
                log(lst, 4)
                log(match, 4)
                log(lst2, 4)
            lst = lst2
        ret_lst += lst

    log("Done", 1)
    return ret_lst


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
        log("Got data to POST: " + urllib.urlencode(get("post_data")), 2)
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


def openFile(filepath, options="w"):
    log(repr(filepath), 5)
    if options.find("b") == -1:  # Toggle binary mode on failure
        alternate = options + "b"
    else:
        alternate = options.replace("b", "")

    try:
        log("Trying normal", 5)
        return io.open(filepath, options)
    except:
        log("Fallback to binary", 5)
        return io.open(filepath, alternate)


def log(description, level=0):
    if dbg and dbglevel > level:
        # Funny stuff..
        # [1][3] needed for calls from scrapeShow
        # print repr(inspect.stack())
        try:
            xbmc.log("[%s] %s : '%s'" % (plugin, inspect.stack()[1][3], description.encode("utf-8", "ignore")), xbmc.LOGNOTICE)
        except:
            xbmc.log("[%s] %s : '%s'" % (plugin, inspect.stack()[1][3], description), xbmc.LOGNOTICE)
