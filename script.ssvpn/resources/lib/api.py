#/*
# *
# * OpenVPN for Kodi.
# *
# * Copyright (C) 2018 Venus
# *
# * This program is free software: you can redistribute it and/or modify
# * it under the terms of the GNU General Public License as published by
# * the Free Software Foundation, either version 3 of the License, or
# * (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program.  If not, see <http://www.gnu.org/licenses/>.
# *
# */

import requests
import hashlib
import time
import json
import base64

# webapi_endpoint = "https://api.5eurovpn.com/json_api/servers.php?"
webapi_endpoint = "https://api.vpnbrand.com/server-list/v2/"
vpnapi_endpoint = "https://www.5eurovpn.com/en/application-api?"

api_secret = "[g(!*.~MXj!84A~Dz\EFdu*=]"
hash_pre = "changeme"

server_username = "admin"
server_password = "suo2Aedi"

def get_time():
    md5Obj = hashlib.md5()
    time_str = str(int(time.time()))

    hash_str = "debug=1time=" + time_str + "command=get_time" + api_secret
    md5Obj.update(hash_str.encode('utf-8'))
    md5_str = md5Obj.hexdigest()

    req_str = webapi_endpoint + "debug=1&time=" + time_str + "&command=get_time&hash=" + md5_str

    try:
        res = requests.get(req_str)
        jsonObj = json.loads(res.content)
    	return jsonObj['time']
    except requests.exceptions.RequestException as e:
        return None

def get_servlist():
    req_url = webapi_endpoint + "long-list"

    auth_orig_str = server_username + ":" + server_password
    base64_auth_str = base64.b64encode(auth_orig_str.encode())
    header_data = "Basic " + base64_auth_str

    try:
        res = requests.get(req_url, headers={"Authorization": header_data})
        jsonObj = json.loads(res.content)
        return jsonObj

    except requests.exceptions.RequestException as e:
        return None

def get_shortlist():
    req_url = webapi_endpoint + "short-list"

    auth_orig_str = server_username + ":" + server_password
    base64_auth_str = base64.b64encode(auth_orig_str.encode())
    header_data = "Basic " + base64_auth_str

    try:
        res = requests.get(req_url, headers={"Authorization": header_data})
        jsonObj = json.loads(res.content)
        return jsonObj

    except requests.exceptions.RequestException as e:
        return None

def get_cities():
    md5Obj = hashlib.md5()
    time_str = get_time()

    hash_str = "debug=1time=" + time_str + "command=cities" + api_secret
    md5Obj.update(hash_str.encode('utf-8'))
    md5_str = md5Obj.hexdigest()

    req_str = webapi_endpoint + "debug=1&time=" + time_str + "&command=cities&hash=" + md5_str

    try:
        res = requests.get(req_str)
        jsonObj = json.loads(res.content)
        return jsonObj

    except requests.exceptions.RequestException as e:
        return None

def login_process_with_email(email, password):
    md5Obj = hashlib.md5()
    total_md5Obj = hashlib.md5()

    hash_str = "email=" + str(email) + "password=" + str(password) + "access=drupalcommand=authenctication_user"
    md5Obj.update(hash_str.encode('utf-8'))
    md5_str = md5Obj.hexdigest()

    total_hash_str = hash_pre + md5_str
    total_md5Obj.update(total_hash_str.encode('utf-8'))
    total_md5_str = total_md5Obj.hexdigest()

    req_str = vpnapi_endpoint + "email=" + str(email) + "&password=" + str(password) + "&access=drupal&command=authenctication_user&hash=" + total_md5_str

    try:
        res = requests.get(req_str)
        jsonObj = json.loads(res.content)
        return jsonObj

    except requests.exceptions.RequestException as e:
        return None

def login_process_with_authcode(code):
    md5Obj = hashlib.md5()
    total_md5Obj = hashlib.md5()

    hash_str = "authentication_code=" + str(code) + "access=auth_codecommand=authenctication_user"
    md5Obj.update(hash_str.encode('utf-8'))
    md5_str = md5Obj.hexdigest()

    total_hash_str = hash_pre + md5_str
    total_md5Obj.update(total_hash_str.encode('utf-8'))
    total_md5_str = total_md5Obj.hexdigest()

    req_str = vpnapi_endpoint + "authentication_code=" + str(code) + "&access=auth_code&command=authenctication_user&hash=" + total_md5_str

    try:
        res = requests.get(req_str)
        jsonObj = json.loads(res.content)
        return jsonObj

    except requests.exceptions.RequestException as e:
        return None

def get_user_info(email, password):
    md5Obj = hashlib.md5()
    total_md5Obj = hashlib.md5()

    hash_str = "email=" + str(email) + "password=" + str(password) + "access=drupalcommand=user_info"
    md5Obj.update(hash_str.encode('utf-8'))
    md5_str = md5Obj.hexdigest()

    total_hash_str = hash_pre + md5_str
    total_md5Obj.update(total_hash_str.encode('utf-8'))
    total_md5_str = total_md5Obj.hexdigest()

    req_str = vpnapi_endpoint + "email=" + str(email) + "&password=" + str(password) + "&access=drupal&command=user_info&hash=" + total_md5_str

    try:
        res = requests.get(req_str)
        jsonObj = json.loads(res.content)
        return jsonObj

    except requests.exceptions.RequestException as e:
        return None

def get_vpn_credential(email, password):
    md5Obj = hashlib.md5()
    total_md5Obj = hashlib.md5()

    hash_str = "email=" + str(email) + "password=" + str(password) + "access=drupalcommand=vpn_credentials"
    md5Obj.update(hash_str.encode('utf-8'))
    md5_str = md5Obj.hexdigest()

    total_hash_str = hash_pre + md5_str
    total_md5Obj.update(total_hash_str.encode('utf-8'))
    total_md5_str = total_md5Obj.hexdigest()

    req_str = vpnapi_endpoint + "email=" + str(email) + "&password=" + str(password) + "&access=drupal&command=vpn_credentials&hash=" + total_md5_str

    try:
        res = requests.get(req_str)
        jsonObj = json.loads(res.content)
        return jsonObj

    except requests.exceptions.RequestException as e:
        return None
