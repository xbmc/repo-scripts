"""Texture cache statistics calculation and formatting."""
from __future__ import annotations

import os
import xbmc
import xbmcgui
import xbmcvfs
from datetime import datetime
from typing import Optional, Dict, Any

from lib.kodi.client import log, ADDON
from lib.texture.utilities import is_library_artwork_url

# Age and usage bucket boundaries (inclusive upper bound per bucket).
_AGE_BUCKET_BOUNDS = (7, 30, 90, 180)
_AGE_BUCKET_LABELS = ('0-7', '8-30', '31-90', '91-180', '180+', 'unknown')
_USAGE_BUCKET_BOUNDS = (5, 20, 50)
_USAGE_BUCKET_LABELS = ('0', '1-5', '6-20', '21-50', '50+')

# Kodi's `Textures.GetTextures` returns width/usecount swapped for some entries (PR #27584).
# A `usecount >= 256` paired with `width < 256` is the swap signature, fall back to width.
_USECOUNT_SWAP_THRESHOLD = 256


def _real_usecount(size_record: Dict[str, Any]) -> int:
    """Return the true usecount for a size record, accounting for the Kodi width/usecount swap."""
    raw_usecount = size_record.get('usecount', 0)
    raw_width = size_record.get('width', 0)
    if raw_width < _USECOUNT_SWAP_THRESHOLD and raw_usecount >= _USECOUNT_SWAP_THRESHOLD:
        return raw_width
    return raw_usecount


def _bucket_age(days_ago: int) -> str:
    """Return the age-bucket label for `days_ago`."""
    for bound, label in zip(_AGE_BUCKET_BOUNDS, _AGE_BUCKET_LABELS):
        if days_ago <= bound:
            return label
    return _AGE_BUCKET_LABELS[-2]  # '180+'


def _bucket_usage(usecount: int) -> str:
    """Return the usage-bucket label for `usecount`."""
    if usecount == 0:
        return _USAGE_BUCKET_LABELS[0]
    for bound, label in zip(_USAGE_BUCKET_BOUNDS, _USAGE_BUCKET_LABELS[1:]):
        if usecount <= bound:
            return label
    return _USAGE_BUCKET_LABELS[-1]  # '50+'


def _classify_texture_type(url: str) -> str:
    """Classify a texture URL into one of `library`, `video_thumb`, `music`, `other`."""
    if is_library_artwork_url(url):
        return 'library'
    if 'video@' in url:
        return 'video_thumb'
    if 'music@' in url or 'musicdb://' in url:
        return 'music'
    return 'other'


def _bucket_size_record(size: dict, now: datetime, age_buckets: Dict[str, int],
                       usage_buckets: Dict[str, int]) -> None:
    """Update `age_buckets` and `usage_buckets` in place from a single size record."""
    lastusetime = size.get('lastused')
    usecount = _real_usecount(size)

    if lastusetime:
        try:
            last_used = datetime.strptime(lastusetime, '%Y-%m-%d %H:%M:%S')
            age_buckets[_bucket_age((now - last_used).days)] += 1
        except Exception:
            age_buckets['unknown'] += 1
    else:
        age_buckets['unknown'] += 1

    usage_buckets[_bucket_usage(usecount)] += 1


def _calculate_disk_usage(thumbnails_path: str) -> int:
    """Sum the on-disk size of every file under `thumbnails_path`. Returns 0 on walk error."""
    disk_usage = 0
    try:
        for root, _dirs, files in os.walk(thumbnails_path):
            for filename in files:
                filepath = os.path.join(root, filename)
                try:
                    disk_usage += os.path.getsize(filepath)
                except Exception:
                    pass
    except Exception as e:
        log("Texture", f"SkinInfo TextureCache: Disk usage calculation failed: {str(e)}",
            xbmc.LOGWARNING)
    return disk_usage


def calculate_texture_statistics(textures: list[Dict[str, Any]],
                                 progress: xbmcgui.DialogProgress) -> Optional[Dict[str, Any]]:
    """Compute texture-cache stats: counts, age/usage buckets, type breakdown, disk usage."""
    if not textures:
        return None

    try:
        total_textures = len(textures)
        total_sizes = 0
        age_buckets = {label: 0 for label in _AGE_BUCKET_LABELS}
        usage_buckets = {label: 0 for label in _USAGE_BUCKET_LABELS}
        type_breakdown = {'library': 0, 'video_thumb': 0, 'music': 0, 'other': 0}
        now = datetime.now()

        progress.update(30, ADDON.getLocalizedString(32332).format(total_textures))

        for i, texture in enumerate(textures):
            if progress.iscanceled():
                return None
            if i % 100 == 0:
                progress.update(30 + int((i / total_textures) * 50))

            sizes = texture.get('sizes', [])
            total_sizes += len(sizes)
            type_breakdown[_classify_texture_type(texture.get('url', ''))] += 1
            for size in sizes:
                _bucket_size_record(size, now, age_buckets, usage_buckets)

        progress.update(80, ADDON.getLocalizedString(32425))
        disk_usage = _calculate_disk_usage(xbmcvfs.translatePath("special://thumbnails"))
        progress.update(100, ADDON.getLocalizedString(32426))

        return {
            'total_textures': total_textures,
            'total_sizes': total_sizes,
            'disk_usage': disk_usage,
            'age_buckets': age_buckets,
            'usage_buckets': usage_buckets,
            'type_breakdown': type_breakdown,
        }

    except Exception as e:
        log("Texture", f"Statistics calculation failed: {str(e)}", xbmc.LOGERROR)
        return None


def format_statistics_report(stats: Dict[str, Any]) -> str:
    """Render the stats dict from `calculate_texture_statistics` as a textviewer-friendly report."""
    total_textures = stats['total_textures']
    total_sizes = stats['total_sizes']
    disk_usage = stats['disk_usage']
    age_buckets = stats['age_buckets']
    usage_buckets = stats['usage_buckets']
    type_breakdown = stats['type_breakdown']

    disk_gb = disk_usage / (1024 ** 3)
    disk_mb = disk_usage / (1024 ** 2)

    lines = [
        "=" * 50,
        "TEXTURE CACHE STATISTICS",
        "=" * 50,
        "",
        "OVERVIEW",
        "-" * 50,
        f"Total Textures:      {total_textures:,}",
        f"Total Cached Sizes:  {total_sizes:,}",
    ]

    if disk_usage > 0:
        if disk_gb >= 0.1:
            lines.append(f"Disk Usage:          {disk_gb:.2f} GB ({disk_usage:,} bytes)")
        else:
            lines.append(f"Disk Usage:          {disk_mb:.2f} MB ({disk_usage:,} bytes)")
    else:
        lines.append("Disk Usage:          Unable to calculate")

    lines.extend([
        "",
        "AGE DISTRIBUTION (by cached size)",
        "-" * 50
    ])

    age_labels = {
        '0-7': 'Last 7 days',
        '8-30': '8-30 days',
        '31-90': '31-90 days',
        '91-180': '91-180 days',
        '180+': 'Over 180 days',
        'unknown': 'Unknown'
    }

    for key in ['0-7', '8-30', '31-90', '91-180', '180+', 'unknown']:
        count = age_buckets.get(key, 0)
        pct = (count / total_sizes * 100) if total_sizes > 0 else 0
        lines.append(f"{age_labels[key]:18s}  {count:6,} sizes ({pct:5.1f}%)")

    lines.extend([
        "",
        "USAGE DISTRIBUTION (by cached size)",
        "-" * 50
    ])

    usage_labels = {
        '0': 'Never used',
        '1-5': '1-5 times',
        '6-20': '6-20 times',
        '21-50': '21-50 times',
        '50+': 'Over 50 times'
    }

    for key in ['0', '1-5', '6-20', '21-50', '50+']:
        count = usage_buckets.get(key, 0)
        pct = (count / total_sizes * 100) if total_sizes > 0 else 0
        lines.append(f"{usage_labels[key]:18s}  {count:6,} sizes ({pct:5.1f}%)")

    lines.extend([
        "",
        "MEDIA TYPE BREAKDOWN (by texture)",
        "-" * 50
    ])

    type_labels = {
        'library': 'Library Artwork',
        'video_thumb': 'Video Thumbnails',
        'music': 'Music Artwork',
        'other': 'Other/System'
    }

    for key in ['library', 'video_thumb', 'music', 'other']:
        count = type_breakdown.get(key, 0)
        pct = (count / total_textures * 100) if total_textures > 0 else 0
        lines.append(f"{type_labels[key]:18s}  {count:6,} textures ({pct:5.1f}%)")

    lines.extend([
        "",
        "=" * 50
    ])

    return "\n".join(lines)
