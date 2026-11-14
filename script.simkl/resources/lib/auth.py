#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""Login state: the OAuth 2 device flow, token renewal, the legacy pin-flow token, the account line, logout."""

import os
import threading
import time

import xbmc
import xbmcgui

from resources.lib import qr, settings, store, utils
from resources.lib.api import ApiError, CLIENT_V2, SCOPE

DEFAULT_ACCESS_LIFETIME = 7 * 86400
NUDGE_INTERVAL = 5 * 86400
DEVICE_GRANT = 'urn:ietf:params:oauth:grant-type:device_code'
TERMINAL_ERRORS = ('expired_token', 'access_denied', 'invalid_grant', 'invalid_client', 'invalid_request', 'unsupported_grant_type')

PIN_LABEL = 201
INSTRUCTION_LABEL = 202
CANCEL_BUTTON = 203
COUNTDOWN_LABEL = 204
QR_IMAGE = 207
QR_CAPTION = 208
ACTION_PREVIOUS_MENU = 10
ACTION_NAV_BACK = 92


class InvalidToken(Exception):
    pass


class Auth:
    def __init__(self, api):
        self.api = api
        self._renewal = threading.Lock()
        # token and account id are read and published together: a request never sees one login's token with another's account
        self._identity = threading.Lock()
        self._login_thread = None

    # ---------- state ----------

    def token(self):
        return settings.token()

    def logged_in(self):
        return settings.logged_in()

    def is_v2(self):
        return settings.is_v2(self.token())

    @staticmethod
    def _token_fields(data, keep_refresh=''):
        return {
            settings.TOKEN: data['access_token'],
            settings.REFRESH_TOKEN: data.get('refresh_token') or keep_refresh,
            settings.TOKEN_EXPIRES: int(time.time()) + int(data.get('expires_in') or DEFAULT_ACCESS_LIFETIME),
            settings.TOKEN_SCOPE: data.get('scope') or SCOPE,
        }

    def _clear(self):
        with self._identity:
            self._wipe()
        self.update_status()

    @staticmethod
    def _wipe():
        settings.put_identity({key: '' for key in settings.IDENTITY_KEYS})

    # ---------- renewal and authorized calls ----------

    def refresh(self, rejected=None):
        """Renews the access token after a 401, and only then: a renewal tried ahead of time would hold up every
        request while the token endpoint is down. True when a usable token is in hand; False when there is nothing to
        renew (a legacy token, no refresh token) or Simkl refused the renewal for good. A transport failure, a malformed
        answer or an incomplete renewal raises ApiError, so the caller fails that one call instead of throwing a login
        away. rejected: the token the 401 was answered for; when another thread already replaced it, nothing is sent."""
        with self._renewal:
            with self._identity:
                attempted = self.token()
                refresh = settings.get(settings.REFRESH_TOKEN)
            if not settings.is_v2(attempted) or not refresh:
                return False
            if rejected is not None and attempted != rejected:
                return True
            status, data = self.api.request('POST', '/oauth2/token',
                                            {'client_id': CLIENT_V2, 'grant_type': 'refresh_token', 'refresh_token': refresh},
                                            client_id=CLIENT_V2)
            if status < 400 and isinstance(data, dict) and data.get('access_token'):
                with self._identity:
                    # a login that landed during the request owns the slot now: its tokens stay, this answer is dropped
                    if self.token() != attempted:
                        return self.logged_in()
                    settings.put_identity(self._token_fields(data, keep_refresh=refresh))
                utils.log('access token renewed')
                return True
            error = str((data or {}).get('error') or '') if isinstance(data, dict) else ''
            utils.warn('token renewal failed: %s' % (error or 'HTTP %s' % status))
            if error in TERMINAL_ERRORS:
                return False
            raise ApiError(status, error or 'transport', 'renewal did not complete')

    def authorized(self, call, account=None):
        """Runs call(token) for an operation recorded under account ('' = recorded while the account was unknown, None =
        the account lookup itself). A 401 gets one renewal, or the token another thread stored meanwhile, and one retry;
        a token Simkl still rejects is cleared, but only when it is still the stored one. Nothing recorded under an
        account goes out while the connected account is unverified or another one: refused, never sent under a new login."""
        token = self._token_for(account)
        try:
            return call(token)
        except ApiError as exc:
            if exc.status != 401:
                raise
            rejected = exc
        if self.token() == token:
            if not settings.is_v2(token) or not settings.get(settings.REFRESH_TOKEN):
                self.invalidate(token)
                raise InvalidToken()
            try:
                self.refresh(rejected=token)
            except ApiError as failure:
                # a renewal that failed by transport or a server error is not the token's last word: the caller retries
                # that one call later instead of treating the 401 as final
                raise failure if failure.retryable else rejected
        fresh = self._token_for(account)
        if fresh == token:
            self.invalidate(token)
            raise InvalidToken()
        try:
            return call(fresh)
        except ApiError as again:
            if again.status != 401:
                raise
            self.invalidate(fresh)
            raise InvalidToken()

    def _token_for(self, account):
        with self._identity:
            if account is not None:
                current = settings.account_id()
                if not current or (account and account != current):
                    raise InvalidToken()
            token = self.token()
        if not token:
            raise InvalidToken()
        return token

    def invalidate(self, rejected):
        """Clears the login only while the rejected token is still the stored one, in the same step."""
        with self._identity:
            if not rejected or self.token() != rejected:
                return
            self._wipe()
        utils.warn('Simkl rejected the stored token, logging out')
        self.update_status()
        utils.notify(utils.get_str(32213))

    # ---------- account ----------

    def fetch_account(self):
        """Stores the account of the stored token; an answer fetched with a token that was replaced meanwhile is discarded,
        the login that replaced it published its own account."""
        used = {}

        def call(token):
            used['token'] = token
            return self.api.call('GET', '/users/settings', token=token)

        data = self.authorized(call)
        with self._identity:
            if self.token() != used.get('token'):
                return None
            fields = self._account_fields(data)
            settings.put_identity(fields)
        self.update_status()
        return fields

    def _account_with(self, token, monitor, attempts=3):
        """/users/settings with a token that is not stored yet; None when Simkl gave no usable account in three tries."""
        for attempt in range(attempts):
            if attempt and monitor.waitForAbort(2):
                return None
            try:
                data = self.api.call('GET', '/users/settings', token=token)
            except ApiError:
                continue
            if ((data or {}).get('account') or {}).get('id'):
                return data
        return None

    @staticmethod
    def _account_fields(data):
        user = (data or {}).get('user') or {}
        account = (data or {}).get('account') or {}
        # the id arrives as a number; stored and compared as a string everywhere (identity.json, queue entries, sessions)
        return {
            settings.ACCOUNT_ID: str(account.get('id') or ''),
            settings.ACCOUNT_NAME: user.get('name') or '',
            settings.ACCOUNT_PLAN: str(account.get('type') or '').lower(),
        }

    def update_status(self):
        if not self.logged_in():
            settings.put(settings.LOGIN_STATE, 0)
            settings.put(settings.ACCOUNT_STATUS, utils.get_str(32215))
            return
        settings.put(settings.LOGIN_STATE, 2 if self.is_v2() else 1)
        name = settings.get(settings.ACCOUNT_NAME)
        plan = settings.get(settings.ACCOUNT_PLAN)
        if not name:
            label = utils.get_str(32236)
        elif not self.is_v2():
            label = utils.get_str(32242).format(name)
        elif plan in ('pro', 'vip'):
            label = utils.get_str(32217).format(name, plan.upper())
        else:
            label = utils.get_str(32216).format(name)
        settings.put(settings.ACCOUNT_STATUS, label)

    def nudge(self):
        """A legacy login is reminded to reconnect, during playback, at most every five days."""
        if not self.logged_in() or self.is_v2():
            return
        if time.time() - settings.get_int(settings.LAST_NUDGE, 0) < NUDGE_INTERVAL:
            return
        settings.put(settings.LAST_NUDGE, int(time.time()))
        utils.notify(utils.get_str(32212), time_ms=10000)

    # ---------- login and logout ----------

    def logout(self):
        """Clears the login at once and returns what revoke() should tell Simkl about, off the calling thread."""
        token = self.token()
        refresh = settings.get(settings.REFRESH_TOKEN)
        self._clear()
        utils.log('logged out')
        return (refresh or token) if settings.is_v2(token) else ''

    def revoke(self, grant):
        """Best effort: the tokens of a device login are told to Simkl, nothing depends on the answer."""
        if not grant:
            return
        try:
            self.api.request('POST', '/oauth2/revoke', {'client_id': CLIENT_V2, 'token': grant}, client_id=CLIENT_V2)
        except ApiError:
            pass

    def login(self, on_success=None):
        """Starts the device flow on its own thread; the service keeps scrobbling while the code is on screen."""
        if self._login_thread is not None and self._login_thread.is_alive():
            utils.notify(utils.get_str(32239))
            return
        self._login_thread = threading.Thread(target=self._login_flow, args=(on_success,), name='simkl-login')
        self._login_thread.daemon = True
        self._login_thread.start()

    def _login_flow(self, on_success):
        try:
            status, data = self.api.request('POST', '/oauth2/device', {'client_id': CLIENT_V2, 'scope': SCOPE}, client_id=CLIENT_V2)
        except ApiError:
            utils.notify(utils.get_str(32210))
            return
        if status >= 400 or not isinstance(data, dict) or not data.get('device_code') or not data.get('user_code'):
            utils.notify(utils.get_str(32240))
            return
        dialog = DeviceLoginDialog('simkl-DeviceLoginDialog.xml', utils.ADDON_PATH,
                                   code=str(data['user_code']),
                                   url=str(data.get('verification_uri') or 'https://simkl.com/pin'),
                                   complete=str(data.get('verification_uri_complete') or ''),
                                   expires=int(data.get('expires_in') or 900))
        poller = threading.Thread(target=self._poll, args=(dialog, str(data['device_code']), int(data.get('interval') or 5), int(data.get('expires_in') or 900), on_success), name='simkl-login-poll')
        poller.daemon = True
        poller.start()
        dialog.doModal()
        dialog.closed = True
        del dialog

    def _poll(self, dialog, device_code, interval, expires_in, on_success):
        """Every path here closes the dialog or leaves it to the user; nothing escapes as an unhandled error."""
        monitor = xbmc.Monitor()
        deadline = time.time() + expires_in
        try:
            while not dialog.closed and time.time() < deadline:
                if monitor.waitForAbort(max(5, interval)):
                    return
                if dialog.closed:
                    return
                try:
                    status, data = self.api.request('POST', '/oauth2/token',
                                                    {'client_id': CLIENT_V2, 'grant_type': DEVICE_GRANT, 'device_code': device_code},
                                                    client_id=CLIENT_V2)
                except ApiError:
                    continue
                if dialog.closed:
                    return
                if status < 400 and isinstance(data, dict) and data.get('access_token'):
                    # the account is read with the new token before anything is stored, so the stored token and the
                    # stored account id change together; a login whose account cannot be read is not completed
                    account = self._account_with(data['access_token'], monitor)
                    if account is None:
                        utils.notify(utils.get_str(32210))
                        return
                    with self._identity:
                        # cancelled while the requests were out: a later login may own the slot by now
                        if dialog.closed:
                            return
                        previous = settings.account_id()
                        # one write for tokens and account: a crash between two would leave this token under the previous account
                        fields = self._token_fields(data)
                        fields.update(self._account_fields(account))
                        # a reconnect keeps the account, as its help says: another one on the phone is not taken over
                        other = fields[settings.ACCOUNT_NAME] if previous and fields[settings.ACCOUNT_ID] != previous else None
                        before = {key: settings.get(key) for key in settings.IDENTITY_KEYS}
                        saved = other is None and settings.put_identity(fields)
                        if other is None and not saved:
                            # identity.json could not be written: the login would vanish at the next start, so it is not
                            # taken at all, and the memory copy goes back to what the file still holds
                            settings.put_identity(before, write=False)
                    if other is not None or not saved:
                        if other is not None:
                            utils.notify(utils.get_str(32301).format(other), time_ms=10000)
                        else:
                            utils.notify(utils.get_str(32031))
                        self.revoke(data.get('refresh_token') or data['access_token'])
                        return
                    self.update_status()
                    utils.log('logged in through the device flow')
                    utils.notify(utils.get_str(32030).format(fields[settings.ACCOUNT_NAME]))
                    if on_success is not None:
                        on_success(previous, fields[settings.ACCOUNT_ID])
                    return
                error = str(data.get('error') or '') if isinstance(data, dict) else ''
                if error == 'authorization_pending':
                    continue
                if error == 'slow_down':
                    interval += 5
                    continue
                if error == 'expired_token':
                    utils.notify(utils.get_str(32226))
                    return
                if error == 'access_denied':
                    utils.notify(utils.get_str(32227))
                    return
                if error in TERMINAL_ERRORS:
                    utils.warn('device login stopped: %s' % error)
                    utils.notify(utils.get_str(32031))
                    return
            if not dialog.closed:
                utils.notify(utils.get_str(32226))
        except Exception as exc:
            utils.error('device login failed: %r' % exc)
            utils.notify(utils.get_str(32031))
        finally:
            dialog.close()


class DeviceLoginDialog(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.code = kwargs['code']
        self.url = kwargs['url']
        self.complete = kwargs['complete']
        self.expires_at = time.time() + kwargs['expires']
        self.closed = False
        self.qr_path = ''

    def onInit(self):
        self.getControl(PIN_LABEL).setLabel(self.code)
        self.getControl(INSTRUCTION_LABEL).setLabel(utils.get_str(32022).format('[B][COLOR ffffbf00]' + self.url + '[/COLOR][/B]'))
        self._show_qr()
        countdown = threading.Thread(target=self._countdown, name='simkl-login-countdown')
        countdown.daemon = True
        countdown.start()

    def _show_qr(self):
        """The pin link as a QR code for the phone, drawn into the add-on profile for this code; a failure only leaves
        the picture empty, the code and the link still work."""
        try:
            self.qr_path = store.path('qr-%s.png' % self.code.replace('-', ''))
            with open(self.qr_path, 'wb') as handle:
                handle.write(qr.png(self.complete or '%s?user_code=%s' % (self.url, self.code)))
            self.getControl(QR_IMAGE).setImage(self.qr_path, False)
            self.getControl(QR_CAPTION).setLabel(utils.get_str(32282))
        except Exception as exc:
            utils.error('cannot draw the QR code: %r' % exc)

    def _countdown(self):
        monitor = xbmc.Monitor()
        while not self.closed:
            remaining = int(self.expires_at - time.time())
            if remaining <= 0:
                break
            try:
                self.getControl(COUNTDOWN_LABEL).setLabel(utils.get_str(32200).format(utils.format_duration(remaining)))
            except RuntimeError:
                break
            if monitor.waitForAbort(1):
                break

    def onAction(self, action):
        if action.getId() in (ACTION_PREVIOUS_MENU, ACTION_NAV_BACK):
            self.close()

    def onClick(self, control_id):
        if control_id == CANCEL_BUTTON:
            self.close()

    def close(self):
        self.closed = True
        if self.qr_path:
            try:
                os.remove(self.qr_path)
            except OSError:
                pass
            self.qr_path = ''
        super().close()
