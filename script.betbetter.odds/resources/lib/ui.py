# -*- coding: utf-8 -*-
"""Kodi dialogs for the Odds Converter."""
import xbmcaddon
import xbmcgui

from resources.lib import odds

ADDON = xbmcaddon.Addon()


def tr(string_id):
    return ADDON.getLocalizedString(string_id)


def convert_one():
    text = xbmcgui.Dialog().input(tr(32010))
    if not text:
        return
    try:
        decimal = odds.parse(text)
    except ValueError:
        xbmcgui.Dialog().ok(tr(32000), tr(32020))
        return
    xbmcgui.Dialog().textviewer(tr(32001), odds.describe(decimal))


def market_margin():
    text = xbmcgui.Dialog().input(tr(32011))
    if not text:
        return
    try:
        prices = [odds.parse(part) for part in text.replace(',', ' ').split()]
        if len(prices) < 2:
            raise ValueError
    except ValueError:
        xbmcgui.Dialog().ok(tr(32000), tr(32021))
        return
    xbmcgui.Dialog().textviewer(tr(32002), odds.describe_market(prices))


def main():
    while True:
        choice = xbmcgui.Dialog().select(tr(32000), [tr(32001), tr(32002)])
        if choice == 0:
            convert_one()
        elif choice == 1:
            market_margin()
        else:
            break


