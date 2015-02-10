# -*- coding: utf-8 -*-

# Shooter.cn subtitles
import sys,os
import hashlib
from httplib import HTTPConnection, OK

import struct
from cStringIO import StringIO
import gzip
import traceback
import random
from urlparse import urlparse

import string
import xbmc, xbmcgui, xbmcvfs
from utilities import log
_ = sys.modules[ "__main__" ].__language__

SVP_REV_NUMBER = 1543
CLIENTKEY = "SP,aerSP,aer %d &e(\xd7\x02 %s %s"
RETRY = 3

def grapBlock(f, offset, size):
    f.seek(offset, 0)
    return f.read(size)

def getBlockHash(f, offset):
    return hashlib.md5(grapBlock(f, offset, 4096)).hexdigest()

def genFileHash(fpath):
    f = xbmcvfs.File(fpath)
    ftotallen = f.size()
    if ftotallen < 8192:
        f.close()
        return ""
    offset = [4096, ftotallen/3*2, ftotallen/3, ftotallen - 8192]
    hash = ";".join(getBlockHash(f, i) for i in offset)
    f.close()
    return hash

def getShortNameByFileName(fpath):
    fpath = os.path.basename(fpath).rsplit(".",1)[0]
    fpath = fpath.lower()
    
    for stop in ["blueray","bluray","dvdrip","xvid","cd1","cd2","cd3","cd4","cd5","cd6","vc1","vc-1","hdtv","1080p","720p","1080i","x264","stv","limited","ac3","xxx","hddvd"]:
        i = fpath.find(stop)
        if i >= 0:
            fpath = fpath[:i]
    
    for c in "[].-#_=+<>,":
        fpath = fpath.replace(c, " ")
    
    return fpath.strip()

def getShortName(fpath):
    for i in range(3):
        shortname = getShortNameByFileName(os.path.basename(fpath))
        if not shortname:
            fpath = os.path.dirname(fpath)
        else:
            return shortname

def genVHash(svprev, fpath, fhash):
    """
    the clientkey is not avaliable now, but we can get it by reverse engineering splayer.exe
    to get the clientkey from splayer.exe:
    f = open("splayer","rb").read()
    i = f.find(" %s %s%s")"""
    global CLIENTKEY
    if CLIENTKEY:
        #sprintf_s( buffx, 4096, CLIENTKEY , SVP_REV_NUMBER, szTerm2, szTerm3, uniqueIDHash);
        vhash = hashlib.md5(CLIENTKEY%(svprev, fpath, fhash)).hexdigest()
    else:
        #sprintf_s( buffx, 4096, "un authiority client %d %s %s %s", SVP_REV_NUMBER, fpath.encode("utf8"), fhash.encode("utf8"), uniqueIDHash);
        vhash = hashlib.md5("un authiority client %d %s %s "%(svprev, fpath, fhash)).hexdigest()
    return vhash

def urlopen(url, svprev, formdata):
    ua = "SPlayer Build %d" % svprev
    #prepare data
    #generate a random boundary
    boundary = "----------------------------" + "%x"%random.getrandbits(48)
    data = []
    for item in formdata:
        data.append("--" + boundary + "\r\nContent-Disposition: form-data; name=\"" + item[0] + "\"\r\n\r\n" + item[1] + "\r\n")
    data.append("--" + boundary + "--\r\n")
    data = "".join(data)
    cl = str(len(data))
    
    r = urlparse(url)
    h = HTTPConnection(r.hostname)
    h.connect()
    h.putrequest("POST", r.path, skip_host=True, skip_accept_encoding=True)
    h.putheader("User-Agent", ua)
    h.putheader("Host", r.hostname)
    h.putheader("Accept", "*/*")
    h.putheader("Content-Length", cl)
    h.putheader("Content-Type", "multipart/form-data; boundary=" + boundary)
    h.endheaders()
    
    h.send(data)
    
    resp = h.getresponse()
    if resp.status != OK:
        raise Exception("HTTP response " + str(resp.status) + ": " + resp.reason)
    return resp

def downloadSubs(fpath, lang):
    global SVP_REV_NUMBER
    global RETRY
    pathinfo = fpath
    if os.path.sep != "\\":
        #*nix
        pathinfo = "E:\\" + pathinfo.replace(os.path.sep, "\\")
    filehash = genFileHash(fpath)
    shortname = getShortName(fpath)
    vhash = genVHash(SVP_REV_NUMBER, fpath.encode("utf-8"), filehash)
    formdata = []
    formdata.append(("pathinfo", pathinfo.encode("utf-8")))
    formdata.append(("filehash", filehash))
    if vhash:
        formdata.append(("vhash", vhash))
    formdata.append(("shortname", shortname.encode("utf-8")))
    if lang != "chn":
        formdata.append(("lang", lang))
    
    for server in ["www", "svplayer", "splayer1", "splayer2", "splayer3", "splayer4", "splayer5", "splayer6", "splayer7", "splayer8", "splayer9"]:
        for schema in ["http", "https"]:
            theurl = schema + "://" + server + ".shooter.cn/api/subapi.php"
            for i in range(1, RETRY+1):
                try:
                    print "trying %s (retry %d)" % (theurl, i)
                    handle = urlopen(theurl, SVP_REV_NUMBER, formdata)
                    resp = handle.read()
                    if len(resp) > 1024:
                        return resp
                    else:
                        return ''
                except Exception, e:
                    traceback.print_exc()
    return ''

class Package(object):
    def __init__(self, s):
        self.parse(s)
    def parse(self, s):
        c = s.read(1)
        self.SubPackageCount = struct.unpack("!B", c)[0]
        print "self.SubPackageCount: %d"%self.SubPackageCount
        self.SubPackages = []
        for i in range(self.SubPackageCount):
            sub = SubPackage(s)
            self.SubPackages.append(sub)

class SubPackage(object):
    def __init__(self, s):
        self.parse(s)
    def parse(self, s):
        c = s.read(8)
        self.PackageLength, self.DescLength = struct.unpack("!II", c)
        self.DescData = s.read(self.DescLength)
        c = s.read(5)
        self.FileDataLength, self.FileCount = struct.unpack("!IB", c)
        self.Files = []
        for i in range(self.FileCount):
            file = SubFile(s)
            self.Files.append(file)

class SubFile(object):
    def __init__(self, s):
        self.parse(s)
    def parse(self, s):
        c = s.read(8)
        self.FilePackLength, self.ExtNameLength = struct.unpack("!II", c)
        self.ExtName = s.read(self.ExtNameLength)
        c = s.read(4)
        self.FileDataLength = struct.unpack("!I", c)[0]
        self.FileData = s.read(self.FileDataLength)
        if self.FileData.startswith("\x1f\x8b"):
            gzipper = gzip.GzipFile(fileobj=StringIO(self.FileData))
            self.FileData = gzipper.read()

def getSub(fpath, languagesearch, languageshort, languagelong, subtitles_list):
    subdata = downloadSubs(fpath, languagesearch)
    if (subdata):
        package = Package(StringIO(subdata))
        basename = os.path.basename(fpath)
        barename = basename.rsplit(".",1)[0]
        for sub in package.SubPackages:
            for file in sub.Files:
                if (file.ExtName in ["srt", "txt", "ssa", "smi", "sub"]):
                    filename = ".".join([barename, file.ExtName])
                    subtitles_list.append({'filedata': sub.Files,'filename': filename,'language_name': languagelong,'language_flag':'flags/' + languageshort + '.gif',"rating":'0',"sync": True})

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
    subtitles_list = []
    msg = ""

    chinese = 0
    if string.lower(lang1) == "chinese": chinese = 1
    elif string.lower(lang2) == "chinese": chinese = 2
    elif string.lower(lang3) == "chinese": chinese = 3

    english = 0
    if string.lower(lang1) == "english": english = 1
    elif string.lower(lang2) == "english": english = 2
    elif string.lower(lang3) == "english": english = 3

    if ((chinese > 0) and (english == 0)):
        getSub(file_original_path, "chn", "zh", "Chinese", subtitles_list)

    if ((english > 0) and (chinese == 0)):
        getSub(file_original_path, "eng", "en", "English", subtitles_list)

    if ((chinese > 0) and (english > 0) and (chinese < english)):
        getSub(file_original_path, "chn", "zh", "Chinese", subtitles_list)
        getSub(file_original_path, "eng", "en", "English", subtitles_list)

    if ((chinese > 0) and (english > 0) and (chinese > english)):
        getSub(file_original_path, "eng", "en", "English", subtitles_list)
        getSub(file_original_path, "chn", "zh", "Chinese", subtitles_list)

    if ((chinese == 0) and (english == 0)):
        msg = "Won't work, Shooter.cn is only for Chinese and English subtitles!"

    return subtitles_list, "", msg #standard output


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    subs_file = ''
    barename = subtitles_list[pos][ "filename" ].rsplit(".",1)[0]
    language = subtitles_list[pos][ "language_name" ]
    for file in subtitles_list[pos][ "filedata" ]:
        filename = os.path.join(tmp_sub_dir, ".".join([barename, file.ExtName]))
        open(filename,"wb").write(file.FileData)
        if (file.ExtName in ["srt", "txt", "ssa", "smi", "sub"]):
            subs_file = filename
    return False, language, subs_file #standard output

