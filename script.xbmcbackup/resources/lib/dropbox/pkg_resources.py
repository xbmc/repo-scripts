import resources.lib.utils as utils

def resource_filename(*args):
    return utils.addon_dir() + "/resources/lib/dropbox/trusted-certs.crt"
