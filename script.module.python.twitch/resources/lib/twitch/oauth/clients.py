# -*- encoding: utf-8 -*-
"""

    Copyright (C) 2016-2018 script.module.python.twitch

    This file is part of script.module.python.twitch

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

from urllib.parse import urlsplit
from urllib.parse import urlencode

from .. import CLIENT_ID, CLIENT_SECRET, methods
from ..queries import OAuthQuery as Qry
from ..queries import query

class MobileClient:
    def __init__(self, client_id='', client_secret=''):
        self.client_id = client_id if client_id else CLIENT_ID
        self.client_secret = client_secret if client_secret else CLIENT_SECRET

    def prepare_request_uri(self, redirect_uri='http://localhost:3000/', scope=list(), force_verify=False, state=''):
        q = Qry('authorize')
        q.add_param('response_type', 'token')
        q.add_param('client_id', self.client_id)
        q.add_param('redirect_uri', redirect_uri)
        q.add_param('scope', ' '.join(scope))
        q.add_param('force_verify', str(force_verify).lower())
        q.add_param('state', state)
        return '?'.join([q.url, urlencode(q.params)])

    def prepare_token_uri(self, scope=list()):
        q = Qry('token')
        q.add_param('client_id', self.client_id)
        q.add_param('client_secret', self.client_secret)
        q.add_param('grant_type', 'client_credentials')
        q.add_param('scope', ' '.join(scope))
        return '?'.join([q.url, urlencode(q.params)])

    def prepare_revoke_uri(self, token):
        q = Qry('revoke')
        q.add_param('client_id', self.client_id)
        q.add_param('token', token)
        return '?'.join([q.url, urlencode(q.params)])

    @query
    def revoke_token(self, token):
        q = Qry('revoke', method=methods.POST)
        q.add_param('client_id', self.client_id)
        q.add_param('token', token)
        return q

    @query
    def get_app_access_token(self, scope=list()):
        q = Qry('token', method=methods.POST)
        q.add_param('client_id', self.client_id)
        q.add_param('client_secret', self.client_secret)
        q.add_param('grant_type', 'client_credentials')
        q.add_param('scope', ' '.join(scope))
        return q

    @staticmethod
    def parse_implicit_response(url):
        pairs = urlsplit(url).fragment.split('&')
        fragment = dict()
        for pair in pairs:
            key, value = pair.split('=')
            fragment[key] = value
        return {'access_token': fragment.get('access_token'), 'scope': fragment.get('scope', '').split('+'), 'state': fragment.get('state')}
