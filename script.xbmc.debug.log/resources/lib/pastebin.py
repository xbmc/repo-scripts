#!/usr/bin/env python

# Copyright (c) 2009-2010, Mario Vilas
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice,this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import urllib

# Python interface to the Pastebin API
# More information here: http://pastebin.com/api.php
# Blog post: http://http://breakingcode.wordpress.com/2010/03/06/using-the-pastebin-api-with-python/
class Pastebin(object):

    # Valid Pastebin URLs begin with this string
    prefix_url = 'http://pastebin.com/'

    # Valid Pastebin URLs with a custom subdomain begin with this string
    subdomain_url = 'http://%s.pastebin.com/' # % paste_subdomain

    # URL to the POST API
    api_url = 'http://pastebin.com/api_public.php'

    # Valid paste_expire_date values
    paste_expire_date = ('N', '10M', '1H', '1D', '1M')

    # Valid parse_format values
    paste_format = (
        'abap', 'actionscript', 'actionscript3', 'ada', 'apache',
        'applescript', 'apt_sources', 'asm', 'asp', 'autoit', 'avisynth',
        'bash', 'basic4gl', 'bibtex', 'blitzbasic', 'bnf', 'boo', 'bf', 'c',
        'c_mac', 'cill', 'csharp', 'cpp', 'caddcl', 'cadlisp', 'cfdg',
        'klonec', 'klonecpp', 'cmake', 'cobol', 'cfm', 'css', 'd', 'dcs',
        'delphi', 'dff', 'div', 'dos', 'dot', 'eiffel', 'email', 'erlang',
        'fo', 'fortran', 'freebasic', 'gml', 'genero', 'gettext', 'groovy',
        'haskell', 'hq9plus', 'html4strict', 'idl', 'ini', 'inno', 'intercal',
        'io', 'java', 'java5', 'javascript', 'kixtart', 'latex', 'lsl2',
        'lisp', 'locobasic', 'lolcode', 'lotusformulas', 'lotusscript',
        'lscript', 'lua', 'm68k', 'make', 'matlab', 'matlab', 'mirc',
        'modula3', 'mpasm', 'mxml', 'mysql', 'text', 'nsis', 'oberon2', 'objc',
        'ocaml-brief', 'ocaml', 'glsl', 'oobas', 'oracle11', 'oracle8',
        'pascal', 'pawn', 'per', 'perl', 'php', 'php-brief', 'pic16',
        'pixelbender', 'plsql', 'povray', 'powershell', 'progress', 'prolog',
        'properties', 'providex', 'python', 'qbasic', 'rails', 'rebol', 'reg',
        'robots', 'ruby', 'gnuplot', 'sas', 'scala', 'scheme', 'scilab',
        'sdlbasic', 'smalltalk', 'smarty', 'sql', 'tsql', 'tcl', 'tcl',
        'teraterm', 'thinbasic', 'typoscript', 'unreal', 'vbnet', 'verilog',
        'vhdl', 'vim', 'visualprolog', 'vb', 'visualfoxpro', 'whitespace',
        'whois', 'winbatch', 'xml', 'xorg_conf', 'xpp', 'z80'
    )

    # Submit a code snippet to Pastebin
    @classmethod
    def submit(cls, paste_code,
                paste_name = None, paste_email = None, paste_subdomain = None,
                paste_private = None, paste_expire_date = None,
                paste_format = None):

        # Code snippet to submit
        argv = { 'paste_code' : str(paste_code) }

        # Name of the poster
        if paste_name is not None:
            argv['paste_name'] = str(paste_name)
            
        if paste_email is not None:
            argv['paste_email'] = str(paste_email)    

        # Custom subdomain
        if paste_subdomain is not None:
            paste_subdomain = str(paste_subdomain).strip().lower()
            argv['paste_subdomain'] = paste_subdomain

        # Is the snippet private?
        if paste_private is not None:
            argv['paste_private'] = int(bool(int(paste_private)))

        # Expiration for the snippet
        if paste_expire_date is not None:
            paste_expire_date = str(paste_expire_date).strip().upper()
            if not paste_expire_date in cls.paste_expire_date:
                raise ValueError, "Bad expire date: %s" % paste_expire_date

        # Syntax highlighting
        if paste_format is not None:
            paste_format = str(paste_format).strip().lower()
            if not paste_format in cls.paste_format:
                raise ValueError, "Bad format: %s" % paste_format
            argv['paste_format'] = paste_format

        # Make the request to the Pastebin API
        fd = urllib.urlopen(cls.api_url, urllib.urlencode(argv))
        try:
            response = fd.read()
        finally:
            fd.close()
        del fd

        # Return the new snippet URL on success, raise exception on error
        if argv.has_key('paste_subdomain'):
            prefix = cls.subdomain_url % paste_subdomain
        else:
            prefix = cls.prefix_url
        if not response.startswith(prefix):
            raise RuntimeError, response
        return response

if __name__ == "__main__":
    import sys
    import optparse

    # Build the command line parser
    parser = optparse.OptionParser(usage = '%prog <file> [options]')
    parser.add_option("-n", "--name",
                      action="store", type="string", metavar="NAME",
                      help="Name of poster")
    parser.add_option("-s", "--subdomain",
                      action="store", type="string", metavar="SUBDOMAIN",
                      help="Custom subdomain")
    parser.add_option("--private",
                      action="store_true",
                      help="The snippet is private")
    parser.add_option("--public",
                      action="store_false", dest="private",
                      help="The snippet is public")
    parser.add_option("-e", "--expire",
                      action="store", type="string", metavar="TIME",
                      help="Expiration time: N (never), 10M (10 minutes), 1H (1 hour), 1D (1 day), 1M (1 month)")
    parser.add_option("-f", "--format", "--syntax", "--highlight",
                      action="store", type="string", metavar="FORMAT", dest="format",
                      help="Syntax highlighting, see source for full list")

    # Parse the command line and submit each snippet
    options, args = parser.parse_args(sys.argv)
    for filename in args[1:]:
        data = open(filename, 'rb').read()
        url = Pastebin.submit(paste_code = data,
                paste_name = options.name, paste_subdomain = options.subdomain,
                paste_private = options.private, paste_expire_date = options.expire,
                paste_format = options.format)
        print "%s\n --> %s" % (filename, url)