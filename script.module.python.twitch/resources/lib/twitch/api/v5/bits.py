# -*- encoding: utf-8 -*-
# https://dev.twitch.tv/docs/v5/reference/bits/

from ... import keys
from ...queries import V5Query as Qry
from ...queries import query


# required scope: None
@query
def get_cheermotes(channel_id=None):
    q = Qry('bits/actions', use_token=False)
    q.add_param(keys.CHANNEL_ID, channel_id, None)
    return q
