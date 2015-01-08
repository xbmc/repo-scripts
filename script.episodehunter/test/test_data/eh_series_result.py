# SERIES = {
#     "71663": {
#         "seasons": [
#             {
#                 "season": "22",
#                 "episodes": [
#                     1,
#                     2
#                 ]
#             }
#         ]
#     },
#     "72227": {
#         "seasons": [
#             {
#                 "season": "9",
#                 "episodes": [
#                     1,
#                     2
#                 ]
#             },
#             {
#                 "season": "10",
#                 "episodes": [
#                     4
#                 ]
#             }
#         ]
#     }
# }


class EHSeries(object):

    def __init__(self):
        """Constructor for EHSeries"""
        super(EHSeries, self).__init__()
        self.__series = {}

    def episode(self, series, season, episodes):
        series = str(series)
        season_and_episode = {'season': season, 'episodes': episodes}
        if series in self.__series:
            self.__series[series]['seasons'].append(season_and_episode)
        else:
            self.__series[series] = {'seasons': [season_and_episode]}
        return self

    def get(self):
        return self.__series
