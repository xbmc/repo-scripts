# -*- coding: utf-8 -*-
import xbmc
import base

class VideoInfoDialogReader(base.DefaultWindowReader):
    ID = 'videoinfodialog'
    def init(self):
        self.listMap = {    20376:xbmc.getInfoLabel('ListItem.OriginalTitle'),
                            20339:xbmc.getInfoLabel('ListItem.Director'),
                            20417:xbmc.getInfoLabel('ListItem.Writer'),
                            572:xbmc.getInfoLabel('ListItem.Studio'),
                            515:xbmc.getInfoLabel('ListItem.Genre'),
                            562:xbmc.getInfoLabel('ListItem.Year'),
                            2050:'{0} {1}'.format(xbmc.getInfoLabel('ListItem.Duration'),xbmc.getLocalizedString(12391)),
                            563:xbmc.getInfoLabel('ListItem.RatingAndVotes'), #Works the same as ListItem.Rating when no votes, at least as far as speech goes
                            202:xbmc.getInfoLabel('ListItem.TagLine'),
                            203:xbmc.getInfoLabel('ListItem.PlotOutline'),
                            20074:xbmc.getInfoLabel('ListItem.mpaa'),
                            15311:xbmc.getInfoLabel('ListItem.FilenameAndPath'),
                            20364:xbmc.getInfoLabel('ListItem.TVShowTitle'),
                            20373:xbmc.getInfoLabel('ListItem.Season'),
                            20359:xbmc.getInfoLabel('ListItem.Episode'),
                            31322:xbmc.getInfoLabel('ListItem.Premiered'),
                            20360:'{0} ({1} - {2})'.format(xbmc.getInfoLabel('ListItem.episode'),xbmc.getInfoLabel('$INFO[ListItem.Property(WatchedEpisodes),, $LOCALIZE[16102]]'),xbmc.getInfoLabel('$INFO[ListItem.Property(UnWatchedEpisodes), , $LOCALIZE[16101]]')),
                            557:xbmc.getInfoLabel('ListItem.Artist'),
                            558:xbmc.getInfoLabel('ListItem.Album'),
        }

    def getHeading(self):
        return xbmc.getInfoLabel('ListItem.Title').decode('utf-8') or u''

    def getControlText(self,controlID):
        if not controlID: return (u'',u'')
        text = u''
        if controlID == 49:
            text = xbmc.getInfoLabel('System.CurrentControl'.format(controlID)).strip(': ')
            for k in self.listMap.keys():
                if text == xbmc.getLocalizedString(k).strip(': '):
                    text = '{0}: {1}'.format(text,self.listMap[k])
                    break
        elif controlID == 50:
            text = '{0}: {1}'.format(xbmc.getInfoLabel('Container(50).ListItem.Label'), xbmc.getInfoLabel('Container(50).ListItem.Label2'))
        elif controlID == 61:
            text = '{0}: {1}'.format(xbmc.getLocalizedString(207),xbmc.getInfoLabel('ListItem.Plot'))
        elif controlID == 138:
            text = xbmc.getInfoLabel('ListItem.Plot').decode('utf-8')
        else:
            text = xbmc.getInfoLabel('Control.GetLabel({0})'.format(controlID))

        if not text: text = xbmc.getInfoLabel('System.CurrentControl')
        if not text: return (u'',u'')
        return (text.decode('utf-8'),text)

    def getControlPostfix(self, controlID):
        post = base.DefaultWindowReader.getControlPostfix(self, self.service.controlID)
        if self.service.controlID == 50:
            return 'Cast: {0}'.format(post)

