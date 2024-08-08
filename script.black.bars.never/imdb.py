import requests
from bs4 import BeautifulSoup

import xbmc
import xbmcgui

def notify(msg):
    xbmcgui.Dialog().notification("BlackBarsNever", msg, None, 1000)

def getOriginalAspectRatio(title, imdb_number=None):
    BASE_URL = "https://www.imdb.com/"
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'}

    if imdb_number and str(imdb_number).startswith("tt"):
        URL = "{}/title/{}/".format(BASE_URL, imdb_number)
    else:
        URL = BASE_URL + "find/?q={}".format(title)
        search_page = requests.get(URL, headers=HEADERS)

        # lxml parser would have been better but not currently supported in Kodi
        soup = BeautifulSoup(search_page.text, 'html.parser')

        title_url_tag = soup.select_one(
            '.ipc-metadata-list-summary-item__t')
        if title_url_tag:
            # we have matches, pick the first one
            title_url = title_url_tag['href']
            imdb_number = title_url.rsplit(
                '/title/', 1)[-1].split("/")[0]
            # this below could have worked instead but for some reason SoupSieve not working inside Kodi
            """title_url = soup.css.select(
                '.ipc-metadata-list-summary-item__t')[0].get('href')
                """

            URL = BASE_URL + title_url

    title_page = requests.get(URL, headers=HEADERS)
    soup = BeautifulSoup(title_page.text, 'html.parser')

    # this below could have worked instead but for some reason SoupSieve not working inside Kodi
    aspect_ratio_tags = soup.find(
        attrs={"data-testid": "title-techspec_aspectratio"})
    
    if aspect_ratio_tags:
        aspect_ratio_full = aspect_ratio_tags.select_one(
            ".ipc-metadata-list-item__list-content-item").decode_contents()

        """aspect_ratio_full = soup.find(
            attrs={"data-testid": "title-techspec_aspectratio"}).css.select(".ipc-metadata-list-item__list-content-item")[0].decode_contents()
            """

        if aspect_ratio_full:
            aspect_ratio = aspect_ratio_full.split(':')[0].replace('.', '')
    else:
        # check if video has multiple aspect ratios
        URL = "{}/title/{}/technical/".format(BASE_URL, imdb_number)
        tech_specs_page = requests.get(URL, headers=HEADERS)
        soup = BeautifulSoup(tech_specs_page.text, 'html.parser')
        aspect_ratio_li = soup.select_one("#aspectratio").find_all("li")
        if len(aspect_ratio_li) > 1:
            aspect_ratios = []

            for li in aspect_ratio_li:
                aspect_ratio_full = li.select_one(
                    ".ipc-metadata-list-item__list-content-item").decode_contents()
                
                aspect_ratio = aspect_ratio_full.split(':')[0].replace('.', '')
                sub_text = li.select_one(".ipc-metadata-list-item__list-content-item--subText").decode_contents()
                
                if sub_text == "(theatrical ratio)":
                    xbmc.log("using theatrical ratio " + str(aspect_ratio), level=xbmc.LOGINFO)
                    return aspect_ratio
                
                
                aspect_ratios.append(aspect_ratio)

            return aspect_ratios

    return aspect_ratio