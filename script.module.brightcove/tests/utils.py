from unittest2 import TestCase
import hashlib
import urllib
from urlparse import parse_qs
from brightcove.api import Brightcove
import email

ORIGINAL_URLOPEN = urllib.urlopen

def _parse_command(url):
    '''Returns the command query string value or None.'''
    _, querystring = url.split('?')
    params = parse_qs(querystring)
    commands = params.get('command')
    if commands:
        return commands[0]
    return None


def _request(url, data=None):
    md5 = hashlib.md5(url)
    filename = 'tests/data/%s,%s' % (_parse_command(url), md5.hexdigest())
    try:
        resp = email.message_from_file(open(filename))
    except IOError:
        assert False, 'No test data available for %s\nExpecting filename %s' % (url, filename)
    return resp.get_payload()

class MockHTTPTestCase(TestCase):
    def setUp(self):
        TOKEN = 'cE97ArV7TzqBzkmeRVVhJ8O6GWME2iG_bRvjBTlNb4o.'
        TOKEN = 'foobar'
        self.b = Brightcove(TOKEN)
        self.b._orig_read_conn = self.b.read_conn
        self.b.read_conn._request = _request


    def tearDown(self):
        self.b.read_conn = self.b._orig_read_conn
