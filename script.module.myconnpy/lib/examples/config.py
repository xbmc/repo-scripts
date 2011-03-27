# -*- coding: utf-8 -*-

class Config(object):
    """Configure me so examples work
    
    Use me like this:
    
        mysql.connector.Connect(**Config.dbinfo())
    """
    
    HOST = 'localhost'
    DATABASE = 'test'
    USER = ''
    PASSWORD = ''
    PORT = 3306
    
    CHARSET = 'utf8'
    UNICODE = True
    WARNINGS = True
    
    @classmethod
    def dbinfo(cls):
        return {
            'host': cls.HOST,
            'port': cls.PORT,
            'database': cls.DATABASE,
            'user': cls.USER,
            'password': cls.PASSWORD,
            'charset': cls.CHARSET,
            'use_unicode': cls.UNICODE,
            'get_warnings': cls.WARNINGS,
            }
    