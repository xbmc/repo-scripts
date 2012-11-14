# MySQL Connector/Python - MySQL driver written in Python.
# Copyright (c) 2009,2011, Oracle and/or its affiliates. All rights reserved.
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

"""Unittests for bugs
"""

import sys
import struct
import os
import time

import tests
from mysql.connector import connection, cursor, conversion, protocol, utils, errors, constants

class Bug328998Tests(tests.MySQLConnectorTests):
    
    def test_set_connection_timetout(self):
        config = tests.MYSQL_CONFIG.copy()
        config['connection_timeout'] = 5
        self.db = connection.MySQLConnection(**config)
        self.assertEqual(config['connection_timeout'],
            self.db.protocol.conn.connection_timeout)
        if self.db:
            self.db.disconnect()
    
    def test_timeout(self):
        config = tests.MYSQL_CONFIG.copy()
        config['connection_timeout'] = 1
        self.db = connection.MySQLConnection(**config)

        c = self.db.cursor()
        self.assertRaises(errors.InterfaceError,
            c.execute, "SELECT SLEEP(%d)" % (config['connection_timeout']+4))

        if self.db:
            self.db.disconnect()

class Bug437972Tests(tests.MySQLConnectorTests):

    def test_windows_tcp_connection(self):
        """lp:437972 TCP connection to Windows"""
        if os.name != 'nt':
            pass
        
        db = None
        try:
            db = connection.MySQLConnection(**tests.MYSQL_CONFIG)
        except errors.InterfaceError:
            self.fail()

        if db:
            db.close()

class Bug441430Tests(tests.MySQLConnectorTests):

    def test_execute_return(self):
        """lp:441430 cursor.execute*() should return the cursor.rowcount"""
        
        db = connection.MySQLConnection(**self.getMySQLConfig())
        c = db.cursor()
        tbl = "buglp44130"
        c.execute("DROP TABLE IF EXISTS %s" % tbl)
        c.execute("CREATE TABLE %s (id INT)" % tbl)
        res = c.execute("INSERT INTO %s VALUES (%%s),(%%s)" % tbl, (1,2,))
        self.assertEqual(2,res)
        stmt = "INSERT INTO %s VALUES (%%s)" % tbl
        res = c.executemany(stmt,[(3,),(4,),(5,),(6,),(7,),(8,)])
        self.assertEqual(6,res)
        res = c.execute("UPDATE %s SET id = id + %%s" % tbl , (10,))
        self.assertEqual(8,res)
        c.close()
        db.close()
        
class Bug454782(tests.MySQLConnectorTests):
    
    def test_fetch_retun_values(self):
        """lp:454782 fetchone() does not follow pep-0249"""
        
        db = connection.MySQLConnection(**self.getMySQLConfig())
        c = db.cursor()
        self.assertEqual(None,c.fetchone())
        self.assertEqual([],c.fetchmany())
        self.assertRaises(errors.InterfaceError,c.fetchall)
        c.close()
        db.close()

class Bug454790(tests.MySQLConnectorTests):
    
    def test_pyformat(self):
        """lp:454790 pyformat / other named parameters broken"""
        
        db = connection.MySQLConnection(**self.getMySQLConfig())
        c = db.cursor()
        
        data = {'name': 'Geert','year':1977}
        c.execute("SELECT %(name)s,%(year)s", data)
        self.assertEqual((u'Geert',1977L),c.fetchone())
        
        data = [{'name': 'Geert','year':1977},{'name':'Marta','year':1980}]
        self.assertEqual(2,c.executemany("SELECT %(name)s,%(year)s", data))
        c.close()
        db.close()

class Bug480360(tests.MySQLConnectorTests):
    
    def test_fetchall(self):
        """lp:480360: fetchall() should return [] when no result"""
        
        db = connection.MySQLConnection(**self.getMySQLConfig())
        c = db.cursor()
        
        # Trick to get empty result not needing any table
        c.execute("SELECT * FROM (SELECT 1) AS t WHERE 0 = 1")
        self.assertEqual([],c.fetchall())
        c.close()
        db.close()
        
class Bug380528(tests.MySQLConnectorTests):

    def test_old_password(self):
        """lp:380528: we do not support old passwords."""

        config = self.getMySQLConfig()
        db = connection.MySQLConnection(**config)
        c = db.cursor()

        if config['unix_socket']:
            user = "'myconnpy'@'localhost'"
        else:
            user = "'myconnpy'@'%s'" % (config['host'])
        
        try:
            c.execute("GRANT SELECT ON %s.* TO %s" % (config['database'],user))
            c.execute("SET PASSWORD FOR %s = OLD_PASSWORD('fubar')" % (user))
        except:
            self.fail("Failed executing grant.")
        c.close()
        db.close()
        
        # Test using the newly created user
        test_config = config.copy()
        test_config['user'] = 'myconnpy'
        test_config['password'] = 'fubar'
        
        self.assertRaises(errors.NotSupportedError,connection.MySQLConnection,**test_config)
            
        db = connection.MySQLConnection(**config)
        c = db.cursor()
        try:
            c.execute("REVOKE SELECT ON %s.* FROM %s" % (config['database'],user))
            c.execute("DROP USER %s" % (user))
        except:
            self.fail("Failed cleaning up user %s." % (user))
        c.close()
        db.close()

class Bug499362(tests.MySQLConnectorTests):
    
    def test_charset(self):
        """lp:499362 Setting character set at connection fails"""
        config = self.getMySQLConfig()
        config['charset'] = 'latin1'
        db = connection.MySQLConnection(**config)
        c = db.cursor()
        
        ver = db.get_server_version()
        if ver < (5,1,12):
            exp1 = [(u'character_set_client', u'latin1'), 
                (u'character_set_connection', u'latin1'),
                (u'character_set_database', u'utf8'),
                (u'character_set_filesystem', u'binary'),
                (u'character_set_results', u'latin1'),
                (u'character_set_server', u'utf8'),
                (u'character_set_system', u'utf8')]
            exp2 = [(u'character_set_client', u'latin2'),
                (u'character_set_connection', u'latin2'),
                (u'character_set_database', u'utf8'),
                (u'character_set_filesystem', u'binary'),
                (u'character_set_results', u'latin2'),
                (u'character_set_server', u'utf8'),
                (u'character_set_system', u'utf8')]
            varlst = []
            stmt = "SHOW SESSION VARIABLES LIKE 'character\_set\_%%'"
        else:
            exp1 = [(u'CHARACTER_SET_CONNECTION', u'latin1'),
                (u'CHARACTER_SET_CLIENT', u'latin1'),
                (u'CHARACTER_SET_RESULTS', u'latin1')]
            exp2 = [(u'CHARACTER_SET_CONNECTION', u'latin2'),
                (u'CHARACTER_SET_CLIENT', u'latin2'),
                (u'CHARACTER_SET_RESULTS', u'latin2')]
        
            varlst = ['character_set_client','character_set_connection',
                'character_set_results']
            stmt = """SELECT * FROM INFORMATION_SCHEMA.SESSION_VARIABLES
                WHERE VARIABLE_NAME IN (%s,%s,%s)"""
            
        c.execute(stmt, varlst)
        res1 = c.fetchall()
        db.set_charset('latin2')
        c.execute(stmt, varlst)
        res2 = c.fetchall()
        
        c.close()
        db.close()
        
        self.assertTrue(self.cmpResult(exp1, res1))
        self.assertTrue(self.cmpResult(exp2, res2))

class Bug499410(tests.MySQLConnectorTests):
    
    def test_use_unicode(self):
        """lp:499410 Disabling unicode does not work"""
        config = self.getMySQLConfig()
        config['use_unicode'] = False
        db = connection.MySQLConnection(**config)
        
        self.assertEqual(False, db.use_unicode)
        db.close()
    
    def test_charset(self):
        config = self.getMySQLConfig()
        config['use_unicode'] = False
        charset = 'greek'
        config['charset'] = charset
        db = connection.MySQLConnection(**config)
        
        data = [
             # Bye in Greek
            '\xe1\xed\xf4\xdf\xef',
            ]
        
        exp_nonunicode = [(data[0],)]
        exp_unicode = [(u'\u03b1\u03bd\u03c4\u03af\u03bf',),]
        
        c = db.cursor()
        
        tbl = '%stest' % (charset)
        try:
            c.execute('DROP TABLE IF EXISTS %s' % (tbl))
            c.execute('CREATE TABLE %s (c1 VARCHAR(60)) charset=%s' %\
                (tbl,charset))
        except:
            self.fail("Failed creating test table.")
        
        try:
            stmt = 'INSERT INTO %s VALUES (%%s)' % (tbl)
            for line in data:
                c.execute(stmt, (line.strip(),))
        except:
            self.fail("Failed populating test table.")
        
        c.execute("SELECT * FROM %s" %(tbl))
        res_nonunicode = c.fetchall()
        db.set_unicode(True)
        c.execute("SELECT * FROM %s" %(tbl))
        res_unicode = c.fetchall()
        
        try:
            c.execute('DROP TABLE IF EXISTS %s' % (tbl))
        except:
            self.fail("Failed cleaning up test table.")
        
        db.close()
        
        self.assertEqual(exp_nonunicode,res_nonunicode)
        self.assertEqual(exp_unicode,res_unicode)

class Bug501290(tests.MySQLConnectorTests):
    """lp:501290 Client flags are set to None when connecting"""
    
    def setUp(self):
        config = self.getMySQLConfig()
        self.db = connection.MySQLConnection(**config)
    
    def tearDown(self):
        self.db.close()
    
    def test_default(self):
        """lp:501290 Check default client flags"""
        self.assertEqual(self.db.client_flags,
            constants.ClientFlag.get_default())
    
    def test_set_client_flag(self):
        """lp:501290 Set one flag, check if set"""
        exp = constants.ClientFlag.get_default() | \
            constants.ClientFlag.COMPRESS
            
        self.db.set_client_flag(constants.ClientFlag.COMPRESS)
        self.assertEqual(self.db.client_flags,exp)
    
    def test_unset_client_flag(self):
        """lp:501290 Unset a client flag"""
        data = constants.ClientFlag.get_default() | \
            constants.ClientFlag.COMPRESS
        exp = constants.ClientFlag.get_default()
        
        self.db.client_flags = data
        self.db.unset_client_flag(constants.ClientFlag.COMPRESS)
        
        self.assertEqual(self.db.client_flags,exp)
    
    def test_isset_client_flag(self):
        """lp:501290 Check if client flag is set"""
        data = constants.ClientFlag.get_default() | \
            constants.ClientFlag.COMPRESS
        
        self.db.client_flags = data
        self.assertEqual(True,
            self.db.isset_client_flag(constants.ClientFlag.COMPRESS))
    
class Bug507466(tests.MySQLConnectorTests):
    """lp:507466 BIT values are not converted correctly to Python"""
    
    def setUp(self):
        config = self.getMySQLConfig()
        self.db = connection.MySQLConnection(**config)
    
    def tearDown(self):
        try:
            c = db.cursor("DROP TABLE IF EXISTS myconnpy_bits")
        except:
            pass
        self.db.close()
    
    def test_bits(self):
        """lp:507466 Store bitwise values in MySQL and retrieve them"""
        c = self.db.cursor()

        c.execute("DROP TABLE IF EXISTS myconnpy_bits")
        c.execute("""CREATE TABLE `myconnpy_bits` (
          `id` int NOT NULL AUTO_INCREMENT,
          `c1` bit(8) DEFAULT NULL,
          `c2` bit(16) DEFAULT NULL,
          `c3` bit(24) DEFAULT NULL,
          `c4` bit(32) DEFAULT NULL,
          `c5` bit(40) DEFAULT NULL,
          `c6` bit(48) DEFAULT NULL,
          `c7` bit(56) DEFAULT NULL,
          `c8` bit(64) DEFAULT NULL,
          PRIMARY KEY (id)
        )
        """)

        insert = """insert into myconnpy_bits (c1,c2,c3,c4,c5,c6,c7,c8)
            values (%s,%s,%s,%s,%s,%s,%s,%s)"""
        select = "SELECT c1,c2,c3,c4,c5,c6,c7,c8 FROM myconnpy_bits ORDER BY id"

        data = []
        data.append((0, 0, 0, 0, 0, 0, 0, 0))
        data.append((
            1 <<  7, 1 << 15, 1 << 23, 1 << 31,
            1 << 39, 1 << 47, 1 << 55, 1 << 63,
            ))
        c.executemany(insert, data)
        c.execute(select)
        rows = c.fetchall()
        
        self.assertEqual(rows, data)

class Bug510110(tests.MySQLConnectorTests):
    """lp:510110 Rollback fails when still reading"""
    
    def setUp(self):
        config = self.getMySQLConfig()
        self.db = connection.MySQLConnection(**config)
        self.c = self.db.cursor()
        
        self.tbl = 'Bug510110'
        self.c.execute("DROP TABLE IF EXISTS %s" % (self.tbl))
        self.c.execute("""CREATE TABLE %s (
            id int unsigned auto_increment key,
            c1 varchar(20)
        ) ENGINE=InnoDB""" % (self.tbl))
    
    def tearDown(self):
        try:
            self.c = db.cursor("DROP TABLE IF EXISTS %s" % (self.tbl))
            self.c.close()
        except:
            pass
        self.db.close()
    
    def test_unbuffered(self):
        """lp:510110 InternalError exception with unbuffered cursor"""
        self.c.execute("INSERT INTO %s (c1) VALUES ('foo')" % (self.tbl))
        self.db.commit()
        self.c.execute("INSERT INTO %s (c1) VALUES ('bar')" % (self.tbl))
        self.c.execute("SELECT * FROM %s ORDER BY id" % (self.tbl))
        self.assertRaises(errors.InternalError,self.db.rollback)
    
    def test_buffered(self):
        """lp:510110 Buffered cursor, rollback is possible after SELECT"""
        self.c.close()
        self.db.buffered = True
        self.c = self.db.cursor()
        self.c.execute("INSERT INTO %s (c1) VALUES ('foo')" % (self.tbl))
        self.db.commit()
        self.c.execute("INSERT INTO %s (c1) VALUES ('bar')" % (self.tbl))
        self.db.rollback()
        self.c.execute("SELECT * FROM %s ORDER BY id" % (self.tbl))
        self.assertEqual([(1L, u'foo')],self.c.fetchall())

class Bug519301(tests.MySQLConnectorTests):
    """lp:519301 Temporary connection failures with 2 exceptions"""

    def test_auth(self):

        config = self.getMySQLConfig()
        config['user'] = 'ham'
        config['password'] = 'spam'
        
        db = None
        for i in xrange(1,100):
            pass
            try:
                db = connection.MySQLConnection(**config)
            except errors.OperationalError, e:
                pass
            except errors.ProgrammingError, e:
                self.fail("Failing authenticating")
                break
            else:
                db.close()

class Bug524668(tests.MySQLConnectorTests):
    """lp:524668 Error in server handshake with latest code"""
    
    def test_handshake(self):
        """lp:524668 Error in server handshake with latest code"""
        
        handshake = '\x47\x00\x00\x00\x0a\x35\x2e\x30\x2e\x33\x30\x2d\x65'\
            '\x6e\x74\x65\x72\x70\x72\x69\x73\x65\x2d\x67\x70\x6c\x2d\x6c\x6f'\
            '\x67\x00\x09\x01\x00\x00\x68\x34\x69\x36\x6f\x50\x21\x4f\x00'\
            '\x2c\xa2\x08\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'\
            '\x00\x00\x4c\x6e\x67\x39\x26\x50\x44\x40\x57\x72\x59\x48\x00'
        
        class Cnx(object):
            pass
            
        p = protocol.MySQLProtocol(Cnx())
        try:
            p.handle_handshake(handshake)
        except:
            raise
            self.fail("Failed handling handshake")

class Bug571201(tests.MySQLConnectorTests):
    """lp:571201 Problem with more than one statement at a time"""
    
    def setUp(self):
        config = self.getMySQLConfig()
        self.db = connection.MySQLConnection(**config)
        self.c = self.db.cursor()
        
        self.tbl = 'Bug571201'
        self.c.execute("DROP TABLE IF EXISTS %s" % (self.tbl))
        self.c.execute("""CREATE TABLE %s (
            id INT AUTO_INCREMENT KEY,
            c1 INT
        )""" % (self.tbl))
    
    def tearDown(self):
        try:
            self.c = db.cursor("DROP TABLE IF EXISTS %s" % (self.tbl))
            self.c.close()
        except:
            pass
        self.db.close()
    
    def test_multistmts(self):
        """lp:571201 Problem with more than one statement at a time"""
        
        stmts = [
            "SELECT * FROM %s" % (self.tbl),
            "INSERT INTO %s (c1) VALUES (10),(20)" % (self.tbl),
            "SELECT * FROM %s" % (self.tbl),
            ]
        self.c.execute(';'.join(stmts))
        
        self.assertEqual(None,self.c.fetchone())
        self.assertEqual(True,self.c.next_resultset())
        self.assertEqual(2,self.c.rowcount)
        self.assertEqual(True,self.c.next_resultset())
        exp = [(1, 10), (2, 20)]
        self.assertEqual(exp,self.c.fetchall())
        self.assertEqual(None,self.c.next_resultset())

class Bug551533and586003(tests.MySQLConnectorTests):
    """lp: 551533, 586003: impossible to retrieve big result sets"""

    def setUp(self):
        config = self.getMySQLConfig()
        config['connection_timeout'] = 2
        self.db = connection.MySQLConnection(**config)
        self.c = self.db.cursor()

        self.tbl = 'Bug551533'
        self.c.execute("DROP TABLE IF EXISTS %s" % (self.tbl))
        self.c.execute("""CREATE TABLE %s (
            id INT AUTO_INCREMENT KEY,
            c1 VARCHAR(100) DEFAULT 'abcabcabcabcabcabcabcabcabcabc'
        )""" % (self.tbl))

    def tearDown(self):
        try:
            self.c = db.cursor("DROP TABLE IF EXISTS %s" % (self.tbl))
            self.c.close()
        except:
            pass
        self.db.close()

    def test_select(self):
        """lp: 551533, 586003: impossible to retrieve big result sets"""

        insert = "INSERT INTO %s VALUES ()" % (self.tbl)
        exp = 20000
        i = exp
        while i > 0:
            self.c.execute(insert)
            i -= 1
        
        self.c.execute('SELECT * FROM %s LIMIT 20000' % (self.tbl))
        try:
            rows = self.c.fetchall()
        except:
            self.fail("Failed retrieving big result set")
        else:
            self.assertEqual(exp, self.c.rowcount)

class Bug598706(tests.MySQLConnectorTests):
    """lp: 598706: config file in examples doesn't return the port"""

    def test_getport(self):
        """lp: 598706: config file in examples doesn't return the port"""
        
        from examples import config
        exp = 3306
        data = config.Config.dbinfo()
        self.assertEqual(exp, data['port'])

class Bug675425(tests.MySQLConnectorTests):
    """lp: 675425: Problems with apostrophe"""
    
    def setUp(self):
        config = self.getMySQLConfig()
        config['connection_timeout'] = 2
        self.db = connection.MySQLConnection(**config)
        self.c = self.db.cursor()

        self.tbl = 'Bug551533'
        self.c.execute("DROP TABLE IF EXISTS %s" % (self.tbl))
        self.c.execute("""CREATE TABLE %s (
            c1 VARCHAR(30),
            c2 VARCHAR(30)
        )""" % (self.tbl))

    def tearDown(self):
        try:
            self.c = db.cursor("DROP TABLE IF EXISTS %s" % (self.tbl))
            self.c.close()
        except:
            pass
        self.db.close()
    
    def test_executemany_escape(self):
        """lp: 675425: Problems with apostrophe"""
        
        data = [("ham","spam",),("spam","ham",),
            ("ham \\' spam","spam ' ham",)]
        sql = "INSERT INTO %s VALUES (%%s,%%s)" % (self.tbl)
        try:
            self.c.executemany(sql, data)
        except:
            self.fail("Failed inserting using executemany"
                " and escaped strings")

class Bug695514(tests.MySQLConnectorTests):
    """lp: 695514: Infinite recursion when setting connection client_flags"""

    def test_client_flags(self):
        """lp: 695514: Infinite recursion when setting connection client_flags
        """
        try:
            config = self.getMySQLConfig()
            config['client_flags'] = constants.ClientFlag.get_default()
            self.db = connection.MySQLConnection(**config)
        except:
            self.fail("Failed setting client_flags using integer")
    