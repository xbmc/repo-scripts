# https://github.com/soundcloud/soundcloud-python
"""Python Soundcloud API Wrapper."""

__version__ = '0.4.2'
__all__ = ['Client']

USER_AGENT = 'SoundCloud Python API Wrapper %s' % __version__

from soundcloud.client import Client
