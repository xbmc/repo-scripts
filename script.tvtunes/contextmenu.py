# -*- coding: utf-8 -*-

# Import the common settings
from resources.lib.settings import log
from resources.lib.scraper import TvTunesScraper


#########################
# Main
#########################
if __name__ == '__main__':
    log("TvTunes: Context menu called TvTunes Scraper")

    themeScraper = TvTunesScraper()
    del themeScraper
