#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import shutil
import zipfile
from json.decoder import JSONDecodeError
import requests
from bs4 import BeautifulSoup


class RUtils(object):
    SESSION = requests.Session()
    USERAGENT = 'phate89 utility module'
    DEFPARAMS = {}
    LOGLEVEL = 5

    def __init__(self):
        self.setUserAgent(self.USERAGENT)

    def setUserAgent(self, useragent):
        self.setHeader('user-agent', useragent)

    def setHeader(self, voice, value):
        self.SESSION.headers.update({voice: value})

    def log(self, msg, level=2):
        if level <= self.LOGLEVEL:
            print(u"#### {name}: {text} ####".format(name=os.path.basename(__file__), text=msg))

    def createRequest(self, url, params=None, post=None, stream=False, addDefault=True, **kwargs):
        if params is None:
            params = {}
        if addDefault:
            params.update(self.DEFPARAMS)
        if post is not None:
            r = self.SESSION.post(url, params=params, data=post,
                                  stream=stream, **kwargs)
        else:
            r = self.SESSION.get(url, params=params, stream=stream, **kwargs)
        self.log("Opening url %s" % r.url, 2)
        if r.ok:
            return r
        if r.status_code < 500:
            self.log("Error opening url. Client error " + str(r.status_code))
        else:
            self.log("Error opening url. Server error " + str(r.status_code))
        return False

    def newSession(self):
        self.SESSION = requests.Session()
        self.setUserAgent(self.USERAGENT)

    def getJson(self, url, params=None, post=None, **kwargs):
        r = self.createRequest(url, params, post, **kwargs)
        if r:
            try:
                return r.json()
            except (requests.HTTPError, JSONDecodeError):
                self.log("Error serializing json")
        return None

    def getSoup(self, url, params=None, post=None, parser="html.parser", **kwargs):
        r = self.createRequest(url, params, post)
        if r:
            return BeautifulSoup(r.text, parser, **kwargs)
        return False

    def getSoupFromRes(self, res, parser="html.parser", **kwargs):
        if res:
            return BeautifulSoup(res.text, parser, **kwargs)
        return False

    def getText(self, url, params=None, post=None, **kwargs):
        r = self.createRequest(url, params, post, **kwargs)
        if r:
            return r.text
        return False

    def getFileExtracted(self, url, params=None, post=None, dataPath='', index=0):
        if not dataPath:
            return False
        data = self.createRequest(url, params, post, stream=True)
        if not data:
            self.log(url + " file read failed", 4)
            return False

        if os.path.isdir(dataPath):
            shutil.rmtree(dataPath)
        os.makedirs(dataPath)
        chunk = ''
        for chunk in data.iter_content(1):
            ext = 'srt'
            if chunk == 'P':
                ext = 'zip'
            elif chunk == 'R':
                ext = 'rar'
            break

        TEMPFILE = os.path.join(dataPath, 'itasa.' + ext)
        if os.path.exists(TEMPFILE):
            os.remove(TEMPFILE)
        try:
            with open(TEMPFILE, 'wb') as fd:
                fd.write(chunk)
                for chunk in data.iter_content(chunk_size=1024):
                    fd.write(chunk)
        except EnvironmentError:
            self.log("Error writing file")
            return False

        if ext == 'srt':
            outName = TEMPFILE
            index = 0
        elif ext == 'zip':
            zf = zipfile.ZipFile(TEMPFILE, 'r')
            exts = ['.srt', '.sub', '.txt', '.smi', '.ssa', '.ass']
            subs = [x for x in zf.namelist() if os.path.splitext(x)[1] in exts]
            if index >= len(subs):
                index = 0
            binData = zf.read(subs[index])
            zf.close()
            outName = os.path.join(dataPath, subs[index])

            if binData:
                try:
                    with open(outName, 'wb') as fp:
                        fp.write(binData)
                        fp.close()
                except EnvironmentError:
                    self.log("Error writing text subtitle file")
                    return False
            else:
                self.log('subtitle not found in zip file', 1)
                fp.close()
                return False
        elif ext == 'rar':
            try:
                import xbmc
            except ImportError:
                self.log('rar extraction not supported', 1)
                return False
            TEMPFOLDER = os.path.join(dataPath, 'temp', '')
            if os.path.isdir(TEMPFOLDER):
                shutil.rmtree(TEMPFOLDER)
            os.makedirs(TEMPFOLDER)
            xbmc.executebuiltin('Extract(%s,%s)' % (TEMPFILE, TEMPFOLDER), True)
            exts = ['.srt', '.sub', '.txt', '.smi', '.ssa', '.ass']
            subs = [os.path.join(root, name)
                    for root, dirs, files in os.walk(TEMPFOLDER)
                    for name in files
                    if os.path.splitext(name)[1] in exts]
            if not subs:
                return False
            if index >= len(subs):
                index = 0
            outName = subs[0]
        return index, outName
