# -*- encoding: utf-8 -*-
# https://dev.twitch.tv/docs/v5/guides/using-the-twitch-api/

from ...queries import V5Query as Qry
from ...queries import query


# required scope: any
@query
def root():
    return Qry('')
