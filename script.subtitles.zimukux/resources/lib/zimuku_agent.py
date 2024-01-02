"""
Subtitle add-on for Kodi 19+ derived from https://github.com/taxigps/xbmc-addons-chinese/tree/master/service.subtitles.zimuku
Copyright (C) <2021>  <root@wokanxing.info>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""


import os
import sys
import time
import json
import base64
import urllib
import requests
from bs4 import BeautifulSoup


class Zimuku_Agent:
    def __init__(self, base_url, dl_location, logger, unpacker, settings, ocrUrl=''):
        self.ua = 'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; Trident/6.0)'
        self.ZIMUKU_BASE = base_url
        # self.ZIMUKU_API = '%s/search?q=%%s&vertoken=%%s' % base_url
        self.ZIMUKU_API = '%s/search?q=%%s' % base_url
        self.INIT_PAGE = base_url + '/?security_verify_data=313932302c31303830'
        self.DOWNLOAD_LOCATION = dl_location
        self.FILE_MIN_SIZE = 1024

        self.logger = logger
        self.unpacker = unpacker
        self.plugin_settings = settings
        self.session = requests.Session()
        self.vertoken = ''
        self.ocrUrl = ocrUrl

        # 一次性调用，获取必需的cookies，验证机制可能之后会变
        self.init_site()

    def set_setting(self, settings):
        # for unittestting purpose
        self.plugin_settings = settings

    def init_site(self):
        self.get_page(self.INIT_PAGE)
        self.get_page(self.INIT_PAGE)

    def get_page(self, url, **kwargs):
        """
        Get page with requests session.

        Parameters:
            url     Target URL.
            kwargs  Attached headers. HTTP_HEADER_KEY = HTTP_HEADER_VALUE. Use '_' instead of '-' in HTTP_HEADER_KEY since '-' is illegal in python variable name.

        Return:
            headers     The http response headers.
            http_body   The http response body.
        """
        headers = None
        http_body = None
        s = self.session
        try:
            request_headers = {'User-Agent': self.ua}
            if kwargs:
                for key, value in list(kwargs.items()):
                    request_headers[key.replace('_', '-')] = value

            a = requests.adapters.HTTPAdapter(max_retries=3)
            s.mount('http://', a)

            # url += '&' if '?' in url else '?'
            # url += 'security_verify_data=313932302c31303830'

            self.logger.log(sys._getframe().f_code.co_name,
                            'requests GET [%s]' % (url), level=3)

            http_response = s.get(url, headers=request_headers)
            """
            if http_response.status_code != 200:
                s.get(url, headers=request_headers)
                http_response = s.get(url, headers=request_headers)
            """

            headers = http_response.headers
            http_body = http_response.content
        except Exception as e:
            self.logger.log(sys._getframe().f_code.co_name,
                            "ERROR READING %s: %s" % (url, e), level=3)

        return headers, http_body

    def verify(self, url, append):
        headers = None
        http_body = None
        s = self.session
        try:
            request_headers = {'User-Agent': self.ua}

            a = requests.adapters.HTTPAdapter(max_retries=3)
            s.mount('https://', a)

            self.logger.log(sys._getframe().f_code.co_name,
                            '[CHALLENGE VERI-CODE] requests GET [%s]' % (url), level=3)

            http_response = s.get(url, headers=request_headers)

            if http_response.status_code != 200:
                soup = BeautifulSoup(http_response.content, 'html.parser')
                content = soup.find_all(attrs={'class': 'verifyimg'})[
                    0].get('src')
                if content is not None:
                    # 处理编码
                    ocrurl = self.ocrUrl
                    payload = {'imgdata': content}
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.54 Safari/537.36'
                    }
                    response = requests.request(
                        "POST", ocrurl, headers=headers, json=payload)
                    result_json = json.loads(response.text)
                    text = ''
                    if result_json['code'] == 1:
                        text = result_json['result']
                    str1 = ''
                    i = 0
                    for ch in text:
                        if str1 == '':
                            str1 = hex(ord(text[i]))
                        else:
                            str1 += hex(ord(text[i]))
                        i = i + 1

                    # 使用带验证码的访问
                    get_cookie_url = '%s%s&%s' % (
                        url, append, 'security_verify_img=' + str1.replace('0x', ''))
                    http_response = s.get(
                        get_cookie_url, headers=request_headers)
                    a = 1

        except Exception as e:
            self.logger.log(sys._getframe().f_code.co_name,
                            "ERROR CHALLENGING VERI-CODE(target URL: %s): %s" % (url, e), level=3)

    def extract_sub_info(self, sub, lang_info_mode):
        """
        从 html 块中解析出字幕信息

        Params:
            ele              包含字幕信息的 html 块，由美丽肥皂返回
            lang_info_mode   搜索第一页面显示的字幕，里面包含的语言信息跟详情页的不一样，需要用两套规则处理  

        Return:
            []  字幕信息列表，格式：
                {
                    "language_name": 'Chinese',
                    "filename": 显示在 Kodi 界面的子目名称,
                    "link": 下载页面地址,
                    "language_flag": 'zh',
                    "rating": 0-5（字符）,
                    "lang": ['简体中文', 'English']
                }
        """
        link = urllib.parse.urljoin(self.ZIMUKU_BASE, sub.a.get('href'))
        disp_ep_info = sub.a.text

        langs = []
        if lang_info_mode == 1:
            # 这个变量代表从哪里得到的字幕
            # 1：搜索第一页面，那么语言从 img 的 alt 属性读出来
            # alt="&nbsp;简体中文字幕&nbsp;English字幕&nbsp;双语字幕"
            alt_text = sub.img.get('alt')
            langs = alt_text.split('\xa0')
            if langs[0] == '':
                langs = langs[1:]
            langs = [lang.rstrip('字幕') for lang in langs]
        elif lang_info_mode == 2:
            # 2：某一季的页面，那么 img 外面的 td 的 class 不一样
            try:
                td = sub.find("td", class_="tac lang")
                r2 = td.find_all("img")
                langs = [x.get('title').rstrip('字幕') for x in r2]
            except:
                langs = '未知'
        ab_langs = []
        if '简体中文' in langs:
            ab_langs.append('简')
        if '繁體中文' in langs:
            ab_langs.append('繁')
        if '双语' in langs:
            ab_langs.append('双')
        if 'English' in langs:
            ab_langs.append('英')
        name = '[ %s ] %s' % (''.join(ab_langs), disp_ep_info)

        # Get rating. rating from str(int [0 , 5]).
        # 「字幕库」的 rating 有 11 档，从 allstar00 05 到 50，但好像除了 00 就是 50……
        # <i class="rating-star allstar50 tooltips"
        try:
            rating_div = sub.find("i", class_="rating-star")
            rating_div_str = str(rating_div)
            rating_star_str = "allstar"
            rating = rating_div_str[
                rating_div_str.find(rating_star_str) +
                len(rating_star_str)]
            if rating not in ["0", "1", "2", "3", "4", "5"]:
                self.logger.log(
                    sys._getframe().f_code.co_name, "NO RATING AVAILABLE IN (%s), URL: %s" %
                                                    (rating_div_str, link),
                    2)
                rating = "0"
        except:
            rating = "0"

        # In GUI, only "lang", "filename" and "rating" displays to users,
        lang_vals = ['', '']
        if '简体中文' in langs or '繁體中文' in langs or '双语' in langs:
            lang_vals = ['Chinese', 'zh']
        elif 'English' in langs:
            lang_vals = ['English', 'en']
        else:
            self.logger.log(sys._getframe().f_code.co_name,
                            "Unrecognized lang: %s" % (langs))
            lang_vals = ['Unknown', '']

        return {
            "language_name": lang_vals[0],
            "filename": name,
            "link": link,
            "language_flag": lang_vals[1],
            "rating": rating,
            "lang": langs
        }

    def get_vertoken(self, resp):
        # get vertoken from home page and cache it for the session
        self.logger.log(sys._getframe().f_code.co_name,
                        "Fetching new vertoken form home page")
        try:
            headers, data = self.get_page(self.ZIMUKU_BASE + '/')
            hsoup = BeautifulSoup(resp, 'html.parser')
            vertoken = hsoup.find(
                'input', attrs={'name': 'vertoken'}).attrs.get('value', '')
            self.vertoken = vertoken
            return vertoken
        except Exception as e:
            self.logger.log(sys._getframe().f_code.co_name, 'ERROR GETTING vertoken, E=(%s: %s)' %
                            (Exception, e), level=3)
            return ''

    def search(self, title, items):
        """
        搜索字幕

        Params:
            title    片名
            item     Kodi 传进来的参数，如：
                        {
                        'temp': False, 'rar': False, 'mansearch': False, 'year': '2021', 'season': '4',
                        'episode': '17', 'tvshow': '小谢尔顿', 'title': '由一个黑洞引发的联想',
                        'file_original_path':
                        'C:\\Young.Sheldon.S04E17.720p.HEVC.x265-MeGusta.mkv',
                        '3let_language': ['eng']
                        }

        Return:
            []       供选择的字幕清单，格式为 extract_sub_info 的返回值
        """
        subtitle_list = []

        # vertoken = self.get_vertoken()

        url = self.ZIMUKU_API % urllib.parse.quote(title)
        try:
            # 10/10/22: 变成搜索要先拿 cookie
            # self.get_page(url)
            # self.get_page(get_cookie_url)

            # 处理验证码逻辑
            # self.verify(url, '&chost=zimuku.org')

            # 真正的搜索
            self.logger.log(sys._getframe().f_code.co_name,
                            "Search API url: %s" % (url))

            url += '&chost=zimuku.org'
            _, data = self.get_page(url)
            soup = BeautifulSoup(data, 'html.parser')
        except Exception as e:
            self.logger.log(sys._getframe().f_code.co_name, 'ERROR SEARCHING, E=(%s: %s)' %
                            (Exception, e), level=3)
            return []

        s_e = 'S%02dE%02d' % (int(items['season']), int(items['episode'])
                              ) if items['season'] != '' and items['episode'] != '' else 'N/A'
        if s_e != 'N/A':
            # 1. 从搜索结果中看看是否能直接找到
            sub_list = soup.find_all('tr')
            self.logger.log(sys._getframe().f_code.co_name, "to find [%s] in %s" % (
                s_e, [ep.a.text for ep in sub_list]))
            for sub in reversed(sub_list):
                sub_name = sub.a.text
                if s_e in sub_name.upper():
                    subtitle_list.append(self.extract_sub_info(sub, 1))
                    # break  还是全列出来吧

        if len(subtitle_list) != 0:
            return self.double_filter(subtitle_list, items)

        # 2. 直接找不到，看是否存在同一季的链接，进去找
        season_name_chn = \
            ('一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一', '十二', '十三', '十四', '十五')[
                int(items['season']) - 1] if s_e != 'N/A' else 'N/A'
        season_list = soup.find_all("div", class_="item prel clearfix")

        page_list = soup.find('div', class_='pagination')
        if page_list:
            pages = page_list.find_all('a', class_='num')
            if len(pages) > 3:  # 这么多，是不是有问题……
                self.logger.log(sys._getframe().f_code.co_name,
                                "TOO MANY PAGES RETURNED, TRIMMED TO 3")
                pages = pages[:3]
            for page in pages:
                url = urllib.parse.urljoin(self.ZIMUKU_BASE, page.get('href'))
                try:
                    headers, data = self.get_page(url)
                    soup = BeautifulSoup(data, 'html.parser')
                    season_list.extend(soup.find_all(
                        "div", class_='item prel clearfix'))
                except:
                    self.logger.log(sys._getframe().f_code.co_name,
                                    'ERROR GETTING PAGE', level=3)

        for s in season_list:
            season_name = s.b.text
            if '第%s季' % season_name_chn in season_name:
                url = urllib.parse.urljoin(self.ZIMUKU_BASE, s.find(
                    "div", class_="title").a.get('href'))
                try:
                    headers, data = self.get_page(url)
                    soup = BeautifulSoup(
                        data, 'html.parser').find(
                        "div", class_="subs box clearfix")
                except:
                    self.logger.log(sys._getframe().f_code.co_name,
                                    'Error getting sub page', level=3)
                    return []
                subs = soup.tbody.find_all("tr")
                unfiltered_sub_list = []
                for sub in reversed(subs):
                    subtitle = self.extract_sub_info(sub, 2)
                    unfiltered_sub_list.append(subtitle)
                    sub_name = sub.a.text
                    if s_e in sub_name.upper():
                        subtitle_list.append(subtitle)
                # 如果匹配到了季，那就得返回了，没有就是没有
                # 如果没有匹配到，可能整季度的字幕被打包到一个文件中了，那就把所有的结果都返回让用户自己选择
                if len(subtitle_list) > 0:
                    return self.double_filter(subtitle_list, items)
                else:
                    return unfiltered_sub_list

        # 精确查找没找到，那就返回所有
        subtitle_list = []
        urls = [urllib.parse.urljoin(
            self.ZIMUKU_BASE, s.find("div", class_="title").a.get('href'))
            for s in reversed(season_list)]
        for url in urls:
            try:
                headers, data = self.get_page(url)
                soup = BeautifulSoup(
                    data, 'html.parser').find(
                    "div", class_="subs box clearfix")
            except:
                self.logger.log(sys._getframe().f_code.co_name,
                                'Error getting sub page', level=3)
                return []
            subs = soup.tbody.find_all("tr")
            for sub in reversed(subs):
                subtitle_list.append(self.extract_sub_info(sub, 2))

        return self.double_filter(subtitle_list, items)

    def double_filter(self, subtitle_list, items):
        # 适用当前集数再次过滤字幕
        try:
            episode = int(items['episode'])
            es = 'E%02d' % episode
            filtered = [
                s for s in subtitle_list if es in s['filename'].upper()]
            return filtered if len(filtered) > 0 else subtitle_list
        except:
            return subtitle_list

    def find_in_list(self, lst, include, *kws):
        """
        在列表中按关键字查找元素

        Params:
            include     包含字符串，还是排除字符串
            kws         任意个待查找的字符串，如果 include 是 OR 的关系，否则是 AND。

        Return:
            []  查找结果
        """
        if lst is None:
            return lst
        new_lst = []
        for e in lst:
            s = e.lower()
            exclude_match = False
            for kw in kws:
                if include:
                    if s.find(kw) != -1:
                        new_lst.append(e)
                        break
                else:
                    if s.find(kw) != -1:
                        exclude_match = True
                        break
            if not include and not exclude_match:
                new_lst.append(e)
        return new_lst

    def get_preferred_subs(self, sub_name_list, short_sub_name_list, sub_file_list):
        """
        根据插件的参数找出偏好的字幕

        Params:
            sub_name_list       文件名
            short_sub_name_list 短文件名
            sub_file_list       对应的文件绝对路径

        Return:
            [], [], []  返回筛选列表。如果筛选结果是空，意味着没有匹配上任意一条，那就返回传进来的列表；也可能不止一条，比如只指定了 srt 然后有不止一条
        """
        if len(sub_name_list) <= 1:
            return sub_name_list, short_sub_name_list, sub_file_list
        else:
            tpe = self.plugin_settings['subtype']
            lang = self.plugin_settings['sublang']
            self.logger.log(sys._getframe().f_code.co_name,
                            "按照偏好筛选字幕：%s，类型=%s，语言=%s" % (
                                sub_name_list, tpe, lang),
                            level=1)

            if tpe == 'none ' and lang == 'none':
                return sub_name_list, short_sub_name_list, sub_file_list
            filtered_name_list = sub_name_list
            if tpe != 'none':
                filtered_name_list = self.find_in_list(
                    filtered_name_list, True, "." + tpe)
                self.logger.log(sys._getframe().f_code.co_name, "筛完类型：%s" %
                                filtered_name_list, level=1)
            if lang != 'none':
                # chs/cht/dualchs/dualcht
                if lang.startswith('dual'):
                    filtered_name_list = self.find_in_list(
                        filtered_name_list, True, '英', 'eng', '双语')
                    if lang == 'dualchs':
                        filtered_name_list = self.find_in_list(
                            filtered_name_list, True, '简', 'chs')
                    else:
                        filtered_name_list = self.find_in_list(
                            filtered_name_list, True, '繁', 'cht')
                else:
                    if lang == 'chs':
                        filtered_name_list = self.find_in_list(
                            filtered_name_list, True, '简', 'chs')
                    else:
                        filtered_name_list = self.find_in_list(
                            filtered_name_list, True, '繁', 'cht')
                    filtered_name_list = self.find_in_list(
                        filtered_name_list, False, '英', 'eng', '双语')
                self.logger.log(sys._getframe().f_code.co_name, "筛完语言：%s" %
                                filtered_name_list, level=1)
            if len(filtered_name_list) == 0:
                return sub_name_list, short_sub_name_list, sub_file_list

            # 把原先的路径找回来
            indices = [sub_name_list.index(x) for x in filtered_name_list]
            return filtered_name_list, [short_sub_name_list[x] for x in indices], [sub_file_list[x] for x in indices]

    def download(self, url):
        """
        下载并返回字幕文件列表

        Params:
            url    字幕详情页面，如 https://srtku.com/detail/155262.html

        Return:
            [], [], []  返回 3 个列表
            第一个为文件名（用于不止一个时在 Kodi 界面上让用户选择）
            第二个是极短文件名（通过参数 cutsubfn 控制，避免文件名过长滚动）
                短文件名本来在 sub_provider_service 做更合适（PR 也是这么提的），但问题是那样不好写 testcase，所以先放这里
            第三个为完整路径（用户送给播放器使用）
        """
        exts = (".srt", ".sub", ".smi", ".ssa", ".ass", ".sup")
        supported_archive_exts = (".zip", ".7z", ".tar", ".bz2", ".rar",
                                  ".gz", ".xz", ".iso", ".tgz", ".tbz2", ".cbr")
        try:
            # 处理验证码逻辑
            # self.verify(url, '?')

            # Subtitle detail page.
            headers, data = self.get_page(url)
            soup = BeautifulSoup(data, 'html.parser')
            url = soup.find("li", class_="dlsub").a.get('href')

            if not (url.startswith(('http://', 'https://'))):
                url = urllib.parse.urljoin(self.ZIMUKU_BASE, url)

            # 处理验证码逻辑
            # self.verify(url, '?')

            # Subtitle download-list page.
            headers, data = self.get_page(url)
            soup = BeautifulSoup(data, 'html.parser')
            links = soup.find("div", {"class": "clearfix"}).find_all('a')
        except:
            self.logger.log(sys._getframe().f_code.co_name, "Error (%d) [%s]" % (
                sys.exc_info()[2].tb_lineno, sys.exc_info()[1]), level=3)
            return [], [], []

        filename, data = self.download_links(links, url)
        if filename == '':
            # No file received.
            return [], [], []

        # 小写扩展名
        dot = filename.rfind(".")
        if dot != -1:
            filename = filename[:dot] + filename[dot:].lower()

        rtn_list = []
        if filename.endswith(exts):
            full_path = self.store_file(filename, data)
            fn = self.fix_garbled_filename(os.path.basename(full_path))
            return [fn], [fn], [full_path]
        elif filename.endswith(supported_archive_exts):
            full_path = self.store_file(filename, data)
            archive_path, sub_name_list = self.unpacker.unpack(full_path)

            # 返回的文件名不能做乱码修正，不然找不到……
            sub_file_list = [os.path.join(archive_path, x).replace('\\', '/')
                             for x in sub_name_list]
            sub_name_list = [self.fix_garbled_filename(
                x) for x in sub_name_list]

            if len(sub_name_list) > 1:
                # 不显示相同的前缀，防止文件名过长滚动
                shortest_fn = min(sub_name_list, key=len)
                diff_index = next(filter(
                    lambda i: any(s[i] != shortest_fn[i]
                                  for s in sub_name_list),
                    range(len(shortest_fn))
                ))
                dot = shortest_fn[:diff_index].rfind('.') + 1
                short_sub_name_list = [s[dot:] for s in sub_name_list]

                return sub_name_list, short_sub_name_list, sub_file_list
            else:
                return sub_name_list, sub_name_list, sub_file_list
        else:
            self.logger.log(sys._getframe().f_code.co_name, "UNSUPPORTED FILE: % s" %
                            (filename), level=2)
            # xbmc.executebuiltin(('XBMC.Notification("zimuku","不支持的压缩格式，请选择其他字幕文件。")'), True)
            return [], [], []

    def fix_garbled_filename(self, fn):
        # hack to fix encoding problem of zip file
        # https://blog.csdn.net/u010099080/article/details/79829247
        # if data[:2] == 'PK':   //pizzamx: 这个检测好像没用
        try:
            return fn.encode('CP437').decode('gbk')
        except:
            return fn

    def store_file(self, filename, data):
        """
        Store file function. Store bin(data) into os.path.join(__temp__, "subtitles<time>.<ext>")

        This may store subtitle files or compressed archive. So write in binary mode.

        Params:
            filename    The name of the file. May include non-unicode chars, so may cause problems if used as filename to store directly.
            data        The data of the file. May be compressed.

        Return:
            The absolute path to the file.
        """
        # Store file in an ascii name since some chars may cause some problems.
        t = time.time()
        ts = time.strftime("%Y%m%d%H%M%S", time.localtime(t)
                           ) + str(int((t - int(t)) * 1000))
        tempfile = os.path.join(self.DOWNLOAD_LOCATION, "subtitles%s%s" % (
            ts, os.path.splitext(filename)[1])).replace('\\', '/')
        with open(tempfile, "wb") as sub_file:
            sub_file.write(data)
            sub_file.flush()
            os.fsync(sub_file.fileno())
        return tempfile.replace('\\', '/')

    def download_links(self, links, referer):
        """
        Download subtitles one by one until success.

        Parameters:
            links   The list of subtitle download links.
            referer The url of dld list page, used as referer.

        Return:
            '', []          If nothing to return.
            filename, data  If success.
        """
        filename = None
        data = None
        small_size_confirmed = False
        data_size = -1
        link_string = ''

        for link in links:
            url = link.get('href')
            if not url.startswith('http'):
                url = urllib.parse.urljoin(self.ZIMUKU_BASE, url)
            link_string += url + ' '

            try:
                self.logger.log(sys._getframe().f_code.co_name,
                                "DOWNLOAD SUBTITLE: %s" % (url))

                # 处理验证码逻辑
                # self.verify(url, '?')

                # Download subtitle one by one until success.
                headers, data = self.get_page(url, Referer=referer)

                filename = headers['Content-Disposition'].split(
                    'filename=')[1].strip('"').strip("'")
                small_size_confirmed = data_size == len(data)
                if len(data) > self.FILE_MIN_SIZE or small_size_confirmed:
                    break
                else:
                    data_size = len(data)

            except Exception:
                if filename is not None:
                    self.logger.log(sys._getframe().f_code.co_name,
                                    "Failed to download subtitle data of %s." % (
                                        filename),
                                    level=2)
                    filename = None
                else:
                    self.logger.log(sys._getframe().f_code.co_name,
                                    "Failed to download subtitle from %s" % (
                                        url),
                                    level=2)

        if filename is not None:
            if data is not None and (len(data) > self.FILE_MIN_SIZE or small_size_confirmed):
                return filename, data
            else:
                self.logger.log(
                    sys._getframe().f_code.co_name, 'File received but too small: %s %d bytes' %
                                                    (filename, len(data)),
                    level=2)
                return '', ''
        else:
            self.logger.log(
                sys._getframe().f_code.co_name, 'Failed to download subtitle from all links: %s' %
                                                (referer),
                level=2)
            return '', ''

    def close(self):
        self.session.close()
