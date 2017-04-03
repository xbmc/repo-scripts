# -*- coding: utf-8 -*-
#
# Copyright (C) 2017 zosky
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import xbmc
import xbmcgui
import xbmcaddon
import json


def main():
    # GET ITEM DATA
    assetID = int(xbmc.getInfoLabel('ListItem.DBID'))
    assetTYPE = xbmc.getInfoLabel('ListItem.DBtype')

    # GET ITEM TAGS
    GETassetTAGS = {'jsonrpc': '2.0', 'id': 'tagSelector',
                    'method': 'VideoLibrary.Get' + assetTYPE + 'Details',
                    'params': {assetTYPE + 'id': assetID,
                               'properties': ['tag']}}

    assetTAGS = json.loads(xbmc.executeJSONRPC(json.dumps(GETassetTAGS)))
    assetTAGS = assetTAGS['result'][assetTYPE + 'details']['tag']

    # GET ALL TAGS (FOR assetTYPE)
    GETallTAGS = {'jsonrpc': '2.0', 'id': 'tagSelector',
                  'method': 'VideoLibrary.GetTags',
                  'params': {'type': assetTYPE}}

    allTAGS = json.loads(xbmc.executeJSONRPC(json.dumps(GETallTAGS)))
    allTAGS = allTAGS['result']['tags']

    # MASSAGE TAG LIST INTO MULTI-SELECT FORMAT
    tags = []
    for item in allTAGS:
        tags.append(item['label'])

    # IDENTIFY PRESELECTED TAGS
    preSelectedTAGS = []
    for item in assetTAGS:
        preSelectedTAGS.append(tags.index(item))

    # MAKE DIALOG
    dialog = xbmcgui.Dialog()
    title = xbmcaddon.Addon().getLocalizedString(32001)
    returned = dialog.multiselect(title, tags, preselect=preSelectedTAGS)
    # IF NOT CANCELED
    if returned is not None:
        selected = []
        for n in returned:
            selected.append(tags[n])

        # SUBMIT
        SETnewTAGS = {'jsonrpc': '2.0', 'id': 'tagSelector',
                      'method': 'VideoLibrary.Set' + assetTYPE + 'Details',
                      'params': {assetTYPE + 'id': assetID,
                                 'tag': selected}}

        xbmc.executeJSONRPC(json.dumps(SETnewTAGS))


if __name__ == '__main__':
    main()
