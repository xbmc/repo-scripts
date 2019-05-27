import os
import uuid, hmac, hashlib, base64, time
import xbmc, xbmcgui, xbmcaddon
import cookielib, requests


class ADOBE:
    REGGIE_FQDN = 'http://api.auth.adobe.com'
    SP_FQDN = 'http://sp.auth.adobe.com'
    app_id = ''
    app_version = ''
    device_id = ''
    device_type = ''
    device_user = ''
    headers = {
        'Accept': '*/*',
        'Content-type': 'application/x-www-form-urlencoded',
        'Accept-Language': 'en-US',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/43.0.2357.81 Safari/537.36',
        'Connection': 'Keep-Alive',
        'Pragma': 'no-cache'
    }
    mvpd_id = ''
    private_key = ''
    public_key = ''
    reg_code = ''
    registration_url = ''
    requestor_id = ''
    resource_id = ''
    sso_path = xbmc.translatePath(xbmcaddon.Addon('script.module.adobepass').getAddonInfo('profile'))
    verify = False

    def __init__(self, service_vars):
        # service_vars is a dictionary type variable (key: value)
        self.device_id = self.get_device_id()

        # Mandatory Parameters
        self.requestor_id = service_vars['requestor_id']
        self.public_key = service_vars['public_key']
        self.private_key = service_vars['private_key']
        self.registration_url = service_vars['registration_url']
        self.resource_id = service_vars['resource_id']

        # Optional Parameters
        if 'app_id' in service_vars: self.app_id = service_vars['app_id']
        if 'app_version' in service_vars: self.app_version = service_vars['app_version']
        if 'device_type' in service_vars: self.device_type = service_vars['device_type']
        if 'device_user' in service_vars: self.device_user = service_vars['device_user']
        if 'mvpd_id' in service_vars: self.mvpd_id = service_vars['mvpd_id']

    def get_device_id(self):
        file_name = os.path.join(self.sso_path, 'device.id')
        if not os.path.isfile(file_name):
            if not os.path.exists(self.sso_path):
                os.makedirs(self.sso_path)
            new_device_id = str(uuid.uuid1())
            device_file = open(file_name, 'w')
            device_file.write(new_device_id)
            device_file.close()

        file_name = os.path.join(self.sso_path, 'device.id')
        device_file = open(file_name, 'r')
        device_id = device_file.readline()
        device_file.close()

        return device_id

    def create_authorization(self, request_method, request_uri):
        nonce = str(uuid.uuid4())
        epoch_time = str(int(time.time() * 1000))
        authorization = request_method + " requestor_id=" + self.requestor_id + ", nonce=" + nonce \
                        + ", signature_method=HMAC-SHA1, request_time=" + epoch_time + ", request_uri=" + request_uri
        signature = hmac.new(self.private_key, authorization, hashlib.sha1)
        signature = base64.b64encode(signature.digest())
        authorization += ", public_key=" + self.public_key + ", signature=" + signature

        return authorization

    def register_device(self):
        """
        <REGGIE_FQDN>/reggie/v1/{requestorId}/regcode
        Returns randomly generated registration Code and login Page URI
        """
        reggie_url = '/reggie/v1/' + self.requestor_id + '/regcode'
        #reggie_url = '/reggie/v1/nbcsports/regcode'
        self.headers['Authorization'] = self.create_authorization('POST', reggie_url)

        url = self.REGGIE_FQDN + reggie_url

        payload = 'registrationURL='
        if self.registration_url != '':
            payload += self.registration_url
        else:
            payload += self.SP_FQDN + '/adobe-services'

        payload += '&ttl=3600'
        payload += '&deviceId=' + self.device_id
        payload += '&format=json'
        if self.app_id != '': payload += '&appId=' + self.app_id
        if self.app_version != '': payload += '&appVersion=' + self.app_version
        if self.device_type != '': payload += '&deviceType=' + self.device_type
        if self.mvpd_id != '': payload += '&mvpd=' + self.mvpd_id

        r = requests.post(url, headers=self.headers, cookies=self.load_cookies(), data=payload, verify=self.verify)
        self.reg_code = r.json()['code']

        msg = '1. Go to [B][COLOR yellow]' + self.registration_url + '[/COLOR][/B][CR]'
        msg += '2. Select any platform, it does not matter[CR]'
        msg += '3. Enter [B][COLOR yellow]' + self.reg_code + '[/COLOR][/B] as your activation code'

        dialog = xbmcgui.Dialog()
        dialog.ok('Activate Device', msg)

    def pre_auth(self):
        """
        <SP_FQDN>/api/v1/preauthorize
        Retrieves the list of preauthorized resource
        """
        pre_auth_url = '/api/v1/preauthorize'
        self.headers['Authorization'] = self.create_authorization('GET', pre_auth_url)

        url = self.REGGIE_FQDN + preauth_url
        url += '?deviceId=' + self.device_id
        url += '&requestor=' + self.requestor_id
        url += '&resource=' + self.resource_id
        url += '&format=json'

        requests.get(url, headers=self.headers, cookies=self.load_cookies(), verify=self.verify)

    def authorize(self):
        """
        <SP_FQDN>/api/v1/authorize
        Obtains authorization response

        200 - Success
        403 - No Success
        """
        auth_url = '/api/v1/authorize'
        self.headers['Authorization'] = self.create_authorization('GET', auth_url)

        url = self.REGGIE_FQDN + auth_url
        url += '?deviceId=' + self.device_id
        url += '&requestor=' + self.requestor_id
        url += '&resource=' + self.resource_id
        url += '&format=json'

        r = requests.get(url, headers=self.headers, cookies=self.load_cookies(), verify=self.verify)
        self.save_cookies(r.cookies)

        if r.status_code != 200:
            title = 'Authorization Failed'
            if 'message' in r.json() and 'details' in r.json():
                title = r.json()['message']
                msg = r.json()['details']
            elif 'message' in r.json():
                msg = r.json()['message']
            else:
                msg = r.text
            dialog = xbmcgui.Dialog()
            dialog.ok(title, msg)
            return False
        else:
            return True

    def logout(self):
        """
        <SP_FQDN>/api/v1/logout
        Remove AuthN and AuthZ tokens from storage
        """
        auth_url = '/api/v1/logout'
        self.headers['Authorization'] = self.create_authorization('DELETE', auth_url)

        url = self.REGGIE_FQDN + auth_url
        url += '?deviceId=' + self.device_id
        url += '&requestor=' + self.requestor_id
        url += '&format=json'

        r = requests.delete(url, headers=self.headers, cookies=self.load_cookies(), verify=self.verify)

        if r.status_code == 204:
            dialog = xbmcgui.Dialog()
            dialog.notification('Logout', 'You have successfully logged out.', '', 3000, False)

    def media_token(self):
        """
        <SP_FQDN>/api/v1/mediatoken
        Obtains Short Media Token
        """
        token_url = '/api/v1/mediatoken'
        self.headers['Authorization'] = self.create_authorization('GET', token_url)

        url = self.REGGIE_FQDN + token_url
        url += '?deviceId=' + self.device_id
        url += '&requestor=' + self.requestor_id
        url += '&resource=' + self.resource_id
        url += '&format=json'

        r = requests.get(url, headers=self.headers, cookies=self.load_cookies(), verify=self.verify)
        self.save_cookies(r.cookies)

        if r.status_code == 200:
            return r.json()['serializedToken']
        else:
            if 'details' in r.json():
                msg = r.json()['details']
            else:
                msg = r.text

            dialog = xbmcgui.Dialog()
            dialog.ok('Obtain Media Token Failed', msg)
            return ''

    def get_authn(self):
        """
        <SP_FQDN>/api/v1/tokens/authn
        Returns the AuthN token if found

        200 - Success
        404 - Not Found
        410 - Expired
        """
        authn_url = '/api/v1/tokens/authn'
        self.headers['Authorization'] = self.create_authorization('GET', authn_url)

        url = self.SP_FQDN + authn_url
        url += '?deviceId=' + self.device_id
        url += '&requestor=' + self.requestor_id
        url += '&resource=' + self.resource_id
        url += '&format=json'

        r = requests.get(url, headers=self.headers, cookies=self.load_cookies(), verify=self.verify)
        self.save_cookies(r.cookies)

        auth_info = ''
        if 'mvpd' in r.json():
            auth_info = 'Provider: ' + json_source['mvpd']
        if 'expires' in r.json():
            auth_info += ' expires on ' + json_source['expires']

        return auth_info

    def check_authn(self):
        """
        <SP_FQDN>/api/v1/checkauthn
        Indicates whether the device has an unexpired AuthN token.

        200 - Success
        403 - No Success
        """
        authn_url = '/api/v1/checkauthn'
        self.headers['Authorization'] = self.create_authorization('GET', authn_url)

        url = self.SP_FQDN + authn_url
        url += '?deviceId=' + self.device_id
        url += '&format=json'

        r = requests.get(url, headers=self.headers, cookies=self.load_cookies(), verify=self.verify)
        self.save_cookies(r.cookies)

        if r.status_code == 200:
            return True
        else:
            return False

    def get_authz(self):
        """
        <SP_FQDN>/api/v1/tokens/authz
        Returns the AuthZ token if found

        200 - Success
        412 - No AuthN
        404 - No AuthZ
        410 - AuthZ Expired
        """
        authz_url = '/api/v1/tokens/authz'
        self.headers['Authorization'] = self.create_authorization('GET', authz_url)

        url = self.SP_FQDN + authz_url
        url += '?deviceId=' + self.device_id
        url += '&requestor=' + self.requestor_id
        url += '&resource=' + self.resource_id
        url += '&format=json'

        r = requests.get(url, headers=self.headers, cookies=self.load_cookies(), verify=self.verify)
        self.save_cookies(r.cookies)

        if r.status_code != 200:
            title = "Authz Failed" + str(r.status_code)
            if 'message' in r.json():
                title = r.json()['message']
            if 'details' in r.json():
                msg = r.json()['details']
            else:
                msg = r.text

            dialog = xbmcgui.Dialog()
            dialog.ok(title, msg)
            return ''

    def save_cookies(self, cookiejar):
        cookie_file = os.path.join(self.sso_path, 'cookies.lwp')
        cj = cookielib.LWPCookieJar()
        try:
            cj.load(cookie_file, ignore_discard=True)
        except:
            pass
        for c in cookiejar:
            args = dict(vars(c).items())
            args['rest'] = args['_rest']
            del args['_rest']
            c = cookielib.Cookie(**args)
            cj.set_cookie(c)
        cj.save(cookie_file, ignore_discard=True)

    def load_cookies(self):
        cookie_file = os.path.join(self.sso_path, 'cookies.lwp')
        cj = cookielib.LWPCookieJar()
        try:
            cj.load(cookie_file, ignore_discard=True)
        except:
            pass

        return cj
