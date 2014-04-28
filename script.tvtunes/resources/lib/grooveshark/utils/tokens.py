# -*- coding:utf-8 -*-
#
# Copyright (C) 2012, Maximilian Köhl <linuxmaxi@googlemail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import re
import shutil
import subprocess
import tempfile
import urllib.request

def htmlshark():
    app = urllib.request.urlopen('http://static.a.gs-cdn.net/gs/app.js').read().decode('utf-8')
    token = re.search('revToken\s*:\s*"([a-zA-Z]+)"', app).group(1)
    return token

def jsqueue():
    with tempfile.NamedTemporaryFile() as queue:
        shutil.copyfileobj(urllib.request.urlopen('http://grooveshark.com/JSQueue.swf'), queue)
        token = re.search('NULL::secretKey:<q>\[public\]::String\s*=\s*([a-zA-Z]+)', subprocess.check_output(['swfdump', '-a', queue.name], stderr=open('/dev/null', 'wb')).decode('utf-8')).group(1)
    return token

if __name__ == '__main__':
    print('Tokens:')
    print('   HtmlShark: {}'.format(htmlshark()))
    print('   JSQueue: {}'.format(jsqueue()))
