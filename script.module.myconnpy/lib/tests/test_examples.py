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

"""Unittests for examples
"""

import sys

import mysql.connector as myconn

import tests

class TestExamples(tests.MySQLConnectorTests):
    
    def _exec_main(self, exp):
        try:
            exp.main(self.getMySQLConfig())
        except StandardError, e:
            self.fail(e)
    
    def test_dates(self):
        """examples/dates.py"""
        try:
            import examples.dates as exp
        except StandardError, e:
            self.fail(e)
        self._exec_main(exp)
        
    def test_engines(self):
        """examples/engines.py"""
        try:
            import examples.engines as exp
        except:
            self.fail()
        self._exec_main(exp)
        
    def test_inserts(self):
        """examples/inserts.py"""
        try:
            import examples.inserts as exp
        except StandardError, e:
            self.fail(e)
        self._exec_main(exp)
    
    def test_transactions(self):
        """examples/transactions.py"""
        
        db = myconn.connect(**self.getMySQLConfig())
        r = self.haveEngine(db,'InnoDB')
        db.close()
        if not r:
            return
            
        try:
            import examples.transaction as exp
        except StandardError, e:
            self.fail(e)
        self._exec_main(exp)
    
    def test_unicode(self):
        """examples/unicode.py"""
        try:
            import examples.unicode as exp
        except StandardError, e:
            self.fail(e)
        self._exec_main(exp)
    
    def test_warnings(self):
        """examples/warnings.py"""
        try:
            import examples.warnings as exp
        except StandardError, e:
            self.fail(e)
        self._exec_main(exp)
    
    def test_multi_resultsets(self):
        """examples/multi_resultsets.py"""
        try:
            import examples.multi_resultsets as exp
        except StandardError, e:
            self.fail(e)
        self._exec_main(exp)
