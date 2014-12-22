from urlparse import urlparse
import re

def is_local(path):
    """ Returns True if the given path is a local address, otherwise False. """
    parse_result = urlparse(path)
    # only analyze http(s)/rtmp streams
    if (not parse_result.scheme == 'http') and (not parse_result.scheme == 'https') and (not parse_result.scheme == 'rtmp'):
        return True
    if not parse_result.netloc:
        return True  # assume a lack of network location implies a private address
    # regex reference: http://stackoverflow.com/a/692457/577298
    elif re.match("127\.\d{1,3}\.\d{1,3}\.\d{1,3}", parse_result.netloc, flags=0):
        return True
    elif re.match("192\.168\.\d{1,3}\.\d{1,3}", parse_result.netloc, flags=0):
        return True
    elif re.match("10\.\d{1,3}\.\d{1,3}\.\d{1,3}", parse_result.netloc, flags=0):
        return True
    elif re.match("172\.(1[6-9]|2[0-9]|3[0-1])\.[0-9]{1,3}\.[0-9]{1,3}", parse_result.netloc, flags=0):
        return True
    elif parse_result.netloc.startswith("fe80:"):  # link-local IPv6 address
        return True
    elif parse_result.netloc.startswith("fc00:"):  # IPv6 ULA
        return True
    else:
        return False
