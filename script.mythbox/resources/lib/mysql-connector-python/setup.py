#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

"""

To install MySQL Connector/Python:

    shell> python ./setup.py install

"""

from distutils.core import setup
import sys
import metasetupinfo

setup(
    name = metasetupinfo.name,
    version = metasetupinfo.version,
    description = metasetupinfo.description,
    long_description = metasetupinfo.long_description,
    author = metasetupinfo.author,
    author_email = metasetupinfo.author_email,
    license = metasetupinfo.license,
    keywords = metasetupinfo.keywords,
    url = metasetupinfo.url,
    download_url = metasetupinfo.download_url,
    package_dir = metasetupinfo.package_dir,
    packages = metasetupinfo.packages,
)
