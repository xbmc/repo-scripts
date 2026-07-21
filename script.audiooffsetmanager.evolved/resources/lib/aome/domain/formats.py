"""Format facts shared across layers: the absence sentinel, spatial bases.

Formats are accepted verbatim (the reported string is the store-key
segment), so there is no vocabulary gating which formats are known. The one
fact table here, ``SPATIAL_BASE``, does not gate acceptance either: it maps
a spatial object-audio variant to the base codec whose bitstream carries it,
consulted only when the distinct-spatial toggle asks for the coarser key. An
unlisted segment passes through unchanged, so an unrecognized variant stays
its own working key. Display names live with the key codec in
``aome.store.keys``.

Pure Python: no Kodi imports.
"""

# Sentinel for any undetected axis, and the absence key segment:
# keys.audio_segment/hdr_segment normalize ''/'none'/'unknown' to this.
UNKNOWN = 'unknown'

# Spatial variant -> base codec, on normalized audio segments. Observed
# Kodi spellings only (StreamUtils::GetCodecName has exactly these variant
# cases), same never-speculative rule as the HDR aliases in
# ``aome.store.keys``. Lossy DTS:X over DTS-HD HRA exists in the wild but
# FFmpeg detects the X syncword only inside the lossless XLL substream, so
# Kodi reports such a stream as plain 'dtshd_hra' — already the base. Add
# its entry when a distinct spelling actually appears.
SPATIAL_BASE = {
    'truehd_atmos': 'truehd',
    'eac3_ddp_atmos': 'eac3',
    'dtshd_ma_x': 'dtshd_ma',
    'dtshd_ma_x_imax': 'dtshd_ma',
}


def spatial_base(segment):
    """The base codec a spatial variant collapses to; itself when not one."""
    return SPATIAL_BASE.get(segment, segment)
