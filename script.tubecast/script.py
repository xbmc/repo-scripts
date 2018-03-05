# -*- coding: utf-8 -*-
from resources.lib.kodi.utils import get_string, yes_no
from resources.lib.tubecast.youtube.pairing import generate_pairing_code

if __name__ == "__main__":
    dg = yes_no(get_string(32008),
                yeslabel=get_string(32009), nolabel=get_string(32010))
    if dg:
        generate_pairing_code()
