from urlparse import urlsplit, urlunsplit
from urllib import urlencode, quote_plus, unquote_plus
import string

def removeFromStackAndRecurse(url):
	url = urlsplit(url)
	netloc = url.netloc
	if "@" in netloc:
		netloc = netloc[netloc.index("@") + 1:]

	netloc_list = netloc.split(" , ") if url.scheme == "stack" else [ netloc ]
	newnetloc_list = list()

	for n in netloc_list:
		netloc_unquoted = unquote_plus(n)
		if netloc_unquoted != n:
			newnetloc_list.append(quote_plus(removeFromStackAndRecurse(netloc_unquoted)))

	netloc = string.join(newnetloc_list, " , ")

	return urlunsplit((url.scheme, netloc, url.path, url.query, url.fragment))
