import requests
import threading


_local = threading.local()


def _session():
    if hasattr(_local, 'session'):
        return _local.session
    _local.session = requests.Session()
    return _local.session


def _get_proxy_cfg(kw):
    proxy = kw.pop('proxy', None)
    proxy_user = kw.pop('proxy_user', None)
    proxy_password = kw.pop('proxy_password', None)
    if proxy and proxy_user and proxy_password:
        return {
            'http': 'http://{}:{}@{}'.format(proxy_user, proxy_password, proxy),
            'https': 'http://{}:{}@{}'.format(proxy_user, proxy_password, proxy),
        }
    elif proxy:
        return {
            'http': 'http://{}'.format(proxy),
            'https': 'http://{}'.format(proxy),
        }


def configure_pool(**kw):
    keys = ['pool_connections', 'pool_maxsize', 'max_retries']
    args = {k: kw[k] for k in keys if kw.get(k, None) is not None}
    if len(args) == 0:
        return
    https_adapter = requests.adapters.HTTPAdapter(**args)
    http_adapter = requests.adapters.HTTPAdapter(**args)
    _session().mount('https://', https_adapter)
    _session().mount('http://', http_adapter)


def post(*args, **kw):
    proxies = _get_proxy_cfg(kw)
    return _session().post(*args, proxies=proxies, **kw)


def get(*args, **kw):
    proxies = _get_proxy_cfg(kw)
    return _session().get(*args, proxies=proxies, **kw)


__all__ = ['post', 'get', 'configure_pool']
