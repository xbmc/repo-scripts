# -*- coding: utf-8 -*-
import xbmc

def main():
    if xbmc.getCondVisibility('String.IsEqual(ListItem.DBType,movie) + !String.IsEmpty(ListItem.DBID)'):
        xbmc.executebuiltin('RunScript(script.embuary.info,call=movie,dbid=%s)' % xbmc.getInfoLabel('ListItem.DBID'))

    elif xbmc.getCondVisibility('String.IsEqual(ListItem.DBType,movie)'):
        xbmc.executebuiltin('RunScript(script.embuary.info,call=movie,query=\'"%s"\',year=%s)' % (xbmc.getInfoLabel('ListItem.Title'),xbmc.getInfoLabel('ListItem.Year')))

    elif xbmc.getCondVisibility('String.IsEqual(ListItem.DBType,tvshow) + !String.IsEmpty(ListItem.DBID)'):
        xbmc.executebuiltin('RunScript(script.embuary.info,call=tv,dbid=%s)' % xbmc.getInfoLabel('ListItem.DBID'))

    elif xbmc.getCondVisibility('String.IsEqual(ListItem.DBType,tvshow)'):
        xbmc.executebuiltin('RunScript(script.embuary.info,call=tv,query=\'"%s"\',year=%s)' % (xbmc.getInfoLabel('ListItem.TVShowTitle'),xbmc.getInfoLabel('ListItem.Year')))

    elif xbmc.getCondVisibility('String.IsEqual(ListItem.DBType,episode) | String.IsEqual(ListItem.DBType,season)'):
        xbmc.executebuiltin('RunScript(script.embuary.info,call=tv,query=\'"%s"\')' % xbmc.getInfoLabel('ListItem.TVShowTitle'))

    elif xbmc.getCondVisibility('String.IsEqual(ListItem.DBType,actor)'):
        xbmc.executebuiltin('RunScript(script.embuary.info,call=person,query=\'"%s"\')' % xbmc.getInfoLabel('ListItem.Label'))

if __name__ == '__main__':
    main()
