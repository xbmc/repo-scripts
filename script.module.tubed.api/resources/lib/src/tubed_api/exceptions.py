# -*- coding: utf-8 -*-
"""
    Copyright (C) 2020 Tubed API (script.module.tubed.api)

    This file is part of script.module.tubed.api

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""


class TubedAPIException(Exception):
    _data = {
        'error': 'exception',
        'error_description': 'Unknown exception occurred',
        'code': '500'
    }

    def __init__(self, data=None):
        super().__init__()

        if isinstance(data, str) and data:
            self._data['error_description'] = data
        elif isinstance(data, dict):
            self._data.update(data)

    @property
    def data(self):
        return self._data

    @property
    def error(self):
        return self.data.get('error', 'exception')

    @property
    def description(self):
        return self.data.get('description', 'Unknown exception occurred')

    @property
    def code(self):
        return self.data.get('code', '500')


class TubedOAuthException(TubedAPIException):
    pass


class ResourceUnavailable(TubedAPIException):
    pass


class ContentNoResponse(TubedAPIException):
    pass


class ContentRestricted(TubedAPIException):
    pass


class OAuthRequestFailed(TubedOAuthException):
    pass


class OAuthInvalidGrant(TubedOAuthException):
    pass
