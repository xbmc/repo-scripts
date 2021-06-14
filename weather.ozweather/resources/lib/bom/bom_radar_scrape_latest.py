# N.B. THIS IS (NOT YET?) DIRECTLY RUN BY XBMC - IS JUST AN AID FOR DEVELOPMENT

import re
import requests
from pprint import pprint
from bs4 import BeautifulSoup

# The master page for the BOM radars
radar_page = "http://www.bom.gov.au/australia/radar/about/radar_site_info.shtml"
# Needed to bypass the BOM's stupid web scraping filter
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0'}

r = requests.get(radar_page, headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')

content = soup.find(id="content")
anchors = content.find_all("a")

print(f"# Automatically generated from {radar_page}")
print("BOM_RADAR_LOCATIONS = [")

# The last anchor is not needed, but loop through the rest to scrape the actual radars...
for anchor in anchors[:-1]:
    href = anchor.get('href')

    radar_page = "http://www.bom.gov.au" + href
    print("# " + radar_page)

    r = requests.get(radar_page, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')

    site_infos = soup.find_all('div', class_='site-info')
    for site_info in site_infos:

        # Get the radar name
        name = site_info.find("h2").text
        name = name.strip()

        # Get the radar code like IDR023
        link_item = site_info.find('li', class_='link')
        anchor = link_item.find('a')
        radar_code_matches = re.search(r'IDR\d+', anchor.get('href'))
        radar_code = radar_code_matches.group(0) or None

        # Get the latitude and longitude
        lat_lon_li = site_info.find('li')
        text = lat_lon_li.text
        text = text.replace("\n", "")
        lat_lon_matches = re.findall(r'([+-]?[0-9]+\.[0-9]+)', lat_lon_li.text)
        # bizarrely Mildura is the only one that has the '-' in the latitude, the rest all say 'south'
        if lat_lon_matches[0][0] == '-':
            lat_lon_matches[0] = lat_lon_matches[0][1:]
        print(f'(-{lat_lon_matches[0]}, {lat_lon_matches[1]}, "{name}", "{radar_code}"),')

print("]")
