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

"""Unittests for MySQL data types
"""

from decimal import Decimal
import time
import datetime

from mysql.connector.connection import MySQLConnection
import tests

class TestsDataTypes(tests.MySQLConnectorTests):
    
    tables = {
        'bit': 'myconnpy_mysql_bit',
        'int': 'myconnpy_mysql_int',
        'bool': 'myconnpy_mysql_bool',
        'float': 'myconnpy_mysql_float',
        'decimal': 'myconnpy_mysql_decimal',
        'temporal': 'myconnpy_mysql_temporal',
    }
    
    def _get_insert_stmt(self, tbl, cols):
        insert = """insert into %s (%s) values (%s)""" % (
            tbl, ','.join(cols),
            ','.join(['%s']*len(cols)))
        return insert
        
    def _get_select_stmt(self, tbl, cols):
        select = "SELECT %s FROM %s ORDER BY id" % (
            ','.join(cols), tbl)
        return select
        
class TestsCursor(TestsDataTypes):
    
    def setUp(self):
        config = self.getMySQLConfig()
        self.db = MySQLConnection(**config)
        c = self.db.cursor()
        tblNames = self.tables.values()
        c.execute("DROP TABLE IF EXISTS %s" % (','.join(tblNames)))
        c.close()
    
    def tearDown(self):
        
        c = self.db.cursor()
        tblNames = self.tables.values()
        c.execute("DROP TABLE IF EXISTS %s" % (','.join(tblNames)))
        c.close()
        
        self.db.close()
    
    def test_numeric_int(self):
        """MySQL numeric integer data types"""
        c = self.db.cursor()
        columns = [
            'tinyint_signed',
            'tinyint_unsigned',
            'bool_signed',
            'smallint_signed',
            'smallint_unsigned',
            'mediumint_signed',
            'mediumint_unsigned',
            'int_signed',
            'int_unsigned',
            'bigint_signed',
            'bigint_unsigned',
        ]
        c.execute("""CREATE TABLE %s (
          `id` TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
          `tinyint_signed` TINYINT SIGNED,
          `tinyint_unsigned` TINYINT UNSIGNED,
          `bool_signed` BOOL,
          `smallint_signed` SMALLINT SIGNED,
          `smallint_unsigned` SMALLINT UNSIGNED,
          `mediumint_signed` MEDIUMINT SIGNED,
          `mediumint_unsigned` MEDIUMINT UNSIGNED,
          `int_signed` INT SIGNED,
          `int_unsigned` INT UNSIGNED,
          `bigint_signed` BIGINT SIGNED,
          `bigint_unsigned` BIGINT UNSIGNED,
          PRIMARY KEY (id)
          )
        """ % (self.tables['int']))
        
        data = [
            (
            -128, # tinyint signed
            0, # tinyint unsigned
            0, # boolean
            -32768, # smallint signed
            0, # smallint unsigned
            -8388608, # mediumint signed
            0, # mediumint unsigned
            -2147483648, # int signed
            0, # int unsigned
            -9223372036854775808, # big signed
            0, # big unsigned
            ),
            (
            127, # tinyint signed
            255, # tinyint unsigned
            127, # boolean
            32767, # smallint signed
            65535, # smallint unsigned
            8388607, # mediumint signed
            16777215, # mediumint unsigned
            2147483647, # int signed
            4294967295, # int unsigned
            9223372036854775807, # big signed
            18446744073709551615, # big unsigned
            )
        ]

        insert = self._get_insert_stmt(self.tables['int'],columns)
        select = self._get_select_stmt(self.tables['int'],columns)
        
        c.executemany(insert, data)
        c.execute(select)
        rows = c.fetchall()
        
        def compare(name, d, r):
           self.assertEqual(d,r,"%s  %s != %s" % (name,d,r))
            
        for i,col in enumerate(columns):
            compare(col,data[0][i],rows[0][i])
            compare(col,data[1][i],rows[1][i])
        
        c.close()
    
    def test_numeric_bit(self):
        """MySQL numeric bit data type"""
        c = self.db.cursor()
        columns = [
             'c8','c16','c24','c32',
            'c40','c48','c56','c63',
            'c64']
        c.execute("""CREATE TABLE %s (
          `id` int NOT NULL AUTO_INCREMENT,
          `c8` bit(8) DEFAULT NULL,
          `c16` bit(16) DEFAULT NULL,
          `c24` bit(24) DEFAULT NULL,
          `c32` bit(32) DEFAULT NULL,
          `c40` bit(40) DEFAULT NULL,
          `c48` bit(48) DEFAULT NULL,
          `c56` bit(56) DEFAULT NULL,
          `c63` bit(63) DEFAULT NULL,
          `c64` bit(64) DEFAULT NULL,
          PRIMARY KEY (id)
        )
        """ % self.tables['bit'])
        
        insert = self._get_insert_stmt(self.tables['bit'],columns)
        select = self._get_select_stmt(self.tables['bit'],columns)
        
        data = list()
        data.append(tuple([0]*len(columns)))
        
        values = list()
        for col in columns:
            values.append( 1 << int(col.replace('c',''))-1)
        data.append(tuple(values))
        
        values = list()
        for col in columns:
            values.append( (1 << int(col.replace('c',''))) -1)
        data.append(tuple(values))
        
        c.executemany(insert, data)
        c.execute(select)
        rows = c.fetchall()

        self.assertEqual(rows, data)
        c.close()

    def test_numeric_float(self):
        """MySQL numeric float data type"""
        c = self.db.cursor()
        columns = [
            'float_signed',
            'float_unsigned',
            'double_signed',
            'double_unsigned',
        ]
        c.execute("""CREATE TABLE %s (
            `id` int NOT NULL AUTO_INCREMENT,
            `float_signed` FLOAT(6,5) SIGNED,
            `float_unsigned` FLOAT(6,5) UNSIGNED,
            `double_signed` DOUBLE(15,10) SIGNED,
            `double_unsigned` DOUBLE(15,10) UNSIGNED,
            PRIMARY KEY (id)
        )""" % (self.tables['float']))
        
        insert = self._get_insert_stmt(self.tables['float'],columns)
        select = self._get_select_stmt(self.tables['float'],columns)
        
        data = [
            (-3.402823466,0,-1.7976931348623157,0,),
            (-1.175494351,3.402823466,1.7976931348623157,2.2250738585072014),
            (-1.23455678,2.999999,-1.3999999999999999,1.9999999999999999),
        ]
        c.executemany(insert, data)
        c.execute(select)
        rows = c.fetchall()
        
        def compare(name, d, r):
           self.assertEqual(d,r,"%s  %s != %s" % (name,d,r))
        
        for j in (range(0,len(data))):
            for i,col in enumerate(columns[0:2]):
                compare(col,round(data[j][i],5),rows[j][i])
            for i,col in enumerate(columns[2:2]):
                compare(col,round(data[j][i],10),rows[j][i])
        c.close()
    
    def test_numeric_decimal(self):
        """MySQL numeric decimal data type"""
        c = self.db.cursor()
        columns = [
            'decimal_signed',
            'decimal_unsigned',
        ]
        c.execute("""CREATE TABLE %s (
            `id` int NOT NULL AUTO_INCREMENT,
            `decimal_signed` DECIMAL(65,30) SIGNED,
            `decimal_unsigned` DECIMAL(65,30) UNSIGNED,
            PRIMARY KEY (id)
        )""" % (self.tables['decimal']))
        
        insert = self._get_insert_stmt(self.tables['decimal'],columns)
        select = self._get_select_stmt(self.tables['decimal'],columns)
        
        data = [
         (Decimal('-9999999999999999999999999.999999999999999999999999999999'),
          Decimal('+9999999999999999999999999.999999999999999999999999999999')),
         (Decimal('-1234567.1234'),
          Decimal('+123456789012345.123456789012345678901')),
         (Decimal('-1234567890123456789012345.123456789012345678901234567890'),
          Decimal('+1234567890123456789012345.123456789012345678901234567890')),
        ]
        c.executemany(insert, data)
        c.execute(select)
        rows = c.fetchall()
        
        self.assertEqual(data,rows)
        
        c.close()
    
    def test_temporal_datetime(self):
        """MySQL temporal date/time data types"""
        c = self.db.cursor()
        c.execute("SET SESSION time_zone = '+00:00'")
        columns = [
            't_date',
            't_datetime',
            't_time',
            't_timestamp',
            't_year_2',
            't_year_4',
        ]
        c.execute("""CREATE TABLE %s (
            `id` int NOT NULL AUTO_INCREMENT,
            `t_date` DATE,
            `t_datetime` DATETIME,
            `t_time` TIME,
            `t_timestamp` TIMESTAMP DEFAULT 0,
            `t_year_2` YEAR(2),
            `t_year_4` YEAR(4),
            PRIMARY KEY (id)
        )""" % (self.tables['temporal']))
        
        insert = self._get_insert_stmt(self.tables['temporal'],columns)
        select = self._get_select_stmt(self.tables['temporal'],columns)
        
        data = [
            (datetime.date(2010,1,17),
             datetime.datetime(2010,1,17,19,31,12),
             datetime.timedelta(hours=43,minutes=32,seconds=21),
             datetime.datetime(2010,1,17,19,31,12),
             10,
             0),
            (datetime.date(1000,1,1),
             datetime.datetime(1000,1,1,0,0,0),
             datetime.timedelta(hours=-838,minutes=59,seconds=59),
             datetime.datetime(*time.gmtime(1)[:6]),
             70,
             1901),
            (datetime.date(9999,12,31),
             datetime.datetime(9999,12,31,23,59,59),
             datetime.timedelta(hours=838,minutes=59,seconds=59),
             datetime.datetime(2038,1,19,3,14,7),
             69,
             2155),
        ]
        
        c.executemany(insert, data)
        c.execute(select)
        rows = c.fetchall()
        from pprint import pprint
        
        def compare(name, d, r):
           self.assertEqual(d,r,"%s  %s != %s" % (name,d,r))
        
        for j in (range(0,len(data))):
            for i,col in enumerate(columns):
                compare("%s (data[%d])" % (col,j),data[j][i],rows[j][i])
        
        c.close()
        
