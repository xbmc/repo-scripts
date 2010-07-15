# -*- coding: utf-8 -*-
# 2008-07, Erik Svensson <erik.public@gmail.com>

import sys, os, time, datetime
import re
import httplib, urllib2, base64, socket

try:
    import json
except ImportError:
    import simplejson as json

from constants import *
from utils import *

class TransmissionError(Exception):
    def __init__(self, message='', original=None):
        Exception.__init__(self, message)
        self.message = message
        self.original = original

    def __str__(self):
        if self.original:
            original_name = type(self.original).__name__
            return '%s Original exception: %s, "%s"' % (self.message, original_name, self.original.args)
        else:
            return self.args

class Torrent(object):
    """
    Torrent is a class holding the data raceived from Transmission regarding a bittorrent transfer.
    All fetched torrent fields are accessable through this class using attributes.
    This class has a few convenience properties using the torrent data.
    """

    def __init__(self, fields):
        if 'id' not in fields:
            raise ValueError('Torrent requires an id')
        self.fields = {}
        self.update(fields)

    def __repr__(self):
        return '<Torrent %d \"%s\">' % (self.fields['id'], self.fields['name'])

    def __str__(self):
        return 'torrent %s' % self.fields['name']

    def update(self, other):
        """Update the torrent data from a Transmission arguments dictinary"""
        fields = None
        if isinstance(other, dict):
            fields = other
        elif isinstance(other, Torrent):
            fields = other.fields
        else:
            raise ValueError('Cannot update with supplied data')
        for k, v in fields.iteritems():
            self.fields[k.replace('-', '_')] = v

    def files(self):
        """
        Get list of files for this torrent. This function returns a dictionary with file information for each file.
        """
        result = {}
        if 'files' in self.fields:
            indicies = xrange(len(self.fields['files']))
            files = self.fields['files']
            priorities = self.fields['priorities']
            wanted = self.fields['wanted']
            index = 1
            for item in zip(indicies, files, priorities, wanted):
                selected = bool(item[3])
                priority = PRIORITY[item[2]]
                result[item[0]] = {
                    'selected': selected,
                    'priority': priority,
                    'size': item[1]['length'],
                    'name': item[1]['name'],
                    'completed': item[1]['bytesCompleted']}
        return result

    def __getattr__(self, name):
        try:
            return self.fields[name]
        except KeyError, e:
            raise AttributeError('No attribute %s' % name)

    @property
    def status(self):
        """Get the status as string."""
        return STATUS[self.fields['status']]

    @property
    def progress(self):
        """Get the download progress in percent as float."""
        try:
            return 100.0 * (self.fields['sizeWhenDone'] - self.fields['leftUntilDone']) / float(self.fields['sizeWhenDone'])
        except ZeroDivisionError:
            return 0.0

    @property
    def ratio(self):
        """Get the upload/download ratio."""
        try:
            return self.fields['uploadedEver'] / float(self.fields['downloadedEver'])
        except ZeroDivisionError:
            return 0.0

    @property
    def eta(self):
        """Get the "eta" as datetime.timedelta."""
        eta = self.fields['eta']
        if eta >= 0:
            return datetime.timedelta(seconds=eta)
        else:
            ValueError('eta not valid')

    @property
    def date_active(self):
        """Get the attribute "activityDate" as datetime.datetime."""
        return datetime.datetime.fromtimestamp(self.fields['activityDate'])

    @property
    def date_added(self):
        """Get the attribute "addedDate" as datetime.datetime."""
        return datetime.datetime.fromtimestamp(self.fields['addedDate'])

    @property
    def date_started(self):
        """Get the attribute "startDate" as datetime.datetime."""
        return datetime.datetime.fromtimestamp(self.fields['startDate'])

    @property
    def date_done(self):
        """Get the attribute "doneDate" as datetime.datetime."""
        return datetime.datetime.fromtimestamp(self.fields['doneDate'])

    def format_eta(self):
        """Returns the attribute "eta" formatted as a string."""
        eta = self.fields['eta']
        if eta == -1:
            return 'not available'
        elif eta == -2:
            return 'unknown'
        else:
            return format_timedelta(self.eta)

class Session(object):
    """
    Session is a class holding the session data for a Transmission daemon.

    Access the session field can be done through attributes.
    The attributes available are the same as the session arguments in the
    Transmission RPC specification, but with underscore instead of hypen.
    ``download-dir`` -> ``download_dir``.
    """

    def __init__(self, fields={}):
        self.fields = {}
        self.update(fields)

    def update(self, other):
        """Update the session data from a session arguments dictinary"""

        fields = None
        if isinstance(other, dict):
            fields = other
        elif isinstance(other, Session):
            fields = other.fields
        else:
            raise ValueError('Cannot update with supplied data')

        for k, v in fields.iteritems():
            self.fields[k.replace('-', '_')] = v

    def __getattr__(self, name):
        try:
            return self.fields[name]
        except KeyError, e:
            raise AttributeError('No attribute %s' % name)

    def __str__(self):
        text = ''
        for k, v in self.fields.iteritems():
            text += "% 32s: %s\n" % (k[-32:], v)
        return text

class Client(object):
    """
    This is it. This class implements the json-RPC protocol to communicate with Transmission.
    """

    def __init__(self, address='localhost', port=DEFAULT_PORT, user=None, password=None):
        base_url = 'http://' + address + ':' + str(port)
        self.url = base_url + '/transmission/rpc'
        if user and password:
            password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
            password_manager.add_password(realm=None, uri=self.url, user=user, passwd=password)
            opener = urllib2.build_opener(
                urllib2.HTTPBasicAuthHandler(password_manager)
                , urllib2.HTTPDigestAuthHandler(password_manager)
                )
            urllib2.install_opener(opener)
        elif user or password:
            logger.warning('Either user or password missing, not using authentication.')
        self._sequence = 0
        self.session = Session()
        self.sessionid = 0
        self.protocol_version = None
        self.get_session()
        self.torrent_get_arguments = get_arguments('torrent-get'
                                                   , self.rpc_version)

    def _debug_request(self, request):
        logger.debug(
            json.dumps(
                {
                    'request': {
                        'url': request.get_full_url(),
                        'request-headers': dict(request.header_items()),
                        'request-data': json.loads(request.data),
                    }
                },
                indent=2
            )
        )

    def _debug_response(self, response, response_data):
        try:
            response_data = json.loads(response_data)
        except:
            pass
        logger.debug(
            json.dumps(
                {
                    'response': {
                        'url': response.url,
                        'code': response.code,
                        'msg': response.msg,
                        'headers': dict(response.headers),
                        'data': response_data,
                    }
                },
                indent=2
            )
        )

    def _http_query(self, query):
        headers = {'X-Transmission-Session-Id': self.sessionid}
        request = urllib2.Request(self.url, query, headers)
        request_count = 0
        while True:
            error_data = ""
            try:
                try:
                    self._debug_request(request)
                    socket.setdefaulttimeout(10)
                    if (sys.version_info[0] == 2 and sys.version_info[1] > 5) or sys.version_info[0] > 2:
                        response = urllib2.urlopen(request, timeout=60)
                    else:
                        response = urllib2.urlopen(request)
                    break
                except urllib2.HTTPError, error:
                    error_data = error.read()
                    if error.code == 409:
                        logger.info('Server responded with 409, trying to set session-id.')
                        if request_count > 1:
                            raise TransmissionError('Session ID negotiation failed.', error)
                        if 'X-Transmission-Session-Id' in error.headers:
                            self.sessionid = error.headers['X-Transmission-Session-Id']
                            request.add_header('X-Transmission-Session-Id', self.sessionid)
                        else:
                            raise TransmissionError('Unknown conflict.', error)
                except urllib2.URLError, error:
                    raise TransmissionError('Failed to connect to daemon.', error)
                except httplib.BadStatusLine, error:
                    if (request_count > 1):
                        raise TransmissionError('Failed to request %s "%s".' % (self.url, query), error)
            finally:
                if error_data:
                    self._debug_response(error, error_data)
            request_count = request_count + 1
        result = response.read()
        self._debug_response(response, result)
        return result

    def _request(self, method, arguments={}, ids=[], require_ids = False):
        """Send json-rpc request to Transmission using http POST"""

        if not isinstance(method, (str, unicode)):
            raise ValueError('request takes method as string')
        if not isinstance(arguments, dict):
            raise ValueError('request takes arguments as dict')
        ids = self._format_ids(ids)
        if len(ids) > 0:
            arguments['ids'] = ids
        elif require_ids:
            raise ValueError('request require ids')

        query = json.dumps({'tag': self._sequence, 'method': method
                            , 'arguments': arguments})
        logger.info(query)
        self._sequence += 1
        start = time.time()
        http_data = self._http_query(query)
        elapsed = time.time() - start
        logger.info('http request took %.3f s' % (elapsed))

        try:
            data = json.loads(http_data)
        except ValueError, e:
            logger.error('Error: ' + str(e))
            logger.error('Request: \"%s\"' % (query))
            logger.error('HTTP data: \"%s\"' % (http_data))
            raise

        logger.info(json.dumps(data, indent=2))

        if data['result'] != 'success':
            raise TransmissionError('Query failed with result \"%s\"'
                                    % data['result'])

        results = {}
        if method == 'torrent-get':
            for item in data['arguments']['torrents']:
                results[item['id']] = Torrent(item)
                if self.protocol_version == 2 and 'peers' not in item:
                    self.protocol_version = 1
        elif method == 'torrent-add':
            item = data['arguments']['torrent-added']
            results[item['id']] = Torrent(item)
        elif method == 'session-get':
            self._update_session(data['arguments'])
        elif method == 'session-stats':
            # older versions of T has the return data in "session-stats"
            if 'session-stats' in data['arguments']:
                self._update_session(data['arguments']['session-stats'])
            else:
                self._update_session(data['arguments'])
        elif method in ('port-test', 'blocklist-update'):
            results = data['arguments']
        else:
            return None

        return results

    def _format_ids(self, args):
        """Take things and make them valid torrent identifiers"""
        ids = []

        if isinstance(args, (int, long)):
            ids.append(args)
        elif isinstance(args, (str, unicode)):
            for item in re.split(u'[ ,]+', args):
                if len(item) == 0:
                    continue
                addition = None
                try:
                    # handle index
                    addition = [int(item)]
                except ValueError:
                    pass
                if not addition:
                    # handle hashes
                    try:
                        int(item, 16)
                        addition = [item]
                    except:
                        pass
                if not addition:
                    # handle index ranges i.e. 5:10
                    match = re.match(u'^(\d+):(\d+)$', item)
                    if match:
                        try:
                            idx_from = int(match.group(1))
                            idx_to = int(match.group(2))
                            addition = range(idx_from, idx_to + 1)
                        except:
                            pass
                if not addition:
                    raise ValueError(u'Invalid torrent id, \"%s\"' % item)
                ids.extend(addition)
        elif isinstance(args, (list)):
            for item in args:
                ids.extend(self._format_ids(item))
        else:
            raise ValueError(u'Invalid torrent id')
        return ids

    def _update_session(self, data):
        self.session.update(data)

    @property
    def rpc_version(self):
        if self.protocol_version == None:
            if hasattr(self.session, 'rpc_version'):
                self.protocol_version = self.session.rpc_version
            elif hasattr(self.session, 'version'):
                self.protocol_version = 3
            else:
                self.protocol_version = 2
        return self.protocol_version

    def _rpc_version_warning(self, version):
        if self.rpc_version < version:
            logger.warning('Using feature not supported by server. RPC version for server %d, feature introduced in %d.' % (self.rpc_version, version))

    def add(self, data, **kwargs):
        """
        Add torrent to transfers list. Takes a base64 encoded .torrent file in data.
        Additional arguments are:

            * `paused`, boolean, Whether to pause the transfer on add.
            * `download_dir`, path, The directory where the downloaded
              contents will be saved in.
            * `peer_limit`, number, Limits the number of peers for this
              transfer.
            * `files_unwanted`,
            * `files_wanted`,
            * `priority_high`,
            * `priority_low`,
            * `priority_normal`,
        """
        args = {'metainfo': data}
        for key, value in kwargs.iteritems():
            argument = make_rpc_name(key)
            (arg, val) = argument_value_convert('torrent-add',
                                        argument, value, self.rpc_version)
            args[arg] = val
        return self._request('torrent-add', args)

    def add_url(self, torrent_url, **kwargs):
        """
        Add torrent to transfers list. Takes a url to a .torrent file.
        Additional arguments are:

            * `paused`, boolean, Whether to pause the transfer on add.
            * `download_dir`, path, The directory where the downloaded
              contents will be saved in.
            * `peer_limit`, number, Limits the number of peers for this
              transfer.
            * `files_unwanted`,
            * `files_wanted`,
            * `priority_high`,
            * `priority_low`,
            * `priority_normal`,
        """
        torrent_file = None
        if os.path.exists(torrent_url):
            torrent_file = open(torrent_url, 'r')
        else:
            try:
                torrent_file = urllib2.urlopen(torrent_url)
            except:
                torrent_file = None

        if not torrent_file:
            raise TransmissionError('File does not exist.')

        torrent_data = base64.b64encode(torrent_file.read())
        return self.add(torrent_data, **kwargs)

    def remove(self, ids, delete_data=False):
        """
        remove torrent(s) with provided id(s). Local data is removed if
        delete_data is True, otherwise not.
        """
        self._rpc_version_warning(3)
        self._request('torrent-remove',
                    {'delete-local-data':rpc_bool(delete_data)}, ids, True)

    def start(self, ids):
        """start torrent(s) with provided id(s)"""
        self._request('torrent-start', {}, ids, True)

    def stop(self, ids):
        """stop torrent(s) with provided id(s)"""
        self._request('torrent-stop', {}, ids, True)

    def verify(self, ids):
        """verify torrent(s) with provided id(s)"""
        self._request('torrent-verify', {}, ids, True)

    def reannounce(self, ids):
        """reannounce torrent(s) with provided id(s)"""
        self._rpc_version_warning(5)
        self._request('torrent-reannounce', {}, ids, True)

    def info(self, ids=[], arguments={}):
        """Get detailed information for torrent(s) with provided id(s)."""
        if not arguments:
            arguments = self.torrent_get_arguments
        return self._request('torrent-get', {'fields': arguments}, ids)

    def get_files(self, ids=[]):
        """
        Get list of files for provided torrent id(s).
        This function returns a dictonary for each requested torrent id holding
        the information about the files.
        """
        fields = ['id', 'name', 'hashString', 'files', 'priorities', 'wanted']
        request_result = self._request('torrent-get', {'fields': fields}, ids)
        result = {}
        for id, torrent in request_result.iteritems():
            result[id] = torrent.files()
        return result

    def set_files(self, items):
        """
        Set file properties. Takes a dictonary with similar contents as the
        result of get_files.
        """
        if not isinstance(items, dict):
            raise ValueError('Invalid file description')
        for tid, files in items.iteritems():
            if not isinstance(files, dict):
                continue
            wanted = []
            unwanted = []
            priority_high = []
            priority_normal = []
            priority_low = []
            for fid, file in files.iteritems():
                if not isinstance(file, dict):
                    continue
                if 'selected' in file and file['selected']:
                    wanted.append(fid)
                else:
                    unwanted.append(fid)
                if 'priority' in file:
                    if file['priority'] == 'high':
                        priority_high.append(fid)
                    elif file['priority'] == 'normal':
                        priority_normal.append(fid)
                    elif file['priority'] == 'low':
                        priority_low.append(fid)
            self.change([tid], files_wanted = wanted
                        , files_unwanted = unwanted
                        , priority_high = priority_high
                        , priority_normal = priority_normal
                        , priority_low = priority_low)

    def list(self):
        """list all torrents"""
        fields = ['id', 'hashString', 'name', 'sizeWhenDone', 'leftUntilDone'
            , 'eta', 'status', 'rateUpload', 'rateDownload', 'uploadedEver'
            , 'downloadedEver']
        return self._request('torrent-get', {'fields': fields})

    def change(self, ids, **kwargs):
        """
        Change torrent parameters. This is the list of parameters that.
        """
        args = {}
        for key, value in kwargs.iteritems():
            argument = make_rpc_name(key)
            (arg, val) = argument_value_convert('torrent-set'
                                    , argument, value, self.rpc_version)
            args[arg] = val

        if len(args) > 0:
            self._request('torrent-set', args, ids, True)
        else:
            ValueError("No arguments to set")

    def get_session(self):
        """Get session parameters"""
        self._request('session-get')
        return self.session

    def set_session(self, **kwargs):
        """Set session parameters"""
        args = {}
        for key, value in kwargs.iteritems():
            if key == 'encryption' and value not in ['required', 'preferred', 'tolerated']:
                raise ValueError('Invalid encryption value')
            argument = make_rpc_name(key)
            (arg, val) = argument_value_convert('session-set'
                                , argument, value, self.rpc_version)
            args[arg] = val
        if len(args) > 0:
            self._request('session-set', args)

    def blocklist_update(self):
        """Update block list. Returns the size of the block list."""
        self._rpc_version_warning(5)
        result = self._request('blocklist-update')
        if 'blocklist-size' in result:
            return result['blocklist-size']
        return None

    def port_test(self):
        """
        Tests to see if your incoming peer port is accessible from the
        outside world.
        """
        self._rpc_version_warning(5)
        result = self._request('port-test')
        if 'port-is-open' in result:
            return result['port-is-open']
        return None

    def session_stats(self):
        """Get session statistics"""
        self._request('session-stats')
        return self.session
