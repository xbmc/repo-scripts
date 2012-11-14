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

"""Unittests for mysql.connector.constants
"""

import sys
import struct

import tests
from mysql.connector import constants, errors

class Helpers(tests.MySQLConnectorTests):
    
    def test_flag_is_set(self):
        """Check if a particular flag/bit is set"""
        
        data = [
            1 << 3,
            1 << 5,
            1 << 7,
            ]
        flags = 0
        for d in data:
            flags |= d
        
        for d in data:
            self.assertTrue(constants.flag_is_set(d,flags))
        
        self.assertFalse(constants.flag_is_set(1 << 4,flags))

class FieldTypeTests(tests.MySQLConnectorTests):
    
    desc = {
        'DECIMAL':       (0x00, 'DECIMAL'),
        'TINY':          (0x01, 'TINY'),
        'SHORT':         (0x02, 'SHORT'),
        'LONG':          (0x03, 'LONG'),
        'FLOAT':         (0x04, 'FLOAT'),
        'DOUBLE':        (0x05, 'DOUBLE'),
        'NULL':          (0x06, 'NULL'),
        'TIMESTAMP':     (0x07, 'TIMESTAMP'),
        'LONGLONG':      (0x08, 'LONGLONG'),
        'INT24':         (0x09, 'INT24'),
        'DATE':          (0x0a, 'DATE'),
        'TIME':          (0x0b, 'TIME'),
        'DATETIME':      (0x0c, 'DATETIME'),
        'YEAR':          (0x0d, 'YEAR'),
        'NEWDATE':       (0x0e, 'NEWDATE'),
        'VARCHAR':       (0x0f, 'VARCHAR'),
        'BIT':           (0x10, 'BIT'),
        'NEWDECIMAL':    (0xf6, 'NEWDECIMAL'),
        'ENUM':          (0xf7, 'ENUM'),
        'SET':           (0xf8, 'SET'),
        'TINY_BLOB':     (0xf9, 'TINY_BLOB'),
        'MEDIUM_BLOB':   (0xfa, 'MEDIUM_BLOB'),
        'LONG_BLOB':     (0xfb, 'LONG_BLOB'),
        'BLOB':          (0xfc, 'BLOB'),
        'VAR_STRING':    (0xfd, 'VAR_STRING'),
        'STRING':        (0xfe, 'STRING'),
        'GEOMETRY':      (0xff, 'GEOMETRY'),
    }
    
    type_groups = {
        'string' : [
            constants.FieldType.VARCHAR,
            constants.FieldType.ENUM,
            constants.FieldType.VAR_STRING, constants.FieldType.STRING,
            ],
        'binary' : [
            constants.FieldType.TINY_BLOB, constants.FieldType.MEDIUM_BLOB,
            constants.FieldType.LONG_BLOB, constants.FieldType.BLOB,
            ],
        'number' : [
            constants.FieldType.DECIMAL, constants.FieldType.NEWDECIMAL,
            constants.FieldType.TINY, constants.FieldType.SHORT,
            constants.FieldType.LONG,
            constants.FieldType.FLOAT, constants.FieldType.DOUBLE,
            constants.FieldType.LONGLONG, constants.FieldType.INT24,
            constants.FieldType.BIT,
            constants.FieldType.YEAR,
            ],
        'datetime' : [
            constants.FieldType.DATETIME, constants.FieldType.TIMESTAMP,
            ],
    }
    
    def test_attributes(self):
        """Check attributes for FieldType"""
        
        self.assertEqual('FIELD_TYPE_', constants.FieldType.prefix)
        
        for k,v in self.desc.items():
            self.failUnless(constants.FieldType.__dict__.has_key(k),
                '%s is not an attribute of FieldType' % k)
            self.assertEqual(v[0],constants.FieldType.__dict__[k],
                '%s attribute of FieldType has wrong value' % k)
    
    def test_get_desc(self):
        """Get field type by name"""
        
        for k,v in self.desc.items():
            exp = v[1]
            res = constants.FieldType.get_desc(k)
            self.assertEqual(exp, res)
        
        self.assertEqual(None,constants.FieldType.get_desc('FooBar'))
            
    def test_get_info(self):
        """Get field type by id"""
        
        for k,v in self.desc.items():
            exp = v[1]
            res = constants.FieldType.get_info(v[0])
            self.assertEqual(exp, res)
    
        self.assertEqual(None,constants.FieldType.get_info(999999999))
    
    def test_get_string_types(self):
        """DBAPI string types"""
        self.assertEqual(self.type_groups['string'],
            constants.FieldType.get_string_types())

    def test_get_binary_types(self):
        """DBAPI string types"""
        self.assertEqual(self.type_groups['binary'],
            constants.FieldType.get_binary_types())
    
    def test_get_number_types(self):
        """DBAPI number types"""
        self.assertEqual(self.type_groups['number'],
            constants.FieldType.get_number_types())

    def test_get_timestamp_types(self):
        """DBAPI datetime types"""
        self.assertEqual(self.type_groups['datetime'],
            constants.FieldType.get_timestamp_types())

class FieldFlagTests(tests.MySQLConnectorTests):


    desc = {
        'NOT_NULL': (1 <<  0, "Field can't be NULL"),
        'PRI_KEY': (1 <<  1, "Field is part of a primary key"),
        'UNIQUE_KEY': (1 <<  2, "Field is part of a unique key"),
        'MULTIPLE_KEY': (1 <<  3, "Field is part of a key"),
        'BLOB': (1 <<  4, "Field is a blob"),
        'UNSIGNED': (1 <<  5, "Field is unsigned"),
        'ZEROFILL': (1 <<  6, "Field is zerofill"),
        'BINARY': (1 <<  7, "Field is binary  "),
        'ENUM': (1 <<  8, "field is an enum"),
        'AUTO_INCREMENT': (1 <<  9, "field is a autoincrement field"),
        'TIMESTAMP': (1 << 10, "Field is a timestamp"),
        'SET': (1 << 11, "field is a set"),
        'NO_DEFAULT_VALUE': (1 << 12, "Field doesn't have default value"),
        'ON_UPDATE_NOW': (1 << 13, "Field is set to NOW on UPDATE"),
        'NUM': (1 << 14, "Field is num (for clients)"),

        'PART_KEY': (1 << 15, "Intern; Part of some key"),
        'GROUP': (1 << 14, "Intern: Group field"),   # Same as NUM
        'UNIQUE': (1 << 16, "Intern: Used by sql_yacc"),
        'BINCMP': (1 << 17, "Intern: Used by sql_yacc"),
        'GET_FIXED_FIELDS': (1 << 18, "Used to get fields in item tree"),
        'FIELD_IN_PART_FUNC': (1 << 19, "Field part of partition func"),
        'FIELD_IN_ADD_INDEX': (1 << 20, "Intern: Field used in ADD INDEX"),
        'FIELD_IS_RENAMED': (1 << 21, "Intern: Field is being renamed"),
    }

    def test_attributes(self):
        """Check attributes for FieldFlag"""
        
        self.assertEqual('', constants.FieldFlag._prefix)
        
        for k,v in self.desc.items():
            self.failUnless(constants.FieldFlag.__dict__.has_key(k),
                '%s is not an attribute of FieldFlag' % k)
            self.assertEqual(v[0],constants.FieldFlag.__dict__[k],
                '%s attribute of FieldFlag has wrong value' % k)
    
    def test_get_desc(self):
        """Get field flag by name"""
        
        for k,v in self.desc.items():
            exp = v[1]
            res = constants.FieldFlag.get_desc(k)
            self.assertEqual(exp, res)
            
    def test_get_info(self):
        """Get field flag by id"""
        
        for k,v in self.desc.items():
            # Ignore the NUM/GROUP (bug in MySQL source code)
            if v[0] == 1 << 14:
                break
            exp = v[1]
            res = constants.FieldFlag.get_info(v[0])
            self.assertEqual(exp, res)
    
    def test_get_bit_info(self):
        """Get names of the set flags"""
        
        data = 0
        data |= constants.FieldFlag.BLOB
        data |= constants.FieldFlag.BINARY
        exp = ['BINARY', 'BLOB']
        self.assertEqual(exp,constants.FieldFlag.get_bit_info(data))
            
class CharacterSetTests(tests.MySQLConnectorTests):
    """Tests for constants.CharacterSet"""
    
    def test_get_info(self):
        """Get info about charset using MySQL ID"""
        exp = ('utf8','utf8_general_ci')
        data = 33
        self.assertEqual(exp, constants.CharacterSet.get_info(data))
        
        exception = errors.ProgrammingError
        data = 50000
        self.assertRaises(exception, constants.CharacterSet.get_info, data)
    
    def test_get_desc(self):
        """Get info about charset using MySQL ID as string"""
        exp = 'utf8/utf8_general_ci'
        data = 33
        self.assertEqual(exp, constants.CharacterSet.get_desc(data))
        
        exception = errors.ProgrammingError
        data = 50000
        self.assertRaises(exception, constants.CharacterSet.get_desc, data)
    
    def test_get_default_collation(self):
        """Get default collation for a given Character Set"""
        func = constants.CharacterSet.get_default_collation
        data = 'sjis'
        exp = ('sjis_japanese_ci',data,13)
        self.assertEqual(exp, func(data))
        self.assertEqual(exp, func(exp[2]))
        
        exception = errors.ProgrammingError
        data = 'foobar'
        self.assertRaises(exception, func, data)
        
    def test_get_charset_info(self):
        """Get info about charset by name and collation"""
        func = constants.CharacterSet.get_charset_info
        exp = (209,'utf8','utf8_esperanto_ci')
        data = exp[1:]
        
        self.assertEqual(exp, func(data[0],data[1]))
        self.assertEqual(exp, func(exp[0]))
                
        exception = errors.ProgrammingError
        data = ('utf8','utf8_OOOOPS_ci',False)

        self.assertRaises(exception,
            constants.CharacterSet.get_charset_info, data[0], data[1])
    
    def test_get_supported(self):
        """Get list of all supported character sets"""
        exp = ('big5', 'latin2', 'dec8', 'cp850', 'latin1', 'hp8', 'koi8r',
          'swe7', 'ascii', 'ujis', 'sjis', 'cp1251', 'hebrew', 'tis620',
          'euckr', 'latin7', 'koi8u', 'gb2312', 'greek', 'cp1250', 'gbk',
          'cp1257', 'latin5', 'armscii8', 'utf8', 'ucs2', 'cp866', 'keybcs2',
          'macce', 'macroman', 'cp852', 'cp1256', 'binary', 'geostd8',
          'cp932', 'eucjpms')
        
        self.assertEqual(exp, constants.CharacterSet.get_supported())

    
