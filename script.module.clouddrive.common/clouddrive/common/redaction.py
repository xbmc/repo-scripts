#-------------------------------------------------------------------------------
# Copyright (C) 2017 Carlos Guzman (cguZZman) carlosguzmang@protonmail.com
#
# This file is part of Cloud Drive Common Module for Kodi
#
# Cloud Drive Common Module for Kodi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Cloud Drive Common Module for Kodi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#-------------------------------------------------------------------------------

import re

# Values that give access to an account. Users post their Kodi logs publicly, so these must never reach a log.
# tempauth: OneDrive's pre-authenticated download links (?tempauth=...) open the file without signing in.
_SECRET_KEYS = r'access_token|refresh_token|id_token|client_secret|code_verifier|device_code|password|code|tempauth'
_REMOVED = '*removed*'

# key=value in query strings, URL fragments, form bodies and Kodi's "url|Header=value" options
_FORM = re.compile(r'(?i)((?:^|[?&|#;\s"\'])(?:' + _SECRET_KEYS + r')=)[^&\s"\']+')
# "key": "value" in JSON, and 'key': 'value' in printed Python dicts
_JSON = re.compile(r'(?i)(["\'](?:' + _SECRET_KEYS + r')["\']\s*:\s*["\'])[^"\']*')
# Authorization header values, also URL-encoded (Bearer%20...)
_AUTH_SCHEME = re.compile(r'(?i)\b((?:Bearer|Basic)(?:\s+|%20|\+))[A-Za-z0-9._~+/=-]+')
# "authorization": "..." header dicts and Authorization=... options with any value
_AUTH_HEADER = re.compile(r'(?i)(["\']?authorization["\']?\s*[:=]\s*["\']?)[^"\'&,}\s]+(?:(?:\s|%20)[^"\'&,}\s]+)?')


def redact(text):
    if not text:
        return text
    text = _FORM.sub(r'\1' + _REMOVED, text)
    text = _JSON.sub(r'\1' + _REMOVED, text)
    text = _AUTH_SCHEME.sub(r'\1' + _REMOVED, text)
    text = _AUTH_HEADER.sub(r'\1' + _REMOVED, text)
    return text
