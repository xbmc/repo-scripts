# -*- coding: UTF-8 -*-

import sys
import os
from utilities import languageTranslate
import xbmc
import xbmcvfs
import urllib

try:
  #Python 2.6 +
  from hashlib import md5
except ImportError:
  #Python 2.5 and earlier
  from md5 import new as md5

# Version 0.1 
# 
# Coding by gregd
# http://greg.pro
# License: GPL v2


_ = sys.modules[ "__main__" ].__language__

def timeout(func, args=(), kwargs={}, timeout_duration=10, default=None):

    import threading
    class InterruptableThread(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)
            self.result = "000000000000"
        def run(self):
            self.result = func(*args, **kwargs)
    it = InterruptableThread()
    it.start()
    it.join(timeout_duration)
    if it.isAlive():
        return it.result
    else:
        return it.result
        
def set_filehash(path,rar):
    d = md5();    
    qpath=urllib.quote(path)
    if rar:
        path="""rar://"""+qpath
    d.update(xbmcvfs.File(path,"rb").read(10485760))
    return d

def f(z):
        idx = [ 0xe, 0x3,  0x6, 0x8, 0x2 ]
        mul = [   2,   2,    5,   4,   3 ]
        add = [   0, 0xd, 0x10, 0xb, 0x5 ]

        b = []
        for i in xrange(len(idx)):
                a = add[i]
                m = mul[i]
                i = idx[i]

                t = a + int(z[i], 16)
                v = int(z[t:t+2], 16)
                b.append( ("%x" % (v*m))[-1] )

        return ''.join(b)

def search_subtitles( file_original_path, title, tvshow, year, season, episode, set_temp, rar, lang1, lang2, lang3, stack ): #standard input
       
    ok = False
    msg = ""    
    subtitles_list = []    
    languages = {}
    for lang in (lang1,lang2,lang3):
        languages[lang]=languageTranslate(lang,0,2)
        
    d = timeout(set_filehash, args=(file_original_path, rar), timeout_duration=15)

    for lang,language in languages.items():
        str = "http://napiprojekt.pl/unit_napisy/dl.php?l="+language.upper()+"&f="+d.hexdigest()+"&t="+f(d.hexdigest())+"&v=dreambox&kolejka=false&nick=&pass=&napios="+os.name
        subs=urllib.urlopen(str).read()
        if subs[0:4]!='NPc0':		            
            flag_image = "flags/%s.gif" % (language,)            
            s={'filename':title,'link':subs,"language_name":lang,"language_flag":flag_image,"language_id":language,"ID":0,"sync":True, "format":"srt", "rating": "" }
            subtitles_list.append(s)        
            
    return subtitles_list, "", "" #standard output


def download_subtitles (subtitles_list, pos, zip_subs, tmp_sub_dir, sub_folder, session_id): #standard input
    local_tmp_file = os.path.join(tmp_sub_dir, "napiprojekt_subs.srt")
    local_file_handle = open(local_tmp_file, "w" + "b")
    local_file_handle.write(subtitles_list[pos][ "link" ])
    local_file_handle.close()  
    language = subtitles_list[pos][ "language_name" ]
    return False, language, local_tmp_file #standard output    

    
