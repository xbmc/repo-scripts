# -*- encoding: utf-8 -*-
"""
    Reference: https://dev.twitch.tv/docs/api/reference

    Copyright (C) 2016-2018 script.module.python.twitch

    This file is part of script.module.python.twitch

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

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
