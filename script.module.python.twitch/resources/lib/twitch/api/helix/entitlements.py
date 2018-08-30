# -*- encoding: utf-8 -*-
# https://dev.twitch.tv/docs/api/reference

from ..parameters import EntitlementType
from ... import keys
from ...queries import HelixQuery as Qry
from ...queries import query


# required scope: none
# requires app access token
@query
def upload(manifest_id, entitlement_type=EntitlementType.BULK_DROPS_GRANT):
    q = Qry('entitlements/upload', use_app_token=True)
    q.add_param(keys.MANIFEST_ID, manifest_id)
    q.add_param(keys.TYPE, EntitlementType.validate(entitlement_type))

    return q
