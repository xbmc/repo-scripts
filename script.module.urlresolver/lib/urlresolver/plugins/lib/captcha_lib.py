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

net = Net()

def get_response(img):
    try:
        img = xbmcgui.ControlImage(450,15,400,130,img)
        wdlg = xbmcgui.WindowDialog()
        wdlg.addControl(img)
        wdlg.show()
        xbmc.sleep(3000)
        kb = xbmc.Keyboard('', 'Type the letters in the image', False)
        kb.doModal()
        if (kb.isConfirmed()):
            solution = kb.getText()
            if solution == '':
                raise Exception ('You must enter text in the image to access video')
            else:
                return solution
        else:
            raise Exception ('Captcha Error')
    finally:
        wdlg.close()

def do_solvemedia_captcha(captcha_url, puzzle_img):
    common.addon.log_debug('SolveMedia Captcha')
    html = net.http_GET(captcha_url).content
    hugekey=re.search('id="adcopy_challenge" value="(.+?)">', html).group(1)
    open(puzzle_img, 'wb').write(net.http_GET("http://api.solvemedia.com%s" % re.search('<img src="(.+?)"', html).group(1)).content)
    solution = get_response(puzzle_img)
    return {'adcopy_challenge': hugekey,'adcopy_response': solution}

def do_recaptcha(captcha_url):
    common.addon.log_debug('Google ReCaptcha')
    html = net.http_GET(captcha_url).content
    part = re.search("challenge \: \\'(.+?)\\'", html)
    captchaimg = 'http://www.google.com/recaptcha/api/image?c='+part.group(1)
    solution = get_response(captchaimg)
    return {'recaptcha_challenge_field': part.group(1),'recaptcha_response_field': solution}

    