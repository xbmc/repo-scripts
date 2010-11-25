import sys

if sys.version_info >= (3,1):
    from py3k.mysql.connector._version import version as myconnpy_version
    package_dir = { '' : 'py3k'}
else:
    from mysql.connector._version import version as myconnpy_version
    package_dir = None
    
name = 'mysql-connector-python'
version = '%s-%s' % ('.'.join(map(str,myconnpy_version[0:3])),myconnpy_version[3])
packages = ['mysql','mysql.connector']
description = "MySQL driver written in Python"
long_description = """\
MySQL driver written in Python which does not depend on MySQL C client
libraries and implements the DB API v2.0 specification (PEP-249).
"""
author = 'Sun Microsystems, Inc.'
author_email = 'geert.vanderkelen@sun.com'
maintainer = 'Geert Vanderkelen'
maintainer_email = 'geert.vanderkelen@sun.com'
license = "GNU GPLv2 (with FOSS License Exception)"
keywords = "mysql db",
url = 'http://launchpad.net/myconnpy'
download_url = 'http://launchpad.net/myconnpy'
