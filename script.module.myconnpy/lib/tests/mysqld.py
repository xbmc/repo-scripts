import sys
import os
from shutil import rmtree
import tempfile
import subprocess
import logging
import time

import tests

logger = logging.getLogger(tests.LOGGER_NAME)

class MySQLInstallError(Exception):

    def __init__(self, m):
        self.msg = m

    def __str__(self):
        return repr(self.msg)
        
class MySQLBootstrapError(MySQLInstallError):
    pass

class MySQLdError(MySQLInstallError):
    pass

class MySQLInstallBase(object):
    
    def __init__(self, basedir, optionFile=None):
        self._basedir = basedir
        self._bindir = None
        self._sbindir = None
        self._sharedir = None
        self._init_mysql_install()
        
        if optionFile is not None and os.access(optionFile,0):
            MySQLBootstrapError("Option file not accessible: %s" % \
                optionFile)
        self._optionFile = optionFile

    def _init_mysql_install(self):
        """Checking MySQL installation

        Check the MySQL installation and set the directories where
        to find binaries and SQL bootstrap scripts.

        Raises MySQLBootstrapError when something fails.
        """
        locs = ('libexec/','bin/','sbin/')
        for loc in locs:
            d = os.path.join(self._basedir,loc)
            if os.access(os.path.join(d,'mysqld'),0):
                self._sbindir = d
            if os.access(os.path.join(d,'mysql'),0):
                self._bindir = d

        if self._bindir is None or self._sbindir is None:
            raise MySQLBootstrapError("MySQL binaries not found under %s" %\
                self._basedir)

        locs = ('share/','share/mysql')
        for loc in locs:
            d = os.path.join(self._basedir,loc)
            if os.access(os.path.join(d,'mysql_system_tables.sql'),0):
                self._sharedir = d
                break

        if self._sharedir is None:
            raise MySQLBootstrapError("MySQL bootstrap scripts not found\
                under %s" % self._basedir)

class MySQLBootstrap(MySQLInstallBase):
    
    def __init__(self, topdir, datadir=None, optionFile=None,
                 basedir='/usr/local/mysql', tmpdir=None,
                 readOptionFile=False):
        if optionFile is not None:
            MySQLBootstrapError("No default option file support (yet)")
        self._topdir = topdir
        self._datadir = datadir or os.path.join(topdir,'data')
        self._tmpdir = tmpdir or os.path.join(topdir,'tmp')
        self.extra_sql = list()
        super(MySQLBootstrap, self).__init__(basedir, optionFile)
        
    def _create_directories(self):
        """Create directory structure for bootstrapping
        
        Create the directories needed for bootstrapping a MySQL
        installation, i.e. 'mysql' directory.
        The 'test' database is deliberatly not created.
        
        Raises MySQLBootstrapError when something fails.
        """
        logger.debug("Creating %(d)s %(d)s/mysql and %(d)s/test" % dict(
            d=self._datadir))
        try:
            os.mkdir(self._topdir)
            os.mkdir(os.path.join(self._topdir, 'tmp'))
            os.mkdir(self._datadir)
            os.mkdir(os.path.join(self._datadir, 'mysql'))
        except OSError, e:
            raise MySQLBootstrapError("Failed creating directories: " + str(e))

    def _get_bootstrap_cmd(self):
        """Get the command for bootstrapping.
        
        Get the command which will be used for bootstrapping. This is
        the full path to the mysqld executable and its arguments.
        
        Returns a list (used with subprocess.Popen)
        """
        cmd = [
          os.path.join(self._sbindir,'mysqld'),
          '--bootstrap',
          '--basedir=%s' % self._basedir,
          '--datadir=%s' % self._datadir,
          '--log-warnings=0',
          '--loose-skip-innodb',
          '--loose-skip-ndbcluster',
          '--max_allowed_packet=8M',
          '--default-storage-engine=myisam',
          '--net_buffer_length=16K',
          '--tmpdir=%s' % self._tmpdir,
        ]
        return cmd
    
    def bootstrap(self):
        """Bootstrap a MySQL installation
        
        Bootstarp a MySQL installation using the mysqld executable
        and the --bootstrap option. Arguments are defined by reading
        the defaults file and options set in the _get_bootstrap_cmd()
        method.
        
        Raises MySQLBootstrapError when something fails.
        """
        if os.access(self._datadir,0):
            raise MySQLBootstrapError("Datadir exists, can't bootstrap MySQL")
        
        # Order is important
        script_files = (
            'mysql_system_tables.sql',
            'mysql_system_tables_data.sql',
            'fill_help_tables.sql',
            )
        
        self._create_directories()
        try:
            cmd = self._get_bootstrap_cmd()
            sql = list()
            sql.append("USE mysql")
            for f in script_files:
                logger.debug("Reading SQL from '%s'" % f)
                fp = open(os.path.join(self._sharedir,f),'r')
                sql += fp.readlines()
                fp.close()
            sql += self.extra_sql
            prc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            prc.communicate('\n'.join(sql))
        except Exception, e:
            raise MySQLBootstrapError(e)

class MySQLd(MySQLInstallBase):
    
    def __init__(self, basedir, optionFile):
        self._process = None
        super(MySQLd, self).__init__(basedir, optionFile)
        
    def _get_cmd(self):
        cmd = [
            os.path.join(self._sbindir,'mysqld'),
            "--defaults-file=%s" % (self._optionFile)
        ]
        return cmd
        
    def start(self):
        try:
            cmd = self._get_cmd()
            self._process = subprocess.Popen(cmd)
        except Exception, e:
            raise MySQLdError(e)
    
    def stop(self):
        try:
            self._process.terminate()
        except Exception, e:
            raise MySQLdError(e)

class MySQLInit(object):
    
    def __init__(self, basedir, topdir, cnf, option_file, bind_address, port,
            unix_socket):
        self._cnf = cnf
        self._option_file = option_file
        self._unix_socket = unix_socket
        self._bind_address = bind_address
        self._port = port
        self._topdir = topdir
        self._basedir = basedir
        
        self._install = None
        self._server = None
        self._debug = False
        
    def bootstrap(self):
        """Bootstrap a MySQL server"""
        try:
            self._install = MySQLBootstrap(self._topdir,
                basedir=self._basedir)
            self._install.extra_sql = (
                "CREATE DATABASE myconnpy;",)
            self._install.bootstrap()
        except Exception, e:
            logger.error("Failed bootstrapping MySQL: %s" % e)
            if self._debug is True:
                raise
            sys.exit(1)
    
    def start(self):
        """Start a MySQL server"""
        try:
            fp = open(self._option_file,'w')
            fp.write(self._cnf % dict(
                mysqld_basedir=self._basedir,
                mysqld_datadir=self._install._datadir,
                mysqld_bind_address=self._bind_address,
                mysqld_port=self._port,
                mysqld_socket=self._unix_socket,
                ))
            fp.close()
            self._server = MySQLd(self._basedir,self._option_file)
            self._server.start()
            time.sleep(3)
        except MySQLdError, e:
            logger.error("Failed starting MySQL server: %s" % e)
            if self._debug is True:
                raise
            sys.exit(1)

    def stop(self):
        try:
            self._server.stop()
        except MySQLdError, e:
            logger.error("Failed stopping MySQL server: %s" % e)
            if self._debug is True:
                raise
        else:
            logger.info("MySQL server stopped.")
    
    def remove(self):
        try:
            rmtree(self._topdir)
        except Exception, e:
            logger.debug("Failed removing %s: %s" % (self._topdir, e))
            if self._debug is True:
                raise
        else:
            logger.info("Removed %s" % self._topdir)
    
