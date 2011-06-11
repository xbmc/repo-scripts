# MySQL Connector/Python - MySQL driver written in Python.
# Copyright (c) 2009,2010, Oracle and/or its affiliates. All rights reserved.
# Use is subject to license terms. (See COPYING)

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation.
# 
# There are special exceptions to the terms and conditions of the GNU
# General Public License as it is applied to this software. View the
# full text of the exception in file EXCEPTIONS-CLIENT in the directory
# of this software distribution or see the FOSS License Exception at
# www.mysql.com.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

import sys

if sys.version_info >= (3,1):
    from python3.mysql.connector._version import version as myconnpy_version
    package_dir = { '' : 'python3' }
elif sys.version_info >= (2,4) and sys.version_info < (3,0):
    from python2.mysql.connector._version import version as myconnpy_version
    package_dir = { '' : 'python2' }
else:
    raise RuntimeError("Python v%d.%d is not supported" %\
        sys.version_info[0:2])
    
name = 'mysql-connector-python'
version = '%s-%s' % ('.'.join(map(str,myconnpy_version[0:3])),
    myconnpy_version[3])
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
