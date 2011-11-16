import os
from setuptools import setup, find_packages

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = 'python-brightcove',
    version = '0.1',
    author = 'Jonathan Beluch',
    author_email = 'web@jonathanbeluch.com',
    description = 'A python wrapper for the Brightcove read-only API.',
    license = "GPL3",
    keywords = "python brightcove api",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Programming Language :: Python',
    ],
)
