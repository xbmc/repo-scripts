# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Philipp Temminghoff
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
import sys


def main():
    info = sys.listitem.getVideoInfoTag()
    dbid = info.getDbId()
    db_type = info.getMediaType()
    if not dbid:
        dbid = sys.listitem.getProperty("dbid")
    if db_type == "movie":
        xbmc.executebuiltin("RunScript(script.extendedinfo,info=ratemedia,type=movie,dbid=%s,id=%s)" % (dbid, sys.listitem.getProperty("id")))
    elif db_type == "tvshow":
        xbmc.executebuiltin("RunScript(script.extendedinfo,info=ratemedia,type=tv,dbid=%s,id=%s)" % (dbid, sys.listitem.getProperty("id")))
    elif db_type == "episode":
        xbmc.executebuiltin("RunScript(script.extendedinfo,info=ratemedia,type=episode,tvshow=%s,season=%s,episode=%s)" % (info.getTVShowTitle(), info.getSeason(), info.getEpisode()))

if __name__ == '__main__':
    main()
