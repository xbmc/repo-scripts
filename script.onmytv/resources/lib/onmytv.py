import re
try:
    from elementtree import ElementTree
    string_to_etree = ElementTree.fromstring
except ImportError:
    from lxml import etree
    string_to_etree = etree.fromstring
import os
import time
import sys
import datetime
import urllib
import re

def strip_tags(s):
    if not s:
        return ""
    return re.sub(r"<[^>]+>","",s)

class OnMyTV(object):
    def __init__(self, uid='', cache_dir=None, max_cache_age=None):
        self.cache_dir = cache_dir
        self.uid = uid
        self.base_url = "http://next.seven.days.on-my.tv/?xml"
        self.max_age = int(max_cache_age) or 60*60
        self.full_listing = {}
        self.user_listing = {}
        
    def check_cache(self, dest):
        now = int(time.time())
        print 'checking cache: NOW: %s' % (now,)
        if not os.path.exists(dest):
            print "%s doesn't exist" % (dest,)
            return False
        else:
            cachetime = int(os.path.getmtime(dest))
            diff = int(now - cachetime)
            print ">>> %d - %d = %d max age(%d)<<<" % (now, cachetime, diff, self.max_age)
            if diff > self.max_age:
                print 'Too Old!'
                return False
            print 'not too old'
        return True

    def user_cache_file(self):
        return os.path.join(self.cache_dir, "%s.cache" % (self.uid,))
        
    def full_cache_file(self):
        return os.path.join(self.cache_dir, "full.cache")
    
    def load_listings(self, full=True, report_hook=None):
        if full:
            url = self.base_url
            dest = self.full_cache_file()
        
        else:
            url = self.base_url + "&uid=" + self.uid
            dest = self.user_cache_file()

        if not self.check_cache(dest):
            if os.path.exists(dest):
                try:
                    os.unlink(dest)
                except:
                    pass
            urllib.urlretrieve(url, dest, report_hook)
        
        fh = open(dest,'r')
        xml = fh.read()
        fh.close()
        
        if full:
            self.full_listing = self.parse_results(xml)
        else:
            self.user_listing = self.parse_results(xml)
            
        
    def clean_data_dict(self, ed):
        del ed['ep_date_utc']
        ed['ep_date_utc'] = datetime.datetime(*map(int, re.split(r"[-:\s]", ed['date'])))
        ed['ep_date_local'] = ed['ep_date_utc'] - datetime.timedelta(seconds = time.altzone)
        ed['episode_summary'] = strip_tags(ed['episode_summary'])
        
        del ed['date']
        for k, v in ed.iteritems():
            if isinstance(ed[k], basestring) and ed[k].isdigit():
                ed[k] = int(v)
        return ed
    
    def parse_results(self, xml):
        tree = string_to_etree(xml)
        data = []
        for entry in tree.findall(".//entry"):
            ed = dict((i.tag, i.text) for i in entry)
            ed = self.clean_data_dict(ed)
            data.append(ed)
        return data
    