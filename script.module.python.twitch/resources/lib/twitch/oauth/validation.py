# -*- encoding: utf-8 -*-
"""

    Copyright (C) 2022 script.module.python.twitch

    This file is part of script.module.python.twitch

    SPDX-License-Identifier: GPL-3.0-only
    See LICENSES/GPL-3.0-only for more information.
"""

from ..queries import OAuthValidationQuery as Qry
from ..queries import query


@query
def validate(token=None):
    q = Qry(token)
    return q
