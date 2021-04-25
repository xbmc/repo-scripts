# encoding: utf-8
#
#  --------------------------------------------
#  based on https://github.com/yuppity/ttml2srt
#  --------------------------------------------
# SPDX-License-Identifier: LGPL-2.1-or-later

from __future__ import unicode_literals, absolute_import, division
import re

class TimestampConverter(object):

    def __init__(self, frame_rate=23.976, tick_rate=1):
        self.tick_rate = tick_rate
        self.frame_rate = frame_rate

    def timeexpr_to_ms(self, *args):
        return self._timeexpr_to_ms(*args)

    def _timeexpr_to_ms(self, time_expr):
        """Use the given time expression to get a matching conversion method
        to overwrite self.timeexpr_to_ms() with.
        """

        self.timeexpr_to_ms = self.determine_ms_convfn(time_expr)
        return self.timeexpr_to_ms(time_expr)

    def _hhmmss_to_ms(self, hh, mm, ss):
        return hh * 3600 * 1000 + mm * 60 * 1000 + ss * 1000

    def subrip_to_ms(self, timestamp):
        """Desconstruct SubRip timecode down to milliseconds
        """

        hh, mm, ss, ms = re.split(r'[:,]', timestamp)
        return int(int(hh) * 3.6e6 + int(mm) * 60000 + int(ss) * 1000 + int(ms))

    def _metric_to_ms(self, metric_multiplier, metric_value):
        return int(metric_multiplier * metric_value)

    def _ms_to_hhmmssms(self, ms):
        hh = int(ms / 3.6e6)
        mm = int((ms % 3.6e6) / 60000)
        ss = int((ms % 60000) / 1000)
        ms = int(ms % 1000)

        return hh, mm, ss, ms

    def ms_to_subrip(self, ms):
        """Build SubRip timecode from milliseconds
        """

        hh, mm, ss, ms = self._ms_to_hhmmssms(ms)
        return '{:02d}:{:02d}:{:02d},{:03d}'.format(hh, mm, ss, ms)

    def ms_to_ssa(self, ms):
        """Build SSA/ASS timecode from milliseconds
        """

        hh, mm, ss, ms = self._ms_to_hhmmssms(ms)
        return '{:01d}:{:02d}:{:02d}.{:02d}'.format(hh, mm, ss, int(ms / 10))

    def frames_to_ms(self, frames):
        """Convert frame count to ms
        """

        return int(int(frames) * (1000 / self.frame_rate))

    def offset_frames_to_ms(self, time):
        """Convert offset-time expression with f metric to milliseconds.
        """

        frames = float(time[:-1])
        return int(int(frames) * (1000 / self.frame_rate))

    def offset_ticks_to_ms(self, time):
        """Convert offset-time expression with t metric to milliseconds.
        """

        ticks = int(time[:-1])
        seconds = 1.0 / self.tick_rate
        return (seconds * ticks) * 1000

    def offset_hours_to_ms(self, time):
        """Convert offset-time expression with h metric to milliseconds.
        """

        hours = float(time[:-1])
        return self._metric_to_ms(3.6e6, hours)

    def offset_minutes_to_ms(self, time):
        """Convert offset-time expression with m metric to milliseconds.
        """

        return self._metric_to_ms(60 * 1000, float(time[:-1]))

    def offset_seconds_to_ms(self, time):
        """Convert offset-time expression with s metric to milliseconds.
        """

        seconds = float(time[:-1])
        return self._metric_to_ms(1000, seconds)

    def offset_ms_to_ms(self, time):
        """Convert offset-time expression with ms metric to milliseconds.
        """

        ms = int(time[:-2])
        return ms

    def fraction_timestamp_to_ms(self, timestamp):
        """Convert hh:mm:ss.fraction to milliseconds
        """

        hh, mm, ss, fraction = re.split(r'[:.]', timestamp)
        hh, mm, ss = [int(i) for i in (hh, mm, ss)]
        # Resolution beyond ms is useless for our purposes
        ms = int(fraction[:3])

        return self._hhmmss_to_ms(hh, mm, ss) + ms

    def frame_timestamp_to_ms(self, timestamp):
        """Convert hh:mm:ss:frames to milliseconds

        Will handle hh:mm:ss:frames.sub-frames by discarding the sub-frame part
        """

        hh, mm, ss, frames = [int(i) for i in timestamp.split('.')[0].split(':')]
        hhmmss_ms = self._hhmmss_to_ms(hh, mm, ss)
        ms = self.frames_to_ms(frames)
        return hhmmss_ms + ms

    def determine_ms_convfn(self, time_expr):
        """Determine approriate ms conversion fn to pass the time expression to.

        Args:
            time_exrp (str): TTML time expression

        Return:
            Conversion method (callable)

        Strips the time expression of digits and uses the resulting string as
        a key to a dict of conversion methods.
        """

        # Map time expression delimiters to conversion methods. Saves
        # us from having to exec multibranch code on each line but assumes all
        # time expressions to be of the same form.
        time_expr_fns = {

            # clock-time, no frames or fraction
            # Example(s): "00:02:23"
            '::': self.frame_timestamp_to_ms,

            # clock-time, frames
            # Example(s): "00:02:23:12", "00:02:23:12.222"
            ':::': self.frame_timestamp_to_ms,
            ':::.': self.frame_timestamp_to_ms,

            # clock-time, fraction
            # Example(s): "00:02:23.283"
            '::.': self.fraction_timestamp_to_ms,

            # offset-time, hour metric
            # Example(s): "1h", "1.232837372637h"
            'h': self.offset_hours_to_ms,
            '.h': self.offset_hours_to_ms,

            # offset-time, minute metric
            # Example(s): "1m", "13.72986323m"
            'm': self.offset_minutes_to_ms,
            '.m': self.offset_minutes_to_ms,

            # offset-time, second metric
            # Example(s): "1s", "113.2312312s"
            's': self.offset_seconds_to_ms,
            '.s': self.offset_seconds_to_ms,

            # offset-time, millisecond metric
            # Example(s): "1ms", "1000.1231231231223ms"
            'ms': self.offset_ms_to_ms,
            '.ms': self.offset_ms_to_ms,

            # offset-time, frame metric
            # Example(s): "100f"
            'f': self.offset_frames_to_ms,
            '.f': self.offset_frames_to_ms,

            # offset-time, tick metric
            # Example(s): "19298323t"
            't': self.offset_ticks_to_ms,
            '.t': self.offset_ticks_to_ms,

        }

        try:
            delims = ''.join([i for i in time_expr if not i.isdigit()])
            return time_expr_fns[delims]
        except KeyError:
            raise NotImplementedError(
                'Unknown timestamp format ("{}")'.format(time_expr))
