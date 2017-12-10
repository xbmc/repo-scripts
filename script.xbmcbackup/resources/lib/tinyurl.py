import urllib2

#this is duplicated in snipppets of code from all over the web, credit to no one
#in particular - to all those that have gone before me!
def shorten(aUrl):
    tinyurl = 'http://tinyurl.com/api-create.php?url='
    req = urllib2.urlopen(tinyurl + aUrl)
    data = req.read()

    #should be a tiny url
    return str(data)
