# -*- coding: utf-8 -*-
"""
    Copyright (C) 2020 Tubed API (script.module.tubed.api)

    This file is part of script.module.tubed.api

    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

import requests

from ..exceptions import OAuthInvalidGrant
from ..exceptions import OAuthRequestFailed
from . import scopes


class Client:
    # https://developers.google.com/youtube/v3/guides/auth/devices

    def __init__(self, client_id='', client_secret=''):
        # pylint: disable=import-outside-toplevel

        if client_id and client_secret:
            self.client_id = client_id
            self.client_secret = client_secret
        else:
            from .. import CLIENT_ID
            from .. import CLIENT_SECRET
            self.client_id = CLIENT_ID
            self.client_secret = CLIENT_SECRET

    def request_codes(self, scope=None):
        headers = {
            'Host': 'accounts.google.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        if not scope:
            scope = scopes.YOUTUBE

        elif isinstance(scope, list):
            scope = ' '.join(scope)

        data = {
            'client_id': self.client_id,
            'scope': scope
        }

        response, payload = self._post('https://accounts.google.com/o/oauth2/device/code',
                                       data=data, headers=headers)

        if 'error' in payload:
            payload.update({
                'code': str(response.status_code)
            })
            raise OAuthRequestFailed(payload)

        if response.status_code != requests.codes.ok:  # pylint: disable=no-member
            raise OAuthRequestFailed({
                'error': 'code_request_failed',
                'error_description': 'Code request failed with status code %s' %
                                     str(response.status_code),
                'code': str(response.status_code)
            })

        if response.headers.get('content-type', '').startswith('application/json'):
            return payload

        raise OAuthRequestFailed({
            'error': 'code_request_failed_unknown',
            'error_description': 'Code request failed with an unknown response',
            'code': str(response.status_code)
        })

    def request_access_token(self, code):
        headers = {
            'Host': 'www.googleapis.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'grant_type': 'http://oauth.net/grant_type/device/1.0'
        }

        response, payload = self._post('https://www.googleapis.com/oauth2/v4/token',
                                       data=data, headers=headers)

        pending = False

        if 'error' in payload:
            pending = payload['error'] == 'authorization_pending'

            if not pending:
                payload.update({
                    'code': str(response.status_code)
                })
                raise OAuthRequestFailed(payload)

        if (response.status_code != requests.codes.ok) and not pending:  # pylint: disable=no-member
            raise OAuthRequestFailed({
                'error': 'access_token_request_failed',
                'error_description': 'Access token request failed with status code %s' %
                                     str(response.status_code),
                'code': str(response.status_code)
            })

        if response.headers.get('content-type', '').startswith('application/json'):
            return payload

        raise OAuthRequestFailed({
            'error': 'access_token_request_failed_unknown',
            'error_description': 'Access token request failed with an unknown response',
            'code': str(response.status_code)
        })

    def refresh_token(self, token):
        headers = {
            'Host': 'www.googleapis.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': token,
            'grant_type': 'refresh_token'
        }

        response, payload = self._post('https://www.googleapis.com/oauth2/v4/token',
                                       data=data, headers=headers)

        if 'error' in payload:
            payload.update({
                'code': str(response.status_code)
            })

            if payload['error'] == 'invalid_grant' and payload['code'] == '400':
                raise OAuthInvalidGrant(payload)

            raise OAuthRequestFailed(payload)

        if response.status_code != requests.codes.ok:  # pylint: disable=no-member
            raise OAuthRequestFailed({
                'error': 'refresh_token_request_failed',
                'error_description': 'Refreshing token failed with status code %s' %
                                     str(response.status_code),
                'code': str(response.status_code)
            })

        if response.headers.get('content-type', '').startswith('application/json'):
            return payload['access_token'], int(payload.get('expires_in', 3600))

        return '', ''

    def revoke_token(self, token):
        headers = {
            'Host': 'accounts.google.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        data = {
            'token': token
        }

        response, payload = self._post('https://accounts.google.com/o/oauth2/revoke',
                                       data=data, headers=headers)

        if 'error' in payload:
            payload.update({
                'code': str(response.status_code)
            })
            raise OAuthRequestFailed(payload)

        if response.status_code != requests.codes.ok:  # pylint: disable=no-member
            raise OAuthRequestFailed({
                'error': 'revoke_token_request_failed',
                'error_description': 'Token revocation failed',
                'code': str(response.status_code)
            })

    @staticmethod
    def _post(url, data, headers):
        response = requests.post(url, data=data, headers=headers)

        response.encoding = 'utf-8'

        try:
            return response, response.json()
        except ValueError:
            return response, {}
