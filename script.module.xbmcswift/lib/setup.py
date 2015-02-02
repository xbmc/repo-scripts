import os
from setuptools import setup, find_packages

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = 'XBMC Swift',
    version = '0.1',
    author = 'Jonathan Beluc',
    author_email = 'xbmc@jonathanbeluch.com',
    description = 'A micro framework for rapid development of XBMC plugins.',
    license = "GPL3",
    keywords = "example documentation tutorial",
    #url = '',
    packages=find_packages(),
    long_description=read('../README.md'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        #"License :: OSI Approved :: BSD License",
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Programming Language :: Python',
    ],
    entry_points={
       'console_scripts': [
           'xbmcswift = xbmcswift.console:main',
       ]
    },
)
