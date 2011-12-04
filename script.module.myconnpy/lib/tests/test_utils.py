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

"""Unittests for mysql.connector.utils
"""

import sys, struct

import tests
from mysql.connector import connection, cursor, conversion, protocol, utils, errors, constants

class UtilsTests(tests.MySQLConnectorTests):
    """Testing the helper functions in the utils module.
    
    These tests should not make a connection to the database.
    """
    def test_int1store(self):
        """Use int1store to pack an integer (2^8) as a string."""
        data = 2**(8-1)
        exp = struct.pack('<B',data)
        
        try:
            result = utils.int1store(data)
        except ValueError, e:
            self.fail("int1store failed: %s" % e)
        else:
            if not isinstance(result, str):
                self.fail("Wrong result. Expected %s, we got %s" %\
                    (type(exp), type(result)))
            elif exp != result:
                self.fail("Wrong result. Expected %s, we got %s" %\
                    (data, result))
                
    def test_int2store(self):
        """Use int2store to pack an integer (2^16) as a string."""
        data = 2**(16-1)
        exp = struct.pack('<H',data)
        
        try:
            result = utils.int2store(data)
        except ValueError, e:
            self.fail("int2store failed: %s" % e)
        else:
            if not isinstance(result, str):
                self.fail("Wrong result. Expected %s, we got %s" %\
                    (type(exp), type(result)))
            elif exp != result:
                self.fail("Wrong result. Expected %s, we got %s" %\
                    (data, result))

    def test_int3store(self):
        """Use int3store to pack an integer (2^24) as a string."""
        data = 2**(24-1)
        exp = struct.pack('<I',data)[0:3]
        
        try:
            result = utils.int3store(data)
        except ValueError, e:
            self.fail("int3store failed: %s" % e)
        else:
            if not isinstance(result, str):
                self.fail("Wrong result. Expected %s, we got %s" %\
                    (type(exp), type(result)))
            elif exp != result:
                self.fail("Wrong result. Expected %s, we got %s" %\
                    (data, result))

    def test_int4store(self):
        """Use int4store to pack an integer (2^32) as a string."""
        data = 2**(32-1)
        exp = struct.pack('<I',data)
        
        try:
            result = utils.int4store(data)
        except ValueError, e:
            self.fail("int4store failed: %s" % e)
        else:
            if not isinstance(result, str):
                self.fail("Wrong result. Expected %s, we got %s" %\
                    (type(exp), type(result)))
            elif exp != result:
                self.fail("Wrong result. Expected %s, we got %s" %\
                    (data, result))
    
    def test_int8store(self):
        """Use int8store to pack an integer (2^64) as a string."""
        data = 2**(64-1)
        exp = struct.pack('<Q',data)

        try:
            result = utils.int8store(data)
        except ValueError, e:
            self.fail("int8store failed: %s" % e)
        else:
            if not isinstance(result, str):
                self.fail("Wrong result. Expected %s, we got %s" %\
                    (type(exp), type(result)))
            elif exp != result:
                self.fail("Wrong result. Expected %s, we got %s" %\
                    (data, result))

    def test_intstore(self):
        """Use intstore to pack valid integers (2^64 max) as a string."""
        try:
            for i,r in enumerate((8, 16, 24, 32, 64)):
                val = 2**(r-1)
                utils.intstore(val)
        except ValueError, e:
            self.fail("intstore failed with 'int%dstore: %s" %\
                (i,e))
    
    def test_read_bytes(self):
        """Read a number of bytes from a bufffer"""
        buf = "ABCDEFghijklm"
        readsize = 6
        exp = "ghijklm"
        expsize = len(exp)
        
        try:
            (result, s) = utils.read_bytes(buf, readsize)
        except:
            self.fail("Failed reading bytes using read_bytes.")
        else:
            if result != exp or len(result) != expsize:
                self.fail("Wrong result. Expected: '%s' / %d, got '%s'/%d" %\
                    (exp, expsize, result, len(result)))
    
    def test_read_lc_string_1(self):
        """Read a length code string from a buffer ( <= 250 bytes)"""
        exp = "a" * 2**(8-1)
        expsize = len(exp)
        lcs = utils.int1store(expsize) + exp
        
        (rest, result) = utils.read_lc_string(lcs)
        if result != exp or len(result) != expsize:
            self.fail("Wrong result. Expected '%d', got '%d'" %\
                expsize, len(result))

    def test_read_lc_string_2(self):
        """Read a length code string from a buffer ( <= 2^16 bytes)"""
        exp = "a" * 2**(16-1)
        expsize = len(exp)
        lcs = '\xfc' + utils.int2store(expsize) + exp

        (rest, result) = utils.read_lc_string(lcs)
        if result != exp or len(result) != expsize:
            self.fail("Wrong result. Expected '%d', got '%d'" %\
                expsize, len(result))

    def test_read_lc_string_3(self):
        """Read a length code string from a buffer ( <= 2^24 bytes)"""
        exp = "a" * 2**(24-1)
        expsize = len(exp)
        lcs = '\xfd' + utils.int3store(expsize) + exp

        (rest, result) = utils.read_lc_string(lcs)
        if result != exp or len(result) != expsize:
            self.fail("Wrong result. Expected size'%d', got '%d'" %\
                expsize, len(result))

    def test_read_lc_string_8(self):
        """Read a length code string from a buffer ( <= 2^32 bytes)"""
        exp = "a" * (2**24)
        expsize = len(exp)
        lcs = '\xfe' + utils.int8store(expsize) + exp

        (rest, result) = utils.read_lc_string(lcs)
        if result != exp or len(result) != expsize:
            self.fail("Wrong result. Expected size '%d', got '%d'" %\
                expsize, len(result))
    
    def test_read_lc_string_5(self):
        """Read a length code string from a buffer which is 'NULL'"""
        exp = 'abc'
        lcs = '\xfb' + 'abc'
        
        (rest, result) = utils.read_lc_string(lcs)
        if result != None or rest != 'abc':
            self.fail("Wrong result. Expected None.")
    
    def test_read_string_1(self):
        """Read a string from a buffer up until a certain character."""
        buf = 'abcdef\x00ghijklm'
        exp = 'abcdef'
        exprest = 'ghijklm'
        end = '\x00'
        
        (rest, result) = utils.read_string(buf, end=end)
        if result != exp:
            self.fail("Wrong result. Expected '%s', got '%s'" %\
                exp, result)
        elif rest != exprest:
            self.fail("Wrong result. Expected '%s', got '%s'" %\
                exp, result)
    
    def test_read_string_2(self):
        """Read a string from a buffer up until a certain size."""
        buf = 'abcdefghijklm'
        exp = 'abcdef'
        exprest = 'ghijklm'
        size = 6
        
        (rest, result) = utils.read_string(buf, size=size)
        if result != exp:
            self.fail("Wrong result. Expected '%s', got '%s'" %\
                exp, result)
        elif rest != exprest:
            self.fail("Wrong result. Expected '%s', got '%s'" %\
                exp, result)

    def test_read_int(self):
        """Read an integer from a buffer."""
        buf = '34581adbkdasdf'

        self.assertEqual(51, utils.read_int(buf,1)[1])
        self.assertEqual(13363, utils.read_int(buf,2)[1])
        self.assertEqual(3486771, utils.read_int(buf,3)[1])
        self.assertEqual(943010867, utils.read_int(buf,4)[1])
        self.assertEqual(7089898577412305971, utils.read_int(buf,8)[1])

    def test_read_lc_int(self):
        """Read a length encoded integer from a buffer."""
        buf = '\xfb'

        exp = 2**(8-1)
        lcs = utils.intstore(exp)
        self.assertEqual(exp,utils.read_lc_int(lcs)[1],
            "Failed getting length coded int(250)")

        exp = 2**(8-1)
        lcs = utils.intstore(251) + utils.intstore(exp)
        self.assertEqual(None,utils.read_lc_int(lcs)[1],
            "Failed getting length coded int(250)")

        exp = 2**(16-1)
        lcs = utils.intstore(252) + utils.intstore(exp)
        self.assertEqual(exp,utils.read_lc_int(lcs)[1],
            "Failed getting length coded int(2^16-1)")

        exp = 2**(24-1)
        lcs = utils.intstore(253) + utils.intstore(exp)
        self.assertEqual(exp,utils.read_lc_int(lcs)[1],
            "Failed getting length coded int(2^24-1)")

        exp = 12321848580485677055
        lcs = '\xfe\xff\xff\xff\xff\xff\xff\xff\xaa\xdd\xdd'
        exprest = '\xdd\xdd'
        self.assertEqual((exprest,exp),utils.read_lc_int(lcs),
            "Failed getting length coded long long")
