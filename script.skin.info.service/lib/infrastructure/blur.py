"""Blurred background copies and main colors of artwork images."""

import colorsys
import hashlib
import os
from typing import Final, Optional

import xbmc
import xbmcvfs

from lib.kodi.client import log, decode_image_url, encode_image_url


PIL_AVAILABLE = None

_COLOR_LIGHTNESS: Final = 0.75
_COLOR_SATURATION: Final = 0.75


def _check_pil():
    """Whether PIL can be imported, probed once and remembered."""
    global PIL_AVAILABLE

    if PIL_AVAILABLE is not None:
        return PIL_AVAILABLE

    try:
        from PIL import Image, ImageFilter  # noqa: F401
        PIL_AVAILABLE = True
        return True
    except ImportError:
        PIL_AVAILABLE = False
        log("Blur", "PIL (Pillow) not available - blur and image color will not work",
            xbmc.LOGWARNING)
        return False


def _get_resize_filter():
    """Get the nearest-neighbor resize filter under both old and new Pillow."""
    try:
        from PIL.Image import Resampling
        return Resampling.NEAREST
    except (ImportError, AttributeError):
        from PIL import Image
        return Image.NEAREST  # type: ignore[attr-defined]


def _get_cache_dir():
    """Get the blur cache directory, created on first use; None if it can't be made."""
    cache_dir = os.path.join(
        xbmcvfs.translatePath("special://profile/addon_data/script.skin.info.service"),
        "blur_cache"
    )

    if not xbmcvfs.exists(cache_dir):
        success = xbmcvfs.mkdirs(cache_dir)
        if not success:
            log("Blur", f"Failed to create blur cache directory: {cache_dir}", xbmc.LOGERROR)
            return None

    return cache_dir


def _url_to_cached_path(url: str) -> Optional[str]:
    """Map an image URL to its Kodi texture-cache file, `.jpg` before `.png`; None if not cached."""
    if not url:
        return None

    url = decode_image_url(url)

    cache_name = xbmc.getCacheThumbName(url)
    hex_name = cache_name[:-4] if cache_name.endswith('.tbn') else cache_name

    for ext in ['.jpg', '.png']:
        cache_path = xbmcvfs.translatePath(f"special://profile/Thumbnails/{hex_name[0]}/{hex_name}{ext}")
        if xbmcvfs.exists(cache_path):
            return cache_path

    return None


def _generate_cache_key(source_path: str, blur_radius: int) -> str:
    """Generate the cache filename for a source and radius pair."""
    cache_key = f"{source_path}_{blur_radius}"
    hash_value = hashlib.md5(cache_key.encode("utf-8")).hexdigest()
    return f"{hash_value}.jpg"


def _is_full_path(path: str) -> bool:
    """Kodi's `CURL::IsFullPath`: rooted, a scheme, a drive letter, or a UNC share."""
    return (path.startswith('/')
            or '://' in path
            or (len(path) > 1 and path[1] == ':')
            or path.startswith('\\\\'))


def _is_skin_texture(source_path: str) -> bool:
    """True for a skin-relative texture, which the skin draws itself and never wants blurred."""
    return bool(source_path) and not _is_full_path(source_path)


def _resolve_source_for_mtime(source_path: str) -> Optional[str]:
    """Map a source URL/path to its local filesystem path for mtime checks. None if unmappable."""
    if source_path.startswith(('http://', 'https://', 'image://')):
        return _url_to_cached_path(source_path)
    try:
        return xbmcvfs.translatePath(source_path)
    except Exception:
        return None


def _cache_is_fresh(source_path: str, cache_path: str) -> bool:
    """True if the blurred copy is at least as new as its source, or the times can't be compared."""
    try:
        cache_mtime = os.path.getmtime(cache_path)
    except OSError:
        return False

    local = _resolve_source_for_mtime(source_path)
    if not local:
        return True

    try:
        return cache_mtime >= os.path.getmtime(local)
    except OSError:
        return True


def _skin_radius() -> int:
    """Radius the skin sets in `SkinInfo.BlurRadius`, 40 when unset or invalid."""
    try:
        radius = int(xbmc.getInfoLabel("Skin.String(SkinInfo.BlurRadius)") or 40)
    except ValueError:
        return 40
    return radius if radius >= 1 else 40


def _unreadable(source_path: str) -> bool:
    """True for an image Kodi holds where neither its texture cache nor VFS can read it."""
    # resource add-ons ship images packed in Textures.xbt, which neither the cache nor VFS reads
    if source_path.startswith('resource://'):
        return True
    # Kodi's virtual icons, such as DefaultShortcut.png
    basename = source_path.rsplit('/', 1)[-1].rsplit('\\', 1)[-1]
    return basename.startswith('Default') and basename.endswith('.png')


def _read_image(source_path: str) -> Optional[bytearray]:
    """Read an image's bytes, Kodi's texture-cache copy first; None if it can't be read."""
    if source_path.startswith('image://') and '@' in source_path:
        log("Blur", f"Not fetchable, Kodi-internal art: {source_path}", xbmc.LOGDEBUG)
        return None
    if _is_skin_texture(source_path):
        log("Blur", f"Skin texture, nothing to read: {source_path}", xbmc.LOGDEBUG)
        return None

    if source_path.startswith(('http://', 'https://', 'image://')):
        local_path = _url_to_cached_path(source_path)
        if not local_path:
            try:
                with xbmcvfs.File(encode_image_url(source_path), 'rb') as f:
                    img_bytes = f.readBytes()
            except Exception as e:
                log("Blur", f"Failed to download artwork: {source_path}: {e}", xbmc.LOGWARNING)
                return None
            if not img_bytes:
                log("Blur", f"Failed to download artwork: {source_path}", xbmc.LOGWARNING)
                return None
            return img_bytes
        path = local_path
    else:
        path = xbmcvfs.translatePath(source_path)

    if not xbmcvfs.exists(path):
        log("Blur", f"Source image does not exist: {path}", xbmc.LOGWARNING)
        return None
    try:
        with xbmcvfs.File(path, 'rb') as f:
            return f.readBytes()
    except Exception as e:
        log("Blur", f"Failed to read image {path}: {e}", xbmc.LOGWARNING)
        return None


def blur_image(source_path: str, blur_radius: Optional[int] = None) -> Optional[str]:
    """Return a cached blurred copy of an image, at the skin's radius unless given 1+."""
    if not source_path or _unreadable(source_path):
        return None
    if blur_radius is None or blur_radius < 1:
        blur_radius = _skin_radius()

    cache_dir = _get_cache_dir()
    if not cache_dir:
        return None
    cache_path = os.path.join(cache_dir, _generate_cache_key(source_path, blur_radius))
    if xbmcvfs.exists(cache_path) and _cache_is_fresh(source_path, cache_path):
        return cache_path

    if not _check_pil():
        return None
    img_data = _read_image(source_path)
    if not img_data:
        return None

    try:
        from PIL import Image, ImageFilter
        import io

        with Image.open(io.BytesIO(img_data)) as img:
            if img.format == 'JPEG':
                img.draft('RGB', (480, 480))

            # JPEG has no transparency
            if img.mode in ("RGBA", "LA", "PA", "P"):
                img = img.convert("RGB")

            img = img.resize((480, 480), _get_resize_filter())

            img = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))

            img.save(
                xbmcvfs.translatePath(cache_path),
                "JPEG", quality=70, optimize=False, subsampling=2,
            )

        return cache_path

    except Exception as e:
        log("Blur", f"Failed to blur image {source_path}: {e}", xbmc.LOGERROR)
        return None


def main_color(source_path: str) -> str:
    """Main color as FFRRGGBB, average's hue at set lightness and saturation; empty on failure."""
    if not source_path or _unreadable(source_path) or not _check_pil():
        return ''
    img_data = _read_image(source_path)
    if not img_data:
        return ''

    try:
        from PIL import Image, ImageStat
        import io

        with Image.open(io.BytesIO(img_data)) as img:
            if img.format == 'JPEG':
                img.draft('RGB', (128, 128))
            img = img.convert('RGB')
            img.thumbnail((128, 128))
            red, green, blue = ImageStat.Stat(img).mean[:3]
    except Exception as e:
        log("Blur", f"Failed to read the color of {source_path}: {e}", xbmc.LOGWARNING)
        return ''

    hue = colorsys.rgb_to_hls(red / 255, green / 255, blue / 255)[0]
    rgb = colorsys.hls_to_rgb(hue, _COLOR_LIGHTNESS, _COLOR_SATURATION)
    return 'FF' + ''.join(f'{round(channel * 255):02X}' for channel in rgb)
