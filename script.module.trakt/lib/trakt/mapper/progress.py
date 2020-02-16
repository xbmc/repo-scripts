from __future__ import absolute_import, division, print_function

from trakt.mapper.core.base import Mapper


class ProgressMapper(Mapper):
    @classmethod
    def progress(cls, client, progress_type, item, **kwargs):
        if not item:
            return None

        if 'progress' in item:
            i_progress = item['progress']
        else:
            i_progress = item

        # Create object
        progress = cls.construct(client, '%s_progress' % progress_type, i_progress, **kwargs)

        # Update with root info
        if 'progress' in item:
            progress._update(item)

        return progress
