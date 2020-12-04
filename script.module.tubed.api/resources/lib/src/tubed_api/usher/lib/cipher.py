# -*- coding: utf-8 -*-
"""

    Copyright (C) 2014-2016 bromix (plugin.video.youtube)
    Copyright (C) 2016-2020 plugin.video.youtube
    Copyright (C) 2020 Tubed API (script.module.tubed.api)

    This file is part of script.module.tubed.api

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

import re

import requests

from ...exceptions import CipherUnknownMethod


class Cipher:
    def __init__(self, url):
        self._data = {

        }
        self._javascript = ''
        self._json = {}
        self._url = url

    def signature(self, signature):
        self._download_javascript()
        self._create_json()
        return Engine(self.json).decipher(signature)

    @property
    def url(self):
        if not self._url.startswith('http'):
            self._url = ''.join(['http://', self._url])
        return self._url

    @url.setter
    def url(self, value):
        self._url = value
        if not value.startswith('http'):
            self._url = ''.join(['http://', value])

    @property
    def data(self):
        return self._data

    @property
    def json(self):
        return self._json

    @property
    def javascript(self):
        return self._javascript

    @javascript.setter
    def javascript(self, value):
        self._javascript = value

    def _download_javascript(self):
        if self.javascript:
            return

        headers = {
            'Connection': 'keep-alive',
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/39.0.2171.36 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'DNT': '1',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.8,de;q=0.6'
        }

        response = requests.get(self.url, headers=headers, allow_redirects=True)
        response.encoding = 'utf-8'

        self.javascript = response.text

    def _get_entry_point(self):
        # patterns source is youtube-dl
        # https://github.com/ytdl-org/youtube-dl/blob/master/youtube_dl/extractor/youtube.py#L1344
        # LICENSE: The Unlicense

        patterns = [
            r'\b[cs]\s*&&\s*[adf]\.set\([^,]+\s*,\s*encodeURIComponent\s*'
            r'\(\s*(?P<function>[a-zA-Z0-9$]+)\(',

            r'\b[a-zA-Z0-9]+\s*&&\s*[a-zA-Z0-9]+\.set\([^,]+\s*,\s*encodeURIComponent\s*'
            r'\(\s*(?P<function>[a-zA-Z0-9$]+)\(',

            r'(?:\b|[^a-zA-Z0-9$])(?P<function>[a-zA-Z0-9$]{2})\s*=\s*function\(\s*a\s*\)\s*'
            r'{\s*a\s*=\s*a\.split\(\s*""\s*\)',

            r'(?P<function>[a-zA-Z0-9$]+)\s*=\s*function\(\s*a\s*\)\s*'
            r'{\s*a\s*=\s*a\.split\(\s*""\s*\)',

            r'(["\'])signature\1\s*,\s*(?P<function>[a-zA-Z0-9$]+)\(',

            r'\.sig\|\|(?P<function>[a-zA-Z0-9$]+)\(',

            r'yt\.akamaized\.net/\)\s*\|\|\s*.*?\s*[cs]\s*&&\s*[adf]\.set\([^,]+\s*,\s*'
            r'(?:encodeURIComponent\s*\()?\s*(?P<function>[a-zA-Z0-9$]+)\(',

            r'\b[cs]\s*&&\s*[adf]\.set\([^,]+\s*,\s*(?P<function>[a-zA-Z0-9$]+)\(',

            r'\b[a-zA-Z0-9]+\s*&&\s*[a-zA-Z0-9]+\.set\([^,]+\s*,\s*(?P<function>[a-zA-Z0-9$]+)\(',

            r'\bc\s*&&\s*a\.set\([^,]+\s*,\s*\([^)]*\)\s*\(\s*(?P<function>[a-zA-Z0-9$]+)\(',

            r'\bc\s*&&\s*[a-zA-Z0-9]+\.set\([^,]+\s*,\s*\([^)]*\)\s*\(\s*'
            r'(?P<function>[a-zA-Z0-9$]+)\(',

            r'\bc\s*&&\s*[a-zA-Z0-9]+\.set\([^,]+\s*,\s*\([^)]*\)\s*\(\s*'
            r'(?P<function>[a-zA-Z0-9$]+)\('
        ]

        function_name = ''
        function_parameter = ''
        function_body = ''

        for pattern in patterns:
            match = re.search(pattern, self.javascript)
            if match:
                function_name = match.group('function')
                break

        if not function_name:
            return {}

        function_name = function_name.replace('$', '\\$')

        pattern = r'\s?%s=function\((?P<parameter>[^)]+)\)\s?{\s?' \
                  r'(?P<body>[^}]+)\s?}' % function_name

        match = re.search(pattern, self.javascript)
        if match:
            function_parameter = match.group('parameter').replace('\n', '').split(',')
            function_body = match.group('body').replace('\n', '').split(';')

        if not function_parameter or not function_body:
            return {}

        return {
            'name': function_name,
            'parameter': function_parameter[0],
            'body': function_body
        }

    def _create_json(self):
        self._json = {
            'actions': []
        }

        entry_point = self._get_entry_point()
        if not entry_point:
            return

        for line in entry_point['body']:

            match = re.match(r'%s\s?=\s?%s.split\(""\)' %
                             (entry_point['parameter'], entry_point['parameter']), line)
            if match:
                self._json['actions'].append({
                    'func': 'list',
                    'params': ['%SIG%']
                })

            match = re.match(r'return\s+%s.join\(""\)' % entry_point['parameter'], line)
            if match:
                self._json['actions'].append({
                    'func': 'join',
                    'params': ['%SIG%']
                })

            match = re.match(
                r'(?P<object_name>[$a-zA-Z0-9]+)\.?\[?"?'
                r'(?P<function_name>[$a-zA-Z0-9]+)"?]?\('
                r'(?P<parameter>[^)]+)\)',
                line
            )
            if match:
                object_name = match.group('object_name')
                function_name = match.group('function_name')
                parameter = match.group('parameter').split(',')

                for index in range(len(parameter)):  # pylint: disable=consider-using-enumerate
                    param = parameter[index].strip()
                    if index == 0:
                        param = '%SIG%'
                    else:
                        param = int(param)

                    parameter[index] = param

                _function = self._get_object_function(object_name, function_name)
                _function_body = _function.get('body', [''])[0]

                match = re.match(r'[a-zA-Z]+.slice\((?P<a>\d+),[a-zA-Z]+\)', _function_body)
                if match:
                    params = ['%SIG%', int(match.group('a')), parameter[1]]
                    self._json['actions'].append({
                        'func': 'slice',
                        'params': params
                    })

                match = re.match(r'[a-zA-Z]+.splice\((?P<a>\d+),[a-zA-Z]+\)', _function_body)
                if match:
                    params = ['%SIG%', int(match.group('a')), parameter[1]]
                    self._json['actions'].append({
                        'func': 'splice',
                        'params': params
                    })

                match = re.match(r'var\s?[a-zA-Z]+=\s?[a-zA-Z]+\[0]', _function_body)
                if match:
                    params = ['%SIG%', parameter[1]]
                    self._json['actions'].append({
                        'func': 'swap',
                        'params': params
                    })

                match = re.match(r'[a-zA-Z].reverse\(\)', _function_body)
                if match:
                    params = ['%SIG%']
                    self._json['actions'].append({
                        'func': 'reverse',
                        'params': params
                    })

    def _find_object_body(self, object_name):
        object_name = object_name.replace('$', '\\$')

        match = re.search(r'var %s={(?P<object_body>.*?})};' % object_name, self.javascript, re.S)
        if match:
            return match.group('object_body')

        return ''

    def _get_object_function(self, object_name, function_name):
        if object_name not in self.data:
            self.data[object_name] = {}
        else:
            if function_name in self.data[object_name]:
                return self.data[object_name][function_name]

        _object_body = self._find_object_body(object_name)
        _object_body = _object_body.split('},')

        for _function in _object_body:
            if not _function.endswith('}'):
                _function = ''.join([_function, '}'])

            _function = _function.strip()

            match = re.match(
                r'(?P<name>[^:]*):function\('
                r'(?P<parameter>[^)]*)\){'
                r'(?P<body>[^}]+)}',
                _function
            )
            if match:
                name = match.group('name').replace('"', '')
                parameter = match.group('parameter')
                body = match.group('body').split(';')

                self.data[object_name][name] = {
                    'name': name,
                    'body': body,
                    'params': parameter
                }

        return self.data[object_name][function_name]


class Engine:
    def __init__(self, script):
        self._json = script

    def decipher(self, signature):
        _signature = signature

        _actions = self._json['actions']
        for action in _actions:
            func = ''.join(['_', action['func']])
            params = action['params']

            if func == '_return':
                break

            for index in range(len(params)):  # pylint: disable=consider-using-enumerate
                param = params[index]
                if param == '%SIG%':
                    param = _signature
                    params[index] = param
                    break

            method = getattr(self, func)
            if method:
                _signature = method(*params)
            else:
                raise CipherUnknownMethod({
                    'error': 'cipher_unknown_method',
                    'error_description': 'Signature deciphering encountered '
                                         'an unknown method %s' % func,
                    'code': '500'
                })

        return _signature

    @staticmethod
    def _join(signature):
        return ''.join(signature)

    @staticmethod
    def _list(signature):
        return list(signature)

    @staticmethod
    def _slice(signature, b):  # pylint: disable=invalid-name
        del signature[b:]
        return signature

    @staticmethod
    def _splice(signature, a, b):  # pylint: disable=invalid-name
        del signature[a:b]
        return signature

    @staticmethod
    def _reverse(signature):
        return signature[::-1]

    @staticmethod
    def _swap(signature, b):  # pylint: disable=invalid-name
        c = signature[0]  # pylint: disable=invalid-name
        signature[0] = signature[b % len(signature)]
        signature[b] = c
        return signature
