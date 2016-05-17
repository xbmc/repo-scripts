# -*- coding: utf-8 -*-
#
#  TraduttoriAnonimi.py
#  
#  Copyright 2016 ShellAddicted <shelladdicted@gmail.com<>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 3 of the License
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
# 
import xbmc;
class LogStream(object):
    def write(self,data):
        xbmc.log(("""*** [TraduttoriAnonimiCore] -> {}""".format(data)).encode('utf-8'), level = xbmc.LOGNOTICE)
            
from bs4 import BeautifulSoup;
import requests;
import re;
import logging;
import urlparse;
import traceback
        
log=logging.getLogger("TraduttoriAnonimiCore");
log.setLevel(logging.DEBUG);
style=logging.Formatter("%(asctime)s {%(levelname)s} %(name)s.%(funcName)s() -->> %(message)s");
consoleHandler = logging.StreamHandler(LogStream());
consoleHandler.setFormatter(style)
log.addHandler(consoleHandler);

def MagicInt(x): #Cast to integer (if possible) without Errors
    try:
        return int(x);
    except:
        return x;

def nstring(s):
    try:
        return s.encode(errors="replace").replace("?"," ")
    except:
        try:
            return s.decode(errors="replace").replace(u"\ufffd\ufffd\ufffd"," ")
        except:
            return s;

class SearchableDict(dict):
    def __getitem__(self, token):
        p=re.compile(token,re.IGNORECASE)
        result=[];
        for x,y in self.items():
            if re.search(p,nstring(x)):
                result.append({"Name":x,"URL":y});
                
        if (len(result)==0):
            result=None;
        
        return result;
        
class SearchableList(list):
    def __getitem__(self, token):
        p=re.compile(token,re.IGNORECASE)
        result=[];
        for x in self:
            if re.search(p,x):
                result.append(x);
                
        if (len(result)==0):
            result=None;
        
        return result;
        

def RetriveURL(url):
    try:
        headers={'user-agent': 'Kodi-SubtitleService-TraduttoriAnonimi'};
        q=requests.get(url,headers=headers);
        return q;
    except Exception as exc:
        log.error(traceback.format_exc())
        raise exc;



class TraduttoriAnonimi:
    def __init__(self,BaseURL="http://traduttorianonimi.it"):
        self.log=log.getChild("TA")
        
        self.BaseURL=BaseURL;
        self.log.debug("BaseURL=> {}".format(self.BaseURL))
        
        self.ShowsListURL=urlparse.urljoin(self.BaseURL,"elenco-serie/")
        self.log.debug("ShowsListURL=> {}".format(self.ShowsListURL))
        
        self.ShowsList=SearchableDict()
        self.UpdateShowsList();
        
    def UpdateShowsList(self):
        self._GrabShowsListFromWebsite();
        
    def _GrabShowsListFromWebsite(self):
        self.log.info("Grabbing Shows list from Website.")
        url=self.ShowsListURL
        self.log.debug("self.ShowsList re-initialized")
        self.ShowsList=SearchableDict();
        while (1):
            r=RetriveURL(url);
            if (r!=None):
                html=r.content;
                parser=BeautifulSoup(html,"html.parser");
                
                for ShowTag in parser.findAll("a",{"href":re.compile("serie\?c=\d+", re.IGNORECASE)}):
                    ShowName=ShowTag.find("img").attrs["title"]
                    self.ShowsList[ShowName]=ShowTag.attrs["href"];#TraduttoriAnonimi.Show(ShowName=show_name,url=show_url)
                
                tmp=parser.find("div",{"class":"pagination" }).find("a",{"class":"next"})
                if (tmp!=None):
                    url=urlparse.urljoin(self.BaseURL,tmp.attrs["href"])
                    self.log.debug("Next Page Found. Following => {}".format(url))
                else:
                    self.log.debug("Next Page Not Found. Exiting from loop")
                    break;
            else:
                log.error("respose is None. Exiting from loop")
                break;
        return self.ShowsList;
    
    def GrabSubtitle(self,ShowName,Season,Episode):
        ShowsResults=self.ShowsList[ShowName]
        EpisodeRegex=re.compile("(?P<tvshowname>.+)(?:(?:\s|s|\.)|\.s|\.so)(?P<season>\d+)(?:x|e|\.x|\.e)(?P<episode>\d+)", re.IGNORECASE);
        if (ShowsResults == None):
            self.log.info("No ShowsResults");
            return [];
        for show in ShowsResults:
            r=RetriveURL(show["URL"]);
            if (r!=None):
                html=r.content;
                parser=BeautifulSoup(html,"html.parser");
                        
                for ep in parser.findAll("td",{"class":"dwn"}):
                    tmp=ep.find("a")
                    self.log.debug("Analyzing => {}".format(tmp))
                    if (tmp!=None and "title" in tmp.attrs and "href" in tmp.attrs):
                        x=EpisodeRegex.search(tmp.attrs["title"])
                        self.log.debug("Regex Groups=> {}".format(x.groups()))
                        if (MagicInt(x.group("season"))==Season and MagicInt(x.group("episode"))==Episode):
                            self.log.info("Subtitle Found")
                            return [{"Name":tmp.attrs["title"],"URL":tmp.attrs["href"]}];
