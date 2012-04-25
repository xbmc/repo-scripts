'''
 Megaupload and Megaporn Resolver v0.3
 Copyleft (Licensed under GPLv3) Anarchintosh (all code)

 Also gets megavideo links from megaupload pages.(can't do this for megaporn)

 If account is None or Free, you have to wait 46 or 26 Seconds respectively before accessing the stream. 

 Megaup and megaporn use different logins, so store the cookies in different places.
 
 Commands/Functions:

 __doLogin(baseurl, cookiepath, username, password)

 __resolveURL(url,cookiepath,aviget=True,force_megavid=True)

 __dls_limited(baseurl,cookiepath)

 is_online(cookiepath='YOUR_COOKIE_PATH',url='THE_URL')

'''

import os,re
import urllib,urllib2,cookielib

#global strings for valid baseurl
regular = 'http://www.megaupload.com/'
porn = 'http://www.megaporn.com/'

def setBaseURL(baseurl):
    # API feature to neaten up how functions are used
    if baseurl == 'regular':
       return regular
    elif baseurl == 'porn':
       return porn

def openfile(filename):
    fh = open(filename, 'r')
    contents=fh.read()
    fh.close()
    return contents

def checkurl(url):
    #get necessary url details
        ismegaup = re.search('.megaupload.com/', url)
        ismegavid = re.search('.megavideo.com/', url)
        isporn = re.search('.megaporn.com/', url)
    #second layer of porn url detection
        ispornvid = re.search('.megaporn.com/video/', url)
    # RETURN RESULTS:
        if ismegaup is not None:
            return 'megaup'
        elif ismegavid is not None:
            return 'megavid'
        elif isporn is not None:
            if ispornvid is not None:
                return 'pornvid'
            elif ispornvid is None:
                return 'pornup'

def is_online(cookiepath=None,url=False,source=False):
    if source == False:
        source = GetURL(url,cookiepath)
    checker = re.search('Unfortunately, the link you have clicked is not available.',source)
    if checker is not None:
        return False
    elif checker is None:
        return True

def get_dir(mypath, dirname):
    #...creates sub-directories if they are not found.
    subpath = os.path.join(mypath, dirname)
    if not os.path.exists(subpath):
        os.makedirs(subpath)
    return subpath
    

def megavid_force(url):
    #load a megaup page without cookies, to ensure that the user can get the megavid link.
        source=load_pagesrc(url,enable_cookies=False)
        megavidlink=get_megavid(source)
        return megavidlink
    
def resolveURL(url,cookiepath,aviget=True,force_megavid=True):

        #bring together all the functions into a simple addon-friendly function.

        source=load_pagesrc(url,cookiepath,enable_cookies=True)
        
        #if source is a url (from a Direct Downloads re-direct) not pagesource
        if source.startswith('http://'):
            filelink=source
            '''
            Can't get megavid link if using direct download
            However, as a workaround, can load megaup page without cookies, then scrape.
            '''     
            if force_megavid is True:
                megavidlink=megavid_force(url)
            else:
                megavidlink=None
            
            #speed patch (we know its premium, since we're getting a direct download)
            logincheck='premium'

        else: # if source is html page code...

            #scrape the direct filelink from page
            filelink=get_filelink(source,aviget)

            #scrape the megavideo link if there is one on the page
            megavidlink=get_megavid(source)

            #verify what the user is logged in as.
            logincheck=check_login(source)

        filename=_get_filename(filelink)
        
        return filelink,filename,megavidlink,logincheck


def load_pagesrc(url,cookiepath,enable_cookies=True):
    
    #loads page source code. redirect url is returned if Direct Downloads is enabled.
        
    urltype=checkurl(url)
    if urltype is 'megaup' or 'megaporn':

        source=GetURL(url,cookiepath,enable_cookies)
        
        if is_online(source=source) == True:
            return source
        else:
            return False
    else:
        return False


def check_login(source):
        #feed me some megaupload page source
        #returns 'free' or 'premium' if logged in
        #returns 'none' if not logged in
        
        login = re.search('Welcome', source)
        premium = re.search('flashvars.status = "premium";', source)
        platinum = re.search('flashvars.status = "platinum";', source)       

        if login is not None:
            if premium is not None:
                return 'premium'
            elif premium is None:
                if platinum is not None:
                    return 'premium'
                elif platinum is None:
                    return 'free'
        elif login is None:
            return None

def __dls_limited(baseurl,cookiepath):
    #returns True if download limit has been reached.

    baseurl=setBaseURL(baseurl)

    truestring='Download limit exceeded'
    falsestring='Hooray Download Success'   

    #url to a special small text file that contains the words: Hooray Download Success
    if baseurl == regular:
        testurl = 'http://www.megaupload.com/?d=PQCIEIP7'
    elif baseurl == porn:
        testurl = ''

    source=load_pagesrc(testurl)
    fileurl=get_filelink(source)

    link=GetURL(cookiepath,fileurl)

    exceeded = re.search(truestring, link)
    #notexceeded = re.search(falsestring, link)

    if exceeded is not None:
        return True
    else:
        #if notexceeded is not None:
            return False

def delete_login(cookiepath):
    #clears cookies
    try:
        os.remove(cookiepath)
    except:
        pass
    
def get_megavid (source):
        #verify source is megaupload 
        checker='<span class="down_txt3">Download link:</span> <a href="http://www.megaupload.com/'
        ismegaup=re.search(checker, source)

        if ismegaup is not None:
        #scrape for megavideo link (first check its there)
            megavid = re.search('View on Megavideo', source)

        if megavid is None:
            #no megavideo link on page
            return None
            
        else:
            megavidlink = 'http://www.megavideo.' + ((re.compile('<a href="http://www.megavideo.(.+?)"').findall(source))[0])
            return megavidlink      

        if ismegaup is None:
            return None


def get_filelink(source,aviget=True):
        # load megaupload page and scrapes and adds videolink, passes through partname.  
        #print 'getting file link....'

        login = check_login(source)

        if login == 'premium':
            #get the premium link.
            url = (re.compile('<a href="(.+?)" class="down_ad_butt1">').findall(source))[0]

        if login == 'free' or login == None:
            url = (re.compile('id="downloadlink"><a href="(.+?)" class=').findall(source))[0]

        #aviget is an option where if a .divx file is found, it is renamed to .avi (necessary for XBMC)
        if aviget is True and url.endswith('divx'):
                return url[:-4]+'avi'
        else:       
                return url


def _get_filename(url=False,source=False):
        #accept either source or url
        if url is False:
            if source is not False:
                url=get_filelink(source)
        
        #get file name from url (ie my_vid.avi)
        name = re.split('\/+', url)
        return name[-1]


def doLogin(baseurl, cookiepath, username, password):

    baseurl=setBaseURL(baseurl)

    if username and password:
        #delete the old cookie
        try:
            os.remove(cookiepath)
        except:
            pass

        #build the login code, from user, pass, baseurl and cookie
        login_data = urllib.urlencode({'username' : username, 'password' : password, 'login' : 1, 'redir' : 1}) 
        req = urllib2.Request(baseurl + '?c=login', login_data)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')
        cj = cookielib.LWPCookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

        #do the login and get the response
        response = opener.open(req)
        source = response.read()
        response.close()

        login = check_login(source)

        if login == 'free' or login == 'premium':
            cj.save(cookiepath)

        return login
    else:
        return None
                

def GetURL(url,cookiepath,enable_cookies=True):
    #print 'processing url: '+url

    # use cookie, if logged in.
    if enable_cookies==True and cookiepath is not None and os.path.exists(cookiepath):
        cj = cookielib.LWPCookieJar()
        cj.load(cookiepath)
        req = urllib2.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')   
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        response = opener.open(req)

        #check if we might have been redirected (megapremium Direct Downloads...)
        finalurl = response.geturl()

        #if we weren't redirected, return the page source
        if finalurl is url:
            link=response.read()
            response.close()
            return link

        #if we have been redirected, return the redirect url
        elif finalurl is not url:               
            return finalurl

    # don't use cookie, if not logged in        
    else:
        req = urllib2.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3')   
        response = urllib2.urlopen(req)
        link=response.read()
        response.close()
        return link
