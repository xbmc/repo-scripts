#!/usr/bin/env python
# -*- coding: utf-8 -*-
import zipfile
import requests
import re
import shutil
import os
import staticutils
from bs4 import BeautifulSoup

class RUtils:
    SESSION = requests.Session()
    USERAGENT = 'phate89 utility module'
    DEFPARAMS={}
    LOGLEVEL=5

    def __init__(self):
        self.setUserAgent(self.USERAGENT)

    def setUserAgent(self, useragent):
        self.setHeader('user-agent', useragent)

    def setHeader(self, voice, value):
        self.SESSION.headers.update({voice: value})

    def log(self,msg, level=2):
        if level<=self.LOGLEVEL:
            if isinstance(msg, str):
                msg = msg.decode("utf-8", 'ignore')
            print u"#### {name}: {text} ####".format(name=os.path.basename(__file__),text=msg)

    def createRequest(self,url,params={},post={},stream=False,addDefault=True):
        if addDefault:
            params.update(self.DEFPARAMS)
        if post:
            r = self.SESSION.post(url,params=params,data=post,stream=stream)
        else:
            r = self.SESSION.get(url,params=params,stream=stream)
        self.log("Opening url %s" % r.url,2)
        if r.status_code == requests.codes.ok:
            return r
        elif r.status_code < 500:
            self.log("Error opening url. Client error")
        else:
            self.log("Error opening url. Server error")
        return False

    def newSession(self):
        self.SESSION = requests.Session()
        self.setUserAgent(self.USERAGENT)

    def getJson(self,url,params={},post={}):
        r = self.createRequest(url, params, post)
        if r:
            try:
                return r.json()
            except:
                self.log("Error serializing json")
                return False

    def getSoup(self,url,params={},post={}):
        r = self.createRequest(url, params, post)
        if r:
            return BeautifulSoup(r.text, "html.parser")
        return False

    def getSoupFromRes(self,res):
        if res:
            return BeautifulSoup(res.text, "html.parser")
        return False

    def getText(self,url,params={},post={}):
        r = self.createRequest(url, params, post)
        if r:
            return r.text
        return False

    def getFileExtracted(self,url,params={},post={},dataPath='',index=0):
        if not dataPath:
            return False
        data=self.createRequest(url,params,post,stream=True)
        if not data:
            self.log(sUrl + " file read failed",4)
            return False

        if os.path.isdir(dataPath):
            shutil.rmtree(dataPath)
        os.makedirs(dataPath)
        for chunk in data.iter_content(1):
            ext='srt'
            if chunk=='P':
                ext='zip'
            elif chunk=='R':
                ext='rar'
            break

        TEMPFILE=os.path.join(dataPath, 'itasa.' + ext)
        if os.path.exists(TEMPFILE):
            os.remove(TEMPFILE)
        try:
            with open(TEMPFILE, 'wb') as fd:
                fd.write(chunk)
                for chunk in data.iter_content(chunk_size=1024):
                    fd.write(chunk)
        except:
            self.log("Error writing file")
            return False
        
        if ext=='srt':
            outName = TEMPFILE
            index = 0
        elif ext=='zip':
            zf=zipfile.ZipFile(TEMPFILE,'r')
            exts = ['.srt', '.sub', '.txt', '.smi', '.ssa', '.ass']
            subs = [x for x in zf.namelist() if os.path.splitext(x)[1] in exts]
            if index>=len(subs):
                index=0
            binData=zf.read(subs[index])
            zf.close()
            outName=os.path.join(dataPath,subs[index])
            
            if binData:
                try:       
                    fp=open(outName,'wb')                 
                    fp.write(binData)
                    fp.close()
                except:
                    self.log("Error writing text subtitle file")
                    return False
            else:
                self.log('subtitle not found in zip file',1)
                fp.close()
                return False
        elif ext=='rar':
            try:
                __import__(xbmc)
            except ImportError:
                self.log('rar extraction not supported',1)
                return False
            TEMPFOLDER=os.path.join(dataPath,'temp', '')
            if os.path.isdir(TEMPFOLDER):
                shutil.rmtree(TEMPFOLDER)
            os.makedirs(TEMPFOLDER)
            xbmc.executebuiltin('XBMC.Extract(%s,%s)' % (TEMPFILE, TEMPFOLDER), True)
            exts = ['.srt', '.sub', '.txt', '.smi', '.ssa', '.ass']
            subs = [os.path.join(root, name)
                 for root, dirs, files in os.walk(TEMPFOLDER)
                 for name in files
                 if os.path.splitext(name)[1] in exts]
            if len(subs)<=0:
                return False
            if index>=len(subs):
                index = 0
            outName = subs[0]
        return index, outName
