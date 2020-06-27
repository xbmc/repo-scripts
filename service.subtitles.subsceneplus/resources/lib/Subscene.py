import requests
import html5lib
import re
from html5lib import treebuilders, treewalkers

DOMAIN_NAME = "https://www.subscene.com"
TYPE_MATCH_UNKNOWN = 0
TYPE_MATCH_EXACT = 1
TYPE_MATCH_CLOSE = 2
TYPE_MATCH_POPULAR = 3
TYPE_MATCH_TVSERIES = 4

def SearchTitleMatch(stream):

    results = {
        TYPE_MATCH_UNKNOWN : [],
        TYPE_MATCH_EXACT : [],
        TYPE_MATCH_CLOSE : [],
        TYPE_MATCH_POPULAR : [],
        TYPE_MATCH_TVSERIES : [],
    }

    title_type = TYPE_MATCH_UNKNOWN

    state = 0
    name = "" 
    href = ""

    for token in stream:
        if state == 0:
            if 'data' in token:
                if token['data'] == "Exact":
                    title_type = TYPE_MATCH_EXACT
                    state = 1
                elif token['data'] == "Close":
                    title_type = TYPE_MATCH_CLOSE
                    state = 1
                elif token['data'] == "Popular":
                    title_type = TYPE_MATCH_POPULAR
                    state = 1
                elif token['data'] == "TV-Series":
                    title_type = TYPE_MATCH_TVSERIES
                    state = 1
        elif state == 1:
            if 'name' in token and token['type'] == 'StartTag':
                if token['name'] == 'h':
                    # parsing error, this should not have happend.
                    state = 99
                elif token['name'] == 'ul':
                    state = 2
        elif state == 2:
            if 'name' in token:
                if token['name'] == "ul" and token['type'] == 'EndTag':
                    state = 0
                elif token['name'] == "li" and token['type'] == 'StartTag':
                    state = 3
        elif state == 3:
            if 'name' in token:
                if token['name'] == "li" and token['type'] == 'EndTag':
                    state = 2
                elif token['name'] == "div" and token['type'] == 'StartTag' and list(token['data'].values())[0] == "title":
                    state = 4
        elif state == 4:
            if 'name' in token:
                if token['name'] == "div" and token['type'] == 'EndTag':
                    state = 3
                elif token['name'] == "a" and token['type'] == 'StartTag':
                    for (k,v) in token['data']:
                        if v == "href":
                            # grap href
                            href = token['data'][(k,v)]
                            name = ""
                    state = 5
        elif state == 5:
            if 'name' in token:
                if token['name'] == "a" and token['type'] == 'EndTag':
                    state = 4
                    results[title_type].append((name,href))
            elif 'data' in token:
                # grab name, here we append name, sometime we have newline in tags, which 
                # results in parsing the name in multiple tokens
                name += token['data']
        elif state == 99:
            break

    return results

def EnumSubtitles(url):
    r = requests.get(url)
    p = html5lib.HTMLParser(tree=treebuilders.getTreeBuilder("dom"))
    dom_tree = p.parse(r.text)
    walker = treewalkers.getTreeWalker("dom")
    stream = walker(dom_tree)

    result = []
    state = 0
    href = ""
    lang = ""
    name = ""
    no_of_file = 0
    author = ""
    comment = ""
    for token in stream:

        if state == 0:
            if 'name' in token and token['name'] == "tbody":
                state = 1
        elif state == 1:
            href = ""
            lang = ""
            name = ""
            no_of_file = 0
            author = ""
            comment = ""
            if 'name' in token and token['name'] == "tbody" and token['type'] == 'EndTag':
                state = 99
            elif 'name' in token and token['name'] == "tr" and token['type'] == 'StartTag':
                state = 2
        elif state == 2:
            if 'name' in token and token['name'] == "tr" and token['type'] == 'EndTag':
                state = 1
            elif 'name' in token and token['name'] == "td" and token['type'] == 'StartTag' and list(token['data'].values())[0] == "a1":
                state = 3
        elif state == 3:
            if 'name' in token and token['name'] == "a" and token['type'] == 'StartTag':
                for (k,v) in token['data']:
                    if v == "href":
                        # grab href
                        href = token['data'][(k,v)]
                state = 4
        elif state == 4:
            if 'name' in token and token['name'] == "span" and token['type'] == 'StartTag':
                state = 5
        elif state == 5:
            if 'name' in token and token['name'] == "span" and token['type'] == 'StartTag':
                state = 6
            elif 'data' in token and token['type'] == "Characters":
                # grab lang
                lang = token['data']
        elif state == 6:
            if 'name' in token and token['name'] == "td" and token['type'] == 'StartTag' and list(token['data'].values())[0] == "a3":
                state = 7
            elif 'data' in token and token['type'] == "Characters":
                # grab name
                name = token['data']
        elif state == 7:
            if 'name' in token and token['name'] == "td" and token['type'] == 'StartTag' and list(token['data'].values())[0] == "a40":
                hearing_imp = False
                state = 8
            elif 'name' in token and token['name'] == "td" and token['type'] == 'StartTag' and list(token['data'].values())[0] == "a41":
                hearing_imp = True
                state = 9
            elif 'data' in token and token['type'] == "Characters":
                # grab number of files
                no_of_file = token['data']
        elif state == 8:
            if 'name' in token and token['name'] == "td" and token['type'] == 'StartTag' and list(token['data'].values())[0] == "a5":
                state = 15
        elif state == 9:
            if 'name' in token and token['name'] == "td" and token['type'] == 'StartTag' and list(token['data'].values())[0] == "a5":
                state = 15
        elif state == 15:
            # TODO: Read author
            author = ""
            if 'name' in token and token['name'] == "td" and token['type'] == 'StartTag' and list(token['data'].values())[0] == "a6":
                state = 16
        elif state == 16:
            # TODO: Read comment
            comment = ""
            if 'name' in token and token['name'] == "tr" and token['type'] == 'EndTag':
                state = 1
                result.append((href, lang, name, int(no_of_file), hearing_imp, author, comment))
        elif state == 99:
            break

    return result
    

def SearchMovie(title, year):
    r = requests.post(DOMAIN_NAME + "/subtitles/searchbytitle", data={"query": title, "l": ""})
    p = html5lib.HTMLParser(tree=treebuilders.getTreeBuilder("dom"))
    dom_tree = p.parse(r.text)
    walker = treewalkers.getTreeWalker("dom")
    stream = walker(dom_tree)

    return SearchTitleMatch(stream)

    # TODO: We are currently ignoring tv-series, thats to be handled later.
    


def DownloadSubtitle(link):
    r = requests.get(DOMAIN_NAME + link)
    p = html5lib.HTMLParser(tree=treebuilders.getTreeBuilder("dom"))
    dom_tree = p.parse(r.text)
    walker = treewalkers.getTreeWalker("dom")
    stream = walker(dom_tree)
   
    href = ""
    state = 0
    for token in stream:
        if state == 0:
            if 'name' in token and token['name'] == "div" and token['type'] == "StartTag":
                if 'data' in token and len(token['data']) > 0 and list(token['data'].values())[0] == "download":
                    state = 1
        elif state == 1:
            if 'name' in token and token['name'] == "a" and token['type'] == "StartTag":
                if 'data' in token and len(token['data']) > 0:
                    for k,v in token['data']:
                        if v == "href":
                            # grab href
                            href = token['data'][(k,v)]
                            state = 99

            if 'name' in token and token['name'] == "div" and token['type'] == 'EndTag':
                state = 99 
        elif state == 99:
            break
   
    if href == "":
        return None
    
    r = requests.get(DOMAIN_NAME + href)
    d = r.headers['content-disposition']
    fname = re.findall("filename=(.+)", d)
    if len(fname) > 0:
        return (fname[0], r.content)
    return None


