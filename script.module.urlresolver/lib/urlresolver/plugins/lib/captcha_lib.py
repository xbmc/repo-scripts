"""
    urlresolver XBMC Addon
    Copyright (C) 2014 tknorris

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

    reusable captcha methods
"""
from urlresolver import common
from t0mm0.common.net import Net
import re
import xbmcgui
import xbmc
import os

net = Net()
IMG_FILE = 'captcha_img.png'

def get_response(img):
    try:
        img = xbmcgui.ControlImage(450, 0, 400, 130, img)
        wdlg = xbmcgui.WindowDialog()
        wdlg.addControl(img)
        wdlg.show()
        xbmc.sleep(3000)
        kb = xbmc.Keyboard('', 'Type the letters in the image', False)
        kb.doModal()
        if (kb.isConfirmed()):
            solution = kb.getText()
            if solution == '':
                raise Exception('You must enter text in the image to access video')
            else:
                return solution
        else:
            raise Exception('Captcha Error')
    finally:
        wdlg.close()

def do_captcha(html):
    solvemedia = re.search('<iframe src="((?:https?:)?//api.solvemedia.com[^"]+)', html)
    recaptcha = re.search('<script\s+type="text/javascript"\s+src="(http://www.google.com[^"]+)', html)
    xfilecaptcha = re.search('<img\s+src="([^"]+/captchas/[^"]+)', html)
    
    if solvemedia:
        return do_solvemedia_captcha(solvemedia.group(1))
    elif recaptcha:
        return do_recaptcha(recaptcha.group(1))
    elif xfilecaptcha:
        return do_xfilecaptcha(xfilecaptcha.group(1))
    else:
        captcha = re.compile("left:(\d+)px;padding-top:\d+px;'>&#(.+?);<").findall(html)
        result = sorted(captcha, key=lambda ltr: int(ltr[0]))
        solution = ''.join(str(int(num[1]) - 48) for num in result)
        if solution:
            return {'code': solution}
        else:
            return {}

def do_solvemedia_captcha(captcha_url):
    common.addon.log_debug('SolveMedia Captcha: %s' % (captcha_url))
    if captcha_url.startswith('//'): captcha_url = 'http:' + captcha_url
    html = net.http_GET(captcha_url).content
    data = {
            'adcopy_challenge': ''  # set to blank just in case not found; avoids exception on return
    }
    for match in re.finditer(r'type=hidden.*?name="([^"]+)".*?value="([^"]+)', html):
        name, value = match.groups()
        data[name] = value

    captcha_img = os.path.join(common.profile_path, IMG_FILE)
    try: os.remove(captcha_img)
    except: pass
    
    #Check for alternate puzzle type - stored in a div
    alt_frame = re.search('<div><iframe src="(/papi/media[^"]+)', html)
    if alt_frame:
        html = net.http_GET("http://api.solvemedia.com%s" % alt_frame.group(1)).content
        alt_puzzle = re.search('<div\s+id="typein">\s*<img\s+src="data:image/png;base64,([^"]+)', html, re.DOTALL)
        if alt_puzzle:
            open(captcha_img, 'wb').write(alt_puzzle.group(1).decode('base64'))
    else:
        open(captcha_img, 'wb').write(net.http_GET("http://api.solvemedia.com%s" % re.search('<img src="(/papi/media[^"]+)"', html).group(1)).content)
            
    solution = get_response(captcha_img)
    data['adcopy_response'] = solution
    html = net.http_POST('http://api.solvemedia.com/papi/verify.noscript', data)
    return {'adcopy_challenge': data['adcopy_challenge'], 'adcopy_response': 'manual_challenge'}

def do_recaptcha(captcha_url):
    common.addon.log_debug('Google ReCaptcha: %s' % (captcha_url))
    if captcha_url.startswith('//'): captcha_url = 'http:' + captcha_url
    html = net.http_GET(captcha_url).content
    part = re.search("challenge \: \\'(.+?)\\'", html)
    captcha_img = 'http://www.google.com/recaptcha/api/image?c=' + part.group(1)
    solution = get_response(captcha_img)
    return {'recaptcha_challenge_field': part.group(1), 'recaptcha_response_field': solution}

def do_xfilecaptcha(captcha_url):
    common.addon.log_debug('XFileLoad ReCaptcha: %s' % (captcha_url))
    if captcha_url.startswith('//'): captcha_url = 'http:' + captcha_url
    solution = get_response(captcha_url)
    return {'code': solution}
